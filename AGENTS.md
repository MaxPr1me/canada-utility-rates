# AGENTS.md — Plain-Language Guide for Maintaining This Project

**This guide is for someone with zero coding experience.**

It explains, step by step, what this project does, how everything connects, and how to keep it running. If something breaks, this guide tells you what to check and how to fix it.

---

## What Does This Project Do?

This project answers one question: **"How much do electricity and natural gas cost across Canada?"**

It works in three stages:

1. **Scrape** — Python scripts visit official utility websites and download rate information.
2. **Store** — That information gets organized into a database (a structured file on your computer).
3. **Display** — A simple website reads the database and shows the rates in a browsable format.

The whole cycle runs automatically once a month using GitHub Actions (a free service that runs code on GitHub's servers).

---

## The Big Picture

```
  Official utility websites     ←  The truth source
         │
         ▼
  Python scrapers               ←  Visit the websites, extract rate data
         │
         ▼
  SQLite database               ←  Store everything in organized tables
         │
         ▼
  JSON export                   ←  Convert to a format the website can read
         │
         ▼
  Static website                ←  Anyone can browse rates in their browser
```

---

## Important Files and What They Do

### Where the scrapers live

| File | What it does |
|---|---|
| `scrapers/base.py` | The "template" that all scrapers follow. You don't change this unless you're adding a new feature that applies to ALL scrapers. |
| `scrapers/utilities/bc_hydro.py` | Scrapes BC Hydro electricity rates. |
| `scrapers/utilities/hydro_quebec.py` | Scrapes Hydro-Quebec electricity rates. |
| `scrapers/utilities/ontario_ldc.py` | **Data-driven scraper for all 53 Ontario LDCs.** One class handles every Ontario local distribution company — the registry passes in which LDC to produce data for. Eventually, each LDC should be scraped from its own website. |
| `scrapers/utilities/toronto_hydro.py` | Toronto Hydro (legacy scraper, separate from the LDC scraper). |
| `scrapers/utilities/enbridge_gas.py` | Scrapes Enbridge Gas natural gas rates. |
| `scrapers/utilities/atco_electric.py` | ATCO Electric distribution charges (Alberta). |
| `scrapers/utilities/fortisalberta.py` | FortisAlberta distribution charges (Alberta). |
| `scrapers/utilities/epcor_distribution.py` | EPCOR Distribution charges (Edmonton, Alberta). |
| `scrapers/utilities/enmax_power.py` | ENMAX Power distribution charges (Calgary, Alberta). |
| `scrapers/utilities/direct_energy_regulated.py` | Direct Energy RRO retail rates (Alberta). |
| `scrapers/utilities/enmax_energy.py` | ENMAX Energy RRO retail rates (Alberta). |
| `scrapers/utilities/epcor_energy_alberta.py` | EPCOR Energy RRO retail rates (Alberta). |
| `scrapers/utilities/aeso.py` | AESO market reference price (Alberta wholesale). |
| `scrapers/utilities/nl_hydro.py` | NL Hydro electricity rates (Newfoundland — residential + commercial). |
| `scrapers/registry.py` | Reads the list of all utilities and their scraper info. |
| `scrapers/utils/parsing.py` | HTML/PDF parsing helpers, including PDF URL resolution and strict `verify_tariff_values()` checks that prove fallback values still appear in an official schedule. |
| `scrapers/utils/change_detection.py` | Compares live-parsed rates against seed data. Flags changes by severity (info/warning/critical). If critical drift is detected, the scraper rejects live data and falls back to seed. |
| `scrapers/utils/market_pricing.py` | Ontario IESO market pricing model (HOEP + GA hourly bins). |
| `scrapers/utils/validation.py` | Data quality checks run after every scrape. |

### Where the data lives

| File | What it does |
|---|---|
| `data/sources/registry.json` | **The master list (system of record).** Every utility the project knows about is listed here, along with the URL where its rates are published and which scraper handles it. Currently 84 utilities across 34 scraper files. |
| `data/inventory/utilities.json` | The full inventory of ALL Canadian utilities — even ones we don't scrape yet. This is the reference list. |
| `data/db/rates.db` | The SQLite database where scraped rates are stored. Created automatically when you first run the scraper. |
| `data/excel/old_urls.xlsm` | **Audit reference only.** An Excel file with historical URLs and rate data. NO scraper reads this file. It is git-ignored. |
| `site/data/rates.json` | The JSON file the website reads. Created by running the export script. |
| `site/data/market_pricing_ontario.json` | Ontario IESO hourly market pricing bins (576 bins: 12 months x 2 day types x 24 hours). |
| `site/data/market_structure_notes.json` | Research notes on market structure for every Canadian province/territory. |
| `site/data/missing_classes_report.json` | Audit report showing which utilities are missing customer classes. |
| `site/data/source_review_report.json` | Source URL audit — compares Excel reference URLs against registry. |

### Where the website lives

| File | What it does |
|---|---|
| `site/index.html` | The main web page. Two-tab layout: **Rate Browser** and **Market Pricing**. |
| `site/css/style.css` | How the page looks — includes styles for multi-select filters, heatmap, confidence indicators, source attribution, and market callouts. |
| `site/js/app.js` | The application logic: loads 5 JSON data files, deduplicates rates by effective_date, manages multi-select checkbox filter state (using JavaScript `Set`s), cascades province selection into the utility filter, renders rate cards with confidence dots, shows detail modals with source attribution and market callouts, and powers the Market Pricing dashboard (heatmap, Chart.js line chart, summary table, methodology). |

### Where the automation lives

| File | What it does |
|---|---|
| `.github/workflows/monthly-scrape.yml` | The automation recipe. Tells GitHub to run the scraper on the 1st of every month, save the results, and update the website. |

---

## How to Run the Project on Your Computer

### Before you start

You need:
- A computer (Windows, Mac, or Linux)
- Python 3.10 or newer installed ([download here](https://www.python.org/downloads/))
- A terminal / command prompt

### Step-by-step

**1. Open your terminal and go to the project folder:**
```
cd path/to/canada-utility-costs
```
(Replace `path/to/` with wherever you put the project.)

**2. Install the tools the project needs:**
```
pip install -r requirements.txt
pip install -e .
```
You only need to do this once (or again if someone adds new tools).

**3. Create the empty database:**
```
python -m pipeline.run_scrape --init-db
```
This creates `data/db/rates.db`. You only need to do this once.

**4. Run the scraper:**
```
python -m pipeline.run_scrape
```
This visits utility websites, downloads rate information, and stores it. It takes about 30–60 seconds.

**5. Export data for the website:**
```
python -m pipeline.export_json
```
This creates the JSON files that the website reads.

**6. Open the website:**
Double-click `site/index.html` or open it in your browser.

---

## How to Scrape Just One Utility

If you only want to update one utility's data:
```
python -m pipeline.run_scrape --utility "BC Hydro"
```

To scrape all utilities in a province:
```
python -m pipeline.run_scrape --province ON
```

To test a scraper without saving anything:
```
python -m pipeline.run_scrape --utility "BC Hydro" --dry-run
```

---

## How the Monthly Updates Work

The file `.github/workflows/monthly-scrape.yml` tells GitHub Actions to:

1. **On the 1st of every month**, start a computer in the cloud.
2. Install Python and all the project tools.
3. Run `python -m pipeline.run_scrape` (same command you'd run locally).
4. Run `python -m pipeline.validate` to check data quality.
5. Run `python -m pipeline.export_json` to update the website data.
6. Save the changes to the repository.
7. Update the GitHub Pages website.
8. If something goes wrong, create a GitHub Issue to alert you.

**You don't need to do anything for this to happen.** It runs automatically as long as the repository exists on GitHub.

**To run it early (not waiting for the 1st of the month):**
1. Go to the repository on GitHub.
2. Click the **"Actions"** tab.
3. Click **"Monthly Scrape & Deploy"** on the left.
4. Click the **"Run workflow"** button on the right.

---

## Where Official Sources Are Stored

All information about where rate data comes from is in **two files**:

### `data/sources/registry.json`

This is the file the scraper actually uses. It lists:
- Every utility the scraper knows about
- The URL(s) where rate data is published
- What format the data is in (HTML page, PDF, spreadsheet)
- Which Python scraper handles it
- Whether the scraper is working, partially working, or not built yet

### `data/inventory/utilities.json`

This is the complete reference list of ALL Canadian utilities — including ones we haven't built scrapers for yet. It includes:
- Every electricity and gas utility in every province and territory
- Their official websites
- Their rate pages
- What their regulator is
- How hard they would be to scrape
- What our current coverage status is

---

## How to Check If a Rate Is Still Correct

1. Open `site/data/rates.json` in a text editor (or look at the website).
2. Find the rate you want to check. Note the **source URL**.
3. Visit that URL in your web browser.
4. Compare the numbers on the utility's website to what's in our database.
5. If they're different, the utility has changed their rates. You need to update the scraper.

---

## How to Add a New Utility

See [docs/adding-a-utility.md](docs/adding-a-utility.md) for the full guide.

**The short version:**

1. Find the utility's official rate page.
2. Create a new Python file in `scrapers/utilities/`.
3. Copy the template from an existing scraper (like `bc_hydro.py`).
4. Fill in the rate values you found on the official site.
5. Add the utility to `data/sources/registry.json`.
6. Test it: `python -m pipeline.run_scrape --utility "Your Utility" --dry-run`

---

## What to Do When Something Breaks

### The scraper fails for a specific utility

**What happened:** The utility probably changed their website.

**What to do:**
1. Visit the URL in `data/sources/registry.json` for that utility.
2. Has the page moved? Update the URL.
3. Has the page layout changed? The scraper's HTML parsing needs updating.
4. Is the page down temporarily? Wait and try again.

### The monthly automation fails

**What happened:** The GitHub Actions workflow encountered an error.

**What to do:**
1. Go to the **Actions** tab on GitHub.
2. Click on the failed run to see the error log.
3. Common causes:
   - A utility website was down during the scrape.
   - A dependency (Python library) had a breaking update.
   - GitHub Actions had a temporary problem.
4. You can re-run the workflow by clicking **"Re-run all jobs"**.

### The website shows no data

**What happened:** The JSON data files are missing or empty.

**What to do:**
1. Make sure you've run the scraper: `python -m pipeline.run_scrape`
2. Make sure you've exported: `python -m pipeline.export_json`
3. Check that `site/data/rates.json` exists and is not empty.

### A rate value looks wrong

**What happened:** The scraper may have parsed the data incorrectly.

**What to do:**
1. Check the source URL to see the real value.
2. Look at the scraper file in `scrapers/utilities/`.
3. The value might be in the `SEED_*` data at the top of the file.
4. Correct the value and re-run the scraper.

---

## Understanding the Database

The database (`data/db/rates.db`) has these main tables:

| Table | What it stores |
|---|---|
| `utilities` | One row per utility company (name, province, type). |
| `tariffs` | One row per rate plan (name, customer class, rate structure, dates). |
| `rate_components` | One row per individual charge (energy charge, fixed fee, rider, etc.). This is the most detailed table. Includes `market_reference` for market-indexed components. |
| `customer_classes` | One row per customer class per utility (residential, commercial GS < 50 kW, GS >= 50 kW, etc.) with eligibility thresholds. |
| `market_pricing` | Representative hourly electricity market prices by province (576 bins for Ontario IESO: 12 months × 2 day types × 24 hours). Expandable to AESO. |
| `sources` | URLs where rate data was found. |
| `scrape_runs` | A log of each time the scraper ran. |
| `historical_snapshots` | A copy of each tariff's data at each scrape, so we can track changes over time. |
| `missing_data` | A list of known gaps — utilities or rates we don't have yet. |

**The key relationship:** A utility has many tariffs. A tariff has many rate components. This structure lets us capture the full complexity of utility bills instead of flattening everything into one number.

---

## Ontario Market Pricing — What You Need to Know

Ontario is special. Most Canadian provinces set electricity rates directly — a regulator publishes a price and that's what you pay. Ontario is different:

- **Small customers** (residential, GS < 50 kW) pay OEB-regulated TOU or Tiered rates — simple, published prices.
- **Large customers** (GS >= 50 kW) pay market-based energy prices that change every hour, plus a monthly "Global Adjustment" (GA) that covers long-term generation contracts.

The project models this with a **576-bin hourly pricing surface** stored in `site/data/market_pricing_ontario.json`. Each bin represents a typical $/kWh cost for:
- A specific **month** (1-12)
- A specific **day type** (weekday or weekend)
- A specific **hour** (0-23)

This was derived from 5 years of IESO HOEP data plus monthly GA rates.

**How to update it:** After each month's IESO data is published, re-run the market pricing pipeline to refresh the bins.

---

## Alberta's Deregulated Market

Alberta is the only province where retail electricity is fully deregulated. This means:

- **Distribution companies** (ATCO Electric, FortisAlberta, EPCOR Distribution, ENMAX Power) own the wires and charge regulated delivery rates.
- **Retail energy** is sold by competitive retailers. Customers who don't choose a retailer get the Regulated Rate Option (RRO) — a monthly pass-through of the AESO wholesale pool price.
- The scrapers capture both pieces separately: distribution charges in the distribution scrapers, and RRO energy in the retail scrapers.

---

## Source URL Management

### The Excel file is NOT a data source

There is an Excel file at `data/excel/old_urls.xlsm` that contains historical reference URLs and rate data. **No scraper reads this file.** It exists only for manual audit and comparison. It is git-ignored.

### The registry IS the system of record

`data/sources/registry.json` lists every utility's official source URLs and scraper configuration. When source URLs change, update the registry — not the Excel file.

### Source prioritization

When choosing which URL to use for a utility, prefer:
1. The utility's own rate schedule page
2. Regulator rate orders or decisions
3. Third-party aggregators (last resort)

---

## Glossary

| Term | What it means |
|---|---|
| **Scraper** | A program that visits a website and extracts data from it automatically. |
| **Database** | A structured file that stores information in tables (like a spreadsheet, but more organized). |
| **SQLite** | The specific database format we use. It's a single file — no server needed. |
| **JSON** | A text format for data that web browsers can read easily. |
| **GitHub Actions** | A service that runs code automatically on a schedule (like a cron job in the cloud). |
| **GitHub Pages** | A free service that hosts a static website from a GitHub repository. |
| **Tariff** | A rate plan or schedule published by a utility (e.g., "Residential Time-of-Use"). |
| **Rate component** | One individual charge within a tariff (e.g., "Tier 1 energy charge: $0.095/kWh"). |
| **TOU** | Time-of-Use pricing — rates that change based on time of day. |
| **Tiered** | Pricing where the rate changes based on how much you use (first X kWh at one price, the rest at a higher price). |
| **Demand charge** | A charge based on the peak power (kW) a customer draws, common for commercial and industrial accounts. |
| **Rider** | A temporary adjustment to rates — can be a surcharge or a credit. |
| **LDC** | Local Distribution Company — the utility that delivers electricity to your home (common in Ontario). |
| **OEB** | Ontario Energy Board — the regulator that sets many Ontario utility rates. |
| **IESO** | Independent Electricity System Operator — operates Ontario's wholesale electricity market. |
| **HOEP** | Hourly Ontario Energy Price — the real-time wholesale electricity price in Ontario. |
| **GA** | Global Adjustment — monthly charge in Ontario covering contracted/regulated generation costs. |
| **AESO** | Alberta Electric System Operator — operates Alberta's wholesale electricity market. |
| **RRO** | Regulated Rate Option — default retail electricity rate in Alberta for customers who haven't chosen a competitive retailer. |
| **Class A/B** | Ontario GA allocation categories. Class A (> 1 MW) pays based on coincident peak demand. Class B (everyone else) pays a flat per-kWh charge. |
| **kWh** | Kilowatt-hour — the standard unit for measuring electricity consumption. |
| **GJ** | Gigajoule — a unit for measuring natural gas energy content. |
| **m³** | Cubic metre — a unit for measuring natural gas volume. |

---

## How to Run Tests

Tests check that the code works correctly. Run them with:

```
pytest
```

There are currently 233+ tests across 6 test files (test_scrapers, test_new_scrapers, test_live_parsers, test_parsing, test_change_detection, test_validation, test_schema).

If everything passes, you'll see green output. If something fails, it will show you exactly what went wrong and where.

---

## Documentation Review Rule

**Every task** — whether adding a feature, fixing a bug, or refactoring — must include a final documentation review step. At minimum, check whether the following files need updates:

| File | When to update |
|---|---|
| `README.md` | Roadmap changes, new phases completed, tech stack additions, project structure changes |
| `AGENTS.md` | New files added, glossary terms needed, troubleshooting patterns discovered |
| `CLAUDE.md` | Architecture changes, new conventions, test count changes, key pattern additions |
| `docs/adding-a-utility.md` | Scraper patterns or helper functions changed |
| `docs/live_parser_gap_report.md` | Live parser status changed (new parsers, fixed gaps) |

If the task doesn't warrant a change to any of these, no update needed — but the check should happen.

---

## File Formats Explained

- **`.py`** — Python source code. This is the programming language the scrapers are written in.
- **`.json`** — JavaScript Object Notation. A structured data format used for the registry, exports, and website data.
- **`.sql`** — SQL (Structured Query Language). The commands that create the database tables.
- **`.db`** — SQLite database file. The actual database where scraped data lives.
- **`.html`** — Web page file.
- **`.css`** — Stylesheet file. Controls how the web page looks.
- **`.js`** — JavaScript file. Makes the web page interactive.
- **`.yml`** — YAML file. Used for GitHub Actions configuration.
- **`.md`** — Markdown file. Human-readable documentation (like this file).

## Phase 5: Live Sources, Fallbacks, and History

- **Live parsed** means the scraper read the current official page/document and rebuilt the tariff.
- **Officially verified** means the project already knows the tariff structure and proved every component in its tariff, label, and unit context in a current official document. It is not a number-only match.
- If fetching fails or a schedule changes shape, `mark_fallback()` labels every tariff and component `unverified` and adds `Provenance: seed_fallback` to notes. Never raise this confidence by hand.
- “Structural drift” in logs names components that could not be verified. Open the registry URL, find the current approved schedule, update the utility-specific interpretation and fixture, then run its targeted dry run.
- Ontario updates start with the OEB common-rate page, then each distributor's approved tariff. Alberta wires, default retail, AESO, gas, and northern sources must remain separate and preserve their published classes, communities, tiers, and units.
- Test comparison locally with `python -m http.server --directory site 8000`: add two cards, open **Compare**, remove/replace either, and check the mobile horizontal table. It never calculates a bill total.
- Every successful stored scrape appends `historical_snapshots`. Canonical hashes ignore component ordering but change for values, units, tiers, dates, or structure; old effective-date versions are never deleted.
