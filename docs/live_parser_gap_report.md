# Live Parser Gap Report — Tier 1 Provincial Utilities

**Updated:** 2026-09-29
**Scope:** 8 major provincial utilities (Phase 5, Step 2)

**Provenance surfacing (2026-09-29):** These live parsers and PDF-verifiers stamp `Provenance: live_parsed` (or `officially_verified`) via `mark_live_parsed()` / `verify_official_records()`. The site treats only these as live and hides seed fallbacks by default behind the "Show estimated (not live-verified) rates" toggle.

**Multi-class expansion (2026-09-29):** Several utilities were widened from residential-only to **every published rate class**, parsing the same official document with a shared "section-slice + label/value" approach. A recurring root cause of prior commercial fall-backs was the cent symbol: official pages/PDFs render it with a glyph that a literal `¢`/`[¢c]` regex misses, so energy charges are now matched glyph-agnostically (`[^\d\s]{0,2}` before `per kWh`/`per kilowatthour`). Newly live-parsed classes: Maritime Electric (10 classes), Newfoundland Power (4), Nova Scotia Power (commercial Rate 10/11/12), Manitoba Hydro (7 general-service classes), Hydro-Québec (Rate G + M).

## Summary

| Utility | Province | Page Type | Parser Status | Residential | Commercial | Confidence |
|---------|----------|-----------|---------------|-------------|------------|------------|
| **Manitoba Hydro** | MB | Server-rendered (line-pair text) | Live parser | Flat rate | GS Small Non-Demand/Demand/Seasonal, GS Medium, GS Large (3 voltage tiers) | High |
| **NB Power** | NB | Server-rendered tables | Live parser | Flat rate | GS1 (tiered+demand), Small Industrial | High |
| **Nova Scotia Power** | NS | Server-rendered h4/li | Live parser (residential + commercial) | Flat rate | Rate 10 (tiered), Rate 11 (demand), Rate 12 (demand) | High |
| **BC Hydro** | BC | Prose text (sub-pages) | Live parser | Tiered (Step 1/2) | SGS (flat), MGS (demand), LGS (demand) | High |
| **Hydro-Québec** | QC | JS-rendered + PDF | PDF live parser | Rate D (tiered) | Rate G (mixed), Rate M (demand) | High |
| **SaskPower** | SK | PDF-only | Official PDF component verification | Flat rate | Small + Demand | High when verified |
| **NL Hydro** | NL | PDF + inline text | Official PDF component verification | Rural + Labrador | General Service | High when verified |
| **Newfoundland Power** | NL | PDF-only | Official PDF component verification | Flat rate | General Service | High when verified |

## Group A: Server-Rendered HTML — Full Live Parsing

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

## Group C: PDF-Only — Official-Source Component Verification

These scrapers now resolve relative and query-string PDF links, download the
official schedule, extract its text, and require **every** seeded tariff
component to appear in that schedule. A tariff is marked live-verified and its
source is changed to the exact PDF URL only after the complete check passes.
If one component is absent or changed, the scraper explicitly logs the missing
component and uses fallback data rather than silently treating it as live.

### SaskPower
- **URL:** `saskpower.com/accounts/power-rates/power-supply-rates`
- **Status:** Complete component verification against linked official PDF.
- **Coverage:** Residential (flat), Small Commercial (flat), Demand Commercial.
- **Remaining gap:** The verifier detects drift but does not automatically infer a replacement tariff structure when SaskPower changes a rate.

### NL Hydro
- **URL:** `nlhydro.com/electicity-rates/current-rates/` (note: typo "electicity" is their actual path)
- **Status:** Page shows inline ¢/kWh values; every returned component is verified against the linked official PDF.
- **Coverage:** Rural Residential, Labrador Interconnected, General Service.
- **Remaining gap:** Source drift is flagged and rejected; changed values still require a reviewed seed update.
- **Seed update:** 2024-04-01 → 2026-01-01; energy rates updated from page text (island 15.213¢, Labrador 3.154¢)

### Newfoundland Power
- **URL:** `newfoundlandpower.com/en/My-Account/Usage/Electricity-Rates`
- **Status:** Rates are verified against the linked official "Schedule of Rates, Rules and Regulations" PDF.
- **Coverage:** Domestic Service (Rate 1.1), General Service (Rate 2.1).
- **Remaining gap:** Source drift is flagged and rejected; changed values still require a reviewed seed update.

## Aggregate Statistics

| Metric | Value |
|--------|-------|
| Total tariffs across 8 utilities | 24 |
| Tariffs with live HTML parsing | 11 (MB:3, NB:3, NS:4, BC:4) |
| Tariffs with live PDF parsing | 3 (HQ:3) |
| Tariffs eligible for official live verification | 24/24 |
| Tariffs automatically rebuilt from parsed values | 17/24 |
| Tariffs verified component-by-component against official PDFs | 7/24 |
| Official-source coverage | 100% when the live fetch succeeds and all components match |
| URLs corrected | 3 (NS Power, NL Hydro, Newfoundland Power) |
| Structural data fixes | 2 (NB residential tiered→flat, BC SGS demand removed) |

## Recommended Next Steps

1. **Automatic PDF drift updates** — safely infer replacement values and effective dates after component verification detects a change; until then changed components are logged and fallback data is clearly retained.
2. **NS Power industrial** — Rate 21, 22, 23 are available on the business page but are not yet scraped.
3. **Ontario LDC depth** — the shared Ontario scraper provides broad registry coverage, but each LDC still needs individual source-structure validation rather than relying on a common data-driven pattern.
4. **Live-network CI** — add a non-blocking scheduled source check. Unit tests deliberately use representative official-document text because utility sites can be unavailable or rate-limit CI.

## Phase 5-wide status (2026-07-27)

The original Tier 1 report above remains its historical detailed audit. The live
scope now uses the maintained per-utility matrix in
[`phase5_completion_matrix.md`](phase5_completion_matrix.md), covering all 53
Ontario LDCs, Alberta wires/default retail/AESO, nine gas utilities, and four
northern utilities. Each family has a deterministic contextual-verification
path and conservative fallback provenance. Known fragilities are PDF layout,
JS-only pages, renamed products, quarterly/monthly effective dates, and missing
individual OEB-approved tariff links. Those gaps remain visible blockers; Phase
5 is therefore not claimed complete.
