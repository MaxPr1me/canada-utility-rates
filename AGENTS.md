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
| Alberta electricity | [alberta-electricity.instructions.md](.github/instructions/alberta-electricity.instructions.md) | Alberta wires companies, the Rate of Last Resort, AESO, the Alberta city utilities |
| Other provinces and territories | [regional-utilities.instructions.md](.github/instructions/regional-utilities.instructions.md) | Electricity in the other provinces and the territories |
| Natural gas | [gas-utilities.instructions.md](.github/instructions/gas-utilities.instructions.md) | Natural gas utilities |
| Market data | [market-data.instructions.md](.github/instructions/market-data.instructions.md) | Ontario and Alberta market history, the Ontario Price archive, raw IESO reports, combined totals |
| Representative models | [representative-models.instructions.md](.github/instructions/representative-models.instructions.md) | Representative models, the Across-Canada comparison and spark gap, and the Building Archetypes costs |
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
   never a bill and never count as live coverage. Illustrative (synthetic or simulated) values never
   enter medians, comparisons or change checks. Simulated building archetype costs (the Building
   Archetypes tab, method AC-1) are comparison aids too: shown only in their own labelled tab, never
   a bill or live coverage, and never mixed into model medians, Across-Canada, Compare, Rate History
   or change checks. One exception
   (owner decision 119, November 25, 2026): the Ontario and Alberta business models of 50-499 kW and
   500-4,999 kW add estimated market energy, priced with the general load shape of the simulated
   buildings of their size, to their delivery charges in the main table, so it enters those models'
   medians, change log and Rate History. That energy is labelled estimated, states its assumptions,
   never counts as live coverage, and falls back to "market energy pending" when an input fails.
   The spark gap comparison (Across-Canada; owner decisions 118 and 124-165, November 25-26, 2026) is a
   comparison aid of running costs only: never a bill, never in model medians, the change log, Rate
   History, change checks or coverage. Its Ontario and Alberta mid-size buildings use that labelled
   estimated energy (decision 138).
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

The website also shows real market prices for Ontario and Alberta, "representative models":
typical monthly costs for comparison (see the glossary), a Rate History tab with charts of how
stored prices changed, and a Building Archetypes tab with the yearly cost of simulated buildings at
today's stored tariffs. GitHub Actions (GitHub's cloud
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
| `saint_john_energy.py`, `nelson_hydro.py`, `new_westminster.py`, `penticton.py`, `grand_forks.py`, `summerland.py`, `summerside_electric.py` | Municipal utilities registered in batch 18 (November 4, 2026): Saint John (NB), five BC cities and Summerside (PE). They read council bylaw schedules or rate manuals and have no seed fallback, so a failed source returns no records. |
| `naka_power.py`, `medicine_hat.py`, `lethbridge.py`, `red_deer.py` | Utilities registered in batch 18 continued (November 19, 2026): Naka Power (NT) and the Alberta cities Medicine Hat, Lethbridge and Red Deer. Lethbridge and Red Deer publish their own Rate of Last Resort price; Medicine Hat sells one bundled city rate. No seed fallback. |
| `scrapers/registry.py` | Reads the list of all utilities and their scraper info, finds a typed utility name (accents and capital letters do not matter) and checks a manual Monthly Scrape's inputs before anything is installed. |
| `scrapers/utils/parsing.py` | HTML/PDF reading helpers, including strict checks that a value really appears in an official schedule. |
| `scrapers/utils/change_detection.py` | Compares live-parsed rates against seed data and flags changes by severity (info/warning/critical). If critical drift is detected, the scraper rejects live data and falls back to seed. |
| `scrapers/utils/market_pricing.py` | Reads the Ontario and Alberta market histories for the market benchmarks and for the estimated market energy of the larger Ontario and Alberta business models (see "Estimated market energy" in the glossary). It refuses a file that was not built from real observed prices. |
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
| `site/data/rate_history_series.json`, `rate_history_events.json` | Two reviewed lists for the Rate History tab: the regulated and default prices it charts (Ontario's Regulated Price Plan, Alberta's Rate of Last Resort areas, the default gas supply prices) and the regulator and government decisions it marks, each with its official source. |
| `site/data/rate_history_revisions.json`, `market_quarterly_ontario.json`, `market_quarterly_alberta.json`, `model_cost_quarterly.json` | What the Rate History tab reads besides the rates: stored prices that were corrected later for the same date (written by the Monthly Scrape's export), complete-quarter market averages (written by the market history builders) and the model costs at each quarter's end (written when the model change log is recorded). |
| `data/market/` | Permanent market history for Ontario and Alberta, the project's own hourly Ontario Price archive, and ready-to-use Ontario totals (`ontario_total_*`: energy plus Class B GA in cents/kWh; a missing hour stays blank, never zero, and monthly averages never stand in for it). |
| `data/market/ieso_raw/` | Saved copies of the original IESO reports, kept before any price check. They are unverified evidence, not rates; old copies are never replaced. |
| `data/fuel/heating_oil_prices.json` | Statistics Canada's monthly average retail price of household heating fuel (Table 18-10-0001-01) in six cities (Saint John, Halifax, Charlottetown-Summerside, St. John's, Whitehorse, Yellowknife), for the spark gap. Every month is kept; `scripts/fetch_heating_oil.py` adds new months during the Monthly Scrape and stops for review if a stored month changes. Not a tariff and not in the rates database. |
| `data/btap/` | The owner's simulated buildings (see "Archetype" in the glossary): 68 runs of 17 NECB 2020 building types in Toronto and Calgary, with electric or gas space heating. `results/output.xlsx` describes each run and `parametric/runs/<run id>/timestep.csv` holds its electricity and gas use every 15 minutes. Read by `pipeline/archetype_profiles.py`, which checks every run against the workbook and leaves out a run that does not match, and priced by `pipeline/archetype_costs.py` for the Building Archetypes tab. |
| Other files in `site/data/` | Research notes on each province's market structure, and audit reports of missing customer classes and source URLs. |

