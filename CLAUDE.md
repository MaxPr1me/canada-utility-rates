# CLAUDE.md — Project context for AI assistants

## Project
Canada-wide utility rate scraping and browsing platform.

## Working rules
- **Never display default values as if they were live.** Only rate values pulled from (or verified against) a live official web source may be presented as current. Hardcoded seed/fallback values are a safety net only: they carry `Provenance: seed_fallback` + `confidence: unverified`, export as `provenance: "seed"`, and the site hides them by default behind a labelled "Estimated" toggle. Never dress up a static default as a live-scraped rate.
- **Do not assume scope.** If a requirement is unclear or has multiple reasonable interpretations, stop and ask the user which path to take before proceeding.

## Architecture
- **Scrapers** (Python) live in `scrapers/utilities/`: 33 implementations plus `__init__.py`. The registry references 32 modules for 84 utility entries; legacy `toronto_hydro.py` is unregistered and Ontario shares one data-driven scraper.
  Each inherits from `scrapers/base.py:BaseScraper` and returns `list[TariffRecord]`.
- **Pipeline** scripts in `pipeline/` handle orchestration: `run_scrape.py`, `export_json.py`, `diff_report.py`, `validate.py`.
  - `run_scrape.py` uses upsert logic (`ON CONFLICT ... DO UPDATE SET`) with NULL-safe `IS` comparisons for idempotent re-runs.
- **Database** is SQLite at `data/db/rates.db`, schema defined in `schema/create_tables.sql`.
- **Static site** in `site/` is a single-page app (plain HTML+CSS+JS + Chart.js CDN), deployed to GitHub Pages, reads JSON from `site/data/`.
  - Two views: **Rate Browser** (multi-select checkbox filters, rate cards, detail modal) and **Market Pricing** (heatmap, line chart, summary table, methodology).
  - Filters use a `filterState` object with JavaScript `Set`s — empty set = show all, non-empty = intersection.
  - Province filter cascades into utility filter — selecting a province hides utilities from other provinces.
  - Rate deduplication at load time: only the most recent effective_date per utility+tariff is shown.
- **Source registry** at `data/sources/registry.json` maps utilities to scraper classes and source URLs.

## Key patterns
- Scrapers try live HTTP fetch first, fall back to hardcoded seed data. Provenance is tracked, not flattened (see Working rules): live/verified records carry `Provenance: officially_verified` or `Provenance: live_parsed`; failed fetches call `mark_fallback()` (→ `Provenance: seed_fallback`, `confidence: unverified`). `export_json.derive_provenance()` maps this to a `provenance` field (`"live"`/`"seed"`) and the site hides `seed` by default.
- **Live parsers**: Manitoba Hydro, NB Power, NS Power and BC Hydro have class-specific HTML parsers. Hydro-Quebec, Maritime Electric and Newfoundland Power rebuild supported classes from PDFs. SaskPower parses residential plus 36 supplied/customer-owned, farm and oil-field schedules. NL Hydro still verifies known values rather than rebuilding changed schedules.
- **Multi-class coverage is not catalogue completeness.** Implemented output includes BC Hydro (4), NB Power (3), NS Power (Domestic + 10/11/12), Manitoba Hydro (8), Hydro-Quebec (D/G/M), Maritime Electric (10), Newfoundland Power (1.1/2.1/2.3/2.4). Missing standard classes still require source audits. Reuse section slicing and label/value parsing; handle cent glyph variation without accepting dollar-per-kWh as cents.
- **JS-rendered pages**: `BaseScraper.fetch_rendered_page()` uses headless Chromium; SaskPower needs it for PDF discovery. Missing known classes retain labelled seed fallbacks. Newly discovered unsupported classes are recorded as gaps, never invented as fallback rates.
- **SaskPower (2026-10-01)**: source-derived page fixtures cover E05/E06, E75/E76, E07/E08/E10/E12, E77/E78, E82/E83/E84, E22/E23/E24 and N22/N23/N24. Preserve voltage/urban/rural columns, kVA tiers, TOU hours, closed-to-new eligibility and continuation-page billing conditions. Require source dates and complete rows; isolate failures by schedule. Do not fill kW eligibility fields with kVA thresholds.
- **Supplied-service additions:** E37 irrigation retains `$/season` and `$/HP/season`; E15/E17 use watt-block/month units, E16 uses power-supply-unit/month, E18 uses installed-kVA/month, and E35 diesel has two energy tiers. Slice multiple schedules on the same page before parsing; minimum bills are conditions, not extra additive charges.
- **Farm/oil-field additions:** E34/E19/E41 and E43/E44/E46-E48/E86-E88 have dedicated fixtures. E41 is a monthly per-meter-location charge during the pumping season, not a seasonal lump sum; its 1997 closure notice is not the tariff effective date. Oil-field standard charges are per metering point; power variants preserve voltage and TOU conditions.
- Every tariff stores individual rate_components (fixed, energy, demand, delivery, riders, etc.) — never flatten to one number.
- Historical snapshots are preserved in `historical_snapshots` table — never overwrite.
- Validation runs after scraping (`scrapers/utils/validation.py`).
- `confidence` field on tariffs/components tracks data quality: high / medium / low / unverified.
- **Change detection** (`scrapers/utils/change_detection.py`): `compare_to_seed()` pairs live-parsed records with seed data, flags changes by severity (info <5%, warning 5-30%, critical >30%). Critical alerts cause fallback to seed data.
- **Parsing helpers** (`scrapers/utils/parsing.py`): `find_text_near_label()`, `extract_rate_from_text()`, `detect_js_rendered()`, query-safe/relative-aware `find_pdf_links()`, and strict `verify_tariff_values()` official-source checks.

