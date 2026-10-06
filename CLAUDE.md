# CLAUDE.md — Project context for AI assistants

## Project
Canada-wide utility rate scraping and browsing for building energy-cost analysis.

## Active Scope (2026-10-06)
- The active campaign is limited to 16 registered utilities in BC/QC/MB/SK/NB/NS/PE/NL. ON/AB/YT/NT/NU are excluded from this run but retained in the database/site. Nine batches are implemented, stored and exported; all 16 have live output but catalogue gaps remain.
- Prioritize building tariffs: single-family and multi-unit residential, commercial,
  institutional and industrial service only where relevant to building energy loads.
  NECB 2025 informs the use case; it does not replace utility eligibility rules or
  make this a building-code compliance tool.
- Building-related industrial general facility service defined by size, voltage or
  interruptibility is in scope from October 6. Process-specific farm/oil-field,
  irrigation, NGV fuelling, EV charging, lighting, wholesale/reseller and standby-only
  service is excluded. Keep completed reference parsers/data and all snapshots.
- Significant tested milestones may be committed and pushed, as explicitly requested.
- Near the user's requested 90% context limit, stop new work, validate the current
  batch, save exact resume notes in the matrix/handoff, and commit/push before stopping.
  Checkpoint early if exact usage is unavailable; preserve unrelated changes.

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
  - Three views: **Rate Browser** (filters/cards/details), **Market Pricing** (heatmap/chart/methodology), and **Compare** (two tariffs, no calculated totals). The planned Across-Canada comparison in README Phase 6 is not implemented.
  - Filters use a `filterState` object with JavaScript `Set`s — empty set = show all, non-empty = intersection.
  - Province filter cascades into utility filter — selecting a province hides utilities from other provinces.
  - Rate deduplication at load time: only the most recent effective_date per utility+tariff is shown.
- **Source registry** at `data/sources/registry.json` maps utilities to scraper classes and source URLs.

## Key patterns
- Scrapers try live HTTP fetch first, fall back to hardcoded seed data. Provenance is tracked, not flattened (see Working rules): live/verified records carry `Provenance: officially_verified` or `Provenance: live_parsed`; failed fetches call `mark_fallback()` (→ `Provenance: seed_fallback`, `confidence: unverified`). `export_json.derive_provenance()` maps this to a `provenance` field (`"live"`/`"seed"`) and the site hides `seed` by default.
- **Live parsers**: Manitoba Hydro and NB Power use class-specific HTML parsers. BC Hydro/NSPower residential service, FortisBC Electric, Hydro-Quebec, Maritime Electric, Newfoundland Power and NL Hydro use PDF extraction; BC Hydro/NSPower business service remains HTML-based. SaskPower parses 41 records across audited building schedules and retained references. SaskEnergy and Centra Gas parse official HTML service variants with required dated carbon evidence. FortisBC Energy and Liberty NB parse official HTML tables plus official carbon evidence; Energir follows its pricing page to the current tariff PDF; Eastward follows its business page to the monthly rate-table PDF and cross-checks page summaries.
- **Multi-class coverage is not catalogue completeness.** All 16 targets have live output; optional products and missing classes still require audits. Batch 9 counts are in the matrix.
- **BC Hydro:** RS 1901/1904 exclude 2101 TOD adjustments; prorated tiers and conditional transformer discounts retain their source context. Business power-factor bands are conditional and fail independently.
- **NSPower:** FAM/DSM/storm are separate from base energy; closed pilots are conditional, never proof of participant restoration. November prices are date-gated and unsupported 2027 dates fail closed.
- **Hydro-Quebec DP/DM/DN:** multiplier-based units, additive dwelling/room terms and alternative voltage credits must not become invented fixed allowances or bill totals. Missing/future editions and missing continuations fail closed by class.
- **JS-rendered pages**: `BaseScraper.fetch_rendered_page()` uses headless Chromium; SaskPower needs it for PDF discovery. Missing known classes retain labelled seed fallbacks. Newly discovered unsupported classes are recorded as gaps, never invented as fallback rates.
- **SaskPower:** complete columns, dates and continuation pages gate each schedule independently; never put kVA thresholds in kW fields. E01/E03 columns must agree; bulk charges are per unit, and same-page schedules must be sliced separately.
- **SaskPower references:** E41 is per meter location per month during pumping season, not per season; its 1997 closure is not an effective date. Retain native units for irrigation, unmetered and oil-field schedules without expanding excluded processes.
- **Yukon Energy 1160:** use the base column, then separate R/J/J1 percentages, Rider F and dated energy-only relief. Image-only base PDFs require reviewed OCR/text before broader extraction.
- Per-utility parser rules and remaining class gaps live in [the gap report](docs/live_parser_gap_report.md); use [the matrix](docs/phase5_completion_matrix.md) for the current queue.
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
pytest                                    # run tests (801 tests across 8 modules)
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

