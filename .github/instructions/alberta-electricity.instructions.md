---
description: "Use when changing Alberta electricity scrapers: the wires companies (atco_electric.py, fortisalberta.py, epcor_distribution.py, enmax_power.py), the Rate of Last Resort providers (direct_energy_regulated.py, enmax_energy.py, epcor_energy_alberta.py, scrapers/utils/alberta_rolr.py), the AESO pool price reference (aeso.py) and the municipal utilities (medicine_hat.py, lethbridge.py, red_deer.py). Covers separate distribution and transmission (SAS) components, dated riders, ATCO TOTAL PRICE reconciliation, EPCOR interim rates, kW/kVA alternatives, AESO flow-throughs, the UCA cross-check, the RoLR fixed term and city-published Rate of Last Resort and bundled prices."
applyTo: "scrapers/utilities/atco_electric.py, scrapers/utilities/fortisalberta.py, scrapers/utilities/epcor_distribution.py, scrapers/utilities/enmax_power.py, scrapers/utilities/direct_energy_regulated.py, scrapers/utilities/enmax_energy.py, scrapers/utilities/epcor_energy_alberta.py, scrapers/utilities/aeso.py, scrapers/utils/alberta_rolr.py, scrapers/utilities/medicine_hat.py, scrapers/utilities/lethbridge.py, scrapers/utilities/red_deer.py"
---
# Alberta electricity

Generic scraper rules: [scrapers.instructions.md](scrapers.instructions.md). Class lists, exclusions
and gaps: [gap report](../../docs/live_parser_gap_report.md) (Alberta Electricity).

## Market structure

- Alberta separates regulated wires service (ATCO Electric, FortisAlberta, EPCOR Distribution, ENMAX
  Power and the municipal wires owners), retail energy and the AESO wholesale market. Model each
  piece separately and never add wires charges and energy prices into one price. Only the
  representative models pair them (see
  [representative-models.instructions.md](representative-models.instructions.md)).
- Customers without a retail contract pay the Rate of Last Resort (RoLR), which replaced the
  Regulated Rate Option (RRO) on January 1, 2025. Old RRO estimates stay in history.

## Wires companies

Decisions marked 2026-10-09 are the owner's.

- Parse the AUC-approved schedule PDFs discovered on each run: ENMAX's opaque asset link, ATCO's
  `rates.model.json`, EPCOR's dated DAS/SAS/rider PDFs and FortisAlberta's newest in-effect Rates,
  Options and Riders edition, whose link date must equal its printed date.
- Store distribution and transmission (SAS) charges as separate components (SAS as `transmission`).
  Store each current rider as its own dated component with its quarter gate or end date; leave
  expired riders out by date (2026-10-09).
- kVA limits stay in eligibility text. Municipal access fees and riders are notes.
- AESO-tariff pass-throughs priced elsewhere are value-less components (FortisAlberta Rate 65
  transmission); unpriced flow-throughs are notes (ATCO T31 transmission). FortisAlberta Rate 65 and
  ATCO T31 stay live partial records (2026-10-09).
- **ATCO Electric** (D11, D13, D21, D31, T31): transmission, distribution and service rows must
  reconcile to each printed TOTAL PRICE. Riders B, G and S are dated components cross-checked against
  the copies bound into the price schedules; an expired rider (Rider J) is a note. T31 is in scope
  only where priced; D22, D24 and D34 are out of scope (2026-10-09).
- **ENMAX Power** (D100, D200, D300, D310, D410): D700 is in scope only where priced, and its AESO
  flow-through is source-blocked (2026-10-09). D500 and D600 are excluded.
- **EPCOR Distribution** (DAS-R, SC, MC, TOU, TOUP): "2026 INTERIM RATE" tariffs are live at medium
  confidence with an interim note (2026-10-09). Values must match the tariffs' lookup tables. Riders
  G, J and K are dated components. The SAS operating reserve (a percentage of the pool price) is a
  value-less market component that cites the live aeso.ca Market and System Reporting page.
- **FortisAlberta** (Rates 11, 41, 61, 63, 65): kW/kVA charge pairs are alternatives. The D10, D20
  and D30 seeds are not emitted when the live records exist.

## Rate of Last Resort

- Every RoLR price must match the Government of Alberta Utilities Consumer Advocate (UCA)
  default-rates table (`scrapers/utils/alberta_rolr.py`); without a match the records fail closed.
- RoLR prices are fixed for a two-year term (January 1, 2025 to December 31, 2026). After the term
  ends, the records stop counting as live until the next term's price is published.
- **Direct Energy Regulated Services** (ATCO Electric area): energy price for residential and small
  business. Its daily administration charge is not emitted: the website value is undated and the last
  dated schedule differs.
