# News and market context

Use the user-selected analysis dates for the news and event census; if no period is specified, default to the five years ending on the last completed trading session. Include exact first/last covered sessions in the report and do not imply that a partial source search is exhaustive.

Use this workflow when explaining a material rise or fall. Price co-movement and a headline on the same date are screening clues, not causal proof.

## Search company news in both directions

A full price-driver review needs two complementary passes:

- **Price to news:** around each screened move, inspect a bounded pre/post-event window for candidate disclosures and competing explanations. State the window and expand it when a sourced earlier preview or continuing controversy requires it.
- **News to price:** independently build a timeline of material company developments across the analysis period, then inspect their returns even if no price threshold was crossed. Select events for business relevance before seeing their returns. Preserve quiet and opposite-direction reactions to avoid selecting only supportive stories.

Do not stop at earnings releases or regulatory filings. Adapt the search to the company's business and important regions/languages:

| News family | Examples to investigate | Possible operating link to test |
|---|---|---|
| Product and service | Roadmap, feature preview, beta, launch, rollout, redesign, discontinuation | Adoption, engagement, retention, customer value, development cost |
| Pricing and monetization | Price/package changes, paywalls, trials, advertising, channel terms | Conversion, mix, churn, revenue per customer, margins |
| Commercial development | Customer wins/losses, partnerships, distribution, geographic expansion | Demand, volume, concentration, acquisition cost |
| Operations and organization | Capacity, supply disruption, hiring/layoffs, automation, leadership or strategy changes | Delivery, quality, cost, execution risk |
| Reputation and controversy | Complaints, backlash, boycotts, service outages, recalls, allegations, legal/regulatory developments | Trust, acquisition, renewals, remediation cost, risk premium |
| Company response | Clarification, apology, campaign change, rollback, remediation, subsequent KPI disclosure | Whether the proposed mechanism actually appeared or reversed |

Search official product blogs, release notes, company/executive public posts, conference announcements and customer/partner statements alongside original reporting. Dated user discussions, reviews and archived posts can locate public reaction; allegations and self-reports remain attributed claims. A roadmap is not a shipped product, a phased beta is not a full rollout, and public excitement or criticism is not realized revenue or churn.

## Separate the stages of a news story

Record each relevant stage as its own dated information event: earliest located preview/report, confirmed plan, test, launch/rollout, public reaction, company response and later operating evidence. Some stages may be absent or occur in a different order; do not invent a complete sequence. Identify both the event/effective date and the source publication date, plus time precision and applicable market session.

The earliest source found is not necessarily the first public disclosure. Search backward before claiming novelty; mark unresolved first-disclosure timing. A revised blog, today's product page or a recap cannot establish what was available on a historical date without supporting dated evidence. A later management response may corroborate a mechanism but must not be backdated into what investors knew earlier. Distinguish archived/hidden social posts from confirmed deletion and record access gaps.

## Evaluate three separate claims

1. **Public reaction:** what was actually observed, where and when? Record sampled posts/reviews, dated original reporting and contrary views. Do not infer population sentiment or historical intensity from today's likes, a few selected posts or syndicated copies. Quantified sentiment needs a dated sampling method, denominator and coverage.
2. **Operating impact:** explain the proposed path to acquisition, usage, conversion, renewals, orders, cost or risk. Label evidence as unavailable, management-reported or independently observed; retain KPI definitions, affected cohorts/regions, lags and alternative explanations. A company statement acknowledging an effect is evidence of its explanation, not independent causal verification. Preserve cases where complaints coexist with improving aggregate metrics.
3. **Stock-price contribution:** test timing, novelty, prior expectations, matching broad/industry returns and concurrent information under the normal attribution grades. An operating effect does not automatically establish a price effect. Unknown timing, product announcements overlapping earnings, or criticism followed by positive returns must remain visible.

For each story, state the next measurable observation and falsifier. Treat positive and negative news symmetrically. Keep 1/5/20-session windows descriptive; longer windows may include a response, earnings or unrelated news. Where timing is unknown and material, show sensitivity to alternative session alignment instead of choosing the window that fits the narrative.

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

