# Canada Utility Costs

**Browse electricity and natural gas rates across all Canadian provinces and territories.**

This project scrapes official utility rate data, stores it in a structured database, and
serves it as a clean, browsable static website via GitHub Pages. It focuses on the tariffs
needed to understand building energy costs.

## Quick Start

New to Python or the command line? Follow these steps in order. Type each command in a terminal
opened in the project folder (Windows: press `Win + R`, type `cmd`, press Enter; Mac: open
**Terminal**) and press Enter.

**You need:**

- **Python 3.10 or newer** from [python.org/downloads](https://www.python.org/downloads/). On
  Windows, tick **"Add Python to PATH"** during installation. `python --version` should then
  print something like `Python 3.12.1`.
- **A copy of this project:** with Git, run
  `git clone https://github.com/MaxPr1me/canada-utility-rates.git` and then
  `cd canada-utility-rates`. Without Git, click the green **Code** button on GitHub, choose
  **Download ZIP**, unzip it and open a terminal in that folder.

**1. Install the tools** (once; use the same Python 3.10+ environment for every step, ideally a
virtual environment):

```bash
pip install -r requirements.txt
pip install -e .
python -m playwright install chromium
```

The installs should finish without errors. Chromium is the hidden browser used for rate pages
that need JavaScript.

**2. Get a read-only copy of the database:**

```bash
python scripts/pull_history_db.py
```

It downloads `data/db/rates.db` from the project's `data-history` release on GitHub, checks it
against the SHA-256 fingerprint GitHub publishes and prints a line starting with `Installed`
(or saying "already matches" when your copy is current). An older copy moves to
`data/db/backups/`.

**3. Try a scrape without saving anything:**

```bash
python -m pipeline.run_scrape --dry-run
```

It reads the official utility websites (a full run takes several minutes) and ends with a
summary box: live and estimated record counts, any utility that returned only estimates, and
`(dry run — nothing saved to database)`. A finished run does not prove every rate was live:
read those counts.

**4. Export the website data:**

```bash
python -m pipeline.export_json
```

It writes the JSON files in `site/data/` (rates, utilities, summaries and the representative
models) and prints `JSON export complete`.

**5. View the website:**

```bash
python -m http.server --directory site 8000
```

Open http://localhost:8000 (pick another free port if 8000 is busy) to see five views: Rate
Browser, Market Pricing, Representative Models, Across-Canada and Compare. Opening the HTML file
directly (`file://`) does not load the data reliably. Press `Ctrl + C` to stop the server.

**Important limitations:**

- **Only the Monthly Scrape on GitHub stores data.** Your database is a read-only copy: never
  store scrapes locally or upload a database (see [How Monthly Updates Work](#how-monthly-updates-work)).
- **Estimated values are hidden by default.** Fallback (seed) values are shown only when you
  tick **"Show estimated (not live-verified) rates"** on the site.
- Representative models and market charts are comparison aids, never bills or forecasts.

More commands: [Common Commands](#common-commands). If something goes wrong:
[Troubleshooting](#troubleshooting).

---

## Current Status

- **Live output:** all 78 active registered utilities have stored live output.
- **Latest export (November 4, scrape run 33):** 917 latest live tariffs and 480 retained
  estimates; 1,336 stored live versions and 5,567 history snapshots. Counts include
  conditional products and reference-only records, not complete utility catalogues.
- **Corrections stored (verified November 4):** the targeted Monthly Scrapes stored Centra Gas
  Manitoba's 13 November records and Maritime Electric's first-20-kW-free demand tier; history
  checks, the strict coverage gate (78 of 78), the crosswalk (0 unmapped) and model parity pass.
- **"Coverage complete" is not claimed yet:** the scoped wording (78 active registered
  utilities) awaits the owner's approval.
- **Tests:** 2,252 tests across 38 test modules (run with `pytest tests`).

The [coverage matrix](docs/phase5_completion_matrix.md) holds the work queue; the
[parser gap report](docs/live_parser_gap_report.md) lists class-level gaps and exclusions.

---

## What This Project Does

1. **Scrapes** utility rate data from official Canadian utility websites.
2. **Stores** everything in a normalized SQLite database that preserves every rate detail — not just a single "cost per kWh" number.
3. **Tracks history** — each stored scrape appends snapshots. Only the Monthly Scrape workflow stores scrapes: it keeps `data/db/rates.db` in the `data-history` GitHub release with dated backups and checks that history only grows; local copies are read-only mirrors (`python scripts/pull_history_db.py`).
4. **Exports** the data as JSON for the GitHub Pages static site.
5. **Serves** a browsable web interface with five views: **Rate Browser** (multi-select filters, confidence indicators and source attribution), **Market Pricing** (observed Ontario and Alberta market history with a monthly chart, table and heatmap), **Representative Models** (typical monthly electricity costs for the ten provinces, without and with tax), **Across-Canada** (residential electricity compared by province) and **Compare** (two tariffs side by side, never a bill total).
6. **Provides automation** through monthly scraping, separate Pages deployment, non-blocking source-health runs, a twice-monthly Ontario Price archive and market history update, and Alberta market history and model refreshes.

**Scope: building energy costs.** The work supports building energy-cost analysis, including
work informed by **NECB 2025**, plus **single-family homes**: residential and multi-unit
residential, commercial, institutional and building-related industrial service (the tariffs
for building electricity, heating and other building systems). Tariff eligibility still comes
from the utility's published schedule; the project does not determine building-code
applicability or certify NECB compliance. Process-specific farm and oil-field service,
irrigation, NGV fuelling, EV charging, lighting, wholesale/reseller and standby-only service
are **not completion requirements**; schedules already implemented stay as reference. Shared
general-service tariffs may still matter to buildings even when other users can take them.
Record counts include reference-only records, not just building tariffs.

---

## Working Rules

Two rules govern every change to this project:

1. **Never display default values as if they were live.** Only rate values pulled from (or verified against) a live official web source are shown as current. Hardcoded seed/fallback values are a safety net only — they are marked `provenance: "seed"` (with `confidence: unverified`), hidden by default on the site, and revealed only via the labelled **"Show estimated (not live-verified) rates"** toggle. Never present a static default as a live-scraped rate.
2. **Do not assume scope.** If a requirement is unclear or has more than one reasonable interpretation, stop and ask which path to take before proceeding.

The full list of project safeguards is in [AGENTS.md — Project safeguards](AGENTS.md#project-safeguards).

---

## Project Structure

```
canada-utility-costs/
│
├── scrapers/                 ← The code that scrapes utility websites
│   ├── base.py               ← Shared scraper logic (all scrapers inherit from this)
│   ├── registry.py           ← Loads the source registry
│   ├── utils/                ← Shared helpers
│   │   ├── parsing.py        ← HTML / PDF / spreadsheet parsing + rate extraction
│   │   ├── validation.py     ← Data quality checks
│   │   ├── change_detection.py ← Compare live-parsed vs seed data, alert on drift
│   │   ├── market_pricing.py ← Reads the observed Ontario market history (rolling HOEP/Ontario Price + Class B GA; legacy 2020-2024 files still accepted)
│   │   ├── oeb_tariff.py     ← Ontario OEB Tariff of Rates and Charges PDF reader
│   │   ├── alberta_rolr.py   ← Shared Alberta Rate of Last Resort helpers (UCA cross-check, term gate)
│   │   └── logging_config.py ← Logging setup
│   └── utilities/            ← One scraper module per utility (Ontario distributors share one), plus the package initializer
│       ├── bc_hydro.py       ← BC Hydro (electricity, BC)
│       ├── hydro_quebec.py   ← Hydro-Québec (electricity, QC)
│       ├── ontario_ldc.py    ← All Ontario LDCs (one class; OEB tariff sheets via utils/oeb_tariff.py)
│       ├── toronto_hydro.py  ← Legacy, unregistered; current Toronto entry uses the LDC scraper
│       ├── enbridge_gas.py   ← Enbridge Gas (gas, ON)
│       ├── epcor_gas_ontario.py ← EPCOR Natural Gas (gas, ON: Aylmer and Southern Bruce)
│       ├── epcor_gas.py      ← Retired Alberta "EPCOR Natural Gas" entry (history only)
│       ├── atco_gas.py       ← ATCO Gas (gas, AB)
│       ├── atco_electric.py  ← ATCO Electric (distribution, AB)
│       ├── fortisalberta.py  ← FortisAlberta (distribution, AB)
│       ├── epcor_distribution.py ← EPCOR Distribution (AB)
│       ├── enmax_power.py    ← ENMAX Power (distribution, AB)
│       ├── direct_energy_regulated.py ← Direct Energy Regulated Services Rate of Last Resort (AB)
│       ├── enmax_energy.py   ← ENMAX Energy Rate of Last Resort (AB)
│       ├── epcor_energy_alberta.py ← EPCOR Energy Alberta Rate of Last Resort (AB)
│       ├── aeso.py           ← AESO market reference (AB)
│       ├── nl_hydro.py       ← NL Hydro (electricity, NL)
│       └── ...               ← Other provincial utilities
│
├── pipeline/                 ← Scripts that run the whole process
│   ├── run_scrape.py         ← Main entry: run scrapers → validate → store
│   ├── export_json.py        ← Export database → JSON for the website (also runs the model builder)
│   ├── representative_models.py ← Phase 7 representative models: crosswalk coverage, cost engine, Alberta pairs, 7E illustrative block
│   ├── diff_report.py        ← Compare two scrape runs to see changes
│   └── validate.py           ← Data quality checks
│
├── schema/                   ← Database definition
│   ├── create_tables.sql     ← SQL that creates all tables
│   └── schema_diagram.md     ← Visual diagram of the schema
│
├── data/                     ← Data files
│   ├── db/                   ← SQLite history database: read-only mirror of the CI copy (backups/ is git-ignored)
│   ├── exports/              ← CSV/Excel exports (optional)
│   ├── excel/                ← Audit reference files (not system of record, git-ignored)
│   ├── market/               ← Ontario and Alberta market history kept in git (outside the database)
│   │   ├── ontario_price_hourly.csv   ← Hourly Ontario Price archive (DA-OZP + LFDA) since July 11, 2026
│   │   ├── ontario_total_hourly.csv   ← Combined hourly energy + Class B GA, cents/kWh, with explicit gaps
│   │   ├── ontario_total_hourly_2020_2025.csv ← Requested fixed historical window
│   │   ├── ontario_total_monthly.csv ← Combined monthly reference prices, cents/kWh
│   │   ├── ontario_total_metadata.json ← Method, warnings and source fingerprints
│   │   ├── ieso_raw/                ← Permanent unverified official report captures and SHA-256 index
│   │   ├── ontario_market_monthly.csv ← Permanent monthly energy + Class B GA history since January 2020
│   │   ├── hoep_hourly.csv   ← Legacy hourly HOEP, January 2020-March 2025 (imported once)
│   │   ├── alberta_pool_hourly.csv    ← Hourly AESO pool prices (permanent raw history)
│   │   └── alberta_market_monthly.csv ← Permanent monthly Alberta pool-energy history
│   ├── models/               ← Phase 7 representative model inputs
│   │   ├── crosswalk.json    ← Ordered rules: live record → model key or exclusion reason; Alberta pairs
│   │   ├── usage_levels.json ← Usage levels, TOU/ULO shares, reference-customer charges, 7E synthetic profile
│   │   ├── block_periods.json ← Reviewed periods for block thresholds printed without one
│   │   └── taxes.json        ← Sales taxes and automatic point-of-sale rebates
│   ├── sources/registry.json ← Master list of where to find rate data
│   ├── sources/coverage_ledger.json ← Coverage audit ledger read by the coverage gate
│   └── inventory/            ← Full utility inventory
│
├── site/                     ← Static website (deployed to GitHub Pages)
│   ├── index.html            ← Five views, including separate Across-Canada and two-tariff Compare
│   ├── css/style.css         ← Styles inc. multi-select filters, heatmap, confidence
│   ├── css/models.css        ← Representative Models styles, incl. the illustrative (synthetic) block
│   ├── css/across-canada.css ← Residential national comparison table
│   ├── js/app.js             ← SPA logic: filters, cards, modal, market viz
│   ├── js/models.js          ← Representative Models, assumptions and shared lazy data loader
│   ├── js/across-canada.js   ← Residential comparisons using published model totals only
│   └── data/                 ← Six pipeline exports plus separately maintained market/audit data
│       ├── rates.json        ← All tariff/component data
│       ├── utilities.json    ← Utility metadata
│       ├── summary.json      ← Provincial summaries
│       ├── missing.json      ← Known data gaps
│       ├── missing_classes_report.json  ← Customer class coverage audit
│       ├── representative_models.json   ← Phase 7 models (ten provinces; Representative Models tab)
│       ├── market_pricing_ontario.json  ← Rolling 60-month market history + observed-hours bins (scripts/build_ontario_market.py)
│       ├── market_pricing_alberta.json  ← Alberta market history + observed-hours bins (scripts/build_alberta_market.py)
│       ├── market_structure_notes.json  ← All-province market research
│       └── source_review_report.json    ← Source URL audit report
│
├── scripts/                  ← Market data builders, database history tools and the graphify hook helper
│   ├── build_ontario_market.py    ← Rolling five-year Ontario market history (Ontario Price Archive workflow)
│   ├── archive_ontario_price.py   ← Extends the hourly Ontario Price archive (Ontario Price Archive workflow)
│   ├── preserve_ieso_reports.py  ← Saves raw IESO reports before any price-validation failure
│   ├── export_ontario_totals.py  ← Combines hourly/monthly energy + Class B GA without filling gaps
│   ├── build_alberta_market.py    ← Alberta AESO market history, checked against monthly summaries (Market Benchmarks workflow)
│   ├── generate_market_pricing.py ← Legacy 6A HOEP 2020-2024 surface (manual; its readers are reused by the builder)
│   ├── check_db_history.py        ← Monthly Scrape check: database integrity, history only grows
│   ├── coverage_gate.py           ← Live-rate coverage gate: live output, audit ledger, deferred and monitored items (Monthly Scrape reports it)
│   ├── pull_history_db.py         ← Downloads the CI history database into a read-only local mirror
│   └── graphify_hook.py           ← Optional graphify post-commit hook helper (see Graphify below)
│
├── tests/                    ← Regression tests (run them with: pytest tests)
│   └── fixtures/             ← Source-derived fixtures and frozen export samples; other tests also use inline text
├── docs/                     ← Guides and reference
├── .github/
│   ├── workflows/            ← GitHub Actions automation
│   ├── copilot-instructions.md ← Development workflow for AI agents
│   └── instructions/         ← Area rules for AI agents
├── graphify-out/             ← Code knowledge graph (optional developer tool; see Graphify below)
│
├── README.md                 ← This file
├── AGENTS.md                 ← Step-by-step guide for maintainers
├── requirements.txt          ← Python dependencies
├── requirements-graphify.txt ← Pinned graphify version (optional developer tool)
└── .graphifyignore           ← Paths graphify leaves out of the code graph
```

---

## Common Commands

Stored scrapes are made only by the Monthly Scrape workflow on GitHub; on your computer,
use `--dry-run` and get the history with `python scripts/pull_history_db.py`.

| What you want to do | Command |
|---|---|
| Get the CI history database (read-only mirror) | `python scripts/pull_history_db.py` |
| Initialize an empty practice database | `python -m pipeline.run_scrape --init-db` |
| Test-scrape all active utilities (nothing saved) | `python -m pipeline.run_scrape --dry-run` |
| Test-scrape one utility (nothing saved) | `python -m pipeline.run_scrape --utility "BC Hydro" --dry-run` |
| Test-scrape all utilities in a province (nothing saved) | `python -m pipeline.run_scrape --province ON --dry-run` |
| Export JSON for the website | `python -m pipeline.export_json` |
| Validate data quality | `python -m pipeline.validate` |
| Compare two scrape runs | `python -m pipeline.diff_report` |
| Check the representative-model crosswalk | `python -m pipeline.representative_models --coverage` |
| Build the representative models (summary; `--output PATH` writes the JSON) | `python -m pipeline.representative_models --build` |
| Rebuild the rolling Ontario market history (downloads IESO files) | `python scripts/build_ontario_market.py` |
| Rebuild the legacy 2020-2024 market surface (Phase 6A, manual; writes `logs/market_pricing_legacy_2020_2024.json` by default) | `python scripts/generate_market_pricing.py [--output PATH]` |
| Extend the hourly Ontario Price archive (downloads IESO files) | `python scripts/archive_ontario_price.py` |
| Rebuild combined Ontario cents/kWh CSVs from retained data | `python scripts/export_ontario_totals.py` |
| Check raw IESO preservation without writing | `python scripts/preserve_ieso_reports.py --dry-run` |
| Check the Alberta market history without publishing (downloads AESO files) | `python scripts/build_alberta_market.py --dry-run` |
| Record database statistics (the Monthly Scrape history check) | `python scripts/check_db_history.py stats --db data/db/rates.db --out stats.json` |
| Check live-rate coverage (the coverage gate) | `python scripts/coverage_gate.py` |
| Run tests | `pytest tests` |
| Serve the website locally | `python -m http.server --directory site 8000` |
| See verbose output (nothing saved) | `python -m pipeline.run_scrape --dry-run --verbose` |
| Check graphify, its hook and the code graph (optional) | `python scripts/graphify_hook.py status` |
| Install the graphify post-commit hook (optional; once per checkout) | `python scripts/graphify_hook.py install` |
| Rebuild the code graph from scratch (optional) | `python scripts/graphify_hook.py build` |
| Catch up the code graph by hand, in its own commit (optional) | `python scripts/graphify_hook.py refresh --commit` |

---

## How the Data Is Organized

The database stores rate data at **full granularity**. Instead of one "cost per kWh" number, it stores:

- **Fixed charges** — monthly or daily charges regardless of usage
- **Energy charges** — per-kWh or per-GJ costs, potentially with multiple tiers
- **Demand charges** — per-kW costs for commercial/industrial customers
- **Delivery charges** — distribution and transmission costs
- **Regulatory charges** — regulator fees
- **Riders** — temporary adjustments, credits, or surcharges
- **Carbon charges** — federal and provincial carbon levies
- **Market-indexed components** — prices linked to wholesale markets, stored with a market reference but no number (shown as "Variable"); observed market averages stay in the market history, never in a tariff

Each charge has its own row with:
- The rate value and unit
- Tier thresholds (for tiered pricing)
- TOU periods (for time-of-use pricing)
- Season (winter/summer if different)
- Source URL (where we found it)
- Confidence level (how sure we are it's correct)

**Representative models are derived, never stored as rates.** Every export runs
`pipeline/representative_models.py`, which uses the reviewed inputs in `data/models/`
(crosswalk, usage levels, block periods and taxes) to work out, for each of the ten provinces,
the median monthly electricity cost of its utilities' live tariffs at set example usage levels,
without and with tax, and writes `site/data/representative_models.json`. Models are labelled
modeled, are never a bill and never count as live coverage. [AGENTS.md](AGENTS.md) describes
their inputs and rules.

---

## How to Add a New Utility

See [docs/adding-a-utility.md](docs/adding-a-utility.md) for a detailed guide.

**Short version:**
1. Create a new file in `scrapers/utilities/`.
2. Write a class that inherits from `BaseScraper` and implements `scrape()`.
3. Add the utility to `data/sources/registry.json`.
4. Test with `python -m pipeline.run_scrape --utility "Your Utility" --dry-run`. After the code is pushed, the Monthly Scrape workflow stores it (start it by hand with the `utility` input, or wait for the 1st).

**A utility counts as done** when its standard published classes relevant to building energy
costs (including single-family homes) are accounted for with exact source, date, unit and
component context; source-derived fixtures prove extraction and failure handling; an
official-source dry run has been inspected; storage and export keep every component and
earlier snapshot; and the coverage ledger (`data/sources/coverage_ledger.json`) is updated.
Special, negotiated and closed-to-new schedules are identified where applicable. Unsupported
building classes are recorded as gaps, never invented; non-building services are explicit
exclusions. A generic verifier test or seed-only output is not a working parser.

---

## How Monthly Updates Work

The [Monthly Scrape workflow](.github/workflows/scrape.yml) runs on the 1st at 08:00 UTC or on
manual dispatch, with optional inputs for one `utility` or one two-letter `province` (not both;
the inputs reach the shell through environment variables). It is the **only writer** of the
history database `data/db/rates.db` (owner decision), kept as asset `rates.db` of the
`data-history` GitHub release:

1. **Restore:** if the release exists, the download must succeed and match the asset's SHA-256
   digest, or the run stops; only a missing release (HTTP 404) starts a new database.
   `scripts/check_db_history.py stats` records integrity-checked statistics right after the
   restore.
2. **Test, scrape, validate, export:** deterministic tests, the scrape (all active utilities, one
   utility or one province), validation, JSON export and a check that rejects empty exports.
3. **Check before upload:** `scripts/check_db_history.py verify` requires SQLite `integrity_check`
   "ok", no fewer snapshots, tariff versions or scrape runs, and every earlier snapshot unchanged
   (a digest over all earlier rows). It posts a public "Database history" notice on the run page.
4. **Upload:** a dated gzip backup (`rates-YYYY-MM-DD.db.gz`), then `rates.db`. The bot then
   commits `site/data/` (rebasing on `main` first, because the archive workflow also commits on
   the 1st), and dated backups are pruned to the newest 12.
5. **Failure issue:** a failed step opens a GitHub issue with the test, scrape, validation,
   database-history and diff output; a failed check uploads nothing.

Each scrape run also posts public notes on its run page: the live, estimated and invalid
totals with any failed or estimates-only utility, and a report-only "Coverage gate" result that
never blocks the save. The step summary and full logs need a GitHub sign-in.

Local machines never upload: `python scripts/pull_history_db.py` downloads the public release
copy, checks its digest and keeps the old local copy in `data/db/backups/` (git-ignored). To store
new data, push the code and start Monthly Scrape (optionally for one utility or one province), or
wait for the 1st. `python -m pipeline.run_scrape --province XX` skips merged and retired registry
entries. **Risk:** deleting the `data-history` release deletes `rates.db` and every backup.

**Other workflows:**

- [Deploy Site](.github/workflows/deploy.yml) publishes the site on push or manual dispatch,
  and by itself after each successful Monthly Scrape, Ontario Price Archive or Market Benchmarks
  run; it checks out `main`. A failed data run that still committed new data needs a manual
  deploy.
- [Source Health](.github/workflows/source-health.yml) runs a non-blocking dry run on the 15th
  and uploads its log without publishing; it installs Playwright Chromium.
- [Ontario Price Archive](.github/workflows/ontario-price-archive.yml) runs at 06:00 UTC on the
  1st and 15th and after relevant code pushes. It first commits the raw IESO reports, then
  extends and commits `data/market/ontario_price_hourly.csv`, then runs
  `scripts/build_ontario_market.py` (also when the archive step failed, using the archive
  already committed), the combined-price export and the models, and commits those separately.
  A failure opens an issue whose title says which part failed.
- [Market Benchmarks](.github/workflows/market-benchmarks.yml) runs after the Monthly Scrape and
  Ontario Price Archive workflows and after relevant code or model-input pushes. It publishes
  the Alberta market history and refreshes the representative models without touching the
  database, and opens an issue if it fails.

The three data workflows take turns publishing. Every workflow runs on `ubuntu-24.04`, and steps
that pipe output into `tee` run under `bash -o pipefail`, so a failing command still fails its
step. GitHub Pages must use **GitHub Actions** as its source, and `workflow_run` triggers fire
only from the default branch.

---

## Source Data & Market Pricing

### Source Hierarchy

The project prioritizes data sources in this order:
1. **Utility-owned rate pages** — the utility's own published rates
2. **Regulator filings** — OEB rate orders, BCUC decisions, AUC filings
3. **Third-party aggregators** — only when no direct source is available

`data/sources/registry.json` is the **system of record** for source URLs. Some scraper
modules still fetch URL constants directly, so source corrections must update both the
registry and the owning scraper where necessary. The Excel reference file
(`data/excel/old_urls.xlsm`) is audit-only and is never read by a scraper.

### Ontario Market Pricing (rolling five-year history)

The Market Pricing dashboard shows what market-billed Ontario electricity really cost over the
**latest 60 complete months** (owner decision): the energy price is the legacy Hourly Ontario
Energy Price (HOEP) up to April 2025 and the Ontario Price after it, plus the actual monthly
Class B Global Adjustment (GA). Full cost = energy + Class B GA. It is observed history for
comparison, never a tariff, a bill or a forecast.

**HOEP retired:** the IESO retired the HOEP on April 30, 2025. Since May 1, 2025 market-billed
customers pay the Ontario Electricity Market Price (OEMP, "the Ontario Price": the Day-Ahead
Ontario Zonal Price plus the Load Forecast Deviation Adjustment) plus GA. An always-visible note
on the dashboard says so and links to the IESO's current Ontario market prices. The page shows
the old and new markets as one continuous total because energy plus Class B GA stayed similar
after the change while energy alone did not: GA moves opposite to the energy price.

**Complete months:** a month enters the window when it has ended, its energy value is validated
(legacy HOEP: the hourly mean matches the IESO HOEP Monthly Averages report within 0.01 $/MWh;
Ontario Price: listed in the IESO monthly table, and a month the archive covers must match it
within 0.01 $/MWh) and its Class B GA actual rate is published (IESO Data Directory workbook or
monthly GA reports; where both exist they must agree within 0.005 $/MWh). April 2025 uses the
report value and has no observed hours, because the April mean of the IESO yearly hourly file
(39.181 $/MWh) disagrees with the monthly report (39.22).

**Heatmap (observed hours only, owner decision):** 576 bins (12 months x weekday/weekend x 24
hours, hour beginning EST; a statutory holiday counts as the weekday it falls on) built only
from hours with a recorded price; each cell shows how many hours it averages. The hourly Ontario
Price from May 1, 2025 to July 10, 2026 is no longer published (the IESO keeps about 90 days of
daily files, and its website's chart data reaches back only about 10 days), so that gap is
disclosed and never filled with modelled hours. As archived months enter the window, the
Ontario Price share of the heatmap grows.

**Files:**
- `data/market/ontario_market_monthly.csv`: the permanent monthly history since January 2020:
  era, energy (arithmetic and demand-weighted), Class B GA, total, sources and observed hours.
  It is never trimmed; a month may be revised only within 6 months of its end.
- `data/market/hoep_hourly.csv`: legacy hourly HOEP, January 1, 2020-March 31, 2025, imported
  once with `--refresh-hoep`; CI never downloads legacy HOEP files.
- `data/market/ontario_price_hourly.csv`: the hourly Ontario Price archive (below).
- `site/data/market_pricing_ontario.json` (schema 2, `derivation_method`
  `observed_rolling_60m_hoep_oemp_ga`): metadata (window, eras, gap, change date, source codes,
  cross-checks), the 60 monthly records and the 576 bins with `hours_hoep` and `hours_oemp`.

**Updating:** `scripts/build_ontario_market.py` runs in the Ontario Price Archive workflow after
the archive commit (`--dry-run` checks everything without writing; `--help` lists the other
options). In CI it downloads only the IESO monthly table page, the GA workbooks and the monthly
GA reports. It fails closed: on any missing or inconsistent input it writes nothing and exits
with an error, and a run without new data leaves every file unchanged.
`scrapers/utils/market_pricing.py` and the site accept only observed files (this rolling method
or the legacy one below); otherwise the site shows a "not available" notice.

**Ontario Price archive:** `scripts/archive_ontario_price.py` keeps what is still published:
`data/market/ontario_price_hourly.csv` holds one row per hour from July 11, 2026 with DA-OZP,
LFDA, OEMP, the report version and the LFDA status (Final or Preliminary). A blank LFDA hour
stays blank, never zero (the IESO's published monthly LFDA averages leave blanks out). Every
complete month must match the IESO's monthly Ontario Price table within 0.01 $/MWh for DA-OZP,
LFDA and OEMP (owner decision: all three strict); otherwise the validated CSV is unchanged and
the workflow opens an issue.

**Raw IESO reports:** before any price check, the workflow commits the original daily DA-OZP and
yearly LFDA reports under [data/market/ieso_raw/](data/market/ieso_raw/)
(`scripts/preserve_ieso_reports.py`). Original bytes are compressed, SHA-256 checked and kept by
content hash; new revisions and even malformed responses never overwrite older captures. Raw
files are **unverified** source evidence, not prices to use in calculations.
`scripts/archive_ontario_price.py --raw-dir data/market/ieso_raw --no-site-api` can recover
retained daily reports after the IESO removes them, while LFDA and monthly checks still require
live sources. A failed validation does not undo the raw commit. If saving to GitHub itself
fails, the run keeps a recovery artifact for 90 days and opens an issue: download it and repair
the failure promptly. This protects future captures but cannot recover the old hourly gap.

**Combined energy + Class B GA prices** (no need to join energy and GA yourself):

| File | Contents |
|---|---|
| [2020-2025 hourly totals](data/market/ontario_total_hourly_2020_2025.csv) | All **52,608** hourly slots, in **CAD cents/kWh**, IESO hour-ending 1-24 EST |
| [Permanent hourly totals](data/market/ontario_total_hourly.csv) | January 2020 onward; extended with the archive |
| [Permanent monthly totals](data/market/ontario_total_monthly.csv) | Published arithmetic energy + Class B GA averages, in cents/kWh |
| [Method, sources and coverage](data/market/ontario_total_metadata.json) | Formula, source fingerprints, status definitions and caveats |

`total_cents_per_kwh = (hourly energy $/MWh + monthly Class B GA $/MWh) / 10`. These are
**energy-plus-GA totals, not complete bills**: delivery, losses, other fees and taxes are
excluded. Missing totals stay blank: the 2020-2025 file has 46,728 numeric hourly totals and
5,880 missing hours (May-December 2025). The separate `monthly_average_total_cents_per_kwh`
column is a **monthly reference**, never an hourly observation. April 2025's 720 official HOEP
hours appear only in these exports, flagged `observed_monthly_mismatch` (see "Complete months"
above); the original [2025 IESO report](data/market/PUB_PriceHOEPPredispOR_2025_v119.csv) is
preserved byte-for-byte. These files do not change the stricter site heatmap or the model
calculations. Rebuild them offline with `python scripts/export_ontario_totals.py` (`--dry-run`
writes nothing); the Ontario Price Archive workflow refreshes them after each market build.

**Legacy surface (Phase 6A):** `scripts/generate_market_pricing.py` (manual) still builds the
fixed 2020-2024 HOEP surface from the IESO yearly hourly reports (`PUB_PriceHOEPPredispOR_YYYY`)
and the Data Directory GA workbook, cross-checking all 60 monthly means against the HOEP Monthly
Averages report; the rolling builder reuses its readers. By default it writes the git-ignored
scratch file `logs/market_pricing_legacy_2020_2024.json`, so it cannot replace the rolling site
file by accident. GA defaults the owner may change, kept in both builds: April-June 2020 use the
published capped 115 $/MWh (provincial emergency order; unadjusted 150.57, 147.18 and 128.40),
the 2021 actual rates exclude the separate 2021 recovery rates (5.01-7.09 $/MWh), and holidays
count as weekdays.

### Alberta Deregulated Market

Alberta distribution (wires), default retail and AESO wholesale observations are separate data
sources and stay separate records. The four wires utilities (ENMAX Power, ATCO Electric, EPCOR
Distribution, FortisAlberta) keep distribution and transmission (System Access Service) charges
as separate components and current riders as dated components. The **Rate of Last Resort**
(RoLR), which replaced the Regulated Rate Option on January 1, 2025, is live for its three
providers (Direct Energy Regulated Services, ENMAX Energy and EPCOR Energy Alberta): a fixed
energy price for the term ending December 31, 2026, cross-checked with the Utilities Consumer
Advocate (UCA) default-rates table. These records fail closed after the term ends until the next
term is published; old RRO seeds remain labelled history. Competitive retail contracts are not
included. AESO's pool price is a live market reference with no stored number.

**Alberta market history:** `scripts/build_alberta_market.py` reads the official AESO hourly
pool prices and checks every monthly arithmetic average against AESO's **Pool Monthly Summary**
within $0.01/MWh. It keeps permanent raw hourly (`data/market/alberta_pool_hourly.csv`) and
monthly (`data/market/alberta_market_monthly.csv`) history and publishes
`site/data/market_pricing_alberta.json` for the Market Pricing page's Alberta region: 60 complete
months and 576 heatmap bins from observed hours. Published AESO hour-ending labels keep the
skipped spring hour and the repeated autumn `02*` hour; they are not Ontario EST timestamps.
Missing hours never become zero, and Alberta never uses Ontario's GA. Every refresh rechecks all
archived months; a changed archived price stops publication for source review instead of
guessing a correction. The Market Benchmarks workflow publishes it; check it without publishing
with `python scripts/build_alberta_market.py --dry-run`. The owner confirmed AESO permission for
public raw hourly archives and derived charts and benchmarks; the grant itself was not
independently inspected.

### Market Prices in Tariffs and Models

- **Tariffs never hold market averages.** A tariff part that follows a market price (for
  example Ontario non-RPP demand-class energy, EPCOR Distribution's operating reserve and AESO's
  pool price) is stored with a market reference and no number; the site shows it as
  "Variable". For Ontario demand classes, Class A Global Adjustment (by peak demand factor) is a
  conditional note.
- **Representative models** show delivery charges with *market energy pending* wherever the
  energy itself is market-priced (Ontario and Alberta demand classes); they never guess a
  number. Alberta's wires + Rate of Last Resort pairs apply only below 250,000 kWh a year, the
  RoLR limit.
- **Historical market benchmark (method 7C-4):** for Ontario and Alberta medium and large
  commercial demand models, a separate figure adds the average energy price of 60 complete
  months (each month counts equally) to the modeled delivery charges. Ontario adds actual Class
  B GA; Alberta uses pool energy alone. Energy is added before zone aggregation and taxes.
  Losses, retail fees, Class A and unpriced conditional charges are not included, and a
  province's benchmark is unavailable when its history is missing or invalid or its 60-month
  window is more than four months old. It is **not a customer-profile-weighted bill or
  forecast**, does not replace the base model and is not used in the Across-Canada comparison.
- **Illustrative estimate (7E):** for Ontario's two larger business sizes only, an opt-in
  estimate prices market energy with a made-up (synthetic) business-hours load profile
  (`synthetic_profiles` in `data/models/usage_levels.json`). It is hidden behind a checkbox,
  carries a warning and a SYNTHETIC badge, and is never used in medians, outliers, comparisons
  or change detection. It is not a forecast, a quote or a bill.
- Real commercial load profiles are not qualified yet, so no profile-weighted or all-in bill is
  claimed.

### Other Provinces

Ownership and market structure vary by province, including Crown, investor-owned and
municipal utilities. The market-structure research notes are reference material, not a
substitute for current approved tariff documents.

---

## How to Verify a Rate Is Still Valid

1. Open the database or the exported `site/data/rates.json`.
2. Find the tariff you want to check.
3. Look at the `source_url` field — this is the official page where the rate was found.
4. Visit that URL and compare the numbers.
5. Check the `effective_date` and `confidence` fields.
6. If the rate has changed, update the parser and its source-derived fixture. A seed update alone does not establish live provenance.

---

## Troubleshooting

### "No utilities found in registry"
→ Make sure `data/sources/registry.json` exists and has entries.

### "Database not found"
→ Run `python scripts/pull_history_db.py` to download the read-only copy of the database (or `python -m pipeline.run_scrape --init-db` for an empty practice database).

### A scraper fails with a connection error
→ The utility's website may be down or may have changed its URL. Check the `source_url` in the registry.

### Validation warnings about high values
→ The validation catches unreasonable rates (like $100/kWh). Check if the scraper is parsing correctly or if the utility actually has that rate.

### The website shows no data
→ Make sure you have the database and have run `python -m pipeline.export_json`; the site reads from `site/data/rates.json`. Serve the site over HTTP as in the [Quick Start](#quick-start) instead of opening the file directly.

### The Ontario Price Archive workflow opened an issue
→ A monthly check against the IESO's published Ontario Price table failed, or an official file could not be read, so the validated archive was not changed (raw reports are saved separately before the checks). Run `python scripts/archive_ontario_price.py --no-site-api --raw-dir data/market/ieso_raw --dry-run` to see which month or file failed, and fix it soon: the IESO deletes each daily price file after about 90 days. If the issue says raw report preservation failed, download the run's `ieso-raw-recovery` artifact promptly.

### An issue says "Ontario market history update failed"
→ The archive part of the run was saved; only the market history build failed closed and wrote nothing, so the Market Pricing page keeps its previous data. Run `python scripts/build_ontario_market.py --dry-run` to see the reason (for example a month that disagrees with the IESO table) and fix it before the next run on the 1st or 15th.

### The database history check failed
→ The Monthly Scrape found a problem with `data/db/rates.db` (a failed restore or digest, a failed integrity check, fewer snapshots, tariff versions or scrape runs, or a changed earlier snapshot) and uploaded nothing, so the release copy is unchanged. Read the "Database History" part of the issue. Do not upload a database by hand: fix the cause, then start Monthly Scrape again.

### Market Benchmarks opened an issue
→ A step of the run failed (its tests, the Alberta market history build or the model refresh), so nothing new was published and the site keeps its previous data. A missing hour, a changed source format, a disagreement with AESO's official monthly price or a changed already-archived price stops publication on purpose. Run `python scripts/build_alberta_market.py --dry-run` to see the reason. Do not overwrite archived evidence or guess a correction.

### A workflow log warns that `git` exited with code 128
→ Harmless: it comes from the checkout clean-up, because two committed `.claude/worktrees` links have no `.gitmodules` entry.

More problems and step-by-step fixes are in [AGENTS.md](AGENTS.md) ("What to Do When Something Breaks").

---

## Graphify (optional developer tool)

[graphify](https://graphify.com) turns the code into a searchable knowledge graph in
`graphify-out/` that AI assistants query before reading files. You do not need it to scrape,
test or publish rates, and GitHub Actions never installs it.

**Install once per computer.** You need Python 3.10 or newer, Git and
[uv](https://docs.astral.sh/uv/). The version is pinned in
[requirements-graphify.txt](requirements-graphify.txt):

    uv tool install graphifyy -c requirements-graphify.txt   # recommended: isolated install
    pip install -r requirements-graphify.txt                  # alternative: inside the project's virtual environment

Restart VS Code afterwards so new terminals and AI agents find `graphify`. For the `/graphify`
chat skill, run `graphify vscode install`, then `git restore .github/copilot-instructions.md`
(the installer adds a section that this repository already covers).

**Turn on automatic updates once per checkout.**

    python scripts/graphify_hook.py install   # adds the post-commit hook only
    python scripts/graphify_hook.py status    # checks the graphify version, the hook and the graph

After each commit that changes code, the hook updates the graph and records it in a separate
commit named `chore(graphify): refresh code graph for <commit>`. It never pushes. Commits that
change only documentation skip it. If other uncommitted changes could have reached the graph,
it refreshes the files but leaves them uncommitted. Skip it once by setting
`GRAPHIFY_SKIP_HOOK=1`. A code commit takes longer while the graph updates (up to about a
minute on a slow Windows machine).

**What is in the graph.** Application code only: `.graphifyignore` leaves out tests, the data
folders, the database schema and workflow YAML. Communities get automatic names; no AI model is
called. The views are `graph.html` (interactive graph), `GRAPH_TREE.html` (file tree),
`GRAPH_CALLFLOW.html` (call flow by project area), `wiki/index.md` and `GRAPH_REPORT.md`.

**Other commands.** `python scripts/graphify_hook.py build` rebuilds the graph from scratch
(needed after changing the pin or `.graphifyignore`; review the result, then commit
`graphify-out/`). `python scripts/graphify_hook.py refresh --commit` catches up by hand, and
`uninstall` removes the hook. To upgrade graphify, change the pin, reinstall, run `build` and
`python -m pytest tests/test_graphify_hook.py`, then commit.

---

## Data Format Recommendation

**Primary storage: SQLite** — because it's a single file, needs no server, supports full SQL queries, and works on every platform.

**Static site consumption: JSON** — the browser can't query SQLite directly, so we export to JSON files that the JavaScript app loads.

**Optional: CSV exports** — for people who want to open data in Excel or Google Sheets.

---

## Roadmap

One line per phase; sub-phase detail and the work queue are in the
[coverage matrix](docs/phase5_completion_matrix.md).

- **Earlier phases (foundations)** — done: scraper framework, granular schema, registry, validation, history snapshots, JSON export and the website.
- **Phase 5: Live Parser Completion** — in progress: every active registered utility has live output (see Current Status); the Centra and Maritime corrections are stored and verified (November 4), the scoped coverage-complete claim awaits owner approval, and remaining building-catalogue gaps are tracked in the coverage matrix.
- **Phase 6: Market Integration** — in progress (6A, 6B, 6C and 6D done; 6E gas commodity cadence started).
- **Phase 7: Representative Models** — in progress (7A, 7B, 7C and 7F done, including the separate historical market benchmarks of method 7C-4; 7E is only an opt-in illustrative estimate, not a true all-in bill; 7D gas is a proposal only).
- **Phase 8: Representative Model Refresh Automation** — planned (design reviewed, not implemented; the proposed 2% change threshold is not approved).
- **Phase 9: Product Follow-up** — started (residential Across-Canada comparison done; historical charts, AI-ready exports, a bill calculator or API and commercial/gas comparisons are planned).

---

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| Scraping | Python + requests + BeautifulSoup | Standard, reliable, huge community |
| JS-rendered pages | Playwright (headless Chromium) | Renders JS-heavy rate pages when the static HTML lacks the data |
| PDF parsing | pdfplumber | Best Python PDF table extractor |
| Database | SQLite | Zero setup, single file, full SQL |
| Validation | Dataclass records + custom checks | Checks structure, provenance and rate plausibility; Pydantic is installed but is not the record model |
| Static site | HTML + CSS + vanilla JS + Chart.js | No build step, works on GitHub Pages |
| Automation | GitHub Actions | Free for public repos, built-in cron |
| Testing | pytest | Standard Python testing |
| Code knowledge graph (optional dev tool) | graphify, pinned in requirements-graphify.txt | Lets AI assistants navigate the code |

---

## License

This project collects publicly available rate data from official utility websites. The data itself belongs to the respective utilities and regulators. This tool is for informational and educational purposes.

---

## Contributing

The immediate priority is **complete existing live parsers and their source-derived
fixtures**, not add more seed-only coverage. See [docs/adding-a-utility.md](docs/adding-a-utility.md)
and the [coverage matrix](docs/phase5_completion_matrix.md).
