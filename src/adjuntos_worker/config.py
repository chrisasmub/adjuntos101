import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


def _parse_dotenv(path: Path) -> Dict[str, str]:
    values = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = _normalize_env_value(value.strip())
    return values


def _normalize_env_value(value: str) -> str:
    if value == "":
        return ""

    try:
        tokens = shlex.split(value, posix=True)
    except ValueError:
        return value.strip().strip("\"'")

    if not tokens:
        return ""
    if len(tokens) == 1:
        return tokens[0]
    return " ".join(tokens)


def _get(env: Dict[str, str], key: str, default: Optional[str] = None) -> str:
    if key in os.environ:
        return os.environ[key]
    if key in env:
        return env[key]
    if default is None:
        raise ValueError("Missing required setting: {0}".format(key))
    return default


def _get_int(env: Dict[str, str], key: str, default: int) -> int:
    return int(_get(env, key, str(default)))


def _get_extensions(env: Dict[str, str], key: str, default: str) -> List[str]:
    raw = _get(env, key, default)
    return [item.strip().lower().lstrip(".") for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class PathSettings:
    base_dir: Path
    in_dir: Path
    processing_dir: Path
    processed_dir: Path
    review_dir: Path
    error_dir: Path
    archive_dir: Path
    duplicates_dir: Path


@dataclass(frozen=True)
class WorkerSettings:
    scan_interval_seconds: int
    min_file_age_seconds: int
    stable_check_interval_seconds: int
    allowed_extensions: List[str]


@dataclass(frozen=True)
class DatabaseSettings:
    mode: str
    host: str
    port: int
    namespace: str
    username: str
    password: str

    @property
    def dsn(self) -> str:
        return "{0}:{1}/{2}".format(self.host, self.port, self.namespace)


@dataclass(frozen=True)
class ParseSettings:
    mode: str
    api_key: str
    base_url: str
    default_tier: str
    complex_tier: str
    version: str
    poll_seconds: int
    timeout_seconds: int
    max_retries: int = 2
    retry_backoff_seconds: int = 2


@dataclass(frozen=True)
class LoggingSettings:
    level: str


@dataclass(frozen=True)
class AppConfig:
    paths: PathSettings
    worker: WorkerSettings
    database: DatabaseSettings
    parse: ParseSettings
    logging: LoggingSettings


def load_config(env_file: str = ".env") -> AppConfig:
    env_values = _parse_dotenv(Path(env_file))

    base_dir = Path(_get(env_values, "ADJUNTOS_BASE_DIR", str(Path.cwd() / "runtime"))).expanduser()

    path_settings = PathSettings(
        base_dir=base_dir,
        in_dir=base_dir / "In",
        processing_dir=base_dir / "Processing",
        processed_dir=base_dir / "Processed",
        review_dir=base_dir / "Review",
        error_dir=base_dir / "Error",
        archive_dir=base_dir / "Archive",
        duplicates_dir=base_dir / "Processed" / "Duplicates",
    )

    worker_settings = WorkerSettings(
        scan_interval_seconds=_get_int(env_values, "SCAN_INTERVAL_SECONDS", 30),
        min_file_age_seconds=_get_int(env_values, "MIN_FILE_AGE_SECONDS", 90),
        stable_check_interval_seconds=_get_int(env_values, "STABLE_CHECK_INTERVAL_SECONDS", 5),
        allowed_extensions=_get_extensions(env_values, "ALLOWED_EXTENSIONS", "pdf,png,jpg,jpeg,xlsx,xls"),
    )

    database_settings = DatabaseSettings(
        mode=_get(env_values, "DATABASE_MODE", "iris").lower(),
        host=_get(env_values, "IRIS_HOST", "localhost"),
        port=_get_int(env_values, "IRIS_PORT", 1972),
        namespace=_get(env_values, "IRIS_NAMESPACE", "DOCSPOC"),
        username=_get(env_values, "IRIS_USERNAME", "USER"),
        password=_get(env_values, "IRIS_PASSWORD", ""),
    )

    parse_settings = ParseSettings(
        mode=_get(env_values, "PARSER_MODE", "mock").lower(),
        api_key=_get(env_values, "LLAMAPARSE_API_KEY", ""),
        base_url=_get(env_values, "LLAMAPARSE_BASE_URL", "https://api.cloud.llamaindex.ai/api/v2"),
        default_tier=_get(env_values, "LLAMAPARSE_DEFAULT_TIER", "cost_effective"),
        complex_tier=_get(env_values, "LLAMAPARSE_COMPLEX_TIER", "agentic"),
        version=_get(env_values, "LLAMAPARSE_VERSION", "latest"),
        poll_seconds=_get_int(env_values, "LLAMAPARSE_POLL_SECONDS", 5),
        timeout_seconds=_get_int(env_values, "LLAMAPARSE_TIMEOUT_SECONDS", 300),
        max_retries=_get_int(env_values, "LLAMAPARSE_MAX_RETRIES", 2),
        retry_backoff_seconds=_get_int(env_values, "LLAMAPARSE_RETRY_BACKOFF_SECONDS", 2),
    )

    logging_settings = LoggingSettings(level=_get(env_values, "LOG_LEVEL", "INFO").upper())

    return AppConfig(
        paths=path_settings,
        worker=worker_settings,
        database=database_settings,
        parse=parse_settings,
        logging=logging_settings,
    )
