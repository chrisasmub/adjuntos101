#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import iris

from adjuntos_worker.config import load_config


def _write_sample_document(in_dir: Path) -> str:
    token = uuid.uuid4().hex[:8]
    filename = "smoke-{0}.pdf".format(token)
    file_path = in_dir / filename
    file_path.write_text(
        "\n".join(
            [
                "Factura Electronica",
                "Emisor: ACME SpA",
                "Fecha Emision: 2026-04-09",
                "Moneda: CLP",
                "Monto Total: 12345",
                "Numero Documento: F-{0}".format(token.upper()),
            ]
        ),
        encoding="utf-8",
    )
    return filename


def _query_document_summary(config, filename: str) -> dict:
    connection = iris.connect(config.database.dsn, config.database.username, config.database.password)
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT TOP 1 document_id, current_status, archive_path
              FROM doc_document
             WHERE original_filename = ?
             ORDER BY document_id DESC
            """,
            (filename,),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("No document row found for filename {0}".format(filename))

        document_id = int(row[0])
        current_status = str(row[1])
        archive_path = None if row[2] is None else str(row[2])

        cursor.execute(
            "SELECT COUNT(*) FROM doc_event WHERE document_id = ?",
            (document_id,),
        )
        event_count = int(cursor.fetchone()[0])

        cursor.execute(
            """
            SELECT TOP 1 provider, outcome
              FROM doc_parse_attempt
             WHERE document_id = ?
             ORDER BY parse_attempt_id DESC
            """,
            (document_id,),
        )
        parse_row = cursor.fetchone()
        parse_provider = None if parse_row is None else str(parse_row[0])
        parse_outcome = None if parse_row is None else str(parse_row[1])

        cursor.execute(
            """
            SELECT TOP 1 document_type, review_required
              FROM doc_normalized
             WHERE document_id = ?
            """,
            (document_id,),
        )
        normalized_row = cursor.fetchone()
        document_type = None if normalized_row is None else str(normalized_row[0])
        review_required = None if normalized_row is None else bool(normalized_row[1])

        return {
            "document_id": document_id,
            "current_status": current_status,
            "archive_path": archive_path,
            "event_count": event_count,
            "parse_provider": parse_provider,
            "parse_outcome": parse_outcome,
            "document_type": document_type,
            "review_required": review_required,
        }
    finally:
        cursor.close()
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ejecuta una corrida controlada del worker contra IRIS real usando PARSER_MODE=mock."
    )
    parser.add_argument("--env-file", default=".env", help="Ruta del archivo .env")
    parser.add_argument(
        "--base-dir",
        help="Runtime base temporal. Si no se informa, se crea un directorio nuevo en /tmp",
    )
    args = parser.parse_args()

    config = load_config(args.env_file)
    base_dir = Path(args.base_dir) if args.base_dir else Path(tempfile.mkdtemp(prefix="adjuntos101-iris-smoke-"))
    in_dir = base_dir / "In"
    in_dir.mkdir(parents=True, exist_ok=True)
    filename = _write_sample_document(in_dir)

    env = os.environ.copy()
    env["ADJUNTOS_BASE_DIR"] = str(base_dir)
    env["DATABASE_MODE"] = "iris"
    env["PARSER_MODE"] = "mock"
    env["MIN_FILE_AGE_SECONDS"] = "0"
    env["STABLE_CHECK_INTERVAL_SECONDS"] = "0"
    env["PYTHONPATH"] = str(Path("src").resolve())

    subprocess.run(
        [sys.executable, "-m", "adjuntos_worker", "--env-file", args.env_file, "--run-once"],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env=env,
    )

    summary = _query_document_summary(config, filename)
    print("smoke_runtime={0}".format(base_dir))
    print("smoke_file={0}".format(filename))
    print("document_id={0}".format(summary["document_id"]))
    print("current_status={0}".format(summary["current_status"]))
    print("parse_provider={0}".format(summary["parse_provider"]))
    print("parse_outcome={0}".format(summary["parse_outcome"]))
    print("document_type={0}".format(summary["document_type"]))
    print("review_required={0}".format(summary["review_required"]))
    print("event_count={0}".format(summary["event_count"]))
    print("archive_path={0}".format(summary["archive_path"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
