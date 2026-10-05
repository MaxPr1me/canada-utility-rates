# Phase 5 Completion Matrix

**Updated:** 2026-10-05. Scope: all 84 registered utilities, not every utility
in the broader Canadian inventory. The export has 648 stored tariff versions / 4,160
components / **168 stored live versions / 480 seed**. Latest-per-name coverage is
**166 live tariffs**; older versions remain in history. October 5 adds FortisBC Energy,
Energir, Heritage/Eastward and Liberty NB gas, then batch 5 electricity classes and fees
(NB Power, Newfoundland Power, Maritime Electric); October 2 updated NSPower, Hydro-Quebec, NL
Hydro, FortisBC Electric, SaskEnergy and Centra Gas. Ontario and the five excluded-region
gas utilities still have no live output.
Counts include retained non-building reference records, not only building tariffs.

## Active Regional Campaign (2026-10-05)

Four implementation batches cover the 16 registered utilities in BC, QC, MB, SK,
NB, NS, PE and NL: ten electricity and six gas utilities. Ontario, Alberta and
all three territories are excluded from this run, not removed from the database
or website. Provincial off-grid service in Quebec and Newfoundland and Labrador
remains in scope. No additional inventory utilities are being registered.

**Current checkpoint:** Regional Batch 5, electricity classes and fees (October 5, after
`a2a78a9`). There are
**164 latest live records at all 16 target utilities** and **602 passing tests**. No
target utility is seed-only, and none is catalogue-complete except SaskPower's audited
building scope. Local history contains 1,328 snapshots; prior snapshots and non-target
records were unchanged by the batch.

**Historical starting baseline:** 382 passing tests, 87 latest in-scope live records,
571 stored versions, 3,732 components and 1,208 snapshots. The three batches added
61 latest live records and 74 snapshots. These counts include optional adjustments
and retained non-building references. A successful scrape or one live residential
class does not establish complete building coverage.

| Priority | Utility queue | Next work |
|---|---|---|
| Gas catalogue gaps | FortisBC Energy; Energir; Heritage/Eastward; Liberty NB; SaskEnergy; Centra Gas | FortisBC Rates 6/7, Fort Nelson 4/5 (no price table) and Revelstoke propane; Energir D5, inventory adjustments, load-factor formula and fixed-price/renewable supply; Liberty CGS/ICGS (process loads) and marketer prices; SaskEnergy small industrial/fees; Centra PUB conditions |
| Remaining electricity audits | BC Hydro; FortisBC Electric; Hydro-Quebec; Manitoba Hydro; NB Power; Nova Scotia Power; Maritime Electric; Newfoundland Power; NL Hydro | Finish the class, optional-product, component and fixture gaps in the utility rows below; maintain completed SaskPower building coverage |

Utility parser and fixture work may proceed in parallel. Shared tests, registry,
database writes, exports, documentation and publication are integrated serially.
Each batch requires source-derived rejection tests, a current official-source
check and preservation comparisons before storage/publication. Source-blocked or
unaudited classes remain incomplete. Continue across verified milestones; reserve
time for a tested, pushed checkpoint and exact handoff before context exhaustion.

**Active building scope:** single-family and multi-unit residential, commercial,
institutional and building-related industrial service. NECB 2025 is a use-case
reference, not a utility eligibility rule or a compliance claim. Farm/oil-field
processes, irrigation, standalone street lighting, wholesale and other non-building
services are no longer completion requirements. Keep completed code and data as
reference; do not expand those classes just to fill the entire catalogue.

**Status vocabulary:** *dynamic parser, partial* reconstructs supported classes;
*verification path* checks known seed values but does not extract replacements;
*seed in latest export* means no live output was observed, not proof of a current outage.
*Complete* requires an audit and implementation of building-relevant standard classes
and components, with explicit non-building/special/unavailable exclusions. SaskPower's
audited published building-service schedules are implemented as of October 1; that
does not claim full-catalogue, tax-inclusive billing or building-code compliance.

BC Hydro, FortisBC Electric, Hydro-Quebec, NL Hydro, NSPower, SaskPower, SaskEnergy,
Centra Gas, FortisBC Energy, Energir, Heritage/Eastward, Liberty NB and Yukon Energy have
saved source-derived fixtures in `tests/fixtures/`.
Other tests include inline synthetic text and seed checks. Fixtures cover selected
classes and conditions, not necessarily complete utility catalogues. A shared verifier test,
successful process exit, or empty missing-data log does not establish live coverage.

Official discovery/document links live in [the registry](../data/sources/registry.json).
Keep those links synchronized with URL constants the scrapers actually fetch.
See the [gap report](live_parser_gap_report.md) for detailed findings and
[README](../README.md) for the ordered roadmap.

## Provincial Electricity

| Utility | Live tariffs / source-check date | Implemented path and supported scope | Next work |
|---|---|---|---|
| BC Hydro | 8 / Oct 1 | Approved PDF: tiered 1101, flat 1151, each +2101 TOD, closed dual-fuel 1105; three HTML business classes | Five residential options verified; preserve rider exclusions, prorated tiers and conditional discounts; other building-service audit remains |
| FortisBC Electric | 6 / Oct 2 | Approved PDF 1/2A/20/21/22A/23A, flat/TOU, conditional credits and kW/kVA alternatives | Large commercial 30-33/37/38, Green Power85, financing91, net-metering95 and EV96 remain |
| Hydro-Quebec | 9 / Oct 2 | D/DP/DM/DN/DT/Flex D, closed Winter Credit adjustment, G/M | Inukjuak, net-metering applicability and building business options remain; temperature/event conditions are not calculated bills |
| Manitoba Hydro | 8 / Oct 1 | HTML: residential and seven GS/voltage variants | Building-service audit; preserve kVA and seasonal rules |
| SaskPower | **41 / Oct 1** | **Audited building schedules implemented**; six source fixtures; total includes reference records | Monitor current sources; no remaining identified building-schedule parser gap in the audited catalogue |
| NB Power | 3 / Oct 1 | HTML: residential, GS1, small industrial | Remaining building-service schedules and fixtures |
| Nova Scotia Power | 10 latest / Oct 2 | Standard/TOD/conditional pilots, MURB89, two optional solar adjustments; existing business10/11/12 | Pilot restoration-status and broader business class/rider/date audit remain; unsupported 2027 dates fail closed |
| Maritime Electric | 10 / Oct 1 | IRAC PDF class-section extraction | Building-service audit and source-derived success/failure fixtures |
| Newfoundland Power | 4 / Oct 1 | RateBook PDF: 1.1/2.1/2.3/2.4 | Building-relevant schedules and fixture coverage |
| NL Hydro | 18 / Oct 2 | July PDF Island/Labrador/diesel, government distinctions, Burgeo school/library and two seasonal adjustments | Net-metering and commissioning scope plus contract-specific industrial applicability remain; preserve alternative fixed charges and conditional billing rules |

