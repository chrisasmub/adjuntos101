import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adjuntos_worker.webapp import _parse_limit, _status_class


class WebAppTests(unittest.TestCase):
    def test_parse_limit_bounds_value(self):
        self.assertEqual(_parse_limit("500"), 200)
        self.assertEqual(_parse_limit("0"), 1)
        self.assertEqual(_parse_limit("12"), 12)
        self.assertEqual(_parse_limit("oops"), 50)

    def test_status_class_maps_known_states(self):
        self.assertEqual(_status_class("PROCESSED"), "ok")
        self.assertEqual(_status_class("REVIEW"), "warn")
        self.assertEqual(_status_class("ERROR"), "err")
        self.assertEqual(_status_class("DUPLICATE"), "dup")
        self.assertEqual(_status_class("OTHER"), "neutral")


if __name__ == "__main__":
    unittest.main()
