from typing import Optional, Protocol

from adjuntos_worker.models import (
    DocumentRecord,
    FileFingerprint,
    NormalizedDocument,
    ParseAttemptRecord,
    ParseResult,
)


class Repository(Protocol):
    def get_document_id_by_hash(self, attachment_hash: str) -> Optional[int]:
        ...

    def create_document_stub(
        self,
        fingerprint: FileFingerprint,
        source_path: str,
        current_status: str,
    ) -> int:
        ...

    def update_document_status(
        self,
        document_id: int,
        current_status: str,
        archive_path: Optional[str] = None,
    ) -> None:
        ...

    def append_event(
        self,
        document_id: int,
        stage: str,
        event_type: str,
        message: str,
    ) -> None:
        ...

    def get_document(self, document_id: int) -> DocumentRecord:
        ...

    def create_parse_attempt(
        self,
        document_id: int,
        parse_result: ParseResult,
        raw_json_path: str,
        raw_markdown_path: str,
    ) -> int:
        ...

    def save_normalized_document(
        self,
        document_id: int,
        normalized_document: NormalizedDocument,
        normalized_json_path: str,
    ) -> None:
        ...

    def close(self) -> None:
        ...
