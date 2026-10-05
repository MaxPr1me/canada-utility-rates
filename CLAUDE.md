# CLAUDE.md — Project context for AI assistants

## Project
Canada-wide utility rate scraping and browsing for building energy-cost analysis.

## Active Scope (2026-10-02)
- The active campaign is limited to 16 registered utilities in BC/QC/MB/SK/NB/NS/PE/NL. ON/AB/YT/NT/NU are excluded from this run but retained in the database/site. Three batches are implemented (the October 5 gas batch gives all 16 live output); the campaign is incomplete. Current priority is the recorded catalogue gaps in the matrix.
- Prioritize building tariffs: single-family and multi-unit residential, commercial,
  institutional and industrial service only where relevant to building energy loads.
  NECB 2025 informs the use case; it does not replace utility eligibility rules or
  make this a building-code compliance tool.
- User narrowed the earlier all-published-classes goal. Farm/oil-field processes,
  irrigation, standalone street lighting, wholesale and other non-building services
  are not required for completion. Keep completed implementations/data as reference,
  but stop expanding those classes. Do not remove snapshots or working reference parsers.
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
- **Multi-class coverage is not catalogue completeness.** Current target output: BC Hydro8, FortisBC Electric6, Hydro-Quebec9, Manitoba Hydro8, SaskPower41, NB Power3, NSPower10, Maritime Electric10, Newfoundland Power4, NL Hydro18, SaskEnergy6, Centra Gas12, FortisBC Energy8, Energir4, Heritage/Eastward3 and Liberty NB4. HQ includes DT/Flex D/Winter Credit; NSPower includes MURB89 and two solar adjustments. All 16 target utilities now have live output. Optional products and other missing classes still require source audits; keep class/unit context and do not interpret aggregate counts as completed building classes.
- **BC Hydro residential:** approved PDF RS 1101 tiered, 1151 flat, each combined with optional 2101 time-of-day, and closed dual-fuel 1105. Parse RS 1901/1904 from their own sections; they exclude 2101 adjustments. Preserve daily prorated tier thresholds and conditional transformer discounts. Five residential options and three separate business records are live.
- **NSPower residential (2026-10-02):** approved May 2026 book plus matching product publication dates; base energy and FAM/DSM/storm riders are separate. TOD 05/06 needs ETS/thermal storage and preserves Dec-Feb versus Mar-Nov periods. Pilots 70/80 are closed to new applications; October records are explicitly conditional interim variants, not verified customer restoration status. November rates activate only on the published date, with stable plan identities and source-derived hours/event/holiday rules. Optional Green Power is per purchased block, not a mandatory addition. The current parser rejects unsupported 2027 dates; don't borrow future numbers from the same PDF.
- **Hydro-Quebec DP/DM (2026-10-02):** page-aware sections require charge and continuation pages, publication date, season definitions, monthly proration and conditional supply-credit sources. DP preserves monthly tiers, seasonal demand and five mutually exclusive voltage-credit bands. DM is grandfathered at May 31, 2009; use `$/multiplier/day` and `kWh/day/multiplier`, with max(50 kW, 4 kW x multiplier) demand allowance retained as a rule, not a fixed threshold. Dwelling/room terms within the applicable multiplier branch are additive. Minimum bills and transformation-loss adjustments are conditions, not bill totals. Landing-page failure does not block the official PDF. Rate D is anchored to its own article 2.5; missing/future edition dates fail closed.
- **Hydro-Quebec DN (2026-10-02):** physical pages 127-128 cover domestic off-grid service north of the 53rd parallel except Schefferville. DN defaults to multiplier 1 unless formerly DM-eligible on May 31, 2009; it is not universally grandfathered. Preserve 0.07065/0.50469 energy tiers, 40 kWh/day/multiplier, the complete winter demand-ratchet/kW allowance rules, and DT's off-grid exclusion. Article 9.2 explicitly incorporates the conditional article 12.3 supply credit. The continuation was visually checked for additive room terms. Missing/malformed context rejects DN without downgrading DP/DM.
- **JS-rendered pages**: `BaseScraper.fetch_rendered_page()` uses headless Chromium; SaskPower needs it for PDF discovery. Missing known classes retain labelled seed fallbacks. Newly discovered unsupported classes are recorded as gaps, never invented as fallback rates.
- **SaskPower (2026-10-01)**: source-derived page fixtures cover E05/E06, E75/E76, E07/E08/E10/E12, E77/E78, E82/E83/E84, E22/E23/E24 and N22/N23/N24. Preserve voltage/urban/rural columns, kVA tiers, TOU hours, closed-to-new eligibility and continuation-page billing conditions. Require source dates and complete rows; isolate failures by schedule. Do not fill kW eligibility fields with kVA thresholds.
- **Supplied-service additions:** E37 irrigation retains `$/season` and `$/HP/season`; E15/E17 use watt-block/month units, E16 uses power-supply-unit/month, E18 uses installed-kVA/month, and E35 diesel has two energy tiers. Slice multiple schedules on the same page before parsing; minimum bills are conditions, not extra additive charges.
- **Farm/oil-field additions:** E34/E19/E41 and E43/E44/E46-E48/E86-E88 have dedicated fixtures. E41 is a monthly per-meter-location charge during the pumping season, not a seasonal lump sum; its 1997 closure notice is not the tariff effective date. Oil-field standard charges are per metering point; power variants preserve voltage and TOU conditions.
- **SaskPower building scope:** page-aware E01/E03 standard parsing requires identical city/rural columns and preserves the existing name; bulk-metered service is a separate closed-to-new per-unit billing variant, and diesel E04 has two energy tiers. R23/R24 renewable access requires its eligibility heading and billing-demand continuation. Six source-derived fixtures cover the supported documents; taxes/surcharges excluded by the schedules are not calculated.
- **Yukon Energy 1160:** read the base column, not the combined R/J column. R/J/J1 are separate percentages on base charges; Rider F is per kWh and relief is a dated, usage-limited energy percentage excluding fuel/fixed charges. Require current source dates and class applicability. One multi-document fixture covers this path. The detailed 1160 and 2160 PDFs are image-only; broader building classes and multiple-residence Rider A need OCR or authoritative text alternatives.
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
pytest                                    # run tests (551 tests)
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

