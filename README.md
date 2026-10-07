# Stock Forensics Skill

An Agent Skill for reverse-engineering the events, expectations, and operating metrics that historically moved a public company's stock price.

[中文说明](README.zh-CN.md)

## Problem

Price charts show when a stock moved, but not which expectations changed or which evidence mattered. This Skill provides a repeatable way to connect material moves to dated sources and company-specific operating metrics without turning temporal coincidence into unsupported causality.

## What it does

Stock Forensics researches both from price moves to news and from material company developments to price reactions, including quiet events. It helps an agent:

- map material price swings to dated catalysts;
- separate broad-market and industry moves from company-specific news candidates;
- preserve news timestamps and link later updates to earlier disclosures;
- investigate product plans, business actions and public reaction beyond earnings, separating sentiment, operating impact and price attribution;
- identify the one or two operating metrics investors repeatedly price;
- compare reported results with contemporaneous expectations;
- trace how analyst questions and management tone evolved across earnings calls;
- produce an evidence-labeled report and an optional interactive HTML chart; and
- distinguish company facts, market data, analytical inference, and unresolved gaps.

The repository also includes an optional local Flask app that pulls Yahoo Finance data through `yfinance` and generates a basic chart. That app is a convenience layer, not a substitute for original filings, exchange notices, earnings calls, or source-checked research.

## v1.5.0 — Company news beyond earnings

The research workflow now requires both price-to-news and news-to-price passes for a full review. It covers product previews and launches, pricing, customer/partner changes, operations, public controversies and company responses. Timelines distinguish plans, testing, rollout, public feedback and later operating evidence; quiet events and conflicting reactions remain visible. Reports assess public reaction, operating impact and stock-price contribution separately, with explicit source and sampling limits. Interactive reports can expose these story stages and evidence alongside the price chart. These are agent research/reporting instructions; the bundled app still does not automatically collect news or sentiment. See the [company-news workflow](references/news-and-market-context.md).

## v1.3.0 update

The local upgrade adds transcript evidence/expectation checks, four attribution grades, counterexamples, explicit company/industry/news event types and first-disclosure links, plus 1/5/20-session comparison against multiple named benchmarks. The chart app uses daily adjusted closes and provider announcement dates instead of fiscal-quarter dates, keeps EPS surprise separate from price returns, and displays source gaps. News, industry benchmarks and actual fund-flow evidence still need to be researched and supplied separately; ETF returns are not flows. This local version adds a five-year default period and selectable chart windows. GitHub publication is a separate step.

## v1.4.0 update

The local upgrade extends the news/event census: company-generated items — including routine earnings-date notices, prospectus supplements or share-sale eligibility disclosures, and company-published product or research announcements — are candidate events when they coincide with screened moves. They are graded conservatively (at most `coincident_only` when timing or content evidence is thin), disclosure and market-reaction dates are recorded separately, share-sale eligibility is not treated as evidence of selling, and census completeness is reported as mapped versus unmatched screened dates. It also documents the self-contained interactive HTML explorer pattern: clickable event markers with a detail panel, a documented/unexplained event filter, a default five-year view with selectable ranges, benchmark-relative returns labeled in %, base64-embedded assets for offline viewing, and a qualitative sell-side question-focus migration section built only from available transcripts with coverage disclosed. GitHub publication is a separate step.

The transcript helper validates analyst-authored JSON; it does not transcribe media, read calls, verify source truth or automatically identify price drivers.

```bash
python3 scripts/transcript_forensics.py validate --input examples/transcript-only.json
python3 scripts/transcript_forensics.py price-window --prices examples/daily-prices.json --benchmark examples/daily-benchmark.json --event-date 2026-09-30 --timing after-close
python3 scripts/transcript_forensics.py price-window --prices examples/daily-prices.json --event-date 2026-09-30 --timing after-close --benchmark QQQ=examples/daily-benchmark.json --benchmark XLK=examples/daily-industry-benchmark.json
python3 scripts/transcript_forensics.py export-events --input examples/transcript-only.json --prices examples/daily-prices.json
```

Examples are fictional. JSON `--output` refuses to overwrite existing files. See [evidence contract](references/evidence-schema.md), [window conventions](references/event-windows.md), [call workflow](references/transcript-forensics.md) and [news/market-context workflow](references/news-and-market-context.md). A valid JSON record verifies consistency and attribution eligibility, not the truth or causality of a conclusion.

