---
description: "Use when changing representative models, their inputs or the views that read them: pipeline/representative_models.py, data/models/ (crosswalk.json, usage_levels.json, block_periods.json, taxes.json), site/data/representative_models.json, site/js/models.js, site/js/across-canada.js and their CSS. Covers crosswalk first-match rules and 0 unmapped, Alberta wires + RoLR pairs, required contributors, usage levels, dated TOU/ULO shares, fixed_charge_variants (reference customer), block periods, unit conversions (30.4375 days), taxes and rebates, median of zones, outliers, model states, the 7E synthetic illustrative sidecar, market benchmark sidecars, METHOD_VERSION, math.fsum and Across-Canada constraints."
applyTo: "pipeline/representative_models.py, data/models/**, site/js/models.js, site/js/across-canada.js, site/css/models.css, site/css/across-canada.css, site/data/representative_models.json"
---
# Representative models

Models are comparison indicators (`provenance: "modeled"`): never a billed tariff, a forecast, a quote
or live coverage. Page presentation: [website.instructions.md](website.instructions.md). Market inputs:
[market-data.instructions.md](market-data.instructions.md).

## Method, export and tests

- Every export carries `method_version` from `METHOD_VERSION`. Each owner-approved method change has
  received a new version (7C-3: decisions of 2026-10-30; 7C-4: market benchmark sidecars,
  2026-11-02; 7D-1: residential gas models, 2026-11-04); update the tests that assert it.
- `export_json.export_all()` calls `export_representative_models()` after the other exports
  (`MODEL_PROVINCES` = ON, AB, BC, MB, NB, NL, NS, PE, QC, SK; `zone_policy="median_of_zones"`). The
  hook imports lazily and writes `site/data/representative_models.json` through a temporary file and
  `os.replace`; any failure is logged, keeps the previous file and never fails the export.
- CLI: `python -m pipeline.representative_models --coverage` and/or `--build [--output PATH]
  [--rates PATH] [--province XX ...] [--as-of YYYY-MM-DD]`.
- Sum floats with `math.fsum` in the engine and market code: Python 3.12's built-in `sum()` differs
  from 3.11 and once moved a median by a cent.
- Tests use frozen record fixtures (`tests/fixtures/rm_records_sample.json`, `rm_engine_sample.json`,
  `rm_records_b12.json`, `rm_records_b14.json`, `rm_records_ws_6d.json`, `rm_records_7d_gas.json`),
  so the pre-scrape CI tests never depend on the live export.
- Phase 8 refresh automation exists only as a proposal; the proposed 2% Phase 8 change threshold is
  unapproved; there is no synthetic sensitivity tool.

## Gas models (Phase 7D first slice, method 7D-1, owner decision 2026-11-04)

- `MODEL_FUELS` = electricity and gas, but gas models are built only for `GAS_MODEL_SECTORS`
  (residential). Commercial, contract and interruptible gas keys are withheld and listed in
  `input.withheld_gas_models` until their scenarios are approved.
- Residential default utility supply only. Propane, optional RNG, Customer Choice/marketer and
  delivery-only products are crosswalk exclusions; an optional utility supply (Liberty NB) is not
  included, so that model is not computable rather than assumed.
- Native units, never converted or merged: a gas model's records must price exactly one volume unit
  (`gas_volume_unit`: `$/m³` -> m3, `$/GJ` -> GJ); mixed or missing units leave the model with no
  level. m3 utilities are evaluated at `gas.residential` levels 100/200/400 m3 and GJ utilities at
  4/8/16 GJ (reference levels sourced; the others are labelled sensitivity levels). Level output
  carries `quantity`, `unit` and `role`, with `kwh`/`kw` null. A future cross-unit comparison converts
  toward m3 at 100/200/400 m3, with its heating-value source decided then.
- `price_basis(..., volume_unit=...)` accepts only the model's own volume unit; gas tier thresholds
  must be monthly volumes in that unit (`m³/month`). Daily or annual gas thresholds, per-metering-device
  fees and `$/m³/month` demand charges are unsupported (fail closed, e.g. Energir D1). `commodity`
  components count as energy. Tax thresholds in kWh never apply to gas.
- The Representative Models page shows gas levels in m³ or GJ with Reference/Sensitivity tags;
  Across-Canada stays residential electricity only.

## Inputs and crosswalk (`data/models/crosswalk.json`)

- Use only the latest live records: the site's dedupe, then `provenance == "live"`.
- Rules are ordered and the first match wins: each record maps to {province, fuel, sector, structure,
  size band} or to an exclusion reason. Require 0 unmapped (`--coverage`); the coverage report lists
  the intentional rule overrides.
