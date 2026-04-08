from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class FileFingerprint:
    sha256: str
    file_size_bytes: int
    mime_type: str
    original_filename: str
    detected_at: datetime


@dataclass(frozen=True)
class ClaimedFile:
    claim_id: str
    original_path: Path
    claimed_path: Path
    original_filename: str
    claimed_at: datetime


@dataclass(frozen=True)
class DocumentRecord:
    document_id: int
    attachment_hash: str
    original_filename: str
    source_path: str
    archive_path: Optional[str]
    mime_type: str
    file_size_bytes: int
    received_at: datetime
    current_status: str

