---
name: forensics
description: Investigate historical stock-price drivers, earnings reactions, or information revealed in a call/transcript. Use when the user asks why a stock moved, which metrics were priced, or whether a disclosure contributed to a move. Supports evidence-led attribution and falsifiable current debates.
metadata:
  author: Bill306
  version: "1.4.0"
---

# Forensics — Know the Stock

Identify what information changed expectations, how it could change earnings or valuation, and whether the price reaction supports that explanation. Historical drivers are hypotheses to re-test as the company changes stage, not predictions.

## Choose the task

- **Price drivers:** start with the chart, then test catalysts against the full event set.
- **Earnings reaction:** compare actual results, guidance and key metrics with pre-publication expectations.
- **Call/transcript attribution:** read [references/transcript-forensics.md](references/transcript-forensics.md). Analyze supplied text, PDF or subtitles directly. Route media through available transcript tools, retaining original evidence locations; do not duplicate ASR engines or claim unavailable transcripts were read.
- **Moves with news or market context:** read [references/news-and-market-context.md](references/news-and-market-context.md). Compare broad-market and relevant industry benchmarks, then build a dated company/news event timeline before assigning a company-specific explanation.
- **Current debate:** track changes in questions and disclosed metrics, then identify the disagreement, next observable evidence and falsifier. Use available quarters and disclose coverage; a fixed quarter count does not guarantee understanding.

For broad company research, apply this method to the requested price-driver component. Accounting-quality/fraud investigations need their own accounting procedures; price attribution does not establish fraud.

## Choose the analysis period

Honor a user-specified lookback or exact start/end dates. If none are given, use the five years ending on the most recent completed exchange session and state the actual start and end sessions. Offer a shorter or longer lookback (such as 1, 2, 3 or 10 years), all available history, or custom dates when period choice would help; do not block a useful first pass while waiting for a preference. Retrieve the preceding common trading-session close when needed to calculate the first in-window return. Apply the selected dates consistently to stock prices, benchmarks, move screening and the news/event census. Historical earnings tables may focus on the most recent 6–8 available quarters, but disclose that narrower fundamental sample.

## Evidence and timing

Prefer company, exchange and regulator disclosures for facts. Read full original news and source sell-side data, separating estimates, channel-check claims and opinions. Ratings/targets can themselves be candidate events; they are not proof of value or causation. yfinance is an unofficial data adapter.

Record each source's URL/local path, publication time, data/reporting period, retrieval date and evidence locator. Separate reporting-period end, announcement and call times. Use the exchange timezone and actual sessions. Preserve currency, price-adjustment basis, EPS/accounting basis, metric units and historical consensus cutoff. Missing fields stay explicit; never substitute today's estimates for historical expectations.

## Investigation

1. **Map prices and coverage.** Use the requested period; absent a period, use five years through the latest completed exchange session. State exact first/last dates and price-source coverage. Screen large moves against the stock's own history, a broad-market benchmark and a relevant industry/peer benchmark where available. A 10% threshold is optional, not universal. Retain unexplained moves.
2. **Build a dated event census.** Include company releases/filings, earnings calls, material company news, relevant industry and macro news, and sell-side actions. Record when each item first became public, its source, and whether it repeats, updates or supersedes an earlier disclosure. Company-generated items count even when routine: earnings-date notices, prospectus supplements or share-sale eligibility disclosures, and company-published product or research announcements are candidates when they coincide with a screened date. Record the disclosure date and the market-reaction date separately; share-sale eligibility is not evidence that holders actually sold. Include quiet earnings/events and comparison dates; disclose source gaps. Report census completeness as mapped versus unmatched screened dates (for example, "26 of 46 screened dates mapped to a sourced event; 20 remain unmatched") so unexplained dates stay visible.
3. **Test metric candidates.** Use sector knowledge, calls and company stage. For each candidate retain supporting events, contradictory cases, stage applicability and a falsifier. Rank the best-supported one or two metrics only after this check; leave rankings unresolved when evidence is weak.
4. **Compare prior expectations.** For 6–8 quarters when available, tabulate period, announcement time, metric actual, prior expectation/source/cutoff, surprise, revenue, comparable EPS, guidance delta, stock and benchmark reactions. Show absolute gaps and denominator limits for zero/near-zero or negative estimates. Growth-rate surprises use percentage points. Missing consensus stays unavailable.
5. **Calculate reactions.** Read [references/event-windows.md](references/event-windows.md) for timing, 1/5/20-session windows, broad/industry comparisons, exact benchmark endpoints and missing-data rules. EPS surprise is never a stock-return field. Longer windows collect other information and do not themselves increase causal confidence.
6. **Attribute conservatively.** Test shared market/industry moves before company-specific explanations. Link each candidate to its publication time, novelty, prior expectation, earnings/valuation mechanism and observed reaction. Review company, macro and industry news, peers, FX, policy, concurrent disclosures and anticipated information; explain conflicting signs. A broad or sector ETF is a return benchmark, not proof of investor flows. Call flows only when separate flow data support them. Distinguish facts from inference.
7. **State the debate.** Give evidence on both sides, a verifiable next observation and what would disprove each interpretation. National market characteristics and management tone are hypotheses, not default explanations.

