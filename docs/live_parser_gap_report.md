# Live Parser Gap Report

**Updated:** 2026-10-02
**Scope:** Building-energy parser coverage, including single-family homes, with completed non-building schedules retained as reference.

**Evidence:** October 2 batches `6cdbc67` and `9b5980d` cover Hydro-Quebec,
NL Hydro, SaskEnergy, FortisBC Electric, NSPower and Centra Gas. Other records retain
their earlier October 1 observations. The export dated 2026-10-02 19:08 UTC has
139 stored live versions (137 latest records) and 480 seed versions across 84 utilities.
Of those, 135 latest live records belong to 12 of the 16 campaign utilities.
History remains preserved. This documentation reconciliation is not a new source
run; fixtures, export timestamps and process-success counts alone do not prove live coverage.

**Provenance:** complete fresh extraction uses `mark_live_parsed()`; contextual
verification of known values uses `verify_official_records()`. Seed fallbacks remain
unverified and hidden by default. Several utilities now have multiple live classes,
but **none should be called building-coverage-complete without an audit of the
relevant published building-service schedules**. Non-building services are explicit
exclusions, not required gaps. Cent glyph variation must be handled without accepting dollars
as cents or borrowing a value from a different class/column.

## Summary

The table includes all sixteen campaign utilities and the two utilities with retained
live output outside the campaign. ON/AB/YT/NT/NU remain excluded from new work.
Only SaskPower's audited building schedules have a recorded scoped completion;
other live utilities still have catalogue, component or verification gaps.

| Utility | Province | Page Type | Parser Status | Residential | Commercial | Confidence |
|---------|----------|-----------|---------------|-------------|------------|------------|
| **Manitoba Hydro** | MB | Server-rendered (line-pair text) | Live parser | Flat rate | GS Small Non-Demand/Demand/Seasonal, GS Medium, GS Large (3 voltage tiers) | High |
| **NB Power** | NB | Server-rendered tables | Live parser | Flat rate | GS1 (tiered+demand), Small Industrial | High |
| **Nova Scotia Power** | NS | Approved PDF + product pages; business HTML | Ten live records, catalogue partial | Standard, storage TOD, conditional pilots, MURB89; solar adjustments span multiple classes | Existing Rate 10/11/12 HTML path | High for parsed rates; pilot and subscriber applicability conditional |
| **BC Hydro** | BC | Approved residential PDF + business HTML | Live parser | Tiered, flat, both time-of-day combinations; closed dual fuel | SGS, MGS, LGS | High |
| **Hydro-Québec** | QC | Official PDF + product pages | Nine live records, catalogue partial | D/DP/DM/DN/DT/Flex D and closed Winter Credit adjustment | G/M; broader building options still under audit | High for parsed classes; conditional credits explicit |
| **SaskPower** | SK | Rendered landing page + PDFs | Audited building scope implemented | E01/E03 standard + bulk-metered option; diesel E04 | General service, voltage/TOU/capacity and R23/R24; other records retained as reference | High for complete parsed classes |
| **NL Hydro** | NL | Current-rates page + July approved PDF | Dynamic parser, 18 live records | Island/Labrador/diesel/government and seasonal options | Native kW/kVA and service alternatives; Burgeo school/library | High for complete source classes |
| **SaskEnergy** | SK | Four official HTML pages | Six live full/delivery-only variants | Residential | Small/large commercial | High only with current carbon evidence |
| **FortisBC Electric** | BC | Approved Electric Tariff PDF | Six current schedules, broader catalogue partial | Flat1, closedTOU2A | 20/21/22A/23A with conditional credits and demand alternatives | High for complete parsed schedules |
| **Centra Gas Manitoba** | MB | Current utility HTML + CRA applicability | Twelve live service variants | SGS and marketer-supply variant | SGS/LGS/high-volume/mainline/interruptible Sales/T-service | High with required commodity/carbon evidence |
| **FortisBC Energy** | BC | Configured utility rate pages | Seed verification only; zero live | Seed reference only | Current service-area/class extraction pending | Unverified fallback |
| **Energir** | QC | Configured utility rate pages | Seed verification only; zero live | Seed reference only | Current distribution/supply/balancing extraction pending | Unverified fallback |
| **Heritage Gas / Eastward Energy** | NS | Configured utility rate pages | Seed verification only; zero live | Seed reference only | Current official building schedules pending | Unverified fallback |
| **Liberty Utilities NB** | NB | Configured utility rate pages | Seed verification only; zero live | Seed reference only | Current official customer-class extraction pending | Unverified fallback |
| **Newfoundland Power** | NL | PDF-only | Dynamic PDF parser | Domestic 1.1 | General Service 2.1/2.3/2.4 | High for parsed classes |
| **Maritime Electric** | PE | IRAC PDF | Dynamic PDF parser | Urban/rural | 10 supported classes total | High for parsed classes |
| **FortisAlberta** | AB | AUC/utility PDF | Residential PDF parser | Rate 11 | Other classes remain fallback | High for parsed residential |
| **Yukon Energy** | YT | Cross-reference and current rider PDFs | Partial: separate base/rider/relief parsing | Hydro 1160 | Other classes remain fallback; image-only base schedules | High for supported current residential |

