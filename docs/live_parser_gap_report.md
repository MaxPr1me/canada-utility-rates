# Live Parser Gap Report

**Updated:** 2026-10-06 (batch 9 stored and exported)
**Scope:** Building-energy parser coverage, including single-family homes and building-related industrial general facility service defined by size, voltage or interruptibility. Process-specific farm, oil-field, irrigation, NGV fuelling, EV charging, lighting, wholesale/reseller and standby-only service is excluded; completed non-building schedules remain reference.

**Evidence:** The October 6 batch 9 export has 214 stored live versions (209
latest records across 18 utilities) and 480 seed versions across 84 utilities. Of those,
207 latest live records belong to all 16 campaign utilities. DB validation: 0 errors,
2 existing AESO warnings; 1,570 snapshots (106 appended, prior snapshots unchanged).
History remains preserved. Fixtures, export timestamps and process-success counts alone do not prove live coverage.

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
| **NB Power** | NB | Server-rendered tables | Live parser, 10 records | Flat and rural/seasonal Rate D | GS I, Small/Large Industrial; water-heater rental and SureConnect; lighting/charging reference | High for complete source classes |
| **Nova Scotia Power** | NS | Approved PDF + product pages; business HTML | 14 live records, catalogue partial | Standard, storage TOD, conditional pilots, MURB89; solar adjustments span multiple classes | Rate 10/11/12 and conditional pilots 72/73/82/83 | High for parsed rates; pilot and subscriber applicability conditional |
| **BC Hydro** | BC | Approved PDFs + business HTML | 11 live records, catalogue partial | Tiered, flat, both time-of-day combinations; closed dual fuel and RS1289 generation credit | SGS, MGS, LGS, RS1830 Transmission | High for parsed classes; conditional credits explicit |
| **Hydro-Québec** | QC | Official PDF + product pages | 25 live records, catalogue partial | D/DP/DM/DN/DT/Flex D, Winter Credit, Inukjuak, net metering I/III | G/G9/M, Flex G/M/G9, dual-energy, Winter Credit G, net metering I for M; L/LG/H and Demand Response Leeway | High for parsed classes; conditional credits explicit |
| **SaskPower** | SK | Rendered landing page + PDFs | Audited building scope implemented | E01/E03 standard + bulk-metered option; diesel E04 | General service, voltage/TOU/capacity and R23/R24; other records retained as reference | High for complete parsed classes |
| **NL Hydro** | NL | Current-rates page + July approved PDF | Dynamic parser, 21 live records | Island/Labrador/diesel/government and seasonal options | Native kW/kVA and service alternatives; Burgeo school/library, Island/Labrador Industrial Firm and conditional net-metering credit | High for complete source classes |
| **SaskEnergy** | SK | Four official HTML pages | Six live full/delivery-only variants | Residential | Small/large commercial | High only with current carbon evidence |
| **FortisBC Electric** | BC | Approved Electric Tariff PDF | 11 live records, broader catalogue partial | Flat1, closedTOU2A | 20/21/22A/23A, RS30/32 large commercial primary, RS31/33 transmission and optional RS85; conditional credits and demand alternatives | High for complete parsed schedules |
| **Centra Gas Manitoba** | MB | Current utility HTML + approved PUB schedule PDF + CRA applicability | Twelve live service variants | SGS and marketer-supply variant | SGS/LGS/high-volume/mainline/interruptible Sales/T-service with approved eligibility/demand/alternate-supply conditions | High with required commodity/carbon/schedule evidence |
| **FortisBC Energy** | BC | Official HTML rate pages + tariff index + BC carbon notice | 11 live records, catalogue partial | Rate 1 Mainland/VI, Fort Nelson and Revelstoke propane | Rates 2/3 Mainland/VI, Fort Nelson and Revelstoke propane; Rate 5 contract and seasonal Rate 4 (Mainland/VI) | High with required carbon evidence |
| **Energir** | QC | Pricing page → linked tariff PDF | Five live records (D1 residential/business, D3, D4, D5) | Default Rate D1 | D1/D3/D4/D5; optional replacement RNG supply | High for parsed rates; conditional charges explicit |
| **Heritage Gas / Eastward Energy** | NS | Rate pages → monthly rate-table PDF + tariff PDF | Three live records | Residential | General Service (tiered); Rate Class 3 (Billing Demand unit from tariff); Rate Class 4 negotiated, unpublished | High when table and page summaries agree |
| **Liberty Utilities NB** | NB | Official HTML class/supply pages + CRA | Four live records | SGS | MGS, LGS (seasonal blocks); Off-Peak Service | High with required commodity/carbon evidence |
| **Newfoundland Power** | NL | PDF-only | Dynamic PDF parser, 11 records | Domestic 1.1, seasonal 1.1S and conditional net-metering credit | General Service 2.1/2.3/2.4, Curtailable Option 1 for 2.3/2.4; prompt-payment and primary-voltage discounts, fees | High for parsed classes |
| **Maritime Electric** | PE | IRAC PDF | Dynamic PDF parser | Urban/rural | 10 supported classes total | High for parsed classes |
| **FortisAlberta** | AB | AUC/utility PDF | Residential PDF parser | Rate 11 | Other classes remain fallback | High for parsed residential |
| **Yukon Energy** | YT | Cross-reference and current rider PDFs | Partial: separate base/rider/relief parsing | Hydro 1160 | Other classes remain fallback; image-only base schedules | High for supported current residential |

