# AGENTS.md — Plain-Language Guide for Maintaining This Project

**This guide is for someone with zero coding experience.** It explains what this project does,
the rules that protect its data, how to keep it running and what to do when something breaks;
AI assistants read it before every task.

---

## Required reading and maintenance

Before making task decisions or changes, read this file and
[.github/copilot-instructions.md](.github/copilot-instructions.md). Both apply: this file owns the
project safeguards and the plain-language guide; the Copilot instructions own the development
workflow (asking questions, exploring the code, checking changes, comments, commits and teamwork).

Also read the area file for what you are changing. VS Code loads these files automatically when
matching files are edited, but other tools may not, so open them yourself:

| Area | File | What it covers |
|---|---|---|
| Scrapers | [scrapers.instructions.md](.github/instructions/scrapers.instructions.md) | All scrapers, the utility registry and inventory, test fixtures |
| Ontario electricity | [ontario-electricity.instructions.md](.github/instructions/ontario-electricity.instructions.md) | Ontario distributors and OEB tariff sheets |
| Alberta electricity | [alberta-electricity.instructions.md](.github/instructions/alberta-electricity.instructions.md) | Alberta wires companies, the Rate of Last Resort, AESO |
| Other provinces and territories | [regional-utilities.instructions.md](.github/instructions/regional-utilities.instructions.md) | Electricity in the other provinces and the territories |
| Natural gas | [gas-utilities.instructions.md](.github/instructions/gas-utilities.instructions.md) | Natural gas utilities |
| Market data | [market-data.instructions.md](.github/instructions/market-data.instructions.md) | Ontario and Alberta market history, the Ontario Price archive, raw IESO reports, combined totals |
| Representative models | [representative-models.instructions.md](.github/instructions/representative-models.instructions.md) | Representative models and the Across-Canada comparison |
| Automation and data history | [ci-data-history.instructions.md](.github/instructions/ci-data-history.instructions.md) | GitHub Actions, the database history, the coverage gate, the pipeline |
| Website | [website.instructions.md](.github/instructions/website.instructions.md) | The website (`site/`) |
| graphify | [graphify.instructions.md](.github/instructions/graphify.instructions.md) | graphify and the commit hook |

- If a file is unavailable, report it rather than assume what it says.
- If requirements conflict, report the conflict and resolve it before doing the affected work.
- At completion, check whether the changed behaviour requires documentation updates (see
  "Documentation Review Rule") and make them in the same change. Keep each rule in one place and
  link to it instead of copying it.
- If instructions change during a task, re-read them before continuing.

---

## Project safeguards

These rules apply to every change. They matter more than any single feature.

1. **Never show "default" numbers as if they were real.** Some rates in the code are *seed
   values* — hand-entered fallback numbers used only when the live official website can't be
   read. These are estimates, not live data. The website must never present them as current
   rates. They are labelled **"Estimated"**, hidden by default, and only appear if the visitor
   ticks **"Show estimated (not live-verified) rates."** Only numbers pulled from (or checked
   against) a live official source are shown by default. If you add or change a scraper, make
   sure real live data is marked live and fallbacks stay marked as estimates — never dress up a
   default value as the real thing.
2. **When unsure, ask — don't assume.** If a task is unclear, or there is more than one sensible
   way to do it, stop and ask which path to take before making changes. Give concrete options,
   their trade-offs and your recommendation. Guessing wastes effort and can hide problems; a
   short question is always better than an assumption. An unanswered question is not approval.
3. **Focus on building energy costs.** Prioritize residential (including single-family homes),
   commercial, institutional and building-related industrial general facility service defined
   by size, voltage or interruptibility. NECB 2025 (the National Energy Code of Canada for
   Buildings) is a use-case reference, not a utility-rate eligibility rule or a compliance
   claim. Process-specific farm, oil-field, irrigation, NGV (natural gas vehicle) fuelling, EV
   charging, lighting, wholesale/reseller and standby-only services are excluded. Completed work
   and history for those classes remain as reference; do not delete them.
4. **Only the Monthly Scrape on GitHub writes the database.** The real database lives in the
   `data-history` release on GitHub; copies on other computers are read-only mirrors. Never save
   scrapes into a local copy, never upload a database by hand, and never delete the
   `data-history` release: that deletes the database and all its backups.
5. **The registry is the system of record.** Official sources are listed in
   `data/sources/registry.json`. The Excel file `data/excel/old_urls.xlsm` is for audits only; no
   scraper reads it.
