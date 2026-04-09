import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adjuntos_worker.config import load_config


class ConfigTests(unittest.TestCase):
    def test_load_config_reads_escaped_spaces_from_env_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        r"ADJUNTOS_BASE_DIR=/Users/test/Library/CloudStorage/My\ Drive/ADJUNTOS",
                        "DATABASE_MODE=noop",
                        "PARSER_MODE=mock",
                        "LLAMAPARSE_COMPLEX_TIER=agentic",
                        "LLAMAPARSE_VERSION=latest",
                    ]
                ),
                encoding="utf-8",
            )

            config = load_config(str(env_path))

            self.assertEqual(
                str(config.paths.base_dir),
                "/Users/test/Library/CloudStorage/My Drive/ADJUNTOS",
            )


if __name__ == "__main__":
    unittest.main()
