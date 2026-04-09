import logging
import time
from dataclasses import replace
from typing import Optional

from adjuntos_worker.classifier import classify_document
from adjuntos_worker.claimer import claim_file
from adjuntos_worker.config import AppConfig
from adjuntos_worker.filesystem import (
    create_archive_bundle,
    ensure_runtime_directories,
    finalize_duplicate,
    finalize_error,
    finalize_review,
    finalize_success,
)
from adjuntos_worker.fingerprint import fingerprint_file
from adjuntos_worker.normalizer import normalize_document
from adjuntos_worker.scanner import is_file_stable, scan_candidates
from adjuntos_worker.validator import apply_validation_result, validate_normalized_document


class WorkerApp:
    def __init__(self, config: AppConfig, repository, parser) -> None:
        self.config = config
        self.repository = repository
        self.parser = parser
        self.logger = logging.getLogger("adjuntos_worker")

    def run_forever(self) -> None:
        ensure_runtime_directories(self.config.paths)
        while True:
            processed = self.run_once()
            self.logger.info(
                "Scan cycle completed",
                extra={
                    "event_type": "SCAN_CYCLE",
                    "status": "OK",
                    "path": str(self.config.paths.in_dir),
                },
            )
            if processed:
                self.logger.info(
                    "Files processed in cycle: {0}".format(processed),
                    extra={"event_type": "SCAN_SUMMARY", "status": "OK"},
                )
            time.sleep(self.config.worker.scan_interval_seconds)

    def run_once(self) -> int:
        ensure_runtime_directories(self.config.paths)
        processed_count = 0

        for candidate in scan_candidates(
            self.config.paths.in_dir, self.config.worker.allowed_extensions
        ):
            if not is_file_stable(
                candidate,
                min_file_age_seconds=self.config.worker.min_file_age_seconds,
                stable_check_interval_seconds=self.config.worker.stable_check_interval_seconds,
            ):
                self.logger.info(
                    "Skipping unstable file",
                    extra={"event_type": "FILE_UNSTABLE", "path": str(candidate)},
                )
                continue

            if self._process_candidate(candidate):
                processed_count += 1

        return processed_count

    def close(self) -> None:
        self.repository.close()

    def _process_candidate(self, candidate) -> bool:
        document_id: Optional[int] = None
        claimed_file = None

        try:
            claimed_file = claim_file(candidate, self.config.paths.processing_dir)
            fingerprint = fingerprint_file(claimed_file.claimed_path)

            existing_document_id = self.repository.get_document_id_by_hash(fingerprint.sha256)
            if existing_document_id is not None:
                duplicate_path = finalize_duplicate(
                    claimed_file, fingerprint, self.config.paths.duplicates_dir
                )
                self.repository.append_event(
                    existing_document_id,
                    stage="INTAKE",
                    event_type="DUPLICATE_DETECTED",
                    message="Duplicate file moved to {0}".format(duplicate_path),
                )
                self.logger.info(
                    "Duplicate file detected",
                    extra={
                        "document_id": existing_document_id,
                        "attachment_hash": fingerprint.sha256,
                        "event_type": "DUPLICATE_DETECTED",
                        "path": str(duplicate_path),
                        "status": "DUPLICATE",
                    },
                )
                return True

            document_id = self.repository.create_document_stub(
                fingerprint=fingerprint,
                source_path=str(candidate),
                current_status="CLAIMED",
            )
            self.repository.append_event(
                document_id,
                stage="INTAKE",
                event_type="CLAIMED",
                message="File moved to {0}".format(claimed_file.claimed_path),
            )
            classification = classify_document(
                claimed_file.claimed_path,
                text="",
                parse_settings=self.config.parse,
            )
            self.repository.append_event(
                document_id,
                stage="CLASSIFICATION",
                event_type="CLASSIFIED",
                message="Initial type={0}, tier={1}. {2}".format(
                    classification.document_type,
                    classification.provider_tier,
                    classification.rationale,
                ),
            )
            self.repository.update_document_status(document_id, current_status="PARSING")
            self.repository.append_event(
                document_id,
                stage="PARSING",
                event_type="PARSING_STARTED",
                message="Submitting document to parser provider {0}".format(self.parser.provider_name),
            )

            parse_result = self.parser.parse(claimed_file.claimed_path, classification)
            classification = classify_document(
                claimed_file.claimed_path,
                text=parse_result.markdown,
                parse_settings=self.config.parse,
            )
            normalized_document = normalize_document(classification, parse_result)
            validation = validate_normalized_document(normalized_document)
            normalized_document = apply_validation_result(normalized_document, validation)

            archive_bundle = create_archive_bundle(
                claimed_file=claimed_file,
                fingerprint=fingerprint,
                archive_dir=self.config.paths.archive_dir,
                parse_result=parse_result,
                normalized_document=normalized_document,
            )
            self.repository.create_parse_attempt(
                document_id=document_id,
                parse_result=parse_result,
                raw_json_path=str(archive_bundle / "parse_raw.json"),
                raw_markdown_path=str(archive_bundle / "parse.md"),
            )
            self.repository.update_document_status(document_id, current_status="PARSED")
            self.repository.append_event(
                document_id,
                stage="PARSING",
                event_type="PARSED",
                message="Parser returned outcome {0}.".format(parse_result.outcome),
            )
            self.repository.save_normalized_document(
                document_id=document_id,
                normalized_document=normalized_document,
                normalized_json_path=str(archive_bundle / "normalized.json"),
            )
            self.repository.update_document_status(
                document_id,
                current_status="NORMALIZED",
                archive_path=str(archive_bundle),
            )
            self.repository.append_event(
                document_id,
                stage="NORMALIZATION",
                event_type="NORMALIZED",
                message="Document normalized as {0}.".format(normalized_document.document_type),
            )
            self.repository.update_document_status(document_id, current_status="VALIDATED")
            self.repository.append_event(
                document_id,
                stage="VALIDATION",
                event_type="VALIDATED",
                message=validation.notes or "Document passed required-field validation.",
            )

            if normalized_document.review_required:
                review_path = finalize_review(
                    claimed_file, fingerprint, self.config.paths.review_dir
                )
                self.repository.update_document_status(
                    document_id,
                    current_status="REVIEW",
                    archive_path=str(archive_bundle),
                )
                self.repository.append_event(
                    document_id,
                    stage="VALIDATION",
                    event_type="REVIEW_REQUIRED",
                    message="Document sent to Review at {0}".format(review_path),
                )
                self.logger.info(
                    "File sent to review",
                    extra={
                        "document_id": document_id,
                        "attachment_hash": fingerprint.sha256,
                        "event_type": "REVIEW_REQUIRED",
                        "path": str(review_path),
                        "status": "REVIEW",
                    },
                )
            else:
                processed_path = finalize_success(
                    claimed_file, fingerprint, self.config.paths.processed_dir
                )
                self.repository.update_document_status(
                    document_id,
                    current_status="PROCESSED",
                    archive_path=str(archive_bundle),
                )
                self.repository.append_event(
                    document_id,
                    stage="VALIDATION",
                    event_type="PROCESSED",
                    message="Document stored at {0}".format(processed_path),
                )
                self.logger.info(
                    "File processed successfully",
                    extra={
                        "document_id": document_id,
                        "attachment_hash": fingerprint.sha256,
                        "event_type": "PROCESSED",
                        "path": str(processed_path),
                        "status": "PROCESSED",
                    },
                )
            return True

        except Exception:
            self.logger.exception(
                "Unhandled error while processing file",
                extra={"path": str(candidate), "status": "ERROR"},
            )

            if claimed_file is not None:
                error_path = finalize_error(claimed_file, self.config.paths.error_dir)
                if document_id is not None:
                    try:
                        self.repository.update_document_status(document_id, current_status="ERROR")
                        self.repository.append_event(
                            document_id,
                            stage="INTAKE",
                            event_type="ERROR",
                            message="File moved to {0} after failure".format(error_path),
                        )
                    except Exception:
                        self.logger.exception(
                            "Could not record error status in repository",
                            extra={"document_id": document_id, "path": str(error_path)},
                        )
            return False
