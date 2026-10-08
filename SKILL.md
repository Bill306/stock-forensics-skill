---
name: forensics
description: Investigate historical stock-price drivers, earnings reactions, or information revealed in a call/transcript. Use when the user asks why a stock moved, which metrics were priced, or whether a disclosure contributed to a move. Supports evidence-led attribution and falsifiable current debates.
metadata:
  author: Bill306
  version: "1.6.0"
---

# Forensics — Know the Stock

Identify what information changed expectations, how it could change earnings or valuation, and whether the price reaction supports that explanation. Historical drivers are hypotheses to re-test as the company changes stage, not predictions.

## Choose the task

- **Price drivers:** start with the chart, then test catalysts against the full event set.
- **Earnings reaction:** compare actual results, guidance and key metrics with pre-publication expectations.
- **Call/transcript attribution:** read [references/transcript-forensics.md](references/transcript-forensics.md). Analyze supplied text, PDF or subtitles directly. Route media through available transcript tools, retaining original evidence locations; do not duplicate ASR engines or claim unavailable transcripts were read.
- **Company news and market context:** read [references/news-and-market-context.md](references/news-and-market-context.md). Search both from price moves to news and from material company developments to prices, including product plans, business actions and public reaction. Compare broad-market and relevant industry benchmarks before assigning a company-specific explanation.
- **Current debate:** track changes in questions and disclosed metrics, then identify the disagreement, next observable evidence and falsifier. Use available quarters and disclose coverage; a fixed quarter count does not guarantee understanding.

For broad company research, apply this method to the requested price-driver component. Accounting-quality/fraud investigations need their own accounting procedures; price attribution does not establish fraud.

## Choose the analysis period

Honor a user-specified lookback or exact start/end dates. If none are given, use the five years ending on the most recent completed exchange session and state the actual start and end sessions. Offer a shorter or longer lookback (such as 1, 2, 3 or 10 years), all available history, or custom dates when period choice would help; do not block a useful first pass while waiting for a preference. Retrieve the preceding common trading-session close when needed to calculate the first in-window return. Apply the selected dates consistently to stock prices, benchmarks, move screening and the news/event census. Historical earnings tables may focus on the most recent 6–8 available quarters, but disclose that narrower fundamental sample.

## Evidence and timing

Prefer company, exchange and regulator disclosures for facts. Read full original news and source sell-side data, separating estimates, channel-check claims and opinions. Ratings/targets can themselves be candidate events; they are not proof of value or causation. yfinance is an unofficial data adapter.

Record each source's URL/local path, publication time, data/reporting period, retrieval date and evidence locator. Separate reporting-period end, announcement and call times. Use the exchange timezone and actual sessions. Preserve currency, price-adjustment basis, EPS/accounting basis, metric units and historical consensus cutoff. Missing fields stay explicit; never substitute today's estimates for historical expectations.

For A-share research, read [references/a-share-research.md](references/a-share-research.md) for local disclosures, standalone-quarter accounting and investor-question comparisons. For any market, validate corporate actions and price-provider seams before screening moves; see [references/event-windows.md](references/event-windows.md).

## Investigation

