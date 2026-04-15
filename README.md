# Canada Utility Costs

**Browse electricity and natural gas rates across all Canadian provinces and territories.**

This project scrapes official utility rate data, stores it in a structured database, and serves it as a clean, browsable static website via GitHub Pages.

---

## What This Project Does

1. **Scrapes** utility rate data from official Canadian utility websites.
2. **Stores** everything in a normalized SQLite database that preserves every rate detail — not just a single "cost per kWh" number.
3. **Tracks history** — each monthly scrape creates a new snapshot, so you can see how rates change over time.
4. **Exports** the data as JSON for the GitHub Pages static site.
5. **Serves** a browsable web interface with multi-select filters, confidence indicators, source attribution, and an interactive Market Pricing dashboard with heatmaps and charts.
6. **Runs automatically** on a monthly schedule via GitHub Actions.

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
git clone https://github.com/YOUR_USERNAME/canada-utility-costs.git
cd canada-utility-costs
```

If you don't have Git, click the green **"Code"** button on GitHub and download the ZIP file. Unzip it and open a terminal in that folder.

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
pip install -e .
```

**What this does:** Installs the Python libraries the project needs (web scraping tools, data processing tools, etc.).

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

You'll see output like:
```
INFO     Loaded 4 utilities from registry
INFO     Will scrape 4 utilities
INFO     ─── Scraping: BC Hydro ───
INFO     Successfully scraped 2 BC Hydro tariffs
...
============================================================
  Scrape complete: 4/4 utilities succeeded
  Total tariffs scraped: 8
============================================================
```

### Step 6: Export Data for the Website

```bash
python -m pipeline.export_json
```

**What this does:** Reads the database and creates JSON files in `site/data/` that the static website uses.

### Step 7: View the Website Locally

Open `site/index.html` in your web browser. You should see rate cards you can filter and browse.

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
│   └── utilities/            ← One file per utility (34 scraper files, 84 registered utilities)
│       ├── bc_hydro.py       ← BC Hydro (electricity, BC)
│       ├── hydro_quebec.py   ← Hydro-Québec (electricity, QC)
│       ├── ontario_ldc.py    ← All 53 Ontario LDCs (data-driven, one class)
│       ├── toronto_hydro.py  ← Toronto Hydro (legacy, separate from LDC)
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
│   └── data/                 ← JSON data files (generated by export_json.py)
│       ├── rates.json        ← All tariff/component data
│       ├── utilities.json    ← Utility metadata
│       ├── summary.json      ← Provincial summaries
│       ├── missing.json      ← Known data gaps
│       ├── missing_classes_report.json  ← Customer class coverage audit
│       ├── market_pricing_ontario.json  ← Ontario IESO hourly price bins
│       ├── market_structure_notes.json  ← All-province market research
│       └── source_review_report.json    ← Source URL audit report
│
├── tests/                    ← Automated tests (233 tests)
│   ├── fixtures/             ← Saved HTML snapshots for parser tests
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

A GitHub Actions workflow runs automatically on the 1st of every month:

1. Checks out the repo, installs Python and dependencies.
2. Runs all active scrapers.
3. Validates the scraped data.
4. Exports JSON for the static site.
5. Commits updated data files back to the repo.
6. Deploys the site to GitHub Pages.
7. If any scraper fails or data looks wrong, it creates a GitHub Issue.

You can also trigger a run manually from the **Actions** tab on GitHub.

---

## Source Data & Market Pricing

### Source Hierarchy

The project prioritizes data sources in this order:
1. **Utility-owned rate pages** — the utility's own published rates
2. **Regulator filings** — OEB rate orders, BCUC decisions, AUC filings
3. **Third-party aggregators** — only when no direct source is available

`data/sources/registry.json` is the **system of record** for all source URLs. An Excel reference file (`data/excel/old_urls.xlsm`) exists for audit purposes only and is never read by any scraper — it is git-ignored.

### Ontario Market Pricing (IESO HOEP + GA)

Ontario's large commercial customers (GS >= 50 kW) pay market-based energy prices rather than OEB-regulated TOU/Tiered rates. Their energy cost is:

- **HOEP** (Hourly Ontario Energy Price) — real-time wholesale price set by IESO
- **GA** (Global Adjustment) — monthly charge covering contracted/regulated generation costs

The project includes a 576-bin hourly market pricing model (`site/data/market_pricing_ontario.json`) derived from 5 years of IESO data, with bins for 12 months x 2 day types x 24 hours. This provides representative $/kWh values for each time slot.

**Class A vs. Class B:**
- Class B (< 1 MW) pays GA as a uniform per-kWh volumetric charge
- Class A (> 1 MW) pays GA based on coincident peak demand (ICI mechanism)

To update market data monthly, re-run the market pricing pipeline after fresh IESO data is available.

### Alberta Deregulated Market

Alberta has a fully deregulated energy-only wholesale market operated by AESO. Distribution (wires) charges are regulated separately from retail energy. Customers who don't choose a competitive retailer receive Regulated Rate Option (RRO) pricing — a monthly pass-through of the AESO pool price.

### Other Provinces

All other provinces use vertically integrated Crown utilities with fully regulated tariff structures. See `site/data/market_structure_notes.json` for detailed research notes on every province's market structure.

---

## How to Verify a Rate Is Still Valid

1. Open the database or the exported `site/data/rates.json`.
2. Find the tariff you want to check.
3. Look at the `source_url` field — this is the official page where the rate was found.
4. Visit that URL and compare the numbers.
5. Check the `effective_date` and `confidence` fields.
6. If the rate has changed, update the scraper's seed data or improve the live parser.

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

