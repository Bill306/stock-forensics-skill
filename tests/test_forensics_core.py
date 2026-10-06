import copy
from datetime import date, timedelta
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from forensics_core import benchmark_windows, daily_prices, eps_surprise_pct, event_window, export_events, validate_evidence


def synthetic_document():
    source = {"id": "call", "url_or_path": "synthetic://call", "published_at": "2026-09-30T16:30:00-04:00",
              "retrieved_at": "2026-10-06T12:00:00+08:00", "data_period": "FY26 Q3"}
    return {"ticker": "SYNTH", "analysis_as_of": "2026-10-06T12:00:00+08:00", "sources": [source],
            "events": [{"id": "q3", "date": "2026-09-30", "published_at": source["published_at"], "timing": "after-close",
                        "title": "Synthetic earnings call", "source_id": "call"}],
            "factors": [{"id": "margin", "event_id": "q3", "metric": "margin", "novelty": "new_information",
                         "evidence": [{"source_id": "call", "locator": "Q&A, CFO, line 12", "quote": "Margins will fall."}],
                         "expectation": {"status": "unavailable", "reason": "No prior estimate supplied"},
                         "mechanism": "Lower margins could reduce earnings", "confounders": [],
                         "confounder_review": "No independent news supplied", "grade": "insufficient_evidence",
                         "rationale": "Evidence extraction only", "falsifier": "Prior guidance already included the decline"}]}