## Group A: HTML Parsing for Supported Classes

### Manitoba Hydro
- **URL:** `hydro.mb.ca/accounts_and_services/rates/residential_rates/`
- **Parser:** Residential via text regex; commercial via a line-pair section parser (each class header, then `label` line + value on the next line). Cent glyph handled agnostically; lone footnote-marker lines are filtered so they cannot split a label from its value.
- **Coverage:** Residential (flat); GS Small Non-Demand, GS Small Demand, GS Seasonal, GS Medium, and GS Large at three voltage tiers (>750 V-30 kV / >30-100 kV / >100 kV)
- **Fragilities:** Section boundary detection depends on header text ("non-demand", "medium", "large ... exceeding"); page restructuring would break it
- **Seed update:** 2024-04-01 → 2026-01-01

### NB Power
- **URL:** `nbpower.com/en/products-services/residential/rates` and `/business/rates`
- **Parser:** Table extraction with merged-cell handling (Base/Variance/Total format)
- **Coverage:** Residential (now flat, was tiered), GS1 (demand + tiered energy), Small Industrial
- **Fragilities:** NB Power's merged table cells require custom parsing; residential structure change (tiered→flat) shows rates can restructure
- **Seed update:** 2024-04-01 → 2026-04-14 (structural change: residential tiered→flat)

### Nova Scotia Power
- **Sources:** official standard/TOD/TOU/critical-peak pages plus the linked May 2026 `tariff-book-2026.pdf`, all registered. The approved book and matching dated product pages establish the current rate version; future 2027 rows are not reused as current rates.
- **Standard 02/03/04:** stable `Domestic Service` identity, $20.08/month, base energy $0.18324/kWh; separate FAM $0.00156, DSM $0.00648 and storm $0/kWh. The resulting published energy components agree with the advertised 19.128 cents/kWh, without adding riders twice. Optional $5/month Green Power blocks are labelled opt-in, each representing 125 kWh.
- **TOD 05/06:** requires electric thermal storage or qualifying in-floor storage with approved controls. December-February has four weekday blocks; March-November has two. Weekends/holidays take the overnight rate. Seasonal month sets and source clock windows are preserved, not borrowed from the TOU pilot.
- **TOU 80 and CPP 70:** enrollment is closed. October records are named `Conditional Pilot` with explicit interim-phase eligibility and an October 31 end date. The tariff makes interim applicability depend on system-restoration provisions; the scraper does not verify an individual participant's restoration status or assert that every customer is on this phase. Product pages' advertised time-varying prices are not substituted for dated interim charges.
- **Dated transition:** November 1, 2026 winter prices are implemented and tested but not activated on October 2. TOU uses source-derived morning/evening windows and holiday rules; CPP uses declared four-hour events and published event/notice limits. Stable plan names let a newer phase supersede its old version in the latest-per-name browser. Rates after the supported 2026 tariff/rider year fail closed pending a new review.
- **MURB and solar:** Rate89 adds its General/MURB FAM/DSM/storm rows, ten-unit house-meter eligibility and minimum bill as a condition. The printed peak-price weekend/holiday rule was visually checked. Solar Garden and Community Solar are separate optional adjustments, credited against subscriber-attributable generation rather than household consumption.
- **Verification:** the latest October 2 dry run/store returned ten valid live records. The fixture includes MURB pages35-37, matching rider rows, Solar Garden69-73 and Community Solar80-83. Permanent tests cover required continuations, billing basis, positive prices and repeat storage/export; the current full suite has 465 passing tests. Desktop/mobile checks passed and prior history/non-target data were retained.
- **Still incomplete:** operational confirmation of which pilot phase applies to existing participants, further building-service classes, and full business10/11/12 rider/date coverage. MURB and the two solar adjustments are implemented, not pending extraction. Residential product pages are not the entire building tariff catalogue.

