import copy
from dataclasses import replace
from datetime import datetime
from typing import Dict, List, Optional

from adjuntos_worker.models import (
    DocumentRecord,
    ExceptionRecord,
    FileFingerprint,
    NormalizedDocument,
    ParseAttemptRecord,
    ParseResult,
)


class NoopRepository:
    def __init__(self) -> None:
        self._next_id = 1
        self._next_parse_attempt_id = 1
        self._transaction_snapshot = None
        self.documents: Dict[int, DocumentRecord] = {}
        self.hash_index: Dict[str, int] = {}
        self.events: List[dict] = []
        self.parse_attempts: Dict[int, ParseAttemptRecord] = {}
        self.normalized_documents: Dict[int, dict] = {}
        self.exceptions: Dict[int, ExceptionRecord] = {}
        self._next_exception_id = 1

    def begin(self) -> None:
        if self._transaction_snapshot is not None:
            raise RuntimeError("Transaction already active in NoopRepository.")
        self._transaction_snapshot = {
            "next_id": self._next_id,
            "next_parse_attempt_id": self._next_parse_attempt_id,
            "documents": copy.deepcopy(self.documents),
            "hash_index": copy.deepcopy(self.hash_index),
            "events": copy.deepcopy(self.events),
            "parse_attempts": copy.deepcopy(self.parse_attempts),
            "normalized_documents": copy.deepcopy(self.normalized_documents),
            "exceptions": copy.deepcopy(self.exceptions),
            "next_exception_id": self._next_exception_id,
        }

    def commit(self) -> None:
        if self._transaction_snapshot is None:
            raise RuntimeError("No active transaction in NoopRepository.")
        self._transaction_snapshot = None

    def rollback(self) -> None:
        if self._transaction_snapshot is None:
            raise RuntimeError("No active transaction in NoopRepository.")
        snapshot = self._transaction_snapshot
        self._next_id = snapshot["next_id"]
        self._next_parse_attempt_id = snapshot["next_parse_attempt_id"]
        self.documents = snapshot["documents"]
        self.hash_index = snapshot["hash_index"]
        self.events = snapshot["events"]
        self.parse_attempts = snapshot["parse_attempts"]
        self.normalized_documents = snapshot["normalized_documents"]
        self.exceptions = snapshot["exceptions"]
        self._next_exception_id = snapshot["next_exception_id"]
        self._transaction_snapshot = None

    def open_exception(
        self,
        document_id: int,
        stage: str,
        severity: str,
        reason_code: str,
        reason_detail: str,
    ) -> int:
        opened_at = datetime.utcnow()
        exception_id = self._next_exception_id
        self._next_exception_id += 1
        self.exceptions[exception_id] = ExceptionRecord(
            exception_id=exception_id,
            document_id=document_id,
            stage=stage,
            severity=severity,
            reason_code=reason_code,
            reason_detail=reason_detail,
            opened_at=opened_at,
            closed_at=None,
            resolution_note=None,
        )
        return exception_id

    def close_open_exceptions(self, document_id: int, resolution_note: str) -> None:
        closed_at = datetime.utcnow()
        for exception_id, record in list(self.exceptions.items()):
            if record.document_id != document_id or record.closed_at is not None:
                continue
            self.exceptions[exception_id] = replace(
                record,
                closed_at=closed_at,
                resolution_note=resolution_note,
            )

    def get_document_id_by_hash(self, attachment_hash: str) -> Optional[int]:
        return self.hash_index.get(attachment_hash)

    def create_document_stub(
        self,
        fingerprint: FileFingerprint,
        source_path: str,
        current_status: str,
    ) -> int:
        document_id = self._next_id
        self._next_id += 1
        record = DocumentRecord(
            document_id=document_id,
            attachment_hash=fingerprint.sha256,
            original_filename=fingerprint.original_filename,
            source_path=source_path,
            archive_path=None,
            mime_type=fingerprint.mime_type,
            file_size_bytes=fingerprint.file_size_bytes,
            received_at=fingerprint.detected_at,
            current_status=current_status,
        )
        self.documents[document_id] = record
        self.hash_index[fingerprint.sha256] = document_id
        return document_id

    def update_document_status(
        self,
        document_id: int,
        current_status: str,
        archive_path: Optional[str] = None,
    ) -> None:
        current = self.documents[document_id]
        self.documents[document_id] = replace(
            current,
            current_status=current_status,
            archive_path=archive_path or current.archive_path,
        )

    def append_event(
        self,
        document_id: int,
        stage: str,
        event_type: str,
        message: str,
    ) -> None:
        self.events.append(
            {
                "document_id": document_id,
                "stage": stage,
                "event_type": event_type,
                "message": message,
            }
        )

    def get_document(self, document_id: int) -> DocumentRecord:
        return self.documents[document_id]

    def create_parse_attempt(
        self,
        document_id: int,
        parse_result: ParseResult,
        raw_json_path: str,
        raw_markdown_path: str,
    ) -> int:
        parse_attempt_id = self._next_parse_attempt_id
        self._next_parse_attempt_id += 1
        self.parse_attempts[parse_attempt_id] = ParseAttemptRecord(
            parse_attempt_id=parse_attempt_id,
            document_id=document_id,
            provider=parse_result.provider,
            provider_job_id=parse_result.provider_job_id,
            provider_tier=parse_result.provider_tier,
            provider_version=parse_result.provider_version,
            outcome=parse_result.outcome,
            raw_json_path=raw_json_path,
            raw_markdown_path=raw_markdown_path,
        )
        return parse_attempt_id

    def save_normalized_document(
        self,
        document_id: int,
        normalized_document: NormalizedDocument,
        normalized_json_path: str,
    ) -> None:
        payload = normalized_document.to_dict()
        payload["normalized_json_path"] = normalized_json_path
        self.normalized_documents[document_id] = payload

    def close(self) -> None:
        return None
