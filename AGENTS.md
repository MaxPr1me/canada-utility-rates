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

GitHub Actions (GitHub's cloud computers) runs a monthly scrape on the 1st and a "source
health" test scrape, which publishes nothing, on the 15th. On October 9 the website was
published successfully after each of the four changes pushed that day, and a hand-started
source health run passed every step, including a full scrape (about 11 minutes); its
per-utility list of live and estimated records has not been reviewed yet. Three monthly-scrape
steps have never run: keeping the database between cloud runs, opening an issue automatically
when something fails, and publishing the website automatically afterwards. The first scheduled
monthly scrape is November 1; see "How the Monthly Updates Work" below and [README.md](README.md).
The latest export (October 9, batch 12) has 910 latest live tariffs and 480 estimates; stored
history contains 916 live versions and 3,616 snapshots. Registry coverage is not the same as
live coverage. The active campaign covers 16 provincial utilities (243 latest live records) and,
from October 7, the four territorial utilities (109 latest live records). All 20 have live output.
All 47 active Ontario distributors are live (490 records); PUC Distribution was added on
October 9 even though its tariff prints no connection rate. Batch 12 also added Alberta
electricity (28 records: four wires companies and three Rate of Last Resort providers) and
Ontario/Alberta gas (40 records: Enbridge Gas, ATCO Gas and EPCOR Natural Gas (Ontario)).
Only AESO, a market reference, has no live output.
Since October 9 the export also writes Ontario electricity "representative models" (typical
monthly costs; see the glossary), which the website does not show yet. Also since October 9,
the website's Market Pricing page shows real hourly Ontario market prices from 2020-2024 (the old
HOEP market, before May 2025; see "Ontario Market Pricing" below).
These counts include conditional products and reference-only services, not that many
fully audited building classes. SaskPower's scoped building schedules are audited;
remaining utility gaps are listed in the [coverage matrix](docs/phase5_completion_matrix.md).

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

## Working Rules (Read First)

Two rules govern every change to this project. They matter more than any single feature.

**1. Never show "default" numbers as if they were real.**
Some rates in the code are *seed values* — hand-entered fallback numbers used only when the live official website can't be read. These are estimates, not live data. The website must never present them as current rates. They are labelled **"Estimated"**, hidden by default, and only appear if the visitor ticks **"Show estimated (not live-verified) rates."** Only numbers pulled from (or checked against) a live official source are shown by default. If you add or change a scraper, make sure real live data is marked live and fallbacks stay marked as estimates — never dress up a default value as the real thing.

**2. When unsure, ask — don't assume.**
If a task is unclear, or there is more than one sensible way to do it, stop and ask which path to take before making changes. Guessing wastes effort and can hide problems. A short question is always better than an assumption.

**Current focus: building energy costs.** Prioritize residential (including single-family
homes), commercial, institutional and, from October 6, building-related industrial
general facility service defined by size, voltage or interruptibility. NECB 2025
is a use-case reference, not a utility-rate eligibility rule or a compliance claim.
Process-specific farm, oil-field, irrigation, NGV fuelling, EV charging, lighting,
wholesale/reseller and standby-only services are excluded. Completed work and history
for those classes remain as reference; do not delete them.

**Context checkpoint rule:** when approaching the context/token limit (target: about
90%), stop opening new work. Leave room to finish the bounded batch, run its checks,
record completed work, test results, remaining gaps and the exact next step in the
coverage matrix/handoff, then commit and push the verified changes before stopping.
If an exact context meter is unavailable, checkpoint conservatively rather than claim
an exact percentage. Preserve history and do not stage unrelated work.

---

## Important Files and What They Do

### Where the scrapers live

