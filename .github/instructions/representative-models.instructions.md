---
description: "Use when changing representative models, model change monitoring, their inputs or the views that read them. Covers crosswalk rules, required contributors, usage, taxes, block periods, model states, separate synthetic/observed sidecars, semantic change history, METHOD_VERSION and Across-Canada constraints."
applyTo: "pipeline/representative_models.py, pipeline/model_monitoring.py, tests/test_model_monitoring.py, data/models/**, site/js/models.js, site/js/across-canada.js, site/css/models.css, site/css/across-canada.css, site/data/representative_models.json, site/data/model_change_history.json"
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
  `rm_records_b12.json`, `rm_records_b14.json`, `rm_records_ws_6d.json`, `rm_records_7d_gas.json`,
  `rm_records_b18.json`, `rm_records_b18_ab.json`), so the pre-scrape CI tests never depend on the
  live export.
- The export and model CLI accept `--generation-receipt PATH`. This optional record distinguishes
  successful unchanged generation from failure retaining an old file; monitoring defects cannot
  break the primary export. The CLI requires `--build --output` when requesting a receipt.
- There is no synthetic sensitivity tool.

## Change monitoring (Phase 8, owner decision 2026-11-17)

- `pipeline/model_monitoring.py` compares base models and observed benchmarks separately by stable
  model and usage-level IDs. Material means **at least 5% absolute movement in the median with tax
  and rebates**, using the absolute prior median as denominator and decimal boundary arithmetic.
  Before-tax-only movement is not material. Zero, missing or non-comparable usage/unit/cost bases
  get explicit classifications rather than invented percentages.
- Smaller cost changes and substantive state, contributor, tax, usage, method and input changes
  are recorded too. The threshold marks changes in the public log; it does not govern publication
  or create price-change issues.
- Semantic fingerprints omit routine timestamps, machine paths, illustrative sidecars and
  synthetic-only inputs. Preserve first-match rule order. Fingerprint allowlisted input fields,
  not whole mixed-purpose files; use the actual loaded configuration and reviewed block-period
  inputs from that build. Monitoring alone does not change `METHOD_VERSION`.
- `site/data/model_change_history.json` keeps the last recorded semantic baseline, append-only
  hash-linked events, per-model last-change dates and the exact successful generation receipt.
  Initialization is labelled as a baseline, not a historical price change. Unchanged rebuilds
  advance refresh metadata, not last-change dates. Disclose skipped recording intervals; never
  reset corrupt history to hide a failure. Writes are atomic and retain prior history on failure.
- `python -m pipeline.model_monitoring --dry-run` checks local files without writing history or
  contacting GitHub. Only explicit `--record --receipt PATH` records a generation; `--report PATH`
  writes diagnostics. A receipt must match the model fingerprint, generation date, as-of and
  method. Missing, failed or malformed evidence is not success.
- Freshness, workflow evidence and issue recovery belong to the
  [CI rules](ci-data-history.instructions.md#model-monitoring); optional history display belongs
  to the [website rules](website.instructions.md#representative-models-sitejsmodelsjs).

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
  `paired_retail_component` (Alberta RoLR records), `no_reference_level` (a class whose printed
  eligibility fits no usage level: Lethbridge 992 and 995), `eligibility_unpublished` (class size
  limits not published: Medicine Hat 3.1 and 3.3, owner decision 2026-11-19) and, for AESO and the
  market-indexed products, `market_reference_only`, `optional_product`, `pilot` and
  `industrial_use_only`.
- A rule's optional `model.levels` lists the only usage levels its class can serve when the printed
  eligibility rules out a level that its size band includes. Other levels are excluded with a
  written reason (Lethbridge 994 is three-phase only, so s2 and m1 but not s1; owner decision
  2026-11-19).
- Out of medians (owner decision 2026-10-16): optional TOU/peak-event products and pilots outside
  Ontario (BC Hydro 2101 combinations, FortisBC 22A/32, Hydro-Quebec Flex D/G, ATCO D13). ATCO T31,
  FortisAlberta 65, ENMAX D410 and EPCOR DAS-TOUP are supply-voltage alternatives.
- `pairs` (owner decision 2026-10-16): ENMAX Power + ENMAX Energy, ATCO Electric + DERS (without the
  admin charge, noted), EPCOR Distribution + EPCOR Energy Alberta, FortisAlberta + EPCOR Energy
  Alberta. One composite record `<wires id>+<retail id>` per wires class; each pair counts once and
  each charge keeps its own source. The RoLR variant applies only below 250,000 kWh/year (12 x the
  level's kWh); above it the market variant is wires plus a value-less pool-price energy line
  (`market_energy_pending`). Retailer fees, losses and unpriced conditional charges are excluded.
- Alberta cities (owner decisions 2026-11-04 and 2026-11-19):
  - Lethbridge and Red Deer are single-utility pairs units: the City's wires class plus its own Rate
    of Last Resort record.
  - Medicine Hat's bundled 1.1 counts once as flat. Its conservation charge is costed above 950 kWh.
  - Medicine Hat 3.1 and 3.3 are not modelled (class limits unpublished), nor are 4.1 and 5.1.
  - Lethbridge 991 serves every residential level.
  - Every Alberta unit is a service area: `coverage.contributor_noun` is "service area(s)".
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
  because both utilities' billing pages confirm monthly billing (owner decision 2026-10-30). Summerside
  Electric's residential and General Service I blocks follow the same rule (batch 18, its manual's
  billing period is about one month); its seasonal schedules stay `null`. Grand Forks' commercial block
  is per two-month billing period (`two_months`, like BC Hydro 1101).
- Only these conversions are allowed: $/day x 30.4375; $/30 days x 30.4375/30; "$/two months" / 2 for
  charges printed per two-month billing period (FortisBC; batch 18: Nelson Hydro and New Westminster
  bi-monthly basic charges); per-day energy blocks x 30.4375 (Hydro-Quebec Rate D 40 kWh/day); kVA at
  PF 0.9. Never assume any other conversion.
- Municipal utilities registered in batch 18 join their province's medians like any registered utility
  (owner decision 2026-11-04); their percentage riders of the billed amount (New Westminster) are
  disclosed but not applied, like every percentage adjustment (retained for this milestone by the
  owner on 2026-11-17).

## Costing rules

- A record's cost includes the unconditional components in effect at the as-of date. Conditional,
  alternative, optional, expired and not-yet-effective components, percentage adjustments and
  value-less market components are excluded and counted, except the reviewed `reference_customer`
  entries.
- A record is not computable when its energy components exist but none is in effect, or when its own
  `end_date` is before the as-of date ("record ended on ...", as the coverage gate treats it; owner
  decision 2026-11-19). A scraper whose bundled price expires sooner than its other charges ends the
  record with it (Medicine Hat). Pairs keep the wires record's dates; their expired Rate of Last
  Resort energy already blocks them.
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
  Alberta service areas).
- `coverage.utilities_in_province` counts the province's registered units with live records, except
  a market operator whose only records are value-less price references (`market_reference_only`:
  AESO), which sells nothing to the model's customers (owner decision 2026-11-20).

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
