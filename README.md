# Canada Utility Costs

**Browse electricity and natural gas rates across all Canadian provinces and territories.**

This project scrapes official utility rate data, stores it in a structured database, and serves it as a clean, browsable static website via GitHub Pages.

## Current Status (2026-10-01)

The framework and website are implemented; **nationwide live-rate coverage is not complete**.
The October 1 export includes a targeted SaskPower refresh. Other utilities retain their
September 29 results; this is not a fresh Canada-wide source check.

| Measure | Exported state |
|---|---|
| Registered utilities | 84: 75 electricity and 9 gas, across all 13 provinces/territories |
| Stored tariffs / components | 538 / 3,592, including retained older estimates |
| Live-sourced tariffs | **58 across 10 utilities** |
| Seed/fallback tariffs | **480**, hidden by default |
| SaskPower live tariffs | **20**, up from 1; published class coverage remains partial |
| Deterministic tests | **268 passing** on Python 3.11 |

Live output currently includes BC Hydro (4), Manitoba Hydro (8), NB Power (3),
Nova Scotia Power (4), Hydro-Quebec (3), Maritime Electric (10), Newfoundland Power (4),
SaskPower (20), FortisAlberta (1), and Yukon Energy (1). These counts describe the export,
not complete coverage of each utility's published catalogue. Ontario and all gas utilities
still have no live records in this snapshot.

See the [coverage matrix](docs/phase5_completion_matrix.md) for the implementation queue
and [parser gap report](docs/live_parser_gap_report.md) for class-level details.
A successful scrape can return only seeds; success counts and an empty missing-data log
do **not** prove live coverage.

---

## What This Project Does

1. **Scrapes** utility rate data from official Canadian utility websites.
2. **Stores** everything in a normalized SQLite database that preserves every rate detail — not just a single "cost per kWh" number.
3. **Tracks local history** — each stored scrape appends snapshots. Keep the database to preserve them; durable history across CI runs still needs an explicit restore/save mechanism.
4. **Exports** the data as JSON for the GitHub Pages static site.
5. **Serves** a browsable web interface with multi-select filters, confidence indicators, source attribution, and an interactive Market Pricing dashboard with heatmaps and charts.
6. **Provides automation** through monthly scraping, separate Pages deployment, and non-blocking source-health workflows. Publication reliability is a remaining work item.

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

### Step 4: Initialize the Database

```bash
python -m pipeline.run_scrape --init-db
```

**What this does:** Creates an empty SQLite database file at `data/db/rates.db` with all the right tables.

### Step 5: Run Your First Scrape

```bash
python -m pipeline.run_scrape
```

**What this does:** Runs every active scraper, fetches rate data from official utility websites, validates it, and stores it in the database.

Check the per-utility `Live-parsed` and `Seed fallback` messages. A final
`utilities succeeded` count only means execution completed, not that every rate was live.
Run `python -m pipeline.validate` before exporting. Network retries and rendered pages
can make a full scrape take several minutes.

### Step 6: Export Data for the Website

```bash
python -m pipeline.export_json
```

