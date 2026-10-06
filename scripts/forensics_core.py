"""Deterministic event windows and evidence checks; no downloads or LLM calls."""

from datetime import date, datetime
import math


TIMINGS = {"before-open", "after-close", "during-session", "unknown"}
GRADES = {"supported_driver", "plausible_contributor", "coincident_only", "insufficient_evidence"}


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _session_date(value):
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("Session date must use YYYY-MM-DD")
    return parsed


def daily_prices(records):
    """Validate supplied daily session closes; reject duplicates and invalid values."""
    if not isinstance(records, list) or not records:
        raise ValueError("Prices must be a non-empty array of daily {d, c} records")
    result = []
    seen = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Each price record must be an object")
        day = record.get("d")
        try:
            parsed = date.fromisoformat(day)
        except (TypeError, ValueError):
            raise ValueError("Price dates must use YYYY-MM-DD") from None
        if parsed.isoformat() != day or day in seen:
            raise ValueError("Price dates must be unique YYYY-MM-DD sessions")
        close = record.get("c")
        if not finite_number(close) or close <= 0:
            raise ValueError("Daily closes must be finite and positive")
        seen.add(day)
        result.append({"d": day, "c": float(close)})
    return sorted(result, key=lambda row: row["d"])


def price_on_or_before(records, event_date):
    """No extrapolation outside coverage; only daily closes at/before the date."""
    prices = daily_prices(records)
    _session_date(event_date)
    if event_date < prices[0]["d"] or event_date > prices[-1]["d"]:
        return None
    return next(row["c"] for row in reversed(prices) if row["d"] <= event_date)


def eps_surprise_pct(actual, estimate):
    """Percentage with an absolute denominator; zero/missing estimates are unavailable."""
    if not finite_number(actual) or not finite_number(estimate) or estimate == 0:
        return None
    return (actual - estimate) / abs(estimate) * 100


def event_window(records, event_date, timing="unknown", benchmark=None, horizons=(1, 5, 20)):
    """Close-to-close windows in actual stock sessions, with exact benchmark endpoints.

    Daily data cannot isolate the call from the release or other intraday news.
    Unknown timing uses a descriptive date window and never supports causal attribution.
    """
    if timing not in TIMINGS:
        raise ValueError("Invalid event timing")
    _session_date(event_date)
    prices = daily_prices(records)
    bench = {row["d"]: row["c"] for row in daily_prices(benchmark)} if benchmark is not None else {}
    if any(not isinstance(n, int) or isinstance(n, bool) or n < 1 for n in horizons):
        raise ValueError("Horizons must be positive session counts")
    limitations = ["Daily closes measure the combined disclosure window, not individual remarks."]
    if timing in {"unknown", "during-session"}:
        limitations.append("Timing is unknown or intraday; the window includes other session information.")
    result = {"event_date": event_date, "timing": timing, "returns": {}, "limitations": limitations}
    # An event outside the supplied coverage is never matched to the nearest endpoint.
    if event_date < prices[0]["d"] or event_date > prices[-1]["d"]:
        anchor = None
    elif timing == "after-close":
        baseline = max(i for i, row in enumerate(prices) if row["d"] <= event_date)
        anchor = baseline + 1
    else:
        anchor = next((i for i, row in enumerate(prices) if row["d"] >= event_date), None)
        baseline = anchor - 1 if anchor is not None else -1
    for horizon in horizons:
        entry = {"status": "unavailable", "price_return_pct": None,
                 "benchmark_return_pct": None, "benchmark_adjusted_return_pp": None}
        if anchor is None or baseline < 0 or anchor + horizon - 1 >= len(prices):
            entry["reason"] = "Insufficient daily history for the baseline and complete window"
        else:
            start, end = prices[baseline], prices[anchor + horizon - 1]
            raw = (end["c"] / start["c"] - 1) * 100
            entry.update(status="available", baseline_date=start["d"], end_date=end["d"], price_return_pct=raw)
            if start["d"] in bench and end["d"] in bench:
                reference = (bench[end["d"]] / bench[start["d"]] - 1) * 100
                entry.update(benchmark_return_pct=reference, benchmark_adjusted_return_pp=raw - reference)
            else:
                entry["benchmark_gap"] = "Benchmark closes unavailable on one or both exact endpoint dates"
        result["returns"][str(horizon)] = entry
    result["adjustment_method"] = "stock cumulative return minus benchmark cumulative return (percentage points); not a fitted market model"
    return result


