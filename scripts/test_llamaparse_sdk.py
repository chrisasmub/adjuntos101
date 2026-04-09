import argparse
import asyncio
import os
from pathlib import Path


async def _run(file_path: Path, tier: str, version: str, output_file: Path = None) -> int:
    try:
        from llama_cloud import AsyncLlamaCloud
    except ImportError as exc:
        raise RuntimeError(
            "The llama-cloud package is required. Install it with: python3 -m pip install -e '.[llamacloud]'"
        ) from exc

    api_key = os.environ.get("LLAMA_CLOUD_API_KEY") or os.environ.get("LLAMAPARSE_API_KEY")
    if not api_key:
        raise RuntimeError("Set LLAMA_CLOUD_API_KEY or LLAMAPARSE_API_KEY before running the test.")

    if not file_path.exists():
        raise FileNotFoundError("File not found: {0}".format(file_path))

    client = AsyncLlamaCloud(api_key=api_key)

    file_obj = await client.files.create(file=str(file_path), purpose="parse")
    result = await client.parsing.parse(
        file_id=file_obj.id,
        tier=tier,
        version=version,
        expand=["markdown_full"],
    )

    markdown = getattr(result, "markdown_full", None) or getattr(result, "markdown", "")
    job_id = getattr(result, "id", None) or getattr(result, "job_id", None)

    print("file_id={0}".format(file_obj.id))
    print("parse_job_id={0}".format(job_id))
    print("tier={0}".format(tier))
    print("version={0}".format(version))

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
    parser.add_argument("--tier", default="agentic", help="Tier de parse")
    parser.add_argument("--version", default="latest", help="Version del tier")
    parser.add_argument(
        "--output-file",
        help="Ruta opcional para guardar markdown_full en disco",
    )
    args = parser.parse_args()

    output_file = None if not args.output_file else Path(args.output_file)
    return asyncio.run(
        _run(
            file_path=Path(args.file).expanduser().resolve(),
            tier=args.tier,
            version=args.version,
            output_file=output_file,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())

