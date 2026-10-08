# CLAUDE.md — Project context for AI assistants

## Project
Canada-wide utility rate scraping and browsing for building energy-cost analysis.

## Active Scope (2026-10-06)
- The active campaign covers 16 registered utilities in BC/QC/MB/SK/NB/NS/PE/NL plus, from October 7, the four territorial utilities (YT/NT/NU; non-market regulated service). ON/AB are excluded from this run but retained in the database/site; Ontario LDC work started October 7 as its own block (batches 1-2 stored; 46 distributors live). Ten batches are implemented, stored and exported; all 20 have live output but catalogue gaps remain.
- Decisions (October 7): BC Hydro RS1828, Hydro-Quebec Rate F/FP and FortisBC Energy 11RNG excluded; market-indexed FortisBC RS38, BC Hydro RS1892, NSPower one-part real-time pricing and NL Hydro monthly non-firm prices (5.1L, Island non-thermal) are deferred to the Alberta/Ontario market-rate work.
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
- **Scrapers** (Python) live in `scrapers/utilities/`: 33 implementations plus `__init__.py`. The registry references 32 modules for 86 utility entries (8 Ontario entries `merged`); legacy `toronto_hydro.py` is unregistered and Ontario shares one data-driven scraper.
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
- **Multi-class coverage is not catalogue completeness.** All 20 targets have live output; optional products and missing classes still require audits. Batch 10 counts are in the matrix.
- **Territories:** NTPC parses the PUB June 1, 2026 schedule (zones; per-community government) with GNWT Cost of Living Subsidy as a conditional credit and the TPSP printed first-block price as a conditional alternative energy price (never a derived difference). Qulliq uses the April 1, 2025 interim rates (medium confidence; stale page date label). Yukon Energy and ATCO Electric Yukon share the text joint YECL/YEC rate book cross-checked against the R/J cross-reference; same 20 schedules, not 40 classes.
- **Logging:** `setup_logging()` is idempotent and keeps pdfminer/pdfplumber at WARNING; per-token pdfminer DEBUG once grew `logs/scrape.log` to ~10 GB and stalled the suite. The file now rotates at 10 MB with 3 backups; it is a git-ignored debug diary that nothing reads.
- **Reviewed transcription (Centra MLI only, user-approved):** values from scanned image-only pages live in a module constant, are marked live at medium confidence, and are built only while the page-image SHA-256 hashes, edition headers and text cross-checks match. Never extend this to other image-only sources without explicit approval.
- **BC Hydro:** RS 1901/1904 exclude 2101 TOD adjustments; prorated tiers and conditional transformer discounts retain their source context. Business power-factor bands are conditional and fail independently.
- **NSPower:** FAM/DSM/storm are separate from base energy; closed pilots are conditional, never proof of participant restoration. November prices are date-gated and unsupported 2027 dates fail closed.
- **Hydro-Quebec DP/DM/DN:** multiplier-based units, additive dwelling/room terms and alternative voltage credits must not become invented fixed allowances or bill totals. Missing/future editions and missing continuations fail closed by class.
- **JS-rendered pages**: `BaseScraper.fetch_rendered_page()` uses headless Chromium; SaskPower needs it for PDF discovery. Missing known classes retain labelled seed fallbacks. Newly discovered unsupported classes are recorded as gaps, never invented as fallback rates.
- **SaskPower:** complete columns, dates and continuation pages gate each schedule independently; never put kVA thresholds in kW fields. E01/E03 columns must agree; bulk charges are per unit, and same-page schedules must be sliced separately.
- **SaskPower references:** E41 is per meter location per month during pumping season, not per season; its 1997 closure is not an effective date. Retain native units for irrigation, unmetered and oil-field schedules without expanding excluded processes.
- **Yukon Energy 1160:** use the base column, then separate R/J/J1 percentages, Rider F and dated energy-only relief. Other 1180-2480 classes come only from the text joint YECL/YEC book and must reconcile with the cross-reference; never read image-only PDFs into live values.
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
pytest                                    # run tests (1,213 tests across 8 modules)
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