def benchmark_windows(records, event_date, timing, benchmarks, horizons=(1, 5, 20)):
    """Calculate the same event windows against named broad/industry references."""
    if not isinstance(benchmarks, dict) or not benchmarks:
        raise ValueError("Benchmarks must be a non-empty symbol-to-daily-prices mapping")
    if any(not isinstance(symbol, str) or not symbol.strip() for symbol in benchmarks):
        raise ValueError("Benchmark symbols must be non-empty text")
    return {symbol: event_window(records, event_date, timing, prices, horizons)
            for symbol, prices in benchmarks.items()}


def _aware_timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp must be text")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("Timestamp needs a UTC offset")
    return parsed


def _resolve(mapping, key):
    return mapping.get(key) if isinstance(key, str) else None


def validate_evidence(document):
    """Return errors without modifying the analyst's proposed grades.

    Passing checks verifies consistency/eligibility, not the truth of source material.
    """
    errors = []
    if not isinstance(document, dict):
        return ["Document must be an object"]
    for key in ("ticker", "analysis_as_of"):
        if not isinstance(document.get(key), str) or not document[key].strip():
            errors.append(f"{key}: required text")
    try:
        as_of = _aware_timestamp(document.get("analysis_as_of"))
    except (TypeError, ValueError):
        as_of = None
        errors.append("analysis_as_of: ISO timestamp with UTC offset required")
    arrays = {}
    for key in ("sources", "events", "factors"):
        if not isinstance(document.get(key), list):
            errors.append(f"{key}: array required")
        arrays[key] = document.get(key) if isinstance(document.get(key), list) else []
    sources, events = {}, {}
    for source in arrays["sources"]:
        if not isinstance(source, dict):
            errors.append("sources: object required")
            continue
        sid = source.get("id")
        if not isinstance(sid, str) or not sid or sid in sources:
            errors.append("sources: unique non-empty id required")
            continue
        sources[sid] = source
        for key in ("url_or_path", "published_at", "retrieved_at", "data_period"):
            if not isinstance(source.get(key), str) or not source[key].strip():
                errors.append(f"source {sid}: {key} required (use 'unknown' explicitly where necessary)")
        for key in ("published_at", "retrieved_at"):
            if source.get(key) == "unknown":
                continue
            try:
                timestamp = _aware_timestamp(source.get(key))
                if key == "published_at" and as_of is not None and timestamp > as_of:
                    errors.append(f"source {sid}: published after analysis_as_of")
            except (TypeError, ValueError):
                errors.append(f"source {sid}: {key} must be an offset timestamp or 'unknown'")
    for event in arrays["events"]:
        if not isinstance(event, dict):
            errors.append("events: object required")
            continue
        eid = event.get("id")
        if not isinstance(eid, str) or not eid or eid in events:
            errors.append("events: unique non-empty id required")
            continue
        events[eid] = event
        try:
            _session_date(event.get("date"))
        except (TypeError, ValueError):
            errors.append(f"event {eid}: date must be YYYY-MM-DD")
        if not isinstance(event.get("timing"), str) or event["timing"] not in TIMINGS:
            errors.append(f"event {eid}: invalid timing")
        if _resolve(sources, event.get("source_id")) is None:
            errors.append(f"event {eid}: source_id must resolve")
        if not isinstance(event.get("category", "earnings"), str) or event.get("category", "earnings") not in {"earnings", "corporate", "sellside", "scandal", "narrative"}:
            errors.append(f"event {eid}: invalid chart category")
        if "event_type" in event and (not isinstance(event["event_type"], str) or event["event_type"] not in {"earnings", "company_disclosure", "company_news", "industry_news", "macro_news", "sellside", "fund_flow", "other"}):
            errors.append(f"event {eid}: invalid event_type")
        for date_key in ("publication_date", "retrieval_date"):
            if date_key in event:
                try:
                    _session_date(event[date_key])
                except (TypeError, ValueError):
                    errors.append(f"event {eid}: {date_key} must be YYYY-MM-DD")
        if not isinstance(event.get("title"), str) or not event["title"].strip():
            errors.append(f"event {eid}: title required")
        timestamp = event.get("published_at")
        if timestamp != "unknown":
            try:
                observed = _aware_timestamp(timestamp)
                if as_of is not None and observed > as_of:
                    errors.append(f"event {eid}: occurs after analysis_as_of")
            except (TypeError, ValueError):
                errors.append(f"event {eid}: published_at must be offset timestamp or 'unknown'")
        reactions = []
        if "reaction" in event:
            reactions.append(("reaction", event["reaction"]))
        comparisons = event.get("benchmark_comparisons", [])
        if not isinstance(comparisons, list):
            errors.append(f"event {eid}: benchmark_comparisons must be an array")
            comparisons = []
        symbols = set()
        for item in comparisons:
            if not isinstance(item, dict):
                errors.append(f"event {eid}: benchmark comparison must be an object")
                continue
            symbol, role = item.get("symbol"), item.get("role")
            if not isinstance(symbol, str) or not symbol.strip() or symbol in symbols:
                errors.append(f"event {eid}: benchmark symbols must be unique non-empty text")
            else:
                symbols.add(symbol)
            if not isinstance(role, str) or role not in {"broad_market", "industry", "peer_index", "other"}:
                errors.append(f"event {eid}: invalid benchmark role")
            if _resolve(sources, item.get("benchmark_source_id")) is None:
                errors.append(f"event {eid}: benchmark_source_id must resolve")
            if _resolve(sources, item.get("price_source_id")) is None:
                errors.append(f"event {eid}: comparison price_source_id must resolve")
            if not isinstance(item.get("reaction"), dict):
                errors.append(f"event {eid}: benchmark comparison requires a reaction object")
            else:
                reactions.append((symbol or "benchmark", item["reaction"]))
        for label, reaction in reactions:
            if not isinstance(reaction, dict) or not isinstance(reaction.get("returns"), dict):
                errors.append(f"event {eid}: {label} requires a returns object")
            else:
                if reaction.get("event_date") != event.get("date") or reaction.get("timing") != event.get("timing"):
                    errors.append(f"event {eid}: {label} date/timing must match")
                for horizon, window in reaction["returns"].items():
                    if horizon not in {"1", "5", "20"} or not isinstance(window, dict) or not isinstance(window.get("status"), str) or window["status"] not in {"available", "unavailable"}:
                        errors.append(f"event {eid}: invalid {label} horizon/status")
                        continue
                    if window["status"] == "available":
                        if not finite_number(window.get("price_return_pct")):
                            errors.append(f"event {eid}: {label} window requires numeric stock return")
                        raw = window.get("price_return_pct")
                        reference = window.get("benchmark_return_pct")
                        adjusted = window.get("benchmark_adjusted_return_pp")
                        if reference is not None and not finite_number(reference):
                            errors.append(f"event {eid}: {label} benchmark return must be numeric or null")
                        if adjusted is not None and (not finite_number(adjusted) or not finite_number(raw) or not finite_number(reference) or abs(raw - reference - adjusted) > 1e-8):
                            errors.append(f"event {eid}: {label} subtraction inconsistent with raw returns")
                        try:
                            baseline = _session_date(window.get("baseline_date"))
                            end = _session_date(window.get("end_date"))
                            if end <= baseline:
                                errors.append(f"event {eid}: {label} endpoint must follow baseline")
                            cutoff = as_of
                            if cutoff is not None and timestamp != "unknown":
                                cutoff = cutoff.astimezone(_aware_timestamp(timestamp).tzinfo)
                            if cutoff is not None and end > cutoff.date():
                                errors.append(f"event {eid}: {label} contains prices after analysis_as_of")
                        except (TypeError, ValueError):
                            errors.append(f"event {eid}: invalid {label} endpoint dates")
    for eid, event in events.items():
        first = event.get("first_disclosure_event_id")
        if first is not None and (not isinstance(first, str) or first not in events or first == eid):
            errors.append(f"event {eid}: first_disclosure_event_id must resolve to another event")
        supersedes = event.get("supersedes_event_ids", [])
        if not isinstance(supersedes, list) or any(not isinstance(ref, str) or ref not in events or ref == eid for ref in supersedes):
            errors.append(f"event {eid}: supersedes_event_ids must resolve to other events")
    factor_ids = set()
    for factor in arrays["factors"]:
        if not isinstance(factor, dict):
            errors.append("factors: object required")
            continue
        fid = factor.get("id")
        if not isinstance(fid, str) or not fid or fid in factor_ids:
            errors.append("factors: unique non-empty id required")
            continue
        factor_ids.add(fid)
        label = f"factor {fid}"
        event = _resolve(events, factor.get("event_id"))
        if event is None:
            errors.append(f"{label}: event_id must resolve")
        grade = factor.get("grade")
        if not isinstance(grade, str) or grade not in GRADES:
            errors.append(f"{label}: invalid attribution grade")
        for key in ("metric", "rationale", "falsifier"):
            if not isinstance(factor.get(key), str) or not factor[key].strip():
                errors.append(f"{label}: {key} required")
        novelty = factor.get("novelty")
        if not isinstance(novelty, str) or novelty not in {"new_information", "already_disclosed", "unknown"}:
            errors.append(f"{label}: invalid novelty")
        evidence = factor.get("evidence")
        if not isinstance(evidence, list):
            errors.append(f"{label}: evidence array required")
            evidence = []
        for quote in evidence:
            if not isinstance(quote, dict) or _resolve(sources, quote.get("source_id")) is None or any(
                not isinstance(quote.get(k), str) or not quote[k].strip() for k in ("locator", "quote")
            ):
                errors.append(f"{label}: each evidence item needs a resolved source_id, locator and exact quote")
        expectation = factor.get("expectation")
        if not isinstance(expectation, dict) or not isinstance(expectation.get("status"), str) or expectation["status"] not in {"available", "unavailable"}:
            errors.append(f"{label}: expectation needs available/unavailable status")
            expectation = {}
        expectation_valid = False
        if expectation.get("status") == "available":
            if not finite_number(expectation.get("value")):
                errors.append(f"{label}: expectation value must be finite numeric")
            for key in ("data_period", "unit", "accounting_basis"):
                if not isinstance(expectation.get(key), str) or not expectation[key].strip():
                    errors.append(f"{label}: expectation {key} required")
            expectation_source = _resolve(sources, expectation.get("source_id"))
            if expectation_source is None:
                errors.append(f"{label}: expectation source_id must resolve")
            try:
                cutoff = _aware_timestamp(expectation.get("as_of"))
                published = _aware_timestamp(event.get("published_at")) if event else None
                if published is None or cutoff >= published:
                    errors.append(f"{label}: expectation must precede the event publication")
                else:
                    expectation_valid = True
                if expectation_source is not None:
                    source_time = _aware_timestamp(expectation_source.get("published_at"))
                    if source_time > cutoff:
                        expectation_valid = False
                        errors.append(f"{label}: expectation source was published after its claimed cutoff")
            except (TypeError, ValueError):
                errors.append(f"{label}: comparable offset timestamps needed for expectation and publication")
        elif expectation.get("status") == "unavailable" and not expectation.get("reason"):
            errors.append(f"{label}: unavailable expectation needs a reason")
        if isinstance(grade, str) and grade in {"supported_driver", "plausible_contributor"}:
            if not evidence or not isinstance(factor.get("mechanism"), str) or not factor["mechanism"].strip():
                errors.append(f"{label}: driver grades require located evidence and mechanism")
            if not isinstance(factor.get("confounders"), list) or not isinstance(factor.get("confounder_review"), str) or not factor["confounder_review"].strip():
                errors.append(f"{label}: driver grades require confounders array and documented review")
        if grade == "supported_driver":
            if novelty != "new_information" or not expectation_valid:
                errors.append(f"{label}: supported_driver requires new information and a prior expectation")
            if not event or event.get("timing") == "unknown" or event.get("published_at") == "unknown":
                errors.append(f"{label}: unknown event timing caps the grade below supported_driver")
            reaction = event.get("reaction") if event else None
            windows = reaction.get("returns", {}) if isinstance(reaction, dict) else {}
            if not isinstance(windows, dict) or not any(
                isinstance(w, dict) and w.get("status") == "available" and finite_number(w.get("benchmark_adjusted_return_pp"))
                for w in windows.values()
            ):
                errors.append(f"{label}: supported_driver requires a benchmark-comparable reaction window")
            if not isinstance(reaction, dict) or _resolve(sources, reaction.get("price_source_id")) is None or _resolve(sources, reaction.get("benchmark_source_id")) is None:
                errors.append(f"{label}: reaction must reference stock and benchmark sources")
            if isinstance(reaction, dict) and event and (reaction.get("event_date") != event.get("date") or reaction.get("timing") != event.get("timing")):
                errors.append(f"{label}: reaction date/timing must match the event")
            if isinstance(windows, dict):
                for window in windows.values():
                    if not isinstance(window, dict) or window.get("status") != "available":
                        continue
                    raw, reference, adjusted = (window.get(k) for k in ("price_return_pct", "benchmark_return_pct", "benchmark_adjusted_return_pp"))
                    if finite_number(adjusted) and (not finite_number(raw) or not finite_number(reference) or abs(raw - reference - adjusted) > 1e-8):
                        errors.append(f"{label}: benchmark subtraction inconsistent with raw returns")
            confounders = factor.get("confounders")
            if isinstance(confounders, list) and any(isinstance(c, dict) and c.get("material") is True and c.get("status") == "unresolved" for c in confounders):
                errors.append(f"{label}: material unresolved confounder caps the grade below supported_driver")
    return errors


