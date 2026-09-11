import importlib.util
import os
from pathlib import Path
import tempfile
import unittest


SERVER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "server.py"


def load_server():
    spec = importlib.util.spec_from_file_location("forensics_server", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ServerSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = load_server()

    def test_normalize_symbol_accepts_common_global_tickers(self):
        for raw, expected in [
            (" aapl ", "AAPL"),
            ("700.hk", "700.HK"),
            ("^hstech", "^HSTECH"),
            ("BRK-B", "BRK-B"),
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(self.server.normalize_symbol(raw), expected)

    def test_normalize_symbol_rejects_path_and_markup_input(self):
        for raw in ["../secret", "AAPL/../../x", "<script>", "", "A" * 33]:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    self.server.normalize_symbol(raw)

    def test_chart_path_stays_in_configured_output_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("FORENSICS_OUTPUT_DIR")
            os.environ["FORENSICS_OUTPUT_DIR"] = tmp
            try:
                path = self.server.chart_path("700.HK")
                self.assertEqual(path.parent, Path(tmp).resolve())
                self.assertEqual(path.name, "700.HK_ForensicChart.html")
            finally:
                if old is None:
                    os.environ.pop("FORENSICS_OUTPUT_DIR", None)
                else:
                    os.environ["FORENSICS_OUTPUT_DIR"] = old

    def test_generated_html_escapes_server_and_script_contexts(self):
        html = self.server.generate_html(
            symbol="SAFE",
            company_name="Example <script>alert(1)</script>",
            currency_symbol="$",
            price_data=[{"d": "2025-01-01", "o": 1, "h": 2, "l": 1, "c": 2, "v": 10}],
            events=[{
                "date": "2025-01-01",
                "cat": "earnings",
                "title": "</script><script>alert(2)</script>",
                "px": 2,
                "mv": "+1%",
                "mvDir": "up",
                "desc": "example",
            }],
            last_px=2,
            ttm_return=1,
            cat_counts={"earnings": 1},
        )
        self.assertNotIn("Example <script>", html)
        self.assertNotIn("</script><script>alert(2)</script>", html)
        self.assertIn("Example &lt;script&gt;", html)
        self.assertIn("\\u003c/script\\u003e", html)


if __name__ == "__main__":
    unittest.main()