## Current snapshot and queue (2026-10-06; batch 9)
- Batch 9 stored/exported: 694 tariff versions / 4,453 components / 214 stored live / 480 seed; 209 latest live across 18 utilities, 207 across all 16 targets. History: 1,570 snapshots, 106 appended with prior snapshots unchanged. DB validation: 0 errors, 2 existing AESO warnings; 801 tests passing across 8 modules. Latest target counts: BC Hydro 11, FortisBC Electric 11, Hydro-Quebec 25, Manitoba Hydro 12, SaskPower 41, NB Power 10, NSPower 14, Maritime Electric 10, Newfoundland Power 11, NL Hydro 21, SaskEnergy 6, Centra 12, FortisBC Energy 11, Energir 5, Eastward 3, Liberty NB 4. FortisAlberta and Yukon Energy retain 1 each.
- Batch 9 added NL Hydro Island/Labrador Industrial Firm and conditional net-metering credit, Energir interruptible D5 and optional replacement RNG supply, Newfoundland Power Curtailable Option 1 and domestic net-metering credit, NB Power Large Industrial and hardened Small Industrial, BC Hydro RS1830 and closed RS1289, FortisBC Electric RS31/33, and Hydro-Quebec L/LG/H and business Demand Response Leeway. Manitoba Hydro isolates page failures without adding tariffs. Source-blocked classes, unpriced pass-throughs and conditional credits remain distinct from base charges; see the [gap report](docs/live_parser_gap_report.md).
- Wave 2: NSPower industrial, FortisBC Energy Rate 7 (Rate 6 NGV excluded), SaskEnergy small industrial, Centra remaining classes, Maritime Electric 310-340 building-industrial audit. Also open: BC Hydro transmission pilots, Hydro-Quebec DR Commitment, NL Hydro IND non-firm/wheeling, Manitoba standard service charges/LUBD. Needs decision: BC Hydro RS1828, FortisBC RS38, Hydro-Quebec F/FP. See the [matrix](docs/phase5_completion_matrix.md).
- Operations: source-health Chromium, successful Monthly Scrape `workflow_run` deployment from `main`, release-asset `data-history` database restore/upload after validation/export, and test/scrape failure issues are implemented, pending first CI run verification. Pages source must be GitHub Actions; `workflow_run` fires from the default branch.
- Historical pointer: batch 8 (October 5, after `8a88448`) had 762 tests, 1,464 snapshots and 191 latest live campaign records; it is no longer the current checkpoint.

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
- Deterministic tests block unmocked network access. Run `pytest -q` (801 tests across 8 modules); inspect targeted live dry runs separately. A generic verifier fixture or a successful fallback-only run does not establish a working live parser.

## Active Regional Implementation
- Only 16 registered utilities in BC/QC/MB/SK/NB/NS/PE/NL are in this run. ON/AB/YT/NT/NU remain untouched and retained in exports. Independent parser/fixture work may be parallel; shared tests/registry/docs/DB/export/git integration is serial. The active matrix queue supersedes its retained historical checkpoint instructions.
- HQ options: DT is temperature-switched, Flex D event-based; Winter Credit is a conditional adjustment, not a base rate or calculated total. Preserve source multipliers, notice rules and separate component dates.
- NL Hydro: fixed phase/amperage choices are alternatives; seasonal adjustments require matching complete same-date base schedules. Keep native demand units and minimum/maximum bills as conditions.
- SaskEnergy: carbon evidence and older base components have distinct dates; the assembled date uses the latest required component. Never invent private commodity prices, heat conversions or industrial eligibility.
- FortisBC Electric: RS1 flat supersedes older history; RS2A is closed. RS21 kW/kVA demands are alternatives, negative credits are conditional, and required continuation/date context must be present.
- NSPower: MURB89 needs its own rider rows, weekend/holiday note and house-meter eligibility. Optional solar credits apply to subscriber generation, not household consumption or a guessed bill offset.
- Centra: delivery and volumetric demand parts reconcile to published totals without double counting; required PUB conditions fail closed. Keep CRA carbon evidence separate and fixed-term/private commodity prices unpriced.
- Per-utility implementation rules and gaps are maintained in [the gap report](docs/live_parser_gap_report.md); batch 9 work and the remaining queue are in [the matrix](docs/phase5_completion_matrix.md).
