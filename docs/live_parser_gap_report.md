# Live Parser Gap Report — Tier 1 Provincial Utilities

**Updated:** 2026-07-27
**Scope:** 8 major provincial utilities (Phase 5, Step 2)

## Summary

| Utility | Province | Page Type | Parser Status | Residential | Commercial | Confidence |
|---------|----------|-----------|---------------|-------------|------------|------------|
| **Manitoba Hydro** | MB | Server-rendered tables | Live parser | Flat rate | GS Small (tiered), GS Medium (demand) | High |
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
- **Parser:** Table extraction via `extract_tables()`, `clean_currency()` for ¢ values
- **Coverage:** Residential (flat), GS Small Non-Demand (2 energy tiers), GS Medium (demand + 2 energy tiers)
- **Fragilities:** Section boundary detection depends on header text ("non-demand", "medium"); table structure changes would break parser
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
- **Parser:** Label-based extraction via `find_text_near_label()` for residential; table extraction for commercial rates
- **Coverage:** Residential (live parsed), Rate 10 Small Commercial (tiered, live parsed), Rate 11 Commercial General (demand, live parsed), Rate 12 Large Commercial (demand, live parsed)
- **Gap:** Industrial rates (Rate 21, 22, 23) available on the business page but not yet scraped.
- **Seed update:** 2024-04-01 → 2026-01-01; URLs corrected; commercial rates added from business page

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
- **Fix:** Previously seed-only with medium confidence. Now live-parsed from official PDF with high confidence.
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