## Attribution grades

| Grade | Meaning |
|---|---|
| `supported_driver` | Located evidence of new information, prior expectation, known timing, mechanism, benchmark-comparable reaction and reviewed competing explanations support contribution. This does not prove causality or quantify a share of the move. |
| `plausible_contributor` | Evidence and mechanism support a plausible contribution, but timing, expectations or competing explanations limit confidence. |
| `coincident_only` | Event and move overlap without a supported information/expectation/mechanism link. |
| `insufficient_evidence` | Essential evidence, usable prices or timing are missing. |

Unknown timing caps the grade below `supported_driver`. A routine company disclosure (calendar notice, share-sale eligibility, published research) adjacent to a move is at most `coincident_only` unless timing, novelty and mechanism evidence support more. Transcript-only work can deliver factor hypotheses with missing-data disclosures; never fabricate returns to complete a table.

## Deliverables and helpers

Match the requested scope. A full report includes coverage/cutoff, major moves and the event census, an earnings/expectations table, driver hypotheses with supporting and contradictory cases, current debate/falsifiers, and sources/limitations. Charts are useful when requested or when they clarify the evidence, rather than a mandatory output for every question.

For repeatable transcript work, read [references/evidence-schema.md](references/evidence-schema.md). Save `transcript-factors.json` plus a human-readable report. The helper checks consistency; it does not perform semantic source review or generate LLM conclusions:

```bash
python3 scripts/transcript_forensics.py validate --input transcript-factors.json
python3 scripts/transcript_forensics.py price-window --prices daily-prices.json --benchmark daily-benchmark.json --event-date 2026-09-30 --timing after-close
python3 scripts/transcript_forensics.py export-events --input transcript-factors.json --prices daily-prices.json --output chart-events.json
```

Keep supplied/private documents outside public Skill files. CLI output creates new files and refuses to overwrite existing paths.

## Chart and optional app

Expose sources/locators, timing, uncertainty and labeled return windows in chart annotations. Keep unresolved moves. Verify actual interactions before describing a chart as verified. Compare raw and benchmark returns on matching endpoints and adjustment conventions.

When an interactive HTML explorer is requested, build a single self-contained file. Embed price and event JSON in the page; make each event marker clickable, with a detail panel showing disclosure date, market-reaction date, timing, benchmark-relative returns, source link and attribution grade; include an event list with a documented/unexplained filter; default to the five-year view with selectable 1/2/3-year, all-history and custom-date ranges; label benchmark-relative returns with % (not "pp") when the user prefers percent notation; embed images such as company logos as base64 data URIs so the file works offline over file://. When transcript coverage exists, add a sell-side question-focus migration section: for each available quarter, summarize the marginal change in analyst question themes qualitatively, disclose which quarters are covered, and never present theme summaries as frequency statistics.

The optional app requires Python 3.9+, Flask and yfinance. Explicitly install `requirements.txt` when needed, then run `python3 scripts/server.py` from the repo root. Defaults: `127.0.0.1:3457`, output `./forensics-output`, and a five-year chart view. The chart lets users select other ranges, including 1, 2, 3 or 10 years and all available history. It fetches daily adjusted closes, provider announcement dates, analyst changes and splits, reports source gaps and can add validated evidence through the `/api/generate` JSON `evidence` field. Provider events remain unverified attribution. It does not collect company or market news, industry benchmarks or fund-flow data; research and attach those sources separately.

`scripts/template_chart.html` is a legacy illustration with historical sample data, not a general renderer. For arbitrary tickers use the app renderer or generate a chart from validated evidence and supplied prices. Examples are preserved in [references/legacy-examples.md](references/legacy-examples.md); verify claims before reuse.

## Verification

Run `scripts/validate.sh` after code changes. Check EPS beats with falling prices, stock/benchmark moves together, unknown timing, missing expectations and out-of-coverage windows. Missing fields must stay missing, ineligible grades must fail validation, and no future close may substitute for an earlier baseline. Passing tests verifies mechanics, not a live provider or a research conclusion.
