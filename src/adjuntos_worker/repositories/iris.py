from datetime import datetime
from typing import Optional

from adjuntos_worker.config import DatabaseSettings
from adjuntos_worker.models import DocumentRecord, FileFingerprint


class IrisRepository:
    def __init__(self, connection) -> None:
        self._connection = connection

    @classmethod
    def from_settings(cls, settings: DatabaseSettings) -> "IrisRepository":
        try:
            import iris  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "The intersystems-irispython package is required when DATABASE_MODE=iris."
            ) from exc

        connection = iris.connect(settings.dsn, settings.username, settings.password)
        return cls(connection)

    def get_document_id_by_hash(self, attachment_hash: str) -> Optional[int]:
        cursor = self._connection.cursor()
        cursor.execute(
            "SELECT document_id FROM doc_document WHERE attachment_hash = ?",
            (attachment_hash,),
        )
        row = cursor.fetchone()
        return None if row is None else int(row[0])

    def create_document_stub(
        self,
        fingerprint: FileFingerprint,
        source_path: str,
        current_status: str,
    ) -> int:
        timestamp = datetime.utcnow()
        cursor = self._connection.cursor()
        cursor.execute(
            """
            INSERT INTO doc_document
                (attachment_hash, original_filename, source_path, archive_path, mime_type,
                 file_size_bytes, source_email, source_subject, received_at, current_status,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fingerprint.sha256,
                fingerprint.original_filename,
                source_path,
                None,
                fingerprint.mime_type,
                fingerprint.file_size_bytes,
                None,
                None,
                timestamp,
                current_status,
                timestamp,
                timestamp,
            ),
        )
        self._connection.commit()

        cursor.execute(
            "SELECT document_id FROM doc_document WHERE attachment_hash = ?",
            (fingerprint.sha256,),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("IRIS insert completed but document_id could not be retrieved.")
        return int(row[0])

    def update_document_status(
        self,
        document_id: int,
        current_status: str,
        archive_path: Optional[str] = None,
    ) -> None:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            UPDATE doc_document
               SET current_status = ?,
                   archive_path = COALESCE(?, archive_path),
                   updated_at = ?
             WHERE document_id = ?
            """,
            (current_status, archive_path, datetime.utcnow(), document_id),
        )
        self._connection.commit()

    def append_event(
        self,
        document_id: int,
        stage: str,
        event_type: str,
        message: str,
    ) -> None:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            INSERT INTO doc_event (document_id, event_ts, stage, event_type, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (document_id, datetime.utcnow(), stage, event_type, message),
        )
        self._connection.commit()

    def get_document(self, document_id: int) -> DocumentRecord:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT document_id, attachment_hash, original_filename, source_path, archive_path,
                   mime_type, file_size_bytes, received_at, current_status
              FROM doc_document
             WHERE document_id = ?
            """,
            (document_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise KeyError("Document not found: {0}".format(document_id))
        return DocumentRecord(
            document_id=int(row[0]),
            attachment_hash=str(row[1]),
            original_filename=str(row[2]),
            source_path=str(row[3]),
            archive_path=None if row[4] is None else str(row[4]),
            mime_type="" if row[5] is None else str(row[5]),
            file_size_bytes=int(row[6]),
            received_at=row[7],
            current_status=str(row[8]),
        )

    def close(self) -> None:
        self._connection.close()

