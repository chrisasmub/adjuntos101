from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


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


@dataclass(frozen=True)
class DocumentClassification:
    document_type: str
    provider_tier: str
    provider_version: str
    rationale: str


@dataclass(frozen=True)
class ParseResult:
    provider: str
    provider_job_id: str
    provider_tier: str
    provider_version: str
    raw_json: Dict[str, Any]
    markdown: str
    started_at: datetime
    completed_at: datetime
    outcome: str


@dataclass(frozen=True)
class ParseAttemptRecord:
    parse_attempt_id: int
    document_id: int
    provider: str
    provider_job_id: str
    provider_tier: str
    provider_version: str
    outcome: str
    raw_json_path: Optional[str]
    raw_markdown_path: Optional[str]


@dataclass(frozen=True)
class NormalizedDocument:
    document_type: str
    issuer_name: str
    issuer_tax_id: str
    issue_date: Optional[date]
    due_date: Optional[date]
    period_from: Optional[date]
    period_to: Optional[date]
    currency: str
    total_amount: Optional[float]
    balance_amount: Optional[float]
    account_ref_last4: str
    document_number: str
    confidence: float
    review_required: bool
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_type": self.document_type,
            "issuer_name": self.issuer_name,
            "issuer_tax_id": self.issuer_tax_id,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "period_from": self.period_from.isoformat() if self.period_from else None,
            "period_to": self.period_to.isoformat() if self.period_to else None,
            "currency": self.currency,
            "total_amount": self.total_amount,
            "balance_amount": self.balance_amount,
            "account_ref_last4": self.account_ref_last4,
            "document_number": self.document_number,
            "confidence": self.confidence,
            "review_required": self.review_required,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ValidationResult:
    requires_review: bool
    missing_fields: List[str]
    notes: str
