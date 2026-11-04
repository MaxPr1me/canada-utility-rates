---
description: "Use when changing Ontario electricity scrapers or OEB tariff-sheet parsing: scrapers/utilities/ontario_ldc.py (OEB_TARIFF_DOCUMENTS, every Ontario LDC), scrapers/utils/oeb_tariff.py and the legacy scrapers/utilities/toronto_hydro.py. Covers the OEB RPP page, Tariff of Rates and Charges PDFs, rate zones, RPP energy for residential and GS<50, the value-less Market Energy line for demand classes, Algoma and Hydro One readings, per-document extract settings, PUC Distribution, class rejections, seed suppression and merged distributors."
applyTo: "scrapers/utilities/ontario_ldc.py, scrapers/utilities/toronto_hydro.py, scrapers/utils/oeb_tariff.py"
---
# Ontario electricity distributors

Generic scraper rules: [scrapers.instructions.md](scrapers.instructions.md). Distributor classes,
exclusions and gaps: [gap report](../../docs/live_parser_gap_report.md) (Ontario Distributors).
Market history: [market-data.instructions.md](market-data.instructions.md).

## Sources

- One data-driven scraper, `ontario_ldc.py`, handles every Ontario LDC. `toronto_hydro.py` is a
  legacy module that is not registered.
- `OEB_TARIFF_DOCUMENTS` maps each registry name to `[{url, case_number, zones, default_zone}]`.
- Start every update from the OEB common-rate (RPP) page, then read each distributor's OEB-approved
  Tariff of Rates and Charges PDF. The OEB BillData XML is a name/zone cross-check only, never a
  source of values.
- `parse_rpp_page()` rejects a missing, future-dated or stale RPP effective date, so an Ontario run
  fails before the date the page announces.
- `parse_bill_data()` requires each BillData row's `YEAR` to equal the scrape's calendar year. Until
  the OEB relabels the feed in January, a run rejects every residential and GS<50 row (the stored
  versions stay the latest); relaxing this is an owner decision (`tests/test_edition_rollover.py`).
- A configured tariff sheet is rejected while its effective or implementation date is in the future
  and is treated as superseded 500 days after its effective date (`_TARIFF_STALE_DAYS`). A new rate
  year's sheet is not discovered: add its URL and case number to `OEB_TARIFF_DOCUMENTS` on or after
  its effective date, then dry-run the distributor.
- Each rate zone gets its own records: the legacy codes (`TOU-R`, `GS-TOU-S`, ...) in the default
  zone and "[zone]" names elsewhere.

## Reading tariff sheets (`oeb_tariff.py`)

- Use `extract_tariff_pages`, not `normalize_document_text`, which drops repeated lines.
- An overprinted "Applicable only for ..." tail attaches to the preceding rider.
- A lone Transformation Connection line is the standard connection rate; a lone Line line still fails.
- Take the case number from the Schedule A cover only when its date equals the Issued date.
- "EQUAL TO OR GREATER THAN" open GS and INTERMEDIATE USER (inside 50-5,000 kW) are GS demand classes.
- In-scope classes that classify as "other" surface as rejections.
- Keep every document strict. The only per-document settings are:
  - `"extract": {"y_tolerance": N}` for PDFs whose values print slightly above their labels
    (Kingston 6, Midland 1, Grimsby 4). Never fix such a PDF with a guessed value.
  - `"connection_rate": "not_printed"` for PUC Distribution only: its approved tariff prints no
    Retail Transmission Connection rate, so every PUC record carries a note saying so.

## Classes and energy

- Residential and GS<50: the live provincial RPP energy price plus the distributor's tariff delivery
  charges.
- Non-RPP demand classes (GS 50-4,999 kW and its sub-ranges, open GS 50 kW and over, Large Use,
  Hydro One UGd/GSd/AUGd/AGSd and ST): delivery charges plus a value-less "Market Energy (Ontario
  Electricity Market Price + Class B Global Adjustment)" component with the IESO source URL, and
  `pricing_method` `market_based` (Phase 6B). Class A GA (peak demand factor) and the O. Reg. 95/05
  s. 4(2) RPP-eligibility caveat are conditional notes.
- The market price is the Ontario Electricity Market Price (OEMP = DA-OZP + LFDA) since May 1, 2025;
  HOEP was retired on April 30, 2025.
- Open GS with a floor of 1,000 kW or less is `commercial`; above that it is `large_use`
  (owner-confirmed).
- Algoma R1 is split by its criteria: (i) year-round dwellings (fully fixed; keeps the `TOU-R`
  codes) and (ii) O. Reg. 445/07 customers, both residential. Algoma R2 (50 kW and over, billed per
  kW) is a delivery-only `residential_demand` record with no RPP energy and no Market Energy line,
  because dwelling accounts stay RPP-eligible.
- Hydro One (owner-confirmed readings): Seasonal = the R2 seasonal service charge plus the shared R2
  lines, without the RRRP credit; year-round R2 carries the RRRP credit as conditional; UR/R1
  seasonal properties use the UR/R1 records; DRP is not modelled.

## Rejections, seeds and merged distributors

- A class that cannot be read cleanly is rejected, not guessed, and no new estimate is made for it
  (owner decision: go by live sources). Older stored estimates stay in history, labelled seed.
- Seed suppression: a configured LDC with a class rejection or no such class (`gs:absent`,
  `demand:absent`) emits no residential, GS or GS-demand (Res/GS/GS-D) seeds. A fetch failure or a
  whole-sheet rejection keeps the seeds. The street-lighting seed is always kept.
- Absorbed distributors have `status: "merged"` and a `merged_into` successor and keep their history.
  Their successors, Enova Power and GrandBridge Energy, have no seeds, so they return nothing when
  their tariff cannot be read.
