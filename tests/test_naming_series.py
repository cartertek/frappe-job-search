import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class NamingSeriesTest(unittest.TestCase):
    def test_autoname_series_are_valid(self):
        paths = list((ROOT / "job_search/job_search/doctype").glob("*/*.json"))
        series = [json.loads(p.read_text()).get("autoname", "") for p in paths]
        self.assertEqual(series.count("JS-.YYYY.-.#####"), 9)
        self.assertFalse(any(s.startswith("format:JS-") for s in series))
