# Stock Forensics Skill

An Agent Skill for reverse-engineering the events, expectations, and operating metrics that historically moved a public company's stock price.

[中文说明](README.zh-CN.md)

## Problem

Price charts show when a stock moved, but not which expectations changed or which evidence mattered. This Skill provides a repeatable way to connect material moves to dated sources and company-specific operating metrics without turning temporal coincidence into unsupported causality.

## What it does

Stock Forensics starts from major price moves and works backward to the evidence. It helps an agent:

- map material price swings to dated catalysts;
- identify the one or two operating metrics investors repeatedly price;
- compare reported results with contemporaneous expectations;
- trace how analyst questions and management tone evolved across earnings calls;
- produce an evidence-labeled report and an optional interactive HTML chart; and
- distinguish company facts, market data, analytical inference, and unresolved gaps.

The repository also includes an optional local Flask app that pulls Yahoo Finance data through `yfinance` and generates a basic chart. That app is a convenience layer, not a substitute for original filings, exchange notices, earnings calls, or source-checked research.

## Install the Skill

Clone the repository into a skills directory supported by your agent:

```bash
git clone https://github.com/Bill306/stock-forensics-skill.git
```

Then copy or symlink the repository folder so that the agent can discover its root `SKILL.md`. Exact installation paths vary by client.

## Usage

Invoke it with a request such as:

```text
Use $forensics to analyze the last three years of NVDA price drivers.
Separate verified catalysts from inference, identify the key metrics, and cite original sources.
```

## Input and output

Given a ticker, time range, and available source material, the Skill asks the agent to produce:

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

The validation script compiles the Python server and runs unit tests for ticker validation, output-path containment, and HTML/script escaping. It does not prove that Yahoo Finance is available or that a research conclusion is correct.

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
scripts/template_chart.html Reference chart template
scripts/validate.sh         Local validation entry point
tests/test_server.py        Safety-focused unit tests
```

## Security

See [SECURITY.md](SECURITY.md). Do not commit brokerage data, proprietary reports, API credentials, user portfolios, or generated client material.

## License

MIT License. Copyright (c) 2026 Bill306. See [LICENSE](LICENSE).
