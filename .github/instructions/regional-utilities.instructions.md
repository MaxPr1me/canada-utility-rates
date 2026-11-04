---
description: "Use when changing electricity scrapers outside Ontario and Alberta, including the territories: BC Hydro, FortisBC Electric, Hydro-Quebec, Manitoba Hydro, SaskPower, NB Power, Nova Scotia Power, Maritime Electric, Newfoundland Power, NL Hydro, Yukon Energy, ATCO Electric Yukon (yukon_electrical.py), NTPC, Qulliq and the batch 18 municipal utilities (Saint John Energy, Nelson Hydro, New Westminster, Penticton, Grand Forks, Summerland, Summerside Electric). Covers HTML/PDF parser sources, conditional riders and credits, phase/amperage and kW/kVA alternatives, multipliers, continuation pages, market-indexed products (BC Hydro RS1892, FortisBC RS38, NSPower RTP, NL Hydro non-firm), Maritime's free first 20 kW, territorial subsidies and the Yukon joint rate book."
applyTo: "scrapers/utilities/bc_hydro.py, scrapers/utilities/fortisbc_electric.py, scrapers/utilities/hydro_quebec.py, scrapers/utilities/manitoba_hydro.py, scrapers/utilities/saskpower.py, scrapers/utilities/nb_power.py, scrapers/utilities/nova_scotia_power.py, scrapers/utilities/maritime_electric.py, scrapers/utilities/newfoundland_power.py, scrapers/utilities/nl_hydro.py, scrapers/utilities/yukon_energy.py, scrapers/utilities/yukon_electrical.py, scrapers/utilities/ntpc.py, scrapers/utilities/qulliq.py, scrapers/utilities/saint_john_energy.py, scrapers/utilities/nelson_hydro.py, scrapers/utilities/new_westminster.py, scrapers/utilities/penticton.py, scrapers/utilities/grand_forks.py, scrapers/utilities/summerland.py, scrapers/utilities/summerside_electric.py"
---
# Regional electricity utilities and territories

Generic scraper rules: [scrapers.instructions.md](scrapers.instructions.md). Class lists, exclusions
and gaps: [gap report](../../docs/live_parser_gap_report.md).

## Parser sources and exclusions

- HTML: Manitoba Hydro and NB Power (class-specific parsers) and BC Hydro and NSPower business
  service. PDF extraction: BC Hydro and NSPower residential service, FortisBC Electric, Hydro-Quebec,
  Maritime Electric, Newfoundland Power and NL Hydro.
- Excluded on purpose (owner decision 2026-10-07): BC Hydro RS1828 and Hydro-Quebec Rate F/FP.

## Market-indexed products (Phase 6D, live since 2026-10-30)

- Each is a live record: its fixed parts are real numbers and its market energy line is a value-less
  market component that never gets a number.
- **BC Hydro RS1892** (code `1892`): Mid-C peak/off-peak weighted index with a $0 floor plus a
  $3/MWh adder, kept in the text; RS1901/1904 riders.
- **FortisBC Electric RS38** (code `38`): interruptible pilot to 2028-07-31, medium confidence while
  the sheets say Interim; ICE Day Ahead Mid-C hourly price plus a $0.01/kWh adder. Its two customer
  charges are adopted by reference from RS30/RS31 and stored as alternatives.
- **NSPower One-Part Real Time Pricing** (`RTP-T`, `RTP-D`): the adders and transformer credit come
  from scanned pages whose OCR text layer was checked against the page images (owner-approved
  2026-10-30, medium confidence). Dates past the supported 2026 year fail closed. No FAM line.
- **NL Hydro 5.1L and `IND-NONFIRM`** (Island non-thermal): the NYISO/ISO-NE futures-based monthly
  on/off-peak energy is value-less; the Rate 2.4L floor is text only. Island thermal non-firm stays
  source-blocked as `IND-NONFIRM-THERMAL` (fuel formula).

## BC Hydro

- RS 1901/1904 exclude the 2101 TOD adjustments.
- Prorated tiers and conditional transformer discounts keep their source context.
- The business power-factor surcharge is a conditional percentage of the business rate charges for
  poor (lagging) power factor, not a charge for every customer. Its bands are conditional and fail
  independently.

## FortisBC Electric

- The current RS1 residential price is flat and supersedes the older tiered version, which stays in
  history. RS2A is closed.
- RS21 kW and kVA demand charges are alternatives; voltage/transformation discounts are conditional
  negative credits.
- Required continuation and date context must be present.

## Hydro-Quebec

- DM (grandfathered) and DN charges and energy allowances depend on the approved multiplier.
  Multiplier-based units, additive dwelling/room terms and alternative voltage credits must not
  become invented fixed allowances or bill totals. Preserve source multipliers, notice rules and
  separate component dates.
- DN applies north of the 53rd parallel except Schefferville and normally uses multiplier one; its
  older DM-eligibility exception does not restrict every DN customer.
- DP has summer and winter demand charges.
- Supply-voltage credits are conditional and do not apply to everyone. Minimum bills, demand
  allowances and transformation-loss rules stay conditions, not extra charges or calculated totals.
- Missing or future editions and missing continuation pages fail closed for the affected class only.
- DT switches price with the outdoor temperature, not the clock. Flex D uses notified events.
- Winter Credit is a closed, conditional adjustment to Rate D that keeps the published
  reference-energy rules; it is not a base rate or a calculated total.

## Manitoba Hydro

- A failure on the residential page or the commercial page affects only that page's records.
- Blocks are numbered 1..n with cumulative bounds; phase variants of the basic charge are
  alternatives, never summed; "First 50 kVA no charge" is a $0 block.
