import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
import sys
from unittest.mock import patch

import pandas as pd


SERVER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "server.py"
sys.path.insert(0, str(SERVER_PATH.parent))


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
        self.assertIn('class="range-btn active" data-r="5Y"', html)
        self.assertIn("let currentRange = '5Y';", html)


class ResearchAccuracyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = load_server()

    def setUp(self):
        self.prices = [{"d": "2026-09-29", "c": 100.0}, {"d": "2026-09-30", "c": 95.0}, {"d": "2026-10-01", "c": 96.0}]

    def test_chart_price_api_defaults_to_five_years_and_supports_two_and_ten(self):
        frame = pd.DataFrame({"Open": [100.0], "High": [101.0], "Low": [99.0], "Close": [100.0], "Volume": [10]},
                             index=pd.to_datetime(["2026-10-01"]))

        class FakeTicker:
            def __init__(self):
                self.calls = []

            def history(self, **kwargs):
                self.calls.append(kwargs)
                return frame

        fake = FakeTicker()
        client = self.server.app.test_client()
        with patch.object(self.server.yf, "Ticker", return_value=fake):
            default = client.get("/api/price/SYNTH")
            two_years = client.get("/api/price/SYNTH?range=2Y")
            ten_years = client.get("/api/price/SYNTH?range=10Y")
        self.assertEqual([default.status_code, two_years.status_code, ten_years.status_code], [200, 200, 200])
        self.assertEqual(fake.calls, [
            {"period": "5y", "interval": "1wk", "auto_adjust": True},
            {"period": "2y", "interval": "1wk", "auto_adjust": True},
            {"period": "10y", "interval": "1wk", "auto_adjust": True},
        ])

    def test_price_lookup_never_substitutes_future_or_extrapolated_close(self):
        sparse = [{"d": "2026-09-28", "c": 100.0}, {"d": "2026-10-05", "c": 110.0}]
        self.assertEqual(self.server.find_price_on_date(sparse, "2026-09-30"), 100.0)
        self.assertIsNone(self.server.find_price_on_date(sparse, "2026-10-20"))
        self.assertIsNone(self.server.find_price_on_date(sparse, "2026-09-01"))

    def test_earnings_beat_with_falling_stock_keeps_surprise_and_return_separate(self):
        frame = pd.DataFrame({"Reported EPS": [1.2], "EPS Estimate": [1.0]},
                             index=pd.to_datetime(["2026-09-30T08:00:00-04:00"]))
        event = self.server.build_earnings_events(frame, self.prices, "America/New_York")[0]
        self.assertAlmostEqual(event["eps_surprise_pct"], 20.0)
        self.assertAlmostEqual(event["price_return_pct"], -5.0)
        self.assertEqual(event["mvDir"], "down")
        self.assertIn("-5.0%", event["mv"])
        self.assertEqual(event["timing"], "unknown")

    def test_missing_consensus_and_future_estimated_event_do_not_create_beats(self):
        frame = pd.DataFrame({"Reported EPS": [1.2, float("nan")], "EPS Estimate": [float("nan"), 1.0]},
                             index=pd.to_datetime(["2026-09-30", "2026-10-01"]))
        events = self.server.build_earnings_events(frame, self.prices)
        self.assertEqual(len(events), 1)
        self.assertIsNone(events[0]["eps_surprise_pct"])

    def test_provider_timestamp_is_converted_to_exchange_local_date(self):
        frame = pd.DataFrame({"Reported EPS": [1.2], "EPS Estimate": [1.0]},
                             index=pd.to_datetime(["2026-09-29T23:00:00-04:00"]))
        events = self.server.build_earnings_events(frame, self.prices, "Asia/Tokyo")
        self.assertEqual(events[0]["date"], "2026-09-30")

    def test_generate_uses_calendar_not_fiscal_history_and_discloses_source_failure(self):
        prices = pd.DataFrame({"Open": [100, 95, 96], "High": [101, 96, 97], "Low": [99, 94, 95],
                               "Close": [100, 95, 96], "Volume": [10, 20, 30]},
                              index=pd.to_datetime([p["d"] for p in self.prices]))
        calendar = pd.DataFrame({"Reported EPS": [1.2], "EPS Estimate": [1.0]}, index=pd.to_datetime(["2026-09-30"]))

        class FakeTicker:
            info = {"longName": "Synthetic", "currency": "USD"}
            splits = pd.Series(dtype=float)

            def history(self, **kwargs):
                self.history_kwargs = kwargs
                return prices

            def get_earnings_dates(self, limit):
                return calendar

            @property
            def earnings_history(self):
                raise AssertionError("Fiscal-quarter index must not be used as announcement date")

            @property
            def upgrades_downgrades(self):
                raise RuntimeError("Synthetic source failure")

        fake = FakeTicker()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"FORENSICS_OUTPUT_DIR": tmp}), patch.object(self.server.yf, "Ticker", return_value=fake):
            response = self.server.app.test_client().post("/api/generate", json={"symbol": "SYNTH"})
            self.assertEqual(response.status_code, 200)
            result = response.get_json()
            self.assertEqual(fake.history_kwargs, {"period": "max", "interval": "1d", "auto_adjust": True})
            self.assertEqual(result["events"][0]["date"], "2026-09-30")
            self.assertEqual(result["source_status"][1]["status"], "failed")
            content = Path(result["path"]).read_text()
            self.assertIn("Unavailable", content)  # No fabricated TTM return for a 3-day series.
            self.assertIn("analyst changes: failed", content)
            self.assertNotIn("+20.0% (date window", content)

    def test_bad_evidence_is_rejected_before_any_price_download(self):
        with patch.object(self.server.yf, "Ticker") as ticker:
            response = self.server.app.test_client().post("/api/generate", json={"symbol": "SYNTH", "evidence": {}})
            self.assertEqual(response.status_code, 400)
            ticker.assert_not_called()


if __name__ == "__main__":
    unittest.main()
