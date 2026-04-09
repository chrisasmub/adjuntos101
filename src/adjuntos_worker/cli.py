import argparse

from adjuntos_worker.config import load_config
from adjuntos_worker.logging_utils import configure_logging
from adjuntos_worker.orchestrator import WorkerApp
from adjuntos_worker.parse_clients import LlamaParseClient, MockParseClient
from adjuntos_worker.repositories import IrisRepository, NoopRepository


def _build_repository(config):
    if config.database.mode == "noop":
        return NoopRepository()
    if config.database.mode == "iris":
        return IrisRepository.from_settings(config.database)
    raise ValueError("Unsupported DATABASE_MODE: {0}".format(config.database.mode))


def _build_parser(config):
    if config.parse.mode == "mock":
        return MockParseClient()
    if config.parse.mode == "llamaparse":
        return LlamaParseClient(config.parse)
    raise ValueError("Unsupported PARSER_MODE: {0}".format(config.parse.mode))


def main() -> int:
    parser = argparse.ArgumentParser(description="Adjuntos101 Sprint 1 worker")
    parser.add_argument("--env-file", default=".env", help="Path to .env file")
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Process one scan cycle and exit",
    )
    args = parser.parse_args()

    config = load_config(args.env_file)
    configure_logging(config.logging.level)
    repository = _build_repository(config)
    parser = _build_parser(config)
    app = WorkerApp(config, repository, parser)

    try:
        if args.run_once:
            app.run_once()
            return 0
        app.run_forever()
        return 0
    finally:
        app.close()
