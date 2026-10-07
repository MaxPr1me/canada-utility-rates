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

GitHub Actions schedules a monthly scrape. Deployment and durable history across
cloud runs have new workflows awaiting first CI run verification; see [README.md](README.md).
The latest export has 339 latest live tariffs and 480 estimates; stored history contains
344 live versions and 1,790 snapshots. Registry coverage is not the same as live coverage.
The active campaign covers 16 provincial utilities (230 latest live records) and, from
October 7, the four territorial utilities (108 latest live records). All 20 have live output.
That includes conditional products and reference-only services, not that many
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
| `data/sources/registry.json` | **The master list (system of record).** 84 registered utilities use 32 scraper modules; a 33rd, legacy Toronto module is unregistered. Some scrapers also contain source URL constants that must stay synchronized. |
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
| `site/index.html` | The main web page. **Rate Browser**, **Market Pricing** and the existing two-tariff **Compare** view. The new Across-Canada comparison is planned for Phase 6, not implemented. |
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
can take several minutes. A completed utility may have returned estimates, so check
the `Live-parsed` and `Seed fallback` log messages, not just the success count.

**5. Export data for the website:**
```
python -m pipeline.export_json
```
This creates the JSON files that the website reads.

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

**Known limitations:** these workflow changes, including source-health's Chromium
installation, have not yet been exercised in CI. Verify the first run's database
restore/upload, failure issues and deployment trigger before trusting them. GitHub
Pages must use **GitHub Actions** as its source; `workflow_run` fires from the default
branch. Keep your local database to preserve history; do not delete it when updating a parser.

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

The project models this with a **576-bin hourly pricing surface** stored in `site/data/market_pricing_ontario.json`. Each bin represents a typical $/kWh cost for:
- A specific **month** (1-12)
- A specific **day type** (weekday or weekend)
- A specific **hour** (0-23)

The included generator uses fixed monthly inputs and hourly multipliers; it does
not download five years of observations. Treat the bins as modeled estimates.
The dashboard's historical-data wording is a known issue scheduled for correction.

**How to update it:** Re-running the current generator only rebuilds the same model.
Actual source ingestion and freshness checks are future work, not an existing monthly refresh.

---

## Alberta's Deregulated Market

Alberta is the only province where retail electricity is fully deregulated. This means:

- **Distribution companies** (ATCO Electric, FortisAlberta, EPCOR Distribution, ENMAX Power) own the wires and charge regulated delivery rates.
- **Retail energy** is sold separately from wires service. Existing seeds use legacy RRO terminology; current Rate of Last Resort products and their effective terms need official-source verification.
- The code models these pieces separately. Most Alberta entries still return estimates, not live-extracted rates.

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

There are 994 tests across 8 test modules, including `test_phase5_hardening` for
provenance, storage and history. Normal tests block unmocked network access.
The BC Hydro, FortisBC Electric, Hydro-Quebec, NL Hydro, Manitoba Hydro, NB Power,
Newfoundland Power, Maritime Electric, NSPower, SaskPower, SaskEnergy, Centra Gas,
FortisBC Energy, Energir, Heritage Gas (Eastward), Liberty NB, Yukon Energy, NTPC and
Qulliq fixtures in `tests/fixtures/` hold official
HTML/PDF-text excerpts, source URLs and page/section details for repeatable parser
tests. Batch 10 expands source-derived coverage for eleven utilities including the
territories; a fixture covers only the saved classes and conditions and does not prove
the entire utility catalogue is complete.