- The registry sources must match the scraper constants (`tests/test_source_urls.py` checks this).

## SaskPower

- Maintain the audited building scope: standard, bulk-metered and diesel residential service and
  R23/R24 renewable access.
- PDF discovery needs `fetch_rendered_page()`.
- Complete columns, dates and continuation pages gate each schedule independently; slice same-page
  schedules separately.
- Never put kVA thresholds in kW fields.
- Standard E01/E03 keeps its identity only when both published columns agree.
- Bulk-metered fixed charges are per unit, not per account.
- References: E41 is per meter location per month during the pumping season, not per season; its
  1997 closure is not an effective date. Keep native units for irrigation, unmetered and oil-field
  schedules without expanding the excluded processes.

## Nova Scotia Power

- The mandatory FAM, DSM and storm riders are separate from base energy. Green Power blocks are
  opt-in, not a standard charge.
- Residential service includes standard service, storage-heating time-of-day service and the
  closed-enrollment TOU and critical-peak pilots. The pilots are conditional; their records separate
  the tariff's conditional interim phase from its dated November pricing. A closed pilot is never
  proof of a participant's system-restoration status: do not assume it from an advertising page.
- MURB (MURB89) needs its own rider rows, house-meter eligibility, a minimum-bill condition and a
  weekend/holiday note: the approved book applies its peak price on weekends and holidays.
- Solar Garden and Community Solar records are subscriber adjustments to another tariff, not
  replacement household energy prices. Optional solar credits apply to subscriber generation, never
  to household consumption or a guessed bill offset.
- November prices are date-gated; dates past the supported tariff/rider year (such as 2027) fail
  closed.

## Maritime Electric

- Rates 232/233 (N-28) print the first 20 kW free. Store it as demand tier 1 ($0/kW, upper bound
  20 kW); tier 2 charges only the balance. Never discard the free block or charge the balance price
  on all demand; reject a missing or duplicate free-block structure.
- Parser-to-model tests cover the 20 kW boundary and all four business levels.

## NL Hydro

- Fixed phase/amperage choices are alternatives, never added together.
- Seasonal options need their matching complete, same-date base schedules.
- Keep native demand units; minimum and maximum bills stay conditions.

## Territories

- Government subsidies stay separate and conditional; never fold them into base prices.
- **NTPC:** the PUB schedule by zone, with per-community government rates. The GNWT Cost of Living
  Subsidy is a conditional credit. The TPSP printed first-block price is a conditional alternative
  energy price, never a derived difference. Taltson interruptible heating is conditional.
- **Qulliq:** the April 1, 2025 rates are interim: medium confidence until a final decision is
  published. The page's date label is stale.
- **Yukon Energy and ATCO Electric Yukon** share the text joint YECL/YEC rate book, cross-checked
  against the R/J cross-reference: the same 20 schedules, not 40 classes.
- **Yukon Energy Rate 1160:** take the base column, then the separate R/J/J1 percentage riders, fuel
  Rider F and dated energy-only residential relief. Never add riders to a price that already
  includes them.
- The other Yukon classes (1180-2480) come only from the text joint book and must reconcile with the
  cross-reference. Yukon Energy's own schedule PDFs are image-only: never read them into live values.
- The joint book gets a new address every month. Find it through ATCO's
  `understanding-rates.model.json` (the newest `yecl-yec-rate-schedules-MM-YYYY.pdf` on the AEY asset
  path not later than the current UTC month), then the static page link, then the last known link.

## Municipal utilities (batch 18, owner decision 2026-11-04)

- Saint John Energy (NB), Nelson Hydro, New Westminster, Penticton, Grand Forks, Summerland (BC) and
  Summerside Electric (PE) read council bylaw schedules or rate manuals. They have no seed fallback: a
  failed or doubtful source returns no records (batch 18 provisional decision). They join their
  province's representative-model medians like any registered utility.
- Discovery follows the current link on the official page each run, then a last-known document whose
  records say they came from it. Parse PDFs with `extract_pdf_pages(..., drop_repeated_lines=False)`:
  these schedules repeat identical price lines that the header/footer heuristic would drop. Bound each
  class to its own section so a missing price never borrows the next class's block.
- Dates: use the schedule's own date. Penticton prints only year columns ("Effective 2026"): use the
  current year's column dated January 1 and fail closed when that column is missing. Nelson's rates page
  year selects the bylaw's year-labelled schedules and must equal the current year; its 2026/2027 rates
  are interim (medium confidence). Grand Forks is dated by the amending bylaw named in Schedule G, whose
  prices must match the consolidation.
- Saint John Energy: keep Base Rate and Rate Rider separate and require base + rider = printed total.
  sjenergy.ca serves an incomplete certificate chain: discover the manual with headless Chromium; never
  disable TLS verification.
- Billing periods: bi-monthly basic charges are `$/two months`. Blocks printed per two-month or per
  "Billing Period" keep plain kWh thresholds with a reviewed `data/models/block_periods.json` entry
  (Grand Forks two months; Summerside monthly per the 2026-10-30 pattern). Penticton's "per billing" is
  monthly only while its accounts page says bills are mailed monthly.
- Percentage riders of the billed amount (New Westminster's 2.5% rider and 3.5% climate action levy) are
  stored as `%` components; the models disclose but do not apply them.
- Excluded on purpose (batch 18 provisional decisions): municipal-account rates (Saint John Municipal
  Related, Nelson E1, Penticton 45, Summerland E25), Nelson C1/C4 until the ">25 kVA" demand wording is
  confirmed (source-blocked), lighting, unmetered, EV charging, rentals and pilots.