## Current snapshot and queue (2026-10-05)
- Gas batch 3 (2026-10-05): FortisBC Energy 6 (Rates 1/2/3 × Mainland-VI/Fort Nelson, July 1 2026, $/day basic, BC carbon-tax elimination evidence), Energir 2 (default Rate D1 residential/business from the linked Oct 1 2026 CST PDF; CTEAS cap-and-trade 8.727¢/m³), Heritage/Eastward 2 (Residential + tiered General Service from the October 2026 rate table, cross-checked with page summaries) and Liberty NB 3 (SGS/MGS/LGS, Jan 1 2025 distribution + October LUG commodity + CRA NB carbon evidence). Guarded stores appended 13 snapshots (1,282 total) with all prior snapshots and non-target tariffs unchanged.
- Gas batch 4 (2026-10-05, after 6333ea8): FortisBC Energy 8 (adds Rate 5 General Firm Service from rateschedule_5.pdf: basic $469.00/month as printed by the tariff though the business page says daily, Rider 2 $0.40/month, demand $37.735/GJ/month of daily demand; and seasonal Rate 4 Apr 1-Nov 1 from rateschedule_4.pdf: $14.4230/day basic, off-peak $2.204 / extension $3.268 per GJ; effective July 1 2026, BCUC G-131-26; Fort Nelson 4/5 have no price table), Energir 4 (D3/D4 from article 14.3: subscribed-volume bands in $/m³/day, conditional above-subscribed withdrawal and load-balancing; D1 and D3/D4 fail independently; live D3 supersedes the old estimate), Heritage/Eastward 3 (Rate Class 3: $1,995.54/month, $0.167/GJ, $30.85 per GJ Billing Demand/month from tariff PDF Schedule 3 page 10; Rate Class 4 negotiated, unpublished) and Liberty NB 4 (Off-Peak Service $50.00/month, $5.6244/GJ, Apr-Nov eligibility, $10/GJ Dec-Mar overrun as a note). Guarded store validated all 19 records, appended 19 snapshots (1,301 total); prior snapshots and non-target tariffs unchanged. Browser preview checked (156 live default, no JS errors, no mobile overflow).
- Export: 638 stored versions / 4,123 components / 158 stored live / 480 seed; 156 latest live across 18 utilities; 154 latest live across all 16 target utilities. Tests: 551 passing.
- Next: remaining catalogue gaps at all 16 utilities. Gas: Revelstoke propane, FortisBC Rates 6/7 and Fort Nelson 4/5; Energir D5, inventory adjustments, load-factor formula, fixed-price/renewable supply; Liberty CGS/ICGS (process loads) and marketer prices; SaskEnergy small industrial/fees; Centra PUB conditions. Then electricity building-catalogue audits (BC Hydro business, Manitoba Hydro, NB Power, Maritime Electric, Newfoundland Power) and recorded electricity gaps (see matrix).

