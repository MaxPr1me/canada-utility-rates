# Database Schema Overview

## Why SQLite?

SQLite is the best choice for this project because:
- **Zero installation** — Python includes it by default.
- **Single file** — the entire database is one `.db` file.
- **Full SQL** — supports JOINs, indexes, aggregations, CTEs.
- **Repository-friendly** — easy to back up, move, and share.
- **More than enough scale** — even 100k rows is effortless.

We also **export JSON** for the static GitHub Pages site, because browsers
cannot query SQLite directly.

## Table Diagram

```
┌──────────────┐      ┌──────────────┐
│  utilities   │──1:N─│   sources    │
│              │      │              │
│ id           │      │ id           │
│ name         │      │ utility_id   │→ utilities.id
│ province     │      │ url          │
│ utility_type │      │ source_type  │
│ website      │      │ status       │
│ rate_page_url│      └──────────────┘
│ regulator    │
└──────┬───────┘
       │ 1:N
       ▼
┌──────────────┐      ┌────────────────────┐
│   tariffs    │──1:N─│  rate_components   │
│              │      │                    │
│ id           │      │ id                 │
│ utility_id   │→     │ tariff_id          │→ tariffs.id
│ name         │      │ component_type     │
│ tariff_code  │      │ component_name     │
│ customer_class│     │ charge_value       │
│ rate_structure│     │ charge_unit        │
│ effective_date│     │ tier_number        │
│ source_url   │      │ tou_period         │
│ confidence   │      │ season             │
└──────┬───────┘      │ demand_threshold_kw│
       │ 1:N          │ market_reference   │
       ▼              │ confidence         │
┌───────────────────┐ └────────────────────┘
│ historical_       │
│ snapshots         │
│                   │     ┌──────────────┐
│ id                │     │ scrape_runs  │
│ scrape_run_id     │→    │              │
│ tariff_id         │→    │ id           │
│ snapshot_date     │     │ started_at   │
│ tariff_json       │     │ status       │
│ hash              │     └──────────────┘
└───────────────────┘
                          ┌──────────────┐
                          │ missing_data │
                          │              │
                          │ id           │
                          │ utility_id   │→ utilities.id (optional)
                          │ description  │
                          │ severity     │
                          └──────────────┘
```

## Key Design Decisions

1. **One row per charge line** — `rate_components` stores each individual charge
   (fixed fee, energy tier 1, energy tier 2, demand charge, rider, etc.)
   as its own row.  This avoids flattening complex tariffs into a single number.

2. **Historical preservation** — `historical_snapshots` stores the full JSON
   of each tariff+components after every scrape run, so we can track changes
   over time without ever deleting old data.

3. **Missing data tracking** — `missing_data` explicitly records what we know
   is incomplete, so users and maintainers can prioritize work.

4. **Source traceability** — every tariff and component links back to the
   exact URL and page/section where the data was found.

5. **Confidence flags** — every record has a confidence level so downstream
   consumers (AI, analysts) know how much to trust each value.