## Current snapshot and queue (2026-10-08; Ontario batch 2)
- Ontario batch 2 stored/exported (scrape run 26, all 46 configured LDCs re-stored through `logs/_on2_store.py` live/seed gate): 483 latest live at 46 Ontario distributors. Totals: 1,321 versions / 13,343 components / 841 stored live / 480 seed; 836 latest live across 67 utilities; 3,013 snapshots (527 appended, prior unchanged, non-ON tariffs unchanged); 0 validation errors, 2 AESO warnings; 1,213 tests.
- Batch 2 rules: optional per-document `"extract": {"y_tolerance": N}` (Kingston 6, Midland 1, Grimsby 4) for PDFs whose values print above their labels; overprinted "Applicable only for ..." tail attaches to the preceding rider; a lone Transformation Connection line is the standard connection rate (a lone Line line still fails); case number may come from the Schedule A cover only when its date equals the Issued date; "EQUAL TO OR GREATER THAN" open GS and INTERMEDIATE USER (inside 50-5,000 kW) are GS demand; in-scope classes that classify "other" surface as rejections. Algoma (user-confirmed): R1 criteria (i)/(ii) split, both residential, R1(i) keeps TOU-R codes; R2 = `residential_demand` delivery-only record (no RPP). Seed suppression: configured LDC with a class rejection or no such class (`gs:absent`/`demand:absent`) emits no Res/GS/GS-D seeds; fetch failure / sheet-level rejection keep seeds; SL seed kept. PUC Distribution left unconfigured (no connection RTSR; user decision).
- Representative model (scratch `logs/_on2_r_model.py`): typical monthly delivery CV ~0.18 for residential, GS<50 and GS 50-4,999 (close; Hydro One the outlier). Not published. Planned as README Phase 7 (Representative Models, 7A-7G): per province/sector/structure medians, single-source labelling, all-in energy when the market model allows, `provenance: "modeled"`, own site view; the Phase 6 Across-Canada comparison reads these models.

## Ontario batch 1 snapshot (2026-10-07; historical)
- Ontario batch 1 stored/exported (scrape run 25): 24 distributors, 319 latest live + 25 labelled seed. Totals: 1,157 versions / 10,822 components / 677 stored live / 480 seed; 672 latest live across 45 utilities; 2,486 snapshots (344 appended, prior unchanged); 0 validation errors, 2 AESO warnings; 1,165 tests.
- Ontario architecture: `OEB_TARIFF_DOCUMENTS` (registry name -> [{url, case_number, zones, default_zone}]) in `ontario_ldc.py`; `scrapers/utils/oeb_tariff.py` parses tariff sheets (use `extract_tariff_pages`, not `normalize_document_text`, which drops repeated lines). BillData XML = name/zone cross-check only. Residential/GS<50 = live RPP energy + tariff delivery, legacy codes (TOU-R, GS-TOU-S...) in the default zone and "[zone]" names elsewhere; demand classes delivery-only. Open GS floor <=1,000 kW -> commercial, else large_use (user-confirmed). Merged registry entries have `status: "merged"` + `merged_into` and are skipped by `get_active_utilities`; successors Enova Power Corp./GrandBridge Energy Inc. have no seed. A rejected class emits no new estimate (user decision: go by live sources); older stored estimates stay in history labelled seed. Hydro One Seasonal (user-confirmed): R2 seasonal service charge + shared R2 lines, no RRRP credit; year-round R2 carries the RRRP credit as conditional; UR/R1 seasonal properties use UR/R1 records; DRP not modelled.
- Ontario next: PUC Distribution (needs a no-connection-rate decision), demand-class commodity/GA (market-rate work), Alberta block (research saved in repo memory), ON/AB gas.

