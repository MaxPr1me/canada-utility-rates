---
description: "Use when changing market price history, archives or market workflows: scripts/build_ontario_market.py, scripts/archive_ontario_price.py, scripts/preserve_ieso_reports.py, scripts/export_ontario_totals.py, scripts/generate_market_pricing.py, scripts/build_alberta_market.py, scrapers/utils/market_pricing.py, data/market/, site/data/market_pricing_ontario.json, site/data/market_pricing_alberta.json, ontario-price-archive.yml and market-benchmarks.yml. Covers HOEP, the Ontario Price (OEMP = DA-OZP + LFDA), Class B Global Adjustment, the rolling 60-month window, observed-hours heatmaps, raw IESO preservation, combined totals, AESO pool history, validation tolerances, fail-closed and never-fill-gaps rules."
applyTo: "scripts/build_ontario_market.py, scripts/archive_ontario_price.py, scripts/generate_market_pricing.py, scripts/preserve_ieso_reports.py, scripts/export_ontario_totals.py, scripts/build_alberta_market.py, scrapers/utils/market_pricing.py, data/market/**, site/data/market_pricing_ontario.json, site/data/market_pricing_alberta.json, .github/workflows/ontario-price-archive.yml, .github/workflows/market-benchmarks.yml"
---
# Market data (Ontario IESO and Alberta AESO)

How the models use market prices:
[representative-models.instructions.md](representative-models.instructions.md). How the site shows
them: [website.instructions.md](website.instructions.md).

## Rules for every market file

- Market files hold observed history, never tariffs. Never copy a market average into a tariff:
  market-priced tariff lines stay value-less ("Variable").
- Ontario and Alberta histories stay separate, each with its own files, method and assumptions.
- Fail closed: a missing month, day or hour, an unreadable or empty file or a failed check writes
  nothing and exits non-zero. Write through a temporary file and `os.replace`. A run with no new data
  leaves every file byte-identical.
- Never fill gaps: a blank LFDA is never zero, a missing hourly total stays blank, monthly references
  never fill hourly gaps and unrecoverable hours are disclosed, never invented. Zero and negative
  prices are valid.

## Ontario definitions and defaults

- HOEP (Hourly Ontario Energy Price) ran until April 30, 2025. Since May 1, 2025 the hourly price is
  the Ontario Electricity Market Price (OEMP, "Ontario Price") = DA-OZP + LFDA.
- Compare and show the two markets on the customer-paid basis, energy + Class B GA, as one continuous
  total (owner decisions 2026-10-15/16). Energy alone is not comparable: GA offsets energy.
- Open defaults (the owner may change them; the legacy and rolling builds both use them): April-June
  2020 use the published capped Class B GA (115 $/MWh, provincial emergency order); 2021 actuals
  exclude the separate recovery rates (5.01-7.09 $/MWh) billed to non-RPP Class B customers;
  statutory holidays count as the weekday they fall on.
- Heatmaps have 576 bins (12 months x weekday/weekend x 24 hours beginning, EST), built only from
  observed hours, and each bin reports its hour count.

## Raw IESO preservation (`scripts/preserve_ieso_reports.py`)

- Saves the original daily DA-OZP and yearly LFDA reports before any price check, as content-addressed
  deterministic gzip objects indexed in `data/market/ieso_raw/index.json` (source URL, SHA-256, size,
  `raw_unverified`).
- Raw bytes are unverified source evidence, never prices or rates. Never replace or delete old
  captures; changed LFDA and invalid or empty responses become additional objects.
- A partial fetch failure keeps the successful downloads and exits non-zero.
- `archive_ontario_price.py --raw-dir` replays versioned daily DA reports after the IESO removes them.
  Mutable LFDA, listings and monthly checks stay live, never silently stale.

## Ontario Price archive (`scripts/archive_ontario_price.py`)

- A compact CSV in the repository, extended by CI (owner decision 2026-10-15):
  `data/market/ontario_price_hourly.csv`
  (`date,hour_ending,da_ozp,lfda,oemp,da_ozp_source,da_ozp_version,lfda_status`; hour-ending EST).
  It merges the daily `PUB_DAHourlyOntarioZonalPrice_YYYYMMDD[_vN].xml` reports (highest version wins)
  and the yearly LFDA CSVs.
