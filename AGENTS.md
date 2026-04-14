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
| `scrapers/utilities/hydro_quebec.py` | Scrapes Hydro-Québec electricity rates. |
| `scrapers/utilities/toronto_hydro.py` | Scrapes Toronto Hydro electricity rates. |
| `scrapers/utilities/enbridge_gas.py` | Scrapes Enbridge Gas natural gas rates. |
| `scrapers/registry.py` | Reads the list of all utilities and their scraper info. |

### Where the data lives

| File | What it does |
|---|---|
| `data/sources/registry.json` | **The master list.** Every utility the project knows about is listed here, along with the URL where its rates are published and which scraper handles it. |
| `data/inventory/utilities.json` | The full inventory of ALL Canadian utilities — even ones we don't scrape yet. This is the reference list. |
| `data/db/rates.db` | The SQLite database where scraped rates are stored. Created automatically when you first run the scraper. |
| `site/data/rates.json` | The JSON file the website reads. Created by running the export script. |

### Where the website lives

| File | What it does |
|---|---|
| `site/index.html` | The main web page. |
| `site/css/style.css` | How the page looks (colors, layout, fonts). |
| `site/js/app.js` | The code that loads data and makes the filters work. |

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
| `rate_components` | One row per individual charge (energy charge, fixed fee, rider, etc.). This is the most detailed table. |
| `sources` | URLs where rate data was found. |
| `scrape_runs` | A log of each time the scraper ran. |
| `historical_snapshots` | A copy of each tariff's data at each scrape, so we can track changes over time. |
| `missing_data` | A list of known gaps — utilities or rates we don't have yet. |

**The key relationship:** A utility has many tariffs. A tariff has many rate components. This structure lets us capture the full complexity of utility bills instead of flattening everything into one number.

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
| **kWh** | Kilowatt-hour — the standard unit for measuring electricity consumption. |
| **GJ** | Gigajoule — a unit for measuring natural gas energy content. |
| **m³** | Cubic metre — a unit for measuring natural gas volume. |

---

## How to Run Tests

Tests check that the code works correctly. Run them with:

```
pytest
```

If everything passes, you'll see green output. If something fails, it will show you exactly what went wrong and where.

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
