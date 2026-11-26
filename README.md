# Canada Utility Costs

**Browse electricity and natural gas rates across all Canadian provinces and territories.**

This project scrapes official utility rate data, stores it in a structured database, and
serves it as a clean, browsable static website via GitHub Pages. It focuses on the tariffs
needed to understand building energy costs.

## Quick Start

New to Python or the command line? Follow these steps in order. Type each command in a terminal
opened in the project folder (Windows: press `Win + R`, type `cmd`, press Enter; Mac: open
**Terminal**) and press Enter.

**You need:**

- **Python 3.10 or newer** from [python.org/downloads](https://www.python.org/downloads/). On
  Windows, tick **"Add Python to PATH"** during installation. `python --version` should then
  print something like `Python 3.12.1`.
- **A copy of this project:** with Git, run
  `git clone https://github.com/MaxPr1me/canada-utility-rates.git` and then
  `cd canada-utility-rates`. Without Git, click the green **Code** button on GitHub, choose
  **Download ZIP**, unzip it and open a terminal in that folder.

**1. Install the tools** (once; use the same Python 3.10+ environment for every step, ideally a
virtual environment):

```bash
pip install -r requirements.txt
pip install -e .
python -m playwright install chromium
```

The installs should finish without errors. Chromium is the hidden browser used for rate pages
that need JavaScript.

**2. Get a read-only copy of the database:**

```bash
python scripts/pull_history_db.py
```

It downloads `data/db/rates.db` from the project's `data-history` release on GitHub, checks it
against the SHA-256 fingerprint GitHub publishes and prints a line starting with `Installed`
(or saying "already matches" when your copy is current). An older copy moves to
`data/db/backups/`.

**3. Try a scrape without saving anything:**

```bash
python -m pipeline.run_scrape --dry-run
```

It reads the official utility websites (a full run takes several minutes) and ends with a
summary box: live and estimated record counts, any utility that returned only estimates, and
`(dry run — nothing saved to database)`. A finished run does not prove every rate was live:
read those counts.

**4. Export the website data:**

```bash
python -m pipeline.export_json
```

It writes the JSON files in `site/data/` (rates, utilities, summaries, the representative models,
the spark gap and the building archetype costs) and prints `JSON export complete`.
Change history is recorded by automated refreshes, not this local export; model prices still work
if the optional history panel is unavailable.

**5. View the website:**

```bash
python -m http.server --directory site 8000
```

Open http://localhost:8000 (pick another free port if 8000 is busy) to see seven views: Rate
Browser, Rate History, Market Pricing, Representative Models, Building Archetypes, Across-Canada and
Compare. Opening the HTML file directly (`file://`) does not load the data reliably. Press
`Ctrl + C` to stop the server.

**Important limitations:**

- **Only the Monthly Scrape on GitHub stores data.** Your database is a read-only copy: never
  store scrapes locally or upload a database (see [How Monthly Updates Work](#how-monthly-updates-work)).
- **Estimated values are hidden by default.** Fallback (seed) values are shown only when you
  tick **"Show estimated (not live-verified) rates"** on the site.
- Representative models, building archetype costs and market charts are comparison aids, never
  bills or forecasts.

More commands: [Common Commands](#common-commands). If something goes wrong:
[Troubleshooting](#troubleshooting).

---

## Current Status

- **Stored coverage:** all 89 active registered utilities have live output and the strict coverage
  gate passes (checked November 19). Stored output alone does not prove a source is still healthy:
  Maritime Electric's source fails on GitHub and is refreshed by hand (see below).
- **New utilities (published November 18):** Saint John Energy (NB), Nelson Hydro, New
  Westminster, Penticton, Grand Forks and Summerland (BC), and Summerside Electric (PE) are stored
  live and contribute to their province's models (69 models; BC residential now has 7 utilities).
- **Batch 18 continued (published November 19):** the owner's Monthly Scrapes for province AB and
  for Naka Power stored Naka Power (NT, 6 live) and the Alberta cities Medicine Hat (5), Lethbridge
  (8) and Red Deer (8), with the history verified. The Alberta models now count each city as one
  service area: residential has 7 instead of 4 (1,000 kWh median $209.78 before tax, was $225.16).
  The model-monitoring issue opened by the registration (#7) closed itself after the second run.
  Medicine Hat's default energy price is monthly: its records drop out of the models at month end
  until a run stores the new month (owner decisions November 19). The monthly-price run on the 4th
  (below) now stores it.
- **Small fixes (November 20, owner decisions):** the Alberta models' coverage no longer counts
  AESO, which publishes only a market price reference (7 of 7 service areas, was 7 of 8; prices
  unchanged); the diff report compares only the utilities the newer run scraped; the console log
  writes UTF-8 on Windows.
- **Énergir supply price (fixed and stored November 20, scrape run 45):** the stored price was the
  tariff's October figure (15.535 ¢/m³) although Énergir changes it monthly (10.837 ¢/m³ from
  November 1). The scraper now reads the current month from Énergir's supply-price page, checks it
  against Énergir's price history workbooks, and leaves the supply price out while a month is not
  posted yet.
- **Gas supply-price periods (stored November 20 by the owner's full run, scrape run 46):** Enbridge,
  EPCOR, Centra, Eastward and Liberty supply prices now end with the period their source states
  (quarter, month or Eastward's six-month residential block); FortisBC and SaskEnergy stay
  open-ended.
- **Monthly-price run (added November 23, owner decisions; first run December 4):** the Monthly
  Scrape also runs at 08:00 UTC on the 4th for the utilities whose monthly price is often posted
  after the 1st (Énergir, Eastward, Liberty, Medicine Hat and ATCO Gas's default gas rate, flagged
  `monthly_price_refresh` in the registry). Model monitoring holds those utilities' failures on the
  1st until that run, and checks its schedule apart from the full run. A manual run's inputs are
  now checked before anything is installed: utility names ignore accents and case, and a mistyped
  name or code says what to type.
- **January 1 readiness (November 23, owner decisions):** Nelson Hydro reads its bylaw's 2027
  schedules from January 1 even if its rates page still shows 2026; Nelson's and Penticton's yearly
  prices end December 31. NS Power's 2026 prices also end then and its 2027 riders are not published
  yet, so it is expected to return estimates (and the Nova Scotia models to be left out) until NS
  Power posts a complete 2027 book; the owner then starts its run (see AGENTS.md, "How the Monthly
  Updates Work").
- **One-year check (November 24, owner decisions November 23 and 24):** the coverage gate now warns,
  without failing, when an official document behind a utility's live prices has not changed for more
  than a year, and the first successful full Monthly Scrape of each quarter opens a "Rates not
  updated in a year" issue (first report January 2027). On November 24 it flagged 8 utilities: the
  three Alberta Rate of Last Resort providers (fixed 2025-2026 term), SaskEnergy, Qulliq, Liberty NB
  (distribution charges) and the two Yukon utilities (base rates adjusted through riders). The owner
  reviewed all eight the same day (all legitimate; dated notes in the coverage ledger), so none is
  flagged now. AESO and Maritime Electric are exempt (see AGENTS.md, "Rates not updated in a
  year").
- **Territorial models (method 7T-1, November 24, owner decisions 64-79):** Yukon, the Northwest
  Territories (NTPC and Naka Power) and Nunavut now have electricity models for homes and small
  businesses. Their percentage riders are applied from a reviewed list, government rates are left
  out and interim rates are labelled. Homes also show the cost after automatic subsidies, before tax
  (1,000 kWh: Yukon $323.62 before and $253.66 after; Northwest Territories $542.73 and $429.16);
  Nunavut is shown before subsidy only, because its subsidised price is not published. The ten
  provinces' 85 models are unchanged.
- **Rate History tab (November 24, owner decisions 44-57 and 80-84):** a sixth view charts how stored
  prices changed: each live tariff's price periods (bars as wide as each period lasts) since
  collection began on September 29, 2026; the regulated and default prices (Ontario's Regulated Price
  Plan, Alberta's Rate of Last Resort areas, the default gas supply prices); quarterly Ontario and
  Alberta market averages from the stored history; and quarterly model costs. It opens on the recent
  price changes (November 1 so far). Estimates are never charted, ended prices are never extended,
  charges are never added together, and regulator decisions are marked with their official sources.
  Its quarterly market and model files and its correction notes appear after the next data runs.
- **Estimated market energy in the larger business models (method 7S-2, November 25, owner
  decisions 119-123):** the Ontario and Alberta 50-499 kW and 500-4,999 kW models now include their
  market energy, which has no published price: an estimate from the general load shape of the owner's
  simulated buildings of that size and the observed market history, labelled estimated with its
  assumptions listed (Ontario 50-499 kW: 10.93 cents/kWh, $4,455.56 a month before tax; Alberta: 10.68
  cents/kWh, $4,859.00). If an input fails, they fall back to delivery charges only. Every province now
  uses 25,000 kWh at 100 kW and 250,000 kWh at 1,000 kW for these sizes (Quebec 50-499 kW: $3,397.20 a
  month before tax, was $4,341.00 at 40,000 kWh). This replaced the opt-in estimate of method 7S-1,
  built earlier the same day.
- **Spark gap (method SG-1, November 26, owner decisions 118 and 124-165):** the Across-Canada tab has
  two sub-tabs, "Residential electricity" (unchanged) and "Spark gap". For each region it divides the
  price of a kWh of electricity by the price of a kWh of the usual heating fuel (natural gas from British
  Columbia to Quebec; heating oil, from Statistics Canada's monthly prices, in the Atlantic provinces and
  the territories), for homes and for small and mid-size buildings in the eight gas provinces, then gives
  the heat pump efficiency (COP) that would make up the difference; for homes it is checked against
  published seasonal heat pump COPs. Running costs only, never a bill, and never part of the models. On
  November 26, with tax: a heat pump costs less to run than a new furnace in British Columbia, Quebec and
  the Atlantic provinces, the furnace in Alberta, Saskatchewan, Manitoba and (narrowly) Ontario; Nunavut
  has no official heating-oil price.
- **Building Archetypes tab (method AC-1, November 26, owner decisions 86-114 and 166-168):** a new
  tab prices the owner's 68 simulated NECB 2020 buildings (17 types in Toronto and Calgary, electric or
  gas heating) for a year at today's stored tariffs. Each building is priced month by month in the rate
  class its own simulated load qualifies for (Toronto Hydro and Enbridge Rate 6; ENMAX Power with ENMAX
  Energy's Rate of Last Resort or estimated pool energy, and ATCO Gas). Its time-of-use and on-peak
  energy come from its own hours and its demand charges from its own peaks. Where it would pay the
  market price, the energy is estimated from its own load shape. Labelled simulated: never a bill,
  never part of the models or the other views. On November 26, 61 of 68 were priced (Toronto medium
  office with gas heating: $91,948 a year with tax and rebates). The 7 Calgary buildings on ENMAX
  Energy's Rate of Last Resort for mid-size sites wait for that price, which the December 1 run stores.
  36 runs are flagged for more than 300 occupied unmet hours. The same day, the Alberta market hour on
  the spring daylight-saving day began following AESO's hour-ending labels (decision 166; the Alberta
  500-4,999 kW model moved by $0.26 a month).
- **Latest export (November 20, scrape run 46, the owner's full run):** 987 latest live tariffs and
  484 retained estimates; 1,414 stored live versions and 7,670 history snapshots. Counts include
  conditional products and reference-only records, not complete utility catalogues.
- **Corrections stored (verified November 4):** the targeted Monthly Scrapes stored Centra Gas
  Manitoba's 13 November records and Maritime Electric's first-20-kW-free demand tier; history
  checks, the then-current coverage gate, the crosswalk (0 unmapped) and model parity passed.
- **Source repairs (November 17-18):** Grand Forks reads the dated document library before its
  media API, and the last known bylaw copies when Cloudflare blocks both on GitHub (owner decision
  November 18); New Westminster follows its migrated bylaw page and PDF endpoint. Both are stored
  live. Maritime retries an HTTP 403 with Chromium, which works locally but not on GitHub.
- **Issue #6 (source problems on GitHub), closed November 19:** the November 19 repairs are
  verified on GitHub. Source Health, then single-utility Monthly Scrapes, stored NL Hydro (23 live,
  from its last known Schedule of Rates) and Heritage Gas (3 live, General Service refreshed).
  Cloudflare still blocks Maritime Electric's page, Chromium retry and PDF on GitHub, so its runs
  store 2 labelled estimates; its 10 live August 2026 tariffs stay published. The monitoring check
  after the Maritime decision below found no remaining problem and closed the issue itself.
- **Maritime manual updates (owner decision November 19):** its estimates now mirror the current
  N-28 values (still labelled Estimated), and the coverage ledger records a manual-update decision
  reviewed by September 1, 2027. Model monitoring accepts Maritime's estimates-only checks until
  then. Locally Maritime stays fully live (10 records).
- **"Coverage complete" is not claimed yet:** the scoped wording will be drafted for the owner's
  approval after the January renewals (owner decision November 19; the four new utilities are now
  stored). Dated checks ahead: twelve ledger reviews fall due December 15 (the strict gate
  fails from December 16 unless they are done); the Alberta Rate of Last Resort term ends
  December 31 and no 2027 term is published yet; 14 ledger audits expire on February 4 and 62 on
  February 27 under the gate's 120-day rule.
- **Phase 8 monitoring:** implemented, published and verified through the existing market workflows
  and deployment. The change log starts from its first verified baseline. Source checks ignore only
  labelled excluded-class estimates (owner decision November 18) and a ledger manual-update
  utility's estimates until its review date (November 19); a monthly-price utility's failure seen
  between the 1st and the run on the 4th waits for that run (November 23).
- **Commercial gas models (method 7D-2, owner decisions November 20 and 23):** small and mid-size
  commercial buildings in all eight gas provinces, in each utility's own unit (m³ or GJ), each
  utility priced on the class whose published limits contain the example customer (Liberty Gas NB
  by its peak month; Centra on the cheaper of its two elective classes). Énergir and Liberty homes
  are now modelled too. Small businesses are modelled at 2,000 kWh with 14 kW and 10,000 kWh with
  40 kW, and every usage level records its decision, what it represents and its sources. The Rate
  Browser shows a dated price's period and tags it "Ended" once that date has passed.
- **Validation:** all 2,748 tests passed on Python 3.11 using `pytest tests`.

The [coverage matrix](docs/phase5_completion_matrix.md) holds the work queue; the
[parser gap report](docs/live_parser_gap_report.md) lists class-level gaps and exclusions.

---

## What This Project Does

1. **Scrapes** utility rate data from official Canadian utility websites.
2. **Stores** everything in a normalized SQLite database that preserves every rate detail — not just a single "cost per kWh" number.
3. **Tracks history** — each stored scrape appends snapshots. Only the Monthly Scrape workflow stores scrapes: it keeps `data/db/rates.db` in the `data-history` GitHub release with dated backups and checks that history only grows; local copies are read-only mirrors (`python scripts/pull_history_db.py`).
4. **Exports** the data as JSON for the GitHub Pages static site.
5. **Serves** a browsable web interface with seven views: **Rate Browser** (multi-select filters, confidence indicators and source attribution), **Rate History** (bar charts of how stored prices changed: tariff and regulated or default prices collected since September 29, 2026, quarterly market averages since 2020 and quarterly model costs; never estimates), **Market Pricing** (observed Ontario and Alberta market history with a monthly chart, table and heatmap), **Representative Models** (typical monthly electricity costs for the ten provinces and the three territories, the territories also after automatic subsidies, and natural gas costs for homes and small and mid-size commercial buildings in each utility's m³ or GJ, without and with tax), **Building Archetypes** (the owner's 68 simulated NECB 2020 buildings in Toronto and Calgary priced for a year at today's stored tariffs, each in the rate class its own simulated load qualifies for; labelled simulated, never a bill), **Across-Canada** (two sub-tabs: residential electricity compared by province and territory, and the **spark gap**: the price of a kWh of electricity against a kWh of each region's usual heating fuel, with the heat pump efficiency that would make up the difference) and **Compare** (two tariffs side by side, never a bill total).
6. **Provides automation** through monthly scraping, separate Pages deployment, non-blocking source-health runs, a twice-monthly Ontario Price archive and market history update, and Alberta market history and model refreshes.

**Scope: building energy costs.** The work supports building energy-cost analysis, including
work informed by **NECB 2025**, plus **single-family homes**: residential and multi-unit
residential, commercial, institutional and building-related industrial service (the tariffs
for building electricity, heating and other building systems). Tariff eligibility still comes
from the utility's published schedule; the project does not determine building-code
applicability or certify NECB compliance. Process-specific farm and oil-field service,
irrigation, NGV fuelling, EV charging, lighting, wholesale/reseller and standby-only service
are **not completion requirements**; schedules already implemented stay as reference. Shared
general-service tariffs may still matter to buildings even when other users can take them.
Record counts include reference-only records, not just building tariffs.

---

## Working Rules

Two rules govern every change to this project:

1. **Never display default values as if they were live.** Only rate values pulled from (or verified against) a live official web source are shown as current. Hardcoded seed/fallback values are a safety net only — they are marked `provenance: "seed"` (with `confidence: unverified`), hidden by default on the site, and revealed only via the labelled **"Show estimated (not live-verified) rates"** toggle. Never present a static default as a live-scraped rate.
2. **Do not assume scope.** If a requirement is unclear or has more than one reasonable interpretation, stop and ask which path to take before proceeding.

The full list of project safeguards is in [AGENTS.md — Project safeguards](AGENTS.md#project-safeguards).

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
│   └── utilities/            ← One scraper module per utility (Ontario distributors share one), plus the package initializer
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
│       ├── saint_john_energy.py ← Saint John Energy (municipal, NB; batch 18)
│       ├── nelson_hydro.py, new_westminster.py, penticton.py, grand_forks.py, summerland.py
│       │                     ← BC municipal utilities (council bylaw schedules; batch 18)
│       ├── summerside_electric.py ← Summerside Electric (municipal, PE; batch 18)
│       ├── naka_power.py     ← Naka Power Utilities (NT; batch 18 continued)
│       ├── medicine_hat.py, lethbridge.py, red_deer.py
│       │                     ← Alberta city utilities (wires + City Rate of Last Resort, or bundled; batch 18 continued)
│       └── ...               ← Other provincial utilities
│
├── pipeline/                 ← Scripts that run the whole process
│   ├── run_scrape.py         ← Main entry: run scrapers → validate → store
│   ├── export_json.py        ← Export database → JSON for the website (also runs the model builder)
│   ├── representative_models.py ← Phase 7 representative models: crosswalk coverage, cost engine, Alberta pairs, estimated market energy
│   ├── archetype_profiles.py ← Reads and checks the simulated BTAP buildings (monthly use, peaks, hourly use with clock times and holidays, market-hour load shapes)
│   ├── archetype_costs.py    ← Building Archetypes costs (method AC-1): each simulated building priced at today's stored tariffs
│   ├── spark_gap.py          ← Spark gap comparison: electricity vs the usual heating fuel, break-even heat pump COP
│   ├── diff_report.py        ← Compare two scrape runs to see changes
│   └── validate.py           ← Data quality checks
│
├── schema/                   ← Database definition
│   ├── create_tables.sql     ← SQL that creates all tables
│   └── schema_diagram.md     ← Visual diagram of the schema
│
├── data/                     ← Data files
│   ├── btap/                 ← Simulated NECB 2020 buildings (68 runs, Toronto and Calgary): results workbook and 15-minute timestep CSVs; other outputs ignored
│   ├── db/                   ← SQLite history database: read-only mirror of the CI copy (backups/ is git-ignored)
│   ├── exports/              ← CSV/Excel exports (optional)
│   ├── excel/                ← Audit reference files (not system of record, git-ignored)
│   ├── market/               ← Ontario and Alberta market history kept in git (outside the database)
│   │   ├── ontario_price_hourly.csv   ← Hourly Ontario Price archive (DA-OZP + LFDA) since July 11, 2026
│   │   ├── ontario_total_hourly.csv   ← Combined hourly energy + Class B GA, cents/kWh, with explicit gaps
│   │   ├── ontario_total_hourly_2020_2025.csv ← Requested fixed historical window
│   │   ├── ontario_total_monthly.csv ← Combined monthly reference prices, cents/kWh
│   │   ├── ontario_total_metadata.json ← Method, warnings and source fingerprints
│   │   ├── ieso_raw/                ← Permanent unverified official report captures and SHA-256 index
│   │   ├── ontario_market_monthly.csv ← Permanent monthly energy + Class B GA history since January 2020
│   │   ├── hoep_hourly.csv   ← Legacy hourly HOEP, January 2020-March 2025 (imported once)
│   │   ├── alberta_pool_hourly.csv    ← Hourly AESO pool prices (permanent raw history)
│   │   └── alberta_market_monthly.csv ← Permanent monthly Alberta pool-energy history
│   ├── models/               ← Phase 7 representative model inputs
│   │   ├── crosswalk.json    ← Ordered rules: live record → model key or exclusion reason; Alberta pairs
│   │   ├── usage_levels.json ← Usage levels (some by province), TOU/ULO shares, reference-customer charges, simulated profile
│   │   ├── block_periods.json ← Reviewed periods for block thresholds printed without one
│   │   ├── percentage_riders.json ← Reviewed territorial percentage riders (what each applies to)
│   │   ├── subsidies.json    ← Reviewed territorial subsidies (applied or only named)
│   │   ├── spark_gap.json    ← Reviewed spark gap inputs: points, comparison fuels, heating values, efficiencies, heat pump COPs
│   │   ├── archetypes.json   ← Reviewed archetype cost inputs: rate class rules, clock periods, holidays, ratchet, loss factors
│   │   └── taxes.json        ← Sales taxes and automatic point-of-sale rebates (also the heating-oil lines of the spark gap)
│   ├── fuel/heating_oil_prices.json ← Statistics Canada monthly heating-oil prices for the spark gap (every month kept)
│   ├── sources/registry.json ← Master list of where to find rate data
│   ├── sources/coverage_ledger.json ← Coverage audit ledger read by the coverage gate
│   └── inventory/            ← Full utility inventory
│
├── site/                     ← Static website (deployed to GitHub Pages)
│   ├── index.html            ← Seven views, including Rate History, Building Archetypes, Across-Canada and two-tariff Compare
│   ├── css/style.css         ← Styles inc. multi-select filters, heatmap, confidence
│   ├── css/models.css        ← Representative Models styles, incl. the estimated market energy note
│   ├── css/across-canada.css ← Residential national comparison table
│   ├── css/rate-history.css  ← Rate History charts, tables and phone layout
│   ├── css/spark-gap.css     ← Across-Canada spark gap sub-tab
│   ├── css/archetypes.css    ← Building Archetypes table, detail panel and phone cards
│   ├── js/app.js             ← SPA logic: filters, cards, modal, market viz
│   ├── js/models.js          ← Representative Models, assumptions and shared lazy data loader
│   ├── js/across-canada.js   ← Residential comparisons using published model totals only
│   ├── js/rate-history.js    ← Rate History: recent changes and hand-built SVG history charts
│   ├── js/spark-gap.js       ← Across-Canada sub-tabs and the spark gap view (reads spark_gap.json only)
│   ├── js/archetypes.js      ← Building Archetypes tab (reads archetype_costs.json only)
│   └── data/                 ← Nine pipeline exports plus separately maintained market/audit data
│       ├── rates.json        ← All tariff/component data
│       ├── utilities.json    ← Utility metadata
│       ├── summary.json      ← Provincial summaries
│       ├── missing.json      ← Known data gaps
│       ├── missing_classes_report.json  ← Customer class coverage audit
│       ├── representative_models.json   ← Phase 7 models (provinces and territories; Representative Models tab)
│       ├── model_change_history.json    ← Public model change log (pipeline/model_monitoring.py --record)
│       ├── model_cost_quarterly.json    ← Quarter-end model costs for Rate History, rebuilt from the change log
│       ├── spark_gap.json               ← Spark gap comparison (pipeline/spark_gap.py, rebuilt after every model refresh)
│       ├── archetype_costs.json         ← Simulated building costs (pipeline/archetype_costs.py, rebuilt after every model refresh)
│       ├── rate_history_revisions.json  ← Same-date price corrections found in the database snapshots (export)
│       ├── rate_history_series.json     ← Reviewed regulated and default price series for Rate History
│       ├── rate_history_events.json     ← Reviewed regulator and government decisions marked on its charts
│       ├── market_pricing_ontario.json  ← Rolling 60-month market history + observed-hours bins (scripts/build_ontario_market.py)
│       ├── market_pricing_alberta.json  ← Alberta market history + observed-hours bins (scripts/build_alberta_market.py)
│       ├── market_quarterly_ontario.json, market_quarterly_alberta.json ← Complete-quarter market averages (the same builders)
│       ├── market_structure_notes.json  ← All-province market research
│       └── source_review_report.json    ← Source URL audit report
│
├── scripts/                  ← Market data builders, database history tools and the graphify hook helper
│   ├── build_ontario_market.py    ← Rolling five-year Ontario market history (Ontario Price Archive workflow)
│   ├── archive_ontario_price.py   ← Extends the hourly Ontario Price archive (Ontario Price Archive workflow)
│   ├── preserve_ieso_reports.py  ← Saves raw IESO reports before any price-validation failure
│   ├── export_ontario_totals.py  ← Combines hourly/monthly energy + Class B GA without filling gaps
│   ├── build_alberta_market.py    ← Alberta AESO market history, checked against monthly summaries (Market Benchmarks workflow)
│   ├── market_quarterly.py        ← Shared complete-quarter averages that both market builders write for Rate History
│   ├── generate_market_pricing.py ← Legacy 6A HOEP 2020-2024 surface (manual; its readers are reused by the builder)
│   ├── check_db_history.py        ← Monthly Scrape check: database integrity, history only grows
│   ├── coverage_gate.py           ← Live-rate coverage gate: live output, audit ledger, deferred and monitored items (Monthly Scrape reports it)
│   ├── pull_history_db.py         ← Downloads the CI history database into a read-only local mirror
│   ├── fetch_heating_oil.py       ← Statistics Canada heating-oil prices for the spark gap (Monthly Scrape)
│   └── graphify_hook.py           ← Optional graphify post-commit hook helper (see Graphify below)
│
├── tests/                    ← Regression tests (run them with: pytest tests)
│   └── fixtures/             ← Source-derived fixtures and frozen export samples; other tests also use inline text
├── docs/                     ← Guides and reference
├── .github/
│   ├── workflows/            ← GitHub Actions automation
│   ├── copilot-instructions.md ← Development workflow for AI agents
│   └── instructions/         ← Area rules for AI agents
├── graphify-out/             ← Code knowledge graph (optional developer tool; see Graphify below)
│
├── README.md                 ← This file
├── AGENTS.md                 ← Step-by-step guide for maintainers
├── requirements.txt          ← Python dependencies
├── requirements-graphify.txt ← Pinned graphify version (optional developer tool)
└── .graphifyignore           ← Paths graphify leaves out of the code graph
```

---

## Common Commands

Stored scrapes are made only by the Monthly Scrape workflow on GitHub; on your computer,
use `--dry-run` and get the history with `python scripts/pull_history_db.py`.

| What you want to do | Command |
|---|---|
| Get the CI history database (read-only mirror) | `python scripts/pull_history_db.py` |
| Initialize an empty practice database | `python -m pipeline.run_scrape --init-db` |
| Test-scrape all active utilities (nothing saved) | `python -m pipeline.run_scrape --dry-run` |
| Test-scrape one utility (nothing saved) | `python -m pipeline.run_scrape --utility "BC Hydro" --dry-run` |
| Test-scrape all utilities in a province (nothing saved) | `python -m pipeline.run_scrape --province ON --dry-run` |
| Export JSON for the website | `python -m pipeline.export_json` |
| Validate data quality | `python -m pipeline.validate` |
| Compare two scrape runs (default the two latest; only the utilities the newer run scraped) | `python -m pipeline.diff_report [--run1 ID --run2 ID]` |
| Check the representative-model crosswalk | `python -m pipeline.representative_models --coverage` |
| Build the representative models (summary; `--output PATH` writes the JSON) | `python -m pipeline.representative_models --build` |
| Check the spark gap comparison without writing | `python -m pipeline.spark_gap --dry-run` |
| Check the building archetype costs without writing | `python -m pipeline.archetype_costs --dry-run` |
| Check Statistics Canada's heating-oil prices without writing | `python scripts/fetch_heating_oil.py --dry-run` |
| Rebuild the rolling Ontario market history (downloads IESO files) | `python scripts/build_ontario_market.py` |
| Rebuild the legacy 2020-2024 market surface (Phase 6A, manual; writes `logs/market_pricing_legacy_2020_2024.json` by default) | `python scripts/generate_market_pricing.py [--output PATH]` |
| Extend the hourly Ontario Price archive (downloads IESO files) | `python scripts/archive_ontario_price.py` |
| Rebuild combined Ontario cents/kWh CSVs from retained data | `python scripts/export_ontario_totals.py` |
| Check raw IESO preservation without writing | `python scripts/preserve_ieso_reports.py --dry-run` |
| Check the Alberta market history without publishing (downloads AESO files) | `python scripts/build_alberta_market.py --dry-run` |
| Record database statistics (the Monthly Scrape history check) | `python scripts/check_db_history.py stats --db data/db/rates.db --out stats.json` |
| Check live-rate coverage (the coverage gate) | `python scripts/coverage_gate.py` |
| Run tests | `pytest tests` |
| Serve the website locally | `python -m http.server --directory site 8000` |
| See verbose output (nothing saved) | `python -m pipeline.run_scrape --dry-run --verbose` |
| Check graphify, its hook and the code graph (optional) | `python scripts/graphify_hook.py status` |
| Install the graphify post-commit hook (optional; once per checkout) | `python scripts/graphify_hook.py install` |
| Rebuild the code graph from scratch (optional) | `python scripts/graphify_hook.py build` |
| Catch up the code graph by hand, in its own commit (optional) | `python scripts/graphify_hook.py refresh --commit` |

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

**Representative models are derived, never stored as rates.** Every export runs
`pipeline/representative_models.py`, which uses the reviewed inputs in `data/models/`
(crosswalk, usage levels, block periods, taxes, and the territories' percentage riders and subsidies)
to work out, for each province and territory, the median monthly electricity cost of its utilities'
live tariffs at set example usage levels, before and after sales taxes and automatic rebates (and, for
the territories, after automatic subsidies, before tax), and writes `site/data/representative_models.json`. Models are labelled
modeled, are never a bill and never count as live coverage. [AGENTS.md](AGENTS.md) describes
their inputs and rules.

---

## How to Add a New Utility

See [docs/adding-a-utility.md](docs/adding-a-utility.md) for a detailed guide.

**Short version:**
1. Create a new file in `scrapers/utilities/`.
2. Write a class that inherits from `BaseScraper` and implements `scrape()`.
3. Add the utility to `data/sources/registry.json`.
4. Test with `python -m pipeline.run_scrape --utility "Your Utility" --dry-run`. After the code is pushed, the Monthly Scrape workflow stores it (start it by hand with the `utility` input, or wait for the 1st).

**A utility counts as done** when its standard published classes relevant to building energy
costs (including single-family homes) are accounted for with exact source, date, unit and
component context; source-derived fixtures prove extraction and failure handling; an
official-source dry run has been inspected; storage and export keep every component and
earlier snapshot; and the coverage ledger (`data/sources/coverage_ledger.json`) is updated.
Special, negotiated and closed-to-new schedules are identified where applicable. Unsupported
building classes are recorded as gaps, never invented; non-building services are explicit
exclusions. A generic verifier test or seed-only output is not a working parser.

---

## How Monthly Updates Work

The [Monthly Scrape workflow](.github/workflows/scrape.yml) runs on the 1st at 08:00 UTC, on the
4th at 08:00 UTC for only the utilities flagged `monthly_price_refresh` in the registry (their
monthly price is usually posted after the 1st; owner decisions November 20 and 23), or on manual
dispatch, with optional inputs for one `utility` or one two-letter `province` (not both; the inputs
reach the shell through environment variables). Before anything is installed, the runner's own
Python checks the inputs against the registry: utility names ignore accents and case, and a
mistyped name or code stops the run with what to type instead. It is the **only writer** of the
history database `data/db/rates.db` (owner decision), kept as asset `rates.db` of the
`data-history` GitHub release:

1. **Restore:** if the release exists, the download must succeed and match the asset's SHA-256
   digest, or the run stops; only a missing release (HTTP 404) starts a new database.
   `scripts/check_db_history.py stats` records integrity-checked statistics right after the
   restore.
2. **Test, scrape, validate, export:** deterministic tests, the scrape (all active utilities, one
   utility, one province or, on the 4th, the monthly-price group), validation, `git pull --ff-only
   origin main`, Statistics Canada's heating-oil prices for the spark gap (a failed download keeps
   the last file) and the JSON export (models, then the spark gap and the archetype costs),
   and a check that rejects empty exports. Synchronizing first makes queued runs use the latest
   committed inputs; generated files are never rebased onto newer inputs.
3. **Check before upload:** `scripts/check_db_history.py verify` requires SQLite `integrity_check`
   "ok", no fewer snapshots, tariff versions or scrape runs, and every earlier snapshot unchanged
   (a digest over all earlier rows). It posts a public "Database history" notice on the run page.
4. **Upload:** a dated gzip backup (`rates-YYYY-MM-DD.db.gz`), then `rates.db`. The bot then
   commits `site/data/` and `data/fuel/` with a plain `git push`, and dated backups are pruned to the newest 12.
5. **Failure issue:** a failed step opens a GitHub issue with the test, scrape, validation,
   database-history and diff output; a failed check uploads nothing.

Each scrape run also posts public notes on its run page: the live, estimated and invalid
totals with any failed or estimates-only utility, and a report-only "Coverage gate" result that
never blocks the save. The step summary and full logs need a GitHub sign-in.

Local machines never upload: `python scripts/pull_history_db.py` downloads the public release
copy, checks its digest and keeps the old local copy in `data/db/backups/` (git-ignored). To store
new data, push the code and start Monthly Scrape (optionally for one utility or one province), or
wait for the 1st. `python -m pipeline.run_scrape --province XX` skips merged and retired registry
entries. **Risk:** deleting the `data-history` release deletes `rates.db` and every backup.

**Other workflows:**

- [Deploy Site](.github/workflows/deploy.yml) publishes the site on push or manual dispatch,
  and by itself after each successful Monthly Scrape, Ontario Price Archive or Market Benchmarks
  run; it checks out `main`. A failed data run that still committed new data needs a manual
  deploy. A build job uploads the site and a separate deploy job publishes it (GitHub's own
  layout; deploying in the upload's job sometimes found no upload, November 20-23), so a failed
  deploy can be fixed with "Re-run failed jobs" within a day.
- [Source Health](.github/workflows/source-health.yml) runs a non-blocking dry run on the 15th
  and uploads its log without publishing; it installs Playwright Chromium. Read the
  [source-health troubleshooting note](AGENTS.md#source-health-is-green-but-a-source-failed)
  before treating a green run as healthy live coverage.
- [Ontario Price Archive](.github/workflows/ontario-price-archive.yml) runs at 06:00 UTC on the
  1st and 15th and after relevant code pushes. It first commits the raw IESO reports, then
  extends and commits `data/market/ontario_price_hourly.csv`, then runs
  `scripts/build_ontario_market.py` (also when the archive step failed, using the archive
  already committed), the combined-price export, the models, the spark gap and the archetype costs,
  and commits those separately.
  A failure opens an issue whose title says which part failed.
- [Market Benchmarks](.github/workflows/market-benchmarks.yml) runs after the Monthly Scrape and
  Ontario Price Archive workflows and after relevant code or model-input pushes. It publishes
  the Alberta market history and refreshes the representative models, the spark gap and the
  archetype costs without touching the database, and opens an issue if it fails (a failed spark gap
  or archetype build only keeps the previous file; model monitoring reports it).
- [Model Monitoring](.github/workflows/model-monitoring.yml) is a non-blocking follow-up to the
  existing data workflows and Source Health, not a new daily job. It checks explicit refresh
  evidence and reports input/refresh problems; ordinary changes appear in the model change log.
  See the [maintainer guide](AGENTS.md#model-monitoring-opened-an-issue-or-history-is-unavailable)
  for local checks and recovery.

The three data workflows take turns publishing. Every workflow runs on `ubuntu-24.04`, and steps
that pipe output into `tee` run under `bash -o pipefail`, so a failing command still fails its
step. GitHub Pages must use **GitHub Actions** as its source, and `workflow_run` triggers fire
only from the default branch.

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
**latest 60 complete months** (owner decision): the energy price is the legacy Hourly Ontario
Energy Price (HOEP) up to April 2025 and the Ontario Price after it, plus the actual monthly
Class B Global Adjustment (GA). Full cost = energy + Class B GA. It is observed history for
comparison, never a tariff, a bill or a forecast.

**HOEP retired:** the IESO retired the HOEP on April 30, 2025. Since May 1, 2025 market-billed
customers pay the Ontario Electricity Market Price (OEMP, "the Ontario Price": the Day-Ahead
Ontario Zonal Price plus the Load Forecast Deviation Adjustment) plus GA. An always-visible note
on the dashboard says so and links to the IESO's current Ontario market prices. The page shows
the old and new markets as one continuous total because energy plus Class B GA stayed similar
after the change while energy alone did not: GA moves opposite to the energy price.

**Complete months:** a month enters the window when it has ended, its energy value is validated
(legacy HOEP: the hourly mean matches the IESO HOEP Monthly Averages report within 0.01 $/MWh;
Ontario Price: listed in the IESO monthly table, and a month the archive covers must match it
within 0.01 $/MWh) and its Class B GA actual rate is published (IESO Data Directory workbook or
monthly GA reports; where both exist they must agree within 0.005 $/MWh). April 2025 uses the
report value and has no observed hours, because the April mean of the IESO yearly hourly file
(39.181 $/MWh) disagrees with the monthly report (39.22).

**Heatmap (observed hours only, owner decision):** 576 bins (12 months x weekday/weekend x 24
hours, hour beginning EST; a statutory holiday counts as the weekday it falls on) built only
from hours with a recorded price; each cell shows how many hours it averages. The hourly Ontario
Price from May 1, 2025 to July 10, 2026 is no longer published (the IESO keeps about 90 days of
daily files, and its website's chart data reaches back only about 10 days), so that gap is
disclosed and never filled with modelled hours. As archived months enter the window, the
Ontario Price share of the heatmap grows.

**Files:**
- `data/market/ontario_market_monthly.csv`: the permanent monthly history since January 2020:
  era, energy (arithmetic and demand-weighted), Class B GA, total, sources and observed hours.
  It is never trimmed; a month may be revised only within 6 months of its end.
- `data/market/hoep_hourly.csv`: legacy hourly HOEP, January 1, 2020-March 31, 2025, imported
  once with `--refresh-hoep`; CI never downloads legacy HOEP files.
- `data/market/ontario_price_hourly.csv`: the hourly Ontario Price archive (below).
- `site/data/market_pricing_ontario.json` (schema 2, `derivation_method`
  `observed_rolling_60m_hoep_oemp_ga`): metadata (window, eras, gap, change date, source codes,
  cross-checks), the 60 monthly records and the 576 bins with `hours_hoep` and `hours_oemp`.

**Updating:** `scripts/build_ontario_market.py` runs in the Ontario Price Archive workflow after
the archive commit (`--dry-run` checks everything without writing; `--help` lists the other
options). In CI it downloads only the IESO monthly table page, the GA workbooks and the monthly
GA reports. It fails closed: on any missing or inconsistent input it writes nothing and exits
with an error, and a run without new data leaves every file unchanged.
`scrapers/utils/market_pricing.py` and the site accept only observed files (this rolling method
or the legacy one below); otherwise the site shows a "not available" notice.

**Ontario Price archive:** `scripts/archive_ontario_price.py` keeps what is still published:
`data/market/ontario_price_hourly.csv` holds one row per hour from July 11, 2026 with DA-OZP,
LFDA, OEMP, the report version and the LFDA status (Final or Preliminary). A blank LFDA hour
stays blank, never zero (the IESO's published monthly LFDA averages leave blanks out). Every
complete month must match the IESO's monthly Ontario Price table within 0.01 $/MWh for DA-OZP,
LFDA and OEMP (owner decision: all three strict); otherwise the validated CSV is unchanged and
the workflow opens an issue.

**Raw IESO reports:** before any price check, the workflow commits the original daily DA-OZP and
yearly LFDA reports under [data/market/ieso_raw/](data/market/ieso_raw/)
(`scripts/preserve_ieso_reports.py`). Original bytes are compressed, SHA-256 checked and kept by
content hash; new revisions and even malformed responses never overwrite older captures. Raw
files are **unverified** source evidence, not prices to use in calculations.
`scripts/archive_ontario_price.py --raw-dir data/market/ieso_raw --no-site-api` can recover
retained daily reports after the IESO removes them, while LFDA and monthly checks still require
live sources. A failed validation does not undo the raw commit. If saving to GitHub itself
fails, the run keeps a recovery artifact for 90 days and opens an issue: download it and repair
the failure promptly. This protects future captures but cannot recover the old hourly gap.

**Combined energy + Class B GA prices** (no need to join energy and GA yourself):

| File | Contents |
|---|---|
| [2020-2025 hourly totals](data/market/ontario_total_hourly_2020_2025.csv) | All **52,608** hourly slots, in **CAD cents/kWh**, IESO hour-ending 1-24 EST |
| [Permanent hourly totals](data/market/ontario_total_hourly.csv) | January 2020 onward; extended with the archive |
| [Permanent monthly totals](data/market/ontario_total_monthly.csv) | Published arithmetic energy + Class B GA averages, in cents/kWh |
| [Method, sources and coverage](data/market/ontario_total_metadata.json) | Formula, source fingerprints, status definitions and caveats |

`total_cents_per_kwh = (hourly energy $/MWh + monthly Class B GA $/MWh) / 10`. These are
**energy-plus-GA totals, not complete bills**: delivery, losses, other fees and taxes are
excluded. Missing totals stay blank: the 2020-2025 file has 46,728 numeric hourly totals and
5,880 missing hours (May-December 2025). The separate `monthly_average_total_cents_per_kwh`
column is a **monthly reference**, never an hourly observation. April 2025's 720 official HOEP
hours appear only in these exports, flagged `observed_monthly_mismatch` (see "Complete months"
above); the original [2025 IESO report](data/market/PUB_PriceHOEPPredispOR_2025_v119.csv) is
preserved byte-for-byte. These files do not change the stricter site heatmap or the model
calculations. Rebuild them offline with `python scripts/export_ontario_totals.py` (`--dry-run`
writes nothing); the Ontario Price Archive workflow refreshes them after each market build.

**Legacy surface (Phase 6A):** `scripts/generate_market_pricing.py` (manual) still builds the
fixed 2020-2024 HOEP surface from the IESO yearly hourly reports (`PUB_PriceHOEPPredispOR_YYYY`)
and the Data Directory GA workbook, cross-checking all 60 monthly means against the HOEP Monthly
Averages report; the rolling builder reuses its readers. By default it writes the git-ignored
scratch file `logs/market_pricing_legacy_2020_2024.json`, so it cannot replace the rolling site
file by accident. GA defaults the owner may change, kept in both builds: April-June 2020 use the
published capped 115 $/MWh (provincial emergency order; unadjusted 150.57, 147.18 and 128.40),
the 2021 actual rates exclude the separate 2021 recovery rates (5.01-7.09 $/MWh), and holidays
count as weekdays.

### Alberta Deregulated Market

Alberta distribution (wires), default retail and AESO wholesale observations are separate data
sources and stay separate records. The four wires utilities (ENMAX Power, ATCO Electric, EPCOR
Distribution, FortisAlberta) keep distribution and transmission (System Access Service) charges
as separate components and current riders as dated components. The **Rate of Last Resort**
(RoLR), which replaced the Regulated Rate Option on January 1, 2025, is live for its three
providers (Direct Energy Regulated Services, ENMAX Energy and EPCOR Energy Alberta): a fixed
energy price for the term ending December 31, 2026, cross-checked with the Utilities Consumer
Advocate (UCA) default-rates table. These records fail closed after the term ends until the next
term is published; old RRO seeds remain labelled history. Competitive retail contracts are not
included. AESO's pool price is a live market reference with no stored number.

Three city utilities follow their own published rates (batch 18 continued, November 19, 2026).
Lethbridge and Red Deer own their wires and publish their area's Rate of Last Resort price
themselves; no UCA cross-check exists for them, and the City's term must cover the run date.
Medicine Hat generates, delivers and sells electricity, so each record bundles delivery with the
City's own default energy price, which is published month by month.

**Alberta market history:** `scripts/build_alberta_market.py` reads the official AESO hourly
pool prices and checks every monthly arithmetic average against AESO's **Pool Monthly Summary**
within $0.01/MWh. It keeps permanent raw hourly (`data/market/alberta_pool_hourly.csv`) and
monthly (`data/market/alberta_market_monthly.csv`) history and publishes
`site/data/market_pricing_alberta.json` for the Market Pricing page's Alberta region: 60 complete
months and 576 heatmap bins from observed hours. Published AESO hour-ending labels keep the
skipped spring hour and the repeated autumn `02*` hour; they are not Ontario EST timestamps.
Missing hours never become zero, and Alberta never uses Ontario's GA. Every refresh rechecks all
archived months; a changed archived price stops publication for source review instead of
guessing a correction. The Market Benchmarks workflow publishes it; check it without publishing
with `python scripts/build_alberta_market.py --dry-run`. The owner confirmed AESO permission for
public raw hourly archives and derived charts and benchmarks; the grant itself was not
independently inspected.

### Market Prices in Tariffs and Models

- **Tariffs never hold market averages.** A tariff part that follows a market price (for
  example Ontario non-RPP demand-class energy, EPCOR Distribution's operating reserve and AESO's
  pool price) is stored with a market reference and no number; the site shows it as
  "Variable". For Ontario demand classes, Class A Global Adjustment (by peak demand factor) is a
  conditional note.
- **Representative models** never guess a market price. The Ontario and Alberta 50-499 kW and
  500-4,999 kW models add an estimate, labelled as such (below); the 5,000 kW and over models, and
  any model whose estimate input fails, show delivery charges with *market energy pending*. Alberta's Rate of Last Resort (in the provider pairs and the Lethbridge and Red Deer
  city units) applies only below 250,000 kWh a year, the RoLR limit.
- **Historical market benchmark (method 7C-4):** for Ontario and Alberta medium and large
  commercial demand models, a separate figure adds the average energy price of 60 complete
  months (each month counts equally) to the modeled delivery charges. Ontario adds actual Class
  B GA; Alberta uses pool energy alone. Energy is added before zone aggregation and taxes.
  Losses, retail fees, Class A and unpriced conditional charges are not included, and a
  province's benchmark is unavailable when its history is missing or invalid or its 60-month
  window is more than four months old. It is **not a customer-profile-weighted bill or
  forecast**, does not replace the base model and is not used in the Across-Canada comparison. On
  the Representative Models page it is the "same use every hour" comparison beside the estimate.
- **Estimated market energy (method 7S-2, November 25, owner decisions 119-123):** for the two
  larger business sizes in Ontario and Alberta, the main table adds market energy priced with one
  general load shape: the owner's simulated NECB 2020 buildings (`data/btap/`) whose usual monthly
  peak is in the model's size range (21 in Toronto and 20 in Calgary for 50-499 kW, 5 each for
  500-4,999 kW), both heating fuels, each scaled to the same yearly use and averaged hour by hour, and
  priced over the 60 observed months of the market heatmap (Ontario with actual Class B GA, Alberta
  pool energy only). The price times the example customer's kWh is added to every contributor's
  delivery cost before tax. The page labels it estimated and lists its assumptions, the
  same-use-every-hour price and every building with its own price. It never counts as live coverage;
  Ontario's published loss factors are stated, not applied, as in every model. A failed input (a stale
  or invalid market history, unreadable buildings) leaves *market energy pending*, and model monitoring
  reports it. It replaced the opt-in estimate of method 7S-1 (which used the median building price)
  and, before it, the 7E made-up business-hours profile.
- **Example customers (owner decision 120, November 25):** every province's 50-499 kW and
  500-4,999 kW models use 25,000 kWh at 100 kW and 250,000 kWh at 1,000 kW, the size of the simulated
  buildings in those ranges (about 255-260 kWh per kW of peak) and Hydro-Qu?bec's own 100 kW
  comparison customer. Ontario's bill-impact customers of these classes use more per kW (40,000 and
  500,000 kWh were used until November 25); the levels document that difference.
- Real (metered) commercial load profiles are not qualified yet, so the estimate uses simulated
  buildings and no metered-profile bill is claimed.

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
→ Run `python scripts/pull_history_db.py` to download the read-only copy of the database (or `python -m pipeline.run_scrape --init-db` for an empty practice database).

### A scraper fails with a connection error
→ The utility's website may be down or may have changed its URL. Check the `source_url` in the registry.

### Validation warnings about high values
→ The validation catches unreasonable rates (like $100/kWh). Check if the scraper is parsing correctly or if the utility actually has that rate.

### The website shows no data
→ Make sure you have the database and have run `python -m pipeline.export_json`; the site reads from `site/data/rates.json`. Serve the site over HTTP as in the [Quick Start](#quick-start) instead of opening the file directly.

### Building Archetypes says the costs are not available, or a building is "Not computable"
→ "Not available": `site/data/archetype_costs.json` is missing or its last build failed; run `python -m pipeline.archetype_costs --dry-run` to see why (model monitoring's `archetype_costs` check reports it too). "Not computable": one of that building's prices has ended or is not stored yet, and its detail panel gives the reason; the next export after the price is stored brings it back. Details: [AGENTS.md](AGENTS.md), "Building Archetypes says the costs are not available".

### The Ontario Price Archive workflow opened an issue
→ A monthly check against the IESO's published Ontario Price table failed, or an official file could not be read, so the validated archive was not changed (raw reports are saved separately before the checks). Run `python scripts/archive_ontario_price.py --no-site-api --raw-dir data/market/ieso_raw --dry-run` to see which month or file failed, and fix it soon: the IESO deletes each daily price file after about 90 days. If the issue says raw report preservation failed, download the run's `ieso-raw-recovery` artifact promptly.

### An issue says "Ontario market history update failed"
→ The archive part of the run was saved; only the market history build failed closed and wrote nothing, so the Market Pricing page keeps its previous data. Run `python scripts/build_ontario_market.py --dry-run` to see the reason (for example a month that disagrees with the IESO table) and fix it before the next run on the 1st or 15th.

### The database history check failed
→ The Monthly Scrape found a problem with `data/db/rates.db` (a failed restore or digest, a failed integrity check, fewer snapshots, tariff versions or scrape runs, or a changed earlier snapshot) and uploaded nothing, so the release copy is unchanged. Read the "Database History" part of the issue. Do not upload a database by hand: fix the cause, then start Monthly Scrape again.

### Market Benchmarks opened an issue
→ A step of the run failed (its tests, the Alberta market history build or the model refresh), so nothing new was published and the site keeps its previous data. A missing hour, a changed source format, a disagreement with AESO's official monthly price or a changed already-archived price stops publication on purpose. Run `python scripts/build_alberta_market.py --dry-run` to see the reason. Do not overwrite archived evidence or guess a correction.

### An issue says "Rates not updated in a year"
→ Not an error: the quarterly report lists official documents whose prices have not changed for more than a year. Check each one, then record a dated `freshness_review` finding (`legitimate`, `parser_fixed` or `moved_on`) in `data/sources/coverage_ledger.json`, or fix the scraper; the issue closes itself once every listed utility is updated or reviewed. Step-by-step: [AGENTS.md](AGENTS.md), "Rates not updated in a year".

### A workflow log warns that `git` exited with code 128
→ Harmless: it comes from the checkout clean-up, because two committed `.claude/worktrees` links have no `.gitmodules` entry.

More problems and step-by-step fixes are in [AGENTS.md](AGENTS.md) ("What to Do When Something Breaks").

---

## Graphify (optional developer tool)

[graphify](https://graphify.com) turns the code into a searchable knowledge graph in
`graphify-out/` that AI assistants query before reading files. You do not need it to scrape,
test or publish rates, and GitHub Actions never installs it.

**Install once per computer.** You need Python 3.10 or newer, Git and
[uv](https://docs.astral.sh/uv/). The version is pinned in
[requirements-graphify.txt](requirements-graphify.txt):

    uv tool install graphifyy -c requirements-graphify.txt   # recommended: isolated install
    pip install -r requirements-graphify.txt                  # alternative: inside the project's virtual environment

Restart VS Code afterwards so new terminals and AI agents find `graphify`. For the `/graphify`
chat skill, run `graphify vscode install`, then `git restore .github/copilot-instructions.md`
(the installer adds a section that this repository already covers).

**Turn on automatic updates once per checkout.**

    python scripts/graphify_hook.py install   # adds the post-commit hook only
    python scripts/graphify_hook.py status    # checks the graphify version, the hook and the graph

After each commit that changes code, the hook updates the graph and records it in a separate
commit named `chore(graphify): refresh code graph for <commit>`. It never pushes. Commits that
change only documentation skip it. If other uncommitted changes could have reached the graph,
it refreshes the files but leaves them uncommitted. Skip it once by setting
`GRAPHIFY_SKIP_HOOK=1`. A code commit takes longer while the graph updates (up to about a
minute on a slow Windows machine).

**What is in the graph.** Application code only: `.graphifyignore` leaves out tests, the data
folders, the database schema and workflow YAML. Communities get automatic names; no AI model is
called. The views are `graph.html` (interactive graph), `GRAPH_TREE.html` (file tree),
`GRAPH_CALLFLOW.html` (call flow by project area), `wiki/index.md` and `GRAPH_REPORT.md`.

**Other commands.** `python scripts/graphify_hook.py build` rebuilds the graph from scratch
(needed after changing the pin or `.graphifyignore`; review the result, then commit
`graphify-out/`). `python scripts/graphify_hook.py refresh --commit` catches up by hand, and
`uninstall` removes the hook. To upgrade graphify, change the pin, reinstall, run `build` and
`python -m pytest tests/test_graphify_hook.py`, then commit.

---

## Data Format Recommendation

**Primary storage: SQLite** — because it's a single file, needs no server, supports full SQL queries, and works on every platform.

**Static site consumption: JSON** — the browser can't query SQLite directly, so we export to JSON files that the JavaScript app loads.

**Optional: CSV exports** — for people who want to open data in Excel or Google Sheets.

---

## Roadmap

One line per phase; sub-phase detail and the work queue are in the
[coverage matrix](docs/phase5_completion_matrix.md).

- **Earlier phases (foundations)** — done: scraper framework, granular schema, registry, validation, history snapshots, JSON export and the website.
- **Phase 5: Live Parser Completion** — in progress: the Batch 18 additions are published (municipal utilities in NB, BC and PE on November 18; Naka Power and the Alberta cities on November 19) and issue #6 is closed; the scoped coverage-complete claim will be drafted for owner approval after the January renewals, and remaining building-catalogue gaps and additions are tracked in the coverage matrix.
- **Phase 6: Market Integration** — in progress (6A, 6B, 6C and 6D done; 6E gas supply-price freshness: Énergir's monthly prices and period end dates for the other gas utilities done November 20, and the monthly-price run on the 4th added November 23 (first run December 4)).
- **Phase 7: Representative Models** — in progress (7A, 7B, 7C and 7F done, including the separate historical market benchmarks of method 7C-4; the Ontario and Alberta 50-499 kW and 500-4,999 kW models include market energy estimated from simulated building load shapes since method 7S-2 (November 25), labelled estimated and never a bill; 7D gas done in each utility's native m³ or GJ: homes as method 7D-1 and commercial general service for small and mid-size buildings as method 7D-2, November 23; contract, interruptible and seasonal gas classes come later with their own decision; the territories were added November 24 as method 7T-1, homes and small businesses, before and after automatic subsidies). The check for rates not updated in a year was added November 24.
- **Phase 8: Representative Model Refresh Automation** — done and verified in CI and on the deployed site. Public change history and problem-only monitoring follow the [approved policy](.github/instructions/representative-models.instructions.md#change-monitoring-phase-8-owner-decision-2026-11-17).
- **Phase 9: Product Follow-up** — started (residential Across-Canada comparison done; the Rate History tab of historical charts built November 24, using data collected since September 29, 2026 plus the stored market history; the Building Archetypes tab pricing the 68 simulated NECB 2020 buildings in Toronto and Calgary at the stored tariffs, labelled simulated and kept out of the models, built November 26 as method AC-1). The spark gap comparison by region is done (Across-Canada sub-tab, November 26). Planned later: AI-ready exports, a bill calculator or API and commercial/gas comparisons.

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
| Code knowledge graph (optional dev tool) | graphify, pinned in requirements-graphify.txt | Lets AI assistants navigate the code |

---

## License

This project collects publicly available rate data from official utility websites. The data itself belongs to the respective utilities and regulators. This tool is for informational and educational purposes.

---

## Contributing

The immediate priority is **complete existing live parsers and their source-derived
fixtures**, not add more seed-only coverage. See [docs/adding-a-utility.md](docs/adding-a-utility.md)
and the [coverage matrix](docs/phase5_completion_matrix.md).
