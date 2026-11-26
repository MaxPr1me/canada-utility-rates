---
description: "Use when changing representative models, model change monitoring, their inputs or the views that read them. Covers crosswalk rules, required contributors, usage levels, taxes, block periods, model states, the estimated market energy (method 7S-2) and the observed benchmark, semantic change history, the quarter-end model costs for Rate History, METHOD_VERSION, Across-Canada constraints and the spark gap comparison (method SG-1: comparison fuels, heating values, heating-oil prices, efficiencies, break-even COP)."
applyTo: "pipeline/representative_models.py, pipeline/archetype_profiles.py, pipeline/model_monitoring.py, pipeline/spark_gap.py, scripts/fetch_heating_oil.py, tests/test_model_monitoring.py, tests/test_model_cost_quarterly.py, tests/test_archetype_profiles.py, tests/test_spark_gap.py, tests/test_heating_oil_prices.py, data/models/**, data/fuel/**, site/js/models.js, site/js/across-canada.js, site/js/spark-gap.js, site/css/models.css, site/css/across-canada.css, site/css/spark-gap.css, site/data/representative_models.json, site/data/model_change_history.json, site/data/model_cost_quarterly.json, site/data/spark_gap.json"
---
# Representative models

Models are comparison indicators (`provenance: "modeled"`): never a billed tariff, a forecast, a quote
or live coverage. Page presentation: [website.instructions.md](website.instructions.md). Market inputs:
[market-data.instructions.md](market-data.instructions.md).

## Method, export and tests

- Every export carries `method_version` from `METHOD_VERSION`. Each owner-approved method change has
  received a new version (7C-3: decisions of 2026-10-30; 7C-4: market benchmark sidecars,
  2026-11-02; 7D-1: residential gas models, 2026-11-04; 7D-2: commercial gas, reviewed class bounds
  and the s1/s2 levels, decisions of 2026-11-20; 7T-1: territorial models, decisions 64-79 of
  2026-11-24; 7S-1: an opt-in simulated-shape sidecar and province-specific m1/l1 levels, requested by
  the owner 2026-11-25; 7S-2: estimated market energy in the main table and one m1/l1 customer per band
  for every province, owner decisions 119-123 of 2026-11-25); update the tests that assert it.
- `export_json.export_all()` calls `export_representative_models()` after the other exports
  (`MODEL_PROVINCES` = all 13 jurisdictions: ON, AB, BC, MB, NB, NL, NS, PE, QC, SK, YT, NT, NU;
  `zone_policy="median_of_zones"`). The
  hook imports lazily and writes `site/data/representative_models.json` through a temporary file and
  `os.replace`; any failure is logged, keeps the previous file and never fails the export.
- CLI: `python -m pipeline.representative_models --coverage` and/or `--build [--output PATH]
  [--rates PATH] [--province XX ...] [--as-of YYYY-MM-DD]`.
- Sum floats with `math.fsum` in the engine and market code: Python 3.12's built-in `sum()` differs
  from 3.11 and once moved a median by a cent.
- Tests use frozen record fixtures (`tests/fixtures/rm_records_sample.json`, `rm_engine_sample.json`,
  `rm_records_b12.json`, `rm_records_b14.json`, `rm_records_ws_6d.json`, `rm_records_7d_gas.json`,
  `rm_records_7d2_gas.json`, `rm_records_b18.json`, `rm_records_b18_ab.json`, `rm_records_t.json`), so the
  pre-scrape CI tests never depend on the live export.
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
- Semantic fingerprints omit routine timestamps, machine paths and the legacy synthetic fields
  (`illustrative`, `illustrative_all_in`, `synthetic_profiles`, `simulated_profiles`, kept so older
  histories still compare). Method 7S-2's estimated market energy is part of the models: the level costs
  and `level.market_energy_estimate` are recorded, and its inputs are fingerprinted
  (`usage_levels.market_energy_shapes` and the build's `assumptions.market_energy_shapes`, whose archetype
  summary carries a SHA-256 of the simulated values). The model-level `energy_estimate` (building list,
  assumptions) stays out of the snapshot, so the monthly market window roll shows only through the costs.
  The `market_energy_estimate` check reports a model whose estimate failed on an input until a refresh
  makes it again. Preserve first-match rule order. Fingerprint allowlisted input fields,
  not whole mixed-purpose files; use the actual loaded configuration and reviewed block-period,
  percentage-rider and subsidy inputs from that build. Monitoring alone does not change `METHOD_VERSION`.
