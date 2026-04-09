#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adjuntos_worker.config import load_config


TABLE_NAMES = [
    "doc_document",
    "doc_parse_attempt",
    "doc_normalized",
    "doc_exception",
    "doc_event",
]


def _split_sql_statements(sql_text: str) -> list[str]:
    return [" ".join(line.strip() for line in chunk.splitlines()) for chunk in sql_text.split(";") if chunk.strip()]


def _run_sql_statement(container: str, instance: str, statement: str) -> tuple[str, str]:
    process = subprocess.run(
        ["docker", "exec", "-i", container, "iris", "sql", instance],
        input=statement + "\n",
        text=True,
        capture_output=True,
    )
    output = process.stdout + process.stderr

    if "[SQLCODE:" not in output:
        return "ok", output

    lowered = output.lower()
    if (
        "already exists" in lowered
        or "name not unique" in lowered
        or "already has index named" in lowered
        or "index with this name already defined" in lowered
    ):
        return "skipped", output

    return "error", output


def _build_grant_statements(username: str) -> list[str]:
    return [
        "GRANT SELECT, INSERT, UPDATE, DELETE ON {0} TO {1}".format(table_name, username)
        for table_name in TABLE_NAMES
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aplica el esquema SQL de la POC en IRIS USER y concede permisos DML al usuario configurado."
    )
    parser.add_argument("--env-file", default=".env", help="Ruta del archivo .env")
    parser.add_argument("--container", default="iris105", help="Nombre del contenedor Docker de IRIS")
    parser.add_argument("--instance", default="IRIS", help="Nombre de la instancia IRIS dentro del contenedor")
    parser.add_argument("--sql-file", default="sql/001_init.sql", help="Archivo SQL a aplicar")
    parser.add_argument(
        "--grant-user",
        help="Usuario al que se le conceden permisos DML. Si no se informa, usa IRIS_USERNAME del .env",
    )
    args = parser.parse_args()

    config = load_config(args.env_file)
    sql_path = Path(args.sql_file)
    if not sql_path.exists():
        raise FileNotFoundError("SQL file not found: {0}".format(sql_path))

    schema_statements = _split_sql_statements(sql_path.read_text(encoding="utf-8"))
    grant_user = args.grant_user or config.database.username
    all_statements = schema_statements + _build_grant_statements(grant_user)

    print("bootstrap_target_container={0}".format(args.container))
    print("bootstrap_target_instance={0}".format(args.instance))
    print("bootstrap_target_namespace={0}".format(config.database.namespace))
    print("bootstrap_grant_user={0}".format(grant_user))

    if config.database.namespace.upper() != "USER":
        print(
            "warning=Este script usa el shell SQL del contenedor, que en este proyecto se ejecuta sobre USER. "
            "La configuracion actual no apunta a USER."
        )

    error_count = 0
    for index, statement in enumerate(all_statements, start=1):
        status, output = _run_sql_statement(args.container, args.instance, statement)
        first_line = statement[:120]
        print("step={0:02d} status={1} sql={2}".format(index, status.upper(), first_line))
        if status == "error":
            error_count += 1
            print("step={0:02d} output_begin".format(index))
            print(output.strip())
            print("step={0:02d} output_end".format(index))

    print("bootstrap_error_count={0}".format(error_count))
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
