import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adjuntos_worker.fingerprint import fingerprint_file


class FingerprintTests(unittest.TestCase):
    def test_fingerprint_file_returns_expected_hash_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "invoice.pdf"
            file_path.write_bytes(b"hello-world")

            fingerprint = fingerprint_file(file_path)

            self.assertEqual(fingerprint.sha256, hashlib.sha256(b"hello-world").hexdigest())
            self.assertEqual(fingerprint.file_size_bytes, 11)
            self.assertEqual(fingerprint.original_filename, "invoice.pdf")
            self.assertEqual(fingerprint.mime_type, "application/pdf")


if __name__ == "__main__":
    unittest.main()
