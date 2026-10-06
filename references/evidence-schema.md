# Evidence contract v1.2

Required top-level fields: `ticker`, offset-bearing ISO `analysis_as_of`, and arrays `sources`, `events`, `factors`. IDs are unique within each array. The document is analyst-authored; helpers do not generate semantic conclusions.

| Record | Fields |
|---|---|
| Source | `id`, `url_or_path`, `published_at`, `retrieved_at`, `data_period`; explicitly use `unknown` where appropriate |
| Event | `id`, exchange-local `date`, offset-bearing `published_at` or `unknown`, `timing`, `title`, `source_id`; optional `event_type`, chart `category`, first-disclosure link and benchmark comparisons |
| Factor | `id`, `event_id`, `metric`, `novelty`, `evidence`, `expectation`, `mechanism`, `confounders`, `confounder_review`, `grade`, `rationale`, `falsifier` |
| Evidence item | resolved `source_id`, exact original-language `quote`, `locator` with speaker/section and page/line/time |
| Expectation | `status: unavailable` with `reason`, or `status: available` with finite `value`, prior offset-bearing `as_of`, `source_id`, `data_period`, `unit`, `accounting_basis` |

Timings: `before-open`, `during-session`, `after-close`, `unknown`. Chart categories: `earnings`, `corporate`, `sellside`, `scandal`, `narrative`. Optional `event_type`: `earnings`, `company_disclosure`, `company_news`, `industry_news`, `macro_news`, `sellside`, `fund_flow`, `other`. Novelty: `new_information`, `already_disclosed`, `unknown`. Grades are defined in `SKILL.md`.

An available expectation must precede event publication. Provider estimates without verified historical cutoffs cannot satisfy that requirement. Additional actual/gap fields must use comparable definitions.

Event `reaction`, when supplied, contains the `price-window` result plus resolved `price_source_id` and `benchmark_source_id`. Windows keyed `1`, `5`, `20` have `status`, raw/benchmark percentages, benchmark-adjusted percentage points and baseline/end dates where available. Retain frequency, timezone, currency and adjustment metadata with source records.

Each event represents an information release, not only a fiscal period or a price move. Keep the event date separate from the reporting period. Optional `first_disclosure_event_id` links a later event to where its information first appeared; `supersedes_event_ids` records disclosures that a later update replaces. An already-known fact remains `already_disclosed` even if it is repeated in a later call. Preserve exact public timestamps when sourced; otherwise use `unknown` and retain a verified publication date separately as an extension. Do not use a transcript webpage's publication time as the time management spoke.

For multiple return references, keep `reaction` for the primary broad-market comparison and add optional `benchmark_comparisons`: an array of `{symbol, role, benchmark_source_id, price_source_id, reaction}`. Roles include `broad_market` and `industry`; each reaction uses the same exact-window contract and resolves both the stock-price and benchmark-price sources. A sector ETF return is context, not observed fund flow. `event_type` distinguishes company disclosures/news from macro/industry news and separately sourced flow data; a source-backed headline is not automatically a catalyst.

Driver grades require located evidence, mechanism, a confounders array and written review. Empty confounders means reviewed and none found, not missing review. `supported_driver` additionally requires new information, prior expectation, known timing and at least one benchmark-comparable reaction with stock/benchmark sources. Review material unresolved confounders before assigning this grade. Passing structural checks never establishes source truth.

## Fictional transcript-only example

This is synthetic test material, not a statement about a listed company:

```json
{
  "ticker": "SYNTH",
  "analysis_as_of": "2026-10-06T12:00:00+08:00",
  "sources": [{
    "id": "call", "url_or_path": "synthetic://example-call",
    "published_at": "2026-09-30T16:30:00-04:00",
    "retrieved_at": "2026-10-06T12:00:00+08:00", "data_period": "FY26 Q3"
  }],
  "events": [{
    "id": "q3-call", "date": "2026-09-30", "published_at": "2026-09-30T16:30:00-04:00",
    "timing": "after-close", "title": "Synthetic Q3 call", "source_id": "call", "category": "earnings"
  }],
  "factors": [{
    "id": "margin", "event_id": "q3-call", "metric": "next-quarter margin", "novelty": "unknown",
    "evidence": [{"source_id": "call", "locator": "Q&A, CFO, line 12", "quote": "We expect lower margins next quarter."}],
    "expectation": {"status": "unavailable", "reason": "No dated pre-call estimate supplied"},
    "mechanism": "Lower margin could reduce earnings; market expectations are unknown.",
    "confounders": [], "confounder_review": "Price/news inputs not supplied; competing-event review incomplete.",
    "grade": "insufficient_evidence", "rationale": "Factor hypothesis only; no measured price driver.",
    "falsifier": "A dated estimate already incorporating this outlook would refute novelty."
  }]
}
```

CLI `--output` creates new JSON files only. Price input is an array of actual daily `{d,c}` closes. `export-events` omits out-of-coverage annotations and preserves sources/grades. Move fields stay blank unless a one-session reaction is supplied, in which case the label explicitly says supplied evidence. The app's `evidence` field accepts this record after validation; it does not read PDFs or infer factors automatically.