- `site/data/model_change_history.json` keeps the last recorded semantic baseline, append-only
  hash-linked events, per-model last-change dates and the exact successful generation receipt.
  Initialization is labelled as a baseline, not a historical price change. Unchanged rebuilds
  advance refresh metadata, not last-change dates. Disclose skipped recording intervals; never
  reset corrupt history to hide a failure. Writes are atomic and retain prior history on failure.
- `python -m pipeline.model_monitoring --dry-run` checks local files without writing history or
  contacting GitHub. Only explicit `--record --receipt PATH` records a generation; `--report PATH`
  writes diagnostics. A receipt must match the model fingerprint, generation date, as-of and
  method. Missing, failed or malformed evidence is not success.
- Quarter-end costs for the Rate History tab (owner decisions 50, 55 and 57 of 2026-11-23 and 80 of
  2026-11-24): after `--record` has written the history, it rewrites `site/data/model_cost_quarterly.json`
  (`--quarterly PATH`; default next to `--history`) from that history alone. A quarter shows the
  published medians before and with tax and rebates in effect at its end: the state after the last
  recorded refresh generated (UTC date) on or before its last day; the current quarter is labelled in
  progress. `history_states()` rebuilds earlier states backwards from the latest snapshot and refuses a
  history that does not reproduce its own recorded changes. An unavailable level has no cost (a gap,
  never zero); `recording_gap` marks a completed quarter whose next recorded refresh followed an
  unrecorded one; base levels and observed benchmarks are separate series. `break_before` marks a
  change of the model's cost basis or of the level's example customer (kWh, kW, quantity, unit) between
  two points, including a level removed and added again, and a whole model removed and added again
  (its earlier cost basis is not recorded; decision 84, 2026-11-24); a label-only change (the
  Reference/Sensitivity role) or a method-version bump alone never breaks a series. A failure is logged
  and keeps the previous file without changing the history, its checks or the exit status.