### BC Hydro
- **Sources:** residential tiered/flat/time-of-day pages and the approved Electric Tariff PDF registered in `data/sources/registry.json`. Business service retains its separate HTML parser.
- **Residential coverage:** RS 1101 tiered, RS 1151 flat, 1101 + 2101 tiered/TOD, 1151 + 2101 flat/TOD, and closed dual-fuel RS 1105. Live output is five residential plus three business tariffs.
- **Source values:** flat energy 12.70 cents/kWh and 25.00 cents/day; tiered energy 11.87/14.08 cents/kWh and 23.44 cents/day. Base schedules are effective April 1, 2026; current RS 2101 is effective July 1, 2026.
- **Time-of-day:** daily overnight 23:00-07:00 credit of 5 cents/kWh, on-peak 16:00-21:00 surcharge of 5 cents/kWh, otherwise zero adjustment. These modify base energy, not replace it. Optional eligibility excludes separately metered common property; published EV-metering conditions remain in the tariff.
- **Riders and conditions:** RS 1901 is source-verified -1.5%, RS 1904 is 0%; neither applies to 2101 adjustments. Transformer-ownership discount is conditional for premises with more than three units, not a universal household credit. Tier thresholds distinguish monthly/bi-monthly billing and daily prorating. Closed 1105 eligibility is explicit.
- **Verification:** `bc_hydro_residential.json` holds source-derived page excerpts. Nineteen BC-focused tests cover products, source mutation, missing continuations/riders, future dates, divergent monthly prices and repeat storage. The current full suite has 465 passing tests. BC Hydro's last recorded source run remains October 1: eight live records, not a fresh regional-run catalogue audit.

## Group B: PDF-Parsed — Live Data from Official PDFs