- Exclusion reasons include `gas_models_phase_7d` (ON/AB gas records outside the residential
  first slice), `territory_planned_later`,
  `paired_retail_component` (Alberta RoLR records) and, for AESO and the market-indexed products,
  `market_reference_only`, `optional_product`, `pilot` and `industrial_use_only`.
- Out of medians (owner decision 2026-10-16): optional TOU/peak-event products and pilots outside
  Ontario (BC Hydro 2101 combinations, FortisBC 22A/32, Hydro-Quebec Flex D/G, ATCO D13). ATCO T31,
  FortisAlberta 65, ENMAX D410 and EPCOR DAS-TOUP are supply-voltage alternatives.
- `pairs` (owner decision 2026-10-16): ENMAX Power + ENMAX Energy, ATCO Electric + DERS (without the
  admin charge, noted), EPCOR Distribution + EPCOR Energy Alberta, FortisAlberta + EPCOR Energy
  Alberta. One composite record `<wires id>+<retail id>` per wires class; each pair counts once and
  each charge keeps its own source. The RoLR variant applies only below 250,000 kWh/year (12 x the
  level's kWh); above it the market variant is wires plus a value-less pool-price energy line
  (`market_energy_pending`). Retailer fees, losses and unpriced conditional charges are excluded.
- `required_contributors`: withhold a level (reason `withheld`, state `not_computable`) when a listed
  utility is not computable there (NL residential needs Newfoundland Power).
- `usage_bounds`: quoted annual-use eligibility limits, applied as the level's kWh x 12.

## Usage levels and reference customer (`data/models/usage_levels.json`)

- Owner-approved levels: residential 500, 1,000 and 2,000 kWh; commercial under 50 kW 2,000 kWh at
  10 kW (s1) and 8,000 kWh at 25 kW (s2); 50-499 kW 40,000 kWh at 100 kW (m1); 500-4,999 kW
  500,000 kWh at 1,000 kW (l1). There is no 5,000 kW+ level (those models report buckets only).
- A month is 30.4375 days everywhere (owner decision 2026-10-30), although Hydro-Quebec and Manitoba
  Hydro define a month as 30 days. kVA uses power factor 0.9.
- TOU/ULO shares are dated sets (`effective_date`/`end_date`), one per OEB RPP price period.
  `find_tou_shares(..., as_of)` selects the set in force; more than one in force or a malformed date
  fails closed (TOU energy not computable) instead of guessing. When the next OEB RPP Price Report
  comes out (each October), add a new dated set and end-date the previous one.
- Approved sets (OEB RPP Price Reports; only officially published shares are used, never estimated):
  `ON_RPP_TOU` off/mid/on-peak 64/18/18 and `ON_RPP_ULO` ultra-low overnight/weekend off-peak/
  mid/on-peak 40/20/27/13 for November 1, 2025-October 31, 2026 (`end_date` 2026-11-01); from
  November 1, 2026 `ON_RPP_TOU_2026` 64/18/18 and `ON_RPP_ULO_2026` 41/20/26/13 (report issued
  October 16, 2026).
- `reference_customer` lists the reviewed conditional charges a typical customer does pay: Ontario
  Class B CBR riders, non-RPP Class B GA riders for demand sectors, non-wholesale-market-participant
  riders and the SSS administration charge.
- `fixed_charge_variants` (owner decision 2026-10-30): fixed charges published as phase or amperage
  variants (alternatives or unmarked variants) are never summed. A rule prices exactly one variant per
  level: homes at single-phase 200 A; commercial under 50 kW single phase at s1 and three phase at
  s2. Reason `fixed_charge_variant:<id>`, disclosed per model and per utility row. No match or more
  than one match leaves that utility not computable at that level; Manitoba GS Small (Demand) (50-499
  kW, no variant rule) stays unavailable without phase/history assumptions.

## Block periods and unit conversions

- A kWh block threshold without a stated period needs a reviewed `data/models/block_periods.json`
  entry (`threshold_period`) that quotes the tariff or the utility's billing page. `null` means no
  stated period: the record is left out instead of guessed (Maritime Electric seasonal 133/233,
  Manitoba GS seasonal).
- NB Power GS1 and Maritime Electric 110/130/131/232 "per Billing Period" blocks count as per month
  because both utilities' billing pages confirm monthly billing (owner decision 2026-10-30).
- Only these conversions are allowed: $/day x 30.4375; $/30 days x 30.4375/30; FortisBC "$/two
  months" / 2; per-day energy blocks x 30.4375 (Hydro-Quebec Rate D 40 kWh/day); kVA at PF 0.9. Never
  assume any other conversion.

## Costing rules

- A record's cost includes the unconditional components in effect at the as-of date. Conditional,
  alternative, optional, expired and not-yet-effective components, percentage adjustments and
  value-less market components are excluded and counted, except the reviewed `reference_customer`
  entries.
- Energy is pending only when the energy itself is market-priced. EPCOR's operating reserve (a
  percentage of the pool price) is excluded and listed in `energy.market_indexed_excluded`.