## Running
```bash
pip install -r requirements.txt && pip install -e .
python -m playwright install chromium     # headless browser for JS-rendered pages
python -m pipeline.run_scrape --init-db   # first time
python -m pipeline.run_scrape             # scrape all
python -m pipeline.export_json            # export for site
pytest                                    # run tests (283 tests)
```

## Adding a utility
1. New file in `scrapers/utilities/` inheriting `BaseScraper`.
2. Register in `data/sources/registry.json`.
3. Test with `python -m pipeline.run_scrape --utility "Name" --dry-run`.

## Conventions
- Python 3.10+, type hints throughout.
- ISO-8601 dates, always UTC for timestamps.
- Currency always in CAD unless stated.
- Province codes are 2-letter uppercase (BC, ON, QC, etc.).
- Keep registry URLs and actual scraper URL constants synchronized; most modules do not consume registry sources dynamically.

## Current snapshot and queue (2026-10-01)
- Targeted SaskPower refresh: 37 live records. Export: 555 tariffs / 3,638 components / 75 live / 480 seed across 84 utilities. Other utilities retain September 29 source results; do not describe this as a new national source check.
- Next: remaining SaskPower schedules, then easier Yukon Energy/NS industrial/FortisBC Electric expansions; territorial/provincial depth, nine gas utilities, Alberta electricity and the Ontario distributor campaign follow. README and the Phase 5 matrix hold the maintained roadmap.
- The Ontario market generator uses fixed inputs and multipliers, not reproducible five-year observation ingestion. Document this now; the user deferred UI/metadata correction and real ingestion to later phases.
- Local history is append-only. Monthly CI restore/save, default-token deployment triggering, source-health browser setup and failure reporting remain separate reliability work.

## Task completion checklist
Every task should include a documentation review step. At minimum, assess whether the following need updates:
- `README.md` — project overview, roadmap, tech stack
- `AGENTS.md` — plain-language guide for non-technical maintainers
- `CLAUDE.md` — this file (architecture, patterns, conventions)
- `docs/` — any relevant guides or reports (e.g., `adding-a-utility.md`, `live_parser_gap_report.md`)
Update these files when the task changes architecture, adds major features, changes conventions, or updates test/tariff counts.

## Phase 5 hardening conventions

- `BaseScraper.verify_official_records()` is the shared strict HTML/PDF component verifier; utility modules retain tariff interpretation. `mark_fallback()` recursively downgrades confidence and emits `Provenance: seed_fallback` notes; `mark_live_parsed()` stamps `Provenance: live_parsed` for scrapers that rebuild tariffs directly from a live fetch. `pipeline/export_json.py:derive_provenance()` collapses these markers into a `provenance` field the site uses to hide non-live data by default.
- `scrapers.utils.parsing` provides `DocumentPage`, page-aware fail-closed PDF extraction/section selection, CSV/XLSX readers, content hashing, effective-date/unit/currency normalization, and contextual verification.
- Snapshot serialization is canonical JSON with sorted component dictionaries. Ordering alone is ignored; all semantic fields remain hashed. `diff_runs` compares append-only per-run snapshots.
- The no-build comparison state is an in-memory two-item array in `site/js/app.js`; it aligns exact type/name/unit keys and never totals them.
- Deterministic tests block unmocked network access. Run `pytest -q` (283 tests); inspect targeted live dry runs separately. A generic verifier fixture or a successful fallback-only run does not establish a working live parser.
