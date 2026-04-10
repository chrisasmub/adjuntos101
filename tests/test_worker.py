import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adjuntos_worker.config import (
    AppConfig,
    DatabaseSettings,
    LoggingSettings,
    ParseSettings,
    PathSettings,
    WorkerSettings,
)
from adjuntos_worker.orchestrator import WorkerApp
from adjuntos_worker.parse_clients.mock import MockParseClient
from adjuntos_worker.repositories.noop import NoopRepository


class ExplodingParseClient:
    provider_name = "exploding"

    def parse(self, path, classification):
        raise RuntimeError("Synthetic parser failure")


class FlakyParseClient:
    provider_name = "flaky"

    def __init__(self) -> None:
        self.attempts = 0

    def parse(self, path, classification):
        self.attempts += 1
        if self.attempts == 1:
            raise TimeoutError("Synthetic timeout")
        return MockParseClient().parse(path, classification)


class WorkerAppTests(unittest.TestCase):
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
            scan_interval_seconds=1,
            min_file_age_seconds=0,
            stable_check_interval_seconds=0,
            allowed_extensions=["pdf", "png"],
        )
        database = DatabaseSettings(
            mode="noop",
            host="localhost",
            port=1972,
            namespace="DOCSPOC",
            username="USER",
            password="",
        )
        parse = ParseSettings(
            mode="mock",
            api_key="",
            base_url="https://api.cloud.llamaindex.ai/api/v2",
            default_tier="cost_effective",
            complex_tier="agentic",
            version="latest",
            poll_seconds=1,
            timeout_seconds=10,
            max_retries=2,
            retry_backoff_seconds=0,
        )
        logging = LoggingSettings(level="INFO")
        return AppConfig(paths=paths, worker=worker, database=database, parse=parse, logging=logging)

    def test_run_once_processes_file_and_updates_repository(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            config = self._build_config(base_dir)
            repository = NoopRepository()
            app = WorkerApp(config, repository, MockParseClient())

            config.paths.in_dir.mkdir(parents=True, exist_ok=True)
            file_path = config.paths.in_dir / "sample.pdf"
            file_path.write_text(
                "\n".join(
                    [
                        "Factura Electronica",
                        "Emisor: ACME SpA",
                        "Fecha Emision: 2026-04-01",
                        "Moneda: CLP",
                        "Monto Total: 12345",
                        "Numero Documento: F-100",
                    ]
                ),
                encoding="utf-8",
            )

            processed_count = app.run_once()

            self.assertEqual(processed_count, 1)
            self.assertEqual(len(repository.documents), 1)
            self.assertEqual(len(repository.parse_attempts), 1)
            self.assertEqual(len(repository.normalized_documents), 1)

            record = repository.get_document(1)
            self.assertEqual(record.current_status, "PROCESSED")
            self.assertTrue(Path(record.archive_path).exists())
            self.assertTrue((Path(record.archive_path) / "normalized.json").exists())

            processed_files = list(config.paths.processed_dir.rglob("sample.pdf"))
            self.assertEqual(len(processed_files), 1)

    def test_run_once_routes_duplicate_to_duplicates_folder(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            config = self._build_config(base_dir)
            repository = NoopRepository()
            app = WorkerApp(config, repository, MockParseClient())

            config.paths.in_dir.mkdir(parents=True, exist_ok=True)

            first_file = config.paths.in_dir / "first.pdf"
            first_file.write_text(
                "Factura Electronica\nEmisor: Demo\nFecha Emision: 2026-04-02\nMoneda: CLP\nMonto Total: 2000",
                encoding="utf-8",
            )
            app.run_once()

            second_file = config.paths.in_dir / "second.pdf"
            second_file.write_text(
                "Factura Electronica\nEmisor: Demo\nFecha Emision: 2026-04-02\nMoneda: CLP\nMonto Total: 2000",
                encoding="utf-8",
            )
            processed_count = app.run_once()

            self.assertEqual(processed_count, 1)
            self.assertEqual(len(repository.documents), 1)

            duplicates = list(config.paths.duplicates_dir.rglob("second.pdf"))
            self.assertEqual(len(duplicates), 1)

    def test_run_once_routes_incomplete_document_to_review(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            config = self._build_config(base_dir)
            repository = NoopRepository()
            app = WorkerApp(config, repository, MockParseClient())

            config.paths.in_dir.mkdir(parents=True, exist_ok=True)

            file_path = config.paths.in_dir / "statement.pdf"
            file_path.write_text(
                "\n".join(
                    [
                        "Estado de cuenta tarjeta",
                        "Emisor: Banco Demo",
                        "Moneda: CLP",
                        "Cuenta: 1234",
                    ]
                ),
                encoding="utf-8",
            )

            processed_count = app.run_once()

            self.assertEqual(processed_count, 1)
            record = repository.get_document(1)
            self.assertEqual(record.current_status, "REVIEW")
            self.assertTrue(Path(record.archive_path).exists())
            self.assertTrue((Path(record.archive_path) / "parse.md").exists())
            self.assertTrue(repository.normalized_documents[1]["review_required"])

            review_files = list(config.paths.review_dir.rglob("statement.pdf"))
            self.assertEqual(len(review_files), 1)

    def test_run_once_rolls_back_partial_repository_writes_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            config = self._build_config(base_dir)
            repository = NoopRepository()
            app = WorkerApp(config, repository, ExplodingParseClient())

            config.paths.in_dir.mkdir(parents=True, exist_ok=True)

            file_path = config.paths.in_dir / "broken.pdf"
            file_path.write_text(
                "\n".join(
                    [
                        "Factura Electronica",
                        "Emisor: Demo",
                        "Fecha Emision: 2026-04-03",
                        "Moneda: CLP",
                        "Monto Total: 9999",
                    ]
                ),
                encoding="utf-8",
            )

            processed_count = app.run_once()

            self.assertEqual(processed_count, 0)
            self.assertEqual(len(repository.documents), 1)
            self.assertEqual(len(repository.parse_attempts), 0)
            self.assertEqual(len(repository.normalized_documents), 0)
            self.assertEqual(len(repository.events), 1)
            self.assertEqual(len(repository.exceptions), 1)

            record = repository.get_document(1)
            self.assertEqual(record.current_status, "ERROR")
            self.assertEqual(repository.events[0]["event_type"], "ERROR")
            exception = repository.exceptions[1]
            self.assertEqual(exception.stage, "PARSING")
            self.assertEqual(exception.severity, "ERROR")
            self.assertEqual(exception.reason_code, "PARSING_FAILED")
            self.assertIn("Synthetic parser failure", exception.reason_detail)

            error_files = list(config.paths.error_dir.rglob("broken.pdf"))
            self.assertEqual(len(error_files), 1)

    def test_run_once_retries_transient_parser_error(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            config = self._build_config(base_dir)
            repository = NoopRepository()
            parser = FlakyParseClient()
            app = WorkerApp(config, repository, parser)

            config.paths.in_dir.mkdir(parents=True, exist_ok=True)
            file_path = config.paths.in_dir / "retry.pdf"
            file_path.write_text(
                "\n".join(
                    [
                        "Factura Electronica",
                        "Emisor: Retry Demo",
                        "Fecha Emision: 2026-04-03",
                        "Moneda: CLP",
                        "Monto Total: 1000",
                    ]
                ),
                encoding="utf-8",
            )

            processed_count = app.run_once()

            self.assertEqual(processed_count, 1)
            self.assertEqual(parser.attempts, 2)
            record = repository.get_document(1)
            self.assertEqual(record.current_status, "PROCESSED")
            retry_events = [event for event in repository.events if event["event_type"] == "PARSING_RETRY"]
            self.assertEqual(len(retry_events), 1)


if __name__ == "__main__":
    unittest.main()