| File | What it does |
|---|---|
| `scrapers/base.py` | The "template" that all scrapers follow. You don't change this unless you're adding a new feature that applies to ALL scrapers. |
| `scrapers/utilities/bc_hydro.py` | Scrapes BC Hydro electricity rates. |
| `scrapers/utilities/hydro_quebec.py` | Scrapes Hydro-Quebec electricity rates. |
| `scrapers/utilities/ontario_ldc.py` | **Data-driven scraper for every Ontario LDC.** One class handles every Ontario local distribution company. All 47 active distributors are configured (`OEB_TARIFF_DOCUMENTS`) and read from their OEB-approved tariff PDF; if a tariff cannot be downloaded, labelled estimates are used where they exist. Large demand classes also get a "Market Energy" line with no number (shown as "Variable"). |
| `scrapers/utils/oeb_tariff.py` | Reads OEB "Tariff of Rates and Charges" PDFs: classes, rate zones, riders and their end dates, conditional charges, and fail-closed rejections. Per-document settings handle unusual PDFs (`"extract": {"y_tolerance": N}`) and PUC Distribution's tariff, which prints no connection rate (`"connection_rate": "not_printed"`). |
| `scrapers/utilities/toronto_hydro.py` | Toronto Hydro (legacy scraper, separate from the LDC scraper). |
| `scrapers/utilities/enbridge_gas.py` | Enbridge Gas (Ontario) from the OEB-approved Rate Handbook PDF: 20 system-gas records in the EGD, Union North and Union South rate zones, including the quarterly gas supply (QRAM) price. |
| `scrapers/utilities/epcor_gas_ontario.py` | EPCOR Natural Gas (Ontario): Aylmer and Southern Bruce rate zones from EPCOR's rate pages, checked against the OEB rate order and QRAM notice. It has no estimates: if the sources fail it returns nothing. |
| `scrapers/utilities/epcor_gas.py` | The old Alberta "EPCOR Natural Gas" entry, retired October 9 because EPCOR does not distribute gas in Alberta. Monthly runs skip it; its history stays. |
| `scrapers/utilities/atco_gas.py` | ATCO Gas (Alberta) North and South delivery rates from the rate schedule PDFs, plus Direct Energy Regulated Services' monthly default gas price. |
| `scrapers/utilities/atco_electric.py` | ATCO Electric distribution and transmission charges (Alberta) from the 2026 price schedules; each class must add up to the printed total. |
| `scrapers/utilities/fortisalberta.py` | FortisAlberta distribution and transmission charges (Alberta) from the newest Rates, Options and Riders PDF. |
| `scrapers/utilities/epcor_distribution.py` | EPCOR Distribution charges (Edmonton, Alberta); the 2026 rates are interim, so they are medium confidence. |
| `scrapers/utilities/enmax_power.py` | ENMAX Power distribution and transmission charges (Calgary, Alberta). |
| `scrapers/utilities/direct_energy_regulated.py` | Direct Energy Regulated Services Rate of Last Resort energy price (ATCO Electric area, Alberta). |
| `scrapers/utilities/enmax_energy.py` | ENMAX Energy Rate of Last Resort price and daily administration charge (Calgary area, Alberta). |
| `scrapers/utilities/epcor_energy_alberta.py` | EPCOR Energy Alberta Rate of Last Resort price and administration charge (EPCOR Distribution and FortisAlberta areas). |
| `scrapers/utils/alberta_rolr.py` | Shared Rate of Last Resort helper: checks each provider's price against the Utilities Consumer Advocate table and stops treating it as live once the fixed term ends. |
| `scrapers/utilities/aeso.py` | AESO market reference price (Alberta wholesale); still an estimate until the Alberta market work (Phase 6C). |
| `scrapers/utilities/nl_hydro.py` | NL Hydro electricity rates (Newfoundland — residential + commercial). |
| `scrapers/registry.py` | Reads the list of all utilities and their scraper info. |
| `scrapers/utils/parsing.py` | HTML/PDF parsing helpers, including PDF URL resolution and strict `verify_tariff_values()` checks that prove fallback values still appear in an official schedule. |
| `scrapers/utils/change_detection.py` | Compares live-parsed rates against seed data. Flags changes by severity (info/warning/critical). If critical drift is detected, the scraper rejects live data and falls back to seed. |
| `scrapers/utils/market_pricing.py` | Reads the Ontario market history file (real hourly HOEP prices plus the actual Class B Global Adjustment, 2020-2024). It refuses a file that was not built from real observed prices. |
| `scrapers/utils/validation.py` | Data quality checks run after every scrape. |

### Where the data lives