- **ENMAX Energy** (Calgary area): energy price plus the daily administration charge from the Interim
  2026 schedule, at medium confidence, for D100 (Residential), D200 (Small Commercial) and, since
  owner decision 102 (2026-11-24), D300 (Medium Commercial) and D310/D410 (Large Commercial). The
  commercial schedules apply only to sites under their printed annual limit (250 MWh), each must name
  its distribution rates and its limit, and all are checked against the UCA table's one ENMAX
  Power-area price, which UCA publishes for residential and small business consumers.
- **EPCOR Energy Alberta** (EPCOR Distribution and FortisAlberta areas): energy price plus a per-area
  administration charge. Its pages moved on 2026-10-16: the registry, the scraper constants and
  `tests/fixtures/alberta_rolr.json` must stay in sync.
- The old RRO seed records cite `aeso.REPORT_URL` (the ETS pool price report). The dead seed
  citations of ENMAX Energy, EPCOR Energy Alberta, EPCOR Distribution and DERS are kept on purpose in
  `KEPT_DEAD` (see scrapers.instructions.md).

## Municipal utilities (batch 18 continued, 2026-11-19)

Decisions marked 2026-11-04 and 2026-11-19 are the owner's.

- Lethbridge and Red Deer own their wires and publish their area's Rate of Last Resort price
  themselves; Medicine Hat generates, delivers and sells electricity. One scraper per city emits its
  wires records and its Rate of Last Resort records, or Medicine Hat's bundled records (2026-11-04).
- There is no UCA cross-check for these areas. The City's energy price must name its term and the
  term must cover today, or the records fail closed; a term is never extended (the RoLR rule above).
- Municipal access fees stay notes: Lethbridge Rider A (15.50%), Red Deer's 15% Local Access Fee and
  Medicine Hat's Municipal Consent & Access Fee. No seed fallback. When a page links no document, the
  last known copy is read with a note (Lethbridge's bylaw and rate table, Medicine Hat's brochure).
- **Lethbridge** (991, 992, 994, 995, 996, 997): values come from the consolidated Electric
  Distribution Tariff bylaw linked on the Electric page. Each must equal the year's Rate Table, read
  by column position, and both documents must name the same rate year. Riders B and C are dated
  per-kWh components that must match the Utility Rates page's rider table (Rider C is a credit,
  stored as `rebate`). The page's "RDS" price is defined nowhere and is not stored. The City's one
  Rate of Last Resort price is stored as RoLR-Res and RoLR-SB. The page text contains zero-width
  spaces.
- **Red Deer** (61, 63, 64, 78): Schedule A values must equal the Delivery Rates and Charges page,
  whose date label may lag the schedule. That page's quarterly Transmission Rider is stored for the
  current quarter. The Rate of Last Resort records (RRT-61/63/64/78) take the term's energy price
  from the Rate of Last Resort page for every rate and Schedule D's administration charge, noting
  the page's older $0.2498/day (2026-11-19). Pages are fetched over plain HTTP, with headless
  Chromium only when the expected content is missing.
- **Medicine Hat** (1.1, 3.1, 3.3, 4.1, 5.1): bundled records (delivery plus the City's energy
  price).
  - The brochure is read one page column at a time.
  - 1.1, 3.1 and 3.3 use the monthly default rate. The current month's row must exist and equal the
    page's "Current Electricity Rate", or the records fail closed. The rate is dated to that month.
    The run on the 1st usually comes before the City posts the month's row. Medicine Hat is in the
    registry's `monthly_price_refresh` group, so the Monthly Scrape on the 4th stores it (owner
    decisions 2026-11-20 and 2026-11-23, replacing the owner's monthly run of 2026-11-19). The owner
    starts a Medicine Hat run only when the City posts later, likely when the rate is recalculated on
    the first business day of a quarter (Monday January 4, 2027).
  - 4.1 and 5.1 use the fixed default rate for its term (to December 31, 2026) and fail closed after
    it (2026-11-19).
  - Each record ends with its shortest-lived price (the month for 1.1/3.1/3.3, the fixed rate's term
    for 4.1/5.1), so models and the coverage gate stop using it until a newer record is stored
    (2026-11-19).
  - The undated Going Green surcharge is stored for the month it was read, with a note
    (2026-11-19).
  - The Environmental Conservation Charge applies above 950 kWh a month; demand is per kVA.

## AESO pool price reference (`aeso.py`)

- AESO publishes no customer tariff. The `POOL` record is a value-less market reference ("Variable").
- It is live only when the ETS Historical Pool Price CSV (plain http) posts recent hourly prices in
  the documented format within $0-$999.99 and the metadata PDF still defines the pool price. The
  PDF's modification date is the effective date. Otherwise the labelled seed fallback is used.
- The old aeso.ca hourly-pool-price-report page returns 404 and is on the dead-URL denylist.
- `parse_pool_price_csv()` is shared with the Alberta history builder, which passes
  `price_bounds=None` on purpose (see [market-data.instructions.md](market-data.instructions.md)).
