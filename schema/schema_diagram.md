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

┌───────────────────┐     ┌──────────────────────┐
│ customer_classes  │     │   market_pricing     │
│                   │     │                      │
│ id                │     │ id                   │
│ utility_id        │→    │ province             │
│ class_name        │     │ market_operator      │
│ sub_class         │     │ month                │
│ description       │     │ day_type             │
│ eligibility       │     │ hour                 │
│ threshold_kw      │     │ component            │
│ threshold_kwh     │     │ value                │
│ is_default        │     │ unit                 │
└───────────────────┘     │ derivation_method    │
                          │ history_window_years │
                          └──────────────────────┘
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

6. **Customer class tracking** — `customer_classes` records which classes each
   utility serves and their eligibility thresholds, enabling coverage audits.

7. **Market pricing** — the `market_pricing` table is defined but not populated
   by the pipeline; it is kept for possible future use. The Ontario market
   history lives outside the database, in files kept in git:
   - `site/data/market_pricing_ontario.json` (schema 2, since October 16): the
     latest 60 complete months (legacy HOEP to April 2025, then the Ontario
     Price, plus the actual Class B Global Adjustment) and 576 heatmap bins
     (12 months × 2 day types × 24 hours) built from observed hours only, with
     `hours_hoep`/`hours_oemp` counts; built by `scripts/build_ontario_market.py`
     in the Ontario Price Archive workflow. The legacy Phase 6A file
     (2020-2024, `scripts/generate_market_pricing.py`) is still accepted by
     the readers.
   - `data/market/ontario_market_monthly.csv`: the permanent monthly history
     since January 2020 (never trimmed; a month may be revised only within
     6 months of its end).
   - `data/market/hoep_hourly.csv`: legacy hourly HOEP, January 2020-March
     2025, imported once.
   - `data/market/ontario_price_hourly.csv`: the hourly Ontario Price archive
     from July 11, 2026, extended by `scripts/archive_ontario_price.py`.

   Tariffs never copy these averages; market-indexed components stay
   value-less (`market_reference`, shown as "Variable").

8. **Where the database lives** — since October 16 the Monthly Scrape
   workflow is the only writer of `data/db/rates.db`. The master copy is
   asset `rates.db` of the GitHub release tagged `data-history`, next to dated
   gzip backups (`rates-YYYY-MM-DD.db.gz`, newest 12 kept). Before uploading,
   `scripts/check_db_history.py` requires `PRAGMA integrity_check` "ok", no
   fewer `historical_snapshots`, `tariffs` or `scrape_runs` rows, and an
   unchanged digest over every earlier snapshot row. Local copies are
   read-only mirrors from `scripts/pull_history_db.py` (older local copies go
   to the git-ignored `data/db/backups/`). Deleting the release deletes the
   database and all its backups. The schema itself did not change.