## Group A: HTML Parsing for Supported Classes

### Manitoba Hydro
- **URL:** `hydro.mb.ca/accounts_and_services/rates/residential_rates/`
- **Parser:** Residential via text regex; commercial via a line-pair section parser (each class header, then `label` line + value on the next line). Cent glyph handled agnostically; lone footnote-marker lines are filtered so they cannot split a label from its value.
- **Coverage:** Residential flat, seasonal and diesel (including >200 A basic charge); GS Small Non-Demand/Demand/Seasonal, GS Medium and GS Large at three voltage tiers (>750 V-30 kV / >30-100 kV / >100 kV), diesel GS and government/First Nation education. Large GS voltage tiers cover building-related industrial service; preserve native kVA and seasonal rules. Failure of one residential/commercial page no longer discards the other page's live classes; 12 live records, no new tariffs in batch 9.
- **Remaining:** Curtailable, LUBD and surplus lack complete published prices; net-billing export credit $0.07173/kWh has no published start date and is not live. Standard service charges and the LUBD schedule remain unaudited.
- **Fragilities:** Section boundary detection depends on header text ("non-demand", "medium", "large ... exceeding"); page restructuring would break it
- **Seed update:** 2024-04-01 → 2026-01-01

### NB Power
- **URL:** `nbpower.com/en/products-services/residential/rates` and `/business/rates`
- **Parser:** Table extraction with merged-cell handling (Base/Variance/Total format)
- **Coverage:** Residential (now flat, was tiered), rural/seasonal Rate D, GS I (demand + tiered energy), Small Industrial (both energy tiers, 100 kWh/kW threshold and required $/kW demand), Large Industrial ($19.98/kW/month, $0.0785/kWh, billing-demand alternatives as conditions), water-heater rentals, SureConnect and retained lighting/charging references. Ten live records effective April 14, 2026. GS II merged into GS I. Reconcile base + variance; one-time fees are unmodelled because the source labels them $/month.
- **Remaining:** Net metering and interruptible/surplus prices are source-blocked.
- **Fragilities:** NB Power's merged table cells require custom parsing; residential structure change (tiered→flat) shows rates can restructure
- **Seed update:** 2024-04-01 → 2026-04-14 (structural change: residential tiered→flat)

### Nova Scotia Power
- **Sources:** official standard/TOD/TOU/critical-peak pages plus the linked May 2026 `tariff-book-2026.pdf`, all registered. The approved book and matching dated product pages establish the current rate version; future 2027 rows are not reused as current rates.
- **Standard 02/03/04:** stable `Domestic Service` identity, $20.08/month, base energy $0.18324/kWh; separate FAM $0.00156, DSM $0.00648 and storm $0/kWh. The resulting published energy components agree with the advertised 19.128 cents/kWh, without adding riders twice. Optional $5/month Green Power blocks are labelled opt-in, each representing 125 kWh.
- **TOD 05/06:** requires electric thermal storage or qualifying in-floor storage with approved controls. December-February has four weekday blocks; March-November has two. Weekends/holidays take the overnight rate. Seasonal month sets and source clock windows are preserved, not borrowed from the TOU pilot.
- **TOU 80 and CPP 70:** enrollment is closed. October records are named `Conditional Pilot` with explicit interim-phase eligibility and an October 31 end date. The tariff makes interim applicability depend on system-restoration provisions; the scraper does not verify an individual participant's restoration status or assert that every customer is on this phase. Product pages' advertised time-varying prices are not substituted for dated interim charges.
- **Dated transition:** November 1, 2026 winter prices are implemented and tested but not activated on October 2. TOU uses source-derived morning/evening windows and holiday rules; CPP uses declared four-hour events and published event/notice limits. Stable plan names let a newer phase supersede its old version in the latest-per-name browser. Rates after the supported 2026 tariff/rider year fail closed pending a new review.
- **MURB and solar:** Rate89 adds its General/MURB FAM/DSM/storm rows, ten-unit house-meter eligibility and minimum bill as a condition. The printed peak-price weekend/holiday rule was visually checked. Solar Garden and Community Solar are separate optional adjustments, credited against subscriber-attributable generation rather than household consumption.
- **Verification:** The source fixture includes MURB pages35-37, matching rider rows, Solar Garden69-73 and Community Solar80-83. Tests cover required continuations, billing basis, positive prices and repeat storage/export; the current full suite has 801 passing tests across 8 modules.
- **Business:** Rates 10/11/12 preserve FAM/DSM/storm riders and conditional transformer discounts; pilots 72/73/82/83 are conditional October-interim/November-date-gated variants, never evidence of an individual's restoration status.
- **Still incomplete:** operational confirmation of which pilot phase applies to existing participants and further building-service classes. MURB, solar and business pilots are implemented; residential product pages are not the entire building tariff catalogue.

### BC Hydro
- **Sources:** residential tiered/flat/time-of-day pages and the approved Electric Tariff PDF registered in `data/sources/registry.json`. Business service retains its separate HTML parser.
- **Residential coverage:** RS 1101 tiered, RS 1151 flat, 1101 + 2101 tiered/TOD, 1151 + 2101 flat/TOD, and closed dual-fuel RS 1105. Business 1300/1500/1600 include conditional RS1901/1904 and primary-voltage/transformation discounts; Terms and Conditions Section 11 service charges and section 7.2 power-factor surcharge (ten conditional bands, fraction of Rate section charges) fail closed for business only when required context is malformed.
- **Source values:** flat energy 12.70 cents/kWh and 25.00 cents/day; tiered energy 11.87/14.08 cents/kWh and 23.44 cents/day. Base schedules are effective April 1, 2026; current RS 2101 is effective July 1, 2026.
- **Time-of-day:** daily overnight 23:00-07:00 credit of 5 cents/kWh, on-peak 16:00-21:00 surcharge of 5 cents/kWh, otherwise zero adjustment. These modify base energy, not replace it. Optional eligibility excludes separately metered common property; published EV-metering conditions remain in the tariff.
- **Riders and conditions:** RS 1901 is source-verified -1.5%, RS 1904 is 0%; neither applies to 2101 adjustments. Transformer-ownership discount is conditional for premises with more than three units, not a universal household credit. Tier thresholds distinguish monthly/bi-monthly billing and daily prorating. Closed 1105 eligibility is explicit.
- **Transmission and net metering:** RS1830 (Apr 1, 2026, PDF pp138-140, 232-233) has $12.178/kVA/billing period and $0.04914/kWh with separate RS1901/1904 riders. Closed RS1289 (Jul 1, 2026, pp223-231) adds a conditional generation credit, not a new household supply price; indexed cash settlement is unpriced.
- **Verification:** `bc_hydro_residential.json` and `bc_hydro_business.json` hold source-derived excerpts. Nineteen residential-focused tests cover products, source mutation, missing continuations/riders, future dates, divergent monthly prices and repeat storage. Batch 9: 11 live records; the full suite has 801 passing tests. Neither is a full-catalogue audit.
- **Remaining:** RS2801/2802/2821/2822 transmission pilots, RS1892 and RS2289/2290 are open; RS1828 biomass-program contract needs a scope decision. RS1823 was cancelled. Irrigation, lighting, EV charging and wholesale/reseller service are excluded.

## Group B: PDF-Parsed — Live Data from Official PDFs

