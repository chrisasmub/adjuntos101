import json
import time
import uuid
from pathlib import Path
from urllib import parse, request

from adjuntos_worker.config import ParseSettings
from adjuntos_worker.models import DocumentClassification, ParseResult


class LlamaParseClient:
    provider_name = "llamaparse"

    def __init__(self, settings: ParseSettings) -> None:
        if not settings.api_key:
            raise ValueError("LLAMAPARSE_API_KEY is required when PARSER_MODE=llamaparse.")
        self.settings = settings

    def parse(self, path: Path, classification: DocumentClassification) -> ParseResult:
        started_at = time.time()
        upload_payload = self._upload(path, classification)
        job_id = self._extract_job_id(upload_payload)
        response_payload = self._poll_until_complete(job_id)

        return ParseResult(
            provider=self.provider_name,
            provider_job_id=job_id,
            provider_tier=classification.provider_tier,
            provider_version=classification.provider_version,
            raw_json=response_payload,
            markdown=self._extract_markdown(response_payload),
            started_at=_unix_to_datetime(started_at),
            completed_at=_unix_to_datetime(time.time()),
            outcome=self._extract_status(response_payload),
        )

    def _upload(self, path: Path, classification: DocumentClassification):
        url = self.settings.base_url.rstrip("/") + "/parse/upload"
        boundary = "----adjuntos101-" + uuid.uuid4().hex

        configuration = json.dumps(
            {
                "tier": classification.provider_tier,
                "version": classification.provider_version,
            }
        )
        file_bytes = path.read_bytes()
        mime_type = "application/octet-stream"

        body = []
        body.append("--{0}\r\n".format(boundary).encode("utf-8"))
        body.append(b'Content-Disposition: form-data; name="configuration"\r\n\r\n')
        body.append(configuration.encode("utf-8"))
        body.append(b"\r\n")
        body.append("--{0}\r\n".format(boundary).encode("utf-8"))
        body.append(
            'Content-Disposition: form-data; name="file"; filename="{0}"\r\n'.format(path.name).encode("utf-8")
        )
        body.append("Content-Type: {0}\r\n\r\n".format(mime_type).encode("utf-8"))
        body.append(file_bytes)
        body.append(b"\r\n")
        body.append("--{0}--\r\n".format(boundary).encode("utf-8"))
        payload = b"".join(body)

        req = request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Authorization": "Bearer {0}".format(self.settings.api_key),
                "Content-Type": "multipart/form-data; boundary={0}".format(boundary),
                "Accept": "application/json",
            },
        )
        return self._read_json(req)

    def _poll_until_complete(self, job_id: str):
        deadline = time.time() + self.settings.timeout_seconds
        while True:
            response_payload = self._get_job(job_id)
            status = self._extract_status(response_payload)
            if status == "COMPLETED":
                return response_payload
            if status in {"FAILED", "CANCELLED"}:
                message = (
                    response_payload.get("job", {}).get("error_message")
                    or response_payload.get("error_message")
                    or "LlamaParse job ended unsuccessfully."
                )
                raise RuntimeError(message)
            if time.time() >= deadline:
                raise TimeoutError(
                    "LlamaParse polling exceeded {0} seconds.".format(self.settings.timeout_seconds)
                )
            time.sleep(self.settings.poll_seconds)

    def _get_job(self, job_id: str):
        url = self.settings.base_url.rstrip("/") + "/parse/{0}?{1}".format(
            parse.quote(job_id),
            parse.urlencode({"expand": "markdown,items"}),
        )
        req = request.Request(
            url,
            method="GET",
            headers={
                "Authorization": "Bearer {0}".format(self.settings.api_key),
                "Accept": "application/json",
            },
        )
        return self._read_json(req)

    def _read_json(self, req: request.Request):
        with request.urlopen(req, timeout=self.settings.timeout_seconds) as response:
            payload = response.read().decode("utf-8")
        return json.loads(payload)

    def _extract_job_id(self, payload) -> str:
        for candidate in (
            payload.get("id"),
            payload.get("job_id"),
            payload.get("job", {}).get("id"),
        ):
            if candidate:
                return str(candidate)
        raise RuntimeError("Could not extract LlamaParse job id from upload response.")

    def _extract_status(self, payload) -> str:
        return str(
            payload.get("job", {}).get("status")
            or payload.get("status")
            or "UNKNOWN"
        ).upper()

    def _extract_markdown(self, payload) -> str:
        if "markdown" in payload and payload["markdown"]:
            return str(payload["markdown"])
        job = payload.get("job", {})
        if "markdown" in job and job["markdown"]:
            return str(job["markdown"])
        return ""


def _unix_to_datetime(value: float):
    from datetime import datetime

    return datetime.utcfromtimestamp(value)