### Hydro-Québec
- **Sources:** [approved electricity-rates PDF](https://www.hydroquebec.com/data/documents-donnees/pdf/electricity-rates.pdf) and registered D/DP/DM product pages. The PDF remains usable if the residential landing page fails. The edition date is read from its cover, not a seed or grandfathering notice; missing/future dates fail closed.
- **Coverage:** nine records: D, DP, grandfathered DM, northern off-grid DN, DT, Flex D, closed Winter Credit adjustment, G and M. Domestic products use page-aware sections with required continuations and shared definitions/adjustments; existing D/G/M identities are unchanged. Rate D's charge anchor includes article2.5 so it cannot borrow another schedule's rows.
- **DP:** $0.06878/$0.10458 per kWh, first 1,200 kWh per 30-day monthly period. Demand above 50 kW is $5.369/kW/month in April-November and $7.266 in December-March. The 65-percent winter minimum-demand rule and $13.833 single-phase/$20.750 three-phase minimum bills remain conditions, not extra fixed charges. Non-30-day billing periods are prorated by the tariff rules.
- **DM:** only qualifying bulk-metered contracts eligible on May 31, 2009. System access is $0.46154 per multiplier per day; $0.07065/$0.11142 per kWh with the first allowance of 40 kWh/day/multiplier. Demand is $7.266/kW/month above max(50 kW, 4 kW x multiplier), subject to the published minimum-demand rule. The multiplier depends on eligible dwellings/rooms and mixed-use conditions; no occupancy count or fixed demand threshold is invented.
- **DN:** domestic off-grid supply north of the 53rd parallel, except Schefferville, with the source's other eligibility exceptions retained. System access is $0.46154/multiplier/day; energy is $0.07065/$0.50469 per kWh with the first 40 kWh/day/multiplier. The multiplier defaults to one unless the contract was DM-eligible on May 31, 2009; the whole DN tariff is not grandfathered. Demand is $7.266/kW/month above the source-derived base allowance, with the 65-percent winter demand ratchet. The DT off-grid exclusion is explicit. Both pages and complete kW/percentage rules are required; malformed DN does not downgrade DP/DM.
- **Conditional adjustments:** DP carries five alternative voltage-credit bands from article 12.2, not five cumulative rebates. DM carries the article 12.3 credit of $0.002818/kWh only for qualifying supply voltage/ownership; DN explicitly incorporates that conditional credit through article 9.2. Transformation-loss conditions are retained as text, not a calculated adjustment or bill total.
- **Optional products:** DT pages21-24 preserve dual-energy equipment, climate-zone temperature switching and the off-grid exclusion. Flex D pages32-34 preserve seasonal tiers, notified events and enrollment restrictions. Winter Credit pages29-31 retain the closed enrollment cutoff, reference-energy/temperature-adjustment rules and notification exceptions; it is an adjustment to Rate D, not a separate base price or calculated credit total.
- **Fixture and verification:** [hydro_quebec_domestic.json](../tests/fixtures/hydro_quebec_domestic.json) covers these options plus DP/DM/DN, shared definitions, credits and proration. DM/DN multiplier continuations were visually checked for arithmetic omitted by text extraction. The latest October 2 dry run/store returned nine live records. Tests cover signed values, required source context, future dates, independent failures and persistence; the current full suite has 465 passing tests. Prior snapshots and other utilities were preserved.
- **Remaining:** Inukjuak domestic dual-energy (page139 onward), net-metering eligibility/settlement and other building business options. DT/Flex D/Winter Credit are implemented. Crop-production options remain excluded from the building campaign.

## SaskPower: October 1 Implementation

- **Discovery:** render the official power-supply-rates landing page when needed, then fetch its linked schedules. Failure of one PDF does not discard independent complete classes.
- **Live result:** 41 valid tariffs, all with live provenance; three residential variants, 25 supplied/customer-owned records, R23/R24 renewable access and 11 retained farm/oil-field references. Source schedules are effective February 1, 2026.
- **Residential:** standard E01/E03 remains one stable record only while both city/rural columns match. Bulk-metered service is a separate closed-to-new option with fixed charges per apartment unit or trailer stall. Diesel E04 preserves first-650-kWh and balance energy tiers. Missing or changed rows fail by section, not by borrowing another page's values.
- **Renewable access:** R23/R24 preserve 72-kV/100-kV-and-above charges, participant/self-generation eligibility and the continuation-page demand rule.
- **Supplied transformation:** standard E05/E06 and small commercial E75/E76. Urban/rural energy thresholds differ; both include a free first demand block and a paid balance in kVA. The old flat small-commercial seed was not the current structure.
- **Other supplied services:** E37 irrigation preserves the February-October pumping season, fixed seasonal charge and horsepower-based demand charge. E15/E16/E17/E18 unmetered schedules preserve 100-watt, equipment-unit, 10-watt and installed-kVA units respectively. E35 diesel preserves both energy tiers. Paired schedules on pages 6 and 7 are parsed independently and cannot borrow adjacent rates or minimum-bill conditions.
- **Farm and oil-field (retained reference only):** farm E34/E19/E41 preserve tiers, seasonal versus monthly per-meter-location charges and closed-to-new interruptible eligibility. Oil-field E43/E44 retain per-metering-point charges and a 60-percent demand rule; E46-E48/E86-E88 preserve voltage columns, TOU and billing conditions. This completed work is kept, but further expansion is outside the building-focused campaign.
- **Customer-owned transformation:** standard E07/E08/E10/E12; small commercial E77/E78; power TOU E82/E83/E84; power standard E22/E23/E24; capacity reservation N22/N23/N24. Voltage columns remain distinct; E10/E12 are identified as closed to new customers.
- **Billing context:** preserve minimum-bill rules, demand ratchets and TOU hours from continuation pages. These are source conditions, not a calculated bill total. kVA eligibility is kept as text rather than written into kW-only fields.
- **Safety gates:** require complete column counts, source dates that are not future dates, correct currency/units, and required continuation data. Reject malformed groups independently. Known failed classes retain unverified seeds; unknown classes are logged, not invented.
- **Fixtures:** six SaskPower JSON fixtures cover residential, supplied/customer-owned transformation, renewable access and retained farm/oil-field PDFs, with source URLs, retrieval dates, page numbers and table/condition excerpts.
- **Tests:** 53 focused SaskPower parser/storage/export cases; 465 tests in the current full suite. Coverage includes source-value mutations, cent glyph variation, wrong units/signs, missing/reordered/divergent columns, dates, failed fetches, required continuations, per-unit billing, seasonal/equipment units, historical closure notices, repeated storage and shared-code/codeless-class identity.
- **Persistence:** targeted storage/export retained all 519 previous snapshots and unchanged non-SaskPower records. The two old generic commercial seed records remain labelled estimates; history was not deleted.

**Building audit result:** the currently published building-service schedules linked
from the power-supply-rates catalogue are implemented and live-checked on October 1.
This covers net published charges and conditions, not a tax-inclusive bill calculation.
Standalone streetlight, reseller, agricultural and oil-field processes are outside the
completion target. The 41 live records include reference-only data, not 41 building classes.

The [registry](../data/sources/registry.json) records the landing page and six supported
PDFs. SaskPower remains `partial` for the broader utility catalogue; its audited building
scope is implemented. Maintain it while the regional campaign addresses remaining
in-scope gas and building-catalogue gaps. Yukon and other excluded-region work stays deferred.

## Other PDF Capabilities and Gaps

### NL Hydro: Building-Service Extraction
- **URL:** `nlhydro.com/electicity-rates/current-rates/` (note: typo "electicity" is their actual path)
- **Status:** The July 2026 schedule now rebuilds 18 current Island/Labrador/diesel building-service and seasonal-option records. Required class/charge/minimum/maximum/eligibility context fails independently; optional seasonal adjustments require their matching live base schedule. Fixed phase/amperage rows are alternatives, not cumulative charges.
- **Coverage:** Island residential/seasonal and general-service classes, Burgeo school/library, government/non-government diesel, and Labrador residential/general-service schedules. Native kW/kVA, monthly diesel blocks, required minimum/maximum bills and service-area eligibility are retained. Seasonal adjustments require a complete same-date base schedule.
- **Fixture and dates:** [nl_hydro.json](../tests/fixtures/nl_hydro.json) contains the approved July1,2026 charge pages. Live values are rebuilt from the source; the older January2026 seed versions remain estimates/history, not current pricing evidence.
- **Remaining:** net-metering/commissioning and contract-specific industrial applicability need review. These are not automatically non-building exclusions. Missing mandatory context rejects the affected class; updating a seed is not a substitute for fixing extraction.

### Newfoundland Power
- **URL:** `newfoundlandpower.com/en/My-Account/Usage/Electricity-Rates`
- **Status:** Rebuilds supported classes from the linked official RateBook PDF.
- **Coverage:** Domestic Service 1.1 and General Service 2.1, 2.3 and 2.4; four live records in the integrated October 1 export.
- **Remaining gap:** Audit building-relevant published service and add source-derived success/failure fixtures beyond the existing seed-path checks.

### Maritime Electric, FortisAlberta and Yukon Energy

- **Maritime Electric:** ten supported classes parsed from one IRAC schedule. Preserve individual charges; prioritize building-relevant service rather than all industrial process products.
- **FortisAlberta:** Rate 11 residential parses live; building-relevant distribution classes need source-specific extraction. The October 1 CI observation updates its official schedule URL. The shared verifier is not a complete multi-class parser.
- **Yukon Energy:** Rate 1160 now uses base fixed/energy columns with separate R/J/J1 percentages, current fuel Rider F and dated affordability relief. The prior combined R/J-only interpretation omitted J1/F/relief. The corrected October 1 version contains nine components, each with source details; no total is calculated. Relief ends March 31, 2027, applies only to eligible non-government residential energy up to 1,500 kWh, and excludes fuel/fixed charges.
- **Yukon verification:** 18 focused tests cover missing documents or changed context, future/expired dates, negative/wrong-unit base rows, rider applicability, source mutation and persistence of rebate limits/end dates. The live dry run returned one live 1160 tariff plus two labelled seed fallbacks. Both old and new 1160 versions remain stored; latest-per-name counts must not count this as a second supported class.
- **Yukon blocker:** the linked detailed 1160 residential and 2160 general-service PDFs are valid image-only documents (no text from `pdfplumber`). Their rendered pages confirm monthly residential billing and a multi-tier/demand general-service structure. The readable cross-reference contains only the fourth general-service energy block, so it cannot rebuild a complete GS tariff. Use OCR with reviewed fixtures or authoritative text alternatives before adding general-service, government/diesel variants or Rider A. No OCR dependency was added in this batch. Wholesale and standalone lighting remain excluded.

## Aggregate Statistics

| Metric | Value |
|--------|-------|
| Registered utilities | 84 |
| Stored/exported tariff versions | 619, including history and older retained estimates |
| Rate components | 3,935 |
| Latest live tariffs / utilities with live output | 137 / 14 |
| Stored live versions | 139; includes older versions retained in history |
| Seed tariffs | 480 |
| Newly added SaskPower live tariffs | 40 since the original residential-only parser |
| October 1 observations | Monthly CI snapshot plus newer local SaskPower results |
| Deterministic suite | 465 passing |

## Regional Batch 2 Update (2026-10-02)

Published as `9b5980d`; GitHub Pages deployment succeeded. This batch's test and
preservation results remain the current implementation checkpoint.

FortisBC Electric now reconstructs approved January 2026 RS1/2A/20/21/22A/23A.
RS1 is flat, not the old seeded tiered structure; 2A requires its closed notice.
Conditional primary/transformation discounts are negative rebates. RS21 kW/kVA
charges are alternatives, not cumulative. Required source pages/dates/hours and
nonpositive-price guards have permanent tests. Large-commercial/Green Power/
financing/net-metering/EV schedules remain catalogue gaps.

NSPower adds MURB89 with its own mandatory rider rows, ten-unit house-meter
eligibility and minimum bill retained as a condition. The printed Note1 applies
the peak price on weekends/holidays; this was visually verified. Solar Garden and
Community Solar are optional subscriber adjustments to other tariffs, with credits
on allocated generation only. Existing pilot-status and broader business/rider/date
coverage remain partial; the legacy business change warnings are not new prices.

Centra Gas adds twelve dated August 2026 variants. Published delivery/demand totals
are checked against component parts without double counting. Native volumetric
demand units and the separate April 2025 CRA zero-fuel-charge evidence are retained.
Marketer/T-service excludes unpublished commodity. Full PUB eligibility, alternate
supply conditions, billing-demand rules and fixed-term products still need audit.

465 full tests and 6/10/12-record current-source checks pass. Serial storage kept
all 1,241 earlier snapshots and 587 non-target records unchanged, adding 28 snapshots.
Desktop/mobile filtering and estimate hiding passed without page overflow/JS errors.
The campaign now has live output at 12 of its 16 utilities; utility completion is
not implied. The next seed-only gas targets are FortisBC Energy, Energir,
Heritage/Eastward and Liberty NB. All excluded regions remain unchanged.

## Regional Batch 1 Update (2026-10-02)

Published as `6cdbc67`; the figures below describe that earlier milestone, not the
current aggregate. This batch replaced the former DT-first and verifier-only paths.
HQ now has nine live records, adding DT, Flex D and the closed Winter Credit
adjustment. DT retains temperature-zone equipment/eligibility, Flex D notified
events and seasonal tiers, and Winter Credit the reference-energy calculation
rules and notice exceptions without calculating a total. Source pages 21-24,
29-31 and 32-34 extend the existing domestic fixture.

NL Hydro's new fixture covers the dated July 2026 building pages: eighteen classes,
including two seasonal adjustments. Net-metering/commissioning and contract-specific
industrial applicability remain explicit gaps. SaskEnergy's new fixture covers
residential/commercial base and supply components, retailer eligibility and the
required dated zero-carbon amendment. Its six records distinguish full supply from
delivery-only service with private commodity excluded. Missing carbon evidence
rejects live output; small industrial/fees/municipal-payment scope remains open.

All 33 first-batch records passed current official-source checks and were stored
serially. 428 tests passed at that milestone, including permanent source corruption and repeat-storage
cases. All 1,208 earlier snapshots and 561 non-target records were preserved; no
excluded province was updated. Utility catalogue completion has not been claimed.

## Recommended Next Steps

1. Implement FortisBC Energy, Energir and Heritage/Eastward in parallel, then Liberty NB. These four in-scope utilities still have no live output; establish the complete required sources before extracting their building classes.
2. Resolve the documented remaining classes, eligibility, rider/date and fixture gaps at the twelve already-live target utilities. Maintain SaskPower's audited building schedules without expanding non-building references. Do not repeat the delivered HQ optional-product or NSPower MURB/solar work.
3. Finish with a sixteen-utility restricted source refresh, class-level coverage reconciliation, full tests and preserved-history/export checks. Ontario, Alberta and the territories stay excluded from this campaign and retained in the data.
4. Keep browser-enabled source health, outcome reporting, durable CI history and deployment-trigger reliability on the separate operational track. A successful deployment of this milestone does not resolve those automation gaps.

## Phase 5-wide Status

Use [phase5_completion_matrix.md](phase5_completion_matrix.md) as the maintained
per-utility ledger and [README.md](../README.md) for the ordered roadmap. Ontario's
53 registry identities still need a current distributor/merger audit. Official URL
discovery, effective dates, building-class interpretation and source-derived fixtures remain
material work; a fail-safe seed verifier is not a completed dynamic parser.
