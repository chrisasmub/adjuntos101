import asyncio
from pathlib import Path

from adjuntos_worker.config import ParseSettings
from adjuntos_worker.models import DocumentClassification, ParseResult


class LlamaParseClient:
    provider_name = "llamaparse"

    def __init__(self, settings: ParseSettings, client_factory=None) -> None:
        if not settings.api_key:
            raise ValueError("LLAMAPARSE_API_KEY is required when PARSER_MODE=llamaparse.")
        self.settings = settings
        self._client_factory = client_factory

    def parse(self, path: Path, classification: DocumentClassification) -> ParseResult:
        return asyncio.run(self._parse_async(path, classification))

    async def _parse_async(
        self, path: Path, classification: DocumentClassification
    ) -> ParseResult:
        client = self._build_client()
        file_obj = await client.files.create(file=str(path), purpose="parse")
        response = await client.parsing.parse(
            file_id=file_obj.id,
            tier=classification.provider_tier,
            version=classification.provider_version,
            expand=["markdown_full", "items"],
            polling_interval=float(self.settings.poll_seconds),
            max_interval=float(self.settings.poll_seconds),
            timeout=float(self.settings.timeout_seconds),
            verbose=False,
        )

        return ParseResult(
            provider=self.provider_name,
            provider_job_id=str(response.job.id),
            provider_tier=classification.provider_tier,
            provider_version=classification.provider_version,
            raw_json=self._to_dict(response),
            markdown=self._extract_markdown(response),
            started_at=response.job.created_at or response.job.updated_at,
            completed_at=response.job.updated_at or response.job.created_at,
            outcome=str(response.job.status).upper(),
        )

    def _build_client(self):
        if self._client_factory is not None:
            return self._client_factory()

        try:
            from llama_cloud import AsyncLlamaCloud
        except ImportError as exc:
            raise RuntimeError(
                "The llama-cloud package is required when PARSER_MODE=llamaparse. Install it with: python3 -m pip install '.[llamacloud]'"
            ) from exc

        return AsyncLlamaCloud(
            api_key=self.settings.api_key,
            base_url=self._normalize_base_url(self.settings.base_url),
            timeout=float(self.settings.timeout_seconds),
        )

    def _extract_markdown(self, response) -> str:
        if getattr(response, "markdown_full", None):
            return str(response.markdown_full)

        markdown = getattr(response, "markdown", None)
        if markdown and getattr(markdown, "pages", None):
            pages = []
            for page in markdown.pages:
                if getattr(page, "success", False) and getattr(page, "markdown", None):
                    pages.append(str(page.markdown))
            return "\n\n".join(pages)

        text_full = getattr(response, "text_full", None)
        if text_full:
            return str(text_full)

        return ""

    def _to_dict(self, response) -> dict:
        if hasattr(response, "model_dump"):
            return response.model_dump(mode="json")
        if hasattr(response, "dict"):
            return response.dict()
        raise RuntimeError("Unsupported LlamaParse response object.")

    def _normalize_base_url(self, value: str) -> str:
        normalized = value.rstrip("/")
        if normalized.endswith("/api/v2"):
            return normalized[: -len("/api/v2")]
        return normalized
