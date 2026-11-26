---
description: "Use when changing natural gas scrapers: Enbridge Gas (enbridge_gas.py), EPCOR Natural Gas Ontario (epcor_gas_ontario.py), the retired Alberta epcor_gas.py, ATCO Gas (atco_gas.py), FortisBC Energy (fortisbc_energy.py), Energir (energir.py), Eastward/Heritage Gas (heritage_gas.py), Liberty NB (liberty_gas_nb.py), SaskEnergy (saskenergy.py) and Centra Gas Manitoba (centra_gas.py). Covers gas class scope, commodity and Default Rate Tariff rules, QRAM supply prices, CRA zero-carbon evidence, OEB rate-order cross-checks, negotiated ranges as conditions, edition/month checks and the Centra PDF-authority decision of 2026-11-02."
applyTo: "scrapers/utilities/enbridge_gas.py, scrapers/utilities/epcor_gas_ontario.py, scrapers/utilities/epcor_gas.py, scrapers/utilities/atco_gas.py, scrapers/utilities/fortisbc_energy.py, scrapers/utilities/energir.py, scrapers/utilities/heritage_gas.py, scrapers/utilities/liberty_gas_nb.py, scrapers/utilities/saskenergy.py, scrapers/utilities/centra_gas.py"
---
# Natural gas utilities

Generic scraper rules: [scrapers.instructions.md](scrapers.instructions.md). Class lists, exclusions
and gaps: [gap report](../../docs/live_parser_gap_report.md).

## All gas utilities

- Scope (owner decision 2026-10-09): priced firm and interruptible gas classes are in; storage-only
  and transport-only services are out; negotiated prices and price ranges are conditions, not charges.
- Never invent private (retailer or marketer) commodity prices, heat-value conversions or industrial
  eligibility. Delivery-only service leaves private commodity prices out; fixed-term and private
  commodity prices stay unpriced.
- Zero federal carbon needs the CRA fuel-charge page as evidence (Enbridge, ATCO Gas, EPCOR Ontario);
  a missing or contradicting cross-check fails closed.
- **Supply-price periods (Phase 6E, owner decision 2026-11-20):** each default supply (commodity)
  component carries the end of the period its official source states, so an ended price stops
  counting instead of looking current: Enbridge and EPCOR (OEB quarterly rate adjustment) the
  calendar quarter's end; Centra the day before its next quarterly date (February, May, August or
  November 1); Énergir supply and the Eastward General Service and Rate Class 3 gas cost recovery
  rate the month's end, Énergir cap-and-trade its quarter's end; the Eastward residential rate the
  end of its six-month block (January 31 or July 31); Liberty Utility Gas the month's end; ATCO Gas's
  DERS default rate the month's end. FortisBC and SaskEnergy prices stay open-ended (they change only
  by an approved order). A negotiated, value-less supply line carries no end date. Énergir, Eastward
  (registered as Heritage Gas), Liberty and ATCO Gas's DERS default rate (which must also be in the
  UCA table) are often posted after the 1st, so they are in the registry's `monthly_price_refresh`
  group and the Monthly Scrape on the 4th stores them (owner decisions 2026-11-20 and 2026-11-23;
  ATCO Gas added 2026-11-23).
- **Representative models depend on some stored wording (method 7D-2):** reviewed entries in
  `data/models/usage_levels.json` match component names and notes, and `data/models/crosswalk.json`
  `usage_bounds` restate the class limits. Keep them in step when a scraper changes: Liberty Utility
  Gas ("Optional utility supply at cost ...") and Liberty's two customer charges ("Monthly
  Distribution Customer Charge" and "... (higher consumption)" per class); Énergir's "Load Balancing"
  ("Applies to customers whose annual volume is less than 75,000 m³; ..."), its two "Renewable Gas
  Socialization" charges and its seven "Basic Fee — Band n" components with their annual thresholds;
  and the annual or monthly class limits stored as `usage_min`/`usage_max`. A mismatch fails closed:
  the class or charge becomes not computable in the models until the entry is reviewed.
- **The Building Archetypes costs (method AC-1)** price Enbridge EGD-6 and ATCO Gas Low and Mid Use.
  EGD-6's stored eligibility must contain the reviewed quote in `data/models/archetypes.json`
  (`gas.Enbridge Gas.class_quote`), and Enbridge's m³ use the reviewed heating value shared with the
  spark gap. ATCO's class is chosen by its stored usage limits, and exactly one class must fit. A
  mismatch makes the affected buildings' gas not computable until the entry is reviewed.

## Enbridge Gas (Ontario)

- Source: the OEB-approved Rate Handbook PDF; system-gas records in the EGD, Union North and Union
  South rate zones: EGD 1/6/100/110/115/145/170, Union North 01/10/20/100 for North West and North
  East plus 25, and Union South M1/M2/M4/M5.
- Include the QRAM gas supply and transportation prices, Rider C, Rider J (zero federal carbon with
  CRA evidence) and the facility carbon charge.
- Rider I and marketer-only Dawn transportation are conditional.
- Keep the repaired split-digit PDF artefact covered by tests.

## EPCOR Natural Gas (Ontario) (`epcor_gas_ontario.py`)

- Aylmer (Rate 1 residential and general service, Rates 2-5) and Southern Bruce (Rate 1 residential
  and commercial, Rates 6 and 11) from EPCOR's rate pages. Every value must appear in the OEB
  Decision and Rate Order Appendix A; the supply price must equal the OEB QRAM notice; CRA evidence
  is required. Aylmer Rate 6 and Southern Bruce Rate 16 are excluded.
