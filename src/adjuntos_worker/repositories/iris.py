from datetime import datetime
from typing import Optional

from adjuntos_worker.config import DatabaseSettings
from adjuntos_worker.models import (
    DocumentRecord,
    FileFingerprint,
    NormalizedDocument,
    ParseResult,
)


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
        connection.setAutoCommit(False)
        connection.autocommit = False
        if connection.autocommit:
            raise RuntimeError("Could not disable autocommit for IRIS connection.")
        return cls(connection)

    def begin(self) -> None:
        return None

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def open_exception(
        self,
        document_id: int,
        stage: str,
        severity: str,
        reason_code: str,
        reason_detail: str,
    ) -> int:
        opened_at = datetime.utcnow()
        cursor = self._connection.cursor()
        cursor.execute(
            """
            INSERT INTO doc_exception
                (document_id, stage, severity, reason_code, reason_detail, opened_at, closed_at, resolution_note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (document_id, stage, severity, reason_code, reason_detail, opened_at, None, None),
        )
        cursor.execute(
            """
            SELECT exception_id
              FROM doc_exception
             WHERE document_id = ? AND opened_at = ?
            """,
            (document_id, opened_at),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("IRIS insert completed but exception_id could not be retrieved.")
        return int(row[0])

    def close_open_exceptions(self, document_id: int, resolution_note: str) -> None:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            UPDATE doc_exception
               SET closed_at = ?,
                   resolution_note = ?
             WHERE document_id = ?
               AND closed_at IS NULL
            """,
            (datetime.utcnow(), resolution_note, document_id),
        )

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

    def create_parse_attempt(
        self,
        document_id: int,
        parse_result: ParseResult,
        raw_json_path: str,
        raw_markdown_path: str,
    ) -> int:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            INSERT INTO doc_parse_attempt
                (document_id, provider, provider_job_id, provider_tier, provider_version,
                 started_at, completed_at, outcome, raw_json_path, raw_markdown_path,
                 error_code, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                parse_result.provider,
                parse_result.provider_job_id,
                parse_result.provider_tier,
                parse_result.provider_version,
                parse_result.started_at,
                parse_result.completed_at,
                parse_result.outcome,
                raw_json_path,
                raw_markdown_path,
                None,
                None,
            ),
        )
        cursor.execute(
            """
            SELECT parse_attempt_id
              FROM doc_parse_attempt
             WHERE document_id = ? AND provider_job_id = ?
            """,
            (document_id, parse_result.provider_job_id),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("IRIS insert completed but parse_attempt_id could not be retrieved.")
        return int(row[0])

    def save_normalized_document(
        self,
        document_id: int,
        normalized_document: NormalizedDocument,
        normalized_json_path: str,
    ) -> None:
        cursor = self._connection.cursor()
        cursor.execute(
            "SELECT document_id FROM doc_normalized WHERE document_id = ?",
            (document_id,),
        )
        exists = cursor.fetchone() is not None
        payload = (
            normalized_document.document_type,
            normalized_document.issuer_name,
            normalized_document.issuer_tax_id,
            normalized_document.issue_date,
            normalized_document.due_date,
            normalized_document.period_from,
            normalized_document.period_to,
            normalized_document.currency,
            normalized_document.total_amount,
            normalized_document.balance_amount,
            normalized_document.account_ref_last4,
            normalized_document.document_number,
            normalized_document.confidence,
            1 if normalized_document.review_required else 0,
            normalized_json_path,
            document_id,
        )
        if exists:
            cursor.execute(
                """
                UPDATE doc_normalized
                   SET document_type = ?,
                       issuer_name = ?,
                       issuer_tax_id = ?,
                       issue_date = ?,
                       due_date = ?,
                       period_from = ?,
                       period_to = ?,
                       currency = ?,
                       total_amount = ?,
                       balance_amount = ?,
                       account_ref_last4 = ?,
                       document_number = ?,
                       confidence = ?,
                       review_required = ?,
                       normalized_json_path = ?
                 WHERE document_id = ?
                """,
                payload,
            )
        else:
            cursor.execute(
                """
                INSERT INTO doc_normalized
                    (document_id, document_type, issuer_name, issuer_tax_id, issue_date,
                     due_date, period_from, period_to, currency, total_amount, balance_amount,
                     account_ref_last4, document_number, confidence, review_required,
                     normalized_json_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    normalized_document.document_type,
                    normalized_document.issuer_name,
                    normalized_document.issuer_tax_id,
                    normalized_document.issue_date,
                    normalized_document.due_date,
                    normalized_document.period_from,
                    normalized_document.period_to,
                    normalized_document.currency,
                    normalized_document.total_amount,
                    normalized_document.balance_amount,
                    normalized_document.account_ref_last4,
                    normalized_document.document_number,
                    normalized_document.confidence,
                    1 if normalized_document.review_required else 0,
                    normalized_json_path,
                ),
            )
    def close(self) -> None:
        self._connection.close()