class EventWindowTests(unittest.TestCase):
    def setUp(self):
        self.prices = [{"d": "2026-09-29", "c": 100.0}, {"d": "2026-09-30", "c": 110.0},
                       {"d": "2026-10-01", "c": 121.0}, {"d": "2026-10-02", "c": 120.0}, {"d": "2026-10-05", "c": 118.0}]

    def test_before_open_and_after_close_use_different_baselines(self):
        before = event_window(self.prices, "2026-09-30", "before-open")["returns"]["1"]
        after = event_window(self.prices, "2026-09-30", "after-close")["returns"]["1"]
        self.assertEqual((before["baseline_date"], before["end_date"]), ("2026-09-29", "2026-09-30"))
        self.assertEqual((after["baseline_date"], after["end_date"]), ("2026-09-30", "2026-10-01"))
        self.assertAlmostEqual(before["price_return_pct"], 10.0)
        self.assertAlmostEqual(after["price_return_pct"], 10.0)

    def test_weekend_uses_actual_sessions(self):
        window = event_window(self.prices, "2026-10-03", "before-open")["returns"]["1"]
        self.assertEqual((window["baseline_date"], window["end_date"]), ("2026-10-02", "2026-10-05"))

    def test_market_move_does_not_become_company_specific_return(self):
        benchmark = [{"d": p["d"], "c": p["c"] * 2} for p in self.prices]
        window = event_window(self.prices, "2026-09-30", "before-open", benchmark)["returns"]["1"]
        self.assertAlmostEqual(window["price_return_pct"], 10)
        self.assertAlmostEqual(window["benchmark_adjusted_return_pp"], 0)

    def test_multiple_benchmarks_use_identical_event_endpoints(self):
        sector = [{"d": p["d"], "c": p["c"] * 3} for p in self.prices]
        results = benchmark_windows(self.prices, "2026-09-30", "after-close",
                                    {"QQQ": self.prices, "SECTOR": sector})
        self.assertEqual(set(results), {"QQQ", "SECTOR"})
        for result in results.values():
            window = result["returns"]["1"]
            self.assertEqual((window["baseline_date"], window["end_date"]),
                             ("2026-09-30", "2026-10-01"))
        self.assertAlmostEqual(results["QQQ"]["returns"]["1"]["benchmark_adjusted_return_pp"], 0)

    def test_multiple_benchmark_mappings_require_names(self):
        with self.assertRaises(ValueError):
            benchmark_windows(self.prices, "2026-09-30", "after-close", {"": self.prices})

    def test_missing_benchmark_endpoint_is_not_forward_filled(self):
        window = event_window(self.prices, "2026-09-30", "before-open", [self.prices[0], self.prices[2]])["returns"]["1"]
        self.assertIsNone(window["benchmark_adjusted_return_pp"])

    def test_outside_coverage_and_incomplete_horizons_remain_unavailable(self):
        for day in ("2026-09-20", "2026-10-20"):
            with self.subTest(day=day):
                self.assertTrue(all(w["status"] == "unavailable" for w in event_window(self.prices, day)["returns"].values()))
        self.assertEqual(event_window(self.prices, "2026-09-30")["returns"]["5"]["status"], "unavailable")

    def test_full_windows_count_sessions_not_calendar_days(self):
        start = date(2026, 9, 1)
        days = [start + timedelta(days=i) for i in range(45)]
        prices = [{"d": d.isoformat(), "c": float(i + 100)} for i, d in enumerate(d for d in days if d.weekday() < 5)]
        result = event_window(prices, prices[2]["d"], "after-close")
        for horizon in (1, 5, 20):
            window = result["returns"][str(horizon)]
            self.assertEqual(window["end_date"], prices[2 + horizon]["d"])
            self.assertAlmostEqual(window["price_return_pct"], (prices[2 + horizon]["c"] / prices[2]["c"] - 1) * 100)

    def test_bad_price_series_are_rejected(self):
        for records in ([], [{"d": "2026-09-30", "c": 0}], [{"d": "2026-09-30", "c": float("nan")}], self.prices + self.prices):
            with self.subTest(records=records):
                with self.assertRaises(ValueError):
                    daily_prices(records)

    def test_eps_surprise_denominator_and_missing_inputs(self):
        self.assertAlmostEqual(eps_surprise_pct(-0.8, -1), 20)
        self.assertIsNone(eps_surprise_pct(1, 0))
        self.assertIsNone(eps_surprise_pct(1, None))


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.prices = [{"d": "2026-09-29", "c": 100.0}, {"d": "2026-09-30", "c": 110.0},
                       {"d": "2026-10-01", "c": 121.0}, {"d": "2026-10-02", "c": 120.0},
                       {"d": "2026-10-05", "c": 118.0}]

    def supported_document(self):
        doc = synthetic_document()
        estimate = copy.deepcopy(doc["sources"][0])
        estimate.update(id="estimate", published_at="2026-09-29T12:00:00-04:00")
        doc["sources"].append(estimate)
        factor = doc["factors"][0]
        factor.update(grade="supported_driver", confounder_review="Synthetic news census reviewed; none identified")
        factor["expectation"] = {"status": "available", "value": 20.0, "as_of": estimate["published_at"],
                                 "source_id": "estimate", "data_period": "FY26 Q4", "unit": "percent", "accounting_basis": "operating margin"}
        prices = [{"d": "2026-09-30", "c": 100}, {"d": "2026-10-01", "c": 95}]
        reaction = event_window(prices, "2026-09-30", "after-close", prices)
        reaction.update(price_source_id="call", benchmark_source_id="call")  # Synthetic sources only.
        doc["events"][0]["reaction"] = reaction
        return doc

    def test_transcript_only_with_missing_expectation_is_a_valid_limited_result(self):
        self.assertEqual(validate_evidence(synthetic_document()), [])

    def test_supported_grade_with_required_evidence_is_eligible_not_proven(self):
        self.assertEqual(validate_evidence(self.supported_document()), [])

    def test_unknown_timing_rejects_supported_grade(self):
        doc = self.supported_document()
        doc["events"][0]["timing"] = "unknown"
        self.assertTrue(any("unknown event timing" in e for e in validate_evidence(doc)))

    def test_missing_expectation_cannot_pass_as_supported_driver(self):
        doc = synthetic_document()
        doc["factors"][0]["grade"] = "supported_driver"
        self.assertTrue(any("prior expectation" in e for e in validate_evidence(doc)))

    def test_post_event_estimate_is_rejected(self):
        doc = self.supported_document()
        doc["factors"][0]["expectation"]["as_of"] = "2026-10-01T12:00:00-04:00"
        self.assertTrue(any("precede" in e for e in validate_evidence(doc)))

    def test_broken_quote_locator_is_rejected(self):
        doc = synthetic_document()
        doc["factors"][0]["evidence"][0]["locator"] = ""
        self.assertTrue(any("locator" in e for e in validate_evidence(doc)))

    def test_prices_after_research_cutoff_are_rejected(self):
        doc = self.supported_document()
        doc["events"][0]["reaction"]["returns"]["1"]["end_date"] = "2026-10-20"
        self.assertTrue(any("prices after" in e for e in validate_evidence(doc)))

    def test_expectation_source_cannot_be_published_after_claimed_cutoff(self):
        doc = self.supported_document()
        doc["sources"][1]["published_at"] = "2026-09-30T12:00:00-04:00"
        self.assertTrue(any("source was published after" in e for e in validate_evidence(doc)))

    def test_malformed_reference_and_grade_are_errors_not_exceptions(self):
        doc = synthetic_document()
        doc["factors"][0].update(event_id=[], grade=[], novelty=[], expectation={"status": []})
        doc["events"][0].update(source_id=[], timing=[], category=[])
        self.assertTrue(validate_evidence(doc))

    def test_inconsistent_benchmark_subtraction_is_rejected(self):
        doc = self.supported_document()
        doc["events"][0]["reaction"]["returns"]["1"]["benchmark_adjusted_return_pp"] = 999
        self.assertTrue(any("subtraction inconsistent" in e for e in validate_evidence(doc)))

    def test_already_disclosed_information_cannot_be_a_supported_new_factor(self):
        doc = self.supported_document()
        doc["factors"][0]["novelty"] = "already_disclosed"
        self.assertTrue(any("new information" in e for e in validate_evidence(doc)))

    def test_disclosure_timeline_links_and_multi_benchmark_reactions_validate(self):
        doc = synthetic_document()
        extra = copy.deepcopy(doc["sources"][0]); extra["id"] = "sector"
        doc["sources"].append(extra)
        stock = copy.deepcopy(doc["sources"][0]); stock["id"] = "stock-prices"
        doc["sources"].append(stock)
        event = doc["events"][0]
        event["event_type"] = "company_news"
        event["benchmark_comparisons"] = [{"symbol": "SECTOR", "role": "industry", "benchmark_source_id": "sector",
                                           "price_source_id": "stock-prices",
                                           "reaction": event_window(self.prices, event["date"], event["timing"], self.prices)}]
        update = copy.deepcopy(event); update["id"] = "update"; update["first_disclosure_event_id"] = "q3"
        update["supersedes_event_ids"] = ["q3"]
        doc["events"].append(update)
        self.assertEqual(validate_evidence(doc), [])

    def test_invalid_benchmark_source_or_disclosure_link_is_rejected(self):
        doc = synthetic_document(); event = doc["events"][0]
        event["benchmark_comparisons"] = [{"symbol": "SECTOR", "role": "industry", "benchmark_source_id": "missing",
                                           "price_source_id": "missing-stock",
                                           "reaction": event_window(self.prices, event["date"], event["timing"], self.prices)}]
        event["first_disclosure_event_id"] = "missing"
        errors = validate_evidence(doc)
        self.assertTrue(any("benchmark_source_id" in error for error in errors))
        self.assertTrue(any("first_disclosure_event_id" in error for error in errors))

    def test_export_preserves_industry_benchmark_annotations(self):
        doc = synthetic_document()
        source = copy.deepcopy(doc["sources"][0]); source["id"] = "sector"
        doc["sources"].append(source)
        doc["events"][0]["benchmark_comparisons"] = [{"symbol": "XLK", "role": "industry", "benchmark_source_id": "sector",
            "price_source_id": "call",
            "reaction": event_window(self.prices, "2026-09-30", "after-close", self.prices)}]
        item = export_events(doc, self.prices)[0]
        self.assertEqual(item["benchmark_comparisons"][0]["symbol"], "XLK")

    def test_malformed_news_metadata_is_reported_without_validator_exception(self):
        doc = synthetic_document()
        doc["events"][0]["event_type"] = []
        doc["events"][0]["publication_date"] = "yesterday"
        doc["events"][0]["supersedes_event_ids"] = [[]]
        errors = validate_evidence(doc)
        self.assertTrue(any("invalid event_type" in error for error in errors))
        self.assertTrue(any("publication_date" in error for error in errors))
        self.assertTrue(any("supersedes_event_ids" in error for error in errors))

    def test_cli_accepts_multiple_named_benchmarks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stock, qqq, sector = root / "stock.json", root / "qqq.json", root / "sector.json"
            stock.write_text(json.dumps(self.prices))
            qqq.write_text(json.dumps(self.prices))
            sector.write_text(json.dumps(self.prices))
            result = subprocess.run([sys.executable, str(SCRIPTS / "transcript_forensics.py"), "price-window",
                                     "--prices", str(stock), "--event-date", "2026-09-30", "--timing", "after-close",
                                     "--benchmark", f"QQQ={qqq}", "--benchmark", f"SECTOR={sector}"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            comparisons = json.loads(result.stdout)["benchmark_comparisons"]
            self.assertEqual([item["symbol"] for item in comparisons], ["QQQ", "SECTOR"])
            self.assertTrue(all(item["reaction"]["returns"]["1"]["end_date"] == "2026-10-01" for item in comparisons))

    def test_material_unresolved_confounder_caps_grade(self):
        doc = self.supported_document()
        doc["factors"][0]["confounders"] = [{"description": "Concurrent policy shock", "material": True, "status": "unresolved"}]
        self.assertTrue(any("material unresolved" in e for e in validate_evidence(doc)))

    def test_export_annotations_preserves_grade_without_inventing_move(self):
        doc = synthetic_document()
        events = export_events(doc, [{"d": "2026-09-29", "c": 100}, {"d": "2026-10-01", "c": 95}])
        self.assertEqual(events[0]["px"], 100)
        self.assertEqual(events[0]["grades"], ["insufficient_evidence"])
        self.assertEqual(events[0]["mv"], "")

    def test_cli_refuses_to_overwrite_existing_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path, output_path = Path(tmp) / "factors.json", Path(tmp) / "user-data.json"
            input_path.write_text(json.dumps(synthetic_document()))
            output_path.write_text("keep my data")
            result = subprocess.run([sys.executable, str(SCRIPTS / "transcript_forensics.py"), "validate", "--input", str(input_path), "--output", str(output_path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(output_path.read_text(), "keep my data")


if __name__ == "__main__":
    unittest.main()
