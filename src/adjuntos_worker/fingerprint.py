import hashlib
import mimetypes
from datetime import datetime
from pathlib import Path

from adjuntos_worker.models import FileFingerprint


def fingerprint_file(path: Path) -> FileFingerprint:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    stat = path.stat()

    return FileFingerprint(
        sha256=digest.hexdigest(),
        file_size_bytes=stat.st_size,
        mime_type=mime_type,
        original_filename=path.name,
        detected_at=datetime.utcnow(),
    )