### Phase 1: Architecture & Sample Utilities ✓
- Core scraper framework
- Database schema
- Example scrapers (BC Hydro, Hydro-Quebec, Toronto Hydro, Enbridge Gas)
- Static site viewer
- GitHub Actions automation

### Phase 2: Province-by-Province Expansion ✓
- All 53 Ontario LDCs via data-driven OntarioLDCScraper
- 8 Alberta utilities (4 distribution + 3 RRO retail + AESO market reference)
- Newfoundland Power, NL Hydro, Maritime Electric
- SaskPower, Manitoba Hydro, NB Power, NS Power
- Enbridge Gas, FortisBC Gas

### Phase 3: Customer Class Coverage ✓
- Residential, Commercial (GS < 50 kW, GS >= 50 kW), Street Lighting for all Ontario LDCs
- Commercial classes for Alberta and NL utilities
- `customer_classes` database table
- Validation for class completeness (`missing_classes_report.json`)

### Phase 4: Source Review & Market Pricing ✓
- Excel audit file (`data/excel/old_urls.xlsm`) used as reference only
- Source URL review and prioritization (utility-first sourcing)
- Ontario IESO market pricing model (HOEP + Global Adjustment, 576 hourly bins)
- Provincial market structure research (`market_structure_notes.json`)
- `market_pricing` database table

### Phase 5: Live Parser Hardening & Historical Tracking (In Progress)
- **Step 1 (Complete):** Foundation infrastructure
  - Change detection module (`scrapers/utils/change_detection.py`) — compares live-parsed vs seed data with severity thresholds (info/warning/critical), rejects live data on critical drift
  - Enhanced parsing helpers in `scrapers/utils/parsing.py` — `find_text_near_label()`, `extract_rate_from_text()`, `detect_js_rendered()`, `find_pdf_links()`
  - URL corrections for rebranded utilities (Heritage Gas → Eastward Energy, Liberty Gas NB → naturalgasnb.com, SaskPower, NB Power)
  - Test fixture directory (`tests/fixtures/`) for saved HTML snapshots
  - 27 new change detection tests (174 total)
- **Step 2 (Complete):** Live HTML parsers for Tier 1 major provincial utilities
  - **Full live HTML parsers:** Manitoba Hydro (table extraction, 3 tariffs), NB Power (table extraction with merged cells, 3 tariffs), Nova Scotia Power (residential label-based + commercial Rates 10/11/12, 4 tariffs), BC Hydro (prose text regex, 4 tariffs including LGS)
  - **PDF live parser:** Hydro-Québec (Rate D, G, M from official electricity-rates.pdf, 3 tariffs)
  - **PDF detection:** SaskPower, NL Hydro, Newfoundland Power — landing page parsing, PDF link logging (seed only)
  - Seed data refreshed to 2025-2026 published rates for all 8 utilities
  - URL fixes for NS Power, NL Hydro, Newfoundland Power (old URLs returned 404)
  - Structural fixes: NB Power residential tiered→flat, BC Hydro SGS demand charge removed, BC Hydro LGS added
  - 56 live parser tests (`tests/test_live_parsers.py`), 233+ total
  - Gap report at `docs/live_parser_gap_report.md`
- **Step 3 (Next):** Ontario OEB province-wide rate scraping
- **Step 4:** Alberta electricity parsers (distribution + RRO)
- **Step 5:** Gas utility parsers
- **Step 6:** Northern/remote utility parsers
- Build rate comparison tools (compare two utilities side by side)
- Add PDF tariff parsing for complex rate schedules

### Phase 5.5: Enhanced Web Interface ✓
- Two-tab layout: Rate Browser + Market Pricing dashboard
- Multi-select checkbox filters (province, utility, fuel type, customer class, rate structure) with search
- Province filter cascades into utility filter (selecting BC shows only BC utilities)
- Rate deduplication: only most recent effective_date per tariff displayed
- Confidence indicators on rate cards (colored dots) and in detail modal (badge + tooltip)
- Source attribution in detail modal (primary source + utility website from source review)
- Market-based rate callouts with IESO/AESO/gas explanations and links to Market Pricing tab
- Interactive Market Pricing dashboard:
  - Hourly price heatmap (12 months × 24 hours, blue→yellow→red color scale)
  - Chart.js line chart with 12 monthly price curves
  - Monthly summary table (avg HOEP, GA, combined, peak/off-peak hours)
  - Methodology & sources section with data provenance
- Controls for day type (weekday/weekend) and display metric (Combined/HOEP/GA)

### Phase 6: Better UI & AI Export (Planned)
- Add historical rate charts to the web interface
- AI-ready export format (structured for LLM retrieval/RAG)
- Rate calculator tool
- API endpoint (optional)

---

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| Scraping | Python + requests + BeautifulSoup | Standard, reliable, huge community |
| PDF parsing | pdfplumber | Best Python PDF table extractor |
| Database | SQLite | Zero setup, single file, full SQL |
| Validation | Custom + Pydantic | Type-safe, catches errors early |
| Static site | HTML + CSS + vanilla JS + Chart.js | No build step, works on GitHub Pages |
| Automation | GitHub Actions | Free for public repos, built-in cron |
| Testing | pytest | Standard Python testing |

---

## License

This project collects publicly available rate data from official utility websites. The data itself belongs to the respective utilities and regulators. This tool is for informational and educational purposes.

---

## Contributing

Contributions are welcome. The most impactful thing you can do is **add a new utility scraper** — see [docs/adding-a-utility.md](docs/adding-a-utility.md).
