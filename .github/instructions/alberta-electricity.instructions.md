---
description: "Use when changing Alberta electricity scrapers: the wires companies (atco_electric.py, fortisalberta.py, epcor_distribution.py, enmax_power.py), the Rate of Last Resort providers (direct_energy_regulated.py, enmax_energy.py, epcor_energy_alberta.py, scrapers/utils/alberta_rolr.py) and the AESO pool price reference (aeso.py). Covers separate distribution and transmission (SAS) components, dated riders, ATCO TOTAL PRICE reconciliation, EPCOR interim rates, kW/kVA alternatives, AESO flow-throughs, the UCA cross-check and the RoLR fixed term."
applyTo: "scrapers/utilities/atco_electric.py, scrapers/utilities/fortisalberta.py, scrapers/utilities/epcor_distribution.py, scrapers/utilities/enmax_power.py, scrapers/utilities/direct_energy_regulated.py, scrapers/utilities/enmax_energy.py, scrapers/utilities/epcor_energy_alberta.py, scrapers/utilities/aeso.py, scrapers/utils/alberta_rolr.py"
---
# Alberta electricity

Generic scraper rules: [scrapers.instructions.md](scrapers.instructions.md). Class lists, exclusions
and gaps: [gap report](../../docs/live_parser_gap_report.md) (Alberta Electricity).

## Market structure

- Alberta separates regulated wires service (ATCO Electric, FortisAlberta, EPCOR Distribution, ENMAX
  Power), retail energy and the AESO wholesale market. Model each piece separately and never add
  wires charges and energy prices into one price. Only the representative models pair them (see
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
- **ENMAX Energy** (Calgary area): D100/D200 energy price plus the daily administration charge from
  the Interim 2026 schedule, at medium confidence.
- **EPCOR Energy Alberta** (EPCOR Distribution and FortisAlberta areas): energy price plus a per-area
  administration charge. Its pages moved on 2026-10-16: the registry, the scraper constants and
  `tests/fixtures/alberta_rolr.json` must stay in sync.
- The old RRO seed records cite `aeso.REPORT_URL` (the ETS pool price report). The dead seed
  citations of ENMAX Energy, EPCOR Energy Alberta, EPCOR Distribution and DERS are kept on purpose in
  `KEPT_DEAD` (see scrapers.instructions.md).

## AESO pool price reference (`aeso.py`)

- AESO publishes no customer tariff. The `POOL` record is a value-less market reference ("Variable").
- It is live only when the ETS Historical Pool Price CSV (plain http) posts recent hourly prices in
  the documented format within $0-$999.99 and the metadata PDF still defines the pool price. The
  PDF's modification date is the effective date. Otherwise the labelled seed fallback is used.
- The old aeso.ca hourly-pool-price-report page returns 404 and is on the dead-URL denylist.
- `parse_pool_price_csv()` is shared with the Alberta history builder, which passes
  `price_bounds=None` on purpose (see [market-data.instructions.md](market-data.instructions.md)).