6. **Fail closed.** A doubtful source is rejected, never guessed. A price that follows a market
   (for example Ontario's hourly market price) is stored without a number and shown as
   "Variable", never as a made-up average.
7. **Never delete history.** Every stored scrape adds snapshots; earlier snapshots and tariff
   versions are never deleted or changed. Merged and retired utilities are skipped by monthly
   runs but keep their history.
8. **Models are comparison aids, not bills.** Representative models and market benchmarks are
   never a bill and never count as live coverage. Illustrative (synthetic) values never enter
   medians, comparisons or change checks.
9. **Claim complete coverage only when it is true.** Do not say nationwide live-rate coverage is
   complete unless the coverage gate passes and no known source problem is open. A passing gate
   does not override a known problem.
10. **Preserve unrelated work.** Do not change, delete or undo files or changes that are not part
    of your task (for example `tests/_pending/` and the `.claude/worktrees/` folders).

---

## What Does This Project Do?

This project answers one question: **"How much do electricity and natural gas cost across Canada?"**

It works in three stages:

1. **Scrape** — Python scripts visit official utility websites and download rate information.
2. **Store** — That information gets organized into a database (a structured file, kept safely on GitHub).
3. **Display** — A simple website reads the database and shows the rates in a browsable format.

The website also shows real market prices for Ontario and Alberta, and "representative models":
typical monthly costs for comparison (see the glossary). GitHub Actions (GitHub's cloud
computers) runs the updates on a schedule (see "How the Monthly Updates Work").

Having a utility in the registry is not the same as having live rates for it, and a count of live
records does not prove that every building class is covered. Current figures are in the
[README](README.md); known gaps and the work queue are in the
[coverage matrix](docs/phase5_completion_matrix.md).

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
| `scrapers/utilities/` | One scraper file per utility, named after it (for example `bc_hydro.py` or `centra_gas.py`). |
| `scrapers/utilities/ontario_ldc.py` | **One data-driven scraper for every Ontario LDC** (local distribution company). Each is read from its OEB-approved tariff PDF, using `scrapers/utils/oeb_tariff.py`. |
| `scrapers/utilities/toronto_hydro.py` | Toronto Hydro (legacy scraper, separate from the LDC scraper). |
| `atco_electric.py`, `fortisalberta.py`, `epcor_distribution.py`, `enmax_power.py` | The Alberta wires companies (distribution and transmission charges). |
| `direct_energy_regulated.py`, `enmax_energy.py`, `epcor_energy_alberta.py` | The Alberta Rate of Last Resort providers; `scrapers/utils/alberta_rolr.py` checks their prices against the Utilities Consumer Advocate table. |
| `scrapers/utilities/aeso.py` | The AESO pool price reference: a live record with no number ("Variable"), because AESO publishes no customer tariff. |
| `enbridge_gas.py`, `epcor_gas_ontario.py`, `atco_gas.py` | Natural gas in Ontario and Alberta. |
| `scrapers/utilities/epcor_gas.py` | A retired Alberta entry (EPCOR does not distribute gas in Alberta). Monthly runs skip it; its history stays. |
| `scrapers/registry.py` | Reads the list of all utilities and their scraper info. |
| `scrapers/utils/parsing.py` | HTML/PDF reading helpers, including strict checks that a value really appears in an official schedule. |
| `scrapers/utils/change_detection.py` | Compares live-parsed rates against seed data and flags changes by severity (info/warning/critical). If critical drift is detected, the scraper rejects live data and falls back to seed. |
| `scrapers/utils/market_pricing.py` | Reads the Ontario market history for the illustrative estimate (see the glossary). It refuses a file that was not built from real observed prices. |
| `scrapers/utils/validation.py` | Data quality checks run after every scrape. |

### Where the data lives

| File | What it does |
|---|---|
| `data/sources/registry.json` | **The master list (system of record):** every registered utility, its official source URLs and its scraper. Merged and retired entries are skipped by monthly runs but keep their history. |
| `data/inventory/utilities.json` | The full inventory of ALL Canadian utilities — even ones we don't scrape yet. This is the reference list. |
| `data/db/rates.db` | The SQLite database. The real copy lives on GitHub and only the Monthly Scrape writes it; your copy is a read-only mirror from `python scripts/pull_history_db.py` (older copies move to `data/db/backups/`). |
| `data/excel/old_urls.xlsm` | **Audit reference only:** historical URLs and rate data. NO scraper reads this file. It is git-ignored. |
| `site/data/rates.json` | The rates the website reads, created by the export script. |
| `site/data/market_pricing_ontario.json`, `market_pricing_alberta.json` | What the Market Pricing page reads: the latest 60 complete months and a heatmap built only from real observed hours. |
| `data/market/` | Permanent market history for Ontario and Alberta, the project's own hourly Ontario Price archive, and ready-to-use Ontario totals (`ontario_total_*`: energy plus Class B GA in cents/kWh; a missing hour stays blank, never zero, and monthly averages never stand in for it). |
| `data/market/ieso_raw/` | Saved copies of the original IESO reports, kept before any price check. They are unverified evidence, not rates; old copies are never replaced. |
| Other files in `site/data/` | Research notes on each province's market structure, and audit reports of missing customer classes and source URLs. |

### Where the representative models live

A *representative model* is a "typical" monthly cost for a province, worked out from the middle
value (the median) of its utilities' live rates. Electricity models exist for the ten provinces;
gas and the territories come later.

| File | What it does |
|---|---|
| `data/models/crosswalk.json` | The sorting list. Its rules are read from top to bottom; the first rule that fits puts each live tariff into a model group (province, fuel, customer type, rate structure and size) or leaves it out with a written reason. No live tariff may be left unsorted. |
| `data/models/usage_levels.json` | The example customers, approved by the project owner: homes using 500, 1,000 or 2,000 kWh a month; small businesses (under 50 kW) using 2,000 kWh at 10 kW or 8,000 kWh at 25 kW; medium businesses (50-499 kW) using 40,000 kWh at 100 kW; large businesses (500-4,999 kW) using 500,000 kWh at 1,000 kW. Also the average month (30.4375 days, for turning daily charges into monthly ones), Ontario's dated time-of-use split and the synthetic business load profile. |
| `data/models/block_periods.json` | Reviewed notes saying whether an energy block such as "first 5,000 kWh" is per month or per two months, quoting the source. When nothing says, the tariff is left out of the model instead of guessed. |
| `data/models/taxes.json` | Sales taxes and automatic bill rebates for every province and territory, as dated lines: for example the Ontario Electricity Rebate is 23.5% until October 31, 2026 and 15.7% from November 1, 2026 (O. Reg. 328/26). Municipal taxes and income-tested programs are left out. |
| `pipeline/representative_models.py` | The calculator: each utility's monthly cost at each level, then the median, the spread, the utility closest to the median and any far from it (outliers), without and with tax, with a written explanation of how each number was made. |
| `site/data/representative_models.json` | The results, rewritten by every export (if the calculation fails, the previous file is kept). These are comparison aids, never rates anyone is billed. |

### Where the website lives

| File | What it does |
|---|---|
| `site/index.html` | The page and its views: **Rate Browser**, **Market Pricing**, **Representative Models**, **Across-Canada** and **Compare** (two tariffs side by side, never a bill total). |
| `site/js/app.js` | The main logic: loads the data, shows the newest version of each tariff, and runs the filters, rate cards, detail windows and the Market Pricing page (Ontario or Alberta). |
| `site/js/models.js` | The Representative Models page: typical monthly costs without and with tax, the method, the contributing utilities and the example customer's assumptions; a separate historical market benchmark for larger Ontario and Alberta businesses; and, only behind a checkbox, the illustrative estimate with a warning and a SYNTHETIC badge. |
| `site/js/across-canada.js` | Residential electricity across Canada at 500, 1,000 or 2,000 kWh (default 1,000), with tax by default. It reuses the model file, never recalculates bills or uses synthetic estimates, and never turns a missing model into a zero bar. |
| `site/css/` | How the pages look (`style.css`, `models.css`, `across-canada.css`). |

### Where the automation lives

| File | What it does |
|---|---|
| `.github/workflows/scrape.yml` | **Monthly Scrape** (the 1st): the only writer of the database (see "How the Monthly Updates Work"). |
| `.github/workflows/source-health.yml` | **Source Health** (the 15th): a test scrape that publishes nothing. |
| `.github/workflows/ontario-price-archive.yml` | **Ontario Price Archive** (06:00 UTC on the 1st and 15th): saves the original IESO reports, then the checked Ontario Price archive, the market history, the combined totals and the models. |
| `.github/workflows/market-benchmarks.yml` | **Market Benchmarks**: publishes the Alberta market history and refreshes the models, without touching the database. |
| `.github/workflows/deploy.yml` | **Deploy Site**: publishes the website on push, by hand, and by itself after each successful Monthly Scrape, Ontario Price Archive or Market Benchmarks run. |
| `scripts/check_db_history.py` | The Monthly Scrape's safety check: the database is not damaged, and nothing old was lost or changed. |
| `scripts/coverage_gate.py`, `data/sources/coverage_ledger.json` | The coverage gate (see the glossary) and the audit ledger it reads: audit dates, exclusions, and deferred and monitored items for each utility. The ledger records decisions; it never changes a rate. |
| `scripts/pull_history_db.py` | Downloads the newest database to your computer, checks it, and keeps your old copy. It never uploads anything. |
| `scripts/build_ontario_market.py`, `archive_ontario_price.py`, `preserve_ieso_reports.py`, `export_ontario_totals.py` | Build the Ontario market history, extend the hourly Ontario Price archive, save the original IESO reports, and create the combined energy-plus-GA files. |
| `scripts/build_alberta_market.py` | Builds the Alberta market history, checked against every official AESO monthly summary. |

### Where the AI assistant instructions and code map live

| File | What it does |
|---|---|
| `.github/copilot-instructions.md` | The development workflow for AI assistants. Read it together with this file. |
| `.github/instructions/` | Rules for each area of the project, read by AI assistants (see "Required reading and maintenance"). |
| `requirements-graphify.txt` | The one place where the graphify version is pinned (graphify is optional; see "Graphify and the Commit Hook" below). |
| `.graphifyignore` | What graphify leaves out of its code map (tests, data, the database schema, workflows), with the reason for each. |
| `scripts/graphify_hook.py` | Installs and runs the commit hook that updates the code map; `python scripts/graphify_hook.py status` checks the setup. |
| `graphify-out/` | The generated code map ("knowledge graph") that AI assistants search to find code quickly. Never edit it by hand. |

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
is complete and unchanged, and moves any older copy on your computer to `data/db/backups/`. Only
the Monthly Scrape on GitHub saves new data; your copy is for reading. Run this again whenever
you want the newest data. (For an empty practice database instead, run
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

1. **On the 1st of every month** (or when started by hand), start a computer in the cloud and
   install Python, the project tools and Playwright Chromium.
2. **Get the database** from the `data-history` GitHub Release. If the release exists, the
   download must work and its fingerprint (SHA-256) must match the one GitHub shows; otherwise
   the run stops. Only when there is no release at all does it start a new, empty database.
3. Run the tests, then the scrape (all utilities, or the one utility or province typed in when it
   was started by hand), the data quality checks (`python -m pipeline.validate`) and the export
   for the website (`python -m pipeline.export_json`).
4. **Check the database** with `scripts/check_db_history.py`: it must not be damaged, it must
   have at least as many snapshots, tariff versions and scrape runs as before, and every older
   snapshot must be unchanged. A public "Database history" note on the run page gives the result.
5. Only then **save the database** back to the release, together with a dated backup copy
   (`rates-YYYY-MM-DD.db.gz`; the newest 12 are kept), and save the updated site data to the
   repository.
6. Leave publishing to the separate **Deploy Site** workflow, which starts by itself afterwards.
7. If any step fails, create a GitHub Issue; a failed check saves nothing to the release.

**The rule (project owner decision): only this workflow saves new data.** Your computer keeps a
read-only copy (`python scripts/pull_history_db.py`). To store new data, push the code and start
Monthly Scrape (for everything, one utility or one province), or wait for the 1st. Never upload a
database by hand. **Careful:** deleting the `data-history` release on GitHub deletes the database
and all its backups.

Every scrape run posts a short public note on its GitHub run page with its totals (live,
estimated and invalid records, and any utility that failed or returned only estimates); the full
log needs a GitHub sign-in. GitHub Pages must use **GitHub Actions** as its source, and the
automatic trigger (`workflow_run`) only fires from the default branch.

**To run it early (not waiting for the 1st of the month):**
1. Go to the repository on GitHub.
2. Click the **"Actions"** tab.
3. Click **"Monthly Scrape"** on the left.
4. Click the **"Run workflow"** button on the right. You may type one utility name or one
   two-letter province code (not both); leave both empty for everything.

The **Ontario Price Archive** workflow can be started the same way. The owner's computer has no
GitHub command-line tool, so start workflows from the website. **Deploy Site** can also be run by
hand if it did not start by itself after a successful data update.

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

## Source URL Management

- **The Excel file is NOT a data source.** `data/excel/old_urls.xlsm` contains historical
  reference URLs and rate data. **No scraper reads this file.** It exists only for manual audit
  and comparison, and it is git-ignored.
- **The registry IS the system of record.** When source URLs change, update
  `data/sources/registry.json` — not the Excel file. Some scrapers also contain the same URLs as
  constants; keep them synchronized with the registry.
- **Source prioritization.** When choosing which URL to use for a utility, prefer: (1) the
  utility's own rate schedule page, (2) regulator rate orders or decisions, (3) third-party
  aggregators (last resort).

---

## How to Check If a Rate Is Still Correct

1. Open `site/data/rates.json` in a text editor (or look at the website).
2. Find the rate you want to check. Note the **source URL**.
3. Visit that URL in your web browser.
4. Compare the numbers on the utility's website to what's in our database.
5. If they're different, the utility has changed their rates. You need to update the scraper.

---

## How to Add a New Utility

See [docs/adding-a-utility.md](docs/adding-a-utility.md) for the full guide, and the
[scrapers rules](.github/instructions/scrapers.instructions.md) that every scraper follows.

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
2. Has the page moved? Update the registry and any URL constant used by the scraper, and add the
   old address to the list of dead addresses in `tests/test_source_urls.py` (with the date and
   the answer you got, such as "404" or "301"), so it can never come back by mistake. A dead
   address that must stay (an estimate whose page is gone and has no archived copy showing its
   values) goes into the `KEPT_DEAD` list in the same file, with the reason.
3. Has the page layout changed? The scraper's HTML parsing needs updating.
4. Is the page down temporarily? Wait and try again.
5. Test a fix with a dry run for that utility (see "How to Scrape Just One Utility"); the Monthly
   Scrape on GitHub then stores it.

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
table, or an official IESO file could not be read. The validated archive was not changed.
Original reports are saved separately before these checks, so a failed check does not throw away
new daily reports. The market history build still runs, using the validated archive already
saved.

**What to do (soon):** the IESO deletes each daily price file after about 90 days, so a problem
left too long loses hours for good.
1. Pull the saved reports, then run `python scripts/archive_ontario_price.py --no-site-api
   --raw-dir data/market/ieso_raw --dry-run`; it names the month or file that failed and writes
   nothing. The retained daily reports can be read even after IESO removes them.
2. If it says "the IESO published this file empty", nothing is wrong with the project: start the
   workflow again a day or two later, once the IESO has published the file again. (Project owner
   decision: wait for the IESO rather than save prices without their LFDA.)
   If the issue instead says **raw report preservation failed**, check whether the raw commit
   succeeded. A failed Git save leaves an `ieso-raw-recovery` artifact on the run page for
   90 days: download it promptly and repair the save. Raw files must never be treated as
   validated prices just because they were backed up.
3. If a month's LFDA differs from the IESO table by more than a cent, the table may still show a
   preliminary value while the archive already holds the final one; wait for the IESO to update the
   table, then start the workflow again (all three checks stay strict, project owner decision).
4. If the IESO changed its table or files, the script needs updating; if its website was down,
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

**What happened:** the Ontario Price Archive workflow opened an issue whose title names the
market history ("Ontario market history update failed", or "Ontario Price archive and market
history update failed" when both parts failed). The Market Pricing history was not rebuilt, so
the website keeps the previous version. The build writes nothing when a number
disagrees with the IESO's own tables or a file cannot be read.

**What to do:**
1. Run `python scripts/build_ontario_market.py --dry-run` on your computer; it names the month or
   file that failed and writes nothing.
2. If the IESO changed a table or file, the script needs updating; if its website was down,
   start the workflow again later.

### The Market Benchmarks workflow failed

**What happened:** a missing hour, a changed source format or a disagreement with the official
monthly price stopped publication. A changed price for a month that is already archived also
stops it, for review.

**What to do:** read its failure issue. Do not guess a revision deadline or overwrite old
evidence; Ontario and Alberta history stay separate. To check the Alberta history on your
computer without saving anything, run `python scripts/build_alberta_market.py --dry-run`.

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

### graphify is not found or the commit hook reports a problem

graphify is optional: scraping, testing and publishing work without it. The fixes are in
"Graphify and the Commit Hook (Optional)" below.

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
release, next to up to 12 dated backups. Only the Monthly Scrape writes it; your computer keeps a
read-only copy (see "How the Monthly Updates Work").

---

## Ontario Market Pricing — What You Need to Know

Ontario is special. Most Canadian provinces set electricity rates directly — a regulator publishes a price and that's what you pay. Ontario is different:

- **Small customers** (residential, GS < 50 kW) pay OEB-regulated TOU or Tiered rates — simple, published prices.
- **Large customers** (GS >= 50 kW) pay market-based energy prices that change every hour, plus a monthly "Global Adjustment" (GA) that covers long-term generation contracts. "Class B" GA is the version most customers pay.

The hourly market price was the **HOEP** until April 30, 2025. Since May 1, 2025 it is the
**Ontario Price** (OEMP): the day-ahead price (DA-OZP) plus a small adjustment (LFDA). Because the
price changes every hour, large customers' tariffs show a "Market Energy" line with no number,
labelled "Variable"; market averages are never copied into a tariff.

The **Market Pricing** page shows what the market really cost (energy, GA and their total, the
"full cost" a large customer roughly pays per kWh) over the latest 60 complete months, using only
**real (observed) prices**. A month counts as complete only when it is over, its energy price
matches the IESO's own published monthly value, and its Class B GA rate is published. The
heatmap averages each month, weekday or weekend, and hour, using only hours with a real recorded
price. The hourly Ontario Price from May 1, 2025 to July 10, 2026 can no longer be downloaded, so
that gap is explained on the page and never filled with made-up hours.

**Did the new market change what customers pay?** For a large customer who pays the market price
plus the Class B GA, hardly. The energy price alone is much higher now, but the GA fell by almost
as much, because the GA pays generators the difference between their contracts and what the
market pays them. That is why the page shows the old and new markets as one continuous total.

The IESO deletes its daily price files after about 90 days, so the project keeps its own hourly
Ontario Price archive (from July 11, 2026) and copies of the original reports. An hour without a
published LFDA stays blank; it is never treated as zero. Every number is checked against the
IESO's own tables, and nothing is written when a check fails (see "What to Do When Something
Breaks"). A few choices (some 2020-2021 GA values, holidays counted as weekdays) are defaults the
project owner can change. Technical rules: [market data rules](.github/instructions/market-data.instructions.md).

---

## Alberta's Deregulated Market

Alberta is the only province where retail electricity is fully deregulated. This means:

- **Wires companies** (ATCO Electric, FortisAlberta, EPCOR Distribution, ENMAX Power) own the
  wires and charge regulated delivery rates: separate **distribution** and **transmission**
  lines, plus temporary riders with their own dates. Rates approved only temporarily ("interim")
  are shown at medium confidence with a note.
- **Retail energy** is sold separately from wires service. Customers without a retail contract
  pay the **Rate of Last Resort** (RoLR), which replaced the Regulated Rate Option (RRO) on
  January 1, 2025. Each provider's price is fixed for a two-year term and must match the
  Government of Alberta's Utilities Consumer Advocate table; when the term ends, the records stop
  counting as live until the next price is published. Old RRO estimates stay in history.
- **AESO** runs the wholesale market and publishes no customer tariff: the project keeps a live
  "Variable" reference with no price, plus a history of real hourly pool prices for the Market
  Pricing page and the model benchmarks.
- The code models these pieces separately and never adds them into one price. Only the
  representative models put a wires company and the Rate of Last Resort provider for its area
  together, as one "pair", to show a typical monthly cost; each charge keeps its own source. The
  Rate of Last Resort is only for sites using less than 250,000 kWh a year, so larger business
  models show delivery charges plus a separate historical pool-energy benchmark, never a promised
  retail price.

The technical rules are in the [Alberta electricity rules](.github/instructions/alberta-electricity.instructions.md).

---

## Rules for Each Utility

Every utility publishes its rates differently, so each has its own detailed rules. The same ideas
apply to all of them:

- **"Live" means read from the official source.** A record is live only when its scraper read the
  current official document and rebuilt the tariff from it, or proved every charge in it
  (finding the same number somewhere is not enough). If reading fails or a schedule changes
  shape, the records become labelled estimates; never raise their confidence by hand. A mixed
  list of live and estimated records is never labelled entirely live.
- **Keep every charge as published.** Each charge stays a separate line with its own label, unit
  and date. Conditional, optional and source-blocked prices are not charges that every customer
  pays. Different kinds of sources (Alberta wires, Alberta default retail, AESO, gas and northern
  utilities) stay separate.
- **"Complete" means checked.** Completing a utility means auditing its building-related standard
  published classes, not just replacing old estimates. Some products are left out on purpose;
  exclusions and remaining gaps are listed in the [parser gap report](docs/live_parser_gap_report.md)
  and the [coverage matrix](docs/phase5_completion_matrix.md).
- **"Structural drift"** in the logs names charges that could not be verified. Open the registry
  URL, find the current approved schedule, update that utility's reading and its test fixture,
  then run its dry run.

The detailed rules are in the area files: [all scrapers](.github/instructions/scrapers.instructions.md),
[Ontario electricity](.github/instructions/ontario-electricity.instructions.md),
[Alberta electricity](.github/instructions/alberta-electricity.instructions.md),
[other provinces and territories](.github/instructions/regional-utilities.instructions.md) and
[natural gas](.github/instructions/gas-utilities.instructions.md).

---

## Glossary

| Term | What it means |
|---|---|
| **Scraper** | A program that visits a website and extracts data from it automatically. |
| **Dry run** | A trial scrape that reads the official sources but saves nothing. |
| **Seed value (estimate)** | A hand-entered fallback rate, used only when the official source cannot be read. It is labelled "Estimated" and hidden on the website by default. |
| **Fail closed** | When a source is doubtful, reject it instead of guessing. |
| **Fixture** | A small saved excerpt of an official page or file that the tests read instead of going online. |
| **Database** | A structured file that stores information in tables (like a spreadsheet, but more organized). |
| **SQLite** | The specific database format we use. It's a single file — no server needed. |
| **JSON** | A text format for data that web browsers can read easily. |
| **GitHub Actions** | A service that runs code automatically on a schedule (like a cron job in the cloud). |
| **GitHub Pages** | A free service that hosts a static website from a GitHub repository. |
| **Release (`data-history`)** | A storage place on GitHub for files too big to keep with the code. The project's database (`rates.db`) and its dated backups live there; deleting the release deletes them all. |
| **Tariff** | A rate plan or schedule published by a utility (e.g., "Residential Time-of-Use"). |
| **Rate component** | One individual charge within a tariff (e.g., "Tier 1 energy charge: $0.095/kWh"). |
| **TOU** | Time-of-Use pricing — rates that change based on time of day. |
| **Tiered** | Pricing where the rate changes based on how much you use (first X kWh at one price, the rest at a higher price). |
| **Multiplier** | A tariff-defined factor based on eligible dwellings or rooms. Some bulk-metered buildings multiply daily charges and energy allowances by this factor; it is not automatically one. |
| **Demand charge** | A charge based on the peak power (kW) a customer draws, common for commercial and industrial accounts. |
| **Rider** | A temporary adjustment to rates — can be a surcharge or a credit. |
| **Variable (market) charge** | A charge that follows a market price that changes over time (for example the Ontario Price). It is stored with a link to the market but no number, and the website shows "Variable". |
| **Representative model** | A "typical" monthly cost for a province, built from the median of its utilities' live tariffs at set example usage levels, shown without and with tax, with a note explaining how it was made. In Alberta, one "utility" in a model is a pair: a wires company plus the Rate of Last Resort provider for its area. It is a comparison aid, never a rate anyone is billed, and it never counts as live coverage. |
| **Median** | The middle value when numbers are sorted from lowest to highest. Unlike an average, one unusually high or low utility barely moves it. |
| **Outlier** | In a representative model, a utility whose cost is far from the median (more than 30% away, or well outside the range of the middle half of the utilities). It is named with how far away it is; it is not left out. |
| **Synthetic load profile** | A made-up pattern of when a business uses electricity, not taken from any real customer. The project's one (approved by the project owner) assumes full power on weekdays from 7 a.m. to 7 p.m. (Eastern Standard Time) and a smaller, steady amount at all other hours. It is used only for the illustrative estimate. |
| **Illustrative estimate** | A number shown only to give a rough idea, not to be relied on: for Ontario's two larger business sizes, their delivery charges plus market energy priced with the synthetic load profile. It stays hidden until you tick "Show illustrative all-in estimate (synthetic load profile)", carries a warning and a SYNTHETIC badge, and is never used in medians, comparisons or change checks. It is not a forecast, a quote or a bill, and it needs further analysis. |
| **Historical market benchmark** | A comparison using the average of 60 complete monthly energy prices plus today's modeled delivery charges. Ontario includes actual Class B GA; Alberta uses pool energy alone. It is not a forecast, retail quote or customer-profile-weighted bill, and does not replace the base model. |
| **Rolling window** | A period that moves forward as time passes. The Market Pricing page always shows the latest 60 complete months; when a new month is complete, the oldest one leaves the page (it stays in the monthly history file). |
| **Coverage gate** | `scripts/coverage_gate.py`: the check that must pass before anyone may say nationwide live-rate coverage is complete. It fails while any active utility has no live record, no recent audit, an open deferred item or an overdue review. |
| **LDC** | Local Distribution Company — the utility that delivers electricity to your home (common in Ontario). |
| **OEB** | Ontario Energy Board — the regulator that sets many Ontario utility rates. |
| **QRAM** | Quarterly Rate Adjustment Mechanism — the Ontario Energy Board process that resets Ontario natural gas supply prices every three months. |
| **IESO** | Independent Electricity System Operator — operates Ontario's wholesale electricity market. |
| **HOEP** | Hourly Ontario Energy Price — Ontario's former real-time wholesale electricity price. **Retired April 30, 2025** and replaced by the Ontario Price (OEMP). |
| **Ontario Price (OEMP)** | Ontario Electricity Market Price — Ontario's hourly wholesale electricity price since May 1, 2025: the Day-Ahead Ontario Zonal Price plus a Load Forecast Deviation Adjustment. Large customers who are not on the Regulated Price Plan pay it plus the Global Adjustment. |
| **DA-OZP** | Day-Ahead Ontario Zonal Price — the hourly price for the Ontario zone set a day ahead in the IESO market; the main part of the Ontario Price. The IESO keeps only about 90 days of the hourly files online. |
| **LFDA** | Load Forecast Deviation Adjustment — a small hourly adjustment added to the DA-OZP to make the Ontario Price. The IESO publishes it first as preliminary, then as final; some hours have none. |
| **GA** | Global Adjustment — monthly charge in Ontario covering contracted/regulated generation costs. |
| **Class A/B** | Ontario GA allocation categories. Class A (> 1 MW) pays based on coincident peak demand. Class B (everyone else) pays a flat per-kWh charge. |
| **AESO** | Alberta Electric System Operator — operates Alberta's wholesale electricity market. |
| **RRO** | Regulated Rate Option — Alberta's former default retail electricity rate. **Replaced by the Rate of Last Resort on January 1, 2025**; old RRO estimates stay in history. |
| **RoLR** | Rate of Last Resort — Alberta's default retail electricity rate since January 1, 2025, for customers without a retail contract. Each provider's price is fixed for a two-year term. |
| **UCA** | Utilities Consumer Advocate — Government of Alberta office whose default-rates table is used to double-check Alberta default electricity and gas prices. |
| **kWh** | Kilowatt-hour — the standard unit for measuring electricity consumption. |
| **GJ** | Gigajoule — a unit for measuring natural gas energy content. |
| **m³** | Cubic metre — a unit for measuring natural gas volume. |

---

## How to Run Tests

Tests check that the code works correctly. Run them with:

```
pytest tests
```

Always add `tests`: a bare `pytest` also collects old copies of tests left in the git-ignored
`logs/` folder. To run one test file, use for example `python -m pytest tests/test_coverage_gate.py`.

The tests never go online: any attempt to reach a website that a test has not replaced with a
stand-in is blocked. Instead they read **fixtures** in `tests/fixtures/` (small saved excerpts of
official pages, PDFs and market files, with their source addresses) and frozen copies of exported
records, so the tests that run before each Monthly Scrape never depend on that month's data. A
fixture covers only what was saved in it; passing tests do not prove that a utility's whole
catalogue is complete. To check a scraper against the real website, use a dry run.

If the test run seems to freeze, check the size of `logs/scrape.log`. PDF libraries
can write huge debug logs; `setup_logging()` keeps them quiet and caps the file at
10 MB (three older copies kept). The log is only a debug diary: deleting it is safe.

If everything passes, you'll see green output. If something fails, it will show you exactly what went wrong and where.

---

## Graphify and the Commit Hook (Optional)

graphify draws a "map" of the code in the `graphify-out/` folder so AI assistants can find
things quickly. You do not need it to scrape or publish rates.

**To set it up on a new computer:** install Python 3.10 or newer, Git and
[uv](https://docs.astral.sh/uv/), then run `uv tool install graphifyy -c requirements-graphify.txt`
and restart VS Code. Then, in the project folder, run `python scripts/graphify_hook.py install`
once. Details are in the README section "Graphify (optional developer tool)".

**What happens after that:** each time you commit code, the map is updated and saved in a
second, automatic commit called "chore(graphify): refresh code graph for ...". This makes those
commits slower (up to about a minute). Commits that change only documents are not slowed
down. Nothing is ever pushed to GitHub automatically.

**If something goes wrong:**
- "graphify was not found": install it (above), then restart VS Code.
- "is not the pinned ...": a different graphify version is installed. Run
  `uv tool install --reinstall graphifyy -c requirements-graphify.txt`.
- "did not commit it: uncommitted changes": commit or stash your other changes; the next
  commit saves the map.
- To check everything at once: `python scripts/graphify_hook.py status`.
- Never edit files in `graphify-out/` by hand, and never amend a "chore(graphify)" commit.

---

## Documentation Review Rule

**Every task** — whether adding a feature, fixing a bug, or refactoring — must include a final documentation review step. At minimum, check whether the following files need updates:

| File | When to update |
|---|---|
| `README.md` | Roadmap changes, new phases completed, tech stack additions, project structure changes, the quick start or the short current status |
| `AGENTS.md` | New files added, project safeguards changed, glossary terms needed, troubleshooting patterns discovered |
| `.github/copilot-instructions.md` | The development workflow changed |
| `.github/instructions/*.instructions.md` | That area's technical rules changed |
| `docs/adding-a-utility.md` | Scraper patterns or helper functions changed |
| `docs/live_parser_gap_report.md` | Live parser status changed (new parsers, fixed gaps) |
| `docs/phase5_completion_matrix.md` | The work queue or coverage status changed |

Figures that change often (test totals, record counts, run IDs) belong only in the README's short
status. Dated history goes to the local, git-ignored `.local/HISTORY.md`, not into these files.
If the task doesn't warrant a change to any of these files, no update is needed — but the check
should happen.

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
