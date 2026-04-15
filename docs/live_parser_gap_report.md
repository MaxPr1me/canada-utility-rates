# Live Parser Gap Report — Tier 1 Provincial Utilities

**Generated:** 2026-04-15
**Scope:** 8 major provincial utilities (Phase 5, Step 2)

## Summary

| Utility | Province | Page Type | Parser Status | Residential | Commercial | Confidence |
|---------|----------|-----------|---------------|-------------|------------|------------|
| **Manitoba Hydro** | MB | Server-rendered tables | Live parser | Flat rate | GS Small (tiered), GS Medium (demand) | High |
| **NB Power** | NB | Server-rendered tables | Live parser | Flat rate | GS1 (tiered+demand), Small Industrial | High |
| **Nova Scotia Power** | NS | Server-rendered h4/li | Live parser (residential) | Flat rate | Small General (seed only) | High |
| **BC Hydro** | BC | Prose text (sub-pages) | Live parser | Tiered (Step 1/2) | SGS (flat), MGS (demand) | High |
| **Hydro-Québec** | QC | JS-rendered | JS detection only | Rate D (tiered, seed) | Rate G (mixed, seed) | Medium |
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
- **URL:** `nspower.ca/your-home/residential-rates/standard-residential` (NOT the landing page)
- **Parser:** Label-based extraction via `find_text_near_label()` for "Base Charge" and "Energy Charge"
- **Coverage:** Residential (live parsed), Small General Service (seed only — no confirmed live URL for commercial)
- **Gap:** Commercial rates only from seed data. Need to find and parse the commercial rate page.
- **Seed update:** 2024-04-01 → 2026-01-01; URL corrected from landing page to actual rate sub-page

### BC Hydro
- **URL:** `app.bchydro.com/.../residential-rates/tiered.html` and `.../business-rates.html`
- **Parser:** Regex extraction from prose text ("XX.XX cents per kWh", "XX.XX cents per day")
- **Coverage:** Residential (tiered Step 1/2 + rider), SGS Rate 1300 (flat, no demand), MGS Rate 1500 (demand)
- **Fix:** SGS incorrectly had demand charge removed; MGS (Rate 1500) added. URL redirects www→app handled.
- **Fragilities:** Prose text parsing with regex — any wording change breaks it. Step rate section boundaries could shift.
- **Seed update:** 2024-04-01 → 2026-04-01

## Group B: JS-Rendered — Detection Only

### Hydro-Québec
- **URL:** `hydroquebec.com/residential/customer-space/rates/rate-d.html`
- **Status:** `detect_js_rendered()` identifies the page as JS-rendered (`populate-data.js` injects values client-side)
- **PDF fallback:** `find_pdf_links()` searches for linked PDFs (electricity-rates.pdf)
- **Coverage:** Rate D (residential, tiered) and Rate G (commercial, mixed) from seed data
- **Gap:** Cannot verify 2026-04-01 rate values without headless browser or PDF parsing. Confidence set to "medium".
- **Future:** Implement PDF table extraction for `electricity-rates.pdf`, or use Playwright/Selenium for JS rendering.

## Group C: PDF-Only — Link Detection

### SaskPower
- **URL:** `saskpower.com/accounts/power-rates/power-supply-rates`
- **Status:** Landing page detected; `find_pdf_links()` locates linked PDF rate schedules
- **Coverage:** Residential (flat), Small Commercial (flat), Demand Commercial — all from seed
- **Gap:** No PDF table extraction implemented. Rates may be stale (2025-01-01 effective date).
- **Future:** Download PDF via `fetch_bytes()` and parse with `extract_pdf_tables()`.

### NL Hydro
- **URL:** `nlhydro.com/electicity-rates/current-rates/` (note: typo "electicity" is their actual path)
- **Status:** URL fixed (old path returned 404). Page shows inline ¢/kWh values; full rates in linked PDF.
- **Coverage:** Rural Residential, Labrador Interconnected, General Service — all from seed
- **Gap:** Inline text values used for validation only (logged, not parsed into records). Full rates require PDF parsing.
- **Seed update:** 2024-04-01 → 2026-01-01; energy rates updated from page text (island 15.213¢, Labrador 3.154¢)

### Newfoundland Power
- **URL:** `newfoundlandpower.com/en/My-Account/Usage/Electricity-Rates`
- **Status:** URL fixed (old path returned 404). Rates only in linked PDF "Schedule of Rates, Rules and Regulations".
- **Coverage:** Domestic Service (Rate 1.1), General Service (Rate 2.1) — from seed
- **Gap:** No PDF parsing. Rates may be slightly stale (2025-07-01 effective date).
- **Future:** Implement PDF table extraction for the Schedule of Rates PDF.

## Aggregate Statistics

| Metric | Value |
|--------|-------|
| Total tariffs across 8 utilities | 20 |
| Tariffs with live HTML parsing | 10 (MB:3, NB:3, NS:1, BC:3) |
| Tariffs with seed-only data | 10 (NS:1, HQ:2, SK:3, NL:3, NF:2) |
| Live parser coverage | 50% of tariffs |
| URLs corrected | 3 (NS Power, NL Hydro, Newfoundland Power) |
| Structural data fixes | 2 (NB residential tiered→flat, BC SGS demand removed) |

## Recommended Next Steps

1. **PDF parsing** — SaskPower, NL Hydro, and Newfoundland Power all have PDF rate schedules. Implementing `extract_pdf_tables()` would unlock 8 additional tariffs.
2. **Hydro-Québec JS rendering** — Either implement PDF fallback parsing or add Playwright/Selenium support for JS-rendered pages.
3. **NS Power commercial** — Find the live URL for small general service rates and add a parser.
4. **Automated staleness checks** — Add a periodic job that fetches pages and compares to seed data, flagging when effective dates change.
