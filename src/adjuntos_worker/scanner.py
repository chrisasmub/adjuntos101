import time
from pathlib import Path
from typing import Iterable, List


def scan_candidates(in_dir: Path, allowed_extensions: List[str]) -> Iterable[Path]:
    allowed = {ext.lower().lstrip(".") for ext in allowed_extensions}
    files = []
    for candidate in in_dir.iterdir():
        if not candidate.is_file():
            continue
        if candidate.suffix.lower().lstrip(".") not in allowed:
            continue
        files.append(candidate)

    return sorted(files, key=lambda item: (item.stat().st_mtime, item.name))


def is_file_stable(path: Path, min_file_age_seconds: int, stable_check_interval_seconds: int) -> bool:
    if not path.exists():
        return False

    first_stat = path.stat()
    file_age_seconds = time.time() - first_stat.st_mtime
    if file_age_seconds < min_file_age_seconds:
        return False

    if stable_check_interval_seconds > 0:
        time.sleep(stable_check_interval_seconds)

    if not path.exists():
        return False

    second_stat = path.stat()
    return (
        first_stat.st_size == second_stat.st_size
        and first_stat.st_mtime_ns == second_stat.st_mtime_ns
    )