- A blank LFDA is never zero (the IESO's monthly LFDA averages exclude blanks); a pending LFDA leaves
  `lfda` and `oemp` blank.
- Every complete month must match the IESO monthly Ontario Price table (arithmetic tab) within
  0.01 $/MWh for DA-OZP, LFDA and OEMP, all three strict even when the table's LFDA is still
  preliminary (owner decision 2026-10-15). Otherwise nothing is written.
- An empty or unreadable LFDA file stops the whole run ("the IESO published this file empty"): write
  nothing and run again once the IESO republishes; never make a DA-OZP-only update (owner decision
  2026-10-16).
- The site chart API (`getOntarioDayAheadAndPredispatchPrices`) serves only about 10 days, so it may
  fill gaps only if every month matched the published table, which it cannot; CI runs `--no-site-api`.
  Hourly OEMP for May 1, 2025-July 10, 2026 is unrecoverable (the archive starts July 11, 2026);
  monthly values for that gap come from the IESO monthly table.
- The IESO deletes each daily file after about 90 days: fix a failed archive run quickly.

## Rolling 60-month history (`scripts/build_ontario_market.py`)

- Writes `site/data/market_pricing_ontario.json` (schema 2, `derivation_method`
  `observed_rolling_60m_hoep_oemp_ga`: metadata with window, eras, gap, change date, source codes and
  cross-checks; 60 `monthly` records with era, energy arithmetic/weighted, Class B GA, total in $/kWh,
  sources and observed hours; 576 `hourly_surface` bins with `hours_hoep`/`hours_oemp`) and the
  permanent `data/market/ontario_market_monthly.csv`.
- Inputs: `data/market/hoep_hourly.csv` (legacy hourly HOEP, 2020-01-01..2025-03-31, imported once
  with `--refresh-hoep`) and the OEMP archive. CI downloads only the IESO monthly table page, the GA
  workbooks and the monthly GA reports, never the legacy HOEP files.
- A month is complete when it is over, its energy value is validated (HOEP hourly mean equals the
  IESO monthly report within 0.01 $/MWh; OEMP listed in the IESO monthly table, archive months within
  0.01 of it) and its Class B GA actual is published (Data Directory workbook or monthly
  `PUB_GlobalAdjustment_YYYYMM` XML; overlapping sources agree within 0.005 $/MWh).
- The window is the latest 60 consecutive complete months (owner decision 2026-10-16).
- April 2025 uses the IESO monthly report value with no observed hours: the yearly file's hourly mean
  (39.181 $/MWh) disagrees with the report (39.22).
- Heatmap option (a) (owner decision 2026-10-16): observed hours only; disclose the OEMP gap, never
  fill it.
- The monthly CSV is never trimmed; a changed month is accepted only within `REVISION_MONTHS` (6) of
  its end.

## Combined totals (`scripts/export_ontario_totals.py`)

- Reads only saved HOEP, OEMP and monthly Class B GA plus the byte-preserved
  `data/market/PUB_PriceHOEPPredispOR_2025_v119.csv`: no network, database or tariff writes.
- Writes `ontario_total_hourly.csv`, `ontario_total_hourly_2020_2025.csv` (52,608 fixed hourly slots),
  `ontario_total_monthly.csv` and `ontario_total_metadata.json` in `data/market/`, all totals in CAD
  cents/kWh: (hourly energy + that month's Class B GA), divided by 10 for $/MWh inputs.
- April 2025's 720 official hourly observations are included but flagged `observed_monthly_mismatch`;
  they never enter the validated heatmap or the models. These files never change the heatmap or model
  calculations.
- Missing LFDA or GA stays blank; the monthly-average column is a labelled reference, not a price for
  missing hours.
- Output is deterministic and protects existing rows and non-blank totals. Input fingerprints
  normalize line endings, except for the byte-preserved original report.

## Legacy 2020-2024 surface (`scripts/generate_market_pricing.py`)

- Manual only (`--start-year`/`--end-year` default 2020/2024); the site no longer shows it. The
  default `--output` is the git-ignored scratch file `logs/market_pricing_legacy_2020_2024.json`
  (owner decision 2026-10-30), so it can never overwrite the site's rolling file. Other scripts load
  it for shared readers.
- Downloads the IESO yearly hourly HOEP CSVs (`PUB_PriceHOEPPredispOR_YYYY`, $/MWh, hour-ending 1-24
  EST) and the Class B GA "Actual Rate ($/MWh)" from `Global-Adjustment-Values-MWh.xlsx`,
  cross-checked against the cents/kWh workbook.
- Every month's arithmetic mean must match the IESO HOEP Monthly Averages report within 0.01 $/MWh;
  units must match the HOEP historic prices page, which must carry the retirement sentence.
- Output: `derivation_method` `observed_legacy_hoep_2020_2024_average`; bins with `hours_count`,
  `avg_energy_price`, `avg_ga_class_b` and `combined` in $/kWh; metadata lists sources, hour
  convention, day-type rule, cross-check results and GA notes.

## Readers (`scrapers/utils/market_pricing.py`)

- Load only observed files: `OBSERVED_METHOD_RE` accepts the legacy and rolling methods and refuses
  any file not built from real observed prices.
- `get_observed_bin()`, `get_monthly_series()` and `get_monthly_average()` (weighted by observed
  hours). The tariff metadata formula is "Ontario Electricity Market Price (DA-OZP + LFDA) + Global
  Adjustment".
- `historical_market_price()` (market benchmarks) validates the province, the exact method and unit,
  60 consecutive complete months, finite arithmetic, citations and a window lag of at most four months
  (`max_window_lag_months` in `usage_levels.market_benchmarks`).
- `synthetic_profile_price()` (7E illustrative estimate): for each window month, that month's
  published energy price x that calendar month's profile-weighted shape factor from the heatmap bins,
  plus that month's Class B GA, averaged over the 60 months. It is unavailable when the window ends
  more than `max_window_lag_months` (4) before the as-of date or the file is not the rolling method.

## Alberta AESO history (`scripts/build_alberta_market.py`)

- Observed AESO pool energy only: no tariff values, customer load shapes or Ontario GA. The prices are
  real hourly AESO observations, never Ontario prices with another label.
- Sources: the ETS hourly report with `beginDate`/`endDate` in MMDDYYYY (end exclusive; at most 366
  days per request), the Pool Monthly Summary HTML or its discovered `frSheet`, and the metadata PDF.
- It calls the shared `parse_pool_price_csv(..., price_bounds=None)` on purpose: today's price cap
  does not apply to history.
- Monthly cross-checks against every official summary (within 0.01 $/MWh) and exact hour coverage
  are mandatory. Spring skips native HE02; autumn repeats HE02 as HE02*, and both enter the HE02 bin.
  The heatmap `hour` is an HE-1 index, not an Ontario EST/hour-beginning timestamp.
- Every run re-checks all history. A changed, already archived hourly price or monthly value stops
  publication for review: never assume an AESO revision deadline or overwrite old evidence. History
  is never shortened.
- Outputs: raw hours `data/market/alberta_pool_hourly.csv`, permanent monthly history
  `data/market/alberta_market_monthly.csv` and `site/data/market_pricing_alberta.json` (60 complete
  months, 576 observed-hour bins). `--dry-run` saves nothing.
- The owner confirmed permission to publish raw archives and derived charts and benchmarks; the grant
  itself has not been independently inspected.

## Workflows

- **Ontario Price Archive** (`ontario-price-archive.yml`): 06:00 UTC on the 1st and 15th (the owner
  kept the twice-monthly schedule), manual dispatch and pushes that change its scripts. Order:
  preserve raw reports; commit them even after a partial capture failure, before strict validation;
  update and commit the archive (`--no-site-api --raw-dir data/market/ieso_raw`); synchronize; build
  the market history (also when the archive step failed, using the committed archive, but not after a
  failed install or a failed archive commit); export totals; refresh models; commit. Each commit step
  sets its own git identity. On failure it keeps an `ieso-raw-recovery` artifact for 90 days and
  opens an issue titled by the failing part.
- **Market Benchmarks** (`market-benchmarks.yml`): runs after each successful Monthly Scrape, after
  every Ontario Price Archive run (also a failed one, to isolate Alberta), after relevant code and
  model-input pushes and on dispatch. It tests, builds the Alberta history and refreshes the models
  without writing the database; a failure opens an issue and the site keeps its published files.
- The three data writers (Monthly Scrape, Ontario Price Archive, Market Benchmarks) take turns through
  the `utility-data-updates` concurrency group. All three synchronize with `git pull --ff-only`
  before calculating or exporting and never rebase generated files onto newer inputs (the Monthly
  Scrape since issue #5; owner decision 2026-11-04; see
  [ci-data-history.instructions.md](ci-data-history.instructions.md), which also describes
  deployment chaining).