### SaskPower Delivered Batch

Source tables are effective February 1, 2026; the October 1 source run returned 41
records covering the building schedules below plus retained non-building references:

| Schedule | Supported codes | Preserved distinctions |
|---|---|---|
| Standard residential | E01/E03 | Identical city/rural columns verified before retaining one stable record |
| Bulk-metered residential | E01/E03 application | Closed to new customers; fixed charges per apartment unit or trailer stall |
| Diesel residential | E04 | First-650-kWh and balance tiers, isolated from the standard page |
| Supplied standard | E05/E06 | Urban/rural energy blocks and free first 50 kVA demand |
| Supplied small commercial | E75/E76 | Urban/rural thresholds, tiered energy and kVA demand |
| Customer-owned standard | E07/E08/E10/E12 | Voltage columns; E10/E12 closed to new customers |
| Customer-owned small commercial | E77/E78 | Urban/rural energy and demand tiers |
| Power time-of-use | E82/E83/E84 | Three voltages, on/off-peak hours and demand conditions |
| Power standard | E22/E23/E24 | Three voltages and demand-ratchet rules |
| Capacity reservation | N22/N23/N24 | Reservation eligibility, voltages and 23-month demand rule |
| Renewable Access Service | R23/R24 | Self-generation eligibility, two voltages and required billing-demand continuation |
| Non-farm irrigation | E37 | February-October pumping season, seasonal fixed and horsepower charges |
| Unmetered services | E15/E16/E17/E18 | Native watt-block, equipment and installed-capacity units; independent minimum-bill conditions |
| General service diesel | E35 | Monthly fixed charge and first-650-kWh/balance energy tiers |
| Farm | E34/E19/E41 | Household/agricultural use, irrigation seasons and closed-to-new interruptible service |
| Oil-field standard | E43/E44 | Supplied vs customer-owned transformation, per-metering-point charges and demand conditions |
| Oil-field power/TOU | E46/E47/E48 and E86/E87/E88 | Three voltages, on/off-peak hours and demand rules |

Tests require complete columns, source dates/units and continuation pages, and
isolate schedule failures. Targeted storage preserved all prior snapshots and unchanged
non-SaskPower records. The two old generic commercial seeds remain labelled estimates
in storage. Farm/oil-field, irrigation and other non-building additions are retained
reference work, not the active queue. Forty-one live records is not a count of
41 building tariff classes. The audit covers the published net charges and billing
conditions in the linked building-service schedules; excluded taxes/surcharges and
bill calculations are not claimed. Standard residential identity and historical
snapshots remain intact after the expanded coverage.

## Ontario Registry Inventory

There are 53 registry entries using one `OntarioLDCScraper`. Current company/merger
identities and rate zones still need reconciliation before these can be described as
53 active independent distributors. Every distributor below has **0 live tariffs in
the integrated October 1 export**. The OEB common-price row is a shared source, not a utility.

Current code verifies seeded structures against configured HTML pages plus OEB common
rates. It does not dynamically parse approved distributor PDFs. The strategy column
below is the **target**, not delivered extraction capability; the fixture column denotes
shared synthetic verifier tests, not saved source-derived tariff fixtures. Common energy
prices cannot prove distributor-specific delivery/transmission/rider charges. Existing
modelled street-lighting rows are reference data, not a requirement for building coverage.

| Utility | Official source | Format | Modelled tariffs | Target strategy | Status | Shared test coverage | Remaining gap |
|---|---|---|---|---|---|---|---|
| Ontario OEB common rates | OEB electricity-rates page | HTML | TOU, tiered, ULO; verify which other charges are truly common | Dynamic product parsing and contextual verification | Current path checks seeded values, not replacement extraction | Shared verifier tests | Parse current products/dates and distinguish per-LDC charges |
| Alectra Utilities | https://www.oeb.ca/consumer-information-and-protection/electricity-rates<br>https://alectrautilities.com/rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Algoma Power Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Atikokan Hydro Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Bluewater Power Distribution | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Brantford Power Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Burlington Hydro Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates<br>https://burlingtonhydro.com/charges-rates/ | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Canadian Niagara Power Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Centre Wellington Hydro Ltd. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Chapleau Public Utilities Corp. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Elexicon Energy Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Entegrus Powerlines Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Enwin Utilities Ltd. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Erie Thames Powerlines Corp. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Espanola Regional Hydro | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Essex Powerlines Corp. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Festival Hydro Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Fort Frances Power Corp. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Greater Sudbury Hydro Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Grimsby Power Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Guelph Hydro Electric Systems Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Halton Hills Hydro Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Hearst Power Distribution Co. Ltd. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Hydro 2000 Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Hydro Hawkesbury Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Hydro One Networks Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates<br>https://www.hydroone.com/rates-and-billing/rates-and-charges/residential-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Hydro Ottawa Ltd. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates<br>https://hydroottawa.com/en/accounts-services/accounts/rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Innpower Corporation | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Kingston Hydro Corporation | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Kitchener-Wilmot Hydro Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates<br>https://www.kwhydro.ca/billing-payments/rates/ | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Lakefront Utilities Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Lakeland Power Distribution Ltd. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| London Hydro Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates<br>https://www.londonhydro.com/accounts-and-billing/understanding-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Midland Power Utility Corp. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Milton Hydro Distribution Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Newmarket-Tay Power Distribution Ltd. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Niagara Peninsula Energy Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| North Bay Hydro Distribution Ltd. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Northern Ontario Wires Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Oakville Hydro Electricity Distribution Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Orangeville Hydro Limited | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Oshawa PUC Networks Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Ottawa River Power Corporation | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| PUC Distribution Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Rideau St. Lawrence Distribution Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Sioux Lookout Hydro Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| St. Thomas Energy Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Synergy North Corporation | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Tillsonburg Hydro Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Toronto Hydro-Electric System Ltd. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates<br>https://www.torontohydro.com/for-home/rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Wasaga Distribution Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Waterloo North Hydro Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Welland Hydro-Electric System Corp. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
| Westario Power Inc. | https://www.oeb.ca/consumer-information-and-protection/electricity-rates | HTML | Residential, GS <50 kW, GS ≥50 kW, street lighting | OEB common-rate parse plus contextual approved-tariff verification | Blocked | OEB/LDC contextual verifier fixture | Registry lacks an individual approved tariff source or current document has not been fixture-audited; seed is exported only as unverified fallback |
Pilot materially different documents, such as Toronto, Ottawa and multi-zone Hydro One,
before rollout. Legacy `toronto_hydro.py` is unregistered; do not duplicate Toronto's
current registry entry. No interim mixed-live tariff label should bypass missing delivery data.