**What this does:** Reads the database and creates JSON files in `site/data/` that the static website uses.

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
│   │   ├── market_pricing.py ← Ontario IESO market pricing model
│   │   └── logging_config.py ← Logging setup
│   └── utilities/            ← 33 scraper modules + package initializer; 84 registered utilities
│       ├── bc_hydro.py       ← BC Hydro (electricity, BC)
│       ├── hydro_quebec.py   ← Hydro-Québec (electricity, QC)
│       ├── ontario_ldc.py    ← All 53 Ontario LDCs (data-driven, one class)
│       ├── toronto_hydro.py  ← Legacy, unregistered; current Toronto entry uses the LDC scraper
│       ├── enbridge_gas.py   ← Enbridge Gas (gas, ON)
│       ├── atco_electric.py  ← ATCO Electric (distribution, AB)
│       ├── fortisalberta.py  ← FortisAlberta (distribution, AB)
│       ├── epcor_distribution.py ← EPCOR Distribution (AB)
│       ├── enmax_power.py    ← ENMAX Power (distribution, AB)
│       ├── direct_energy_regulated.py ← Direct Energy RRO (AB)
│       ├── enmax_energy.py   ← ENMAX Energy RRO (AB)
│       ├── epcor_energy_alberta.py ← EPCOR Energy RRO (AB)
│       ├── aeso.py           ← AESO market reference (AB)
│       ├── nl_hydro.py       ← NL Hydro (electricity, NL)
│       └── ...               ← Other provincial utilities
│
├── pipeline/                 ← Scripts that run the whole process
│   ├── run_scrape.py         ← Main entry: run scrapers → validate → store
│   ├── export_json.py        ← Export database → JSON for the website
│   ├── diff_report.py        ← Compare two scrape runs to see changes
│   └── validate.py           ← Data quality checks
│
├── schema/                   ← Database definition
│   ├── create_tables.sql     ← SQL that creates all tables
│   └── schema_diagram.md     ← Visual diagram of the schema
│
├── data/                     ← Data files
│   ├── db/                   ← SQLite database (created by the scraper)
│   ├── exports/              ← CSV/Excel exports (optional)
│   ├── excel/                ← Audit reference files (not system of record, git-ignored)
│   ├── sources/registry.json ← Master list of where to find rate data
│   └── inventory/            ← Full utility inventory
│
├── site/                     ← Static website (deployed to GitHub Pages)
│   ├── index.html            ← Main page: Rate Browser + Market Pricing tabs
│   ├── css/style.css         ← Styles inc. multi-select filters, heatmap, confidence
│   ├── js/app.js             ← SPA logic: filters, cards, modal, market viz
│   └── data/                 ← Five pipeline exports plus separately maintained market/audit data
│       ├── rates.json        ← All tariff/component data
│       ├── utilities.json    ← Utility metadata
│       ├── summary.json      ← Provincial summaries
│       ├── missing.json      ← Known data gaps
│       ├── missing_classes_report.json  ← Customer class coverage audit
│       ├── market_pricing_ontario.json  ← Ontario IESO hourly price bins
│       ├── market_structure_notes.json  ← All-province market research
│       └── source_review_report.json    ← Source URL audit report
│
├── tests/                    ← 268 deterministic tests across 8 test modules
│   ├── fixtures/             ← Source-derived SaskPower PDF-text fixtures; other tests also use inline text
├── docs/                     ← Guides and reference
├── .github/workflows/        ← GitHub Actions automation
│
├── README.md                 ← This file
├── AGENTS.md                 ← Step-by-step guide for maintainers
└── requirements.txt          ← Python dependencies
```

---

## Common Commands

| What you want to do | Command |
|---|---|
| Initialize the database | `python -m pipeline.run_scrape --init-db` |
| Scrape all active utilities | `python -m pipeline.run_scrape` |
| Scrape one utility | `python -m pipeline.run_scrape --utility "BC Hydro"` |
| Scrape all utilities in a province | `python -m pipeline.run_scrape --province ON` |
| Dry run (scrape but don't save) | `python -m pipeline.run_scrape --dry-run` |
| Export JSON for the website | `python -m pipeline.export_json` |
| Validate data quality | `python -m pipeline.validate` |
| Compare two scrape runs | `python -m pipeline.diff_report` |
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
- **Market-indexed components** — prices linked to wholesale markets

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
4. Test with `python -m pipeline.run_scrape --utility "Your Utility"`.

---

## How Monthly Updates Work

The [Monthly Scrape workflow](.github/workflows/scrape.yml) runs on the 1st at
08:00 UTC or on manual dispatch. It installs dependencies and Chromium, runs tests,
scrapes, validates, rejects empty exports, and commits updated data.

[Deploy Site](.github/workflows/deploy.yml) is a separate push/manual workflow.
[Non-blocking Source Health](.github/workflows/source-health.yml) runs on the 15th
and uploads a dry-run log without publishing.

**Remaining operational gaps:** the default Actions token's push does not automatically
trigger the separate push workflow; failure notification paths need verification;
source health lacks browser installation; and the ignored database has no explicit
CI restore/save step. Local snapshots are append-only, but durable monthly CI history
and automatic deployment must not be assumed. Manual workflows are available in **Actions**.

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

### Ontario Market Pricing Model

The dashboard displays a 576-bin illustrative HOEP + Global Adjustment model:
12 months x 2 day types x 24 hours. The included generator uses fixed monthly
inputs and hourly multipliers; it does **not** ingest five years of IESO observations.
Re-running it does not refresh prices from IESO.

**Known provenance issue:** the JSON metadata and dashboard still describe historical
averages. Treat these numbers as modeled estimates, not measured or current prices.
Correcting the display and replacing the model with reproducible official-data ingestion
are explicit follow-up phases. Current market definitions, effective periods and
Class A/Class B allocation rules must be verified before implementing that ingestion.

### Alberta Deregulated Market

Alberta distribution (wires), default retail products and AESO wholesale observations
are separate data sources. Several modules and seeds still use legacy RRO descriptions.
Current Rate of Last Resort product names, terms and published rates require official
verification before completing those parsers; do not assume default retail is a monthly
pool-price pass-through.

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
comparison without bill totals, and a market-model dashboard. These are implemented
features, **not evidence that all registered utilities or published classes are live**.

### Phase 5: Live Parser Completion

| Phase | Work and completion gate | Status |
|---|---|---|
| 5A: Baseline | Dated inventory, honest README, shared class-level coverage ledger | Updated October 1 |
| 5B: SaskPower | All standard published schedules; current business/voltage/TOU/capacity batch adds 19 live tariffs with fixtures | Partial: 20 live tariffs; remaining schedules listed in the gap report |
| 5C: Easier expansions | Yukon Energy classes and current riders; NS Power industrial; FortisBC Electric approved schedules | Next |
| 5D: Provincial/territorial depth | NTPC, Qulliq, Yukon Electrical, NL Hydro; audit missing classes at already-live utilities | Planned |
| 5E: Gas | All nine utilities, preserving zones, commodity/delivery components, units and effective dates | Planned |
| 5F: Alberta electricity | All wires classes, source-correct default retail products, separate AESO market observations | Planned |
| 5G: Ontario | Reconcile 53 registry identities; source approved distributor tariffs; pilot three layouts before rollout | Dedicated later campaign |
| 5H: Reliable publication | Source-health/browser setup, live-vs-fallback reporting, failure notifications, deployment trigger and durable CI history | Independent operational follow-up |

**Definition of done for each utility:** account for every standard published class,
retain exact source/date/unit/component context, prove extraction and failure handling
with source-derived fixtures, inspect an official-source dry run, verify repeat
storage/export without lost components or history, and update the coverage ledger.
Known failures remain unverified; newly discovered unsupported classes are recorded
as gaps, never invented. Special/negotiated and closed-to-new-customer schedules must
be explicitly identified. Do not equate a generic verifier test with a working parser.

Utility-specific research can run independently; shared registry, database and export
updates are integrated serially. Today's first batch is SaskPower, not a promise to
complete all Canadian parsers in one session.

### Phase 6: Provenance and Product Follow-up

1. Correct the market-model metadata and UI disclosure/visibility; documentation is corrected now, the UI change is deferred.
2. Replace fixed market-model inputs with reproducible official observation ingestion and freshness checks.
3. Add historical rate charts and AI-ready exports after coverage is dependable.
4. Scope a bill calculator and optional API separately; current comparison never calculates a total.
5. **Conditional Alberta market region:** if the Alberta source audit reveals comparable market-pricing variation or complexity, add Alberta as a selectable region in the existing Market Pricing dashboard. Reuse the interface, but use Alberta-specific values, official sources, effective periods and methodology, not Ontario's values or HOEP-plus-GA assumptions. Keep wholesale, retail and wires charges distinct and label any modeled estimates explicitly. This is a later-phase option, not a change to the current parser priorities.

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
