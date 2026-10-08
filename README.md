# Canada Utility Costs

**Browse electricity and natural gas rates across all Canadian provinces and territories.**

This project scrapes official utility rate data, stores it in a structured database, and serves it as a clean, browsable static website via GitHub Pages.

## Scope: Building Energy Costs

The active parser campaign supports building energy-cost analysis, including work
informed by **NECB 2025**, plus **single-family homes**. Prioritize residential and
multi-unit residential, commercial, institutional and building-related industrial
service: the tariffs needed for building electricity, heating and other building systems.
Tariff eligibility still comes from the utility's published schedule; this project
does not determine building-code applicability or certify NECB compliance.

Process-specific farm and oil-field service, irrigation, NGV fuelling, EV charging,
lighting, wholesale/reseller and standby-only service are **not completion requirements**. Already
implemented schedules and data remain as reference, including farm/oil-field work,
but further expansion of those classes is deferred. Shared general-service tariffs may
still be relevant to buildings even when the utility also offers them to other users.
Inventory counts below include reference-only records, not just building tariffs.

## Current Status (2026-10-07)

The framework and website are implemented; **nationwide live-rate coverage is not complete**.
The export was regenerated on **2026-10-07** after batch 11 (a full 20-utility refresh). History was preserved.
A successful source check and an export timestamp are different facts;
unverified fallback records remain estimates regardless of the export date.

| Measure | Exported state |
|---|---|
| Registered utilities | 86: 77 electricity and 9 gas, across all 13 provinces/territories (8 absorbed Ontario entries marked `merged`) |
| Stored tariff versions / components | 1,321 / 13,343, including history and older estimates |
| Live-sourced tariffs | **836 latest tariffs across 67 utilities**; 841 stored live versions |
| Active regional campaign | **243 latest live records across all 16 provincial target utilities**; 109 across the four territorial utilities |
| Ontario (batches 1-2) | **483 latest live records across 46 distributors** from OEB-approved tariff sheets; only PUC Distribution stays unconfigured |
| Remaining seed-only campaign utilities | **0**; SaskPower's scoped building schedules are audited, while other targets have recorded gaps |
| Seed/fallback tariffs | **480**, hidden by default |
| SaskPower live tariffs | **41**, including reference-only records; scoped building schedules implemented |
| Historical snapshots | **3,013**; Ontario batch 2 appended 527 without changing prior snapshots |
| DB validation | **0 errors, 2 existing AESO warnings** |
| Deterministic tests | **1,213 passing** across 8 modules |

Live output currently includes BC Hydro (17), FortisBC Electric (11), Manitoba Hydro (18), NB Power (10),
Nova Scotia Power (18), Hydro-Quebec (26), Maritime Electric (10), Newfoundland Power (11),
NL Hydro (21), SaskPower (41), SaskEnergy (8), Centra Gas Manitoba (13), FortisBC Energy (27),
Energir (5), Heritage/Eastward (3), Liberty NB (4), NTPC (63), Qulliq Energy (6), Yukon Energy (20),
ATCO Electric Yukon (20), FortisAlberta (1) and 46 Ontario distributors (483; Hydro One 50,
Alectra 44, Elexicon 19, ERTH 18, Enova 16, GrandBridge 16, North Bay 15, Newmarket-Tay 14,
Toronto 12, Algoma 10 and others; see the matrix).
These counts use the latest version per tariff, not complete utility catalogues.
They include conditional products, adjustment-only records and retained non-building
references, not a count of complete building classes. Yukon Energy and ATCO Electric Yukon
publish the same 20 joint YUB schedules; NTPC's 63 include 52 per-community government
records. FortisAlberta is retained without a new regional-run scrape. Ontario demand classes
are delivery-only (commodity/GA deferred to market-rate work); 23 smaller Ontario distributors
and the five Ontario/Alberta gas utilities still have no live records.