## Batch 11 snapshot (2026-10-07; historical)
- Batch 11 (full 20-utility refresh) stored/exported: 838 tariff versions / 5,417 components / 358 stored live / 480 seed; 353 latest live across 21 utilities: 243 at the 16 provincial targets and 109 at the four territorial utilities. History: 2,142 snapshots, 352 appended with prior snapshots unchanged. DB validation: 0 errors, 2 existing AESO warnings; 1,052 tests. Batch 11 added FortisBC Energy 1U/2U/3U and RNG variants (27), SaskEnergy service fees (8), Centra Mainline Interruptible transcription (13), NTPC Taltson heating (63). The matrix reconciliation table shows no priced, dated in-scope gap left; remaining items are source-blocked, excluded, monitored or deferred to market-rate work.
- Batch 10 (historical): 824 tariff versions / 5,286 components / 344 stored live / 480 seed; 339 latest live across 21 utilities: 230 at the 16 provincial targets and 108 at the four territorial utilities. History: 1,790 snapshots. Latest counts: BC Hydro 17, FortisBC Electric 11, Hydro-Quebec 26, Manitoba Hydro 18, SaskPower 41, NB Power 10, NSPower 18, Maritime Electric 10, Newfoundland Power 11, NL Hydro 21, SaskEnergy 7, Centra 12, FortisBC Energy 16, Energir 5, Eastward 3, Liberty NB 4, NTPC 62, Qulliq 6, Yukon Energy 20, ATCO Electric Yukon 20; FortisAlberta 1.
- Batch 10 added NSPower industrial 21/22/23 and Interruptible Rider 25; FortisBC Energy Rate 7 and delivery-only transportation 22/23/25/27; SaskEnergy closed Small Industrial; BC Hydro transmission pilots 2801/2802/2821/2822 and generation credits 2289/2290; Hydro-Quebec DR Commitment; Manitoba LUBD 2026-50..55; Maritime 310/320 audited (330/340 are Summerside wholesale reference); Centra class audit and NL Hydro non-firm (source-blocked)/wheeling (excluded) audits; and the four territorial parsers.
- Open: Centra Mainline Interruptible (scanned Appendix A; needs reviewed text), NTPC Taltson interruptible heating (needs decision), NTPC Snare TPSP mismatch, Qulliq final GRA decision, Yukon riders R1/S/E and winter rebate, FortisBC Energy RNG/Customer Choice variants, HQ Load Retention/Additional Electricity/Industrial Revitalization (not general published prices), plus the earlier source-blocked items. See the [matrix](docs/phase5_completion_matrix.md).
- Operations: source-health Chromium, successful Monthly Scrape `workflow_run` deployment from `main`, release-asset `data-history` database restore/upload after validation/export, and test/scrape failure issues are implemented, pending first CI run verification (Deploy Site for `1b05a2f` succeeded on push; Source Health not yet dispatched). Pages source must be GitHub Actions; `workflow_run` fires from the default branch.
- Historical pointer: batch 9 (October 6, `1b05a2f`) had 801 tests, 1,570 snapshots and 207 latest live campaign records; it is no longer the current checkpoint.

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
- Deterministic tests block unmocked network access. Run `pytest -q` (1,213 tests across 8 modules); inspect targeted live dry runs separately. A generic verifier fixture or a successful fallback-only run does not establish a working live parser.

## Active Regional Implementation
- The 16 registered utilities in BC/QC/MB/SK/NB/NS/PE/NL and, from October 7, the four territorial utilities are in this run. ON/AB remain untouched and retained in exports. Independent parser/fixture work may be parallel; shared tests/registry/docs/DB/export/git integration is serial. The active matrix queue supersedes its retained historical checkpoint instructions.
- HQ options: DT is temperature-switched, Flex D event-based; Winter Credit is a conditional adjustment, not a base rate or calculated total. Preserve source multipliers, notice rules and separate component dates.
- NL Hydro: fixed phase/amperage choices are alternatives; seasonal adjustments require matching complete same-date base schedules. Keep native demand units and minimum/maximum bills as conditions.
- SaskEnergy: carbon evidence and older base components have distinct dates; the assembled date uses the latest required component. Never invent private commodity prices, heat conversions or industrial eligibility.
- FortisBC Electric: RS1 flat supersedes older history; RS2A is closed. RS21 kW/kVA demands are alternatives, negative credits are conditional, and required continuation/date context must be present.
- NSPower: MURB89 needs its own rider rows, weekend/holiday note and house-meter eligibility. Optional solar credits apply to subscriber generation, not household consumption or a guessed bill offset.
- Centra: delivery and volumetric demand parts reconcile to published totals without double counting; required PUB conditions fail closed. Keep CRA carbon evidence separate and fixed-term/private commodity prices unpriced.
- Per-utility implementation rules and gaps are maintained in [the gap report](docs/live_parser_gap_report.md); batch 10 work and the remaining queue are in [the matrix](docs/phase5_completion_matrix.md).