1. **Map prices and coverage.** Use the requested period; absent a period, use five years through the latest completed exchange session. State exact first/last dates and price-source coverage. Screen large moves against the stock's own history, a broad-market benchmark and a relevant industry/peer benchmark where available. A 10% threshold is optional, not universal. Retain unexplained moves.
2. **Build a dated event census in both directions.** For screened price moves, search contemporaneous company, industry, macro and sell-side news. Independently review material company developments throughout the selected period, even when they did not cross the price threshold: planned features/products, launches, pricing, customer/partner changes, operational actions, controversies and company responses. Use company blogs, product channels and original reporting as well as filings and calls; include dated public feedback where relevant. Separate preview, testing, rollout, public reaction and response, linking earlier disclosures and later updates. Routine notices and share-sale eligibility are also candidates, but eligibility does not prove selling. Keep disclosure and market-reaction dates separate, and retain quiet events and contradictory price reactions. Report news-search coverage and mapped versus unmatched screened dates separately from event counts; a sourced event is not automatically an explained move. Follow the company-news workflow in [references/news-and-market-context.md](references/news-and-market-context.md).
3. **Test metric candidates.** Use sector knowledge, calls and company stage. For each candidate retain supporting events, contradictory cases, stage applicability and a falsifier. Rank the best-supported one or two metrics only after this check; leave rankings unresolved when evidence is weak.
4. **Compare prior expectations.** For 6–8 quarters when available, tabulate period, announcement time, metric actual, prior expectation/source/cutoff, surprise, revenue, comparable EPS, guidance delta, stock and benchmark reactions. Show absolute gaps and denominator limits for zero/near-zero or negative estimates. Growth-rate surprises use percentage points. Missing consensus stays unavailable.
5. **Calculate reactions.** Read [references/event-windows.md](references/event-windows.md) for timing, 1/5/20-session windows, broad/industry comparisons, exact benchmark endpoints and missing-data rules. EPS surprise is never a stock-return field. Longer windows collect other information and do not themselves increase causal confidence.
6. **Attribute conservatively.** Test shared market/industry moves before company-specific explanations. Link each candidate to its publication time, novelty, prior expectation, earnings/valuation mechanism and observed reaction. For company news, assess public reaction, operating impact and stock-price contribution separately: criticism is not measured churn, and management's explanation of a KPI is not proof of a price driver. Review company, macro and industry news, peers, FX, policy, concurrent disclosures and anticipated information; explain conflicting signs. A broad or sector ETF is a return benchmark, not proof of investor flows. Call flows only when separate flow data support them. Distinguish facts from inference.
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

Expose sources/locators, timing, uncertainty and labeled return windows in chart annotations. Keep unresolved moves. Use a company logo from a verified official source when available, recording its URL and retrieval date. Check its contrast on the chosen background; embed the original asset for offline use and use a labeled text fallback if unavailable. Verify actual interactions before describing a chart as verified. Compare raw and benchmark returns on matching endpoints and adjustment conventions.

When an interactive HTML explorer is requested, build a single self-contained file. Embed price and event JSON in the page; make each event marker clickable, with a detail panel showing disclosure date, market-reaction date, timing, benchmark-relative returns, source link and attribution grade; include an event list with a documented/unexplained filter; default to the five-year view with selectable 1/2/3-year, all-history and custom-date ranges; label benchmark-relative returns with % (not "pp") when the user prefers percent notation; embed images such as company logos as base64 data URIs so the file works offline over file://. When transcript coverage exists, add a question-focus migration section, labeled sell-side only when the source supports that participant identity: for each available quarter, summarize the marginal change in analyst question themes qualitatively, disclose which quarters are covered, and never present theme summaries as frequency statistics.

For generated explorers, test marker-to-detail selection, date/range and benchmark changes, news filters, question expansion and earnings links. Related-event navigation must reveal an event hidden by the current filters. Check empty results, invalid dates, unavailable windows, visible logos and console errors. Offer only ranges actually supported by downloaded data, or label a separate retrieval action.

For a full company-news review, add a product/business-actions/public-reaction timeline when evidence is available, including material events below the move threshold. Let users filter themes and click through to facts, proposed operating mechanisms, evidence limits, sources and comparable return windows. Link previews, rollouts, public responses and later operating disclosures; clearly label later evidence as hindsight. Do not imply these research annotations are collected or rendered automatically by the bundled app.

The optional app requires Python 3.9+, Flask and yfinance. Explicitly install `requirements.txt` when needed, then run `python3 scripts/server.py` from the repo root. Defaults: `127.0.0.1:3457`, output `./forensics-output`, and a five-year chart view. The chart lets users select other ranges, including 1, 2, 3 or 10 years and all available history. It fetches daily adjusted closes, provider announcement dates, analyst changes and splits, reports source gaps and can add validated evidence through the `/api/generate` JSON `evidence` field. Provider events remain unverified attribution. It does not collect company or market news, industry benchmarks or fund-flow data; research and attach those sources separately.

`scripts/template_chart.html` is a legacy illustration with historical sample data, not a general renderer. For arbitrary tickers use the app renderer or generate a chart from validated evidence and supplied prices. Examples are preserved in [references/legacy-examples.md](references/legacy-examples.md); verify claims before reuse.

## Verification

Run `scripts/validate.sh` after code changes. Check EPS beats with falling prices, stock/benchmark moves together, unknown timing, missing expectations and out-of-coverage windows. Missing fields must stay missing, ineligible grades must fail validation, and no future close may substitute for an earlier baseline. Passing tests verifies mechanics, not a live provider or a research conclusion.