See the [coverage matrix](docs/phase5_completion_matrix.md) for the implementation queue
and [parser gap report](docs/live_parser_gap_report.md) for class-level details.
A successful scrape can return only seeds; success counts and an empty missing-data log
do **not** prove live coverage.

The active campaign covers 16 registered utilities in BC/QC/MB/SK/NB/NS/PE/NL plus,
from October 7, the four territorial utilities (non-market regulated service).
Alberta remains excluded from this run. Ontario electricity distribution started October 7
(batch 1: Hydro One and the larger distributors). From October 6,
building-related industrial general facility classes are in scope, including those
defined by size, voltage or interruptibility. Process-specific farm, oil-field,
irrigation, NGV fuelling, EV charging, lighting, wholesale/reseller and standby-only
services remain excluded. See the [coverage matrix](docs/phase5_completion_matrix.md)
for the queue and the [parser gap report](docs/live_parser_gap_report.md) for parser rules.

---

## What This Project Does

1. **Scrapes** utility rate data from official Canadian utility websites.
2. **Stores** everything in a normalized SQLite database that preserves every rate detail — not just a single "cost per kWh" number.
3. **Tracks history** — each stored scrape appends snapshots. Keep the local database; CI restore/save via a release asset is implemented but awaits its first CI run verification.
4. **Exports** the data as JSON for the GitHub Pages static site.
5. **Serves** a browsable web interface with multi-select filters, confidence indicators, source attribution, and an interactive Market Pricing dashboard with heatmaps and charts.
6. **Provides automation** through monthly scraping, separate Pages deployment, and non-blocking source-health workflows. The new publication handoff still awaits its first CI run verification.

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
│   └── utilities/            ← 33 scraper modules + package initializer; 86 registered utilities
│       ├── bc_hydro.py       ← BC Hydro (electricity, BC)
│       ├── hydro_quebec.py   ← Hydro-Québec (electricity, QC)
│       ├── ontario_ldc.py    ← All Ontario LDCs (one class; OEB tariff sheets via utils/oeb_tariff.py)
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
├── tests/                    ← 1,213 deterministic tests across 8 test modules
│   ├── fixtures/             ← Source-derived fixtures; other tests also use inline text
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
scrapes, validates, rejects empty exports, and commits updated data. It now restores
`data/db/rates.db` from the GitHub Release asset tagged `data-history` and uploads it
only after validation and export succeed. Failure issues cover tests, scraping and
validation/export failures.

[Deploy Site](.github/workflows/deploy.yml) is a separate push/manual workflow with a
`workflow_run` trigger after a successful Monthly Scrape; it checks out `main`.
[Non-blocking Source Health](.github/workflows/source-health.yml) runs on the 15th
and uploads a dry-run log without publishing; it now installs Playwright Chromium.

**Remaining operational gaps:** these workflow changes are implemented but have not
been exercised in CI. Verify release-asset history restoration/upload, failure issues,
browser-enabled source health and the deployment handoff on the first CI run; do not
assume durable CI history or automatic deployment yet. GitHub Pages must use **GitHub
Actions** as its source, and `workflow_run` fires from the default branch. Manual
workflows are available in **Actions**.

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
| 5B: SaskPower | Standard/bulk-metered/diesel residential, general-service/voltage/TOU and renewable-access schedules | Audited building scope implemented October 1; 41 live tariffs total including retained non-building reference records |
| 5C: Residential products and building-service expansion | Review optional residential plans and retain building-service gaps | Nine batches delivered; remaining building catalogues still incomplete |
| 5D: Provincial/territorial depth | Building-class audits at already-live utilities; later territorial coverage | NL Hydro 21 records implemented; territories reopened October 7 (NTPC, Qulliq, Yukon Energy and ATCO Electric Yukon live) |
| 5E: Gas | Building heating/service tariffs preserving zones, components, units and dates | All six in-scope gas utilities have live output; building-service gaps remain. ON/AB gas excluded from this run |
| 5F: Alberta electricity | Building-relevant wires/default retail products; separate AESO reference where required | Planned |
| 5G: Ontario | Batches 1-2 done October 7-8: 46 distributors live from OEB tariff sheets; rejected classes no longer re-emit estimates. PUC Distribution unconfigured (no connection rate printed). Demand-class commodity/GA waits for market-rate work | Mostly done |
| 5H: Reliable publication | Source-health/browser setup, live-vs-fallback reporting, failure notifications, deployment trigger and durable CI history | Browser setup, failure issues, deployment trigger and release-asset history implemented; first CI run verification and provenance reporting remain |