## Previous snapshot (2026-10-02)
- Reconciled against the 2026-10-02 19:08 UTC export: 135 latest live records across 12 of the 16 target utilities. The other two nationwide live records are FortisAlberta and Yukon Energy, retained from earlier observations. Source dates were not refreshed during this documentation review.
- Export: 619 stored versions / 3,935 components / 139 stored live versions / 480 seed across 84 utilities; 137 latest live tariffs across 14 utilities. Batch 1 added HQ options, NL Hydro and SaskEnergy; batch 2 adds FortisBC Electric (6), NSPower MURB/solar (10 current total), and Centra Gas (12). Batch 2 preserved all 1,241 prior snapshots and 587 non-target records, appending 28 snapshots (1,269 total).
- Published implementation: `6cdbc67` (batch1) and `9b5980d` (batch2); Pages deployment for `9b5980d` was confirmed successful. Tests: 465 passing. SaskPower is the only recorded completed building-catalogue audit; other live utilities retain the documented gaps.
- Next: the four seed-only in-scope gas utilities (FortisBC Energy, Energir, Heritage/Eastward, Liberty NB), then remaining building-catalogue audits and recorded utility gaps. HQ DT/Flex D/Winter Credit, FortisBC Electric's first six schedules and NSPower MURB/solar are implemented, not full catalogue completion. Inukjuak/net-metering, broader business/rider/eligibility conditions and pilot restoration status remain explicit gaps. Do not restart excluded regions or farm/oil-field expansion.
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
- Deterministic tests block unmocked network access. Run `pytest -q` (551 tests); inspect targeted live dry runs separately. A generic verifier fixture or a successful fallback-only run does not establish a working live parser.

## Active Regional Implementation
- Only 16 registered utilities in BC/QC/MB/SK/NB/NS/PE/NL are in this run. ON/AB/YT/NT/NU remain untouched and retained in exports. Independent parser/fixture work may be parallel; shared tests/registry/docs/DB/export/git integration is serial. The active matrix queue supersedes its retained historical checkpoint instructions.
- HQ optional products: DT requires full equipment/temperature-zone/multiplier/credit/off-grid context. Flex D retains seasonal tiers and source-notified peak events. Winter Credit has its own curtailed-energy unit and reference-energy/temperature-adjustment/notice rules, with no calculated credit total; it is not another base rate. Inukjuak/net-metering/business options remain gaps.
- NL Hydro: 18 dated July 2026 classes retain service areas, government/non-government diesel, monthly blocks, native demand units and minimum/maximum bills as conditions. Fixed amperage/phase rows are mutually exclusive. Seasonal adjustments require the complete same-date base schedule and retain signup/term conditions. Net-metering/commissioning and contract-specific industrial applicability remain gaps, not automatically non-building exclusions.
- SaskEnergy: six residential/small/large-commercial full-service/delivery-only variants. Mandatory zero-carbon evidence is separately dated April 1, 2025; base components retain October 1, 2023. Assembled date uses the latest required component, preventing the older seed from superseding it in the browser. Do not infer private commodity prices, unit conversions, or industrial scope from a class label. Small-industrial and ancillary-charge audit remains incomplete.
- FortisBC Electric: six January 2026 schedules (1/2A/20/21/22A/23A). Footer-selected PDF extraction avoids table-of-contents stalls. Flat RS1 supersedes the old tiered price; RS2A requires its closed notice. Monthly/two-month units, source seasons/hours and required RS21 continuation are retained. Credits are negative/conditional; kVA demand is an alternative to kW. Large-commercial/Green Power/financing/net-metering/EV schedules remain gaps.
- NSPower additions: MURB89 requires the General/MURB FAM/DSM/storm rows, all three source pages, ten-unit/house-meter eligibility and minimum bill as a condition. The printed weekend/holiday peak-price rule was visually confirmed. Solar Garden and Community Solar use subscriber-attributable generation, not household consumption, and remain optional adjustments to base tariffs. No guessed enrollment, subscription size or bill offset.
- Centra: twelve August 2026 residential/commercial Sales/T-service/marketer variants. Separate delivery and volumetric demand components reconcile to source totals; totals are not added again. CRA evidence explicitly establishes Manitoba's zero fuel charge from April 2025. No heat-content conversion. Commodity must agree with the default quarterly table; private marketer prices are omitted explicitly. Full PUB eligibility/demand and alternate-supply conditions/fixed-term products remain review gaps.
- Next campaign queue: remaining building-catalogue audits and recorded gaps at all sixteen live target utilities (gas batch 3 completed FortisBC Energy, Energir, Heritage/Eastward and Liberty NB live output on 2026-10-05). ON/AB/YT/NT/NU remain excluded from this run.
