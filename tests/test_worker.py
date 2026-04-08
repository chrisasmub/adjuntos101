import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adjuntos_worker.config import AppConfig, DatabaseSettings, LoggingSettings, PathSettings, WorkerSettings
from adjuntos_worker.orchestrator import WorkerApp
from adjuntos_worker.repositories.noop import NoopRepository


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
        logging = LoggingSettings(level="INFO")
        return AppConfig(paths=paths, worker=worker, database=database, logging=logging)

    def test_run_once_processes_file_and_updates_repository(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            config = self._build_config(base_dir)
            repository = NoopRepository()
            app = WorkerApp(config, repository)

            config.paths.in_dir.mkdir(parents=True, exist_ok=True)
            file_path = config.paths.in_dir / "sample.pdf"
            file_path.write_bytes(b"content-1")

            processed_count = app.run_once()

            self.assertEqual(processed_count, 1)
            self.assertEqual(len(repository.documents), 1)

            record = repository.get_document(1)
            self.assertEqual(record.current_status, "PROCESSED")
            self.assertTrue(Path(record.archive_path).exists())
            self.assertIn("Processed", record.archive_path)

    def test_run_once_routes_duplicate_to_duplicates_folder(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            config = self._build_config(base_dir)
            repository = NoopRepository()
            app = WorkerApp(config, repository)

            config.paths.in_dir.mkdir(parents=True, exist_ok=True)

            first_file = config.paths.in_dir / "first.pdf"
            first_file.write_bytes(b"same-content")
            app.run_once()

            second_file = config.paths.in_dir / "second.pdf"
            second_file.write_bytes(b"same-content")
            processed_count = app.run_once()

            self.assertEqual(processed_count, 1)
            self.assertEqual(len(repository.documents), 1)

            duplicates = list(config.paths.duplicates_dir.rglob("second.pdf"))
            self.assertEqual(len(duplicates), 1)


if __name__ == "__main__":
    unittest.main()

