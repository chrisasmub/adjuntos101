import argparse
import asyncio
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adjuntos_worker.config import load_config


async def _run(file_path: Path, env_file: str, tier: str = None, version: str = None, output_file: Path = None) -> int:
    try:
        from llama_cloud import AsyncLlamaCloud
    except ImportError as exc:
        raise RuntimeError(
            "The llama-cloud package is required. Install it with: python3 -m pip install -e '.[llamacloud]'"
        ) from exc

    config = load_config(env_file)

    api_key = (
        os.environ.get("LLAMA_CLOUD_API_KEY")
        or os.environ.get("LLAMAPARSE_API_KEY")
        or config.parse.api_key
    )
    if not api_key:
        raise RuntimeError("Set LLAMA_CLOUD_API_KEY or LLAMAPARSE_API_KEY before running the test.")

    if not file_path.exists():
        raise FileNotFoundError("File not found: {0}".format(file_path))

    client = AsyncLlamaCloud(api_key=api_key)
    effective_tier = tier or config.parse.complex_tier
    effective_version = version or config.parse.version

    file_obj = await client.files.create(file=str(file_path), purpose="parse")
    result = await client.parsing.parse(
        file_id=file_obj.id,
        tier=effective_tier,
        version=effective_version,
        expand=["markdown_full"],
    )

    markdown = getattr(result, "markdown_full", None) or getattr(result, "markdown", "")
    job_id = (
        getattr(result, "id", None)
        or getattr(result, "job_id", None)
        or getattr(getattr(result, "job", None), "id", None)
    )

    print("file_id={0}".format(file_obj.id))
    print("parse_job_id={0}".format(job_id))
    print("tier={0}".format(effective_tier))
    print("version={0}".format(effective_version))
    print("env_file={0}".format(Path(env_file).resolve()))

    if output_file is not None:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(markdown or "", encoding="utf-8")
        print("markdown_saved_to={0}".format(output_file))
    else:
        print("--- markdown ---")
        print(markdown or "")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba de integracion LlamaParse usando AsyncLlamaCloud.")
    parser.add_argument("file", help="Archivo local a subir para parse")
    parser.add_argument("--env-file", default=".env", help="Ruta del archivo .env")
    parser.add_argument("--tier", help="Tier de parse. Si no se informa, usa .env")
    parser.add_argument("--version", help="Version del tier. Si no se informa, usa .env")
    parser.add_argument(
        "--output-file",
        help="Ruta opcional para guardar markdown_full en disco",
    )
    args = parser.parse_args()

    output_file = None if not args.output_file else Path(args.output_file)
    return asyncio.run(
        _run(
            file_path=Path(args.file).expanduser().resolve(),
            env_file=args.env_file,
            tier=args.tier,
            version=args.version,
            output_file=output_file,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