**Definition of done for each utility:** account for the standard published classes
relevant to building energy costs, including single-family homes,
retain exact source/date/unit/component context, prove extraction and failure handling
with source-derived fixtures, inspect an official-source dry run, verify repeat
storage/export without lost components or history, and update the coverage ledger.
Known failures remain unverified; unsupported building classes are recorded as gaps,
never invented. Non-building services are explicit exclusions, not blockers to building
coverage. Special/negotiated and closed-to-new schedules must be identified where
applicable. Do not equate a generic verifier test with a working parser.

Utility-specific research can run independently; shared registry, database and export
updates are integrated serially. Completed batches are published at tested milestones;
the roadmap is not a promise to complete all Canadian parsers in one session.

### Phase 6: Provenance and Product Follow-up

1. Correct the market-model metadata and UI disclosure/visibility; documentation is corrected now, the UI change is deferred.
2. Replace fixed market-model inputs with reproducible official observation ingestion and freshness checks.
3. Add historical rate charts and AI-ready exports after coverage is dependable.
4. Scope a bill calculator and optional API separately; current comparison never calculates a total.
5. **Conditional Alberta market region:** if the Alberta source audit reveals comparable market-pricing variation or complexity, add Alberta as a selectable region in the existing Market Pricing dashboard. Reuse the interface, but use Alberta-specific values, official sources, effective periods and methodology, not Ontario's values or HOEP-plus-GA assumptions. Keep wholesale, retail and wires charges distinct and label any modeled estimates explicitly. This is a later-phase option, not a change to the current parser priorities.
6. **Across-Canada comparison view:** expand the Compare tab with a separate national view alongside the existing two-tariff comparison. Compare common customer classes and rate structures across provinces, using the Phase 7 representative models as the provincial values. This is planned work after Phase 7F, not part of the current parser campaign.

#### Across-Canada Comparison: Design Direction

