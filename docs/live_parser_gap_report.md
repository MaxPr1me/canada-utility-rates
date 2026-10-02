# Live Parser Gap Report

**Updated:** 2026-10-02
**Scope:** Building-energy parser coverage, including single-family homes, with completed non-building schedules retained as reference.

**Evidence:** October 2 NSPower and Hydro-Quebec results are combined with October 1 local
BC Hydro/SaskPower/Yukon and monthly CI observations. History remains preserved.
The current export has
91 stored live versions (89 latest tariffs) and 480 seed tariffs across 84 registered utilities. A fixture or verifier
implementation alone is not evidence of a successful live run.

**Provenance:** complete fresh extraction uses `mark_live_parsed()`; contextual
verification of known values uses `verify_official_records()`. Seed fallbacks remain
unverified and hidden by default. Several utilities now have multiple live classes,
but **none should be called building-coverage-complete without an audit of the
relevant published building-service schedules**. Non-building services are explicit
exclusions, not required gaps. Cent glyph variation must be handled without accepting dollars
as cents or borrowing a value from a different class/column.

## Summary

| Utility | Province | Page Type | Parser Status | Residential | Commercial | Confidence |
|---------|----------|-----------|---------------|-------------|------------|------------|
| **Manitoba Hydro** | MB | Server-rendered (line-pair text) | Live parser | Flat rate | GS Small Non-Demand/Demand/Seasonal, GS Medium, GS Large (3 voltage tiers) | High |
| **NB Power** | NB | Server-rendered tables | Live parser | Flat rate | GS1 (tiered+demand), Small Industrial | High |
| **Nova Scotia Power** | NS | Approved PDF + product pages; business HTML | Residential source parser, broader coverage partial | Standard, storage TOD, conditional interim TOU/CPP pilots | Existing Rate 10/11/12 HTML path | High for published rates; pilot applicability is explicitly conditional |
| **BC Hydro** | BC | Approved residential PDF + business HTML | Live parser | Tiered, flat, both time-of-day combinations; closed dual fuel | SGS, MGS, LGS | High |
| **Hydro-Québec** | QC | Official PDF + product pages | PDF live parser, catalogue partial | D, seasonal-demand DP, grandfathered bulk-metered DM, northern off-grid DN | Rate G (mixed), Rate M (demand) | High for parsed classes; conditional credits are explicit |
| **SaskPower** | SK | Rendered landing page + PDFs | Audited building scope implemented | E01/E03 standard + bulk-metered option; diesel E04 | General service, voltage/TOU/capacity and R23/R24; other records retained as reference | High for complete parsed classes |
| **NL Hydro** | NL | PDF + inline text | Official PDF component verification | Rural + Labrador | General Service | High when verified |
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
- **Verification:** 32 focused NSPower tests; 350 full-suite tests at its checkpoint. Live dry run and targeted stored scrape returned seven valid live records: four residential variants and the three existing business records. The source fixture covers residential section boundaries and mandatory rider rows. Storage/export tests preserve conditions, dates, sources and snapshots. Desktop/mobile browser checks verified four residential options, storage eligibility, conditional notices and comparison scrolling. Non-NSPower data and prior snapshots were unchanged.
- **Still incomplete:** operational confirmation of which pilot phase applies to existing participants, MURB TOU (listed at tariff-book page 35), Solar Garden and Community Solar riders (pages 69/80), and further building-service classes. The residential product pages are not the entire building tariff catalogue. Existing business 10/11/12 remains on its prior HTML parser; this batch does not certify its full rider/date coverage.