| File | What it does |
|---|---|
| `data/sources/registry.json` | **The master list (system of record).** 87 registered utilities use 33 scraper modules; a 34th, legacy Toronto module is unregistered. Eight absorbed Ontario distributors have `status: "merged"` and a `merged_into` successor; the mistaken Alberta "EPCOR Natural Gas" entry has `status: "retired"`. Monthly runs skip both kinds but keep their history. Some scrapers also contain source URL constants that must stay synchronized. |
| `data/inventory/utilities.json` | The full inventory of ALL Canadian utilities — even ones we don't scrape yet. This is the reference list. |
| `data/db/rates.db` | The SQLite database where scraped rates are stored. Created automatically when you first run the scraper. |
| `data/excel/old_urls.xlsm` | **Audit reference only.** An Excel file with historical URLs and rate data. NO scraper reads this file. It is git-ignored. |
| `site/data/rates.json` | The JSON file the website reads. Created by running the export script. |
| `site/data/market_pricing_ontario.json` | Ontario market history: 576 averages (12 months x weekday/weekend x 24 hours) of the real hourly HOEP price and the actual monthly Class B Global Adjustment for 2020-2024. Rebuilt by `scripts/generate_market_pricing.py` (see "Ontario Market Pricing" below). |
| `site/data/market_structure_notes.json` | Research notes on market structure for every Canadian province/territory. |
| `site/data/missing_classes_report.json` | Audit report showing which utilities are missing customer classes. |
| `site/data/source_review_report.json` | Source URL audit — compares Excel reference URLs against registry. |

### Where the representative models live

A *representative model* is a "typical" monthly cost for a province, worked out from the middle
value (the median) of its utilities' live rates. Only Ontario electricity has models so far, and
the website does not show them yet.

| File | What it does |
|---|---|
| `data/models/crosswalk.json` | The sorting list. Its 224 rules are read from top to bottom, and the first rule that fits decides where each live tariff goes: into a model group (province, fuel, customer type, rate structure and size) or out, with a written reason. Today 548 of the 910 live tariffs are used and 362 are left out on purpose; none is left unsorted. Alberta electricity waits for Phase 7C (its models must combine a wires company with a Rate of Last Resort provider), Ontario and Alberta gas wait for Phase 7D, and the territories come later. The other provinces are already sorted, but only Ontario's models are calculated so far. |
| `data/models/usage_levels.json` | The example customers, approved by the project owner: homes using 500, 1,000 or 2,000 kWh a month; small businesses (under 50 kW) using 2,000 kWh at 10 kW or 8,000 kWh at 25 kW; medium businesses (50-499 kW) using 40,000 kWh at 100 kW; large businesses (500-4,999 kW) using 500,000 kWh at 1,000 kW. It also holds the Ontario Energy Board's split of use between time-of-use periods and a short, reviewed list of "conditional" Ontario charges that a typical customer does pay. |
| `data/models/taxes.json` | Sales taxes (GST, HST, PST, QST, RST) and automatic bill rebates, such as the Ontario Electricity Rebate, for every province and territory: electricity and gas, homes and businesses. Municipal taxes and income-tested programs are left out. |
| `pipeline/representative_models.py` | The calculator. For every utility it works out the monthly cost at each example level, then reports the median, the spread, the real utility closest to the median and any utility far from it (an "outlier"), without and with tax, plus a written explanation of how each number was made. |
| `site/data/representative_models.json` | The results. The export step rewrites this file every time; if the calculation fails, the export still finishes and the previous file is kept. The website does not read it yet (Phase 7F). These are comparison aids, never rates anyone is billed. |

### Where the website lives

| File | What it does |
|---|---|
| `site/index.html` | The main web page. **Rate Browser**, **Market Pricing** and the existing two-tariff **Compare** view. The new Across-Canada comparison is planned for Phase 9, not implemented. |
| `site/css/style.css` | How the page looks — includes styles for multi-select filters, heatmap, confidence indicators, source attribution, and market callouts. |
| `site/js/app.js` | The application logic: loads 5 JSON data files, deduplicates rates by effective_date, manages multi-select checkbox filter state (using JavaScript `Set`s), cascades province selection into the utility filter, renders rate cards with confidence dots, shows detail modals with source attribution and market callouts, and powers the Market Pricing dashboard (heatmap, Chart.js line chart, summary table, methodology). |

### Where the automation lives

| File | What it does |
|---|---|
| `.github/workflows/scrape.yml` | Monthly tests, scrape, validation and export on the 1st. |
| `.github/workflows/deploy.yml` | Separate GitHub Pages deployment on push or manual dispatch. |
| `.github/workflows/source-health.yml` | Non-blocking dry run on the 15th; uploads logs without publishing. |

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
python -m playwright install chromium
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
This visits utility websites, downloads rate information, and stores it. A full run
can take several minutes. A completed utility may have returned estimates, so read
the end-of-run box: it shows how many records were live and how many were estimates,
and lists any utility that returned only estimates ("Seed-only utilities").

**5. Export data for the website:**
```
python -m pipeline.export_json
```
This creates the JSON files that the website reads. It also rewrites the Ontario representative
models file, which the website does not read yet.

**6. Open the website:**
Run `python -m http.server --directory site 8000`, then open http://localhost:8000.
The browser needs HTTP access to fetch the JSON files; double-clicking the HTML
is not a reliable way to load them.

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

The file `.github/workflows/scrape.yml` tells GitHub Actions to:

1. **On the 1st of every month**, start a computer in the cloud.
2. Install Python, the project tools and Playwright Chromium.
3. Restore the database from the `data-history` GitHub Release asset.
4. Run `python -m pipeline.run_scrape` (same command you'd run locally).
5. Run `python -m pipeline.validate` to check data quality.
6. Run `python -m pipeline.export_json` to update the website data.
7. Upload the database asset only after validation and export succeed, then save the updated site data to the repository.
8. Leave deployment to the separate **Deploy Site** workflow, now triggered by a successful **Monthly Scrape** run and checking out `main`.
9. Attempt to create a GitHub Issue for test, scrape or validation/export failures.

**Known limitations:** only part of this has run on GitHub so far. On October 9 the **Deploy
Site** workflow published the website successfully after each of the four changes pushed that
day, and a hand-started **Source Health** run (run #4) passed every step: it installed the
Chromium browser, ran the full scrape without publishing anything (about 11 minutes) and
uploaded its logs. Its per-utility summary of live and estimated records has not been reviewed
yet. Never run yet: restoring and uploading the database through the `data-history` release
(steps 3 and 7), the automatic failure issues (step 9) and Deploy Site starting by itself after
a successful Monthly Scrape (step 8). The first scheduled Monthly Scrape is November 1; the
project owner may start one by hand earlier (see below). Check that first run before trusting
those steps. GitHub Pages must use **GitHub Actions** as its source; the automatic trigger
(`workflow_run`) only fires from the default branch. Keep your local database to preserve
history; do not delete it when updating a parser.

**To run it early (not waiting for the 1st of the month):**
1. Go to the repository on GitHub.
2. Click the **"Actions"** tab.
3. Click **"Monthly Scrape"** on the left.
4. Click the **"Run workflow"** button on the right.

After a successful data update, **Deploy Site** can still be run manually if the
new automatic handoff has not yet been verified.

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
4. Save a small source-derived test fixture and parse the published classes, values, units and dates.
5. Add the utility and official schedule URLs to `data/sources/registry.json`.
6. Run the focused tests, then `python -m pipeline.run_scrape --utility "Your Utility" --dry-run`. Seed constants alone are not a completed live parser.

---

## What to Do When Something Breaks

### The scraper fails for a specific utility

**What happened:** The utility probably changed their website.

**What to do:**
1. Visit the URL in `data/sources/registry.json` for that utility.
2. Has the page moved? Update the registry and any URL constant used by the scraper.
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
4. Serve the site over HTTP using the command above.

### Python cannot find pytest, requests, or the browser

Select a Python 3.10+ environment and install the requirements in that same
environment. Then run `python -m playwright install chromium`. Activating an
older or empty environment does not make the dependencies available.

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

Since May 1, 2025 that hourly market price is the **Ontario Price** (Ontario Electricity Market
Price, OEMP): the Day-Ahead Ontario Zonal Price plus a small Load Forecast Deviation Adjustment.
The older Hourly Ontario Energy Price (HOEP) was retired on April 30, 2025. Since October 9 the
large customers' tariffs show a "Market Energy" line with no number, labelled "Variable",
because the price changes every hour; no made-up average is stored in a tariff.

The website's **Market Pricing** page shows what this market really cost before it changed:
**real (observed) prices**, not estimates, clearly labelled as the market before May 2025.
In plain words:

- The **HOEP** was Ontario's wholesale electricity price, set every hour, until April 30, 2025.
- The **Global Adjustment (GA)** is charged per kWh and changes once a month. "Class B" is the
  version most customers pay; the page uses its actual monthly rates.
- A large customer buying at market prices paid roughly HOEP + GA for each kWh.

The page covers every hour of the five full years 2020-2024. The averages are stored in
`site/data/market_pricing_ontario.json` as 576 "bins", one for each:
- **month** (1-12)
- **day type**: weekday (Monday-Friday) or weekend (Saturday-Sunday); a statutory holiday counts
  as the weekday it falls on
- **hour** (0-23, Eastern Standard Time)

Each weekday bin is the average of 101-112 real hours and each weekend bin of 41-46. Example: on
July weekdays at 4 p.m. the HOEP averaged 5.09 cents/kWh and the GA 6.58 cents/kWh, so 11.67
cents/kWh together, over 110 hours.

**Why old prices?** The HOEP ended on April 30, 2025. The new Ontario Price only started in May
2025, and the IESO keeps only about 90 days of its hourly files online, so a full year of it
cannot be downloaded. (The project would have to save the daily files itself for 12 months; that
has not started.) A note on the page that is always visible says this and links to the IESO's
current prices. These averages are never copied into a tariff: large customers' tariffs keep
their "Variable" line.

**How to update it:** run `python scripts/generate_market_pricing.py`. It downloads the official
IESO files (the yearly hourly HOEP prices and the GA spreadsheet), checks that every month's
average matches the IESO's own published monthly average (all 60 months agree within one cent
per MWh) and that the units are right, and only then rewrites the file. If anything is missing
or a check fails, it writes nothing and stops with an error, so the old file stays as it was.
It is not part of the monthly automation. Because 2020-2024 are finished years, the numbers do
not change unless someone chooses other years (`--start-year` and `--end-year`).

Two GA details are written into the file: April-June 2020 use the lower, capped GA (115 $/MWh)
that the IESO published under a provincial emergency order, and the 2021 rates leave out a
separate recovery charge billed that year to Class B customers who were not on the Regulated
Price Plan. These choices, and counting holidays as weekdays, are defaults the project owner can
change. If the file was not built from real prices, the website hides the dashboard and shows a
"not available" notice instead.

---

## Alberta's Deregulated Market

Alberta is the only province where retail electricity is fully deregulated. This means:

- **Distribution companies** (ATCO Electric, FortisAlberta, EPCOR Distribution, ENMAX Power) own the wires and charge regulated delivery rates. Since October 9 their main home and business rates are read live from their approved schedules. Delivery is split into **distribution** and **transmission** lines, and temporary riders are listed separately with their own dates.
- **EPCOR Distribution's 2026 rates are interim** (approved only temporarily), so they are shown at medium confidence with a note.
- **Retail energy** is sold separately from wires service. Customers without a retail contract pay the **Rate of Last Resort** (RoLR), which replaced the Regulated Rate Option (RRO) on January 1, 2025. Its price is fixed until December 31, 2026: 12.02 cents/kWh from Direct Energy Regulated Services (ATCO Electric area), 12.06 from ENMAX Energy (Calgary) and 12.01 from EPCOR Energy Alberta (Edmonton and FortisAlberta areas). Each price must match the Government of Alberta's Utilities Consumer Advocate table. After December 31, 2026 these records stop counting as live until the next price is published. Old RRO estimates stay in history.
- **AESO** (the wholesale market) is still only a reference estimate; Alberta market prices are future work (Phase 6C).
- The code models these pieces separately and never adds them into one price.

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
| **Multiplier** | A tariff-defined factor based on eligible dwellings or rooms. Some bulk-metered buildings multiply daily charges and energy allowances by this factor; it is not automatically one. |
| **Demand charge** | A charge based on the peak power (kW) a customer draws, common for commercial and industrial accounts. |
| **Rider** | A temporary adjustment to rates — can be a surcharge or a credit. |
| **Representative model** | A "typical" monthly cost for a province (Phase 7), built from the median of its utilities' live tariffs at set example usage levels, shown without and with tax, with a note explaining exactly how it was made. Built for Ontario electricity since October 9 (`site/data/representative_models.json`) but not shown on the website yet; other provinces and gas come later. It is a comparison aid, never a rate anyone is billed, and it never counts as live coverage. |
| **Median** | The middle value when numbers are sorted from lowest to highest. Unlike an average, one unusually high or low utility barely moves it. |
| **Outlier** | In a representative model, a utility whose cost is far from the median (more than 30% away, or well outside the range of the middle half of the utilities). It is named with how far away it is; it is not left out. |
| **LDC** | Local Distribution Company — the utility that delivers electricity to your home (common in Ontario). |
| **OEB** | Ontario Energy Board — the regulator that sets many Ontario utility rates. |
| **QRAM** | Quarterly Rate Adjustment Mechanism — the Ontario Energy Board process that resets Ontario natural gas supply prices every three months. |
| **IESO** | Independent Electricity System Operator — operates Ontario's wholesale electricity market. |
| **HOEP** | Hourly Ontario Energy Price — Ontario's former real-time wholesale electricity price. **Retired April 30, 2025** and replaced by the Ontario Price (OEMP). The Market Pricing page shows its real hourly history for 2020-2024. |
| **Ontario Price (OEMP)** | Ontario Electricity Market Price — Ontario's hourly wholesale electricity price since May 1, 2025: the Day-Ahead Ontario Zonal Price plus a Load Forecast Deviation Adjustment. Large customers who are not on the Regulated Price Plan pay it plus the Global Adjustment. |
| **DA-OZP** | Day-Ahead Ontario Zonal Price — the hourly price for the Ontario zone set a day ahead in the IESO market; the main part of the Ontario Price. The IESO keeps only about 90 days of the hourly files online. |
| **Variable (market) charge** | A charge that follows a market price that changes over time (for example the Ontario Price). It is stored with a link to the market but no number, and the website shows "Variable". |
| **GA** | Global Adjustment — monthly charge in Ontario covering contracted/regulated generation costs. The Market Pricing page shows the actual monthly Class B rates for 2020-2024. |
| **AESO** | Alberta Electric System Operator — operates Alberta's wholesale electricity market. |
| **RRO** | Regulated Rate Option — Alberta's former default retail electricity rate. **Replaced by the Rate of Last Resort on January 1, 2025**; old RRO estimates stay in history. |
| **RoLR** | Rate of Last Resort — Alberta's default retail electricity rate since January 1, 2025, for customers without a retail contract. Each provider's price is fixed for a two-year term (currently January 1, 2025 to December 31, 2026). |
| **UCA** | Utilities Consumer Advocate — Government of Alberta office whose default-rates table is used to double-check Alberta default electricity and gas prices. |
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

There are 1,683 tests across 8 test modules, including `test_phase5_hardening` for
provenance, storage and history. Normal tests block unmocked network access.
The BC Hydro, FortisBC Electric, Hydro-Quebec, NL Hydro, Manitoba Hydro, NB Power,
Newfoundland Power, Maritime Electric, NSPower, SaskPower, SaskEnergy, Centra Gas,
FortisBC Energy, Energir, Heritage Gas (Eastward), Liberty NB, Yukon Energy, NTPC,
Qulliq, Ontario OEB tariff (including PUC Distribution), ENMAX Power, ATCO Electric, EPCOR
Distribution, FortisAlberta, Alberta Rate of Last Resort, Enbridge Gas, ATCO Gas and EPCOR
Natural Gas (Ontario) fixtures in `tests/fixtures/` hold official
HTML/PDF-text excerpts, source URLs and page/section details for repeatable parser
tests. Batch 10 expands source-derived coverage for eleven utilities including the
territories, and batch 12 adds the Alberta, Ontario/Alberta gas and PUC Distribution fixtures;
a fixture covers only the saved classes and conditions and does not prove
the entire utility catalogue is complete. The representative model tests use frozen copies of
exported records (`rm_records_sample.json`, `rm_engine_sample.json` and `rm_records_b12.json`),
so the tests that run before each monthly scrape never depend on that month's data. The Ontario
market history tests use `ieso_market.json`, small saved excerpts of the official IESO files, so
they never download anything.

If the test run seems to freeze, check the size of `logs/scrape.log`. PDF libraries
can write huge debug logs; `setup_logging()` now keeps them quiet and caps the file at
10 MB (three older copies kept). The log is only a debug diary: deleting it is safe.

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

---

## Phase 5: Live Sources and Fallbacks - Rules That Still Apply

These rules came out of the live-source work (Phase 5). They still apply to every change.

### Labels and checks

- **Live parsed** means the scraper read the current official page or document and rebuilt the tariff from it.
- **Officially verified** means the project already knows the tariff's structure and proved every component, with its tariff, label and unit, in a current official document. Finding the same number somewhere is not enough.
- **Estimate (fallback):** if fetching fails or a schedule changes shape, `mark_fallback()` labels every tariff and component `unverified` and adds `Provenance: seed_fallback` to the notes. Never raise this confidence by hand.
- **"Structural drift"** in the logs names components that could not be verified. Open the registry URL, find the current approved schedule, update that utility's interpretation and test fixture, then run its targeted dry run.
- A class that was read completely can stay live when another class of the same utility fails, but a mixed list of live and estimated records is never labelled entirely live.
- "Fails closed" means a doubtful source is rejected instead of guessed. A missing carbon-charge source cannot be hidden under a live label. When a tariff is built from parts with different dates, the tariff takes the latest required part's date and each part keeps its own date.
- Conditional, optional and source-blocked prices are not charges that every customer pays.
- Source-check dates, live-record counts and catalogue completion are different facts. **Completing a utility** means auditing its building-relevant standard published classes, not just replacing existing estimates or completing every unrelated service.
- Different kinds of sources (Alberta wires, Alberta default retail, AESO, gas and northern utilities) stay separate and keep their published classes, communities, tiers and units.
- Some products are left out on purpose (for example BC Hydro RS1828, Hydro-Quebec Rate F/FP and FortisBC Energy 11RNG). Exclusions and remaining gaps are listed in the [parser gap report](docs/live_parser_gap_report.md) and the [coverage matrix](docs/phase5_completion_matrix.md).

### History, testing and teamwork

- Every successful stored scrape adds a copy of each tariff to `historical_snapshots`. The snapshot fingerprint ignores the order of components but changes when values, units, tiers, dates or structure change. Old effective-date versions are never deleted; the website shows the latest version of each tariff.
- Merged and retired registry entries are skipped by monthly runs but keep their history.
- To test the Compare view locally, run `python -m http.server --directory site 8000`, add two cards, open **Compare**, remove or replace either one, and check the sideways-scrolling table on a phone-sized screen. It never calculates a bill total.
- Parallel workers may each own separate utility files, but database, export, registry and test integration and publishing are done one at a time. Preserve all earlier snapshots.

### Market prices

- A price that follows a market (for example the energy price of Ontario's large customers) is stored without a number and shown as "Variable", never as a made-up value.
- Four market-indexed products wait for Phase 6D, which will add them as "Variable" lines: BC Hydro RS1892, FortisBC Electric RS38, NSPower one-part real-time pricing and NL Hydro monthly non-firm prices.

### Ontario electricity

- Updates start with the OEB common-rate page, then each distributor's OEB-approved Tariff of Rates and Charges PDF. The OEB bill-data XML is only a cross-check, never a source of values. Each rate zone gets its own records.
- Homes and small businesses (GS<50) get the live provincial Regulated Price Plan (RPP) energy price plus the distributor's delivery charges. Larger demand classes get delivery charges plus a "Market Energy" line with no number ("Variable").
- Algoma's R1 is split into year-round dwellings (fully fixed) and O. Reg. 445/07 customers. Its R2 (50 kW and over, billed per kW) is delivery-only and has no "Market Energy" line, because accounts for homes stay eligible for the Regulated Price Plan.
- A class that cannot be read cleanly is rejected, not guessed, and no new estimate is made for it; older estimates stay in history, labelled. A configured distributor that rejects a class, or publishes no such class, does not re-send old estimates for it. Estimates are still used if the tariff cannot be downloaded or read at all.
- Some PDFs print values slightly above their labels; the fix is a per-document text-reading setting (`"extract": {"y_tolerance": N}`), never a guessed value.
- PUC Distribution's approved tariff prints no transmission connection rate, so each of its records carries a note saying so.
- Merged distributors keep their history; their successors (Enova Power and GrandBridge Energy) now publish the rates. The successors have no estimates, so they return nothing if their tariff cannot be read.

### Alberta

See also "Alberta's Deregulated Market" above.

- The wires companies list distribution and transmission as separate lines and keep each current rider as its own dated line; an expired rider is left out by its date. Wires charges and energy prices are never added into one price.
- ATCO Electric's lines must add up to the total printed in its schedule.
- EPCOR Distribution's 2026 rates are interim, so they are shown at medium confidence with a note.
- Each Rate of Last Resort price, and ATCO Gas's monthly default gas price, must match the Utilities Consumer Advocate table. After the fixed term ends (December 31, 2026), the Rate of Last Resort records stop counting as live until the next price is published.

### Other utilities

- **BC Hydro:** the power-factor surcharge is a conditional percentage of the business rate charges for poor (lagging) power factor, not an extra charge for every customer.
- **FortisBC Electric:** the current residential price is flat; the older tiered version stays in history. Rate 21's kW and kVA charges are alternatives, and voltage/transformation discounts are conditional negative credits.
- **FortisBC Energy:** Rates 1-3 have **daily** basic charges. The Rate 5 basic charge (written contract, about 5,000 GJ or more a year) is **monthly** as printed in the tariff, even though the business page says daily, so Rate 5 is not interchangeable with Rates 1-3. Rate 4 is seasonal (April 1-November 1). Revelstoke business rates are live only when the approved tariff index says the class is offered in Revelstoke. Fort Nelson Rates 4/5 have no published price table (a gap).
- **Hydro-Quebec:** DM (grandfathered) and DN charges and energy allowances depend on the approved multiplier. DP has summer and winter demand charges. DN applies north of the 53rd parallel except Schefferville and normally uses multiplier one; its older DM-eligibility exception does not restrict every DN customer. Supply-voltage credits are conditional and do not apply to everyone. Minimum bills, demand allowances and transformation-loss rules stay conditions, not extra charges or calculated totals. A missing continuation page rejects only the affected class. DT switches price with the outdoor temperature, not the clock. Flex D uses notified events. Winter Credit is a closed, conditional adjustment to Rate D that keeps the published reference-energy rules.
- **Manitoba Hydro:** a failure on the residential page or the commercial page affects only that page's records.
- **SaskPower:** maintain the audited building scope (standard, bulk-metered and diesel residential service and R23/R24 renewable access). Standard E01/E03 keeps its identity only when both published columns agree. Bulk fixed charges are per unit, not per account.
- **SaskEnergy:** delivery-only service leaves out private (retailer) commodity prices.
- **Centra Gas:** published delivery and demand parts stay separate, with no guessed heat conversion and no private marketer commodity price. Classes need the approved PUB schedule's volume, contract and billing-demand conditions. Mainline Interruptible prices exist only on scanned pages, so they were typed in once by hand, checked visually and are shown at medium confidence; the scraper drops them automatically if those scanned pages ever change. Do not use this approach for any other scanned document without asking.
- **NL Hydro:** phase/amperage fixed charges are alternatives, not added together; seasonal options need their matching base schedules.
- **NSPower:** the mandatory FAM, DSM and storm riders are separate from base energy; Green Power blocks are opt-in, not a standard charge. Residential service includes standard service, storage-heating time-of-day service and closed-enrollment TOU and critical-peak pilots. The pilots are conditional, and their records separate the tariff's conditional interim phase from its dated November pricing; do not assume an existing customer's system-restoration status from an advertising page. MURB has its own rider rows and a minimum-bill condition, and the approved book applies its peak price on weekends and holidays. Solar Garden and Community Solar records are subscriber adjustments to another tariff, not replacement household energy prices. Dates past the supported tariff/rider year fail closed.
- **Energir:** follows the current document link and fails closed on an edition/month mismatch. D3/D4 minimum daily obligation bands are per m³/day of **subscribed volume**; above-subscribed-volume withdrawal, average load-balancing and renewable-gas charges are conditional. Inventory adjustments depend on each customer's storage use and have no published price, so they are explained, never given a number.
- **Eastward (Heritage Gas):** follows the current document link and fails closed on an edition/month mismatch. Municipal riders apply to a limited charge base. Rate Class 3's demand charge is per GJ of Billing Demand per month (the greater of 225 GJ, contract demand or maximum 24-hour use), a unit taken from the approved tariff PDF rather than the rate table. Rate Class 4 is negotiated per site and not published, so it is an exclusion, not a parser gap.
- **Liberty NB:** the MGS/LGS customer charges are alternatives. Off-Peak Service eligibility is April-November only; the December-March overrun is a note.
- **Territories:** government subsidies stay separate and conditional; never fold them into base prices. NTPC's Taltson interruptible heating is conditional. Qulliq's rates are interim (medium confidence) until a final decision is published.
- **Yukon Energy:** Rate 1160 lists base rates, the R/J/J1 percentage riders, fuel Rider F and dated residential relief separately; never add riders to a price that already includes them. The other residential and general-service classes come from ATCO's text joint rate book, checked against Yukon Energy's cross-reference. Yukon Energy's own schedule PDFs are image-only and are never read into live values.

**History:** batch-by-batch history (dates, counts and decisions) is in the History section of
[docs/phase5_completion_matrix.md](docs/phase5_completion_matrix.md) and in git history.
