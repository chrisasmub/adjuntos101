import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adjuntos_worker.config import (
    AppConfig,
    DatabaseSettings,
    LoggingSettings,
    ParseSettings,
    PathSettings,
    WorkerSettings,
)
from adjuntos_worker.webapp import _parse_limit, _status_class, build_wsgi_app


class WebAppTests(unittest.TestCase):
    def _build_config(self, base_dir: Path) -> AppConfig:
        paths = PathSettings(
            base_dir=base_dir,
            in_dir=base_dir / "In",
            processing_dir=base_dir / "Processing",
            processed_dir=base_dir / "Processed",
            review_dir=base_dir / "Review",
            error_dir=base_dir / "Error",
            archive_dir=base_dir / "Archive",
            duplicates_dir=base_dir / "Processed" / "Duplicates",
        )
        worker = WorkerSettings(
            scan_interval_seconds=30,
            min_file_age_seconds=90,
            stable_check_interval_seconds=5,
            allowed_extensions=["pdf"],
        )
        database = DatabaseSettings(
            mode="iris",
            host="localhost",
            port=1972,
            namespace="USER",
            username="admin",
            password="secret",
        )
        parse = ParseSettings(
            mode="mock",
            api_key="",
            base_url="https://api.cloud.llamaindex.ai/api/v2",
            default_tier="cost_effective",
            complex_tier="agentic",
            version="latest",
            poll_seconds=5,
            timeout_seconds=300,
        )
        logging = LoggingSettings(level="INFO")
        return AppConfig(paths=paths, worker=worker, database=database, parse=parse, logging=logging)

    def _call_app(self, app, path: str, method: str = "GET"):
        query_string = ""
        path_info = path
        if "?" in path:
            path_info, query_string = path.split("?", 1)

        response = {}

        def start_response(status, headers):
            response["status"] = status
            response["headers"] = headers

        body = b"".join(
            app(
                {
                    "REQUEST_METHOD": method,
                    "PATH_INFO": path_info,
                    "QUERY_STRING": query_string,
                    "wsgi.input": None,
                },
                start_response,
            )
        )
        response["body"] = body
        return response

    def test_parse_limit_bounds_value(self):
        self.assertEqual(_parse_limit("500"), 200)
        self.assertEqual(_parse_limit("0"), 1)
        self.assertEqual(_parse_limit("12"), 12)
        self.assertEqual(_parse_limit("oops"), 50)

    def test_status_class_maps_known_states(self):
        self.assertEqual(_status_class("PROCESSED"), "ok")
        self.assertEqual(_status_class("REVIEW"), "warn")
        self.assertEqual(_status_class("ERROR"), "err")
        self.assertEqual(_status_class("DUPLICATE"), "dup")
        self.assertEqual(_status_class("OTHER"), "neutral")

    def test_document_detail_route_renders_artifact_links(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            archive_dir = base_dir / "Archive" / "bundle"
            archive_dir.mkdir(parents=True, exist_ok=True)
            original_path = archive_dir / "original.pdf"
            parse_raw_path = archive_dir / "parse_raw.json"
            parse_markdown_path = archive_dir / "parse.md"
            normalized_path = archive_dir / "normalized.json"
            original_path.write_bytes(b"%PDF-1.4 fake")
            parse_raw_path.write_text('{"ok": true}', encoding="utf-8")
            parse_markdown_path.write_text("# Parsed", encoding="utf-8")
            normalized_path.write_text('{"document_type": "invoice"}', encoding="utf-8")

            fake_read_model = mock.Mock()
            fake_read_model.summary_counts.return_value = {"ALL": 1, "PROCESSED": 1}
            fake_read_model.list_documents.return_value = [
                {
                    "document_id": 42,
                    "original_filename": "invoice.pdf",
                    "current_status": "PROCESSED",
                    "document_type": "invoice",
                    "issuer_name": "ACME SpA",
                    "issue_date": "2026-04-13",
                    "currency": "CLP",
                    "total_amount": 12345,
                }
            ]
            fake_read_model.get_document_detail.return_value = {
                "document_id": 42,
                "attachment_hash": "abc123",
                "original_filename": "invoice.pdf",
                "source_path": "/tmp/In/invoice.pdf",
                "archive_path": str(archive_dir),
                "mime_type": "application/pdf",
                "file_size_bytes": 123,
                "received_at": "2026-04-13 22:00:00",
                "current_status": "PROCESSED",
                "document_type": "invoice",
                "issuer_name": "ACME SpA",
                "issuer_tax_id": "",
                "issue_date": "2026-04-13",
                "due_date": None,
                "period_from": None,
                "period_to": None,
                "currency": "CLP",
                "total_amount": 12345,
                "balance_amount": None,
                "account_ref_last4": "",
                "document_number": "F-42",
                "confidence": 0.9,
                "review_required": False,
                "normalized_json_path": str(normalized_path),
                "parse_attempts": [
                    {
                        "parse_attempt_id": 7,
                        "provider": "mock",
                        "provider_job_id": "job-1",
                        "provider_tier": "cost_effective",
                        "provider_version": "latest",
                        "started_at": "2026-04-13 22:00:00",
                        "completed_at": "2026-04-13 22:00:01",
                        "outcome": "COMPLETED",
                        "raw_json_path": str(parse_raw_path),
                        "raw_markdown_path": str(parse_markdown_path),
                        "error_code": None,
                        "error_message": None,
                    }
                ],
                "events": [
                    {
                        "event_id": 1,
                        "event_ts": "2026-04-13 22:00:00",
                        "stage": "VALIDATION",
                        "event_type": "PROCESSED",
                        "message": "ok",
                    }
                ],
                "exceptions": [],
                "normalized_json": {"document_type": "invoice"},
                "artifacts": {
                    "original": str(original_path),
                    "parse_raw": str(parse_raw_path),
                    "parse_markdown": str(parse_markdown_path),
                    "normalized_json": str(normalized_path),
                },
            }

            with mock.patch("adjuntos_worker.webapp.IrisReadModel", return_value=fake_read_model):
                app = build_wsgi_app(self._build_config(base_dir))
                response = self._call_app(app, "/documents/42")

            self.assertEqual(response["status"], "200 OK")
            body = response["body"].decode("utf-8")
            self.assertIn("Documento #42", body)
            self.assertIn("/documents/42/artifacts/original", body)
            self.assertIn("/documents/42/artifacts/parse_raw", body)
            self.assertIn("/documents/42/artifacts/parse_markdown", body)
            self.assertIn("/documents/42/artifacts/normalized_json", body)

    def test_document_artifact_route_serves_file_content(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            artifact_path = base_dir / "normalized.json"
            artifact_path.write_text('{"document_type":"invoice"}', encoding="utf-8")

            fake_read_model = mock.Mock()
            fake_read_model.get_document_detail.return_value = {
                "document_id": 42,
                "artifacts": {
                    "normalized_json": str(artifact_path),
                },
            }

            with mock.patch("adjuntos_worker.webapp.IrisReadModel", return_value=fake_read_model):
                app = build_wsgi_app(self._build_config(base_dir))
                response = self._call_app(app, "/documents/42/artifacts/normalized_json")

            self.assertEqual(response["status"], "200 OK")
            header_map = dict(response["headers"])
            self.assertEqual(header_map["Content-Type"], "application/json")
            self.assertIn(b'"document_type":"invoice"', response["body"])


if __name__ == "__main__":
    unittest.main()
