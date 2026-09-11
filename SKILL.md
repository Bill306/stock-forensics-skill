---
name: forensics
description: Stock forensics — reverse-engineer what has historically moved a stock's price and valuation. Use whenever the user asks to analyze a stock, understand why it moved, research price drivers, do equity due diligence, or asks "what happened to [ticker]?" Also applies when the user provides sell-side reports, earnings data, or asks about key metrics. Even a casual "look into [ticker]" or "analyze [company]" should trigger this skill.
metadata:
  author: Bill306
  version: "1.0.0"
---

# Forensics — Know the Stock

The goal: **Identify the major drivers of a stock's price.**

The optional local web app requires Python 3.9 or newer. Research works best when web search and financial-data tools are available.

Understanding what drove a stock historically tells you what will drive it going forward. This is not about predicting — it's about reverse-engineering past price action to find the catalysts that actually matter.

## Rules of Thumb

These principles guide every forensics analysis:

1. **Start with the price chart.** What moved the stock price in the past? Let the chart tell you where to dig.
2. **Find the metrics investors care about.** Every stock has 1-2 key metrics — find them.
3. **Read sell-side reports for facts, not views.** Extract data points, consensus estimates, and industry facts. Ignore their ratings and price targets.
4. **Read news.** Map major events to price moves.
5. **Focus on big stories, not small volatilities.** A 2% daily move is noise. A 30% drawdown is signal.
6. **Identify the company's stage.** The stage determines which metrics matter and what drives the stock.
7. **Each market has its own characteristics — don't mix them up.** US guidance culture, Japan governance reform, HK dividend focus, China policy dominance — these are different games.

## The Forensics Process

### Step 1: Map the Price History

Pull the stock's price chart (1–2 years minimum) and identify the **big moves** — the 10%+ swings, not daily noise. For each major move, ask: what happened here?

Data sources to use:
- **Exchange, regulator, and company disclosures** for authoritative event and financial facts
- **yfinance** as a convenient, unofficial OHLCV and metadata adapter
- **TradingView MCP** for technical context and current market data, if available
- **Web search** for original news and disclosures around key dates

Cross-verify material price moves and corporate actions when possible. Record the source URL, publication date, data period, retrieval date, currency, adjustment basis, and unresolved gaps. Discrepancies may indicate stock splits, currency differences, time-zone boundaries, or data errors — investigate and note the reason.

Focus on **big stories, not small volatilities**. A 2% daily move is noise. A 30% drawdown over 3 months is signal.

### Step 2: Identify the Key Metrics

Every stock has 1–2 metrics that the market cares about most. Finding these is the whole game — and the key metrics often change as the company moves between stages (e.g. a company in crisis: "are they still losing money?" vs. the same company in recovery: "how fast is profit growing?").

**How to identify them:**
- Look at what metrics correlate with the biggest price moves
- Check what sell-side analysts highlight in their report titles and summaries
- Look at earnings call Q&A — what do investors keep asking about?
**Examples by sector:**
- Retail: Same-store sales growth (SSSG), guidance
- SaaS: Net revenue retention (NRR), ARR growth, Rule of 40
- Banks: Net interest margin (NIM), credit quality
- Semiconductors: Inventory levels, design wins, ASP trends
- E-commerce: GMV growth, take rate, user growth
- Restaurants (JP): Like-for-like (LFL) sales, customer count, overseas mix

### Step 3: Build the Earnings Forensics Table

Pull 6–8 quarters of data and construct a table:

| | Q1 | Q2 | Q3 | Q4 | Q1 | Q2 | Q3 | Q4 |
|---|---|---|---|---|---|---|---|---|
| **Key Metric (actual)** | | | | | | | | |
| **Key Metric (consensus)** | | | | | | | | |
| **Surprise %** | | | | | | | | |
| **Revenue** | | | | | | | | |
| **EPS (adjusted)** | | | | | | | | |
| **EPS Surprise %** | | | | | | | | |
| **Guidance (if applicable)** | | | | | | | | |
| **Stock move post-earnings** | | | | | | | | |

The surprise column is critical — it shows what the market didn't expect.

### Step 4: Read Sell-Side Reports (Facts Only)

When reading sell-side research, extract **facts**, not opinions:
- Consensus estimates and estimate revisions
- Industry data points and channel checks
- Management commentary and guidance specifics
- Competitive dynamics and market share data

Ignore their buy/sell ratings, price targets, and subjective views. The facts they compile are valuable; their conclusions are not.

