import uuid
from datetime import datetime
from pathlib import Path

from adjuntos_worker.models import DocumentClassification, ParseResult


class MockParseClient:
    provider_name = "mock"

    def parse(self, path: Path, classification: DocumentClassification) -> ParseResult:
        started_at = datetime.utcnow()
        content = path.read_bytes().decode("utf-8", errors="ignore")
        markdown = content if content.strip() else "Filename: {0}".format(path.name)
        raw_json = {
            "job": {"id": str(uuid.uuid4()), "status": "COMPLETED"},
            "markdown": markdown,
            "items": [],
            "metadata": {"filename": path.name},
        }
        completed_at = datetime.utcnow()
        return ParseResult(
            provider=self.provider_name,
            provider_job_id=raw_json["job"]["id"],
            provider_tier=classification.provider_tier,
            provider_version=classification.provider_version,
            raw_json=raw_json,
            markdown=markdown,
            started_at=started_at,
            completed_at=completed_at,
            outcome="COMPLETED",
        )