- **National comparison matrix:** provinces/territories as rows, common customer-class/rate-structure categories as columns or selectable views. Keep every region visible, including where a category is **Not offered**, **Not yet verified**, or **Not comparable**; these are different states, never zero prices. Build the category crosswalk from published eligibility, not just similar utility plan names.
- **Residential profiles:** start with flat, tiered and time-of-use plans, with separate views for other nationally recurring structures. Show energy prices, monthly fixed charges, tier allowances, TOU hours/seasons and mandatory adjustments. Show monthly-equivalent fixed charges only with a disclosed day/billing-period basis and the original units. Do not manufacture a flat rate by averaging a tiered or TOU plan; distinguish ordinary household service from bulk-metered, off-grid, pilot and other conditional products.
- **Commercial class ladders:** compare small, medium and large general service using each utility's actual eligibility bands. Show the peak-demand range, fixed monthly charge, energy structure, when demand billing begins, any free demand allowance, and the applicable charge per kW or kVA. A shared demand-axis chart could reveal where one province's small-commercial class becomes another's medium class. Preserve voltage, season, minimum-bill and demand-ratchet conditions; do not invent universal class boundaries or convert kVA to kW without evidence.
- **Transparent provincial blends:** provincial values come from the [Phase 7 representative models](#phase-7-representative-models-planned) (median across utilities, single-source where only one utility exists, generated method statement); this view adds no blending logic of its own. Display the participating utilities, coverage and min-max range, with expansion to individual tariffs and sources. Incompatible tier boundaries and TOU windows stay visible in the model's method statement. A model is a comparison indicator, not an official tariff or a price every resident pays.
- **Visual exploration:** combine the sortable matrix with provincial dot/range plots, miniature tier-step charts, 24-hour TOU strips and commercial demand-threshold ladders. Selecting a province should reveal its contributing utilities and charge breakdown; selecting a category should line up that structure across Canada. Offer fuel, customer/building type, rate structure and effective-period controls, with an accessible table alternative to charts.
- **Fair comparisons:** keep energy, delivery, fixed charges, demand and riders distinct. Flag energy-only versus bundled service, differing units and incomplete component coverage before ranking or blending. Show source dates and methodology; keep estimated inputs separate and explicitly labelled. Any usage-weighted effective price or example monthly bill requires a disclosed load profile and the separately scoped calculator work above, not an implicit total in this comparison view.

### Phase 7: Representative Models (planned)

A new **Representative Models** section gives, for each province (territories later), one modeled
tariff per sector (residential, commercial) and per rate structure actually offered there
(for example Ontario TOU, Tiered, ULO and GS demand; Quebec Rate D; BC tiered/flat/TOD).
These are comparison indicators built from live records. They are **not tariffs anyone is
billed**, are labelled `provenance: "modeled"`, are never counted as live coverage and are
never shown as a utility's rate. The Phase 6 Across-Canada comparison reads these models for
its provincial values instead of computing its own blends.

**Decisions (user, October 8):** median across utilities (each utility counts once); a
province/structure with one utility uses that utility's tariff, labelled single-source; the
target is a full all-in price including energy/commodity (market-priced energy comes from the
market model and is labelled modeled); a dedicated site view next to Rate Browser, Market
Pricing and Compare; planned now, implemented later. A first Ontario delivery-only prototype
exists as scratch analysis (`logs/_on2_r_model.py`, October 8): typical monthly delivery varies
about 18% across 46 distributors (Hydro One the main outlier).

#### Representative Models: Design

- **Model key:** province, fuel (electricity, gas), sector (residential; commercial
  small, medium, large), structure (flat, tiered, TOU, ULO, seasonal, demand, interruptible...)
  and, where relevant, size band. A model exists only where at least one live record of that
  structure exists; otherwise the state is *Not offered* or *Not yet live*, never zero.
- **Category crosswalk:** a reviewed configuration file maps each utility's tariff (registry
  name and tariff code) to a model key from published eligibility, not from similar plan names.
  Default rate zones and standard service only; closed, pilot, optional, bulk-metered, off-grid
  and process-specific products are excluded unless a model is defined for them, and every
  exclusion is listed with its reason. A multi-zone utility counts once (median of its zones).
- **Component buckets:** fixed per month, energy/commodity (by period or tier), distribution
  volumetric, demand per kW or kVA, transmission, regulatory, mandatory riders, carbon and other
  mandatory charges. Conditional, optional and expired components are excluded and counted.
  Unit conversions are disclosed ($/day x 30.4375 = $/month; cents to dollars); kVA is never
  treated as kW without a disclosed power-factor assumption; m3 is never converted to GJ without
  a published heat content.
- **Combining rule:** each bucket is the median across contributing utilities, shown with n,
  min, p25, p75 and max. Because bucket medians do not add up to a coherent bill, each model also
  reports, at every common usage level, the median cost (computed per utility, then the median),
  without and with tax, and the closest real utility (whose cost is nearest the median), linked
  to its live tariff. Major outliers are named with their deviation from the median.
- **TOU and time periods:** if one schedule applies province-wide (Ontario RPP), use it as
  published. Otherwise compute each utility's price for every hour of a reference week per
  season, take the median per hour, then group equal-priced hours into representative periods.
  The model states which utilities had which schedules.
- **Tiers:** identical thresholds are used directly. Otherwise build each utility's marginal
  price over a usage grid, take the median per point and simplify it into representative tiers;
  original thresholds stay visible.