- It has no seeds: when the sources fail it returns nothing.
- `epcor_gas.py` is the old Alberta "EPCOR Natural Gas" entry, retired on 2026-10-09 because EPCOR
  does not distribute gas in Alberta. Monthly runs skip it; keep its history.

## ATCO Gas (Alberta)

- North and South Low, Mid, High and Ultra High Use and ATA from the rate schedule PDFs; Riders L
  and T and South Rider W are dated components; Riders A/B and South Rider E are notes; CRA zero
  carbon is required.
- Commodity (owner decision 2026-10-09): Direct Energy Regulated Services' monthly Default Rate
  Tariff, on Low, Mid and High Use only. It must match the Utilities Consumer Advocate (UCA)
  default-rates table, whose current-year table must show the current month; otherwise every class
  priced with it fails closed. ATCO Gas is therefore in the `monthly_price_refresh` group (owner
  decision 2026-11-23): the run on the 4th catches a rate posted after the 1st.

## FortisBC Energy

- Official HTML tables plus official carbon evidence.
- Rates 1-3 have **daily** basic charges. The Rate 5 basic charge (written contract, about 5,000 GJ
  or more a year) is **monthly** as printed in the tariff, even though the business page says daily,
  so Rate 5 is not interchangeable with Rates 1-3.
- Rate 4 is seasonal (April 1-November 1).
- Revelstoke business rates are live only when the approved tariff index says the class is offered
  in Revelstoke. Fort Nelson Rates 4/5 have no published price table (a gap).
- Rate 11RNG is excluded (owner decision 2026-10-07).

## Energir

- Follow the pricing page to the current tariff PDF; fail closed on an edition/month mismatch.
- **Monthly supply and cap-and-trade prices (owner decision 2026-11-20):** the tariff prints supply and
  CTEAS prices only "as of" its edition date ("may be adjusted monthly" / "quarterly"). Both come from
  the supply-price page column for the current month and must match the two five-year price history
  workbooks it links. Supply runs from the first to the last day of the month; CTEAS from the first
  month of its quarter with the same workbook value to the quarter end. A month the page does not show
  yet, or a workbook that disagrees, leaves the supply price out (record notes explain it); CTEAS then
  falls back to the tariff's value only within the tariff edition's quarter. In the edition month the
  tariff's supply price must equal the page's, otherwise the supply price is left out.
- D3/D4 minimum daily obligation bands are per m³/day of **subscribed volume**. Above-subscribed-volume
  withdrawal, average load-balancing and renewable-gas charges are conditional.
- Inventory adjustments depend on each customer's storage use and have no published price: explain
  them, never give them a number.

## Eastward (Heritage Gas)

- Follow the business page to the monthly rate-table PDF, cross-check the page summaries and fail
  closed on an edition/month mismatch.
- **General Service summary date (owner decision 2026-11-19, issue #6):** the business page can lag the
  monthly rate table. An older "as of" date is accepted only when the page's fixed, base energy and gas
  cost values equal the table's exactly; the table sets the effective date and the record notes the
  page's date. A newer page date or any value difference is rejected. The residential summary stays
  strict: its date must match the table.
- Municipal riders apply to a limited charge base.
- Rate Class 3's demand charge is per GJ of Billing Demand per month (the greater of 225 GJ, contract
  demand or maximum 24-hour use); take this unit from the approved tariff PDF, not the rate table.
- Rate Class 4 is negotiated per site and not published: an exclusion, not a parser gap.

## Liberty NB

- Official HTML tables plus official carbon evidence.
- The MGS/LGS customer charges are alternatives.
- Off-Peak Service eligibility is April-November only; the December-March overrun is a note.

## SaskEnergy

- Parse the official HTML service variants with required, dated carbon evidence. The carbon evidence
  and the older base components keep their distinct dates; the tariff takes the latest required date.

## Centra Gas Manitoba

- **PDF authority (owner decision 2026-11-02):** the approved current quarterly PDF is the price
  authority, not stale website headings. `SCHEDULE_EDITIONS` requires the current quarterly period
  (February, May, August or November), not a commercial HTML headline. A new edition needs a
  `SCHEDULE_EDITIONS` entry. Its `general_pages` names the date and Board order its class-definition
  pages print (November 1, 2025, Order 138/25 in both supported editions): the check requires them and
  record notes cite them, while the prices cite the edition's own Appendix A order (owner decision
  2026-11-23: citations come from the edition).
- v1126 (PUB Order 150/26) supplies every scoped record from the Appendix A text tables on pages 81
  and 82 at high confidence, including Mainline Interruptible (owner decision 2026-10-30); base page
  80 is checked but not added.
- Validate the exact date, order, columns and units, and totals within one printed rounding unit.
  The commercial-page totals check allows one 0.01-cent rounding unit (owner decision 2026-10-30).
  Only volumetric transport may be signed (negative transport credits); reject other negative
  charges.
- Missing eligibility, carbon or marketer evidence still fails closed at its existing scope.
- Log stale or contradictory HTML and record it in the record notes; never describe it as matching
  evidence.
- Unknown quarters and missing current tables never fall back to old live prices.
- v0826 keeps its existing August HTML behaviour and the narrowly approved, hash-gated Mainline
  Interruptible transcription at medium confidence (historical support only). Never extend
  transcription to another scanned document without asking the owner.
- Keep delivery and volumetric demand parts separate; reconcile them to the published totals without
  double counting. Keep the CRA carbon evidence separate. Required PUB conditions fail closed.