### Where the representative models live

A *representative model* is a "typical" monthly cost for a province or territory, worked out from the
middle value (the median) of its utilities' live rates. Electricity models exist for the ten provinces
and, since November 24, 2026, for the three territories (homes and small businesses; see "Territorial
models" below). Natural gas models exist for homes and for small and mid-size commercial buildings, in
the unit each utility bills (cubic metres or gigajoules, never converted); contract, interruptible and
seasonal gas services come later.

**Territorial models (owner decisions, November 24, 2026).** Yukon's two utilities share one rate book,
so it counts once; the Northwest Territories model combines NTPC and Naka Power; Nunavut is Qulliq.
Their prices add percentage riders to old base charges (Yukon's Rider J alone adds 100.23%), so a
reviewed list says what each percentage applies to; an unknown one stops that tariff from being
priced. Each territorial model shows the cost before subsidies (the published tariff, with GST like
the provinces) and, below it, the cost after the automatic territorial subsidies, before tax (the tax
on subsidised bills is not confirmed yet). Nunavut is shown before subsidy only, because Qulliq does
not publish the subsidised price. Government accounts are left out, and interim rates (Qulliq, Naka
Power) are labelled.

| File | What it does |
|---|---|
| `data/models/crosswalk.json` | The sorting list. Its rules are read from top to bottom; the first rule that fits puts each live tariff into a model group (province, fuel, customer type, rate structure and size) or leaves it out with a written reason. No live tariff may be left unsorted. It also holds the reviewed class limits that decide which tariff serves each example customer, each quoting the tariff's own words (for example whether "1,200 GJ per year or less" includes 1,200 GJ). |
| `data/models/usage_levels.json` | The example customers, approved by the project owner: homes using 500, 1,000 or 2,000 kWh a month (1,000 kWh is the reference level); small businesses (under 50 kW) using 2,000 kWh at 14 kW or 10,000 kWh at 40 kW; medium businesses (50-499 kW) using 25,000 kWh at 100 kW; large businesses (500-4,999 kW) using 250,000 kWh at 1,000 kW (both sized from the simulated buildings for every province, owner decision of November 25, 2026). For gas, homes using 100, 200 or 400 cubic metres a month, or 4, 8 or 16 GJ where gas is billed in GJ; small commercial buildings using 500, 1,000 or 2,000 m³ (15, 30 or 60 GJ); mid-size buildings using 2,500, 5,000 or 10,000 m³ (100, 200 or 400 GJ). In each gas set the middle value is the reference level and the others show the range. Every level records who decided it, what it represents, why, and its official sources. Also the average month (30.4375 days, for turning daily charges into monthly ones), Ontario's dated time-of-use split, the settings of the simulated buildings' general load shape that prices the larger Ontario and Alberta businesses' market energy, and the few reviewed rules for charges that depend on the customer (for example which of Liberty Gas NB's customer charges applies). |
| `data/models/block_periods.json` | Reviewed notes saying whether an energy block such as "first 5,000 kWh" is per month or per two months, quoting the source. When nothing says, the tariff is left out of the model instead of guessed. |
| `data/models/percentage_riders.json` | The reviewed list of percentage riders the territorial models apply (Yukon's Riders R, J and J1; Naka Power's Riders R, E and H), each quoting what its percentage applies to, plus the ones left out (a percentage of the whole bill) and the Yukon relief applied only after subsidies. |
| `data/models/subsidies.json` | The reviewed territorial subsidies: which territories show a cost after automatic subsidies, which programs are applied (NWT power support first block, NTPC's Cost of Living Subsidy, Naka's rate equalization, the Yukon relief) or only named (Nunavut's subsidy, whose price is unpublished), each with its official source. |
| `data/models/taxes.json` | Sales taxes and automatic bill rebates for every province and territory, as dated lines: for example the Ontario Electricity Rebate is 23.5% until October 31, 2026 and 15.7% from November 1, 2026 (O. Reg. 328/26). Municipal taxes and income-tested programs are left out. Its `heating_oil` lines (NB, NS, PE, NL, YT, NT) serve only the spark gap: they take the sales tax out of Statistics Canada's heating-oil prices for the before-tax view and never change the models. |
| `pipeline/representative_models.py` | The calculator: each utility's monthly cost at each level, then the median, the spread, the utility closest to the median and any far from it (outliers), without and with tax, with a written explanation of how each number was made. |
| `pipeline/archetype_profiles.py` | Reads and checks the simulated buildings in `data/btap/`: each run's monthly electricity, peaks and gas, its use in each of the year's 8,760 hours (with each hour's local clock time and the tariffs' holidays, for time-of-use and on-peak periods), and its average use in each hour of the market heatmaps (Ontario's in Eastern Standard Time, Alberta's in local time by AESO's hour-ending labels), plus a fingerprint of those values so model monitoring notices when they change. |
| `site/data/representative_models.json` | The results, rewritten by every export (if the calculation fails, the previous file is kept). These are comparison aids, never rates anyone is billed. |
| `data/models/spark_gap.json` | The reviewed spark gap inputs (owner decisions 124-165): the energy amounts compared (a home at 2,000 kWh = 7.2 GJ a month; small and mid-size buildings at their electricity levels), each region's comparison fuel and the published heating-fuel shares behind it, each gas utility's heating value (m³ to GJ; else the CER factor, labelled), the heating-oil energy content, the furnace and boiler efficiencies of the Energy Efficiency Regulations, the realistic heat pump COPs by city, and the reviewed choices when a utility appears in several models. Every value quotes its official source with the date it was checked. |
| `pipeline/spark_gap.py` | The spark gap calculator: prices electricity and gas with the model engine at the spark gap's own points (average = the whole bill ÷ its energy; marginal = the next kWh, m³ or GJ), reads the heating-oil price, and writes `site/data/spark_gap.json`: each region's prices, spark gap, break-even heat pump COP and, for homes, the result in plain words. Rebuilt after every model refresh; a failed build keeps the previous file. |
| `data/models/archetypes.json` | The reviewed inputs of the archetype costs (method AC-1; owner decisions 86-114 and 166-168, November 24-26, 2026): each city's utilities (Toronto Hydro and Enbridge Gas; ENMAX Power, ENMAX Energy and ATCO Gas in Calgary), the rate class rules quoting each class's own words (Toronto Hydro's demand classes and its apartment rule, ENMAX's D200, D300 and D310 tests and demand ratchet, Enbridge Rate 6, which includes apartment buildings, and ATCO Gas Low and Mid Use), the Regulated Price Plan and Ontario Electricity Rebate limits, the time-of-use and on-peak hours with their holidays, Ontario's loss factor rule, Enbridge's heating value (taken from the spark gap entry, not copied) and the dwelling units of the apartment buildings. Every value quotes its official source with the date it was checked. |
| `pipeline/archetype_costs.py` | The archetype cost calculator (method AC-1): prices each simulated building month by month with today's stored tariffs for its city, in the rate class its own simulated load qualifies for. Time-of-use and on-peak energy come from its own hours and demand charges from its own monthly peaks. Where the account would pay the market price, the energy is estimated from its own load shape and the observed market history (labelled estimated). Taxes and rebates are then added. It writes `site/data/archetype_costs.json`; a building with a charge it cannot price is marked "Not computable" with the reason, never guessed. Rebuilt after every model refresh; a failed build keeps the previous file. `python -m pipeline.archetype_costs --dry-run` prints the results and writes nothing. |
| `pipeline/model_monitoring.py` | Compares successful model refreshes, checks whether their saved inputs are usable (including the Rate History list of regulated and default prices) and, when it records the change log, writes the quarter-end model costs that Rate History charts. It does not calculate bills or write the database. |
| `site/data/model_change_history.json` | The public change log, created by a verified automated refresh. Its first entry starts tracking; it does not invent earlier history. |

### Where the website lives

| File | What it does |
|---|---|
| `site/index.html` | The page and its views: **Rate Browser**, **Rate History**, **Market Pricing**, **Representative Models**, **Building Archetypes**, **Across-Canada** and **Compare** (two tariffs side by side, never a bill total). |
| `site/js/app.js` | The main logic: loads the data, shows the newest version of each tariff, and runs the filters, rate cards, detail windows and the Market Pricing page (Ontario or Alberta). A price with an end date shows its period, and an "Ended" tag once that date has passed. A live tariff's detail window has a "History" button that opens it in Rate History. |
| `site/js/rate-history.js` | The Rate History page: the recent price changes, then bar charts of each stored price period (as wide as the period lasts), of the regulated and default prices, of quarterly market averages and of quarterly model costs, each with a table, a CSV download and a shareable link. It charts only live prices collected since September 29, 2026 (the market history goes back further), never estimates, never adds charges together and never extends a price that has ended. |
| `site/js/models.js` | The Representative Models page: typical monthly costs without and with tax, the method, the contributing utilities and the example customer's assumptions; for the territories, the cost after automatic subsidies (before tax) and an "Interim rates" label; and, for the larger Ontario and Alberta businesses, an "Estimated energy" tag in the table and an always-visible note on their estimated market energy: the price used, its assumptions, the same-use-every-hour comparison (the historical market benchmark) and the simulated buildings behind it. |
| `site/js/across-canada.js` | Residential electricity across Canada at 500, 1,000 or 2,000 kWh (default 1,000), with tax by default. It reuses the model file, never recalculates bills or uses estimated, synthetic or simulated values, and never turns a missing model into a zero bar. Territorial bars are labelled "before subsidies"; each territory's row gives its cost after automatic subsidies, before tax. |
| `site/js/spark-gap.js` | The Across-Canada sub-tabs ("Residential electricity", the view above, and "Spark gap") and the spark gap view: a customer selector (home, small building, mid-size building), the tax toggle, bars of the spark gap with a line at 1, and a table of both prices (average and marginal), the spark gap, the break-even heat pump COP and, for homes, the realistic COP and the result in words. It reads `site/data/spark_gap.json` only, the first time its sub-tab opens, and recalculates nothing. |
| `site/js/archetypes.js` | The Building Archetypes page, labelled "Simulated": the yearly cost of each simulated building (with tax and rebates by default; a switch shows the cost before), filters by city, building type and heating, sortable columns, and a detail panel per building: its monthly costs, the rate classes chosen and why, its supply, the cost by charge group and taxes, the same building with the other heating fuel, and links to its simulation files. On phones each building becomes a card. It reads `site/data/archetype_costs.json` only, the first time the tab opens, and recalculates nothing. |
| `site/css/` | How the pages look (`style.css`, `models.css`, `across-canada.css`, `rate-history.css`, `spark-gap.css`, `archetypes.css`). |

The model views label totals **"Before tax and rebates"** and **"With tax and rebates"**.
The second can be lower when an automatic rebate exceeds sales tax (for example Ontario's
Electricity Rebate). An explanation beside the prices names the applied rebate; this is not a
swap of the two amounts.

The Representative Models page also has a **Last changed** note and a change log for one model or
all models. It separates ordinary models from historical market benchmarks; the costs of the larger
Ontario and Alberta business models include their estimated market energy (since November 25, 2026),
so the market's monthly roll changes them. A routine rebuild does not mean the prices changed. If the history is missing
or belongs to a different model generation, the page says so and keeps the model prices usable.
The comparison policy is in the
[model monitoring rules](.github/instructions/representative-models.instructions.md#change-monitoring-phase-8-owner-decision-2026-11-17).

### Where the automation lives

| File | What it does |
|---|---|
| `.github/workflows/scrape.yml` | **Monthly Scrape** (the 1st, and the 4th for the monthly-price utilities): the only writer of the database (see "How the Monthly Updates Work"). |
| `.github/workflows/source-health.yml` | **Source Health** (the 15th): a test scrape that publishes nothing. |
| `.github/workflows/ontario-price-archive.yml` | **Ontario Price Archive** (06:00 UTC on the 1st and 15th): saves the original IESO reports, then the checked Ontario Price archive, the market history, the combined totals, the models, the spark gap and the archetype costs. |
| `.github/workflows/market-benchmarks.yml` | **Market Benchmarks**: publishes the Alberta market history and refreshes the models, the spark gap and the archetype costs, without touching the database. |
| `.github/workflows/model-monitoring.yml`, `scripts/model_monitoring_issue.js` | A shared follow-up check called by the existing data workflows and Source Health. It reports input/refresh problems and manages its own issue; it has no daily schedule and does not block valid publication. |
| `.github/workflows/deploy.yml` | **Deploy Site**: publishes the website on push, by hand, and by itself after each successful Monthly Scrape, Ontario Price Archive or Market Benchmarks run. |
| `scripts/check_db_history.py` | The Monthly Scrape's safety check: the database is not damaged, and nothing old was lost or changed. |
| `scripts/coverage_gate.py`, `data/sources/coverage_ledger.json` | The coverage gate (see the glossary) and the audit ledger it reads: audit dates, exclusions, deferred and monitored items, manual-update decisions, and the "not updated in a year" exemptions and review notes for each utility. The ledger records decisions; it never changes a rate. |
| `scripts/pull_history_db.py` | Downloads the newest database to your computer, checks it, and keeps your old copy. It never uploads anything. |
| `scripts/fetch_heating_oil.py` | Downloads Statistics Canada's monthly heating-oil prices for the spark gap into `data/fuel/heating_oil_prices.json` (run by the Monthly Scrape before the export; `--dry-run` writes nothing). A failed download keeps the last file. |
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

1. **On the 1st of every month**, again **on the 4th** for a short list of utilities (see "Prices
   posted after the 1st" below), or when started by hand, start a computer in the cloud and
   install Python, the project tools and Playwright Chromium.
2. **Get the database** from the `data-history` GitHub Release. If the release exists, the
   download must work and its fingerprint (SHA-256) must match the one GitHub shows; otherwise
   the run stops. Only when there is no release at all does it start a new, empty database.
3. Run the tests, then the scrape (all utilities; on the 4th only the monthly-price utilities; or
   the one utility or province typed in when it was started by hand), the data quality checks
   (`python -m pipeline.validate`), the heating-oil prices for the spark gap
   (`python scripts/fetch_heating_oil.py`) and the export for the website
   (`python -m pipeline.export_json`, which also rebuilds the models, the spark gap and the
   archetype costs).
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
4. Click the **"Run workflow"** button on the right. Type one utility name in the **utility** box
   (accents and capital letters do not matter: `energir` finds `Énergir`), or one two-letter
   province code in the **province** box (not both); leave both empty for everything. A mistyped
   entry stops the run within seconds, before anything is installed, scraped or saved, and the red
   error says what to type instead: the utility box for a utility name typed in the province box,
   or the closest registry names for a name it does not know (Eastward Energy is registered as
   `Heritage Gas`). Such a stopped run does not open a monitoring issue.

The **Ontario Price Archive** workflow can be started the same way. The owner's computer has no
GitHub command-line tool, so start workflows from the website. **Deploy Site** can also be run by
hand if it did not start by itself after a successful data update. If Deploy Site itself failed at
its publishing job, open the failed run and click **"Re-run failed jobs"** within a day: only the
publishing job runs again, using the site copy already prepared (kept for one day). After that,
start Deploy Site again with **"Run workflow"**.

**Prices posted after the 1st (owner decisions, November 20 and 23, 2026):** Énergir, Eastward
Energy (registered as `Heritage Gas`), Liberty Utilities NB, the City of Medicine Hat and ATCO Gas's
default gas rate (Direct Energy Regulated Services, which must match the Utilities Consumer Advocate
table) change a price every month and are often posted after the 1st. The run on the 1st then stores
nothing new for them: Medicine Hat's monthly records fail closed, and the gas utilities' stored
supply prices have ended, so the models leave those tariffs out. These five are marked
`monthly_price_refresh` in `data/sources/registry.json`, and the Monthly Scrape runs again at
08:00 UTC on the 4th (1 a.m. in Alberta in winter) for them only. Model monitoring waits for that
run before reporting their failures from the 1st, and names them only if the run on the 4th fails
too or has not refreshed them within a day.

If the City of Medicine Hat posts its month after the run on the 4th (likely in January 2027: it
recalculates its rate on the first business day of the quarter, Monday January 4), start Monthly
Scrape with the utility `City of Medicine Hat Electric Utility` once the new month appears on the
City's [Energy Plans & Pricing page](https://www.medicinehat.ca/home-property-utilities/utilities/energy-plans-pricing/).
Until a run stores it, its residential and small-business prices are left out of the Alberta
models. Its fixed rate for large customers ends December 31, 2026, so from January 1, 2027 until
that run the coverage gate also reports Medicine Hat as having no live rates.

**Nova Scotia Power in January 2027 (owner decision, November 23, 2026):** every NS Power base
tariff stored today ends December 31, 2026. Its approved tariff book already lists the January 1,
2027 base prices and fuel adjustment, but not the 2027 energy-efficiency (DSM) and storm riders,
which NS Power publishes later (in 2026 its new book arrived in May). Until NS Power posts a book
with every 2027 charge, its runs return estimates, the Nova Scotia electricity models are left out,
and the coverage gate and model monitoring report it: this gap is expected. Once the new book is
linked from NS Power's [residential rates page](https://www.nspower.ca/your-home/residential-rates/standard-residential),
start Monthly Scrape with the utility `Nova Scotia Power`; if that run still returns estimates, the
scraper needs updating for the new book. Similarly, Nelson Hydro's 2027 prices come from its bylaw
from January 1, while the City of Penticton's 2027 prices count only once its fees bylaw prints a
2027 column (its 2026 prices end December 31); the next Monthly Scrape stores them.

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
7. Push, then start Monthly Scrape for the new utility (or its province) to store it; see the full guide's "Verify the data".

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

### Source Health is green but a source failed

**What happened:** Source Health is deliberately non-blocking. A scraper can return estimates or no
records without raising an error, so "utilities succeeded" and a green workflow do not mean every
utility returned live rates.

**What to do:** read the public "Scrape provenance" notice and the final log summary for seed-only or
empty utilities. In the full log, the "Response from ..." lines for that utility show what each
website answered (for example "HTTP 403 ... server cloudflare" means the site refused GitHub's
computer, not that the rates changed). Check each named utility with a targeted dry run, repair its
official-source access or parsing, then inspect a fresh GitHub Source Health log before publishing
the repaired data.

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

### Model monitoring opened an issue or history is unavailable

**What happened:** a saved input, source check or refresh could not be verified, failed, or became
overdue. Ordinary price changes go in the public change log, not failure issues. A green data
workflow does not dismiss a monitoring warning.

**What to do:**
1. Read the named checks and their linked run. For a local, read-only check, run
   `python -m pipeline.model_monitoring --dry-run`; it checks saved files, not GitHub's schedule.
2. Fix or verify the named source/input, then use the appropriate existing workflow. A source-only
   problem can recover through Source Health; a publication problem needs a successful data
   publication. Checking just one utility does not replace a full source refresh.
   A utility the ledger marks for manual updates (`manual_update`; Maritime Electric, whose website
   blocks GitHub) is named only once its yearly review is overdue: follow its yearly procedure in the
   [regional rules](.github/instructions/regional-utilities.instructions.md#maritime-electric).
   A newly registered utility is named as having no live output from the first check after it is
   registered until a Monthly Scrape stores it: start that run and the issue closes itself
   (November 19, 2026).
   Énergir, Eastward (`Heritage Gas`), Liberty, Medicine Hat or ATCO Gas named after the 4th: see
   "Prices posted after the 1st" above. A check named `workflow:scrape.yml:monthly-price` means no
   successful run refreshed those utilities within a day of the 4th: start Monthly Scrape with both
   boxes empty (a full run also refreshes them).
   A check named `rate_history_series` means a regulated or default price charted on the Rate History
   tab no longer matches a current stored price, usually because a scraper renamed it: update its
   entry in `site/data/rate_history_series.json` (and the test records in
   `tests/fixtures/rate_history_records.json`), then push; the next check closes it.
   A check named `market_energy_estimate` means a larger Ontario or Alberta business model could not
   estimate its market energy (the reason is given: usually a market history that is out of date or
   invalid, or simulated buildings that could not be read), so it shows delivery charges only. Fix the
   named input (for a stale market history, see the market workflows below); the next successful model
   refresh makes the estimate again and the issue closes itself.
   A check named `spark_gap` names one of four problems. "Older than the representative models": the
   last spark gap build failed (read "Refresh spark gap comparison" or the export log; run
   `python -m pipeline.spark_gap --dry-run` to see the error), and the page keeps its previous
   comparison. "More than 3 months old": Statistics Canada's heating-oil prices were not refreshed (read
   "Refresh heating-oil prices" in the Monthly Scrape log; `python scripts/fetch_heating_oil.py
   --dry-run` shows what Statistics Canada answers; if it says a stored month changed, check the
   table before refreshing). "Checked more than 365 days ago": a reviewed value in
   `data/models/spark_gap.json` (a heating value, an efficiency or a source) needs its yearly check:
   open its source, update the value if it changed, set its `reviewed` or `checked` date and push.
   "Invalid": fix the named entry. The next check closes the issue.
   A check named `archetype_costs` names one of two kinds of problem. "Missing or unreadable", "not a
   AC-1 SIMULATED document" or "older than the representative models": the last archetype build failed
   (read "Refresh archetype costs" or the export log; run `python -m pipeline.archetype_costs --dry-run`
   to see the error), and the Building Archetypes tab keeps its previous costs. "Checked more than 365
   days ago" or "Reviewed archetype input problem": a value in `data/models/archetypes.json` needs its
   yearly check or a fix: open its source, update the value if it changed, set its `checked` or
   `reviewed` date and push. The next check closes the issue.
3. The checker updates its own issue and closes it only after all recorded problems have verified
   recovery. Other issues and maintainer notes are left alone. Do not delete change history to
   silence a warning. On a data run while a problem is open, the "Record model change history" step
   can show "Process completed with exit code 1" although the run succeeded: that step only reports,
   never blocks, and the change history is still saved.
4. If tracking has not started, the first verified automated model refresh creates the baseline.
   Local exports do not update that shared history, so their history panel may be unavailable even
   while their model prices work.

There is no daily checker: missed refreshes are noticed at the next existing or manual check.
Timing and recovery details are in the
[CI monitoring rules](.github/instructions/ci-data-history.instructions.md#model-monitoring).

### Rates not updated in a year

**What happened:** an issue titled "Rates not updated in a year: 2027 Q1" (or a later quarter) lists
utilities with an official document (a tariff sheet, a rate page, a supply-price page) whose prices
have not changed for more than a year. Each line gives the document, its last price change and the
date it became a year old. The issue is created only after the first successful full Monthly Scrape
of January, April, July or October; between those reports the same list appears in the coverage
gate note on Monthly Scrape run pages and in the monitoring summary of each run. This is a prompt to
check, not an error: the gate still passes. A price whose term has ended is a different problem (the
gate reports it as `live_expiring` or `no_live_output`).

**What to do:**
1. For each utility, open the listed document and the utility's official rate page, and run a dry run
   (`python -m pipeline.run_scrape --utility "Name" --dry-run`).
2. Decide which of three findings applies:
   - **legitimate:** the prices really have not changed (for example a fixed multi-year term, or base
     rates that change only through riders printed in other documents);
   - **parser fixed:** the utility published new prices but the scraper missed them; fix the scraper
     (the next Monthly Scrape stores the new prices, which clears the flag by itself);
   - **moved on:** the utility now publishes its prices in a new document or at a new address; update
     the scraper and `data/sources/registry.json`.
3. Record the finding in the utility's entry in `data/sources/coverage_ledger.json`, for example
   `"freshness_review": {"reviewed": "2027-01-05", "finding": "legitimate", "basis": "Fixed term
   January 1, 2025 to December 31, 2026, checked on the official page"}`. `finding` is `legitimate`,
   `parser_fixed` or `moved_on`. The note clears the flags that exist on its date for one year, or
   until an earlier `"review_by"` date you add; a price that turns a year old later is flagged again.
   Only one note per utility: a new review replaces the old one, and Git keeps the history.
4. Push the change. Every monitoring run refreshes the issue's list, and the issue closes itself once
   the list is empty. A closed issue is never reopened: new flags wait for the next quarter's report,
   which also replaces an issue still open.

Details: the [CI rules](.github/instructions/ci-data-history.instructions.md#coverage-gate-scriptscoverage_gatepy-owner-decisions-2026-10-30).

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

### Rate History says a chart's data is "not available yet"

**What happened:** that part's file has not been written yet. The quarterly market files appear after
the next Ontario Price Archive or Market Benchmarks run, the quarterly model costs after the next run
that records the model change log, and the correction notes after the next Monthly Scrape.

**What to do:** wait for that run (or start it by hand on GitHub). The other parts of the tab keep
working. If the note stays after a successful run, read that run's log: a failed quarterly file is
logged there and the previous file is kept.

### Building Archetypes says the costs are not available, or a building is "Not computable"

**What happened:** "Not available" means `site/data/archetype_costs.json` is missing or could not be
read; the other tabs are not affected. "Not computable" on one building means one of its prices could
not be used, and the reason is listed in its detail panel. Usually a price has ended and the next one is
not stored yet. Expected cases:
- the Calgary gas buildings, from the 1st of each month until the run on the 4th stores ATCO Gas's
  new default supply price;
- from January 1, Toronto's gas buildings until Enbridge's January supply price is stored, and the
  Calgary buildings on the Rate of Last Resort until its 2027 term is stored.

A building is never priced with a guessed value.

**What to do:** for "Not available", see the `archetype_costs` check under "Model monitoring opened an
issue" above. For "Not computable", wait for the run that stores the missing price (or start Monthly
Scrape by hand for that utility). Every export rebuilds the costs, so the building comes back by
itself.

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
- **City utilities:** Lethbridge and Red Deer own their wires and publish their area's Rate of Last
  Resort price themselves. Medicine Hat produces, delivers and sells electricity, so each of its
  prices bundles delivery and energy.
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
  together, as one "service area", to show a typical monthly cost; each charge keeps its own
  source. Each city also counts as one service area. The Rate of Last Resort is only for sites
  using less than 250,000 kWh a year, so larger business models show delivery charges plus an
  estimate of their pool energy (priced with the general load shape of the simulated Calgary buildings
  of their size, labelled estimated), never a promised retail price.

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
- **A price with a period ends on time.** Gas supply prices that change monthly, quarterly or every
  six months carry the end of the period their source states (owner decision, November 20, 2026),
  and a price its source labels with a year (Nelson Hydro's and Penticton's yearly schedules) ends on
  December 31 of that year (owner decision, November 23, 2026). After that date the next model update
  leaves that tariff out (a tariff is never priced without one of its required prices) until a
  Monthly Scrape stores the new price, and the Rate Browser tags the price "Ended" (it is never hidden;
  owner decision, November 23, 2026). A price with no set period, which changes only when a regulator
  approves a new one (FortisBC, SaskEnergy), stays open-ended. The gas list is in the
  [gas rules](.github/instructions/gas-utilities.instructions.md#all-gas-utilities).
- **Up to date within months; a year is the alarm (owner decision, November 23, 2026).** Rates
  should be kept up to date, but being a few months behind (for example a utility posting its
  January prices late) is acceptable. Data that has not been updated in a year is the real problem.
  Scrapers should find new documents, editions and years by themselves, and a flagged error should
  name what changed so it is quick to fix. Details: the
  [scraper rules](.github/instructions/scrapers.instructions.md#freshness-and-maintenance).
  The coverage gate checks this for every official document a utility's prices come from, and a
  quarterly issue lists what is a year old (see "Rates not updated in a year" under "What to Do When
  Something Breaks"). AESO (it
  publishes no price) and Maritime Electric (its yearly manual update already checks it) are exempt,
  as their ledger entries say (owner decisions, November 23 and 24, 2026).
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
| **Same-date correction** | A stored price that was fixed later for the same effective date (for example after a scraper fix). Rate History shows the latest value with a "revised on" note; it never counts as a price change. |
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
| **Representative model** | A "typical" monthly cost for a province or territory, built from the median of its utilities' live tariffs at set example usage levels, shown without and with tax, with a note explaining how it was made. In Alberta, one "utility" in a model is a service area: a wires company plus the Rate of Last Resort provider for its area, or one city utility (Lethbridge, Red Deer or Medicine Hat). Territorial models also show the cost after automatic subsidies, before tax. It is a comparison aid, never a rate anyone is billed, and it never counts as live coverage. |
| **Median** | The middle value when numbers are sorted from lowest to highest. Unlike an average, one unusually high or low utility barely moves it. |
| **Reference level / sensitivity level** | In a representative model, the reference level is the example customer the model is built around (for example a home using 1,000 kWh a month, or a small commercial building using 1,000 m³ of gas); sensitivity levels (often half and double) show how the cost changes with use. Sensitivity levels are not "typical" customers. |
| **Outlier** | In a representative model, a utility whose cost is far from the median (more than 30% away, or well outside the range of the middle half of the utilities). It is named with how far away it is; it is not left out. |
| **Archetype (simulated building)** | A typical building of one type (for example a medium office, a primary school or a hospital) designed to the National Energy Code of Canada for Buildings 2020 and run through an energy simulation for a typical weather year. The project holds the owner's 68 runs: 17 building types in Toronto and Calgary, each with electric or gas space heating. They are simulations, not metered customers: anything priced from them is labelled simulated or estimated. A run with more than 300 occupied hours of unmet heating or cooling is flagged as lower quality. The Building Archetypes tab prices each run at today's stored tariffs for its city (method AC-1). |
| **Demand ratchet** | A tariff rule that bills demand at no less than a share of the highest demand of the past months (for ENMAX Power's D300 and D310 classes, 90% of the highest kVA demand in the last 365 days), so a building with a winter peak still pays for part of it in summer. |
| **Loss factor** | In Ontario, the factor each distributor publishes (for example 1.0295 for Toronto Hydro's secondary-metered customers) by which metered kWh are raised for the electricity lost in the wires; bills charge the energy and the per-kWh transmission and regulatory charges on those adjusted kWh. The Building Archetypes tab applies it; the representative models state it but do not apply it (owner decision 122). |
| **BTAP** | Building Technology Assessment Platform: Natural Resources Canada's tool that builds and simulates the archetypes (with OpenStudio and EnergyPlus). |
| **Simulated load shape** | When a simulated building uses electricity through the year, every 15 minutes. The Representative Models page scales the simulated buildings whose usual monthly peak falls in a model's size range to the same yearly use and averages them, hour by hour, into one general shape, which prices the market energy of the larger Ontario and Alberta businesses. |
| **Estimated market energy** | The energy part of the Ontario and Alberta business models of 50-499 kW and 500-4,999 kW. These customers buy energy at market prices, which have no published price, so the model adds an estimate: the market price of the general load shape of the simulated buildings of that size over the latest 60 complete months, times the example customer's kWh (owner decisions of November 25, 2026). It is labelled estimated, its assumptions are listed under the table, it never counts as live coverage, and if an input fails the model shows delivery charges only ("market energy pending"). It replaced, the same day, an opt-in estimate shown behind a checkbox, which had itself replaced one built from a made-up business-hours profile. |
| **Historical market benchmark** | A comparison using the average of 60 complete monthly energy prices plus today's modeled delivery charges. Ontario includes actual Class B GA; Alberta uses pool energy alone. It is not a forecast, retail quote or customer-profile-weighted bill, and does not replace the base model: the Representative Models page shows it as the "same use every hour" comparison beside the estimated market energy. |
| **Rolling window** | A period that moves forward as time passes. The Market Pricing page always shows the latest 60 complete months; when a new month is complete, the oldest one leaves the page (it stays in the monthly history file). |
| **Spark gap** | The price of a kWh of electricity divided by the price of a kWh of the region's usual heating fuel (natural gas, or heating oil where gas is not the usual fuel), before any equipment efficiency. A spark gap of 3 means a kWh of electricity costs three times a kWh of the fuel. Not the power-market "spark spread". |
| **Break-even heat pump COP** | The spark gap × the furnace's efficiency: a heat pump whose seasonal COP is higher costs less to run than that furnace. |
| **COP (coefficient of performance)** | The heat a heat pump delivers for each unit of electricity it uses. A *seasonal* COP averages a heating season, including any backup heat; it falls as the climate gets colder. |
| **AFUE** | Annual fuel utilization efficiency: the seasonal efficiency rating of a home furnace (new gas furnaces must reach 95% and new oil furnaces 83% under the Energy Efficiency Regulations). Commercial equipment is rated by its steady-state *thermal efficiency* instead. |
| **Heating value** | The energy in a cubic metre of natural gas (or a litre of oil), used to turn m³ or litres into GJ or kWh. Each gas utility publishes its own (for example Énergir bills at 37.89 MJ/m³). |
| **Coverage gate** | `scripts/coverage_gate.py`: the check that must pass before anyone may say nationwide live-rate coverage is complete. It fails while any active utility has no live record, no recent audit, an open deferred item or an overdue review. It also warns, without failing, about documents whose prices have not changed for more than a year. |
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