- **Commercial size bands:** under 50 kW, 50-499 kW, 500-4,999 kW and 5,000 kW and over (volume
  bands for gas). Each utility contributes the class whose published eligibility covers the
  band's reference load, and the model names that class.
- **All-in energy:** regulated energy (Ontario RPP, provincial rates, regulated gas supply) is
  used as published. Market-priced energy (Ontario non-RPP demand classes: HOEP plus Class B GA;
  Alberta pool/RoLR; monthly or quarterly gas commodity) comes from the market model, is labelled
  modeled with its period basis, and waits for Phase 6 item 2 (real observation ingestion) and
  the Alberta block (5F). Until then the model shows delivery plus a *market energy pending*
  state, never a guessed number.
- **Transparency text:** every model carries a generated method statement, for example
  "Median of 44 Ontario LDC TOU delivery charges (default rate zones, Hydro One included) plus
  the province-wide OEB RPP TOU prices and hours effective November 1, 2025; excludes Algoma (no
  standard TOU-R) and Oakville (GS<50 rejected)", or "Single source: Nova Scotia Power Domestic
  Service is the only utility; no averaging". It also lists contributing utilities, record ids,
  effective dates, source URLs, coverage (n of N utilities), exclusions with reasons, outliers,
  generated date and the input export.
- **Outputs:** a builder run by `pipeline/export_json.py` writes
  `site/data/representative_models.json`, rebuilt on every export and kept in git history. No
  schema change is planned.
- **Site view:** a **Representative Models** tab with province, fuel, sector and structure
  selectors; a component table with spread, a 24-hour/season strip for TOU, a tier-step chart, a
  demand-band ladder, the method statement and an expandable list of contributing tariffs. A
  permanent banner says the model is not a billed tariff.
- **Across-Canada use:** the national matrix, dot/range plots, TOU strips and demand ladders
  read the same JSON; a province drill-down shows the model's contributing tariffs. The
  comparison states *Not offered / Not yet verified / Not comparable* map to the model states.

#### Representative Models: Phases

| Phase | Work and completion gate | Depends on |
|---|---|---|
| 7A: Taxonomy and crosswalk | Model keys and size bands; reviewed crosswalk for every live utility; exclusion reasons; tests for unmapped/ambiguous records | Current live data |
| 7B: Engine (delivery + regulated energy) | Bucket normalization, median/spread, cost at each common usage level without and with tax, closest utility, outlier notes, TOU hour surfaces, tier curves, demand bands, method text and provenance; synthetic and fixture tests; Ontario first (promote the scratch prototype) | 7A |
| 7C: Electricity, all provinces | Residential and commercial models for every province with live data; single-source labelling; coverage report (territories planned separately) | 7B |
| 7D: Gas | Residential and commercial gas models (commodity, delivery, carbon kept as buckets) | 7B; ON/AB gas parsers |
| 7E: All-in market energy | Market-priced energy from the market model with period basis; *pending* state until available | Phase 6 item 2; 5F Alberta |
| 7F: Site view | Representative Models tab, charts, method/coverage disclosure, accessible table, desktop/mobile checks | 7C |
| 7G: Across-Canada integration | Phase 6 national comparison built on the models: electricity first, gas after 7D, all-in after 7E | 7F; Phase 6 item 6 |

**Decisions before 7A (user, October 8):**
- **Taxes:** every all-in model is shown both without tax and with tax (applicable GST/HST/PST,
  each tax line disclosed with its rate and source).
- **Usage levels:** no single reference usage. Each model is evaluated at a set of common usage
  levels per sector (for example low/typical/high monthly kWh for residential, and several
  kW/kWh combinations per commercial size band), with the level definitions and their basis
  published; the median and closest utility are reported per level.
- **Outliers:** no "excluding" variants. When a utility is a major outlier, the model says so
  and by how much (for example "Hydro One: +55% versus the median at typical usage").
- **Scope:** provinces only for now. Territorial models (community-level rates, NTPC zones,
  Qulliq, subsidies) get their own plan later.

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
