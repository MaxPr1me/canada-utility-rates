# Phase 5 Completion Matrix

**Updated:** 2026-10-01. Scope: all 84 registered utilities, not every utility
in the broader Canadian inventory. The export has 560 stored tariff versions / 3,658
components / **80 stored live versions / 480 seed**. Latest-per-name coverage is
**79 live tariffs**; an older Yukon 1160 version remains in history. The export combines
October 1 CI observations with newer local SaskPower/Yukon results. No gas or Ontario
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

SaskPower and Yukon Energy have saved source-derived fixtures in `tests/fixtures/`.
Other tests include inline synthetic text and seed checks. A shared verifier test,
successful process exit, or empty missing-data log does not establish live coverage.

Official discovery/document links live in [the registry](../data/sources/registry.json).
Keep those links synchronized with URL constants the scrapers actually fetch.
See the [gap report](live_parser_gap_report.md) for detailed findings and
[README](../README.md) for the ordered roadmap.

## Provincial Electricity

| Utility | Live tariffs / source-check date | Implemented path and supported scope | Next work |
|---|---|---|---|
| BC Hydro | 4 / Oct 1 | HTML: tiered residential, SGS, MGS, LGS | Optional residential and other building-service schedules |
| FortisBC Electric | 0 / Oct 1 | Known-value verification for two seed classes | Current utility/BCUC building-service sources and extraction |
| Hydro-Quebec | 3 / Oct 1 | PDF: D/G/M | Remaining building-relevant products and source-derived fixtures |
| Manitoba Hydro | 8 / Oct 1 | HTML: residential and seven GS/voltage variants | Building-service audit; preserve kVA and seasonal rules |
| SaskPower | **41 / Oct 1** | **Audited building schedules implemented**; six source fixtures; total includes reference records | Monitor current sources; no remaining identified building-schedule parser gap in the audited catalogue |
| NB Power | 3 / Oct 1 | HTML: residential, GS1, small industrial | Remaining building-service schedules and fixtures |
| Nova Scotia Power | 4 / Oct 1 | HTML: Domestic and Rates 10/11/12 | Building-relevant products and source dates; industrial process-only rates deferred |
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

1. Broader Yukon building classes/Rider A via reviewed OCR or text alternatives, then NS building-service and FortisBC Electric; maintain implemented SaskPower coverage and corrected Yukon 1160.
2. Territorial/provincial depth and building-relevant class audits of existing live utilities.
3. Building-service tariffs at nine gas utilities, Alberta electricity, then the Ontario campaign.
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