- Freshness, workflow evidence and issue recovery belong to the
  [CI rules](ci-data-history.instructions.md#model-monitoring); optional history display belongs
  to the [website rules](website.instructions.md#representative-models-sitejsmodelsjs).

## Gas models (Phase 7D: method 7D-1, owner decision 2026-11-04; method 7D-2, owner decisions 2026-11-20)

- `MODEL_FUELS` = electricity and gas; gas models are built for `GAS_MODEL_SECTORS` (residential and
  commercial). Any other gas key would be withheld and listed in `input.withheld_gas_models` (none
  today). Contract-demand, interruptible, seasonal, peaking and load-factor classes are crosswalk
  exclusions (`gas_models_phase_7d`) until their own decision (decision 4, 2026-11-20).
- Default utility supply only. Propane, optional RNG, Customer Choice/marketer and delivery-only
  products are crosswalk exclusions. Liberty Utility Gas (an optional supply at cost) is the New
  Brunswick reference supply through a reviewed `reference_customer` entry (decision 7); without it
  the NB models fail closed.
- Native units, never converted or merged: a gas model's records must price exactly one volume unit
  (`gas_volume_unit`: `$/m³` -> m3, `$/GJ` -> GJ); mixed or missing units leave the model with no
  level. Homes use `gas.residential` (100/200/400 m3 or 4/8/16 GJ); commercial models use the
  building-size bands `commercial_small` (500/1,000/2,000 m3 or 15/30/60 GJ) and `commercial_medium`
  (2,500/5,000/10,000 m3 or 100/200/400 GJ), each a reference level with x0.5 and x2 sensitivity
  levels (decision 16). Level output carries `quantity`, `unit` and `role`, with `kwh`/`kw` null. A
  future cross-unit comparison converts toward m3, with its heating-value source decided then.
- Class selection (decision 16): every general-service class of a utility lists both building bands,
  and at each level the engine uses the class whose published limits contain the level's annual
  volume (12 x the level). Reviewed crosswalk `usage_bounds` gas entries quote the wording that says
  whether a limit itself is included (ATCO 100 GJ/month = 1,200 GJ/yr is Low Use, "or less"); an
  entry whose numbers differ from the stored bounds, or a level exactly on a stored bound without
  an entry, is not computable. Liberty's classes and customer charges follow the monthly peak, the
  level x the `peak_month_factors` entry (1.85, decision 17). Union Rate 01/M1 and ATCO Low Use
  (stored as residential) also serve the commercial models through the rule's `model.also`, with
  commercial taxes (decision 18). Centra's elective Small and Large General Service count once, as
  the cheaper at each level, named (`elective_classes`, decision 19).
- Energir Rate D1 (decision 8): one metering device (`$/metering device/day` x 30.4375); the
  basic-fee band whose annual window strictly contains 12 x the level (`fixed_charge_variants` rule
  `qc-energir-basic-fee-band`; a level on a band boundary is not computable); daily blocks
  (`m³/day`) x 30.4375; load balancing below 75,000 m3 a year only (a `reference_customer` entry
  with an annual limit, so 10,000 m3/month is not computable); both renewable-gas socialization
  charges included (decision 22).
- `price_basis(..., volume_unit=...)` accepts only the model's own volume unit; gas block thresholds
  are monthly or daily volumes in that unit. Annual thresholds only select bands or classes, never
  blocks; `$/m³/month` demand charges are unsupported. `commodity` components count as energy. Tax
  thresholds in kWh never apply to gas. Heritage Gas's municipal riders A and B are percentages,
  disclosed but not applied, as for homes.
- The Representative Models page shows gas levels in m³ or GJ with Reference/Sensitivity tags and
  the class used at each level; Across-Canada's residential electricity sub-tab stays residential electricity only.

## Inputs and crosswalk (`data/models/crosswalk.json`)

- Use only the latest live records: the site's dedupe, then `provenance == "live"`.
- Rules are ordered and the first match wins: each record maps to {province, fuel, sector, structure,
  size band} or to an exclusion reason. Require 0 unmapped (`--coverage`); the coverage report lists
  the intentional rule overrides.
- Exclusion reasons include `gas_models_phase_7d` (gas classes outside the Phase 7D models:
  contract-demand, interruptible, seasonal, peaking and load-factor services in every province),
  `government_rate` (territorial government account classes, including Qulliq's municipal tax-based
  commercial class; decision 71), `territory_planned_later` (a territorial class outside the first
  release: Naka's Taltson Large General Service),
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
  level's kWh); above it the market variant is wires plus a value-less pool-price energy line, estimated
  in the m1/l1 models (method 7S-2) and `market_energy_pending` otherwise. Retailer fees, losses and unpriced conditional charges are excluded.
- Alberta cities (owner decisions 2026-11-04 and 2026-11-19):
  - Lethbridge and Red Deer are single-utility pairs units: the City's wires class plus its own Rate
    of Last Resort record.
  - Medicine Hat's bundled 1.1 counts once as flat. Its conservation charge is costed above 950 kWh.
  - Medicine Hat 3.1 and 3.3 are not modelled (class limits unpublished), nor are 4.1 and 5.1.
  - Lethbridge 991 serves every residential level.
  - Every Alberta unit is a service area: `coverage.contributor_noun` is "service area(s)".
- `required_contributors`: withhold a level (reason `withheld`, state `not_computable`) when a listed
  utility is not computable there (NL residential needs Newfoundland Power).
- `usage_bounds`: quoted eligibility limits. Electricity entries (`min_annual_kwh`/`max_annual_kwh`)
  apply as the level's kWh x 12 when the record publishes them only in text. Gas entries (`unit`
  m3/GJ, `basis` annual or peak_month, `min`/`max` with `min_inclusive`/`max_inclusive`, `quote`,
  `source`) decide class selection (see Gas models).
- `demand_bounds`: reviewed inclusivity of a kW class limit where the published wording differs from
  the engine default `[min, max)` (FortisBC Electric Rate 20 "not more than 40 kW", so s2 at 40 kW
  stays on Rate 20; Rate 21 is "greater than 40 kW"). Different stored numbers fail closed.
- A rule's `model.also` lists further {sector, structure, size_band} targets that the same record
  serves (decision 18: Union 01/M1 and ATCO Low Use in the commercial gas models).
- `elective_classes`: classes open to the same customers, of which the model prices the cheapest at
  each level and names it in the utility row (`elective_classes` notes) and the model (Centra Small
  and Large General Service, decision 19).
- Classes whose kW limits cross a reference level were re-checked when s2 moved to 40 kW
  (2026-11-23): BC Hydro Rate 1500 (35-150 kW) also lists the small band, so BC Hydro is priced on it
  at s2 (decision 28); no other class limit lies at 14 or 40 kW.

## Usage levels and reference customer (`data/models/usage_levels.json`)

- **Documented backing (owner decision 2026-11-20):** every typical energy-use level and load
  profile, electricity or gas, records three things where it is defined: the decision (who
  approved it and when), why it was chosen, and what it represents (customer or building type,
  size, period and units). Back it with official sources (utilities, regulators, statistical
  agencies, government programs) and, where they exist, peer-reviewed research data, each cited
  with its title, URL or DOI, date and the exact figure used. A sensitivity level or a simulated
  or made-up profile says so; never present one as typical or observed. In `usage_levels.json` each
  level carries `decided`, `represents`, `why` and `sources` (title, url, date, figure; "computed"
  marks arithmetic on published cells); sensitivity levels may have no source and say so in `why`.
- Owner-approved levels: residential 500, 1,000 and 2,000 kWh (1,000 is the reference level, 500
  and 2,000 sensitivity levels, decision 29); commercial under 50 kW 2,000 kWh at 14 kW (s1) and
  10,000 kWh at 40 kW (s2, three phase; decisions 27-28 of 2026-11-20 replaced 10 kW and 8,000 kWh
  at 25 kW); 50-499 kW 25,000 kWh at 100 kW (m1); 500-4,999 kW 250,000 kWh at 1,000 kW (l1). There
  is no 5,000 kW+ level (those models report buckets only). Gas levels: see Gas models.
- m1 and l1 are sized from the simulated archetypes for every province (owner decision 120,
  2026-11-25, method 7S-2): the runs in each size band use a median 260 and 256 kWh per kW of average
  monthly peak, and Hydro-Quebec's price comparison prints 100 kW at 25,000 kWh. They replaced 40,000
  kWh at 100 kW and 500,000 kWh at 1,000 kW (Ontario bill-impact customers, kept for Ontario and Alberta
  by method 7S-1). The known difference is documented in the levels: Ontario's GS 50 kW and over and
  Large User classes use more per kW. A level's optional `provinces` list (unused since 7S-2) limits
  where it applies; exactly one entry per level id may apply to a province (a second one fails the
  build). The territories have no m1/l1 models (decision 73). `tests/test_archetype_profiles.py`
  re-derives the band figures quoted in the level sources.
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
  riders and the SSS administration charge; Energir's renewable-gas socialization charges and load
  balancing (with `annual_volume` below 75,000 m3; outside it the record is not computable). An entry
  with `exclusion: "optional"` unlocks an optional component instead (Liberty Utility Gas).
- `fixed_charge_variants` (owner decision 2026-10-30): fixed charges published as phase or amperage
  variants (alternatives or unmarked variants) are never summed. A rule prices exactly one variant per
  level: homes at single-phase 200 A; commercial under 50 kW single phase at s1 and three phase at
  s2. Since 7D-2 a rule may instead select by the level's monthly peak (`peak_month` range, Liberty's
  customer charges) or by annual-volume band (`select: annual_volume_band`, Energir's basic fee), and
  may name a `province`, `utility` and `tariff_code`. Reason `fixed_charge_variant:<id>`, disclosed per
  model and per utility row. No match or more than one match leaves that utility not computable at
  that level; Manitoba GS Small (Demand) (50-499 kW, no variant rule) stays unavailable without
  phase/history assumptions.
- `peak_month_factors`: the peak month as a multiple of the average month for a province, fuel and
  sectors (NB commercial gas 1.85: Statistics Canada NB commercial deliveries, January 2025 against the
  average month; decision 17), disclosed as the model's `peak_month_factor`.

## Block periods and unit conversions

- A kWh block threshold without a stated period needs a reviewed `data/models/block_periods.json`
  entry (`threshold_period`) that quotes the tariff or the utility's billing page. `null` means no
  stated period: the record is left out instead of guessed (Maritime Electric seasonal 133/233,
  Manitoba GS seasonal).
- NB Power GS1 and Maritime Electric 110/130/131/232 "per Billing Period" blocks count as per month
  because both utilities' billing pages confirm monthly billing (owner decision 2026-10-30). Summerside
  Electric's residential and General Service I blocks follow the same rule (batch 18, its manual's
  billing period is about one month); its seasonal schedules stay `null`. Grand Forks' commercial block
  is per two-month billing period (`two_months`, like BC Hydro 1101). Yukon's joint rate book prints
  "Charges for service in any one billing month", so its blocks count per month (7T-1).
- Only these conversions are allowed: $/day x 30.4375; $/30 days x 30.4375/30; "$/two months" / 2 for
  charges printed per two-month billing period (FortisBC; batch 18: Nelson Hydro and New Westminster
  bi-monthly basic charges); per-day energy blocks x 30.4375 (Hydro-Quebec Rate D 40 kWh/day; Energir
  D1 m³/day, 7D-2); $/metering device/day x 30.4375 for one metering device (Energir D1, decision 8);
  kVA at PF 0.9. Never assume any other conversion.
- An unseasoned first block followed by seasonal blocks applies in every season (Liberty LGS: block 1
  all year, block 2 Sep-Apr and May-Aug); its bounds must agree across seasons.
- Municipal utilities registered in batch 18 join their province's medians like any registered utility
  (owner decision 2026-11-04); their percentage riders of the billed amount (New Westminster) are
  disclosed but not applied, like every percentage adjustment outside the territories' reviewed list
  (retained for this milestone by the owner on 2026-11-17; see Territorial models).

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
- Ontario loss factors and Class A GA are not modeled; the method text says so, and an estimated model
  states its contributing records' published total loss factors (decision 122).

## Zones, statistics and states

- Each utility counts once, as the median of its standard zones (`median_of_zones`, owner decision
  2026-10-09; `default_only` is the alternative policy, an open default).
- Per level: median, n, min, p25, p75, max, the real utility closest to the median, and outliers
  (more than 30% from the median or outside 1.5 x IQR, n >= 3), which are named with their distance
  from the median, never removed.
- States: `modeled`, `single_source`, `market_energy_estimated` (the Ontario and Alberta m1/l1 models
  with estimated market energy, method 7S-2), `market_energy_pending` (market-priced energy without an
  estimate: the 5,000 kW and over models, or an m1/l1 model whose estimate input failed) and
  `not_computable`. Estimated models have energy status `market_estimated` and cost basis
  `delivery_and_estimated_market_energy`; `energy.market_pending` still lists the value-less components. `coverage.contributor_noun` names the contributors (utilities, distributors, or
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
- Commercial gas (decision 23, 2026-11-20): Saskatchewan shows a PST line at 0% with medium
  confidence (the building-heating exemption; commercial water heating and cooking may be taxable at
  6%, not modelled); the Alberta Natural Gas Rebate Program is named in the Alberta gas methods
  (`NOT_APPLIED`), with no line while the price is below its $6.50/GJ trigger; claim-based rebates
  are left out; BC PST and ICE stay separate lines.
- Heating oil (spark gap, decision 151, 2026-11-26): `jurisdictions[province]["heating_oil"]["residential"]`
  lines (NB HST 15%; NS HST 14% less YERP 9%; PE 5% as IRAC prints it; NL HST 15%; YT and NT GST 5%)
  only take the tax out of Statistics Canada's as-paid oil prices; the models never read them and model
  monitoring leaves them out of the input fingerprints.

## Territorial models (method 7T-1, owner decisions 64-79, 2026-11-24)

- Scope: Yukon, the Northwest Territories and Nunavut, residential and small commercial (s1, s2)
  non-government classes (decision 75). Government classes are `government_rate` (decision 71), Naka's
  Taltson Large General Service is `territory_planned_later` and NTPC's interruptible heating is
  excluded. Levels are the provincial ones, with documented northern reference points (decision 73).
- Contributors: Yukon's joint YUB rate book counts once, as Yukon Energy (crosswalk
  `shared_rate_books`; Yukon Electrical Company is a `duplicate_variant`; decision 66). The NWT models
  are NTPC and Naka Power, each the median of its zones (decision 65). Interim rates (Qulliq since
  April 1, 2025; Naka's July 1, 2026 riders) are included and labelled (crosswalk `interim_rates`,
  `model.interim` and a warning; decision 72).
- Percentage riders (`data/models/percentage_riders.json`, decision 64): each reviewed entry quotes what
  its percentage applies to. `apply` prices it as that percentage of the named base charges, never of
  other riders: Yukon Riders R, J and J1, and Naka Riders R, E and H, whose base includes the fuel charge
  (decision 79; Naka's July 2026 notice reconciles only that way). `exclude` keeps a percentage of the
  whole bill disclosed (Naka's franchise tax). `subsidy` is left out of the cost before subsidies and
  applied only after them (the Yukon Affordability Rate Relief, while its component dates include the
  as-of date; decision 70). A percentage component of a territorial record without an entry makes the
  record not computable. Provincial percentage adjustments are unchanged (disclosed, not applied).
- Subsidies (`data/models/subsidies.json`): every level shows its cost before subsidies (the tariff,
  with GST like the provinces) and, where the jurisdiction allows it, the median after the automatic
  subsidies (`level.after_subsidy`, utility rows `cost_after_subsidy`) before tax only: no with-tax
  after-subsidy figure until bills or official text confirm the GST base (decisions 67 and 74). A
  subsidy counts as automatic only where an official source says so.
  - Applied: the NWT TPSP first block at 36.50 cents/kWh all-in (it replaces the whole per-kWh price of
    the first-block kWh; NTPC's riders and its Cost of Living Subsidy apply above it; decision 76),
    month-weighted like the Ontario RPP tiers: 7/12 at 1,000 kWh and 5/12 at 600 kWh
    (`usage_levels.seasons.NT_TPSP`, decision 68); NTPC's Cost of Living Subsidy on every kWh where
    no first block applies; Naka's GREP for non-government Thermal homes, whose all-in reference
    prices replace Naka's own Thermal price and riders (decision 78); the Yukon relief (decision 70).
  - Not applied, named: NTPC's Snare zone first block (no stored price: its stated saving does not
    reconcile; decision 77) and Nunavut's NESP (no published price: Nunavut is before subsidy only;
    decision 69). Commercial models have no after-subsidy figure: no automatic subsidy with a
    published general-service amount applies (NTPC's credit also covers commercial customers but has
    no published general-service value). Naka's 30-day pro-rating of the TPSP block is not modelled.
- The territorial models depend on stored component names and notes that these lists match (for
  example "GNWT TPSP First-Block Energy Price (...)", "Rider J - Base Rate Adjustment"); a scraper
  change that renames them must update the lists, or the record fails closed.
- Both lists fail closed and never fail a build. A missing or unreadable file states its problem: with
  no percentage riders, territorial percentage components are not computable; with no subsidies, no
  after-subsidy figure is published. An unreviewed or malformed entry is skipped with its reason and never
  applied: a skipped rider leaves its record not computable, and a skipped program publishes no
  after-subsidy cost for its territory and sector. An applied program (`treatment` `reference_rates`,
  `first_block_price` or `per_kwh_credit`) needs `automatic` (the official text and its URL); a first
  block states `replaces.all_energy` and its `seasons`; reference rates state `replaces.all_charges` and
  their `required_components`, and apply only to the zone records `applies_to` selects; `absent` names
  the zone records without a stored price, with the reviewed reason; `disclose` programs are only named.

## Estimated market energy (method 7S-2, owner decisions 119-123 of 2026-11-25)

- History: owner decisions 11 and 12 (2026-11-20) replaced the Phase 7E made-up business-hours profile
  (`synthetic_profiles`, 2026-10-16) with the simulated archetypes priced on the observed market bins.
  Method 7S-1 (owner request 2026-11-25) did it as an opt-in sidecar; method 7S-2 replaced the sidecar
  the same day. No opt-in estimate remains.
- Scope (decision 119): the Ontario and Alberta 50-499 kW and 500-4,999 kW electricity models, whose
  market energy has no stored value. The estimate is in the main table (costs, medians, outliers,
  closest utility, change history and Rate History), labelled estimated, states its assumptions, never
  counts as live coverage, and falls back to `market_energy_pending` when an input fails (safeguard 8's
  exception in AGENTS.md).
- Shape (decision 121, `usage_levels.market_energy_shapes.BTAP_NECB2020_BAND_GENERAL_SHAPE`): every
  validated archetype run of the province (Toronto, Calgary) whose average monthly peak (mean of the 12
  monthly highest 15-minute demands) is in the model's crosswalk size band, both heating fuels. Each
  run's market-clock bins and months are divided by its own yearly kWh (the same yearly use, counted
  once) and averaged; the general shape is priced once by `market_pricing.load_shape_price()` (checks
  in [market-data.instructions.md](market-data.instructions.md)). Each run is also priced alone for the
  published list and range, and a flat load gives the same-use-every-hour price. Runs come from
  `pipeline/archetype_profiles.py` (reads and checks `data/btap/`: totals against `output.xlsx`,
  15-minute steps, IESO bins in EST, AESO bins in prevailing time; a failing run is left out with its
  reason; `archetype_fingerprint()` hashes the values used).
- Applying it: price x the level's kWh is added to each market-priced record's cost and energy
  subtotal before the tax lines and the per-utility medians (`level.market_energy_estimate`
  {price_per_kwh, cost}; utility rows `estimated_market_energy`). The level's kWh and kW are unchanged
  (decision 120: the general shape is used as it is, no constant-load fit). Records with a stored
  energy price are never estimated.
- `model.energy_estimate`: available, reason, input_problem, profile, price, flat price, price range,
  window, market file, shape summary (buildings, cities, heating fuels, quality flags, month weights,
  shape factors), the buildings and plain-language `assumptions` (Ontario adds `loss_factors`: the
  published secondary-metered total loss factors of the contributing records, read from the
  scraper's note and never applied, decision 122). A model the shape covers but whose records all have
  a stored energy price gets `available: false` with `input_problem: false`.
- Fail closed: a flat-load probe checks the market file before any run is read; any doubtful input (the
  shape settings, size-band limits, the market file or window, the archetypes, no run in the band, a
  run or the shape that cannot be priced, an unexpected error) leaves the estimate unavailable with its
  reason, the model `market_energy_pending` (method text and page say why) and never fails the build.
  Model monitoring's `market_energy_estimate` check reports it.
- Inputs sit under `assumptions.market_energy_shapes` (profiles, an archetype summary without machine
  paths but with the data fingerprint, the market files) and are fingerprinted (Change monitoring).
- No real commercial load profile is qualified: Toronto Hydro's EB-2023-0195 Exhibit 7 example is
  illustrative (its full-year attachment and rights are unverified), and FortisAlberta's assigned
  settlement shapes are not observed commercial class loads.

## Market benchmark sidecars (method 7C-4)

- Separate `model.market_benchmark` and `level.market_benchmark` objects for the Ontario and Alberta
  commercial market-only levels, priced by `historical_market_price()` (its checks are in the
  market-data instructions; settings in `usage_levels.market_benchmarks`).
- Ontario uses energy + actual Class B GA; Alberta uses pool energy only. Add the benchmark energy
  before the per-zone taxes and statistics.
- A benchmark is the 60-complete-month historical energy average plus today's modeled delivery: not a
  forecast, a retail quote or a customer-profile-weighted bill, and it never replaces the base table.
  It prices the delivery-only costs (never on top of the estimated energy) and is shown as the
  same-use-every-hour comparison in the energy note (decision 123) and as Rate History's benchmark line.

## Across-Canada (`site/js/across-canada.js`)

- Two sub-tabs (owner decision 144, 2026-11-26): "Residential electricity" (this section, the default)
  and "Spark gap" (next section).
- Residential electricity only, at 500, 1,000 or 2,000 kWh (default 1,000), with tax by default and a
  before-tax option; all 13 jurisdictions; rate structures stay separate.
- Read the model file through the shared loader in `models.js`. Never recalculate bills, never use
  estimated, simulated or benchmark values (only complete modeled residential costs enter Across-Canada) and never show a computed bill
  breakdown.
- Chart and table share one eligibility rule. Show missing, pending and withheld states explicitly,
  and never turn a missing model into a zero bar. Territorial totals are before subsidies (decision
  74): their rows and bars say "before subsidies", and each row states the published cost after
  automatic subsidies, before tax, or why there is none (Nunavut).

## Spark gap (method SG-1, owner decisions 118 and 124-165, 2026-11-25 and 2026-11-26)

`pipeline/spark_gap.py` writes `site/data/spark_gap.json`; `site/js/spark-gap.js` shows it. Reviewed
inputs: `data/models/spark_gap.json` (each value with its decision, why, what it represents, its
official source and the date it was checked). It is a comparison aid of running costs only: never a
bill, a savings estimate or a forecast, and never in model medians, the change log, Rate History,
change checks or coverage (decision 143).

- **What it compares:** step 1, the spark gap = the electricity price ÷ the comparison fuel's price per
  kWh of energy, before efficiency; step 2, the break-even heat pump COP = spark gap × efficiency
  (decisions 128 and 135). Cents per kWh headline, $/GJ alongside (decision 134); 1 GJ = 277.7778 kWh.
- **Who:** one row per province and territory for homes; small and mid-size buildings only in the eight
  gas provinces, paired with electricity s2 and m1 (decisions 125, 126 and 136).
- **Comparison fuel (decision 146):** each region's most common heating fuel other than electricity
  among the fuels with an official price: gas in BC, AB, SK, MB, ON and QC; heating oil in NB, NS, PE,
  NL and the territories; businesses gas only. Wood and propane are left out, their shares named (147).
- **Prices (decisions 129-131, 137, 139-142):** average = the whole monthly bill, fixed charges included,
  ÷ its energy, at the same energy for both fuels (homes 2,000 kWh = 7.2 GJ; s2 36 GJ; m1 90 GJ, gas
  priced in whichever class its own limits select); marginal = the next kWh (businesses at the same
  load factor: kW grows by kW/kWh) and the next m³ or GJ above 400 m³/16 GJ, 2,000 m³/60 GJ or 5,000
  m³/200 GJ. Prices come from `build_models(..., exact_costs=True)` (unrounded per-utility and
  per-record costs; off for the published models) at the spark gap's own levels: electricity keeps the
  model level ids (reviewed rules tied to them still apply) and fails if the point no longer equals the
  model level; gas runs once per published heating value. A utility whose next unit changes its records
  is left out of the marginal median and named.
- **One price per region (decision 131):** the median across utilities, each counted once. Reviewed
  choices settle a utility found in several models: Ontario electricity uses the TOU models only;
  BC Hydro homes use the plan that costs less at the average point (159); EPCOR Ontario gas is the
  median of its two systems (160). Any other overlap makes the row not available (fail closed). Only
  models in state modeled, single_source or market_energy_estimated count (the Ontario and Alberta
  mid-size estimate is labelled, 138); a pending or withheld level makes the row not available.
- **Gas heating values (153):** a record billed in m³ uses its utility's published value (reviewed
  entries matched by utility and optional `tariff_code_regex`), else the CER 37.3 MJ/m³, labelled; GJ
  needs none. The gas models keep their native units: the conversion is for this comparison only.
- **Heating oil (148-152, 164, 165):** `scripts/fetch_heating_oil.py` reads Statistics Canada Table
  18-10-0001-01 (household heating fuel, six city vectors) through the Web Data Service into
  `data/fuel/heating_oil_prices.json`, keeping every month; a stored month whose value changes stops
  the refresh (nothing written); unavailable values are stored without a price. The engine uses each
  region's latest usable month (dated on the page), as paid including sales tax; the before-tax price
  divides by 1 + the reviewed `heating_oil` sales taxes - rebates in `taxes.json` (none reviewed: before
  tax not available). Energy: 38.80 MJ/L (Statistics Canada energy accounts, derived). Average and
  marginal are equal. Nunavut is not available (no official price found).
- **Efficiency and realistic COP (155-158, 163):** homes, the new-equipment AFUE minimums of SOR/2016-311
  (gas 95%, oil 83%); businesses, both commercial gas minimums as a range (furnace 80%, hot-water
  boiler 90%, thermal efficiencies) and no realistic COP or words. Homes compare with the CCI/Dunsky
  2024 seasonal system COPs (standard and cold-climate, 2035 climate, backup included) of the nearest
  of five cities, labelled approximate; the territories show the break-even only.
- **Result in words (157, 161):** homes with a realistic COP, on the average price: both heat pump
  types above the break-even COP → `heat_pump_cheaper`; only cold-climate → `depends_on_heat_pump`;
  neither → `furnace_cheaper`; a note when the marginal price gives another result.
- **Views and taxes (132-133):** with tax and rebates (default) and before; the territories also show
  after automatic subsidies (electricity before tax ÷ oil before tax). Business prices with tax are as
  billed; the page notes GST/HST input tax credits.
- **Publication and monitoring (143, 152):** rebuilt after every model refresh (export, Market
  Benchmarks, Ontario Price Archive); a failed build keeps the previous file. Model monitoring's
  `spark_gap` check is described in the [CI rules](ci-data-history.instructions.md#model-monitoring).
- **Adding a gas utility billed in m³** needs a reviewed heating value entry (else the labelled CER
  factor); a utility that appears in more than one model at a spark gap point needs a reviewed choice.