## Alberta Electricity

Gas entries are tracked once in the next section. All source-check counts here are
from October 1 CI observations; there are no saved utility-specific source fixtures yet.

| Utility | Live tariffs | Implemented path | Required work |
|---|---|---|---|
| ATCO Electric | 0 | Seed verification wrapper | Current approved building-service distribution tables |
| FortisAlberta | 1 | Rate 11 residential PDF parser; other seeds | Building-service distribution catalogue and fixtures |
| EPCOR Distribution | 0 | Seed verification wrapper | Current Edmonton distribution schedules, classes and riders |
| ENMAX Power | 0 | Seed verification wrapper | Current Calgary distribution schedules, classes and riders |
| Direct Energy Regulated Services | 0 | Seed verification wrapper | Current default-retail product, territory, terms and energy/admin components |
| ENMAX Energy Corporation | 0 | Seed verification wrapper | Current default-retail product and effective terms |
| EPCOR Energy Alberta | 0 | Seed verification wrapper | Current default-retail product and effective terms |
| Alberta Electric System Operator | 0 | Seed verification wrapper | Dated official market observations with published units/cadence |

Verify the Rate of Last Resort transition and provider terms before choosing a parser
model; legacy RRO seeds do not prove a monthly pool-price pass-through. Keep wires,
retail and wholesale references separate. Historical dead-URL reports need rechecking,
not automatic classification as present outages.

## Natural Gas

SaskEnergy now has six live records and Centra Gas twelve; the October 5 batch adds
FortisBC Energy eight, Energir four, Heritage/Eastward three and Liberty NB four, all with
source-derived fixtures. The five excluded-region gas utilities remain seed-only. No gas
utility is yet certified complete for its published building catalogue.

| Registry utility | Region / campaign | Latest live records | Implemented path and remaining work |
|---|---|---|---|
| Enbridge Gas | ON / excluded | 0 | Seed verification; legacy rate zones and full component extraction remain deferred |
| Énergir | QC / live, partial catalogue | 4 / Oct 5 | Default Rate D1 (residential and business listings) from the pricing page's linked October 1, 2026 tariff PDF: seven basic-fee bands, nine daily distribution blocks, supply, transportation, conditional load balancing and renewable-gas socialization, cap-and-trade (CTEAS); D3 and D4 (article 14.3) with subscribed-volume bands in $/m³/day and conditional above-subscribed withdrawal/load-balancing prices. Remaining: interruptible D5, inventory-related adjustments, load-factor formula, rate reductions, fixed-price/renewable supply |
| FortisBC Energy | BC / live, partial catalogue | 8 / Oct 5 | Rates 1/2/3 for Mainland/Vancouver Island and Fort Nelson (July 1, 2026; $/day basic, $/GJ components) with the BC carbon-tax elimination notice required; Rate 5 General Firm Service (basic $469.00 per month as the tariff prints it) and seasonal Rate 4 (Apr 1-Nov 1) for Mainland/Vancouver Island from the approved schedules. Remaining: Revelstoke propane, Rates 6/7, Fort Nelson 4/5 (no published price table), marketer prices |
| ATCO Gas | AB / excluded | 0 | Seed verification; current approved delivery classes/riders remain deferred |
| EPCOR Natural Gas | AB registry entry / excluded | 0 | Seed verification; product, jurisdiction and identity still need confirmation |
| Centra Gas Manitoba | MB / live, partial catalogue | 12 / Oct 2 | Residential/commercial Sales/T-service/marketer variants; full PUB class/demand/alternate-supply conditions and fixed-term products remain under review |
| SaskEnergy | SK / live, partial catalogue | 6 / Oct 2 | Residential/small/large-commercial full/delivery-only variants; small-industrial applicability, fees and municipal-payment scope remain under audit |
| Heritage Gas / Eastward Energy | NS / live, partial catalogue | 3 / Oct 5 | Residential and tiered General Service from the October 2026 monthly rate table linked by 'View Rates', cross-checked with page summaries; dated zero federal charge note required; municipal riders A/B as percentages; Rate Class 3 ($1,995.54/month, $0.167/GJ, $30.85 per GJ Billing Demand/month, unit and rule from the approved tariff PDF). Rate Class 4 is negotiated per site and unpublished (exclusion, not a parser gap) |
| Liberty Utilities NB / Natural Gas NB | NB / live, partial catalogue | 4 / Oct 5 | SGS, MGS, LGS (January 1, 2025 distribution; alternative customer charges; LGS seasonal blocks) and Off-Peak Service ($50.00/month, April-November eligibility, December-March overrun note) with the current Liberty Utility Gas month and CRA New Brunswick evidence. CGS/ICGS are process-load exclusions; marketer prices not included |

Preserve m3/GJ, volume tiers and component source ownership. Verify current tax/carbon
applicability rather than copying obsolete charges. Incomplete commodity/delivery
coverage must not be hidden under a live tariff label; do not invent unit conversions.

## Northern Electricity

This section is retained reference coverage, outside the current regional campaign.