Company-generated items count, including routine ones: earnings-date notices, prospectus supplements and share-sale eligibility, and company-published research or product announcements. Routine informational items adjacent to a move stay `coincident_only` unless novelty, timing and mechanism support more; unknown timing always excludes `supported_driver`. Share-sale eligibility is not evidence that holders actually sold. Track census completeness explicitly — for example, "26 of 46 screened dates mapped to a sourced event; 20 remain unmatched" — so unexplained dates stay visible. Separately report the number of reviewed company-news events, covered themes/dates/channels, and price-attribution grades. Adding news below the move threshold need not improve screened-date coverage, and matched dates must not be relabeled as causally explained.

Prefer the original filing, company release, exchange notice or news report. Capture a headline's URL, publisher, exact publication time and timezone when available, reporting period, retrieval date and the first public disclosure. Distinguish event time from the later publication time of a transcript or recap. If only the date is known, preserve that precision and leave the exact time unknown.

Link follow-up events to their first public source. A preliminary update can make the same fact already known before the formal earnings release; a later release may add new figures or forward guidance. Grade novelty for each claim, not for the whole earnings date. Questions from analysts and claims repeated by secondary outlets are not independent confirmation.

## Attribute without forcing a story

For each move, record the candidate headline/event, the benchmark context, the company-specific mechanism if any, whether the information was new, price-window evidence and competing explanations. Label the screen as:

- **Explained candidate:** a dated, source-backed disclosure has a plausible mechanism and event-window evidence consistent with contribution; keep the normal attribution grade and caveats.
- **Multiple candidates:** more than one material company, sector or macro event overlaps; retain each and do not allocate a causal share without additional evidence.
- **Unexplained:** the available sources do not establish a material candidate. Keep the move in the report.

Include quiet dates and earnings events as controls. Record search scope and source failures so “no news found” does not read as “no news existed.” Do not require an RSS/API integration: use the available browser, exchange/regulatory sources and reputable publishers, then preserve links and timestamps in the evidence record.

## Keep a search audit

For each screened date retain the searched pre/post window, actual queries or channels, retrieved candidate links, access failures and review status. Distinguish **not yet searched**, **searched with no reliable candidate**, and **candidate located but attribution unresolved**. A price-only recap can corroborate a move without supplying a catalyst. A later article can support chronology but cannot establish that its explanation was known earlier.

Report screened dates, dates with a sourced candidate, dates with plausible/supported attribution, and independently reviewed company-news events as separate counts. Multiple stories on one day do not increase date coverage. Do not mark all grey/unmatched dates as searched unless the search log supports it.

## Structured fields

Use `event_type` to distinguish `company_news`, `company_disclosure`, `industry_news`, `macro_news`, `sellside`, and separately sourced `fund_flow`. Use `first_disclosure_event_id` and `supersedes_event_ids` for information chronology. Keep chart `category` compatible with existing chart consumers. Store each broad-market and industry benchmark in `benchmark_comparisons` with its symbol, role, stock-price source, benchmark-price source and matching event-window returns. Read [evidence-schema.md](evidence-schema.md) for validation details.

For richer company-news reports, keep topic/stage, related event IDs, first-disclosure uncertainty, facts versus claims, public-reaction evidence, operating-impact evidence/status, proposed mechanism, confounders and falsifier as report annotations or optional extensions. These do not replace required source/event/factor fields. The current helper does not validate these extensions or guarantee that the optional app renders them; review them and verify generated chart interactions separately.

## Review before delivery

- A product launch coincides with earnings: retain both; do not assign the whole move to the feature.
- A controversy has no threshold-crossing decline: retain the news and measured return rather than omitting it or forcing a selloff story.
- Management later acknowledges acquisition friction: identify the later disclosure date and distinguish reported operating impact from price attribution.
- Users dislike a change while management reports better conversion: retain both and ask which cohorts and metrics can resolve the disagreement.