To include reviewed annotations in the app, send `{"symbol":"TICKER","evidence":{...}}` to `/api/generate`. Evidence must match the ticker and validate first. The chart exposes timing, grades and source/quote locations. Provider consensus without a verified cutoff cannot support the strongest attribution grade.

## Install the Skill

Clone the repository into a skills directory supported by your agent:

```bash
git clone https://github.com/Bill306/stock-forensics-skill.git
```

Then copy or symlink the repository folder so that the agent can discover its root `SKILL.md`. Exact installation paths vary by client.

## Usage

If a request gives no analysis period, the Skill defaults to the five years ending on the most recent completed exchange session. Users can request another lookback or exact start/end dates. The chart defaults to 5Y and offers 1Y, 2Y, 3Y, 10Y and all available history.

Invoke it with a request such as:

```text
Use $forensics to analyze NVDA price drivers. Use the default five-year window unless I specify another period.
Separate verified catalysts from inference, identify the key metrics, and cite original sources.
```

## Input and output

Given a ticker, an optional time range, and available source material, the Skill asks the agent to produce:

1. a price-history summary focused on material moves;
2. an earnings-forensics table;
3. the primary and secondary metrics that appear to move the stock;
4. a current bull-versus-bear debate with falsifiable resolution points;
5. market-specific context; and
6. an optional self-contained HTML catalyst chart.

Illustrative input:

```text
Analyze 700.HK from 2023 through 2025. Explain the largest moves, show which metrics mattered,
and mark any missing consensus data as unavailable.
```

Illustrative output shape:

```text
Price move: [date range and magnitude]
Verified catalyst: [event with original source and publication date]
Primary metric: [metric and evidence]
Interpretation: [clearly labeled inference]
Data gap: [unavailable or unresolved item]
```

The example describes the structure only; it is not a claim about Tencent or any other security.

## Optional local chart app

Python 3.9 or newer is recommended.

There is no live demo. Run the local app below to use the ticker search and chart generator on your own machine.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 scripts/server.py
```

Open `http://127.0.0.1:3457`. Generated files are written to `./forensics-output` by default.

Optional environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `FORENSICS_HOST` | `127.0.0.1` | Bind address |
| `FORENSICS_PORT` | `3457` | Local HTTP port |
| `FORENSICS_OUTPUT_DIR` | `./forensics-output` | Generated chart directory |

The app has no authentication. Keep it on localhost unless you independently add access controls and complete a deployment security review.

## Validate

```bash
./scripts/validate.sh
```

The validation script compiles the helpers/server and tests safety, session alignment, EPS/return separation, benchmark endpoints, missing-data handling, evidence eligibility and the chart-generation API with synthetic data. It does not prove that Yahoo Finance is available or that a research conclusion is correct.

## Data and research limitations

- `yfinance` is an unofficial data adapter. Availability, field definitions, adjustments, and historical coverage can change.
- Consensus estimates and post-earnings reactions require contemporaneous, source-appropriate data; missing values must not be invented.
- Price-event alignment suggests hypotheses but does not by itself establish causality.
- Generated HTML loads Google Fonts when online; the chart remains usable with local fallback fonts.
- The quality of the analysis depends on the quality and completeness of the supplied sources.
- Outputs are research material, not personalized investment advice or trade execution.

## Repository layout

```text
SKILL.md                    Agent instructions
agents/openai.yaml          UI metadata and invocation policy
scripts/server.py           Optional local chart app
scripts/forensics_core.py    Evidence checks and deterministic return windows
scripts/transcript_forensics.py JSON CLI (no data downloads or LLM calls)
scripts/template_chart.html Reference chart template
scripts/validate.sh         Local validation entry point
references/                 Call workflow, evidence contract, return conventions
examples/                   Fictional input fixtures
tests/                      Safety and research-mechanics regression tests
```

## Security

See [SECURITY.md](SECURITY.md). Do not commit brokerage data, proprietary reports, API credentials, user portfolios, or generated client material.

## License

MIT License. Copyright (c) 2026 Bill306. See [LICENSE](LICENSE).
