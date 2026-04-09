import sys
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adjuntos_worker.config import ParseSettings
from adjuntos_worker.models import DocumentClassification
from adjuntos_worker.parse_clients.llamaparse import LlamaParseClient


class _FakeFileObject:
    def __init__(self, file_id: str) -> None:
        self.id = file_id


class _FakeJob:
    def __init__(self) -> None:
        self.id = "pjb-test-123"
        self.status = "COMPLETED"
        self.created_at = datetime(2026, 4, 8, 12, 0, 0)
        self.updated_at = datetime(2026, 4, 8, 12, 0, 5)


class _FakeResponse:
    def __init__(self) -> None:
        self.job = _FakeJob()
        self.markdown_full = "# Test\n\nParsed document"
        self.items = {"pages": []}

    def model_dump(self, mode="json"):
        return {
            "job": {
                "id": self.job.id,
                "status": self.job.status,
                "created_at": self.job.created_at.isoformat(),
                "updated_at": self.job.updated_at.isoformat(),
            },
            "markdown_full": self.markdown_full,
            "items": self.items,
        }


class _FakeFilesResource:
    async def create(self, file: str, purpose: str):
        return _FakeFileObject("file-123")


class _FakeParsingResource:
    async def parse(self, **kwargs):
        return _FakeResponse()


class _FakeAsyncClient:
    def __init__(self) -> None:
        self.files = _FakeFilesResource()
        self.parsing = _FakeParsingResource()


class LlamaParseClientTests(unittest.TestCase):
    def test_normalize_legacy_api_v2_base_url(self):
        settings = ParseSettings(
            mode="llamaparse",
            api_key="test-key",
            base_url="https://api.cloud.llamaindex.ai/api/v2",
            default_tier="cost_effective",
            complex_tier="agentic",
            version="latest",
            poll_seconds=2,
            timeout_seconds=60,
        )
        client = LlamaParseClient(settings, client_factory=_FakeAsyncClient)

        self.assertEqual(
            client._normalize_base_url(settings.base_url),
            "https://api.cloud.llamaindex.ai",
        )

    def test_parse_uses_sdk_response_shape(self):
        settings = ParseSettings(
            mode="llamaparse",
            api_key="test-key",
            base_url="https://api.cloud.llamaindex.ai/api/v2",
            default_tier="cost_effective",
            complex_tier="agentic",
            version="latest",
            poll_seconds=2,
            timeout_seconds=60,
        )
        client = LlamaParseClient(settings, client_factory=_FakeAsyncClient)
        classification = DocumentClassification(
            document_type="invoice",
            provider_tier="agentic",
            provider_version="latest",
            rationale="test",
        )

        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sample.pdf"
            path.write_bytes(b"test")

            result = client.parse(path, classification)

        self.assertEqual(result.provider, "llamaparse")
        self.assertEqual(result.provider_job_id, "pjb-test-123")
        self.assertEqual(result.outcome, "COMPLETED")
        self.assertEqual(result.markdown, "# Test\n\nParsed document")
        self.assertEqual(result.raw_json["job"]["id"], "pjb-test-123")


if __name__ == "__main__":
    unittest.main()