### BC Hydro
- **Sources:** residential tiered/flat/time-of-day pages and the approved Electric Tariff PDF registered in `data/sources/registry.json`. Business service retains its separate HTML parser.
- **Residential coverage:** RS 1101 tiered, RS 1151 flat, 1101 + 2101 tiered/TOD, 1151 + 2101 flat/TOD, and closed dual-fuel RS 1105. Live output is five residential plus three business tariffs.
- **Source values:** flat energy 12.70 cents/kWh and 25.00 cents/day; tiered energy 11.87/14.08 cents/kWh and 23.44 cents/day. Base schedules are effective April 1, 2026; current RS 2101 is effective July 1, 2026.
- **Time-of-day:** daily overnight 23:00-07:00 credit of 5 cents/kWh, on-peak 16:00-21:00 surcharge of 5 cents/kWh, otherwise zero adjustment. These modify base energy, not replace it. Optional eligibility excludes separately metered common property; published EV-metering conditions remain in the tariff.
- **Riders and conditions:** RS 1901 is source-verified -1.5%, RS 1904 is 0%; neither applies to 2101 adjustments. Transformer-ownership discount is conditional for premises with more than three units, not a universal household credit. Tier thresholds distinguish monthly/bi-monthly billing and daily prorating. Closed 1105 eligibility is explicit.
- **Verification:** `bc_hydro_residential.json` holds source-derived page excerpts. Nineteen BC-focused tests cover products, source mutation, missing continuations/riders, future dates, divergent monthly prices and repeat storage. Current full suite: 382 passing. Its completed live dry run/store/export returned eight valid live tariffs; other utilities and prior snapshots were preserved.

## Group B: PDF-Parsed — Live Data from Official PDFs

