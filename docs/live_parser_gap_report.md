# Live Parser Gap Report — Tier 1 Provincial Utilities

**Generated:** 2026-04-15
**Scope:** 8 major provincial utilities (Phase 5, Step 2)

## Summary

| Utility | Province | Page Type | Parser Status | Residential | Commercial | Confidence |
|---------|----------|-----------|---------------|-------------|------------|------------|
| **Manitoba Hydro** | MB | Server-rendered tables | Live parser | Flat rate | GS Small (tiered), GS Medium (demand) | High |
| **NB Power** | NB | Server-rendered tables | Live parser | Flat rate | GS1 (tiered+demand), Small Industrial | High |
| **Nova Scotia Power** | NS | Server-rendered h4/li | Live parser (residential + commercial) | Flat rate | Rate 10 (tiered), Rate 11 (demand), Rate 12 (demand) | High |
| **BC Hydro** | BC | Prose text (sub-pages) | Live parser | Tiered (Step 1/2) | SGS (flat), MGS (demand), LGS (demand) | High |
| **Hydro-Québec** | QC | JS-rendered + PDF | PDF live parser | Rate D (tiered) | Rate G (mixed), Rate M (demand) | High |
| **SaskPower** | SK | PDF-only | PDF link detection | Flat rate (seed) | Small + Demand (seed) | High |
| **NL Hydro** | NL | PDF + inline text | PDF link detection | Rural + Labrador (seed) | General Service (seed) | Medium |
| **Newfoundland Power** | NL | PDF-only | PDF link detection | Flat rate (seed) | General Service (seed) | High |

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

## Group C: PDF-Only — Link Detection (Not Yet Parsed)

### SaskPower
- **URL:** `saskpower.com/accounts/power-rates/power-supply-rates`
- **Status:** Landing page detected; `find_pdf_links()` locates linked PDF rate schedules
- **Coverage:** Residential (flat), Small Commercial (flat), Demand Commercial — all from seed
- **Gap:** No PDF table extraction implemented. Rates may be stale (2025-01-01 effective date).
- **Action needed:** Locate direct PDF URL(s) for rate schedules. Implement `extract_pdf_tables()`.

### NL Hydro
- **URL:** `nlhydro.com/electicity-rates/current-rates/` (note: typo "electicity" is their actual path)
- **Status:** URL fixed (old path returned 404). Page shows inline ¢/kWh values; full rates in linked PDF.
- **Coverage:** Rural Residential, Labrador Interconnected, General Service — all from seed
- **Gap:** Inline text values used for validation only (logged, not parsed into records). Full rates require PDF parsing.
- **Action needed:** Locate direct PDF URL for "Schedule of Rates, Rules and Regulations" (Jan 2026 edition).
- **Seed update:** 2024-04-01 → 2026-01-01; energy rates updated from page text (island 15.213¢, Labrador 3.154¢)

### Newfoundland Power
- **URL:** `newfoundlandpower.com/en/My-Account/Usage/Electricity-Rates`
- **Status:** URL fixed (old path returned 404). Rates only in linked PDF "Schedule of Rates, Rules and Regulations".
- **Coverage:** Domestic Service (Rate 1.1), General Service (Rate 2.1) — from seed
- **Gap:** No PDF parsing. Rates may be slightly stale (2025-07-01 effective date).
- **Action needed:** Locate direct PDF URL for "Schedule of Rates" PDF. Implement PDF parsing.

## Aggregate Statistics

| Metric | Value |
|--------|-------|
| Total tariffs across 8 utilities | 24 |
| Tariffs with live HTML parsing | 11 (MB:3, NB:3, NS:4, BC:4) |
| Tariffs with live PDF parsing | 3 (HQ:3) |
| Tariffs with seed-only data | 7 (SK:3, NL:3, NF:2) |
| Live parser coverage | 70% of tariffs (17/24) |
| URLs corrected | 3 (NS Power, NL Hydro, Newfoundland Power) |
| Structural data fixes | 2 (NB residential tiered→flat, BC SGS demand removed) |

## Recommended Next Steps

1. **PDF parsing for remaining 3 utilities** — SaskPower, NL Hydro, and Newfoundland Power all have PDF rate schedules. Need manual identification of direct PDF URLs, then implement `extract_pdf_tables()` to unlock 7 additional tariffs.
2. **NS Power industrial** — Rate 21, 22, 23 available on the business rates page but not yet scraped.
3. **Automated staleness checks** — Add a periodic job that fetches pages and compares to seed data, flagging when effective dates change.
