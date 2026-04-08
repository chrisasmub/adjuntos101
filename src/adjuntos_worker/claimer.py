import uuid
from datetime import datetime
from pathlib import Path

from adjuntos_worker.models import ClaimedFile


def claim_file(path: Path, processing_dir: Path) -> ClaimedFile:
    claim_id = str(uuid.uuid4())
    destination_dir = processing_dir / claim_id
    destination_dir.mkdir(parents=True, exist_ok=False)
    destination = destination_dir / path.name
    path.rename(destination)

    return ClaimedFile(
        claim_id=claim_id,
        original_path=path,
        claimed_path=destination,
        original_filename=path.name,
        claimed_at=datetime.utcnow(),
    )

