# Canada Utility Costs

**Browse electricity and natural gas rates across all Canadian provinces and territories.**

This project scrapes official utility rate data, stores it in a structured database, and serves it as a clean, browsable static website via GitHub Pages.

## Scope: Building Energy Costs

The active parser campaign supports building energy-cost analysis, including work
informed by **NECB 2025**, plus **single-family homes**. Prioritize residential and
multi-unit residential, commercial, institutional and building-related industrial
service: the tariffs needed for building electricity, heating and other building systems.
Tariff eligibility still comes from the utility's published schedule; this project
does not determine building-code applicability or certify NECB compliance.

Process-specific farm and oil-field service, irrigation, NGV fuelling, EV charging,
lighting, wholesale/reseller and standby-only service are **not completion requirements**. Already
implemented schedules and data remain as reference, including farm/oil-field work,
but further expansion of those classes is deferred. Shared general-service tariffs may
still be relevant to buildings even when the utility also offers them to other users.
Inventory counts below include reference-only records, not just building tariffs.

## Current Status (2026-10-16)

The framework and website are implemented; **nationwide live-rate coverage is not complete**.
The tariff export was regenerated on **2026-10-09** after batch 12 (scrape run 27: Alberta electricity
plus all 47 Ontario distributors re-stored with PUC Distribution and Phase 6B; scrape run 28:
Ontario/Alberta gas). History was preserved. October 15 added CI fixes, the Representative
Models tab and the Ontario Price archive. October 16 (batch 14) fixed EPCOR Energy Alberta's moved
pages, made CI the only writer of the history database, turned the Market Pricing page into a
rolling five-year history and built representative models for all ten provinces (7C) plus a
clearly labelled illustrative estimate (7E). No scrape was stored on either day, so the tariff
counts below are still batch 12's.
A successful source check and an export timestamp are different facts;
unverified fallback records remain estimates regardless of the export date.

| Measure | Exported state |
|---|---|
| Registered utilities | 87: 77 electricity and 10 gas, across all 13 provinces/territories (8 absorbed Ontario entries marked `merged`; the mis-registered Alberta "EPCOR Natural Gas" entry marked `retired`) |
| Stored tariff versions / components | 1,396 / 14,179, including history and older estimates |
| Live-sourced tariffs | **910 latest tariffs across 77 utilities**; 916 stored live versions |
| Active regional campaign | **243 latest live records across all 16 provincial target utilities**; 109 across the four territorial utilities |
| Ontario electricity | **490 latest live records across all 47 active distributors** from OEB-approved tariff sheets (PUC Distribution configured October 9) |
| Alberta electricity (batch 12) | **28 latest live records**: ENMAX Power, ATCO Electric, EPCOR Distribution and FortisAlberta wires (5 each) plus 8 Rate of Last Resort records from three providers |
| Ontario/Alberta gas (batch 12) | **40 latest live records**: Enbridge Gas 20, ATCO Gas 10, EPCOR Natural Gas (Ontario) 10 |
| Active utilities without live output | **1**: AESO, a market reference; every other active utility has live output, with recorded gaps |
| Seed/fallback tariffs | **480**, hidden by default |
| SaskPower live tariffs | **41**, including reference-only records; scoped building schedules implemented |
| Historical snapshots | **3,616**; batch 12 runs 27 and 28 appended 563 and 40 without changing prior snapshots |
| DB validation | **0 errors, 2 existing AESO warnings** |
| Representative models | **55** across the ten provinces (October 16, method 7C-2): 16 modeled, 20 single-source, 6 *market energy pending*, 13 not computable; comparison indicators, never live coverage |
| Deterministic tests | **1,863 passing** across 14 modules (October 16) |

Live output currently includes BC Hydro (17), FortisBC Electric (11), Manitoba Hydro (18), NB Power (10),
Nova Scotia Power (18), Hydro-Quebec (26), Maritime Electric (10), Newfoundland Power (11),
NL Hydro (21), SaskPower (41), SaskEnergy (8), Centra Gas Manitoba (13), FortisBC Energy (27),
Energir (5), Heritage/Eastward (3), Liberty NB (4), NTPC (63), Qulliq Energy (6), Yukon Energy (20),
ATCO Electric Yukon (20); in Alberta ENMAX Power (5), ATCO Electric (5), EPCOR Distribution (5),
FortisAlberta (5), Direct Energy Regulated Services (2), ENMAX Energy (2) and EPCOR Energy
Alberta (4); Enbridge Gas (20), ATCO Gas (10) and EPCOR Natural Gas (Ontario) (10); and all 47
active Ontario distributors (490; Hydro One 50, Alectra 44, Elexicon 19, ERTH 18, Enova 16,
GrandBridge 16, North Bay 15, Newmarket-Tay 14, Toronto 12, Algoma 10, PUC Distribution 7 and
others; see the matrix).
These counts use the latest version per tariff, not complete utility catalogues.
They include conditional products, adjustment-only records and retained non-building
references, not a count of complete building classes. Yukon Energy and ATCO Electric Yukon
publish the same 20 joint YUB schedules; NTPC's 63 include 52 per-community government
records. Ontario non-RPP demand classes list their delivery charges plus a market energy component with
no stored number (shown as "Variable"; the observed market history from Phase 6A stays in the Market
Pricing view and is never copied into a tariff). Alberta wires records
keep distribution and transmission separate; Rate of Last Resort energy is a separate retail
record. AESO is the only active registered utility without live output.

**Where we stand (October 16):** the 20-utility regional campaign is closed out (batch 11), all 47
active Ontario distributors are live, and batch 12 added Alberta electricity (four wires
utilities and the three Rate of Last Resort providers), Ontario/Alberta gas (Enbridge Gas, ATCO
Gas and a new EPCOR Natural Gas (Ontario) entry that replaces a retired, mis-registered Alberta
entry), PUC Distribution and value-less market energy components for Ontario demand classes
(Phase 6B). A per-run live/seed summary in `run_scrape` is published, and every scrape run posts
a public live/seed notice. Batch 14 (October 16; commits `a919684`, `b070725`, `49a0daa`):

- **Lane F:** EPCOR Energy Alberta moved its Rate of Last Resort pages (the FortisAlberta-area
  residential page had returned 404 since October 15). The registry and scraper follow the new
  addresses and a dry run gives 4 live records again (12.01 cents/kWh); the next CI Monthly Scrape
  stores them.
