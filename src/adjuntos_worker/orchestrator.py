import logging
import time
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
        fingerprint = None
        transaction_started = False
        final_path = None
        current_stage = "INTAKE"

        try:
            claimed_file = claim_file(candidate, self.config.paths.processing_dir)
            fingerprint = fingerprint_file(claimed_file.claimed_path)

            existing_document_id = self.repository.get_document_id_by_hash(fingerprint.sha256)
            if existing_document_id is not None:
                final_path = finalize_duplicate(claimed_file, fingerprint, self.config.paths.duplicates_dir)
                self.repository.begin()
                transaction_started = True
                self.repository.append_event(
                    existing_document_id,
                    stage="INTAKE",
                    event_type="DUPLICATE_DETECTED",
                    message="Duplicate file moved to {0}".format(final_path),
                )
                self.repository.commit()
                transaction_started = False
                self.logger.info(
                    "Duplicate file detected",
                    extra={
                        "document_id": existing_document_id,
                        "attachment_hash": fingerprint.sha256,
                        "event_type": "DUPLICATE_DETECTED",
                        "path": str(final_path),
                        "status": "DUPLICATE",
                    },
                )
                return True

            self.repository.begin()
            transaction_started = True
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
            current_stage = "CLASSIFICATION"
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
            current_stage = "PARSING"
            self.repository.append_event(
                document_id,
                stage="PARSING",
                event_type="PARSING_STARTED",
                message="Submitting document to parser provider {0}".format(self.parser.provider_name),
            )

            parse_result = self._parse_with_retry(
                claimed_file.claimed_path,
                classification,
                document_id=document_id,
                attachment_hash=fingerprint.sha256,
            )
            classification = classify_document(
                claimed_file.claimed_path,
                text=parse_result.markdown,
                parse_settings=self.config.parse,
            )
            current_stage = "NORMALIZATION"
            normalized_document = normalize_document(classification, parse_result)
            current_stage = "VALIDATION"
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
                final_path = finalize_review(claimed_file, fingerprint, self.config.paths.review_dir)
                self.repository.update_document_status(
                    document_id,
                    current_status="REVIEW",
                    archive_path=str(archive_bundle),
                )
                self.repository.append_event(
                    document_id,
                    stage="VALIDATION",
                    event_type="REVIEW_REQUIRED",
                    message="Document sent to Review at {0}".format(final_path),
                )
                self.logger.info(
                    "File sent to review",
                    extra={
                        "document_id": document_id,
                        "attachment_hash": fingerprint.sha256,
                        "event_type": "REVIEW_REQUIRED",
                        "path": str(final_path),
                        "status": "REVIEW",
                    },
                )
            else:
                final_path = finalize_success(claimed_file, fingerprint, self.config.paths.processed_dir)
                self.repository.update_document_status(
                    document_id,
                    current_status="PROCESSED",
                    archive_path=str(archive_bundle),
                )
                self.repository.append_event(
                    document_id,
                    stage="VALIDATION",
                    event_type="PROCESSED",
                    message="Document stored at {0}".format(final_path),
                )
                self.logger.info(
                    "File processed successfully",
                    extra={
                        "document_id": document_id,
                        "attachment_hash": fingerprint.sha256,
                        "event_type": "PROCESSED",
                        "path": str(final_path),
                        "status": "PROCESSED",
                    },
                )
            self.repository.close_open_exceptions(
                document_id,
                resolution_note="Document reached final state {0}".format(
                    "REVIEW" if normalized_document.review_required else "PROCESSED"
                ),
            )
            self.repository.commit()
            transaction_started = False
            return True

        except Exception as exc:
            if transaction_started:
                try:
                    self.repository.rollback()
                except Exception:
                    self.logger.exception(
                        "Could not rollback repository transaction",
                        extra={"document_id": document_id, "path": str(candidate)},
                    )
            self.logger.exception(
                "Unhandled error while processing file",
                extra={"path": str(candidate), "status": "ERROR"},
            )

            if claimed_file is not None:
                if claimed_file.claimed_path.exists():
                    final_path = finalize_error(claimed_file, self.config.paths.error_dir)
                if fingerprint is not None:
                    try:
                        self.repository.begin()
                        transaction_started = True
                        document_id = self.repository.create_document_stub(
                            fingerprint=fingerprint,
                            source_path=str(candidate),
                            current_status="ERROR",
                        )
                        reason_code = "{0}_FAILED".format(current_stage)
                        reason_detail = "{0}: {1}".format(type(exc).__name__, exc)
                        self.repository.open_exception(
                            document_id,
                            stage=current_stage,
                            severity="ERROR",
                            reason_code=reason_code,
                            reason_detail=reason_detail,
                        )
                        self.repository.append_event(
                            document_id,
                            stage=current_stage,
                            event_type="ERROR",
                            message="File moved to {0} after failure ({1}).".format(
                                final_path or candidate,
                                reason_code,
                            ),
                        )
                        self.repository.commit()
                        transaction_started = False
                    except Exception:
                        if transaction_started:
                            try:
                                self.repository.rollback()
                            except Exception:
                                self.logger.exception(
                                    "Could not rollback error registration transaction",
                                    extra={"document_id": document_id, "path": str(candidate)},
                                )
                        self.logger.exception(
                            "Could not record error status in repository",
                            extra={"document_id": document_id, "path": str(final_path or candidate)},
                        )
            return False

    def _parse_with_retry(self, path, classification, document_id: int, attachment_hash: str):
        max_retries = max(0, self.config.parse.max_retries)
        attempt = 0

        while True:
            try:
                return self.parser.parse(path, classification)
            except Exception as exc:
                if attempt >= max_retries or not self._is_retryable_parser_error(exc):
                    raise

                attempt += 1
                backoff_seconds = max(0, self.config.parse.retry_backoff_seconds) * attempt
                self.repository.append_event(
                    document_id,
                    stage="PARSING",
                    event_type="PARSING_RETRY",
                    message="Retry {0}/{1} after transient parser error: {2}: {3}".format(
                        attempt,
                        max_retries,
                        type(exc).__name__,
                        exc,
                    ),
                )
                self.logger.warning(
                    "Transient parser error; retrying parse",
                    extra={
                        "document_id": document_id,
                        "attachment_hash": attachment_hash,
                        "event_type": "PARSING_RETRY",
                        "status": "RETRY",
                        "path": str(path),
                    },
                )
                if backoff_seconds:
                    time.sleep(backoff_seconds)

    def _is_retryable_parser_error(self, exc: Exception) -> bool:
        retryable_names = {
            "TimeoutError",
            "ReadTimeout",
            "WriteTimeout",
            "ConnectTimeout",
            "PoolTimeout",
            "ConnectError",
            "ReadError",
            "RemoteProtocolError",
            "NetworkError",
            "TransportError",
        }
        if type(exc).__name__ in retryable_names:
            return True
        if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
            return True

        message = str(exc).lower()
        return any(
            marker in message
            for marker in (
                "timeout",
                "timed out",
                "temporary failure",
                "temporarily unavailable",
                "connection reset",
                "connection refused",
                "connection aborted",
                "429",
                "502",
                "503",
                "504",
                "rate limit",
            )
        )