If the test run seems to freeze, check the size of `logs/scrape.log`. PDF libraries
can write huge debug logs; `setup_logging()` now keeps them quiet.

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
- The October 1 SaskPower batches parse 41 live tariffs, including completed reference-only classes. Building scope includes standard, bulk-metered and diesel residential service and R23/R24 renewable access. Standard E01/E03 keeps its identity only when both published columns agree; bulk fixed charges are per unit, not per account. Maintain this coverage; the four provincial gas utilities that were seed-only now have live parsers (October 5), so the next work is the recorded catalogue gaps. See [docs/live_parser_gap_report.md](docs/live_parser_gap_report.md).
- Yukon Energy Rate 1160 now lists base rates, R/J/J1 percentage riders, fuel Rider F and dated residential relief separately. Do not add riders to a price that already includes them. Its old version remains in history; the browser keeps the latest version. Since October 7 the other residential and general-service classes come from ATCO's text joint rate book, checked against Yukon Energy's cross-reference; Yukon Energy's own schedule PDFs are still image-only.
- NSPower residential service includes standard, storage-heating TOD and closed-enrollment TOU/critical-peak pilots. Pilot records explicitly distinguish the tariff's conditional interim phase from its dated November pricing. Do not assume an existing customer's system-restoration status from an advertising page. Mandatory FAM/DSM/storm riders are separate from base energy; Green Power blocks are opt-in, not a standard charge. Dates past the supported tariff/rider year fail closed.
- Hydro-Quebec DP, grandfathered DM and northern off-grid DN are now parsed alongside D/G/M. DP has summer/winter demand charges; DM/DN charges and energy allowances depend on the approved multiplier. DN applies north of the 53rd parallel except Schefferville and normally uses multiplier one; its older DM-eligibility exception is not a restriction on every DN customer. Conditional supply-voltage credits do not apply to everyone. Minimum bills, demand allowances and transformation-loss rules remain conditions, not extra charges or calculated totals. Missing continuation pages reject only the affected class. The remaining domestic catalogue is still incomplete.
- Completing a utility means auditing its building-relevant standard published classes, not just replacing existing seed values or completing every unrelated service. A complete class can stay live when another class fails, but never stamp a mixed live/seed list as entirely live.
- The current campaign covers the 16 registered provincial utilities outside Ontario and Alberta plus, from October 7, the four territorial utilities. Parallel workers own separate utility files; database/export/registry/test integration and publication are serial. Preserve excluded regions and all earlier snapshots.
- Batch 10 is stored and exported: 994 passing tests, 1,790 snapshots (220 new, prior snapshots unchanged), 824 versions / 5,286 components / 344 stored live / 480 seed; 339 latest live across 21 utilities. DB validation: 0 errors and 2 existing AESO warnings.
- Batch 10 added NSPower industrial rates, FortisBC Energy Rate 7 and transportation rates, SaskEnergy Small Industrial, BC Hydro transmission pilots and generation credits, Hydro-Quebec DR Commitment, Manitoba LUBD and live territorial rates (NTPC, Qulliq, Yukon Energy, ATCO Electric Yukon). Territorial government subsidies are kept separate and conditional; never fold them into base prices. Qulliq's rates are interim until a final decision is published.
- Decisions (October 7): BC Hydro RS1828 and Hydro-Quebec F/FP are excluded. Market-indexed prices (FortisBC RS38, BC Hydro RS1892, NSPower real-time pricing) wait for the Alberta/Ontario market-rate work.
- Batch 9 (historical) stored and exported: 801 passing tests, 1,570 snapshots (106 new, prior snapshots unchanged), 694 versions / 4,453 components / 214 stored live / 480 seed; 209 latest live across 18 utilities, 207 at all 16 campaign utilities. Source-check dates, live-record counts and catalogue completion are different facts. Follow the current [coverage matrix](docs/phase5_completion_matrix.md) and [parser gap report](docs/live_parser_gap_report.md).
- Batch 9 added NL Hydro Island/Labrador Industrial Firm and conditional net metering; Energir D5 and optional replacement RNG supply; Newfoundland Power Curtailable Option 1 and domestic net metering; NB Power Large Industrial; BC Hydro RS1830 and closed RS1289; FortisBC Electric RS31/33; Hydro-Quebec L/LG/H and business Demand Response Leeway. Manitoba Hydro isolates residential/commercial page failures without adding records. Source-blocked and conditional prices are not universal charges.
- FortisBC Energy Rates 1-3 have per-day basic charges; Rates 4/5 and Revelstoke propane are also parsed. Energir and Eastward follow the current document link and fail closed on edition/month mismatch. Energir's load balancing and renewable-gas charges are conditional; Eastward's municipal riders have a limited charge base; Liberty's MGS/LGS customer charges are alternatives.
- Gas batch 4: FortisBC Energy now also parses Rate 5 (written contract, about 5,000 GJ+/yr) and seasonal Rate 4 (April 1-November 1) from their approved schedules; the Rate 5 basic charge is **monthly** as printed in the tariff, even though the business page says daily, so Rate 5 is not interchangeable with the daily Rates 1-3. Fort Nelson Rates 4/5 have no published price table (gap). Energir D3/D4 share one schedule: minimum daily obligation bands are per m³/day of **subscribed volume**, and above-subscribed-volume withdrawal and average load-balancing prices are conditional. Eastward Rate Class 3's demand charge is per GJ of Billing Demand per month (greater of 225 GJ, contract demand or maximum 24-hour use), a unit taken from the approved tariff PDF rather than the rate table; Rate Class 4 is negotiated per site and not published, so it is an exclusion, not a parser gap. Liberty's Off-Peak Service is April-November eligibility only, with the December-March overrun as a note.
- Hydro-Quebec DT uses temperature switching, not clock-based TOU. Flex D uses notified events; Winter Credit is a closed, conditional adjustment to Rate D and retains the published reference-energy rules. NL Hydro's phase/amperage fixed charges are alternatives, not cumulative charges; seasonal options require their matching base schedules. SaskEnergy delivery-only service excludes private commodity prices. A missing carbon source cannot be hidden under a live label; assembled tariff dates reflect the latest required component while component dates remain intact.
- FortisBC Electric's current residential price is flat; its older tiered version remains history. Rate 21's kW/kVA charges are alternatives, and voltage/transformation discounts are conditional negative credits. NSPower MURB has its own rider rows and minimum-bill condition; the approved book explicitly applies its peak price on weekends/holidays. Solar Garden and Community Solar records are subscriber adjustments to another tariff, not replacement household energy prices. Centra keeps published delivery/demand parts separate, with no guessed heat conversion or private marketer commodity price.
- Batch 8: BC Hydro's power-factor surcharge is a conditional percentage of the business rate charges for poor (lagging) power factor; it is not an extra charge for every customer. Centra classes now need the approved PUB schedule's volume, contract and billing-demand conditions. FortisBC Revelstoke business rates are live only when the approved tariff index says each class is offered in Revelstoke. Energir inventory adjustments depend on each customer's storage use and have no published price, so they are explained, never given a number.