Observed counts below use the latest tariff versions. Yukon 1160 was refreshed locally
on October 1 with a multi-document source fixture; other entries retain CI results.
Representative seed zones are not proof of the actual published catalogue.

| Utility | Live tariffs | Implemented path | Required work |
|---|---|---|---|
| Yukon Energy | 1 latest | 1160 base rates + separate R/J/J1 percentages, F and dated residential relief; source fixture and 18 focused tests | Broader building classes and Rider A require OCR/text alternatives for image-only base PDFs; not complete |
| Yukon Electrical Company | 0 | Seed verification wrapper | ATCO Electric Yukon/Yukon Utilities Board sources and class/rider applicability |
| Northwest Territories Power Corporation | 0 | Seed verification wrapper | Confirm actual service territory, zones/classes and subsidy eligibility; full extraction |
| Qulliq Energy Corporation | 0 | Seed verification wrapper | Current QEC/regulator class schedules and subsidy applicability |

Yukon 1160 now reads the base column and separately sources J1/F/relief with class,
unit and date checks; R/J rates and dates come from the official cross-reference.
The rebate is limited to eligible energy up to 1,500 kWh and ends March 31, 2027;
it excludes Rider F and fixed charges. Older versions remain in history.

The detailed 1160 and 2160 PDFs are image-only. Rendered source pages confirm that
general service includes demand and four energy blocks, while the readable
cross-reference lists only block 4. Do not infer the missing blocks from seeds.
Deferred gate: reviewed OCR or authoritative text for full building-class extraction
when territorial work resumes. Do not open this work during the restricted campaign.

## Next Batches and Acceptance

1. Gas batches 3 and 4 (October 5) implemented FortisBC Energy, Energir, Heritage/Eastward and Liberty NB (including Rate 5/4, D3/D4, Rate Class 3 and Off-Peak); all sixteen target utilities have live output. Next: the remaining gas catalogue gaps (see the Natural Gas table).
2. Finish the recorded catalogue and component gaps at the twelve already-live target utilities. HQ DT/Flex D/Winter Credit, FortisBC Electric's six schedules, NSPower MURB/solar, NL Hydro's eighteen records and SaskEnergy/Centra variants are implemented, not the next missing parser tasks.
3. Audit the still-unreviewed building catalogues and add source-derived fixtures at BC Hydro business, Manitoba Hydro, NB Power, Maritime Electric and Newfoundland Power as needed; maintain SaskPower's audited building schedules. End with an explicit sixteen-utility refresh and class-level reconciliation. ON/AB/YT/NT/NU remain excluded from this run.
4. Separate operational track: browser-enabled source health, meaningful provenance counts,
   failure reporting, deployment triggering and durable CI history.
5. Deferred product track: market-model UI/metadata correction, real observation ingestion,
   historical charts and AI export. Calculator/API requirements are separate.
6. Conditional Alberta extension: if its market-pricing variation or complexity warrants
    a dedicated view, add Alberta as a region in the existing Market Pricing dashboard.
    Use Alberta-specific values, sources, dates and methodology; reuse the interface,
    not Ontario's HOEP-plus-GA assumptions. Keep wholesale, retail and wires distinct,
    with any modeled estimates clearly identified. This remains deferred work.
7. Phase 6 also includes the separate Across-Canada comparison view described in
    [README](../README.md#phase-6-provenance-and-product-follow-up): common residential
    structures, monthly charges, commercial demand-class ladders and transparent
    provincial utility blends. It is a roadmap item, not an implemented feature.

Each batch requires source-derived positive/negative tests, a source-inspected dry run,
validated storage/export, preserved history and a ledger update. Record observation dates
separately from parser capability, keep unsupported classes visible, and never delete a
database or invent rates to make completion metrics look better.

## Historical Checkpoint: BC Hydro (2026-10-01)

Historical checkpoints retain their original counts and resume instructions for
traceability. Use the active queue above and the final Regional Batch 2 checkpoint
for current work; do not resume an older queue.

**Completed:** BC Hydro now parses five residential options from the approved tariff:
1101 tiered, 1151 flat, both with optional 2101 time-of-day, and closed dual-fuel 1105.
Riders 1901/1904 are source-parsed; their percentage base excludes 2101 adjustments.
Conditional transformer discounts and monthly/bi-monthly tier rules are preserved.
The existing tiered name remains stable. Eight live BC tariffs (including business)
were dry-run checked, stored and exported; all other utilities and snapshots were retained.

**Verification:** 325 tests pass, including 19 BC-focused tests. Database validation has
zero errors and two existing AESO class warnings. New source fixture:
`tests/fixtures/bc_hydro_residential.json`. No frontend code changed in this checkpoint.

The NSPower resume instructions below describe the October 1 handoff. That parser
batch has since progressed; use the final Regional Batch 2 checkpoint for current status.

**Resume here:**
1. Read `scrapers/utilities/nova_scotia_power.py` at `_try_live_scrape()` and
    `_parse_residential()`, plus `TestNovaScotiaPowerSeed` in `tests/test_live_parsers.py`.
2. Inspect the official residential catalogue starting at
    https://www.nspower.ca/your-home/residential-rates/standard-residential and follow
    its current time-based product/tariff links. Distinguish generally available rates,
    storage-heating/equipment requirements, closed offerings and pilots. Preserve actual
    seasonal calendars, hour windows, fixed charges, rider bases and effective dates.
3. Add a small source-derived fixture and failing product-coverage test, then extend
    the residential owner path without letting a failed optional plan erase valid classes.
4. Run `./venv/Scripts/python.exe -m pytest -q tests/test_live_parsers.py -k NovaScotia`,
    then the full suite and a targeted official-source dry run before storage/export.
5. Audit the remaining utilities' residential catalogues and record exact implemented,
    missing, closed/conditional and source-blocked products. Existing Ontario shared
    TOU/Tiered/ULO seeds are not proof of individual distributor verification. Gas and
    northern/community variants must retain their actual eligibility and units.

The supported local test interpreter is `./venv/Scripts/python.exe` (Python 3.11);
the old editor-selected `.venv` remains Python 3.9 with missing dependencies. Preview:
http://127.0.0.1:8000/ (reload to read the latest JSON). Leave unrelated
`.claude/worktrees/` modifications untouched. Near the requested 90% context threshold,
stop new work, validate the current batch, update this checkpoint/handoff and push before
ending; checkpoint conservatively when exact token usage is unavailable.

## Residential Catalogue Audit (2026-10-02)

This catalogue ledger includes the two October 2 implementation batches, not a fresh
live-rate run for every utility. The rest of the registry still needs review; no
absence of optional products is inferred from an old seed or a single residential page.

| Utility/group | Official evidence reviewed | Finding and remaining gate |
|---|---|---|
| BC Hydro | October 1 approved tariff and residential pages | Five options implemented: tiered/flat, both +TOD, closed dual-fuel. Preserve conditions/rider exclusions |
| NSPower | October 2 [residential catalogue](https://www.nspower.ca/your-home/residential-rates/standard-residential) and [May 2026 tariff book](https://www.nspower.ca/docs/default-source/regulatory/tariff-book-2026.pdf) | Standard, storage TOD, conditional closed pilots, MURB89 and two optional solar adjustments implemented. Pilot restoration-status and broader business/rider/date coverage remain open |
| Hydro-Quebec | October 2 [domestic-rate catalogue](https://www.hydroquebec.com/residential/customer-space/rates/) and approved tariff | D/DP/DM/DN/DT/Flex D and closed Winter Credit adjustment implemented. Inukjuak, net metering and remaining building business options are still gaps |
| FortisBC Electric | October 2 [official Electric Tariff](https://fbcdotcomprod.blob.core.windows.net/libraries/docs/default-source/about-us-documents/regulatory-affairs-documents/electric-utility/fortisbcelectrictariff.pdf) | Flat residential1 and closed TOU2A implemented with commercial20/21/22A/23A. Large commercial and Green Power/financing/net-metering/EV schedules remain under audit |
| NL Hydro | October 2 approved July 2026 schedule | Island/Labrador/diesel/government domestic and general service plus two seasonal adjustments implemented (18 records). Net-metering/commissioning and contract-specific industrial applicability remain open |
| Ontario shared prices | October 2 [OEB price catalogue](https://www.oeb.ca/consumer-information-and-protection/electricity-rates) | TOU, ULO and Tiered choices confirmed; displayed current prices effective November 1, 2025. RPP prices already include an estimate of GA. This does not verify any LDC's delivery charges or merger identity |
| Manitoba Hydro, NB Power, Maritime Electric and Newfoundland Power | Existing matrix/source history; no new campaign catalogue audit yet | Optional/conditional residential and broader building catalogue/fixture audits remain pending; do not mark default-only outputs complete |
| Northern and Alberta families | Existing matrix/source history only in this pass | Preserve community, government/subsidy and wires/retail distinctions; current product audit remains pending |
| SaskEnergy and Centra Gas Manitoba | October 2 official rate/supply pages and required carbon evidence | Six SaskEnergy and twelve Centra live variants; remaining class/eligibility and ancillary-charge gaps are documented above |
| Four October 5 gas utilities | October 5 official pages/documents and dated carbon evidence | FortisBC Energy 8, Energir 4, Eastward 3 and Liberty NB 4 live; their remaining classes are listed in the Natural Gas table |

## Historical Checkpoint: NSPower (2026-10-02)

**Implemented:** standard 02/03/04, equipment-qualified TOD 05/06, and the published
conditional pilot variants 70/80. Current standard base energy is 18.324 cents/kWh,
with separate FAM 0.156, DSM 0.648 and storm 0 cents/kWh; monthly customer charge is
$20.08. Green Power blocks are explicitly optional, not a mandatory $5 addition.

**Important limitation:** advertising pages show time-varying prices, but the approved
tariff includes restoration-dependent interim provisions through October 31, 2026.
The October pilot records describe that conditional variant and do not establish any
participant's restoration status. The November 1 winter phase is date-gated and tested,
with stable plan names and source-derived hour/holiday/event rules. No future 2027
price is silently used in 2026. Broader NSPower coverage is not marked complete.

**Verified:** 350 full tests and 32 NSPower-focused tests; seven valid live records
in the targeted dry run/store (four residential plus existing business 10/11/12).
Database validation has zero errors and the same two AESO class warnings. Prior
snapshots and other utilities were preserved. Two unpublished pilot display labels
were normalized to stable plan names; snapshot contents were not altered.
Desktop/mobile browser checks confirmed four residential options, estimate hiding,
storage-heating eligibility, conditional pilot notices and a horizontally scrolling
comparison table without page overflow at a 390px viewport. No frontend code changed.

**Exact next work:**
1. Implement source-confirmed Hydro-Quebec residential gaps and/or FortisBC Electric
    from its approved tariff, using small source-derived fixtures and independent
    failure handling. Record dates and eligibility before claiming a plan current.
2. For NSPower, inspect tariff-book pages 35-37 (MURB TOU), 69-73 (Solar Garden) and
    80-83 (Community Solar). Their existence is known; their values/eligibility are not
    implemented by this batch. Verify pilot restoration announcements before claiming
    the interim variant applies to every existing participant.
3. Continue the unreviewed residential catalogue groups above; Ontario common prices
    alone cannot make distributor-specific tariffs live. Keep the building focus and
    preserve completed non-building reference data.

Use `./venv/Scripts/python.exe -m pytest -q tests/test_live_parsers.py -k NovaScotia`
for the NSPower slice. The preview was restarted at http://127.0.0.1:8000/; restart it
with `python -m http.server --bind 127.0.0.1 --directory site 8000` if it has stopped.
Keep the earlier context-checkpoint and scoped-push rules.

## Historical Checkpoint: Hydro-Quebec DP/DM (2026-10-02)

**Implemented:** domestic-demand DP and grandfathered bulk-metered DM, alongside
unchanged D/G/M identities. All five read the April 1, 2026 publication date from
the official PDF. DP keeps monthly energy tiers, separate summer/winter demand,
minimum bills and winter demand-ratchet conditions. DM retains its May 31, 2009
eligibility cutoff, dwelling/room multiplier, daily multiplier-based charges/tiers
and variable base-demand allowance. No dwelling count or bill total is assumed.

**Conditional charges:** DP's five supply-voltage rebates are mutually exclusive
bands, not cumulative discounts. DM's domestic voltage credit is also conditional.
Transformation-loss rules remain source text, not a calculated adjustment. Required
continuations and shared billing/credit pages must be present; failures are isolated
by domestic class. Missing or future edition dates fail closed. Landing-page failure
does not prevent direct PDF parsing.

**Verified:** 21 Hydro-Quebec-focused tests and 366 full-suite tests pass. The live
dry run and stored scrape each returned five valid live tariffs; database validation
has zero errors and the two existing AESO class warnings. Export: 570 versions,
3,727 components, 90 stored live versions / 88 latest live tariffs / 480 estimates.
All 1,197 prior snapshot contents/hashes and 565 non-Hydro-Quebec exported records
were unchanged; five snapshots were appended and older tariff versions retained.
Desktop/mobile browser checks confirmed three domestic options, default estimate
hiding, multiplier/eligibility text, conditional voltage credits and a horizontally
scrolling comparison without page overflow or JavaScript errors at 390px. Preview:
http://127.0.0.1:8000/ (reload for the updated data).
The new source-derived fixture is
[hydro_quebec_domestic.json](../tests/fixtures/hydro_quebec_domestic.json).

**Exact next work:**
1. Start at `_parse_domestic_rates()` in
    [hydro_quebec.py](../scrapers/utilities/hydro_quebec.py) and `TestHydroQuebecDomestic`
    in [test_live_parsers.py](../tests/test_live_parsers.py). Inspect physical PDF
    pages 127-128 for DN: north-of-53rd-parallel/off-grid applicability, Schefferville
    exclusion, default versus grandfathered multiplier and demand continuation.
    Save a reviewed fixture and failing coverage test before extending the parser.
2. Then audit DT pages 21-24, Flex D and Winter Credit, including equipment,
    temperature-zone/event rules, enrollment limits and effective periods. Winter
    Credit is not automatically open enrollment. DN's DT exclusion and the Inukjuak
    domestic variant at page 139 onward must not be collapsed into a generic rate.
3. FortisBC's approved tariff and the still-unaudited residential catalogue groups
    remain next leads; NSPower MURB/solar/pilot-status gaps and broader Yukon OCR
    work remain explicit. Keep building scope and completed reference data intact.

Focused command: `./venv/Scripts/python.exe -m pytest -q tests/test_live_parsers.py -k HydroQuebec`.
Follow with the full suite, targeted dry run, preserved-history storage/export and
updated ledger before publishing the next batch. No frontend, schema or shared
pipeline changes were needed for DP/DM. Stop at this verified bounded checkpoint
before opening the next parser slice when approaching the context limit.

## Historical Checkpoint: Hydro-Quebec DN (2026-10-02)

**Implemented:** DN domestic off-grid supply north of the 53rd parallel, excluding
Schefferville. April 1, 2026 base charges are $0.46154/multiplier/day and energy
$0.07065/$0.50469 per kWh, with the first 40 kWh/day/multiplier. DN defaults to
multiplier one unless the contract was DM-eligible on May 31, 2009; this is not a
closed-enrollment restriction on the entire DN tariff. The printed continuation
confirms additive dwelling/room terms in the applicable exception branches.

**Conditions retained:** complete winter demand-ratchet and variable kW allowance
rules, $7.266/kW/month demand charge, DT's off-grid exclusion and the conditional
supply credit incorporated by article 9.2 from article 12.3. The parser requires
both DN pages and shared definitions/credit sources. Missing or malformed DN
context rejects DN while independent DP/DM classes remain live. No bill is calculated.

**Verified:** 37 Hydro-Quebec tests and 382 full-suite tests pass. The targeted
dry run/store returned six valid live records (four domestic plus G/M). Export:
571 versions / 3,732 components / 91 stored live / 89 latest live / 480 estimates.
All 1,202 prior snapshot contents/hashes and 565 non-Hydro-Quebec records were
unchanged; six snapshots were appended. Validation has zero errors and the two
existing AESO class warnings. Desktop/mobile checks confirm DN's eligibility,
multiplier, higher second tier and conditional credit, with estimates hidden and
comparison scrolling without page overflow or JavaScript errors at 390px.
No frontend, schema or shared pipeline changes were needed.

**Exact next work:** inspect physical PDF pages 21-24 for DT dual-energy service,
starting from `_parse_domestic_rates()` and `TestHydroQuebecDomestic`. Establish the
required equipment, temperature-zone switching thresholds, eligibility variants,
multiplier/demand rules and component sources before adding a fixture and failing
coverage test. Do not model temperature switching as ordinary hourly TOU, or apply
DT to DN off-grid customers. Then continue Flex D/Winter Credit, the Inukjuak
domestic variant and net-metering review; FortisBC and other national residential
groups remain queued. Broad Hydro-Quebec residential coverage is still incomplete.

Use `./venv/Scripts/python.exe -m pytest -q tests/test_live_parsers.py -k HydroQuebec`
for the focused checks. Preview remains http://127.0.0.1:8000/. Preserve all existing
history and reference classes, leave unrelated worktrees untouched, and checkpoint
the tested batch before opening new work near the context limit.

## Historical Checkpoint: Regional Batch 1 (2026-10-02)

**Delivered:** three further HQ options (DT/Flex D/Winter Credit), 18 NL Hydro
building-service/seasonal records and six SaskEnergy service variants. Sources and
fixtures are registered; all 33 returned records were freshly fetched and validated
before serial storage. New permanent tests reject missing carbon evidence, negative
charges, future enrollment dates, incomplete billing/eligibility continuations and
wrong units, and prove independent failures plus repeated storage/export.

**Verification:** 428 tests pass; zero database errors and the two unchanged AESO
warnings. All 1,208 previous snapshot contents/hashes and 561 non-target tariff
records were unchanged; 33 snapshots appended. Export: 598 versions, 3,832 components,
118 stored live / 116 latest live / 480 seed. Scope-only latest live count is 114.

**Remaining, not complete:** HQ Inukjuak, net-metering and building business options;
NL Hydro net-metering/commissioning and contract-specific industrial applicability;
SaskEnergy small-industrial eligibility and ancillary/municipal charges. The small
industrial label alone is not evidence that its building loads are excluded. Private
gas-retailer commodity prices are outside the published delivery-only product and
are never invented. All other campaign utilities still need their source audits.

**Next parallel assignments:** FortisBC Electric current approved tariff; NSPower
MURB/solar/building-service gaps; Centra Gas Manitoba current residential/general
service. Shared integration remains serial. Continue the 16-utility queue; do not
restart excluded Ontario/Alberta/territory work or call a partial batch complete.

## Historical Checkpoint: Regional Batch 2 (2026-10-02)

**Delivered:** FortisBC Electric six January 2026 schedules (flat residential,
closed residential TOU and four commercial variants); NSPower MURB89 and two
optional solar adjustments (ten current records total); Centra Gas twelve current
residential/commercial Sales, T-service and marketer-supply variants. Native units,
conditional credits, alternative demand bases and component dates remain explicit.
The unusual MURB weekend/holiday peak-price rule was visually checked against the
official PDF. Solar credits use subscriber-attributable generation, not consumption.

**Verified:** 465 tests pass. Live dry runs and the guarded store returned 6/10/12
valid live records. An initial pre-store attribution failure wrote nothing; the
assembler was repaired and its focused tests rerun before the successful store.
All 1,241 prior snapshot contents/hashes and 587 non-target records were unchanged;
28 snapshots appended (1,269 total). Validation: zero errors, two unchanged AESO
warnings. Desktop/mobile filtering shows 6/10/12 cards, keeps estimates hidden and
has no page overflow or JavaScript errors. No frontend source changes.

**Current counts:** 619 versions / 3,935 components / 139 stored live / 137 latest
live / 480 seed. Scope-only latest live count is 135, across 12 of the 16 target
utilities. This is not a full-building-catalogue completion claim.

**Exact next assignments:** FortisBC Energy, Energir and Heritage/Eastward gas
source extraction in parallel, then Liberty NB. Their current parser paths remain
verifier-only. Preserve jurisdiction-specific carbon/adjustment evidence, native
units, service-area/supply choices and required component periods; no invented
private prices or conversions. Continue the remaining electricity audits and all
recorded first/second-batch gaps afterward. FortisBC Electric large-commercial and
optional riders, NSPower business/rider/date coverage, and Centra's full PUB tariff
conditions/fixed-term products are still open, not silently excluded.

Use the supported `./venv/Scripts/python.exe`; current targeted selectors include
`FortisBCElectricLive`, `NovaScotiaBuildingOptions`, `CentraGasLive` and
`RegionalBatchStorage` in the existing live-parser test module. Keep shared edits,
DB/export/Git integration serial. Before context exhaustion, finish this tested
checkpoint and push verified paths; do not leave unvalidated parallel work staged.

### End-of-Day Handoff (2026-10-02)

- Parser milestones `6cdbc67` and `9b5980d` are published; the Pages deployment for
    `9b5980d` succeeded. The current test result is 465 passing. Documentation now
    distinguishes current coverage from historical checkpoints and planned features.
- Closing totals remain 137 latest live records nationwide, including 135 across
    12 of the 16 campaign utilities, with 1,269 local snapshots preserved. This
    closeout does not run a new scrape or change exported rates.
- Resume with FortisBC Energy, Energir and Heritage/Eastward in parallel, then
    Liberty NB. Follow with the recorded catalogue/component audits; the campaign
    is not complete. Keep ON/AB/YT/NT/NU excluded and shared integration serial.
- The Phase 6 Across-Canada comparison design is saved in
    [README](../README.md#phase-6-provenance-and-product-follow-up). It remains future
    work; no national-comparison UI or bill calculator has been implemented.

## Historical Checkpoint: Regional Batch 3 — Gas (2026-10-05)

**Delivered:** FortisBC Energy 6 (Rates 1/2/3 × Mainland-Vancouver Island/Fort Nelson),
Energir 2 (default Rate D1, residential and business listings), Heritage/Eastward 2
(Residential, tiered General Service) and Liberty NB 3 (SGS/MGS/LGS). All four
replace verifier-only paths with source-derived extraction and four new fixtures
(`fortisbc_energy.json`, `energir.json`, `heritage_gas.json`, `liberty_gas_nb.json`).
Carbon evidence is required and dated separately: BC carbon tax eliminated April 1,
2025; Quebec cap-and-trade 8.727¢/m³; Eastward's own zero federal-charge note; CRA
New Brunswick period. Energir and Eastward follow the current document link each run
and fail closed if the linked edition/month does not match the page.

**Verified:** 507 tests pass (42 new gas tests). Live dry runs returned 6/2/2/3 live
records with no fallback. Guarded stores validated every record as live with complete
component sources before writing, appended 13 snapshots (1,282 total), and left all
prior snapshots and non-target tariffs unchanged. Validation: zero errors. No frontend,
schema or shared pipeline changes; no browser smoke test was run for this batch.

**Current counts:** 632 versions / 4,044 components / 152 stored live / 150 latest
live across 18 utilities / 480 seed. Scope-only latest live count is 148 across all
16 target utilities. This is not a full-building-catalogue completion claim.

**Exact next work:** the recorded gas gaps (FortisBC Rate 5/Rate 4/Revelstoke propane;
Energir D3/D4/D5 and inventory adjustments; Eastward Rate Class 3 demand unit from the
approved tariff and Rate Class 4; Liberty Off-Peak; SaskEnergy small industrial; Centra
PUB conditions), then the electricity catalogue audits listed above. Targeted selectors:
`FortisBCEnergyLive`, `EnergirLive`, `HeritageGasLive`, `LibertyGasNBLive` and
`RegionalBatchStorage`. Keep ON/AB/YT/NT/NU excluded and shared integration serial.

## Current Checkpoint: Regional Batch 5 — Electricity classes and fees (2026-10-05)

Follows `a2a78a9`; the user asked to continue with classes and fees and skip industrial.

- **NB Power 9 live (was 3):** adds Residential Rural/Seasonal (Rate D, $33.82/billing period, $0.1584/kWh), residential and business water-heater rental (monthly), SureConnect (30 A $29.99/month), Recreational Lighting (first 5,000 kWh/billing period $0.1821, then $0.1304) and Public Fast Charging (load-factor bands; on-peak 7am-10pm / off-peak demand and energy; above 20% load factor uses General Service). All effective April 14, 2026 from the two official rate pages; energy totals equal base + variance. Existing Rate D, GS I and Small Industrial carry source URL/detail/date on every component. Skipped: Small/Large Industrial expansion, lighting, General Service II (merged into GS I April 1, 2025). One-time fees (service call/reconnection $76.44, new connection $117.16, seasonal reconnection $184.73, statement $25.28) are not modelled because the official table labels them "$/month". Fixture: `tests/fixtures/nb_power.json`.
- **Newfoundland Power 8 live (was 4):** adds Domestic Seasonal Optional 1.1S (winter Dec-Apr +$0.00953/kWh, non-winter May-Nov -$0.01297/kWh, adjustments to Rate 1.1 energy, 12-month term), prompt-payment discount (-1.5% within 10 days, Rates 1.1/2.1/2.3/2.4), conditional primary-voltage demand discount (-$0.40/kVA 4-25 kV, -$0.90/kVA 33-138 kV) and service fees (reconnection $20 office hours/$40 other, application $8, dishonoured payment $16) from the July 1, 2026 RateBook (pages 11-13, 24-28). Municipal tax and Rate Stabilization riders are already embedded in printed rates. Skipped: curtailable option (industrial/process), lighting, net metering (no prices). Fixture: `tests/fixtures/newfoundland_power.json`.
- **Maritime Electric 10 live (unchanged):** classes 110/130/131/133/232/233 confirmed complete against IRAC Section N-28 effective August 1, 2026; per-class fail-closed parsing; effective date must match header and URL; Rate 320 tier unit corrected to "kWh per kW billing demand"; industrial 310/320/330/340 retained as reference; lighting/short-term unmetered and one-time connection charges excluded; no recurring riders published. No further non-industrial building class is published. Fixture: `tests/fixtures/maritime_electric.json`.
- **SaskEnergy:** service fees researched but not added (the page publishes no effective date; using the observation date would invent one and create a new version every run); municipal surcharge not on static pages; no new non-industrial classes; small industrial skipped (industrial, closed to new customers).

**Verified:** 602 tests pass. The guarded store validated NB Power 9 / Newfoundland Power 8 / Maritime Electric 10 as live with complete component sources, appended 27 snapshots (1,328 total) and left prior snapshots and non-target tariffs unchanged. Database validation: 0 errors. Browser check: default 166 live; no JS errors; no overflow at 390px; 1.1S modal shows 0.00953.

**Current counts:** 648 versions / 4,160 components / 168 stored live / 480 seed; 166 latest live across 18 utilities; 164 latest live across the 16 target utilities.

**Exact next work:** BC Hydro business catalogue audit, Manitoba Hydro building audit, FortisBC Electric large commercial/optional schedules (non-industrial), HQ Inukjuak/net metering/business options, NSPower business/rider/pilot status, NL Hydro net metering; Centra PUB conditions; gas gaps (Energir D5 is industrial-type, inventory adjustments; FortisBC Revelstoke propane/Rates 6-7). Industrial classes are skipped per user. Keep ON/AB/YT/NT/NU excluded.

## Historical Checkpoint: Regional Batch 4 — Gas classes (2026-10-05)

**Delivered** (parallel per-utility workers, serial integration, after `6333ea8`):
FortisBC Energy 8 (adds Rate 5 General Firm Service: basic $469.00/month as the tariff
prints it, although the business page says daily, Rider 2 $0.40/month, demand $37.735 per
GJ/month of daily demand; and seasonal Rate 4, April 1-November 1: $14.4230/day basic,
off-peak $2.204 / extension $3.268 per GJ; effective July 1, 2026, BCUC G-131-26; printed
subtotals reconciled). Energir 4 (D3/D4 from article 14.3: subscribed-volume bands in
$/m³/day, conditional above-subscribed withdrawal and load balancing; D1 and D3/D4 fail
independently; live D3 supersedes the old estimate). Heritage/Eastward 3 (Rate Class 3:
$30.85 per GJ of Billing Demand/month, unit and rule from tariff PDF Schedule 3 page 10;
Rate Class 4 negotiated, not published). Liberty NB 4 (Off-Peak Service: $50.00/month,
$5.6244/GJ, April-November eligibility, $10/GJ December-March overrun as a note).

**Verified:** 551 tests pass (44 new). The guarded store validated all 19 records as live
with complete sources, appended 19 snapshots (1,301 total) and left all prior snapshots
and non-target tariffs unchanged. Database validation: 0 errors. Local browser preview
(batches 3 and 4): 156 live by default; FortisBC Energy 8 / Energir 4 / Heritage 3 /
Liberty 4; no JS errors; no page overflow at 390px; modals show exact values.
GitHub Pages deployment for `6333ea8` succeeded and its deployed `rates.json` contained
the 13 batch-3 live gas records; Deploy Site for `a2a78a9` succeeded and the deployed
`rates.json` had 638 records / 158 live.

**Current counts:** 638 versions / 4,123 components / 158 stored live / 156 latest live
across 18 utilities / 480 seed. Scope-only latest live count is 154 across all 16 target
utilities. This is not a full-building-catalogue completion claim.

**Exact next work:** SaskEnergy small industrial/fees and Centra PUB conditions; remaining
gas gaps (Revelstoke propane, FortisBC Rates 6/7 and Fort Nelson 4/5, Energir D5/inventory
adjustments/load-factor formula/rate reductions/fixed-price and renewable supply, Liberty
CGS/ICGS and marketer prices); then electricity building-catalogue audits (BC Hydro
business, Manitoba Hydro, NB Power, Maritime Electric, Newfoundland Power) and recorded
electricity gaps (FortisBC Electric large commercial 30-33/37/38 and optional schedules,
HQ Inukjuak/net metering/business, NSPower business/rider/pilot status, NL Hydro net
metering/industrial applicability). Keep ON/AB/YT/NT/NU excluded and shared integration
serial.
