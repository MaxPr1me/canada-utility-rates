# Phase 5 Completion Matrix

**Updated:** 2026-10-02. Scope: all 84 registered utilities, not every utility
in the broader Canadian inventory. The export has 571 stored tariff versions / 3,732
components / **91 stored live versions / 480 seed**. Latest-per-name coverage is
**89 live tariffs**; older Yukon/NSPower versions remain in history. The export combines
October 1 observations with the October 2 NSPower/Hydro-Quebec updates. No gas or Ontario
tariffs are live in this export.
Counts include retained non-building reference records, not only building tariffs.

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

BC Hydro, Hydro-Quebec, NSPower, SaskPower and Yukon Energy have saved source-derived fixtures in `tests/fixtures/`.
Other tests include inline synthetic text and seed checks. A shared verifier test,
successful process exit, or empty missing-data log does not establish live coverage.

Official discovery/document links live in [the registry](../data/sources/registry.json).
Keep those links synchronized with URL constants the scrapers actually fetch.
See the [gap report](live_parser_gap_report.md) for detailed findings and
[README](../README.md) for the ordered roadmap.

## Provincial Electricity

| Utility | Live tariffs / source-check date | Implemented path and supported scope | Next work |
|---|---|---|---|
| BC Hydro | 8 / Oct 1 | Approved PDF: tiered 1101, flat 1151, each +2101 TOD, closed dual-fuel 1105; three HTML business classes | Five residential options verified; preserve rider exclusions, prorated tiers and conditional discounts; other building-service audit remains |
| FortisBC Electric | 0 / Oct 1 | Known-value verification for two seed classes | Oct 2 official residential page reachable through direct HTTP and links to Electric Tariff; actual residential extraction/catalogue completeness still pending |
| Hydro-Quebec | 6 / Oct 2 | PDF: D/DP/DM/DN/G/M; page-aware domestic fixtures, seasons, off-grid eligibility, multipliers and conditional credits | DT, Flex D, Winter Credit, Inukjuak domestic variant and net-metering remain; begin with DT pages 21-24 |
| Manitoba Hydro | 8 / Oct 1 | HTML: residential and seven GS/voltage variants | Building-service audit; preserve kVA and seasonal rules |
| SaskPower | **41 / Oct 1** | **Audited building schedules implemented**; six source fixtures; total includes reference records | Monitor current sources; no remaining identified building-schedule parser gap in the audited catalogue |
| NB Power | 3 / Oct 1 | HTML: residential, GS1, small industrial | Remaining building-service schedules and fixtures |
| Nova Scotia Power | 7 latest / Oct 2 | PDF standard/TOD and explicitly conditional interim TOU/CPP pilots, separate riders; existing business 10/11/12 HTML | Participant restoration-status verification, MURB TOU and solar riders remain gaps; 2027 rates unsupported pending new source review |
| Maritime Electric | 10 / Oct 1 | IRAC PDF class-section extraction | Building-service audit and source-derived success/failure fixtures |
| Newfoundland Power | 4 / Oct 1 | RateBook PDF: 1.1/2.1/2.3/2.4 | Building-relevant schedules and fixture coverage |
| NL Hydro | 0 / Oct 1 | PDF verification of rural/Labrador/GS seeds | Building class/zone extraction, preserving interconnected/isolated distinctions |

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

All nine utilities have **0 live tariffs in the integrated October 1 export** and known-value
verification paths, not completed dynamic extraction. None has a saved source-derived
utility fixture. Discovery and component interpretation must precede parser completion.

| Registry utility | Required source/interpretation work |
|---|---|
| Enbridge Gas | Legacy rate zones, building-service classes, commodity/delivery/transport/storage and dated riders |
| Énergir | Current distribution/volume classes, supply/balancing, units and effective dates |
| FortisBC Energy | Service areas, building customer classes and separately published adjustments |
| ATCO Gas | Current approved delivery schedules, classes and applicable riders |
| EPCOR Natural Gas | Confirm product, jurisdiction and utility identity; do not infer these from the module name |
| Centra Gas Manitoba | Current Manitoba Hydro gas tables and individual component periods |
| SaskEnergy | Current class/volume tables, delivery/commodity and applicable adjustments |
| Heritage Gas / Eastward Energy | Current company source and residential/business schedules |
| Liberty Utilities NB / Natural Gas NB | Current company source and complete customer-class schedules |

Preserve m3/GJ, volume tiers and component source ownership. Verify current tax/carbon
applicability rather than copying obsolete charges. Incomplete commodity/delivery
coverage must not be hidden under a live tariff label; do not invent unit conversions.

