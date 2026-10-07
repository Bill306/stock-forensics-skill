# News and market context

Use the user-selected analysis dates for the news and event census; if no period is specified, default to the five years ending on the last completed trading session. Include exact first/last covered sessions in the report and do not imply that a partial source search is exhaustive.

Use this workflow when explaining a material rise or fall. Price co-movement and a headline on the same date are screening clues, not causal proof.

## Separate shared moves from company-specific candidates

1. Calculate the stock's return on matching dates, then compare it with a broad-market ETF/index and, when useful, a liquid industry ETF or peer index. Use the same currency, adjusted-price convention and exact window endpoints. State which benchmark answers which question; do not select one after seeing which gives the preferred narrative.
2. If the stock and benchmarks moved together, report that shared context. If the stock diverged, describe the residual as a screening clue only. Simple stock-minus-ETF returns are not factor-model alpha and do not identify who bought or sold.
3. ETF prices show market performance, not ETF creations/redemptions or flows into the stock. Call “fund flows” only when a dated, source-backed flow dataset supports that claim. Otherwise say “broad-market/industry move” or “relative price move.”

## Build an information timeline

For each material move date and its event window, search a bounded window before and after the move for:

- company investor-relations releases, regulatory filings, guidance updates, earnings calls and product/management announcements;
- reputable original reporting on the company, its competitors or its industry;
- macro, policy, rates or market-wide news that plausibly affected the stock or benchmark;
- sell-side changes as a separate opinion/positioning candidate, not company fact.

Company-generated items count, including routine ones: earnings-date notices, prospectus supplements and share-sale eligibility, and company-published research or product announcements. When such an item coincides with a screened move but its exact publication time is unknown or its content is informational rather than new financial information, keep it as a `coincident_only` candidate with the caveat visible. Share-sale eligibility is not evidence that holders actually sold. Track census completeness explicitly — for example, "26 of 46 screened dates mapped to a sourced event; 20 remain unmatched" — so unexplained dates stay visible.

Prefer the original filing, company release, exchange notice or news report. Capture a headline's URL, publisher, exact publication time and timezone when available, reporting period, retrieval date and the first public disclosure. Distinguish event time from the later publication time of a transcript or recap. If only the date is known, preserve that precision and leave the exact time unknown.

Link follow-up events to their first public source. A preliminary update can make the same fact already known before the formal earnings release; a later release may add new figures or forward guidance. Grade novelty for each claim, not for the whole earnings date. Questions from analysts and claims repeated by secondary outlets are not independent confirmation.

## Attribute without forcing a story

For each move, record the candidate headline/event, the benchmark context, the company-specific mechanism if any, whether the information was new, price-window evidence and competing explanations. Label the screen as:

- **Explained candidate:** a dated, source-backed disclosure has a plausible mechanism and event-window evidence consistent with contribution; keep the normal attribution grade and caveats.
- **Multiple candidates:** more than one material company, sector or macro event overlaps; retain each and do not allocate a causal share without additional evidence.
- **Unexplained:** the available sources do not establish a material candidate. Keep the move in the report.

Include quiet dates and earnings events as controls. Record search scope and source failures so “no news found” does not read as “no news existed.” Do not require an RSS/API integration: use the available browser, exchange/regulatory sources and reputable publishers, then preserve links and timestamps in the evidence record.

## Structured fields

Use `event_type` to distinguish `company_news`, `company_disclosure`, `industry_news`, `macro_news`, `sellside`, and separately sourced `fund_flow`. Use `first_disclosure_event_id` and `supersedes_event_ids` for information chronology. Keep chart `category` compatible with existing chart consumers. Store each broad-market and industry benchmark in `benchmark_comparisons` with its symbol, role, stock-price source, benchmark-price source and matching event-window returns. Read [evidence-schema.md](evidence-schema.md) for validation details.