def export_events(document, records):
    """Export chart annotations after structural validation; never turn EPS into returns."""
    errors = validate_evidence(document)
    if errors:
        raise ValueError("; ".join(errors))
    prices = daily_prices(records)
    result = []
    for event in document["events"]:
        px = price_on_or_before(prices, event["date"])
        if px is None:
            continue
        factors = [f for f in document["factors"] if f["event_id"] == event["id"]]
        source_map = {s["id"]: s for s in document["sources"]}
        locations = [f'{q["source_id"]} / {q["locator"]}' for f in factors for q in f["evidence"]]
        reaction = event.get("reaction", {})
        windows = reaction.get("returns", {}) if isinstance(reaction, dict) else {}
        first_window = windows.get("1", {}) if isinstance(windows, dict) else {}
        move = first_window.get("price_return_pct") if isinstance(first_window, dict) and first_window.get("status") == "available" else None
        result.append({"date": event["date"], "cat": event.get("category", "earnings"),
                       "title": event["title"], "px": px,
                       "mv": f"{move:+.1f}% (1 session, supplied evidence)" if finite_number(move) else "",
                       "mvDir": "up" if finite_number(move) and move > 0 else "down" if finite_number(move) and move < 0 else "",
                       "source_id": event["source_id"], "timing": event["timing"],
                       "source_url_or_path": source_map[event["source_id"]]["url_or_path"], "evidence_locations": locations,
                       "reaction": reaction,
                       "benchmark_comparisons": event.get("benchmark_comparisons", []),
                       "grades": [f["grade"] for f in factors],
                       "desc": " | ".join(f'{f["grade"]}: {f["rationale"]}' for f in factors) or "No attributed factor; event annotation only."})
    return result
