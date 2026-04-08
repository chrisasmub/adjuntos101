from dataclasses import replace
from typing import Dict, List, Optional

from adjuntos_worker.models import DocumentRecord, FileFingerprint


class NoopRepository:
    def __init__(self) -> None:
        self._next_id = 1
        self.documents: Dict[int, DocumentRecord] = {}
        self.hash_index: Dict[str, int] = {}
        self.events: List[dict] = []

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

    def close(self) -> None:
        return None

