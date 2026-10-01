# Live Parser Gap Report

**Updated:** 2026-10-01
**Scope:** Building-energy parser coverage, including single-family homes, with completed non-building schedules retained as reference.

**Evidence:** October 1 local SaskPower/Yukon results are combined with the October 1
monthly CI observations. CI data was integrated while preserving local history and
newer SaskPower classes. The current export has
80 stored live versions (79 latest tariffs) and 480 seed tariffs across 84 registered utilities. A fixture or verifier
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
| **Nova Scotia Power** | NS | Server-rendered h4/li | Live parser (residential + commercial) | Flat rate | Rate 10 (tiered), Rate 11 (demand), Rate 12 (demand) | High |
| **BC Hydro** | BC | Prose text (sub-pages) | Live parser | Tiered (Step 1/2) | SGS (flat), MGS (demand), LGS (demand) | High |
| **Hydro-Québec** | QC | JS-rendered + PDF | PDF live parser | Rate D (tiered) | Rate G (mixed), Rate M (demand) | High |
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
- **URL (residential):** `nspower.ca/your-home/residential-rates/standard-residential`
- **URL (commercial):** `nspower.ca/your-business/save-money-energy/business-rates`
- **Parser:** Label-based extraction via `find_text_near_label()` for residential; a section parser for commercial that slices each rate between its page header and the next rate/sample/minimum-charge marker (replacing the old table heuristic that always fell back because the page's cent glyph is not a literal `¢`)
- **Coverage:** Residential (live parsed), Rate 10 Small Commercial (tiered, live parsed), Rate 11 Commercial General (demand, live parsed), Rate 12 Large Commercial (demand, live parsed)
- **Gap:** Industrial rates (Rate 21, 22, 23) available on the business page but not yet scraped.
- **Seed update:** 2024-04-01 → 2026-01-01; commercial seeds refreshed to current values

### BC Hydro
- **URL:** `app.bchydro.com/.../residential-rates/tiered.html` and `.../business-rates.html`
- **Parser:** Regex extraction from prose text ("XX.XX cents per kWh", "XX.XX cents per day")
- **Coverage:** Residential (tiered Step 1/2 + rider), SGS Rate 1300 (flat, no demand), MGS Rate 1500 (demand), LGS Rate 1600 (demand, higher demand rate / lower energy rate)
- **Fix:** SGS incorrectly had demand charge removed; MGS (Rate 1500) added; LGS (Rate 1600) added.
- **Fragilities:** Prose text parsing with regex — any wording change breaks it. Step rate section boundaries could shift.
- **Seed update:** 2024-04-01 → 2026-04-01

## Group B: PDF-Parsed — Live Data from Official PDFs

### Hydro-Québec
- **URL (residential):** `hydroquebec.com/residential/customer-space/rates/rate-d.html` (JS-rendered, not parseable)
- **PDF URL:** `hydroquebec.com/data/documents-donnees/pdf/electricity-rates.pdf`
- **Parser:** PDF text extraction via `pdfplumber` (`extract_pdf_text()`), regex parsing for ¢/kWh and $/kW patterns
- **Coverage:** Rate D (residential, tiered), Rate G (commercial, mixed demand+tiered), Rate M (medium power, demand+tiered)
- **Fix:** Rate G/M previously fell back to seed because the section extractor keyed on the generic "Rate G"/"Rate M" strings (first found in the table of contents) and the cent regex missed the PDF's glyph. Now anchored on the "Structure of Rate G"/"Structure of Rate M" sections with a glyph-agnostic energy pattern, so all three tariffs parse live.
- **Seed update:** 2024-04-01 → 2026-04-01; values verified from official PDF

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
- **Tests:** 53 focused SaskPower parser/storage/export cases; 316 tests in the full suite. Coverage includes source-value mutations, cent glyph variation, wrong units/signs, missing/reordered/divergent columns, dates, failed fetches, required continuations, per-unit billing, seasonal/equipment units, historical closure notices, repeated storage and shared-code/codeless-class identity.
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
| Stored/exported tariff versions | 560, including history and older retained estimates |
| Rate components | 3,658 |
| Latest live tariffs / utilities with live output | 79 / 10 |
| Stored live versions | 80; includes older Yukon 1160 version |
| Seed tariffs | 480 |
| Newly added SaskPower live tariffs | 40 since the original residential-only parser |
| October 1 observations | Monthly CI snapshot plus newer local SaskPower results |
| Deterministic suite | 316 passing |

## Recommended Next Steps

1. Maintain the implemented SaskPower building schedules; retain non-building classes as reference without expanding them.
2. Next building-service expansions: Yukon Energy, NS Power and FortisBC Electric. Include single-family homes; industrial tariffs only where relevant to building loads, not process-only service.
3. Continue building coverage across provinces/territories, nine gas utilities, Alberta wires/default retail and necessary market references, then Ontario's approved distributor schedules.
4. Repair the existing non-blocking source-health workflow's browser setup and outcome reporting; keep normal tests network-free. Durable CI history and deployment triggering are separate operational follow-ups.

## Phase 5-wide Status

Use [phase5_completion_matrix.md](phase5_completion_matrix.md) as the maintained
per-utility ledger and [README.md](../README.md) for the ordered roadmap. Ontario's
53 registry identities still need a current distributor/merger audit. Official URL
discovery, effective dates, building-class interpretation and source-derived fixtures remain
material work; a fail-safe seed verifier is not a completed dynamic parser.