If the user provides PDF reports, use whatever PDF extraction tools are available in the environment to parse them.

### Step 5: Generate the Interactive Forensic Price Chart

This is a key deliverable. Generate an interactive HTML chart that overlays price history with annotated catalyst events. Use `scripts/template_chart.html` as the reference template.

**Chart structure:**
- **Price line**: Weekly OHLCV data from yfinance, displayed as area + line chart
- **Event markers**: Color-coded dots on the price line, each representing a catalyst
- **Events panel**: Scrollable sidebar listing all events with date, price, move %, and description
- **Legend + filters**: Toggle event categories on/off
- **Range selector**: 1Y / 3Y / 5Y / ALL views
- **Summary stats**: Current price, period return, TTM return, event counts

**Event categories (color-coded):**

| Category | Color | What it covers |
|----------|-------|---------------|
| `scandal` | Red (#d4574a) | Governance issues, fraud, regulatory actions, PR crises |
| `earnings` | Amber (#d4a93e) | Quarterly results, guidance changes, annual results |
| `corporate` | Green (#7fa878) | M&A, IPO, management changes, restructuring, stock splits |
| `sellside` | Blue (#6b8fb8) | Analyst initiations, upgrades/downgrades, target changes |
| `narrative` | Purple (#a88bb3) | Macro themes, sector rotation, thematic shifts |

**How to build the chart:**

1. Read `scripts/template_chart.html` for the full HTML/CSS/JS structure
2. Replace the `priceData` array with weekly OHLCV data for the target stock
3. Replace the `events` array with researched catalyst events
4. Update the header (ticker, company name, subtitle)
5. Update summary stats (current price, returns, event counts)
6. Save the output HTML file to the user's working directory or preferred output location

The bundled local app is optional. Install its dependencies explicitly with `python3 -m pip install -r requirements.txt`; the app must never install packages on import. Run `python3 scripts/server.py` from the repository root. It binds to `127.0.0.1:3457` and writes to `./forensics-output` by default. Override these with `FORENSICS_HOST`, `FORENSICS_PORT`, and `FORENSICS_OUTPUT_DIR` only when the user intends to change the exposure or location.

**Event data format:**
```javascript
{
  date: 'YYYY-MM-DD',
  cat: 'earnings',          // scandal | earnings | corporate | sellside | narrative
  title: 'Q1 FY25 — Rev beat +8%',
  px: 150.25,
  mv: '+12%',               // Price move (1-day, multi-day, or YTD)
  mvDir: 'up',              // 'up' or 'down'
  desc: 'Revenue $4.2B vs $3.9B consensus...'
}
```

The chart should tell the complete story of the stock — someone should be able to look at it and immediately understand what drove every major price move.

### Step 6: Synthesize — The Forensics Report

Produce a structured text report alongside the chart:

```
# [TICKER] — Forensics Report

## Price History Summary
- [Date range analyzed]
- [Major moves identified with dates and magnitudes]

## Key Metrics That Move the Stock
- Primary: [metric] — because [evidence from price correlation]
- Secondary: [metric] — because [evidence]

## Earnings Forensics Table
[The table from Step 4]

## What the Market Cares About Right Now
- [Current narrative / theme]
- [Upcoming catalysts with dates]

## Market-Specific Notes
- [Any characteristics specific to this stock's market]
```

### Step 7: Current Debate — What Is the Market Arguing About Right Now?

Forensics tells you what *has* driven the stock. Current Debate tells you what *will* drive it next — the unresolved questions that analysts, investors, and management are wrestling with right now.

**It takes ~8 quarters to truly know a stock.** Reading one or two earnings calls gives you a snapshot. Reading 8–12 gives you the arc — how the narrative shifted, which concerns faded, which ones persisted, and what new ones emerged.

**How to identify the current debate:**

1. **Read the past 8–12 quarterly earnings call transcripts.** Focus on:
   - **Analyst Q&A section** — this is where the real concerns surface. What questions keep coming up? What new questions appeared recently?
   - **Management tone shifts** — are they getting more defensive on a topic? More confident? Evasive?
   - **The marginal change in questions** — if analysts asked about margins for 6 quarters straight, then suddenly shift to asking about market share, that's a signal. The shift in focus *is* the debate moving.

2. **Cross-reference with your forensics.** Your price history and key metrics work tells you what drove the stock before. The current debate tells you what could drive it next. Where do they overlap? Where do they diverge?

3. **Layer in sell-side reports and common sense.** Sell-side research often frames the debate explicitly ("the bull case is X, the bear case is Y"). Combine this with your own judgment — does the debate make sense given what you found in forensics?

4. **Distill to the true debate.** Strip away noise and find the 1–2 questions that actually matter for the stock price. Not "will revenue grow?" but the specific, falsifiable question that bulls and bears disagree on.

**Output format:**

```
## Current Debate — [TICKER]

### The True Debate
[1-2 sentences: the core question bulls and bears disagree on]

### Earnings Call Evolution (past 8 quarters)
| Quarter | Dominant analyst questions | Management tone | New concerns |
|---|---|---|---|
| [Q] | [topics] | [confident/defensive/evasive] | [any new issues raised] |

### Bull vs Bear
- Bull case: [what bulls believe, with evidence]
- Bear case: [what bears believe, with evidence]
- What would resolve it: [specific data point or event]
```

## Market-Specific Characteristics

Each market has its own quirks. Don't apply one market's logic to another.

**US Stocks:**
- Guidance is extremely important — often matters more than the actual quarter
- Pre-market earnings moves are driven by guidance + key metric surprise
- Sell-side consensus is well-established; surprise vs consensus drives price

**Japan Stocks:**
- Corporate governance reforms (TSE PBR >1 push) drive re-ratings
- Cross-shareholding unwinds create supply pressure
- Shareholder return policy (buybacks, dividends) increasingly matters
- Overseas revenue mix as a growth narrative

**Hong Kong Stocks:**
- Dividend yield and payout ratio matter more
- Southbound flow (mainland money) is a major driver
- Less sell-side coverage → more information asymmetry

**A-Shares (China):**
- Policy and regulatory signals dominate
- Retail sentiment and momentum matter more
- Different accounting standards and disclosure norms

**European Stocks:**
- Organic growth vs FX impact distinction matters
- Regulatory environment varies by country

## Examples

### FIVE (Five Below, US)
- **Key metric**: SSSG — THE metric for US discount retail
- SSSG went negative (-4% to -5%) → stock crashed to ~$52
- SSSG recovered with big EPS surprises (+278%) → stock rallied back
- **Lesson**: Guidance + SSSG surprise = price driver
- **Current Debate**: Can comps stay positive? Can revenue accelerate? Can margins keep expanding? → The *true* debate is comps — because without positive SSSG, revenue growth is just new store openings and margin expansion hits a ceiling. Comps are the gatekeeper.

### FLC / 3563.T (Food & Life Companies, Japan)
- **Key metric**: Like-for-like (LFL) monthly sales, overseas revenue mix
- Scandal cluster (2022–2023): false advertising → sushi terrorism → -30% from peak
- Recovery driven by: decisive crisis response, 40th anniversary campaigns, overseas expansion
- FY25 breakout: OP +58.9%, stock nearly doubled
- **Lesson**: For JP consumer stocks, governance events (scandal/reform) can dominate fundamentals for quarters

### Samsung Electronics (005930.KS, Korea)
- **Key metric**: Memory division operating profit, HBM qualification status
- Trough (2023): Memory losing money → stock bottomed at ~53,000
- Recovery (2024): Memory returns to profit, EPS surprise +94% → rally begins
- Setback (mid-2024): HBM3E fails Nvidia qualification → stock -40% from peak
- Breakout (2025–2026): HBM3E qualified, DRAM ASP +30%, Q1 2026 OP 57.2T → stock 6x from trough
- **Lesson**: The key metric shifted at each stage — from "are they losing money?" to "how fast is profit recovering?" to "can they qualify HBM?" Know what stage the company is in and what the market cares about *right now*.

## Practical Tips

- Start with the price chart. Always. Let the chart tell you where to dig deeper.
- Cross-reference multiple sources — don't rely on a single sell-side report.
- Time your analysis around earnings dates — that's when the most information is revealed.
- The interactive chart is the primary deliverable — it should be self-contained and tell the full story.

## Boundaries and Verification

- This Skill supports research and explanation, not personalized investment advice, order placement, or portfolio action.
- Treat yfinance and search snippets as discovery layers. Prefer original filings, exchange notices, company releases, and full source pages for claims that drive the conclusion.
- Do not invent consensus values, price reactions, catalyst dates, current debates, or chart functionality. Mark missing fields as unavailable.
- Separate event date, publication date, financial reporting period, and retrieval date.
- Before calling an HTML chart interactive, open it and verify that the data arrays initialize and the filters, range buttons, event list, and chart markers respond.
- The optional Flask app is for trusted local use. It has no authentication and should not be exposed publicly without an independent security review and access controls.