## Northern Electricity

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
Next gate: reviewed OCR or authoritative text for full building-class extraction.

## Next Batches and Acceptance

1. Continue the residential audit after Hydro-Quebec DP/DM/DN: DT dual-energy is the next bounded slice, followed by Flex D/Winter Credit and FortisBC's current tariff. BC Hydro's five options and NSPower standard/TOD/conditional pilot phases are implemented; do not infer national product completeness.
2. Resume broader Yukon building classes/Rider A via reviewed OCR or text alternatives and other NS/FortisBC building-service gaps after the residential-priority audit.
3. Territorial/provincial building-service depth, nine gas utilities, Alberta electricity, then the Ontario campaign.
4. Separate operational track: browser-enabled source health, meaningful provenance counts,
   failure reporting, deployment triggering and durable CI history.
5. Deferred product track: market-model UI/metadata correction, real observation ingestion,
   historical charts and AI export. Calculator/API requirements are separate.
6. Conditional Alberta extension: if its market-pricing variation or complexity warrants
    a dedicated view, add Alberta as a region in the existing Market Pricing dashboard.
    Use Alberta-specific values, sources, dates and methodology; reuse the interface,
    not Ontario's HOEP-plus-GA assumptions. Keep wholesale, retail and wires distinct,
    with any modeled estimates clearly identified. This remains deferred work.

Each batch requires source-derived positive/negative tests, a source-inspected dry run,
validated storage/export, preserved history and a ledger update. Record observation dates
separately from parser capability, keep unsupported classes visible, and never delete a
database or invent rates to make completion metrics look better.

## Historical Checkpoint: BC Hydro (2026-10-01)

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
batch has since progressed; use the October 2 checkpoint below for current status.

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

This is a dated product-catalogue audit, not a fresh live-rate run for every utility.
The rest of the registry still needs review; no absence of optional products is inferred
from an old seed or a single residential page.

| Utility/group | Official evidence reviewed | Finding and remaining gate |
|---|---|---|
| BC Hydro | October 1 approved tariff and residential pages | Five options implemented: tiered/flat, both +TOD, closed dual-fuel. Preserve conditions/rider exclusions |
| NSPower | October 2 [residential catalogue](https://www.nspower.ca/your-home/residential-rates/standard-residential) and [May 2026 tariff book](https://www.nspower.ca/docs/default-source/regulatory/tariff-book-2026.pdf) | Standard, thermal-storage TOD, TOU and CPP pilots implemented by dated tariff phase. Both pilots are closed to new applicants; October variants explicitly conditional. MURB TOU and solar riders still need extraction |
| Hydro-Quebec | October 2 [domestic-rate catalogue](https://www.hydroquebec.com/residential/customer-space/rates/) and approved tariff | D/DP/DM/DN are implemented, with seasonal demand, grandfathered multipliers and DN's distinct off-grid/default-multiplier rules. DT, Flex D, Winter Credit, Inukjuak domestic variant and net-metering remain; catalogue links alone do not establish eligibility or current rates |
| FortisBC Electric | October 2 [residential page](https://www.fortisbc.com/accounts-billing/billing-rates/electricity-rates/residential-rates) through direct HTTP | Page links to the [official Electric Tariff](https://fbcdotcomprod.blob.core.windows.net/libraries/docs/default-source/about-us-documents/regulatory-affairs-documents/electric-utility/fortisbcelectrictariff.pdf). Current January 1, 2026 decision is mentioned; tariff extraction and full product audit are pending. Web-tool CSP failure is not proof of an inaccessible source |
| Ontario shared prices | October 2 [OEB price catalogue](https://www.oeb.ca/consumer-information-and-protection/electricity-rates) | TOU, ULO and Tiered choices confirmed; displayed current prices effective November 1, 2025. RPP prices already include an estimate of GA. This does not verify any LDC's delivery charges or merger identity |
| Manitoba, NB, PEI, Newfoundland, Labrador and remaining electricity entries | Existing matrix/source history only in this pass | Optional/conditional residential product catalogue audit remains pending; do not mark default-only outputs complete |
| Northern and Alberta families | Existing matrix/source history only in this pass | Preserve community, government/subsidy and wires/retail distinctions; current product audit remains pending |
| Nine gas utilities | No new catalogue source check in this pass | Residential class/zone and supply-contract options still need audit; all remain seed-only in the current export |

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

## Current Checkpoint: Hydro-Quebec DN (2026-10-02)

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