- Bill demand only above a published threshold; apply energy blocks per kW, kVA or day as printed;
  accept kVA alternatives when the kW charge is priced; zero-valued TOU parts need no share.
- Ontario loss factors and Class A GA are not modeled; the method text says so.

## Zones, statistics and states

- Each utility counts once, as the median of its standard zones (`median_of_zones`, owner decision
  2026-10-09; `default_only` is the alternative policy, an open default).
- Per level: median, n, min, p25, p75, max, the real utility closest to the median, and outliers
  (more than 30% from the median or outside 1.5 x IQR, n >= 3), which are named with their distance
  from the median, never removed.
- States: `modeled`, `single_source`, `market_energy_pending` (Ontario and Alberta demand classes) and
  `not_computable`. `coverage.contributor_noun` names the contributors (utilities, distributors, or
  wires + Rate of Last Resort pairs).

## Taxes and rebates (`data/models/taxes.json`)

- Sales taxes (GST, HST, PST, QST, RST) and automatic point-of-sale rebates (Ontario Electricity
  Rebate, NS Your Energy Rebate 9%, NB 10% residential electricity rebate) are lines of kind
  `sales_tax` or `rebate` per jurisdiction (13), fuel and sector, applied as the file's `notes`
  define. A rate change is two dated lines of the same name; `tax_lines` never lists the line whose
  date window is not in force as "not applied".
- Lines never compound. The Ontario Electricity Rebate applies to the pre-tax amount and HST to the
  pre-rebate amount, so eligible Ontario with-tax costs are below those without tax. OER: 23.5% until
  October 31, 2026 and 15.7% from November 1, 2026 (O. Reg. 328/26).
- Accepted defaults: Manitoba residential is a gas-heated home; municipal taxes and surcharges are
  excluded; commercial tax is shown as billed, without input tax credits; income-tested programs are
  excluded.

## 7E illustrative sidecar (synthetic load profile)

- Only for the Ontario `market_energy_pending` m1/l1 levels: `illustrative_all_in` with
  `synthetic_profile: true`, `illustrative_only: true` and the label "SYNTHETIC LOAD PROFILE -
  ILLUSTRATIVE ONLY". It must stay very obviously synthetic: representative only, not to be taken
  seriously, needing further analysis (owner decision 2026-10-16).
- Profile `usage_levels.synthetic_profiles.ON_SYNTHETIC_BUSINESS_HOURS` (an open default): the level's
  kW Monday-Friday in hours beginning 7-18 EST and a constant base load sized to the level's kWh at
  all other hours; holidays count as weekdays. The price comes from
  `market_pricing.synthetic_profile_price()` (algorithm and availability checks in
  [market-data.instructions.md](market-data.instructions.md)).
- Never use it in medians, outliers, closest utility, Phase 8 change detection or Phase 9 comparisons;
  the level's state stays `market_energy_pending`.
- No real commercial load profile is qualified: Toronto Hydro's EB-2023-0195 Exhibit 7 example is
  illustrative (its full-year attachment and rights are unverified), and FortisAlberta's assigned
  settlement shapes are not observed commercial class loads. Geographic proxies are a separate future
  proposal.

## Market benchmark sidecars (method 7C-4)

- Separate `model.market_benchmark` and `level.market_benchmark` objects for the Ontario and Alberta
  commercial market-only levels, priced by `historical_market_price()` (its checks are in the
  market-data instructions; settings in `usage_levels.market_benchmarks`).
- Ontario uses energy + actual Class B GA; Alberta uses pool energy only. Add the benchmark energy
  before the per-zone taxes and statistics.
- A benchmark is the 60-complete-month historical energy average plus today's modeled delivery: not a
  forecast, a retail quote or a customer-profile-weighted bill, and it never replaces the
  delivery-only base table. Base medians, RPP/RoLR results and synthetic output stay separate.

## Across-Canada (`site/js/across-canada.js`)

- Residential electricity only, at 500, 1,000 or 2,000 kWh (default 1,000), with tax by default and a
  before-tax option; all 13 jurisdictions; rate structures stay separate.
- Read the model file through the shared loader in `models.js`. Never recalculate bills, never use
  synthetic or benchmark values (neither sidecar enters Across-Canada) and never show a computed bill
  breakdown.
- Chart and table share one eligibility rule. Show missing, territorial, pending and withheld states
  explicitly, keep missing territorial models separate from live tariff coverage, and never turn a
  missing model into a zero bar.