### Hydro-Québec
- **Sources:** [approved electricity-rates PDF](https://www.hydroquebec.com/data/documents-donnees/pdf/electricity-rates.pdf) and registered D/DP/DM product pages. The PDF remains usable if the residential landing page fails. The edition date is read from its cover, not a seed or grandfathering notice; missing/future dates fail closed.
- **Coverage:** 25 records: D, DP, grandfathered DM, northern off-grid DN, DT, Flex D, Winter Credit D/G, G/G9/M, Inukjuak DN dual-energy, Flex G/M/G9, three space-heating dual-energy rates, net-metering options I/III (including Option I for Rate M, application 4.28), L, LG, H and business Demand Response Leeway. Every live component carries source URL, detail and date; Rate M charges and its conditional surplus-bank reset credit remain separate. Domestic products require continuations; Rate D's article 2.5 anchor prevents borrowing another schedule's rows.
- **DP:** $0.06878/$0.10458 per kWh, first 1,200 kWh per 30-day monthly period. Demand above 50 kW is $5.369/kW/month in April-November and $7.266 in December-March. The 65-percent winter minimum-demand rule and $13.833 single-phase/$20.750 three-phase minimum bills remain conditions, not extra fixed charges. Non-30-day billing periods are prorated by the tariff rules.
- **DM:** only qualifying bulk-metered contracts eligible on May 31, 2009. System access is $0.46154 per multiplier per day; $0.07065/$0.11142 per kWh with the first allowance of 40 kWh/day/multiplier. Demand is $7.266/kW/month above max(50 kW, 4 kW x multiplier), subject to the published minimum-demand rule. The multiplier depends on eligible dwellings/rooms and mixed-use conditions; no occupancy count or fixed demand threshold is invented.
- **DN:** domestic off-grid supply north of the 53rd parallel, except Schefferville, with the source's other eligibility exceptions retained. System access is $0.46154/multiplier/day; energy is $0.07065/$0.50469 per kWh with the first 40 kWh/day/multiplier. The multiplier defaults to one unless the contract was DM-eligible on May 31, 2009; the whole DN tariff is not grandfathered. Demand is $7.266/kW/month above the source-derived base allowance, with the 65-percent winter demand ratchet. The DT off-grid exclusion is explicit. Both pages and complete kW/percentage rules are required; malformed DN does not downgrade DP/DM.
- **Conditional adjustments:** DP carries five alternative voltage-credit bands from article 12.2, not five cumulative rebates. DM carries the article 12.3 credit of $0.002818/kWh only for qualifying supply voltage/ownership; DN explicitly incorporates that conditional credit through article 9.2. Transformation-loss conditions are retained as text, not a calculated adjustment or bill total.
- **Optional products:** DT pages21-24 preserve dual-energy equipment, climate-zone temperature switching and the off-grid exclusion. Flex D pages32-34 preserve seasonal tiers, notified events and enrollment restrictions. Winter Credit pages29-31 retain the closed enrollment cutoff, reference-energy/temperature-adjustment rules and notification exceptions; it is an adjustment to Rate D, not a separate base price or calculated credit total.
- **Industrial and demand response:** Apr 1, 2026 Rate L (pp63-66) has $15.027/kW/month and $0.03821/kWh with conditional winter overrun; LG (pp67-69) has $16.571/kW/month and $0.04324/kWh with conditional unused-power charge; H (p71) has $6.630/kW/month and $0.06695/$0.2262 winter-weekday $/kWh. Business Demand Response Leeway (pp94-98) has alternative conditional winter credits and weekend event credits. Voltage credits remain conditional; ratchets and power factor are conditions, not extra universal charges.
- **Fixture and verification:** [hydro_quebec_domestic.json](../tests/fixtures/hydro_quebec_domestic.json) covers domestic options, shared definitions, credits and proration. DM/DN multiplier continuations were visually checked for arithmetic omitted by text extraction. Batch 9: 25 live records and 801 passing tests; signed values, source context, dates and independent failures are tested.
- **Remaining:** DR Commitment option open, F/FP need a scope decision, MA absent from this edition. GD backup, BR EV and LD/LP auxiliary/standby are excluded; crop-production options remain excluded.

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
- **Tests:** 53 focused SaskPower parser/storage/export cases; 801 tests in the current full suite. Coverage includes source-value mutations, cent glyph variation, wrong units/signs, missing/reordered/divergent columns, dates, failed fetches, required continuations, per-unit billing, seasonal/equipment units, historical closure notices, repeated storage and shared-code/codeless-class identity.
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
- **Status:** The July 2026 schedule rebuilds 21 current Island/Labrador/diesel building-service, industrial and seasonal-option records. Required class/charge/minimum/maximum/eligibility context fails independently; optional seasonal adjustments require their matching live base schedule. Fixed phase/amperage rows are alternatives, not cumulative charges.
- **Coverage:** Prior Island/Labrador/diesel classes plus Island Industrial Firm (PDF pp9-10: $/kW/month, $/kWh, riders and conditional named-customer charges), Labrador Industrial Firm (pp62-65: conditional 2026 $/MWh energy blocks, no blended price), and Net Metering Service Option (pp67-70: conditional credit equal to applicable class energy rate, not standalone price). Native demand units and service-area eligibility are retained.
- **Fixture and dates:** [nl_hydro.json](../tests/fixtures/nl_hydro.json) contains the approved July1,2026 charge pages. Live values are rebuilt from the source; the older January2026 seed versions remain estimates/history, not current pricing evidence.
- **Remaining:** 5.1L source-blocked by monthly futures pricing; IND non-firm/wheeling not yet audited. CP transmission commissioning and UT wholesale excluded. Missing mandatory context rejects the affected class.

### Newfoundland Power
- **URL:** `newfoundlandpower.com/en/My-Account/Usage/Electricity-Rates`
- **Status:** Rebuilds supported classes from the linked official RateBook PDF.
- **Coverage:** Domestic Service 1.1 and seasonal 1.1S, General Service 2.1/2.3/2.4, prompt-payment and conditional primary-voltage discounts and fees, plus Curtailable Service Option 1 for Rates 2.3/2.4 (conditional -$29/kVA May credit, RateBook pp30-31) and Domestic 1.1 net metering (conditional -$0.15587/kWh generation credit, pp24, 32-34): 11 live records. Printed rates already include municipal tax and Rate Stabilization riders; do not double-count them.
- **Remaining gap:** Option 2 load-factor formula and GS/seasonal net-metering credits unmodelled; annual settlement unpriced. Maintain source-derived success/failure fixtures.

## Other Regional Parser Rules

### FortisBC Electric
- RS1 flat supersedes its old tiered version; RS2A requires its closed-enrollment notice. Footer-selected PDF extraction avoids table-of-contents stalls; retain monthly/two-month units, seasons, hours and the RS21 continuation.
- RS21 kW/kVA demand charges are alternatives, not additive; voltage/transformation credits are negative and conditional. RS30/32 primary service uses 500 kVA contract demand; RS85 Green Power is optional. Jan 1, 2026 RS31 transmission (R-31.1, PDF p65) has $4,077.97/month, $6.29/kVA wires, $4.39/kVA power supply and $0.06851/kWh; RS33 TOU (R-33.1, p67) has $3,785.34/month and six seasonal TOU prices. Eleven live records. RS38 Mid-C indexed service with $0.01/kWh hourly adder needs a scope decision; RS95 source-blocked by unpublished-in-this-tariff BC Hydro RS3808 Tranche 1 price. RS37 standby-only and RS96 EV charging excluded.

### SaskEnergy and Centra Gas
- SaskEnergy's full-service and delivery-only variants require separately dated zero-carbon evidence; the assembled date uses the latest required component while retaining each component date. Do not infer private retailer commodity prices, heat conversions or small-industrial eligibility from a label. Fees without a published effective date remain unpriced.
- Centra reconciles separate delivery and volumetric demand components to published totals without adding those totals again. Require the approved PUB schedule for volume boundaries, contract/election terms, Mainline pressure, winter billing demand, T-service nominations and alternate supply; missing context rejects only affected classes. Fixed-term/private commodity prices remain unpriced.

### FortisBC Energy and Energir
- FortisBC Energy Rates 1-3 have daily basic charges; Rate 5's approved tariff prints a monthly basic charge despite the business-page wording, and Rate 4 is seasonal. Revelstoke business Rates 2/3 require class availability in the approved index as well as propane evidence; fail independently. Carbon-tax elimination evidence is mandatory. Rate 7 building service remains for Wave 2; Rate 6 NGV excluded. Fort Nelson 4/5 lack a published price table.
- Energir follows the pricing page to the current edition PDF; mismatched edition pages fail closed. D3/D4 subscribed-volume obligation bands use $/m³/day and conditional withdrawal/load-balancing charges; D1 is independent. D5 interruptible (Oct 1 CST p62) has distribution bands in $/m3; pp63-65 carry interruption and minimum-volume conditions. Category A/B load-balancing alternatives (p49) are conditional, not additive. Optional RNG supply $0.85239/m3 (p38) replaces supply on D1/D3/D4/D5; missing RNG does not suppress base records. The p49 load-factor formula is published but not computed, fixed-price supply is supplier-specific and D5 make-up gas pass-through unpriced. Inventory price differences remain customer-specific and unpriced; Quebec cap-and-trade is separate from federal carbon charges.

### Heritage/Eastward and Liberty NB
- Eastward follows its current monthly rate table and cross-checks page summaries; municipal riders apply only to fixed/base-energy/demand charges. Rate Class 3 demand is per GJ of Billing Demand per month, using the approved tariff's rule, not the rate table's total-variable row; Rate Class 4 is unpublished and negotiated.
- Liberty requires current-month utility gas and applicable CRA evidence. MGS/LGS customer charges are alternatives by peak monthly usage; LGS excess volume is seasonal. Off-Peak Service is April-November eligible, with winter overrun retained as a note; CGS/ICGS process loads remain excluded.

### Maritime Electric, FortisAlberta and Yukon Energy

- **Maritime Electric:** ten supported classes parsed from one IRAC schedule. Preserve individual charges; Wave 2 audits 310-340 for building-industrial applicability rather than assuming all industrial process products qualify.
- **FortisAlberta:** Rate 11 residential parses live; building-relevant distribution classes need source-specific extraction. The October 1 CI observation updates its official schedule URL. The shared verifier is not a complete multi-class parser.
- **Yukon Energy:** Rate 1160 now uses base fixed/energy columns with separate R/J/J1 percentages, current fuel Rider F and dated affordability relief. The prior combined R/J-only interpretation omitted J1/F/relief. The corrected October 1 version contains nine components, each with source details; no total is calculated. Relief ends March 31, 2027, applies only to eligible non-government residential energy up to 1,500 kWh, and excludes fuel/fixed charges.
- **Yukon verification:** 18 focused tests cover missing documents or changed context, future/expired dates, negative/wrong-unit base rows, rider applicability, source mutation and persistence of rebate limits/end dates. The live dry run returned one live 1160 tariff plus two labelled seed fallbacks. Both old and new 1160 versions remain stored; latest-per-name counts must not count this as a second supported class.
- **Yukon blocker:** the linked detailed 1160 residential and 2160 general-service PDFs are valid image-only documents (no text from `pdfplumber`). Their rendered pages confirm monthly residential billing and a multi-tier/demand general-service structure. The readable cross-reference contains only the fourth general-service energy block, so it cannot rebuild a complete GS tariff. Use OCR with reviewed fixtures or authoritative text alternatives before adding general-service, government/diesel variants or Rider A. No OCR dependency was added in this batch. Wholesale and standalone lighting remain excluded.

## Aggregate Statistics

| Metric | Value |
|--------|-------|
| Registered utilities | 84 |
| Stored/exported tariff versions | 694, including history and older retained estimates |
| Rate components | 4,453 |
| Latest live tariffs / utilities with live output | 209 / 18 (207 across all 16 target utilities) |
| Stored live versions | 214; includes older versions retained in history |
| Seed tariffs | 480 |
| Historical snapshots | 1,570; batch 9 appended 106, prior snapshots unchanged |
| DB validation | 0 errors, 2 existing AESO warnings |
| Newly added SaskPower live tariffs | 40 since the original residential-only parser |
| Observation provenance | October 1 CI baseline plus later stored regional batches through October 6; utility source-check dates are listed in the matrix |
| Deterministic suite | 801 passing across 8 test modules |

## Recommended Next Steps

1. Wave 2: NSPower industrial classes, FortisBC Energy Rate 7 (Rate 6 NGV excluded), SaskEnergy small industrial, Centra remaining classes and Maritime Electric 310-340 building-industrial audit. Maintain SaskPower's audited building schedules and retained references.
2. Address BC Hydro transmission pilots, Hydro-Quebec DR Commitment, NL Hydro IND non-firm/wheeling and Manitoba standard service charges/LUBD. Seek scope decisions on BC Hydro RS1828, FortisBC RS38 and Hydro-Quebec F/FP; do not invent source-blocked prices. See the [matrix](phase5_completion_matrix.md).
3. Finish with a sixteen-utility restricted source refresh, class-level coverage reconciliation, full tests and preserved-history/export checks. Ontario, Alberta and the territories stay excluded from this campaign and retained in the data.
4. Browser-enabled source health, test/scrape failure issues, release-asset database history and a successful Monthly Scrape deployment trigger are implemented, pending first CI run verification. Outcome/provenance reporting remains on the separate operational track; do not claim the automation works until exercised.

## Phase 5-wide Status

Use [phase5_completion_matrix.md](phase5_completion_matrix.md) as the maintained
per-utility ledger and [README.md](../README.md) for the ordered roadmap. Ontario's
53 registry identities still need a current distributor/merger audit. Official URL
discovery, effective dates, building-class interpretation and source-derived fixtures remain
material work; a fail-safe seed verifier is not a completed dynamic parser.