### Hydro-Québec
- **Sources:** [approved electricity-rates PDF](https://www.hydroquebec.com/data/documents-donnees/pdf/electricity-rates.pdf) and registered D/DP/DM product pages. The PDF remains usable if the residential landing page fails. The edition date is read from its cover, not a seed or grandfathering notice; missing/future dates fail closed.
- **Coverage:** D, DP, grandfathered DM, northern off-grid DN, G and M. DP/DM/DN use page-aware sections with required continuations and shared definitions/adjustments; existing D/G/M identities are unchanged. Rate D's charge anchor includes article 2.5 so it cannot borrow another domestic schedule's rows.
- **DP:** $0.06878/$0.10458 per kWh, first 1,200 kWh per 30-day monthly period. Demand above 50 kW is $5.369/kW/month in April-November and $7.266 in December-March. The 65-percent winter minimum-demand rule and $13.833 single-phase/$20.750 three-phase minimum bills remain conditions, not extra fixed charges. Non-30-day billing periods are prorated by the tariff rules.
- **DM:** only qualifying bulk-metered contracts eligible on May 31, 2009. System access is $0.46154 per multiplier per day; $0.07065/$0.11142 per kWh with the first allowance of 40 kWh/day/multiplier. Demand is $7.266/kW/month above max(50 kW, 4 kW x multiplier), subject to the published minimum-demand rule. The multiplier depends on eligible dwellings/rooms and mixed-use conditions; no occupancy count or fixed demand threshold is invented.
- **DN:** domestic off-grid supply north of the 53rd parallel, except Schefferville, with the source's other eligibility exceptions retained. System access is $0.46154/multiplier/day; energy is $0.07065/$0.50469 per kWh with the first 40 kWh/day/multiplier. The multiplier defaults to one unless the contract was DM-eligible on May 31, 2009; the whole DN tariff is not grandfathered. Demand is $7.266/kW/month above the source-derived base allowance, with the 65-percent winter demand ratchet. The DT off-grid exclusion is explicit. Both pages and complete kW/percentage rules are required; malformed DN does not downgrade DP/DM.
- **Conditional adjustments:** DP carries five alternative voltage-credit bands from article 12.2, not five cumulative rebates. DM carries the article 12.3 credit of $0.002818/kWh only for qualifying supply voltage/ownership; DN explicitly incorporates that conditional credit through article 9.2. Transformation-loss conditions are retained as text, not a calculated adjustment or bill total.
- **Fixture and verification:** [hydro_quebec_domestic.json](../tests/fixtures/hydro_quebec_domestic.json) retains cover, definitions, DP pages 17-18, DM pages 19-20, DN pages 127-128, credits page 152 and monthly proration page 154. DM/DN multiplier continuations were visually checked because plain extraction omits standalone plus signs. Thirty-seven focused tests and 382 full-suite tests pass, including source mutation, territory/default-multiplier drift, missing continuations, units/signs, demand rules, publication dates and repeat storage/export. The October 2 DN dry run/store returned six valid live records. All 1,202 prior snapshots and 565 other-utility records were preserved; six snapshots were appended. Database validation: zero errors, two existing AESO class warnings. Desktop/mobile checks confirmed four domestic classes, DN eligibility/prices, estimate hiding and horizontal comparison scrolling without page overflow or JavaScript errors.
- **Remaining:** DT dual-energy (pages 21-24), Flex D, Winter Credit, Inukjuak domestic dual-energy (139 onward), and net-metering eligibility/settlement. Winter Credit has a grandfathering restriction in the current edition; do not assume open enrollment. These are discovery leads, not implemented rates. Crop-production options remain excluded from the building campaign.

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
- **Tests:** 53 focused SaskPower parser/storage/export cases; 382 tests in the current full suite. Coverage includes source-value mutations, cent glyph variation, wrong units/signs, missing/reordered/divergent columns, dates, failed fetches, required continuations, per-unit billing, seasonal/equipment units, historical closure notices, repeated storage and shared-code/codeless-class identity.
- **Persistence:** targeted storage/export retained all 519 previous snapshots and unchanged non-SaskPower records. The two old generic commercial seed records remain labelled estimates; history was not deleted.

**Building audit result:** the currently published building-service schedules linked
from the power-supply-rates catalogue are implemented and live-checked on October 1.
This covers net published charges and conditions, not a tax-inclusive bill calculation.
Standalone streetlight, reseller, agricultural and oil-field processes are outside the
completion target. The 41 live records include reference-only data, not 41 building classes.

The [registry](../data/sources/registry.json) records the landing page and six supported
PDFs. SaskPower remains `partial` for the broader utility catalogue; its audited building
scope is implemented. Monitor source drift and proceed to Yukon Energy building coverage,
not excluded catalogue expansion.

## Other PDF Capabilities and Gaps

### NL Hydro: Verification Only
- **URL:** `nlhydro.com/electicity-rates/current-rates/` (note: typo "electicity" is their actual path)
- **Status:** The code attempts contextual verification of seeded components against a linked PDF; the integrated October 1 export contains no live NL Hydro tariffs. This is not automatic extraction of changed schedules.
- **Coverage:** Rural Residential, Labrador Interconnected, General Service.
- **Remaining gap:** Source drift is flagged and rejected; changed values still require a reviewed seed update.
- **Seed update:** 2024-04-01 → 2026-01-01; energy rates updated from page text (island 15.213¢, Labrador 3.154¢)

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
| Stored/exported tariff versions | 571, including history and older retained estimates |
| Rate components | 3,732 |
| Latest live tariffs / utilities with live output | 89 / 10 |
| Stored live versions | 91; includes older Yukon and NSPower standard versions |
| Seed tariffs | 480 |
| Newly added SaskPower live tariffs | 40 since the original residential-only parser |
| October 1 observations | Monthly CI snapshot plus newer local SaskPower results |
| Deterministic suite | 382 passing |

## Recommended Next Steps

1. Maintain the implemented SaskPower building schedules; retain non-building classes as reference without expanding them.
2. Continue after Hydro-Quebec DP/DM/DN: start with DT's dual-energy equipment and temperature-zone rules, then Flex D/Winter Credit and FortisBC's current electric tariff. NSPower's four core residential variants are implemented; participant pilot status and MURB/solar riders remain partial. The broad national audit is still incomplete.
3. Continue building coverage across provinces/territories, nine gas utilities, Alberta wires/default retail and necessary market references, then Ontario's approved distributor schedules.
4. Repair the existing non-blocking source-health workflow's browser setup and outcome reporting; keep normal tests network-free. Durable CI history and deployment triggering are separate operational follow-ups.

## Phase 5-wide Status

Use [phase5_completion_matrix.md](phase5_completion_matrix.md) as the maintained
per-utility ledger and [README.md](../README.md) for the ordered roadmap. Ontario's
53 registry identities still need a current distributor/merger audit. Official URL
discovery, effective dates, building-class interpretation and source-derived fixtures remain
material work; a fail-safe seed verifier is not a completed dynamic parser.