- **CI is the only writer of the history database** (user decision): the Monthly Scrape restores
  `data/db/rates.db` from the `data-history` release, checks it and uploads it with a dated backup
  only after a history-only-grows check passes. Local copies are read-only mirrors
  (`python scripts/pull_history_db.py`), and nobody stores scrapes locally (see
  [How Monthly Updates Work](#how-monthly-updates-work)). Not yet exercised in a real CI run.
- **Market Pricing** shows a rolling five-year history: the latest 60 complete months (September
  2021-August 2026), the legacy HOEP to April 2025 and then the Ontario Price, plus the actual
  Class B Global Adjustment: 10.40 cents/kWh on average. The heatmap uses observed hours only, and
  the Ontario Price Archive workflow rebuilds the history twice a month (see
  [Ontario Market Pricing](#ontario-market-pricing-rolling-five-year-history)).
- **Representative models** ([Phase 7](#phase-7-representative-models-in-progress)): 7A, 7B and
  now 7C are done. Every export writes electricity models for all ten provinces (in Alberta each
  wires utility is paired with the Rate of Last Resort provider for its area) to
  `site/data/representative_models.json`, and the site's **Representative Models** tab (7F) shows
  them. They are labelled modeled, are never billed tariffs and never count as live coverage.
  **7E is illustrative only:** the two Ontario demand-class models carry a separate all-in estimate
  built from a made-up (synthetic) business-hours load profile, hidden behind a checkbox, labelled
  SYNTHETIC and never used in medians, outliers or comparisons; it needs further analysis.

**Next (in order, October 16):**

1. **First CI runs (owner):** start **Monthly Scrape** by hand: its first run as the only writer
   (restore and checks, store including the Lane F record, backup asset, bot commit, then Deploy
   Site through `workflow_run`); and start **Ontario Price Archive** (archive plus market history
   build). Otherwise both run on November 1. Check each step before trusting it.
2. **Manitoba Hydro block parser fix:** its stored energy blocks are malformed (tier numbers 1 and
   3; "Next 8,500 kWh" stored as a cumulative bound; single- and three-phase basic charge
   variants), so three Manitoba commercial models are not computable.
3. **Decisions:** the length of NB Power's and Maritime Electric's "Billing Period" (their block
   thresholds state no period); a reference customer for amperage/phase fixed-charge alternatives
   (Newfoundland Power, NL Hydro); 30-day versus 30.4375-day months (Hydro-Quebec and Manitoba
   Hydro define a month as 30 days; the engine uses 30.4375).
4. **7E further analysis:** compare the synthetic profile with real commercial load profiles, test
   other business hours, use an Ontario Price-era hourly shape once 12 archived months exist, and
   look at Class A and loss factors.
5. **Remaining lanes:** C (Phase 6D: BC Hydro RS1892, FortisBC Electric RS38, NSPower one-part
   real-time pricing and NL Hydro monthly non-firm prices as value-less "Variable" components),
   E (optional items, each after a yes/no decision; listed in the matrix queue), D (Phase 6C,
   Alberta market), 7D gas, Phase 8 (automatic model refresh; must ignore illustrative values) and
   Phase 9 (product follow-up, including the Across-Canada comparison).
6. **Calendar:** November 1, new OEB RPP prices and the next RPP Price Report's TOU/ULO shares
   (update `data/models/usage_levels.json` by hand); November 15, Ontario Price Archive and Source
   Health.

See the [coverage matrix](docs/phase5_completion_matrix.md) for the implementation queue
and [parser gap report](docs/live_parser_gap_report.md) for class-level details.
A successful scrape can return only seeds; success counts and an empty missing-data log
do **not** prove live coverage.

The regional campaign covers 16 registered utilities in BC/QC/MB/SK/NB/NS/PE/NL plus,
from October 7, the four territorial utilities (non-market regulated service).
Ontario electricity distribution ran as its own block (batches 1-2 on October 7-8; PUC
Distribution added October 9), and batch 12 (October 9) covered Alberta electricity and
Ontario/Alberta gas. From October 6,
building-related industrial general facility classes are in scope, including those
defined by size, voltage or interruptibility. Process-specific farm, oil-field,
irrigation, NGV fuelling, EV charging, lighting, wholesale/reseller and standby-only
services remain excluded. See the [coverage matrix](docs/phase5_completion_matrix.md)
for the queue and the [parser gap report](docs/live_parser_gap_report.md) for parser rules.

---

## What This Project Does

1. **Scrapes** utility rate data from official Canadian utility websites.
2. **Stores** everything in a normalized SQLite database that preserves every rate detail — not just a single "cost per kWh" number.
3. **Tracks history** — each stored scrape appends snapshots. Since October 16 only the Monthly Scrape workflow stores scrapes: it keeps `data/db/rates.db` in the `data-history` GitHub release with dated backups and checks that history only grows; local copies are read-only mirrors (`python scripts/pull_history_db.py`).
4. **Exports** the data as JSON for the GitHub Pages static site.
5. **Serves** a browsable web interface with multi-select filters, confidence indicators, source attribution, an interactive Market Pricing dashboard (a rolling five-year observed Ontario market history: legacy HOEP, then the Ontario Price, plus Class B GA) with a monthly chart, table and heatmap, and a Representative Models view (typical monthly electricity costs for the ten provinces, without and with tax).
6. **Provides automation** through monthly scraping, separate Pages deployment, non-blocking source-health runs and a twice-monthly Ontario Price archive and market history update. The monthly publication chain and the market history build still await their first CI runs.

---

## Working Rules

Two rules govern every change to this project:

1. **Never display default values as if they were live.** Only rate values pulled from (or verified against) a live official web source are shown as current. Hardcoded seed/fallback values are a safety net only — they are marked `provenance: "seed"` (with `confidence: unverified`), hidden by default on the site, and revealed only via the labelled **"Show estimated (not live-verified) rates"** toggle. Never present a static default as a live-scraped rate.
2. **Do not assume scope.** If a requirement is unclear or has more than one reasonable interpretation, stop and ask which path to take before proceeding.

---

## Quick Start (For Beginners)

If you've never used Python or the command line before, follow these steps exactly.

### Step 1: Install Python

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download **Python 3.10 or newer** for your computer.
3. **Important:** During installation, check the box that says **"Add Python to PATH"**.
4. After installing, open a terminal:
   - **Windows:** Press `Win + R`, type `cmd`, press Enter.
   - **Mac:** Open Spotlight (Cmd + Space), type `Terminal`, press Enter.
5. Type `python --version` and press Enter. You should see something like `Python 3.12.1`.

### Step 2: Download This Project

If you have Git installed:
```bash
git clone https://github.com/MaxPr1me/canada-utility-rates.git
cd canada-utility-rates
```

If you don't have Git, click the green **"Code"** button on GitHub and download the ZIP file. Unzip it and open a terminal in that folder.

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
pip install -e .
python -m playwright install chromium
```

**What this does:** Installs the Python libraries and Chromium needed for JavaScript-rendered rate pages. Use the same Python 3.10+ environment for installation, tests, and scraping. A virtual environment is recommended; an older or empty environment will not work just because it is activated.

### Step 4: Get the History Database

```bash
python scripts/pull_history_db.py
```

**What this does:** Downloads the project's history database (`data/db/rates.db`) from the public
`data-history` GitHub release, checks it against the SHA-256 digest GitHub publishes and keeps any
older local copy in `data/db/backups/`. Since October 16 only the Monthly Scrape workflow writes
the real history; your copy is a read-only mirror. For an empty practice database instead, run
`python -m pipeline.run_scrape --init-db`.

### Step 5: Try a Scrape Without Saving

```bash
python -m pipeline.run_scrape --dry-run
```

**What this does:** Runs every active scraper, fetches rate data from official utility websites
and validates it, without storing anything. To store new data, push your code and start the
**Monthly Scrape** workflow (optionally for one utility or one province), or wait for the 1st of
the month. Do not store scrapes in a local copy, and never upload one.

The end-of-run summary counts live and seed (estimated) records and names seed-only
utilities; on GitHub Actions the same table is written to the run's Summary page. A final
`utilities succeeded` count only means execution completed, not that every rate was live.
Network retries and rendered pages can make a full scrape take several minutes.

### Step 6: Export Data for the Website

```bash
python -m pipeline.export_json
```

**What this does:** Reads the database and creates JSON files in `site/data/` that the static website uses. Run `python -m pipeline.validate` first to check the database.

### Step 7: View the Website Locally

Serve the site over HTTP so the browser can fetch its JSON files:

```bash
python -m http.server --directory site 8000
```

Open http://localhost:8000. If that port is occupied, choose another free port.
Opening the HTML directly with `file://` is not a reliable way to load the data.

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
│   └── utilities/            ← 34 scraper modules + package initializer; 87 registered utilities
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
│   ├── market/               ← Ontario market history kept in git (outside the database)
│   │   ├── ontario_price_hourly.csv   ← Hourly Ontario Price archive (DA-OZP + LFDA) since July 11, 2026
│   │   ├── ontario_market_monthly.csv ← Permanent monthly energy + Class B GA history since January 2020
│   │   └── hoep_hourly.csv   ← Legacy hourly HOEP, January 2020-March 2025 (imported once)
│   ├── models/               ← Phase 7 representative model inputs
│   │   ├── crosswalk.json    ← Ordered rules: live record → model key or exclusion reason; Alberta pairs
│   │   ├── usage_levels.json ← Usage levels, TOU/ULO shares, reference-customer charges, 7E synthetic profile
│   │   ├── block_periods.json ← Reviewed periods for block thresholds printed without one
│   │   └── taxes.json        ← Sales taxes and automatic point-of-sale rebates
│   ├── sources/registry.json ← Master list of where to find rate data
│   └── inventory/            ← Full utility inventory
│
├── site/                     ← Static website (deployed to GitHub Pages)
│   ├── index.html            ← Main page: Rate Browser, Market Pricing, Representative Models and Compare tabs
│   ├── css/style.css         ← Styles inc. multi-select filters, heatmap, confidence
│   ├── css/models.css        ← Representative Models styles, incl. the illustrative (synthetic) block
│   ├── js/app.js             ← SPA logic: filters, cards, modal, market viz
│   ├── js/models.js          ← Representative Models tab (loads its JSON on first open)
│   └── data/                 ← Six pipeline exports plus separately maintained market/audit data
│       ├── rates.json        ← All tariff/component data
│       ├── utilities.json    ← Utility metadata
│       ├── summary.json      ← Provincial summaries
│       ├── missing.json      ← Known data gaps
│       ├── missing_classes_report.json  ← Customer class coverage audit
│       ├── representative_models.json   ← Phase 7 models (ten provinces; Representative Models tab)
│       ├── market_pricing_ontario.json  ← Rolling 60-month market history + observed-hours bins (scripts/build_ontario_market.py)
│       ├── market_structure_notes.json  ← All-province market research
│       └── source_review_report.json    ← Source URL audit report
│
├── scripts/                  ← Market data builders and database history tools
│   ├── build_ontario_market.py    ← Rolling five-year Ontario market history (Ontario Price Archive workflow)
│   ├── archive_ontario_price.py   ← Extends the hourly Ontario Price archive (Ontario Price Archive workflow)
│   ├── generate_market_pricing.py ← Legacy 6A HOEP 2020-2024 surface (manual; its readers are reused by the builder)
│   ├── check_db_history.py        ← Monthly Scrape check: database integrity, history only grows
│   └── pull_history_db.py         ← Downloads the CI history database into a read-only local mirror
│
├── tests/                    ← 1,863 deterministic tests across 14 test modules
│   ├── fixtures/             ← Source-derived fixtures and frozen export samples; other tests also use inline text
├── docs/                     ← Guides and reference
├── .github/workflows/        ← GitHub Actions automation
│
├── README.md                 ← This file
├── AGENTS.md                 ← Step-by-step guide for maintainers
└── requirements.txt          ← Python dependencies
```

---

## Common Commands

Stored scrapes are made only by the Monthly Scrape workflow (since October 16); on your computer,
use `--dry-run` and get the history with `python scripts/pull_history_db.py`.

| What you want to do | Command |
|---|---|
| Get the CI history database (read-only mirror) | `python scripts/pull_history_db.py` |
| Initialize an empty practice database | `python -m pipeline.run_scrape --init-db` |
| Scrape all active utilities | `python -m pipeline.run_scrape` |
| Scrape one utility | `python -m pipeline.run_scrape --utility "BC Hydro"` |
| Scrape all utilities in a province | `python -m pipeline.run_scrape --province ON` |
| Dry run (scrape but don't save) | `python -m pipeline.run_scrape --dry-run` |
| Export JSON for the website | `python -m pipeline.export_json` |
| Validate data quality | `python -m pipeline.validate` |
| Compare two scrape runs | `python -m pipeline.diff_report` |
| Check the representative-model crosswalk | `python -m pipeline.representative_models --coverage` |
| Build the representative models (summary; `--output PATH` writes the JSON) | `python -m pipeline.representative_models --build` |
| Rebuild the rolling Ontario market history (downloads IESO files) | `python scripts/build_ontario_market.py` |
| Rebuild the legacy 2020-2024 market surface (Phase 6A, manual; its default output would overwrite the rolling site file) | `python scripts/generate_market_pricing.py --output PATH` |
| Extend the hourly Ontario Price archive (downloads IESO files) | `python scripts/archive_ontario_price.py` |
| Record database statistics (the Monthly Scrape history check) | `python scripts/check_db_history.py stats --db data/db/rates.db --out stats.json` |
| Run tests | `pytest` |
| Serve the website locally | `python -m http.server --directory site 8000` |
| See verbose output | `python -m pipeline.run_scrape --verbose` |

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

---

## How to Add a New Utility

See [docs/adding-a-utility.md](docs/adding-a-utility.md) for a detailed guide.

**Short version:**
1. Create a new file in `scrapers/utilities/`.
2. Write a class that inherits from `BaseScraper` and implements `scrape()`.
3. Add the utility to `data/sources/registry.json`.
4. Test with `python -m pipeline.run_scrape --utility "Your Utility" --dry-run`. After the code is pushed, the Monthly Scrape workflow stores it (start it by hand with the `utility` input, or wait for the 1st).

---

## How Monthly Updates Work

The [Monthly Scrape workflow](.github/workflows/scrape.yml) runs on the 1st at 08:00 UTC or on
manual dispatch, with optional inputs for one `utility` or one two-letter `province` (not both;
the inputs reach the shell through environment variables). Since October 16 (user decision) it is
the **only writer** of the history database `data/db/rates.db`, kept as asset `rates.db` of the
`data-history` GitHub release:

1. **Restore:** if the release exists, the download must succeed and match the asset's SHA-256
   digest, or the run stops; only a missing release (HTTP 404) starts a new database. Before
   October 16 a failed lookup silently started an empty database, which the `--clobber` upload
   could then have used to wipe the history. `scripts/check_db_history.py stats` records
   integrity-checked statistics right after the restore.
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

Local machines never upload: `python scripts/pull_history_db.py` downloads the public release
copy, checks its digest and keeps the old local copy in `data/db/backups/` (git-ignored). To store
new data, push the code and start Monthly Scrape (optionally for one utility or one province), or
wait for the 1st. `python -m pipeline.run_scrape --province XX` skips merged and retired registry
entries. **Risk:** deleting the `data-history` release deletes `rates.db` and every backup.

[Deploy Site](.github/workflows/deploy.yml) is a separate push/manual workflow with a
`workflow_run` trigger after a successful Monthly Scrape; it checks out `main`.
[Non-blocking Source Health](.github/workflows/source-health.yml) runs on the 15th
and uploads a dry-run log without publishing; it installs Playwright Chromium.
[Ontario Price Archive](.github/workflows/ontario-price-archive.yml) runs at 06:00 UTC on the 1st
and 15th. It extends `data/market/ontario_price_hourly.csv` and commits it first, then runs
`scripts/build_ontario_market.py` and commits `site/data/market_pricing_ontario.json` and
`data/market/ontario_market_monthly.csv` in a second commit. A failure opens an issue whose title
says which part failed.

**CI status (October 16):** steps that pipe output into `tee` run under `bash -o pipefail`, so a
failing command fails its step; all workflows run on `ubuntu-24.04`; and each scrape run posts a
public notice on its run page with the live, seed and invalid totals and any failed or seed-only
utility (the step summary and logs need a GitHub sign-in). Deploy Site succeeds on every push.
[Source Health run #6](https://github.com/MaxPr1me/canada-utility-rates/actions/runs/38808829718)
(October 15, started by hand, 13 minutes) passed: live 909, seed 46, invalid 0; 78 utilities, 45
of them with both live and seed records; no failures; AESO the only seed-only utility. The one
missing live record was EPCOR Energy Alberta's FortisAlberta-area residential Rate of Last
Resort, whose page had moved; Lane F fixed it on October 16. A warning that `git` exited with code
128 also appears on earlier runs; its cause is not known yet (it needs the signed-in log). The
owner created the `data-history` release from the local database on October 15 (48,701,440
bytes, the same SHA-256 as the local file).

**Not yet exercised in a real CI run:** the new restore, check, upload and backup chain, the
automatic failure issues, Deploy Site starting after a successful Monthly Scrape (`workflow_run`)
and the Ontario Price Archive workflow with its market history build. The owner may start both
from the **Actions** tab; otherwise they run on November 1. GitHub Pages must use
**GitHub Actions** as its source, and `workflow_run` fires from the default branch.

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
**latest 60 complete months** (user decisions October 15-16): the energy price is the legacy
Hourly Ontario Energy Price (HOEP) up to April 2025 and the Ontario Price after it, plus the
actual monthly Class B Global Adjustment (GA). Full cost = energy + Class B GA. It is observed
history for comparison, never a tariff, a bill or a forecast.

**HOEP retired:** the IESO retired the HOEP on April 30, 2025. Since May 1, 2025 market-billed
customers pay the Ontario Electricity Market Price (OEMP, "the Ontario Price": the Day-Ahead
Ontario Zonal Price plus the Load Forecast Deviation Adjustment) plus GA. An always-visible note
on the dashboard says so and links to the IESO's current Ontario market prices.

**Current window (October 16):** September 2021-August 2026, 44 legacy HOEP months and 16 Ontario
Price months (September 2026 is not in the IESO monthly table yet). Average full cost 104.02
$/MWh = 10.40 cents/kWh (energy 4.49 + GA 5.92); 10.13 cents/kWh in the legacy months and 11.16
in the Ontario Price months. The page shows a headline, the window, a monthly chart of energy, GA
and total with May 2025 marked, a 60-row monthly table with each month's era and sources, the
heatmap and the methodology.

**Complete months:** a month enters the window when it has ended, its energy value is validated
(legacy HOEP: the hourly mean matches the IESO HOEP Monthly Averages report within 0.01 $/MWh;
Ontario Price: listed in the IESO monthly table, and a month the archive covers must match it
within 0.01 $/MWh) and its Class B GA actual rate is published (IESO Data Directory workbook or
monthly GA reports; where both exist they must agree within 0.005 $/MWh). April 2025 uses the
report value and has no observed hours, because the April mean of the IESO yearly hourly file
(39.181 $/MWh) disagrees with the monthly report (39.22).

**Heatmap (user option a):** 576 bins (12 months x weekday/weekend x 24 hours, hour beginning EST;
a statutory holiday counts as the weekday it falls on) built from **observed hours only**: 32,640
of the window's 43,824 hours (31,392 legacy HOEP hours, 96.2%; 1,248 Ontario Price hours, 3.8%).
Weekday bins hold 63-89 hours and weekend bins 25-37, and each cell shows its hour count. The
hourly Ontario Price from May 1, 2025 to July 10, 2026 is no longer published (the IESO keeps
about 90 days of daily files, and its website's chart data reaches back only about 10 days), so
that gap is disclosed and never filled with modelled hours. As archived months enter the window,
the Ontario Price share of the heatmap grows.

**Files:**
- `data/market/ontario_market_monthly.csv`: the permanent monthly history (80 months, January
  2020-August 2026): era, energy (arithmetic and demand-weighted), Class B GA, total, sources and
  observed hours. It is never trimmed; a month may be revised only within 6 months of its end.
- `data/market/hoep_hourly.csv`: legacy hourly HOEP, January 1, 2020-March 31, 2025 (46,008
  hours), imported once with `--refresh-hoep`; CI never downloads legacy HOEP files.
- `data/market/ontario_price_hourly.csv`: the hourly Ontario Price archive (below).
- `site/data/market_pricing_ontario.json` (schema 2, `derivation_method`
  `observed_rolling_60m_hoep_oemp_ga`): metadata (window, eras, gap, change date, source codes,
  cross-checks), the 60 monthly records and the 576 bins with `hours_hoep` and `hours_oemp`.

**Updating:** `scripts/build_ontario_market.py` (options `--output`, `--monthly-csv`,
`--hoep-csv`, `--archive`, `--cache-dir`, `--as-of`, `--dry-run`, `--refresh-hoep`) runs in the
Ontario Price Archive workflow after the archive commit. In CI it downloads only the IESO monthly
table page, the GA workbooks and the monthly GA reports (18 files). It fails closed: on any
missing or inconsistent input it writes nothing and exits with an error, and a run without new
data leaves every file unchanged. All 80 monthly values matched the October 15 comparison to the
cent. `scrapers/utils/market_pricing.py` and the site accept only observed files (this rolling
method or the legacy one below); otherwise the site shows a "not available" notice.

**Legacy surface (Phase 6A, October 9):** `scripts/generate_market_pricing.py` (manual; options
`--start-year`/`--end-year`, default 2020 and 2024, `--output`, `--cache-dir`) still builds the
fixed 2020-2024 HOEP surface from the IESO yearly hourly reports (`PUB_PriceHOEPPredispOR_YYYY`)
and the Data Directory GA workbook, cross-checking all 60 monthly means against the HOEP Monthly
Averages report; the rolling builder reuses its readers. Its default `--output` is still
`site/data/market_pricing_ontario.json`, so pass another path: by default it would replace the
rolling file. GA defaults the user may change, kept in
both builds: April-June 2020 use the published capped 115 $/MWh (provincial emergency order;
unadjusted 150.57, 147.18 and 128.40), the 2021 actual rates exclude the separate 2021 recovery
rates (5.01-7.09 $/MWh), and holidays count as weekdays.

**Ontario Price archive (since October 15):** `scripts/archive_ontario_price.py` keeps what is
still published: `data/market/ontario_price_hourly.csv` holds one row per hour from July 11, 2026
(2,352 hours to October 16) with DA-OZP, LFDA, OEMP, the report version and the LFDA status
(Final or Preliminary). A blank LFDA hour stays blank, never zero (the IESO's published monthly
LFDA averages leave blanks out). Every complete month must match the IESO's monthly Ontario Price
table within 0.01 $/MWh for DA-OZP, LFDA and OEMP (user decision: all three strict); otherwise
nothing is written and the workflow opens an issue. Fix such an issue before the oldest
unarchived daily files disappear.

**Old and new market compared (October 15):** what a market-billed Class B customer pays, energy
plus Class B GA, stayed similar after the change, while energy alone did not. The HOEP years
2020-2024 averaged 106.15 $/MWh in total (energy 28.98 + GA 77.17). The first 12 months of the
Ontario Price (May 2025-April 2026) averaged 108.44 and the latest 12 (September 2025-August
2026) 111.08, with 10 and 9 of the 12 months inside the range of the same calendar month in the
HOEP years; energy alone fell inside that range in only 3 and 2 months. With the separate 2021
GA recovery rates added to the HOEP years, the latest 12 months are only partly similar (8 of
12). GA moves opposite to the energy price (monthly correlation -0.94 in the HOEP years, -0.97 to
-0.99 since), so the total is steadier than either part. That is why the page shows the old and
new markets as one continuous total (done October 16).

Ontario demand-class tariffs never copy these averages: their non-RPP records carry a market
energy component with no stored number (Phase 6B), and Class A Global Adjustment (by peak demand
factor) is a conditional note. The only model use is the Phase 7E **illustrative** estimate, which
weights the monthly values with a synthetic load profile (see Phase 7).

### Alberta Deregulated Market

Alberta distribution (wires), default retail and AESO wholesale observations are separate
data sources and stay separate records. Since batch 12 (October 9) the four wires utilities
(ENMAX Power, ATCO Electric, EPCOR Distribution, FortisAlberta) are live, with distribution and
transmission (System Access Service) charges as separate components and current riders as
dated components. The **Rate of Last Resort** (RoLR), which replaced the Regulated Rate Option on
January 1, 2025, is live for its three providers: a fixed energy price to December 31, 2026
(Direct Energy Regulated Services 12.02, ENMAX Energy 12.06 and EPCOR Energy Alberta 12.01
cents/kWh), cross-checked with the Utilities Consumer Advocate (UCA) default-rates table.
These records fail closed after the term ends until the next term is published; old RRO
seeds remain labelled history. Competitive retail contracts are not included. AESO pool-price
observations remain a market reference for Phase 6C. The representative models (7C, October 16)
pair each wires utility with the Rate of Last Resort provider for its area, but only below
250,000 kWh a year, the RoLR limit; larger commercial models show wires charges with market
energy pending until 6C.

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
→ Run `python -m pipeline.run_scrape --init-db` first.

### A scraper fails with a connection error
→ The utility's website may be down or may have changed its URL. Check the `source_url` in the registry.

### Validation warnings about high values
→ The validation catches unreasonable rates (like $100/kWh). Check if the scraper is parsing correctly or if the utility actually has that rate.

### The website shows no data
→ Make sure you've run `python -m pipeline.export_json` after scraping. The site reads from `site/data/rates.json`.

### The Ontario Price Archive workflow opened an issue
→ A monthly check against the IESO's published Ontario Price table failed, or an official file could not be read, so nothing was written. Run `python scripts/archive_ontario_price.py --dry-run` to see which month or file failed, and fix it soon: the IESO deletes each daily price file after about 90 days.

### An issue says "Ontario market history update failed"
→ The archive part of the run was saved; only the market history build failed closed and wrote nothing, so the Market Pricing page keeps its previous data. Run `python scripts/build_ontario_market.py --dry-run` to see the reason (for example a month that disagrees with the IESO table) and fix it before the next run on the 1st or 15th.

### The database history check failed
→ The Monthly Scrape found a problem with `data/db/rates.db` (a failed restore or digest, a failed integrity check, fewer snapshots, tariff versions or scrape runs, or a changed earlier snapshot) and uploaded nothing, so the release copy is unchanged. Read the "Database History" part of the issue. Do not upload a database by hand: fix the cause, then start Monthly Scrape again.

---

## Data Format Recommendation

**Primary storage: SQLite** — because it's a single file, needs no server, supports full SQL queries, and works on every platform.

**Static site consumption: JSON** — the browser can't query SQLite directly, so we export to JSON files that the JavaScript app loads.

**Optional: CSV exports** — for people who want to open data in Excel or Google Sheets.

---

## Roadmap

### Delivered Foundations

Earlier phases delivered the scraper framework, granular schema, 84-entry registry,
seed class models, validation, local historical snapshots and JSON export. The website
has multi-select filters, detail/source views, estimated-rate hiding, side-by-side
comparison without bill totals, a Market Pricing dashboard and (since October 15) a
Representative Models view. These are implemented
features, **not evidence that all registered utilities or published classes are live**.

### Phase 5: Live Parser Completion

| Phase | Work and completion gate | Status |
|---|---|---|
| 5A: Baseline | Dated inventory, honest README, shared class-level coverage ledger | Updated October 1 |
| 5B: SaskPower | Standard/bulk-metered/diesel residential, general-service/voltage/TOU and renewable-access schedules | Audited building scope implemented October 1; 41 live tariffs total including retained non-building reference records |
| 5C: Residential products and building-service expansion | Review optional residential plans and retain building-service gaps | Nine batches delivered; remaining building catalogues still incomplete |
| 5D: Provincial/territorial depth | Building-class audits at already-live utilities; later territorial coverage | NL Hydro 21 records implemented; territories reopened October 7 (NTPC, Qulliq, Yukon Energy and ATCO Electric Yukon live) |
| 5E: Gas | Building heating/service tariffs preserving zones, components, units and dates | All nine active gas utilities have live output: the six campaign utilities plus, from batch 12 (October 9), Enbridge Gas (20), ATCO Gas (10) and the new EPCOR Natural Gas (Ontario) entry (10), which replaces a retired, mis-registered Alberta entry; building-service gaps and open decisions remain |
| 5F: Alberta electricity | Building-relevant wires/default retail products; separate AESO reference where required | Batch 12 (October 9): ENMAX Power, ATCO Electric, EPCOR Distribution (2026 interim rates, medium confidence) and FortisAlberta live (5 each; transmission and dated riders separate) plus Rate of Last Resort energy from all three providers (8); AESO stays a market reference (Phase 6C); transmission-connected and admin-charge decisions open. EPCOR Energy Alberta moved its Rate of Last Resort pages (404 from October 15); fixed October 16 (Lane F: a dry run gives 4 live again; the next CI Monthly Scrape stores it) |
| 5G: Ontario | Batches 1-2 (October 7-8) plus PUC Distribution (October 9; its tariff prints no connection rate, noted on each record): all 47 active distributors live from OEB tariff sheets (490 records); rejected classes no longer re-emit estimates. Non-RPP demand classes carry a value-less market energy component (Phase 6B) | Done for active distributors; tariff market energy stays value-less (the observed 6A history is shown only in the Market Pricing view) |
| 5H: Reliable publication | Source-health/browser setup, live-vs-fallback reporting, failure notifications, deployment trigger and durable CI history | Browser setup, failure issues, deployment trigger and release-asset history implemented; per-run live/seed summary published (October 9) and, since October 15, a public notice on every scrape run, steps that fail under `pipefail` and runners pinned to `ubuntu-24.04`. **October 16: CI is the only writer of the history database:** the restore must succeed and match the asset's SHA-256 digest, integrity and history-only-grows checks run before the upload, dated backups are pruned to the newest 12, a public "Database history" notice is posted and a `province` input was added; local copies are read-only mirrors. Verified in CI: Deploy Site on every push and Source Health run #6 (October 15: live 909, seed 46, AESO the only seed-only utility; a local dry run matched). Not yet exercised: the Monthly Scrape's database chain, failure issues and `workflow_run` deployment, and the Ontario Price Archive workflow with its market history build (the owner may start them; otherwise November 1) |

**Definition of done for each utility:** account for the standard published classes
relevant to building energy costs, including single-family homes,
retain exact source/date/unit/component context, prove extraction and failure handling
with source-derived fixtures, inspect an official-source dry run, verify repeat
storage/export without lost components or history, and update the coverage ledger.
Known failures remain unverified; unsupported building classes are recorded as gaps,
never invented. Non-building services are explicit exclusions, not blockers to building
coverage. Special/negotiated and closed-to-new schedules must be identified where
applicable. Do not equate a generic verifier test with a working parser.

Utility-specific research can run independently; shared registry, database and export
updates are integrated serially. Completed batches are published at tested milestones;
the roadmap is not a promise to complete all Canadian parsers in one session.

### Future Phases (renumbered October 8)

The original document phases ended at Phase 5. Future work now runs in this order:
**6 Market Integration -> 7 Representative Models -> 8 Representative Model Refresh
Automation -> 9 Product Follow-up** (including the Across-Canada comparison). Phase 5
parser work for Alberta electricity, ON/AB gas and PUC Distribution was delivered in batch 12
(October 9); remaining catalogue gaps and open decisions continue alongside the later phases.

### Phase 6: Market Integration (in progress)

Market-priced energy gets its own phase before any model or comparison uses it. Every
market price needs an official source, a stated pricing period and a freshness date; modeled
values are labelled modeled and are never presented as a tariff. A market-indexed part of a
tariff is stored as a component without a number, with its market reference and source URL; the
site shows it as "Variable". Observed averages stay in the market history (6A) and are never
copied into a tariff.

| Phase | Work and completion gate | Depends on | Status |
|---|---|---|---|
| 6A: Ontario market observations | Replace the fixed generator inputs of the Ontario market model with reproducible official IESO observations (hourly energy prices and actual Class B Global Adjustment) and freshness checks; correct the market-model metadata and UI disclosure | - | **Done.** October 9 (legacy history): the IESO keeps only about 90 days of hourly day-ahead zonal price files, so the user chose observed legacy HOEP hourly prices for 2020-2024 plus actual monthly Class B Global Adjustment rates (`scripts/generate_market_pricing.py`: all 60 monthly averages cross-checked; fails closed). October 15: hourly Ontario Price archive (from July 11, 2026). **October 16: rolling five-year history** (`scripts/build_ontario_market.py`): the latest 60 complete months (legacy HOEP to April 2025, then the Ontario Price) plus Class B GA, a permanent monthly CSV since January 2020 and a heatmap from observed hours only (the gap May 1, 2025-July 10, 2026 disclosed), rebuilt twice a month by the Ontario Price Archive workflow; a month enters the window only once its energy and GA values are published and validated |
| 6B: Ontario demand-class energy | Attach modeled market energy (wholesale price plus Class B GA) to GS 50-4,999 kW and Large Use delivery-only records as labelled components; Class A noted as conditional | 6A for observed averages | **Implemented October 9 (batch 12) as value-less components:** non-RPP demand classes (including Hydro One UGd/GSd/AUGd/AGSd and ST) carry "Market Energy (Ontario Electricity Market Price + Class B Global Adjustment)" with a market reference and the IESO source URL; Class A and RPP eligibility are conditional notes; Algoma R2 (residential dwellings stay RPP-eligible) has none |
| 6C: Alberta market | AESO pool price observations; default retail (RoLR) energy from 5F; optional Alberta region in the Market Pricing dashboard if its variation warrants it (Alberta-specific values, sources, periods and methodology, never Ontario's market-price-plus-GA assumptions; wholesale, retail and wires kept distinct) | 5F | Planned. RoLR fixed prices are live from 5F; EPCOR Distribution's operating reserve charge (a percentage of the pool price) is stored value-less |
| 6D: Deferred market-indexed products | FortisBC Electric RS38 (Mid-C), BC Hydro RS1892, NSPower one-part real-time pricing, NL Hydro monthly non-firm (5.1L, Island non-thermal) | 6A methods | Planned |
| 6E: Gas commodity cadence | Quarterly QRAM (Ontario) and monthly default supply (Alberta GCFR) as dated commodity components with their refresh cadence | ON/AB gas parsers | Partly started: the batch 12 parsers store the current Enbridge and EPCOR QRAM gas supply prices and Direct Energy Regulated Services' monthly default rate as dated commodity components; cadence and freshness checks remain |

### Phase 7: Representative Models (in progress)

A new **Representative Models** section gives, for each province (territories later), one modeled
tariff per sector (residential, commercial) and per rate structure actually offered there
(for example Ontario TOU, Tiered, ULO and GS demand; Quebec Rate D; BC tiered/flat/TOD).
These are comparison indicators built from live records. They are **not tariffs anyone is
billed**, are labelled `provenance: "modeled"`, are never counted as live coverage and are
never shown as a utility's rate. The Phase 9 Across-Canada comparison reads these models for
its provincial values instead of computing its own blends.

**Decisions (user, October 8):** median across utilities (each utility counts once); a
province/structure with one utility uses that utility's tariff, labelled single-source; the
target is a full all-in price including energy/commodity (market-priced energy comes from the
market model and is labelled modeled); a dedicated site view next to Rate Browser, Market
Pricing and Compare; planned now, implemented later. The October 8 scratch prototype
(`logs/_on2_r_model.py`: typical monthly delivery varied about 18% across 46 distributors,
Hydro One the main outlier) is superseded by the 7B engine.

**Status (October 16):** 7A, 7B and 7C are done for electricity in all ten provinces (method
7C-2), and the site's Representative Models tab (7F) shows them; 7E exists only as a clearly
labelled illustrative estimate (below). Every export writes `site/data/representative_models.json`
(compact JSON, about 0.8 MB). Of the 910 latest live records, 557 are mapped to a model, 353 are
excluded with a reason and 0 are unmapped. The 55 models by province:

| Province | Models | Modeled | Single source | Market energy pending | Not computable | Residential at 1,000 kWh, $/month without / with tax |
|---|---|---|---|---|---|---|
| AB | 6 | 3 | - | 3 | - | 225.16 / 236.42 (flat; 4 wires + Rate of Last Resort pairs) |
| BC | 6 | 5 | 1 | - | - | 157.21 / 165.08 (flat; 2 utilities); tiered 133.02 / 139.67 (BC Hydro) |
| MB | 5 | - | 2 | - | 3 | 129.22 / 144.73 (Manitoba Hydro) |
| NB | 4 | - | 1 | - | 3 | 189.22 / 201.76 (NB Power) |
| NL | 6 | 2 | 1 | - | 3 | Withheld: Newfoundland Power is not computable |
| NS | 6 | - | 6 | - | - | 211.36 / 221.93 (Nova Scotia Power) |
| ON | 9 | 6 | - | 3 | - | 192.11 / 171.94 (TOU; 47 distributors) |
| PE | 4 | - | - | - | 4 | Not computable: "Billing Period" length not stated |
| QC | 5 | - | 5 | - | - | 84.70 / 97.38 (Rate D) |
| SK | 4 | - | 4 | - | - | 185.92 / 195.22 (SaskPower) |
| **Total** | **55** | **16** | **20** | **6** | **13** | |

*Single source* means one utility contributes, with no averaging. Models for 5,000 kW and over
report component buckets only (no usage level yet). Alberta's 50-499 kW, 500-4,999 kW and 5,000 kW
and over models are wires charges with market energy pending (above the Rate of Last Resort limit;
Phase 6C), like Ontario's three demand-class models.

**7C rules (user decisions, October 16):**
- **Alberta pairs:** each all-in unit pairs a wires utility with the Rate of Last Resort provider
  for its area: ENMAX Power + ENMAX Energy; ATCO Electric + Direct Energy Regulated Services (no
  administration charge, noted); EPCOR Distribution + EPCOR Energy Alberta; FortisAlberta + EPCOR
  Energy Alberta. Each pair counts once and every component keeps its own source and dates. The
  Rate of Last Resort applies only below 250,000 kWh a year (the residential and small-commercial
  levels); larger loads are wires plus *market energy pending*.
- **Market energy:** a model is pending only when its energy itself is market-priced. EPCOR
  Distribution's operating reserve (a percentage of the AESO pool price) is excluded and named.
- **Exclusions:** optional TOU/peak-event products and pilots outside Ontario (BC Hydro 2101
  combinations, FortisBC 22A/32, Hydro-Quebec Flex D/G, ATCO D13); ATCO T31, FortisAlberta 65,
  ENMAX D410 and EPCOR DAS-TOUP are supply-voltage alternatives.
- **Units:** no assumed conversions. FortisBC "$/two months" charges are halved; per-day energy
  blocks are multiplied by 30.4375 (Hydro-Quebec Rate D: 40 kWh a day); block thresholds printed
  without a period use the reviewed `data/models/block_periods.json` entries quoted from the
  tariffs. NB Power GS1 and Maritime Electric stay not computable because their "Billing Period"
  has no stated length, and amperage/phase fixed-charge alternatives stay not computable. The
  Newfoundland and Labrador residential model is withheld while Newfoundland Power is not
  computable (it would otherwise show NL Hydro's Labrador zone alone).
- **Known blockers:** Manitoba Hydro's stored energy blocks are malformed (a parser fix is
  needed); Hydro-Quebec and Manitoba Hydro define a month as 30 days while the engine uses
  30.4375 (open question).

Ontario results are unchanged by 7C. Ontario medians, $/month:

| Ontario model (usage level) | Utilities | Without tax | With tax | Notes |
|---|---|---|---|---|
| Residential TOU (1,000 kWh) | 47 | 192.11 | 171.94 | Closest to the median: Rideau St. Lawrence; outliers Algoma +16.8%, Sioux Lookout +13.5%, Hydro 2000 +11.8% |
| Commercial under 50 kW, TOU (2,000 kWh at 10 kW) | 45 | 383.69 | 343.40 | - |
| Commercial 50-499 kW (40,000 kWh at 100 kW) | 46 | 1,864.72 | 2,107.14 | Delivery only; market energy pending |
| Commercial 500-4,999 kW (500,000 kWh at 1,000 kW) | 46 | 17,958.81 | 20,293.45 | Delivery only; market energy pending |

The residential and under-50 kW costs are lower with tax than without because the Ontario
Electricity Rebate (23.5% of the pre-tax amount) exceeds the 13% HST, which is charged on the
pre-rebate amount. Demand-class models are in the *market energy pending* state because Ontario
market energy is a value-less component; a source-backed all-in market energy (7E) is not built.

**7E illustrative estimate (October 16; user decision):** the Ontario 50-499 kW and 500-4,999 kW
models keep their delivery-only medians and the *market energy pending* state. A separate
`illustrative_all_in` block adds market energy for a **synthetic load profile**
(`ON_SYNTHETIC_BUSINESS_HOURS` under `synthetic_profiles` in `data/models/usage_levels.json`:
Monday-Friday hours beginning 7-18 EST at the level's kW and a constant base load at all other
hours, sized so the month's kWh equals the level; holidays count as weekdays). Each month's
published energy level is multiplied by that calendar month's profile-weighted shape factor from
the heatmap bins, that month's Class B GA is added, and the 60 months of the market window are
averaged. Class B only; loss factors are not modelled; no estimate is made if the market window
ends more than 4 months before the as-of date.

| Ontario model (level) | Market energy, synthetic profile | Base load | Illustrative median without / with tax |
|---|---|---|---|
| 50-499 kW (40,000 kWh at 100 kW) | 10.83 cents/kWh | 29.6 kW | $6,197.08 / $7,002.71 |
| 500-4,999 kW (500,000 kWh at 1,000 kW) | 10.64 cents/kWh | 509.2 kW | $71,164.80 / $80,416.23 |

On the site it is hidden behind the checkbox "Show illustrative all-in estimate (synthetic load
profile)", with a warning, a SYNTHETIC badge and the text "Representative only: not a forecast, a
quote or a bill. Do not use it for decisions; it needs further analysis." It is never used in
medians, outliers, the closest utility, Phase 8 change detection or Phase 9 comparisons. Further
analysis needed: comparison with real commercial load profiles, sensitivity to the business
hours, an Ontario Price-era hourly shape once 12 archived months exist, Class A and loss factors.

**Inputs (`data/models/`):**
- `crosswalk.json`: 240 ordered rules (first match wins) map every latest live record to a model
  key (province, fuel, sector, structure, size band) or to an exclusion with its reason (15
  intentional rule overrides are reported). A `pairs` section defines the Alberta wires + Rate of
  Last Resort units (the eight Rate of Last Resort records are excluded as
  `paired_retail_component` and used through their pairs), and `required_contributors` withholds
  a level when a required utility is not computable. Ontario and Alberta gas records wait for 7D
  and territorial records for their own plan.
- `usage_levels.json` (user-approved monthly levels): residential 500, 1,000 and 2,000 kWh;
  commercial under 50 kW 2,000 kWh at 10 kW and 8,000 kWh at 25 kW; 50-499 kW 40,000 kWh at
  100 kW; 500-4,999 kW 500,000 kWh at 1,000 kW; no 5,000 kW and over level yet. 30.4375 days per
  month; kVA at a disclosed 0.9 power factor; Ontario TOU shares 64/18/18 (off-peak/mid-peak/
  on-peak) and ULO shares 40/20/27/13 (ultra-low overnight/off-peak/mid-peak/on-peak) from the
  OEB RPP Price Report for November 1, 2025 - October 31, 2026; tier seasons as published. A
  reviewed *reference customer* list adds four Ontario conditional charges that every typical
  customer pays: Class B Capacity Based Recovery riders, non-RPP Class B Global Adjustment riders
  (demand sectors only), riders for customers that are not wholesale market participants and the
  Standard Supply Service administration charge. Since October 16 it also holds the 7E synthetic
  load profile (`synthetic_profiles`).
- `block_periods.json` (October 16): 20 reviewed entries, each quoting its tariff, give the period
  (for example a month or two months) of energy block thresholds printed in kWh without one; an
  entry with no stated period (NB Power GS1, Maritime Electric) leaves the record not computable.
- `taxes.json`: 13 provinces and territories x electricity/gas x residential/commercial: GST,
  HST, PST, QST or RST plus automatic point-of-sale rebates (for example the Ontario Electricity
  Rebate 23.5%, Nova Scotia's Your Energy Rebate 9% and New Brunswick's 10% residential
  electricity rebate). Accepted defaults: Manitoba residential assumes a gas-heated home;
  municipal taxes and surcharges are excluded; commercial tax is shown as billed, without input
  tax credits; income-tested programs are excluded.

#### Representative Models: Design

- **Model key:** province, fuel (electricity, gas), sector (residential; commercial
  small, medium, large), structure (flat, tiered, TOU, ULO, seasonal, demand, interruptible...)
  and, where relevant, size band. A model exists only where at least one live record of that
  structure exists; otherwise the state is *Not offered* or *Not yet live*, never zero.
- **Category crosswalk:** a reviewed configuration file (`data/models/crosswalk.json`) maps each
  utility's tariff (registry name and tariff code) to a model key from published eligibility, not
  from similar plan names. Standard rate zones and standard service only; closed, pilot, optional,
  bulk-metered, off-grid and process-specific products are excluded unless a model is defined for
  them, and every exclusion is listed with its reason. A multi-zone utility counts once: the
  median of its standard zones (user decision).
- **Component buckets:** fixed per month, energy/commodity (by period or tier), distribution
  volumetric, demand per kW or kVA, transmission, regulatory, mandatory riders, carbon and other
  mandatory charges. Conditional, alternative, optional and expired components and value-less
  market components are excluded and counted, except the reviewed reference-customer charges.
  Unit conversions are disclosed ($/day x 30.4375 = $/month; cents to dollars); kVA is never
  treated as kW without a disclosed power-factor assumption (0.9); m3 is never converted to GJ
  without a published heat content.
- **Combining rule:** each bucket is the median across contributing utilities, shown with n,
  min, p25, p75 and max. Because bucket medians do not add up to a coherent bill, each model also
  reports, at every common usage level, the median cost (computed per utility, then the median),
  without and with tax, and the closest real utility (whose cost is nearest the median), linked
  to its live tariff. Major outliers (more than 30% from the median or outside 1.5 x the
  interquartile range) are named with their deviation from the median.
- **TOU and time periods:** if one schedule applies province-wide (Ontario RPP), use it as
  published. Otherwise compute each utility's price for every hour of a reference week per
  season, take the median per hour, then group equal-priced hours into representative periods.
  The model states which utilities had which schedules.
- **Tiers:** identical thresholds are used directly. Otherwise build each utility's marginal
  price over a usage grid, take the median per point and simplify it into representative tiers;
  original thresholds stay visible.
- **Commercial size bands:** under 50 kW, 50-499 kW, 500-4,999 kW and 5,000 kW and over (volume
  bands for gas). Each utility contributes the class whose published eligibility covers the
  band's reference load, and the model names that class.
- **All-in energy:** regulated energy (Ontario RPP, provincial rates, Alberta Rate of Last
  Resort fixed prices, regulated gas supply) is used as published. Market-priced energy (Ontario
  non-RPP demand classes: Ontario Electricity Market Price plus Class B GA; Alberta pool-price
  charges; monthly or quarterly gas commodity) comes from the market model, is labelled
  modeled with its period basis, and comes from Phase 6 (Market Integration). Where Phase 6 has
  no market data yet, the model shows delivery plus a *market energy pending*
  state, never a guessed number. The 7E illustrative estimate (synthetic load profile) is a
  separate, opt-in block beside such a model; it never replaces the pending state.
- **Transparency text:** every model carries a generated method statement, for example
  "Median of 44 Ontario LDC TOU delivery charges (default rate zones, Hydro One included) plus
  the province-wide OEB RPP TOU prices and hours effective November 1, 2025; excludes Algoma (no
  standard TOU-R) and Oakville (GS<50 rejected)", or "Single source: Nova Scotia Power Domestic
  Service is the only utility; no averaging". It also lists contributing utilities, record ids,
  effective dates, source URLs, coverage (n of N utilities), exclusions with reasons, outliers,
  generated date and the input export.
- **Outputs:** the builder (`pipeline/representative_models.py`, method version 7C-2) runs
  inside `pipeline/export_json.py` for the ten provinces and writes
  `site/data/representative_models.json` (compact JSON) on every export; the file is kept in git
  history. A model-build failure is logged and leaves the previous file in place; it never fails
  the export. No schema change.
- **Site view:** a **Representative Models** tab with province, fuel, sector and structure
  selectors; a component table with spread, a 24-hour/season strip for TOU, a tier-step chart, a
  demand-band ladder, the method statement and an expandable list of contributing tariffs. A
  permanent banner says the model is not a billed tariff.
- **Across-Canada use:** the national matrix, dot/range plots, TOU strips and demand ladders
  read the same JSON; a province drill-down shows the model's contributing tariffs. The
  comparison states *Not offered / Not yet verified / Not comparable* map to the model states.

#### Representative Models: Phases

| Phase | Work and completion gate | Depends on | Status |
|---|---|---|---|
| 7A: Taxonomy and crosswalk | Model keys and size bands; reviewed crosswalk for every live utility; exclusion reasons; tests for unmapped/ambiguous records | Current live data | **Done October 9:** crosswalk, usage levels and tax table in `data/models/` (see Inputs above); 0 unmapped records |
| 7B: Engine (delivery + regulated energy) | Bucket normalization, median/spread, cost at each common usage level without and with tax, closest utility, outlier notes, TOU hour surfaces, tier curves, demand bands, method text and provenance; synthetic and fixture tests; Ontario first (promote the scratch prototype) | 7A | **Done for Ontario October 9:** `pipeline/representative_models.py` (method version 7B-2; 7C-2 since October 16), run by every export; Ontario's province-wide RPP periods and tiers are used as published; demand-class models are *market energy pending* |
| 7C: Electricity, all provinces | Residential and commercial models for every province with live data, including Alberta all-in models that combine wires and Rate of Last Resort records; single-source labelling; coverage report (territories planned separately) | 7B | **Done October 16 (method 7C-2):** 55 models across the ten provinces (16 modeled, 20 single-source, 6 *market energy pending*, 13 not computable); four Alberta wires + Rate of Last Resort pairs; reviewed block periods; Newfoundland and Labrador residential withheld while Newfoundland Power is not computable. Open: the Manitoba Hydro parser fix and the decisions under Next |
| 7D: Gas | Residential and commercial gas models (commodity, delivery, carbon kept as buckets) | 7B; ON/AB gas parsers | Planned |
| 7E: All-in market energy | Market-priced energy from Phase 6 with period basis; *pending* state where Phase 6 data is missing | Phase 6 (6A, 6C) | **Illustrative only (October 16):** the two Ontario demand-class models carry a synthetic-profile all-in estimate, hidden by default and never used in medians or comparisons; their state stays *market energy pending*. A source-backed all-in value needs further analysis (Ontario) and 6C (Alberta) |
| 7F: Site view | Representative Models tab, charts, method/coverage disclosure, accessible table, desktop/mobile checks | 7C | **Done October 15** (before 7C; the view handles any province): province, fuel, sector and structure selectors, default Ontario residential TOU at 1,000 kWh, a table with medians without and with tax, middle half, range bars, closest utility and outliers, tax lines, the method, coverage and expandable contributing utilities and exclusions. User decision: no new charts (the TOU strip, tier-step chart and demand ladder above were not built). October 16: all ten provinces, contributor wording such as "wires + Rate of Last Resort pairs", a note on excluded market-indexed charges and the opt-in 7E block (`site/css/models.css`). Gas usage levels (7D) need a label update |

**Decisions before 7A (user, October 8):**
- **Taxes:** every all-in model is shown both without tax and with tax (applicable GST/HST/PST,
  each tax line disclosed with its rate and source).
- **Usage levels:** no single reference usage. Each model is evaluated at a set of common usage
  levels per sector (for example low/typical/high monthly kWh for residential, and several
  kW/kWh combinations per commercial size band), with the level definitions and their basis
  published; the median and closest utility are reported per level.
- **Outliers:** no "excluding" variants. When a utility is a major outlier, the model says so
  and by how much (for example "Hydro One: +55% versus the median at typical usage").
- **Scope:** provinces only for now. Territorial models (community-level rates, NTPC zones,
  Qulliq, subsidies) get their own plan later.

### Phase 8: Representative Model Refresh Automation (planned)

GitHub Actions keep `site/data/representative_models.json` current when the live data
underneath changes considerably, without noise commits for trivial drift.

- **Trigger:** after a successful Monthly Scrape (validation and export passed), plus manual
  dispatch with a force-rebuild option and a dry-run mode that publishes nothing.
- **Change detection:** each model keeps an input fingerprint (contributing record ids, snapshot
  hashes and effective dates). The workflow rebuilds candidate models and compares them with
  the published file.
- **Considerable change (proposed, to confirm):** the median cost at any usage level (without
  tax) moves by 2% or more; a utility joins or leaves a model or its crosswalk mapping changes; a
  structure appears or disappears in a province; a tax rate changes; or the method version
  changes. Below the threshold nothing is committed and the job summary lists the drift.
- **Publishing:** write the new models file and append an entry to
  `site/data/representative_models_changelog.json` (model key, old/new value per usage level,
  percent change, utilities driving it, effective dates, scrape run); commit explicit paths;
  the existing Deploy Site trigger publishes it. The site shows when each model last changed.
- **Safeguards:** models use live records only. If a contributing utility drops out because its
  scraper failed or fell back to estimates (not because its tariff changed), keep the previous
  model, mark the input stale and open or update a GitHub issue instead of publishing. History is
  never overwritten. Illustrative values (the 7E synthetic-profile estimate) are never inputs:
  change detection reads only the source-backed model values.

| Phase | Work and completion gate | Depends on |
|---|---|---|
| 8A: Fingerprint and diff | Input fingerprints, model diff, thresholds; unit tests with synthetic before/after exports | 7B, 7C |
| 8B: Changelog | Changelog format and the site's "last changed" note | 8A, 7F |
| 8C: Workflow | Refresh step or workflow after Monthly Scrape; stale-input issues; dry run | 8A, 5H |
| 8D: CI verification | First real run observed end to end (rebuild, commit, deploy, no-change and stale cases) | 8C |

### Phase 9: Product Follow-up (planned)

1. Add historical rate charts and AI-ready exports after coverage is dependable.
2. Scope a bill calculator and optional API separately; the current comparison never calculates a total.
3. **Across-Canada comparison view:** expand the Compare tab with a separate national view alongside the existing two-tariff comparison. Compare common customer classes and rate structures across provinces, using the Phase 7 representative models as the provincial values (electricity first, gas after 7D, all-in only once 7E is more than illustrative). 7F (the Representative Models view, October 15) and 7C (all ten provinces, October 16) are done, so this national view can start; it never uses the illustrative (synthetic-profile) values.

#### Across-Canada Comparison: Design Direction

- **National comparison matrix:** provinces as rows (territories once they have models), common customer-class/rate-structure categories as columns or selectable views. Keep every region visible, including where a category is **Not offered**, **Not yet verified**, or **Not comparable**; these are different states, never zero prices. The category crosswalk is the Phase 7 crosswalk.
- **Residential profiles:** start with flat, tiered and time-of-use plans, with separate views for other nationally recurring structures. Show energy prices, monthly fixed charges, tier allowances, TOU hours/seasons and mandatory adjustments. Show monthly-equivalent fixed charges only with a disclosed day/billing-period basis and the original units. Do not manufacture a flat rate by averaging a tiered or TOU plan; distinguish ordinary household service from bulk-metered, off-grid, pilot and other conditional products.
- **Commercial class ladders:** compare small, medium and large general service using each utility's actual eligibility bands. Show the peak-demand range, fixed monthly charge, energy structure, when demand billing begins, any free demand allowance, and the applicable charge per kW or kVA. A shared demand-axis chart could reveal where one province's small-commercial class becomes another's medium class. Preserve voltage, season, minimum-bill and demand-ratchet conditions; do not invent universal class boundaries or convert kVA to kW without evidence.
- **Transparent provincial values:** provincial values come from the [Phase 7 representative models](#phase-7-representative-models-in-progress) (median across utilities, single-source where only one utility exists, generated method statement); this view adds no blending logic of its own. Display the participating utilities, coverage and min-max range, with expansion to individual tariffs and sources. Incompatible tier boundaries and TOU windows stay visible in the model's method statement. A model is a comparison indicator, not an official tariff or a price every resident pays.
- **Visual exploration:** combine the sortable matrix with provincial dot/range plots, miniature tier-step charts, 24-hour TOU strips and commercial demand-threshold ladders. Selecting a province should reveal its contributing utilities and charge breakdown; selecting a category should line up that structure across Canada. Offer fuel, customer/building type, rate structure and effective-period controls, with an accessible table alternative to charts.
- **Fair comparisons:** keep energy, delivery, fixed charges, demand and riders distinct. Flag energy-only versus bundled service, differing units and incomplete component coverage before ranking. Show source dates and methodology; keep estimated inputs separate and explicitly labelled. Any usage-weighted effective price or example monthly bill requires a disclosed load profile and the separately scoped calculator work above, not an implicit total in this comparison view.

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

---

## License

This project collects publicly available rate data from official utility websites. The data itself belongs to the respective utilities and regulators. This tool is for informational and educational purposes.

---

## Contributing

The immediate priority is **complete existing live parsers and their source-derived
fixtures**, not add more seed-only coverage. See [docs/adding-a-utility.md](docs/adding-a-utility.md)
and the [coverage matrix](docs/phase5_completion_matrix.md).
