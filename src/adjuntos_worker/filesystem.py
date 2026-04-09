import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from shutil import copy2, move
from typing import Optional

from adjuntos_worker.models import ClaimedFile, FileFingerprint


def ensure_runtime_directories(paths) -> None:
    required = [
        paths.base_dir,
        paths.in_dir,
        paths.processing_dir,
        paths.processed_dir,
        paths.review_dir,
        paths.error_dir,
        paths.archive_dir,
        paths.duplicates_dir,
    ]
    for directory in required:
        directory.mkdir(parents=True, exist_ok=True)


def _dated_destination(root: Path, claimed_file: ClaimedFile, slug: str, filename: str) -> Path:
    return (
        root
        / claimed_file.claimed_at.strftime("%Y")
        / claimed_file.claimed_at.strftime("%m")
        / claimed_file.claimed_at.strftime("%d")
        / slug
        / filename
    )


def relocate_claimed_file(
    claimed_file: ClaimedFile,
    destination_root: Path,
    slug: str,
    filename: Optional[str] = None,
) -> Path:
    destination = _dated_destination(
        destination_root,
        claimed_file,
        slug=slug,
        filename=filename or claimed_file.original_filename,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    move(str(claimed_file.claimed_path), str(destination))
    _cleanup_claim_directory(claimed_file.claimed_path.parent)
    return destination


def finalize_success(claimed_file: ClaimedFile, fingerprint: FileFingerprint, processed_dir: Path) -> Path:
    return relocate_claimed_file(claimed_file, processed_dir, slug=fingerprint.sha256)


def finalize_review(claimed_file: ClaimedFile, fingerprint: FileFingerprint, review_dir: Path) -> Path:
    return relocate_claimed_file(claimed_file, review_dir, slug=fingerprint.sha256)


def finalize_duplicate(claimed_file: ClaimedFile, fingerprint: FileFingerprint, duplicates_dir: Path) -> Path:
    return relocate_claimed_file(claimed_file, duplicates_dir, slug=fingerprint.sha256)


def finalize_error(claimed_file: ClaimedFile, error_dir: Path) -> Path:
    return relocate_claimed_file(claimed_file, error_dir, slug=claimed_file.claim_id)


def create_archive_bundle(
    claimed_file: ClaimedFile,
    fingerprint: FileFingerprint,
    archive_dir: Path,
    parse_result,
    normalized_document,
) -> Path:
    bundle_dir = (
        archive_dir
        / claimed_file.claimed_at.strftime("%Y")
        / claimed_file.claimed_at.strftime("%m")
        / claimed_file.claimed_at.strftime("%d")
        / fingerprint.sha256
    )
    bundle_dir.mkdir(parents=True, exist_ok=True)

    original_path = bundle_dir / ("original" + claimed_file.claimed_path.suffix.lower())
    copy2(claimed_file.claimed_path, original_path)

    _write_json(bundle_dir / "parse_raw.json", parse_result.raw_json)
    (bundle_dir / "parse.md").write_text(parse_result.markdown, encoding="utf-8")
    _write_json(bundle_dir / "normalized.json", normalized_document)

    return bundle_dir


def _write_json(path: Path, payload) -> None:
    serializable = payload
    if hasattr(payload, "to_dict"):
        serializable = payload.to_dict()
    elif is_dataclass(payload):
        serializable = asdict(payload)

    path.write_text(
        json.dumps(serializable, indent=2, ensure_ascii=True, default=str),
        encoding="utf-8",
    )


def _cleanup_claim_directory(path: Path) -> None:
    current = path
    while current.name != "Processing":
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent
