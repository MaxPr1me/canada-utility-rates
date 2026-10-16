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

GitHub Actions (GitHub's cloud computers) runs a monthly scrape on the 1st, a "source
health" test scrape, which publishes nothing, on the 15th, and an Ontario Price archive and
market history update on the 1st and 15th. Since October 16 the monthly scrape is the **only**
thing that saves new data into the project's database; computers like yours keep a read-only
copy. On October 15 a hand-started source health run passed and posted a public note with its
totals: 909 live and 46 estimated records, no failures, and AESO the only utility with estimates
only. The one missing live record (an EPCOR Energy Alberta page that had moved) was fixed on
October 16. The new monthly-scrape steps (getting the database from GitHub, checking it, saving
it with a dated backup, opening an issue when something fails, and publishing the website
afterwards) have not run on GitHub yet. The project owner may start the monthly scrape by hand;
otherwise it first runs on November 1. See "How the Monthly Updates Work" below and
[README.md](README.md).
The latest export (October 9, batch 12) has 910 latest live tariffs and 480 estimates; stored
history contains 916 live versions and 3,616 snapshots. No scrape was stored on October 15 or 16,
so these counts did not change. Registry coverage is not the same as
live coverage. The active campaign covers 16 provincial utilities (243 latest live records) and,
from October 7, the four territorial utilities (109 latest live records). All 20 have live output.
All 47 active Ontario distributors are live (490 records); PUC Distribution was added on
October 9 even though its tariff prints no connection rate. Batch 12 also added Alberta
electricity (28 records: four wires companies and three Rate of Last Resort providers) and
Ontario/Alberta gas (40 records: Enbridge Gas, ATCO Gas and EPCOR Natural Gas (Ontario)).
Only AESO, a market reference, has no live output.
Since October 16 the export writes electricity "representative models" (typical monthly costs;
see the glossary) for all ten provinces, and the website's Representative Models page shows them
(Ontario's since October 15). Also since October 16 the website's Market Pricing page shows the
real Ontario market prices of the latest five years (60 months): the old HOEP price until April
2025 and the new Ontario Price after it (see "Ontario Market Pricing" below).
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
| `scrapers/utilities/epcor_energy_alberta.py` | EPCOR Energy Alberta Rate of Last Resort price and administration charge (EPCOR Distribution and FortisAlberta areas). EPCOR moved these pages; the new addresses went into the registry and this file on October 16. |
| `scrapers/utils/alberta_rolr.py` | Shared Rate of Last Resort helper: checks each provider's price against the Utilities Consumer Advocate table and stops treating it as live once the fixed term ends. |
| `scrapers/utilities/aeso.py` | AESO market reference price (Alberta wholesale); still an estimate until the Alberta market work (Phase 6C). |
| `scrapers/utilities/nl_hydro.py` | NL Hydro electricity rates (Newfoundland — residential + commercial). |
| `scrapers/registry.py` | Reads the list of all utilities and their scraper info. |
| `scrapers/utils/parsing.py` | HTML/PDF parsing helpers, including PDF URL resolution and strict `verify_tariff_values()` checks that prove fallback values still appear in an official schedule. |
| `scrapers/utils/change_detection.py` | Compares live-parsed rates against seed data. Flags changes by severity (info/warning/critical). If critical drift is detected, the scraper rejects live data and falls back to seed. |
| `scrapers/utils/market_pricing.py` | Reads the Ontario market history file (since October 16 the rolling five years; the older 2020-2024 file is still accepted) and works out the illustrative market price for the models (see "Illustrative estimate" in the glossary). It refuses a file that was not built from real observed prices. |
| `scrapers/utils/validation.py` | Data quality checks run after every scrape. |

### Where the data lives

| File | What it does |
|---|---|
| `data/sources/registry.json` | **The master list (system of record).** 87 registered utilities use 33 scraper modules; a 34th, legacy Toronto module is unregistered. Eight absorbed Ontario distributors have `status: "merged"` and a `merged_into` successor; the mistaken Alberta "EPCOR Natural Gas" entry has `status: "retired"`. Monthly runs skip both kinds but keep their history. Some scrapers also contain source URL constants that must stay synchronized. |
| `data/inventory/utilities.json` | The full inventory of ALL Canadian utilities — even ones we don't scrape yet. This is the reference list. |
| `data/db/rates.db` | The SQLite database where scraped rates are stored. Since October 16 only the Monthly Scrape on GitHub writes it; the real copy lives in the `data-history` release on GitHub, next to dated backups. Your copy is read-only: get it with `python scripts/pull_history_db.py` (older copies move to `data/db/backups/`). |
| `data/excel/old_urls.xlsm` | **Audit reference only.** An Excel file with historical URLs and rate data. NO scraper reads this file. It is git-ignored. |
| `site/data/rates.json` | The JSON file the website reads. Created by running the export script. |
| `site/data/market_pricing_ontario.json` | What the Market Pricing page reads: the latest 60 complete months (energy, Class B Global Adjustment and their total) and 576 heatmap averages built only from real observed hours. Rebuilt twice a month by `scripts/build_ontario_market.py` (see "Ontario Market Pricing" below). |
| `data/market/ontario_market_monthly.csv` | The permanent monthly market history since January 2020 (80 months on October 16): energy, Class B Global Adjustment and total for each month. It is never shortened. |
| `data/market/hoep_hourly.csv` | The old hourly HOEP prices, January 2020-March 2025, saved once so GitHub never has to download them again. |
| `data/market/ontario_price_hourly.csv` | The project's own permanent hourly archive of the Ontario Price since July 11, 2026, extended by `scripts/archive_ontario_price.py` (see "Ontario Market Pricing" below). |
| `site/data/market_structure_notes.json` | Research notes on market structure for every Canadian province/territory. |
| `site/data/missing_classes_report.json` | Audit report showing which utilities are missing customer classes. |
| `site/data/source_review_report.json` | Source URL audit — compares Excel reference URLs against registry. |

### Where the representative models live

A *representative model* is a "typical" monthly cost for a province, worked out from the middle
value (the median) of its utilities' live rates. Since October 16 all ten provinces have
electricity models (gas and the territories come later); the website's Representative Models page
shows them.

| File | What it does |
|---|---|
| `data/models/crosswalk.json` | The sorting list. Its 240 rules are read from top to bottom, and the first rule that fits decides where each live tariff goes: into a model group (province, fuel, customer type, rate structure and size) or out, with a written reason. Today 557 of the 910 live tariffs are used and 353 are left out on purpose; none is left unsorted. It also lists the four Alberta "pairs" (a wires company plus the Rate of Last Resort provider for its area, counted as one) and the "required contributors": a model level is not shown when a utility it needs cannot be calculated (Newfoundland and Labrador homes need Newfoundland Power). Ontario and Alberta gas wait for Phase 7D, and the territories come later. |
| `data/models/usage_levels.json` | The example customers, approved by the project owner: homes using 500, 1,000 or 2,000 kWh a month; small businesses (under 50 kW) using 2,000 kWh at 10 kW or 8,000 kWh at 25 kW; medium businesses (50-499 kW) using 40,000 kWh at 100 kW; large businesses (500-4,999 kW) using 500,000 kWh at 1,000 kW. It also holds the Ontario Energy Board's split of use between time-of-use periods, a short, reviewed list of "conditional" Ontario charges that a typical customer does pay, and the made-up (synthetic) business load profile used only for the illustrative estimate (see the glossary). |
| `data/models/block_periods.json` | Some tariffs print an energy block such as "first 5,000 kWh" without saying whether that is per month or per two months. Each of its 20 entries, reviewed with the project owner on October 16, quotes the tariff and says which period applies. When a tariff never says (NB Power GS1, Maritime Electric), that utility is left out of the model instead of guessed. |
| `data/models/taxes.json` | Sales taxes (GST, HST, PST, QST, RST) and automatic bill rebates, such as the Ontario Electricity Rebate, for every province and territory: electricity and gas, homes and businesses. Municipal taxes and income-tested programs are left out. |
| `pipeline/representative_models.py` | The calculator. For every utility it works out the monthly cost at each example level, then reports the median, the spread, the real utility closest to the median and any utility far from it (an "outlier"), without and with tax, plus a written explanation of how each number was made. Since October 16 it covers all ten provinces, treats each Alberta pair as one utility, and adds the clearly labelled illustrative estimate for Ontario's two larger business sizes. |
| `site/data/representative_models.json` | The results. The export step rewrites this file every time; if the calculation fails, the export still finishes and the previous file is kept. The website's Representative Models page reads it. These are comparison aids, never rates anyone is billed. |

### Where the website lives

| File | What it does |
|---|---|
| `site/index.html` | The main web page. **Rate Browser**, **Market Pricing**, **Representative Models** and the existing two-tariff **Compare** view. The new Across-Canada comparison is planned for Phase 9, not implemented. |
| `site/css/style.css` | How the page looks — includes styles for multi-select filters, heatmap, confidence indicators, source attribution, and market callouts. |
| `site/js/app.js` | The application logic: loads 5 JSON data files, deduplicates rates by effective_date, manages multi-select checkbox filter state (using JavaScript `Set`s), cascades province selection into the utility filter, renders rate cards with confidence dots, shows detail modals with source attribution and market callouts, and powers the Market Pricing page (headline, monthly chart, 60-month table, heatmap with hour counts, method). |
| `site/js/models.js` | The Representative Models page. It reads `representative_models.json` the first time the page is opened and offers four drop-down lists (province, fuel, sector, rate structure). It shows a table of typical monthly costs without and with tax, then the taxes, the method and the contributing utilities. A checkbox, off by default, shows the illustrative estimate (synthetic load profile) with a warning and a SYNTHETIC badge. If the file is missing or broken, it shows a "not available" notice and the other pages keep working. |
| `site/css/models.css` | How the Representative Models page looks, including the warning style of the illustrative estimate. |

### Where the automation lives

| File | What it does |
|---|---|
| `.github/workflows/scrape.yml` | Monthly tests, scrape, validation and export on the 1st. Since October 16 the only writer of the database: it gets the database from the `data-history` release, checks it, and saves it back with a dated backup. |
| `.github/workflows/deploy.yml` | Separate GitHub Pages deployment on push or manual dispatch. |
| `.github/workflows/source-health.yml` | Non-blocking dry run on the 15th; uploads logs without publishing. |
| `.github/workflows/ontario-price-archive.yml` | At 06:00 UTC on the 1st and 15th: saves the Ontario Price archive first, then rebuilds and saves the Ontario market history (Market Pricing page) in a second save; opens an issue if a check fails. |
| `scripts/check_db_history.py` | The Monthly Scrape's safety check: the database is not damaged, and nothing old was lost or changed. |
| `scripts/pull_history_db.py` | Downloads the newest database from GitHub to your computer, checks it, and keeps your old copy. It never uploads anything. |
| `scripts/build_ontario_market.py` | Builds the five-year Market Pricing history (runs inside the Ontario Price Archive workflow). |

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

**3. Get a copy of the project's database:**
```
python scripts/pull_history_db.py
```
This downloads the project's database (`data/db/rates.db`) from GitHub, checks that the download
is complete and unchanged, and moves any older copy on your computer to `data/db/backups/`. Since
October 16 only the Monthly Scrape on GitHub saves new data; your copy is for reading. Run this
again whenever you want the newest data. (For an empty practice database instead, run
`python -m pipeline.run_scrape --init-db`.)

**4. Try the scraper (nothing is saved):**
```
python -m pipeline.run_scrape --dry-run
```
This visits utility websites and reads the rate information, but saves nothing. A full run
can take several minutes. A completed utility may have returned estimates, so read
the end-of-run box: it shows how many records were live and how many were estimates,
and lists any utility that returned only estimates ("Seed-only utilities"). To save new data,
see "How the Monthly Updates Work" below: push the work to GitHub and let the Monthly Scrape
store it.

**5. Export data for the website:**
```
python -m pipeline.export_json
```
This creates the JSON files that the website reads, including the representative models file
shown on the Representative Models page.

**6. Open the website:**
Run `python -m http.server --directory site 8000`, then open http://localhost:8000.
The browser needs HTTP access to fetch the JSON files; double-clicking the HTML
is not a reliable way to load them.

---

## How to Scrape Just One Utility

To test one utility's scraper on your computer (nothing is saved):
```
python -m pipeline.run_scrape --utility "BC Hydro" --dry-run
```

To test all utilities in a province (merged and retired entries are skipped):
```
python -m pipeline.run_scrape --province ON --dry-run
```

To **save** new data for one utility or one province, push your work to GitHub, then start the
**Monthly Scrape** by hand (see below) and type the utility name in the `utility` box or the
two-letter province code in the `province` box (not both). Do not save scrapes into your own copy
of the database, and never upload a database by hand.

---

## How the Monthly Updates Work

The file `.github/workflows/scrape.yml` tells GitHub Actions to:

1. **On the 1st of every month** (or when started by hand), start a computer in the cloud.
2. Install Python, the project tools and Playwright Chromium.
3. **Get the database** from the `data-history` GitHub Release. If the release exists, the
   download must work and its fingerprint (SHA-256) must match the one GitHub shows; otherwise
   the run stops. Only when there is no release at all does it start a new, empty database.
   (Before October 16 a failed download quietly started an empty database, which could then
   have replaced the real history.)
4. Run the tests, then `python -m pipeline.run_scrape` (all utilities, or the one utility or
   province typed in when it was started by hand).
5. Run `python -m pipeline.validate` to check data quality.
6. Run `python -m pipeline.export_json` to update the website data.
7. **Check the database** with `scripts/check_db_history.py`: it must not be damaged, it must
   have at least as many snapshots, tariff versions and scrape runs as before, and every older
   snapshot must be unchanged. A public "Database history" note on the run page gives the result.
8. Only then **save the database** back to the release, together with a dated backup copy
   (`rates-YYYY-MM-DD.db.gz`; the newest 12 are kept), and save the updated site data to the
   repository (first catching up with any archive update saved the same day).
9. Leave deployment to the separate **Deploy Site** workflow, which starts by itself after a
   successful **Monthly Scrape** run and checks out `main`.
10. If any step fails, create a GitHub Issue; a failed check saves nothing to the release.

**The rule since October 16 (user decision): only this workflow saves new data.** Your computer
keeps a read-only copy (`python scripts/pull_history_db.py`). To store new data, push the code
and start Monthly Scrape (for everything, one utility or one province), or wait for the 1st.
Never upload a database by hand. **Careful:** deleting the `data-history` release on GitHub
deletes the database and all its backups.

**Known limitations:** only part of this has run on GitHub so far. **Deploy Site** has published
the website after every push, and on October 15 a hand-started **Source Health** run (run #6)
passed. Every scrape run posts a short public note on its GitHub run page with its totals (live,
estimated and invalid records, and any utility that failed or returned only estimates); the full
log still needs a GitHub sign-in. A failing command stops its step instead of being hidden by the
copy written to the log. Never run yet: the new database steps (3, 7 and 8; the project owner
created the release from the local database on October 15), the automatic failure issues (step
10), Deploy Site starting by itself (step 9) and the Ontario Price Archive with its market history
build. The first scheduled Monthly Scrape is November 1; the project owner may start one by hand
earlier (see below). Check that first run before trusting those steps. GitHub Pages must use
**GitHub Actions** as its source; the automatic trigger (`workflow_run`) only fires from the
default branch.

**To run it early (not waiting for the 1st of the month):**
1. Go to the repository on GitHub.
2. Click the **"Actions"** tab.
3. Click **"Monthly Scrape"** on the left.
4. Click the **"Run workflow"** button on the right. You may type one utility name or one
   two-letter province code (not both); leave both empty for everything.

The **Ontario Price Archive** workflow can be started the same way. This computer has no GitHub
command-line tool, so start workflows from the website.

After a successful data update, **Deploy Site** can still be run manually if the
automatic handoff has not yet been verified.

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

Example (October 15-16): EPCOR Energy Alberta moved its Rate of Last Resort pages, and the page
for homes in the FortisAlberta area answered "not found" (404). The scraper skipped that one
record instead of guessing, so its October 9 version stayed the latest stored. On October 16 the
new addresses went into the registry, the scraper and its test file, and a test run gave all 4
records live again; the next Monthly Scrape saves them.

### The monthly automation fails

**What happened:** The GitHub Actions workflow encountered an error.

**What to do:**
1. Go to the **Actions** tab on GitHub.
2. Click on the failed run to see the error log. Every scrape run also shows a short public note
   with its totals; a utility named there as failed or estimates-only is the one to check.
3. Common causes:
   - A utility website was down during the scrape.
   - A dependency (Python library) had a breaking update.
   - GitHub Actions had a temporary problem.
4. You can re-run the workflow by clicking **"Re-run all jobs"**.

### The Ontario Price Archive opened an issue

**What happened:** a month in the archive did not match the IESO's own monthly Ontario Price
table, or an official IESO file could not be read. Nothing was written, so the archive is safe.

**What to do (soon):** the IESO deletes each daily price file after about 90 days, so a problem
left too long loses hours for good.
1. Run `python scripts/archive_ontario_price.py --dry-run` on your computer; it names the month or
   file that failed and writes nothing.
2. If the IESO changed its table or files, the script needs updating; if its website was down,
   start the workflow again later.

### The database history check failed

**What happened:** the Monthly Scrape found a problem with the database and saved nothing, so the
copy on GitHub is unchanged. Possible reasons: the download from the release did not match its
fingerprint, the database is damaged, it has fewer snapshots, tariff versions or scrape runs
than before, or an older snapshot changed.

**What to do:**
1. Open the issue and read its "Database History" part (or the "Database history" note on the
   run page).
2. **Do not upload a database by hand**, and do not delete the `data-history` release (that would
   delete the database and all its backups).
3. Fix the cause (or ask for help), then start Monthly Scrape again. The dated backups
   (`rates-YYYY-MM-DD.db.gz`) of earlier good runs stay in the release.

### The Ontario market history update failed

**What happened:** the Ontario Price Archive workflow opened an issue titled "Ontario market
history update failed". The archive itself was saved; only the Market Pricing history was not
rebuilt, so the website keeps the previous version. The build writes nothing when a number
disagrees with the IESO's own tables or a file cannot be read.

**What to do:**
1. Run `python scripts/build_ontario_market.py --dry-run` on your computer; it names the month or
   file that failed and writes nothing.
2. If the IESO changed a table or file, the script needs updating; if its website was down,
   start the workflow again later.

### The website shows no data

**What happened:** The JSON data files are missing or empty.

**What to do:**
1. Make sure you have the database: `python scripts/pull_history_db.py`
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

**Where the real database lives:** on GitHub, as the file `rates.db` in the `data-history`
release, next to up to 12 dated backups. Only the Monthly Scrape writes it (since October 16);
your computer keeps a read-only copy (see "How the Monthly Updates Work").

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

The website's **Market Pricing** page shows what this market really cost over the **latest five
years** (since October 16): **real (observed) prices**, not estimates. In plain words:

- The **HOEP** was Ontario's wholesale electricity price, set every hour, until April 30, 2025.
  Since May 1, 2025 the hourly price is the **Ontario Price**.
- The **Global Adjustment (GA)** is charged per kWh and changes once a month. "Class B" is the
  version most customers pay; the page uses its actual monthly rates.
- A large customer buying at market prices pays roughly the energy price + GA for each kWh (the
  "full cost").

The page uses a **rolling window** (see the glossary): the latest 60 complete months. On October 16
that is September 2021 to August 2026: 44 months of the HOEP and 16 of the Ontario Price
(September 2026 is not in the IESO's monthly table yet). On average the full cost was 10.40
cents/kWh (energy 4.49 + GA 5.92): 10.13 in the HOEP months and 11.16 in the Ontario Price
months. The page shows that average, a monthly chart of energy, GA and total with May 2025
marked, a table of all 60 months (which market each month used and where its numbers came from),
a heatmap and an explanation of the method.

A month counts as **complete** only when it is over, its energy price matches the IESO's own
published monthly value, and its Class B GA rate is published. April 2025 uses the IESO's monthly
report value only, because the IESO's hourly file for that month does not add up to the report.

**The heatmap** shows averages for each month, weekday or weekend, and hour (576 boxes; a
statutory holiday counts as the weekday it falls on; hours are Eastern Standard Time). It uses
**only hours with a real recorded price**: 32,640 of the window's 43,824 hours (31,392 HOEP hours
and 1,248 Ontario Price hours). Each box shows how many hours it averages (63-89 for weekdays,
25-37 for weekends). The hourly Ontario Price from May 1, 2025 to July 10, 2026 can no longer be
downloaded (the IESO deletes its daily files after about 90 days), so that gap is explained on
the page and never filled with made-up hours. As the archive grows, more Ontario Price hours
enter the heatmap.

**Where the numbers live:**
- `data/market/ontario_market_monthly.csv`: one line per month since January 2020 (80 months on
  October 16). It is never shortened; a month can only be corrected within 6 months of its end.
- `data/market/hoep_hourly.csv`: the old hourly HOEP prices (January 2020-March 2025), saved once
  so GitHub never has to download them again.
- `data/market/ontario_price_hourly.csv`: the project's own hourly Ontario Price archive (below).
- `site/data/market_pricing_ontario.json`: what the website reads (the 60 months and the heatmap).

**How it is updated:** automatically. The **Ontario Price Archive** workflow (1st and 15th, 06:00
UTC) first saves the archive, then runs `python scripts/build_ontario_market.py`. That script
downloads only the IESO's monthly price table and Global Adjustment files (18 files), checks every
number, and only then rewrites the files. If anything is missing or a check fails, it writes
nothing and GitHub opens an issue (see "What to Do When Something Breaks"). You can run the same
command on your computer; add `--dry-run` to check everything without writing. These averages
are never copied into a tariff: large customers' tariffs keep their "Variable" line.

The older 2020-2024 version of the page (from October 9) can still be rebuilt with
`python scripts/generate_market_pricing.py`, but the website no longer shows it. Always give it
`--output` with another file name: by default it would overwrite the website's five-year file.
Two GA details
apply to both versions: April-June 2020 use the lower, capped GA (115 $/MWh) that the IESO
published under a provincial emergency order, and the 2021 rates leave out a separate recovery
charge billed that year to Class B customers who were not on the Regulated Price Plan. These
choices, and counting holidays as weekdays, are defaults the project owner can change. If the
file was not built from real prices, the website hides the dashboard and shows a "not available"
notice instead.

**The Ontario Price archive (since October 15):** `scripts/archive_ontario_price.py` saves every
hour of the Ontario Price that the IESO still publishes into `data/market/ontario_price_hourly.csv`,
starting July 11, 2026 (earlier hours are no longer online, and the IESO website's own chart data
reaches back only about 10 days). Each row holds the date, the hour, the day-ahead price
(DA-OZP), the small adjustment (LFDA, see the glossary), their sum (the Ontario Price) and whether
the LFDA is final. The **Ontario Price Archive** workflow runs it on the 1st and 15th of each
month and saves the file; the market history build above then uses it. Before writing, every
complete month must match the IESO's own monthly
table to the cent for all three numbers; if anything disagrees, nothing is written and GitHub
opens an issue. Fix such an issue quickly: the IESO deletes each daily file after about 90 days.
An hour without a published LFDA stays blank; it is never treated as zero.

**Did the new market change what customers pay?** For a large customer who pays the market
price plus the Class B GA, hardly. From 2020 to 2024 the two together averaged 10.6 cents/kWh;
the first 12 months of the Ontario Price averaged 10.8 and the latest 12 months 11.1, and most
months fell inside the range seen in the same month in 2020-2024. The energy price alone is much
higher now (about 7.0 cents/kWh against 2.9), but the GA fell by almost as much, because the GA
pays generators the difference between their contracts and what the market pays them. That is
why, since October 16, the Market Pricing page shows the old and new markets as one continuous
total.

---

## Alberta's Deregulated Market

Alberta is the only province where retail electricity is fully deregulated. This means:

- **Distribution companies** (ATCO Electric, FortisAlberta, EPCOR Distribution, ENMAX Power) own the wires and charge regulated delivery rates. Since October 9 their main home and business rates are read live from their approved schedules. Delivery is split into **distribution** and **transmission** lines, and temporary riders are listed separately with their own dates.
- **EPCOR Distribution's 2026 rates are interim** (approved only temporarily), so they are shown at medium confidence with a note.
- **Retail energy** is sold separately from wires service. Customers without a retail contract pay the **Rate of Last Resort** (RoLR), which replaced the Regulated Rate Option (RRO) on January 1, 2025. Its price is fixed until December 31, 2026: 12.02 cents/kWh from Direct Energy Regulated Services (ATCO Electric area), 12.06 from ENMAX Energy (Calgary) and 12.01 from EPCOR Energy Alberta (Edmonton and FortisAlberta areas). Each price must match the Government of Alberta's Utilities Consumer Advocate table. After December 31, 2026 these records stop counting as live until the next price is published. Old RRO estimates stay in history.
- **AESO** (the wholesale market) is still only a reference estimate; Alberta market prices are future work (Phase 6C).
- The code models these pieces separately and never adds them into one price.
- Only the representative models (since October 16) put a wires company and the Rate of Last
  Resort provider for its area together, as one "pair", to show a typical monthly cost; each
  charge keeps its own source. The Rate of Last Resort is only for sites using less than 250,000
  kWh a year, so the larger business models show wires charges with energy "pending" until the
  Alberta market work (Phase 6C).

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
| **Representative model** | A "typical" monthly cost for a province (Phase 7), built from the median of its utilities' live tariffs at set example usage levels, shown without and with tax, with a note explaining exactly how it was made. Built for Ontario electricity since October 9 and for all ten provinces since October 16 (`site/data/representative_models.json`), and shown on the website's Representative Models page. In Alberta, one "utility" in a model is a pair: a wires company plus the Rate of Last Resort provider for its area. Gas and the territories come later. It is a comparison aid, never a rate anyone is billed, and it never counts as live coverage. |
| **Synthetic load profile** | A made-up pattern of when a business uses electricity, not taken from any real customer. The project's one (approved by the project owner on October 16) assumes a business uses its full power on weekdays from 7 a.m. to 7 p.m. (Eastern Standard Time) and a smaller, steady amount at all other hours. It is used only for the illustrative estimate. |
| **Illustrative estimate** | A number shown only to give a rough idea, not to be relied on. The Representative Models page has one for Ontario's two larger business sizes: their delivery charges plus market energy priced with the synthetic load profile (about 10.6-10.8 cents/kWh). It stays hidden until you tick "Show illustrative all-in estimate (synthetic load profile)", carries a warning and a SYNTHETIC badge, and is never used in medians, comparisons or change checks. It is representative only: not a forecast, a quote or a bill, and it needs further analysis. |
| **Rolling window** | A period that moves forward as time passes. The Market Pricing page always shows the latest 60 complete months; when a new month is complete, the oldest one leaves the page (it stays in the monthly history file). |
| **Release (`data-history`)** | A storage place on GitHub for files that belong to the project but are too big to keep with the code. The project's database (`rates.db`) and its dated backups live in the `data-history` release. Deleting the release deletes them all. |
| **Median** | The middle value when numbers are sorted from lowest to highest. Unlike an average, one unusually high or low utility barely moves it. |
| **Outlier** | In a representative model, a utility whose cost is far from the median (more than 30% away, or well outside the range of the middle half of the utilities). It is named with how far away it is; it is not left out. |
| **LDC** | Local Distribution Company — the utility that delivers electricity to your home (common in Ontario). |
| **OEB** | Ontario Energy Board — the regulator that sets many Ontario utility rates. |
| **QRAM** | Quarterly Rate Adjustment Mechanism — the Ontario Energy Board process that resets Ontario natural gas supply prices every three months. |
| **IESO** | Independent Electricity System Operator — operates Ontario's wholesale electricity market. |
| **HOEP** | Hourly Ontario Energy Price — Ontario's former real-time wholesale electricity price. **Retired April 30, 2025** and replaced by the Ontario Price (OEMP). The Market Pricing page shows its real prices up to April 2025 as part of the rolling five-year history. |
| **Ontario Price (OEMP)** | Ontario Electricity Market Price — Ontario's hourly wholesale electricity price since May 1, 2025: the Day-Ahead Ontario Zonal Price plus a Load Forecast Deviation Adjustment. Large customers who are not on the Regulated Price Plan pay it plus the Global Adjustment. |
| **DA-OZP** | Day-Ahead Ontario Zonal Price — the hourly price for the Ontario zone set a day ahead in the IESO market; the main part of the Ontario Price. The IESO keeps only about 90 days of the hourly files online. |
| **LFDA** | Load Forecast Deviation Adjustment — a small hourly adjustment added to the DA-OZP to make the Ontario Price. The IESO publishes it first as preliminary, then as final; some hours have none. |
| **Variable (market) charge** | A charge that follows a market price that changes over time (for example the Ontario Price). It is stored with a link to the market but no number, and the website shows "Variable". |
| **GA** | Global Adjustment — monthly charge in Ontario covering contracted/regulated generation costs. The Market Pricing page shows the actual monthly Class B rates for the latest 60 months. |
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

There are 1,863 tests across 14 test modules, including `test_phase5_hardening` for
provenance, storage and history, `test_ontario_price_archive` for the Ontario Price archive,
`test_market_rolling` and `test_market_site` for the five-year market history and its page,
`test_ci_history` for the database safety check and download script, `test_models_7c` for the
all-province models and the illustrative estimate, and `test_site_models` for the
Representative Models page. Normal tests block unmocked network access.
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
exported records (`rm_records_sample.json`, `rm_engine_sample.json`, `rm_records_b12.json` and
`rm_records_b14.json`), so the tests that run before each monthly scrape never depend on that
month's data. The Ontario market history tests use `ieso_market.json` and
`ieso_market_rolling.json` and the archive tests `ieso_ontario_price.json`,
small saved excerpts of the official IESO files, so they never download anything.

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
- Since October 16 only the Monthly Scrape on GitHub stores scrapes. Computers run tests and dry runs and keep a read-only copy of the database; nobody uploads a database by hand.
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
