# Event windows and returns

Use actual daily exchange-session closes: `[{"d":"YYYY-MM-DD","c":100.0}, ...]`. Weekly bars are for overview, never event calculations. The helper validates positive finite values and unique dates; it cannot detect weekly records disguised as daily data or omitted sessions. Confirm frequency/completeness from the source and retain currency, timezone and adjustment metadata.

Translate verified timestamps to exchange-local dates. Classify actual exchange opening/closing times, including holidays and shortened sessions; do not apply US trading hours to other markets.

| Timing | Baseline | First response session |
|---|---|---|
| `before-open` | Previous close | First session on/after event date |
| `after-close` | Last close on/before event date | Next session |
| `during-session` | Previous close | Event session, including pre-event information |
| `unknown` | Previous close | First session on/after event date; descriptive window only |

Weekend events within coverage use adjacent actual sessions. The 1/5/20-session windows end at the first/fifth/twentieth response close. Missing baseline, incomplete horizon or event outside supplied coverage returns unavailable. Never fill with nearest endpoints or shorten a window without changing its label. Completeness between endpoints remains the caller's responsibility.

Daily closes cannot isolate a call from the release, a particular Q&A answer or a concurrent disclosure. Unknown timing caps attribution below `supported_driver`; individual-remark attribution needs verified intraday prices and original timestamps. Report timing sensitivity instead of choosing the best-looking window.

- Stock return `%` = `(end / baseline - 1) * 100`.
- Benchmark uses the exact same baseline/end dates; a missing endpoint leaves adjustment unavailable.
- For attribution, compare a broad-market benchmark and a relevant industry/peer benchmark when both are available. Use the helper's repeatable `--benchmark SYMBOL=JSON` option or call `event_window` once per series; preserve each series' source and role. Do not choose a reference based on which tells the preferred story.
- Benchmark-adjusted return `pp` = stock cumulative return minus benchmark cumulative return. This is descriptive subtraction, not a fitted abnormal-return model or significance test.
- A fitted market model, if warranted, uses pre-event estimation data excluding the event window; state factors, period and diagnostic limits separately.
- EPS surprise `%` = `(actual - estimate) / abs(estimate) * 100`. Zero estimates are unavailable; near-zero estimates can yield misleading percentages. Retain absolute gaps and accounting basis.
- 12% growth vs 10% expectation differs by **2 percentage points**, distinct from relative percentage surprise.

Use broad-market and relevant industry references where available and report both rather than selecting the favorable comparison. Pre-announcement drift, FX, anticipated information and concurrent news remain competing explanations. Longer windows frequently contain subsequent information.

An ETF's return is a market/industry price benchmark, not evidence of fund creations, redemptions or stock-level buying/selling. Use separately sourced dated flow data before making a fund-flow claim.

Trailing-year return uses the last data date rather than today's clock; insufficient baseline history is unavailable. State whether the series is price-only or split/dividend-adjusted. An adjusted historical close is not an executable historical price.

## Analysis-period selection

Use the user's exact dates or requested lookback when provided. Otherwise default to the five years ending on the most recent completed exchange session. Report the actual first and last sessions because weekends, holidays, listing dates and provider coverage can shift the calendar boundary. Keep the preceding common session close as the baseline for an in-window first-day return, but do not count that baseline session as part of the requested window. Use the same window for the stock, benchmarks, move screen and news census. The latest 6–8 earnings may form a separately labeled fundamental sample within the wider price window.

Method reference: [MacKinlay, Event Studies in Economics and Finance](https://www.bu.edu/econ/files/2011/01/MacKinlay-1996-Event-Studies-in-Economics-and-Finance.pdf). Descriptive returns do not establish causality.
