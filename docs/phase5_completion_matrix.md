# Phase 5 Completion Matrix

**Updated:** 2026-10-06. Scope: all 84 registered utilities, not every utility
in the broader Canadian inventory. The batch 9 export has 694 stored tariff versions / 4,453
components / **214 stored live versions / 480 seed**. Latest-per-name coverage is
**209 live tariffs across 18 utilities**; older versions remain in history. All 16 campaign utilities
have live output; Ontario and the five excluded-region gas utilities have none.
Counts include retained non-building reference records, not only building tariffs.

## Active Regional Campaign (2026-10-06)

Nine implementation batches cover the 16 registered utilities in BC, QC, MB, SK,
NB, NS, PE and NL: ten electricity and six gas utilities. Ontario, Alberta and
all three territories are excluded from this run, not removed from the database
or website. Provincial off-grid service in Quebec and Newfoundland and Labrador
remains in scope. No additional inventory utilities are being registered.

**Current checkpoint:** Batch 9 implemented, stored and exported (October 6).
There are **207 latest live records at all 16 target utilities** and **801 passing tests
across 8 modules**. DB validation reported 0 errors and 2 existing AESO warnings. No
target utility is seed-only, and none is catalogue-complete except SaskPower's audited
building scope. Local history contains 1,570 snapshots; batch 9 appended 106 without
changing prior snapshots. Excluded-region records remain retained.

A successful scrape or one live residential class does not establish complete
building coverage; counts include optional adjustments and reference records.

| Priority | Utility queue | Next work |
|---|---|---|
| Wave 2 gas | FortisBC Energy; SaskEnergy; Centra Gas | Rate 7 (Rate 6 NGV excluded), small industrial, and remaining Centra classes; Fort Nelson 4/5 have no published table; supplier-specific commodity prices remain unpriced |
| Wave 2 electricity | Nova Scotia Power; Maritime Electric | Industrial classes and the 310-340 building-industrial audit, respectively; maintain SaskPower's audited building scope |
| Other open work | BC Hydro; Hydro-Quebec; NL Hydro; Manitoba Hydro | Transmission pilots, DR Commitment option, IND non-firm/wheeling, and standard service charges/LUBD; see utility rows for source blockers |
| Needs decision | BC Hydro RS1828; FortisBC Electric RS38; Hydro-Quebec Rate F/FP | Biomass-program contract, Mid-C indexed service, and F/FP applicability require scope decisions before expanding coverage |

Utility parser and fixture work may proceed in parallel. Shared tests, registry,
database writes, exports, documentation and publication are integrated serially.
Each batch requires source-derived rejection tests, a current official-source
check and preservation comparisons before storage/publication. Source-blocked or
unaudited classes remain incomplete. Continue across verified milestones; reserve
time for a tested, pushed checkpoint and exact handoff before context exhaustion.

**Active building scope (October 6):** single-family and multi-unit residential,
commercial, institutional and building-related industrial classes, including general
facility service defined by size, voltage or interruptibility. NECB 2025 is a use-case
reference, not a utility eligibility rule or a compliance claim. Process-specific farm,
oil-field and irrigation service, NGV fuelling, EV charging, lighting, wholesale/reseller
and standby-only service are excluded. Keep completed reference code and data.

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
| BC Hydro | 11 / Oct 6 | Prior residential/business coverage plus RS1830 Transmission Service (Apr 1, 2026, PDF pp138-140, 232-233: $12.178/kVA/billing period, $0.04914/kWh, separate RS1901/1904 riders) and closed RS1289 net-metering conditional generation credit (Jul 1, 2026, pp223-231; indexed cash settlement unpriced) | Transmission pilots RS2801/2802/2821/2822, RS1892 and RS2289/2290 open; RS1828 biomass-program contract needs scope decision; RS1823 cancelled. Irrigation, lighting, EV and wholesale/reseller excluded |
| FortisBC Electric | 11 / Oct 6 | Prior 1/2A/20/21/22A/23A/30/32/85 plus RS31 transmission (R-31.1 p65: $4,077.97/month, $6.29/kVA wires, $4.39/kVA power supply, $0.06851/kWh) and RS33 transmission TOU (R-33.1 p67: $3,785.34/month, six seasonal TOU prices); Jan 1, 2026 | RS38 Mid-C indexed with $0.01/kWh hourly adder needs decision; RS95 source-blocked (BC Hydro RS3808 Tranche 1 price in effect, not printed here). RS37 standby-only and RS96 EV excluded |
| Hydro-Quebec | 25 / Oct 6 | Prior domestic/general-service options plus Rate L (pp63-66: $15.027/kW/month, $0.03821/kWh, conditional winter overrun), LG (pp67-69: $16.571/kW/month, $0.04324/kWh, conditional unused power), H (p71: $6.630/kW/month, $0.06695/$0.2262 winter-weekday $/kWh), and business Demand Response Leeway (pp94-98: alternative winter credits, weekend event credits); Apr 1, 2026. Voltage credits conditional; ratchets/power factor retained as conditions | DR Commitment option open; F/FP need scope decision; MA absent from edition. GD backup, BR EV and LD/LP auxiliary/standby excluded |
| Manitoba Hydro | 12 / Oct 6 | HTML residential and GS small/medium/large/seasonal, diesel and government/education; large GS voltage tiers cover building-related industrial. Failed residential/commercial page no longer discards other page's live classes | Curtailable/LUBD/surplus lack complete published prices; net-billing export credit $0.07173/kWh has no published start date (not live); standard service charges and LUBD schedule unaudited; lighting excluded |
| SaskPower | **41 / Oct 1** | **Audited building schedules implemented**; six source fixtures; total includes reference records | Monitor current sources; no remaining identified building-schedule parser gap in the audited catalogue |
| NB Power | 10 / Oct 6 | Prior HTML classes plus hardened Small Industrial (both energy tiers, 100 kWh/kW threshold and required $/kW demand) and Large Industrial ($19.98/kW/month, $0.0785/kWh; billing-demand alternatives as conditions), Apr 14, 2026 | Net metering and interruptible/surplus prices source-blocked; GS II merged into GS I. Lighting and charging retained as reference |
| Nova Scotia Power | 14 / Oct 5 | Standard/TOD/conditional pilots, MURB89, two optional solar adjustments; business 10/11/12 rebuilt from book pages 16-17/25-26/38-39 with FAM/DSM/storm riders and conditional transformer discounts; business pilots 72/73/82/83 as conditional records (October interim, November 1 date-gated) | Wave 2 industrial classes; pilot restoration status is not assumed; municipal wholesale excluded; unsupported 2027 dates fail closed |
| Maritime Electric | 10 / Oct 5 | IRAC PDF class-section extraction; scoped building classes audited against N-28 with per-class fail-closed fixtures | Audit remaining building-related industrial service under October 6 scope |
| Newfoundland Power | 11 / Oct 6 | Prior RateBook classes plus Curtailable Service Option 1 for 2.3/2.4 (conditional -$29/kVA May credit, pp30-31) and Domestic 1.1 net metering (conditional -$0.15587/kWh generation credit, pp24, 32-34) | Option 2 load-factor formula, GS/seasonal net-metering credits unmodelled; annual settlement unpriced |
| NL Hydro | 21 / Oct 6 | Prior July Island/Labrador/diesel classes plus Island Industrial Firm (pp9-10, $/kW/month, $/kWh, riders and conditional named-customer charges), Labrador Industrial Firm (pp62-65, conditional 2026 $/MWh blocks, no blended price), and Net Metering Service Option (pp67-70, conditional credit at applicable class energy rate, not standalone price) | 5.1L source-blocked by monthly futures pricing; IND non-firm/wheeling unaudited. CP transmission commissioning and UT wholesale excluded |

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

All 53 distributor entries share `OntarioLDCScraper`; their live-parser status is
blocked, and each seed is exported only as unverified fallback. The OEB common-price
source is shared, not per-LDC; it cannot verify distributor-specific charges.

Distributors: Alectra Utilities, Algoma Power Inc., Atikokan Hydro Inc., Bluewater
Power Distribution, Brantford Power Inc., Burlington Hydro Inc., Canadian Niagara
Power Inc., Centre Wellington Hydro Ltd., Chapleau Public Utilities Corp., Elexicon
Energy Inc., Entegrus Powerlines Inc., Enwin Utilities Ltd., Erie Thames Powerlines
Corp., Espanola Regional Hydro, Essex Powerlines Corp., Festival Hydro Inc., Fort
Frances Power Corp., Greater Sudbury Hydro Inc., Grimsby Power Inc., Guelph Hydro
Electric Systems Inc., Halton Hills Hydro Inc., Hearst Power Distribution Co. Ltd.,
Hydro 2000 Inc., Hydro Hawkesbury Inc., Hydro One Networks Inc., Hydro Ottawa Ltd.,
Innpower Corporation, Kingston Hydro Corporation, Kitchener-Wilmot Hydro Inc.,
Lakefront Utilities Inc., Lakeland Power Distribution Ltd., London Hydro Inc.,
Midland Power Utility Corp., Milton Hydro Distribution Inc., Newmarket-Tay Power
Distribution Ltd., Niagara Peninsula Energy Inc., North Bay Hydro Distribution Ltd.,
Northern Ontario Wires Inc., Oakville Hydro Electricity Distribution Inc., Orangeville
Hydro Limited, Oshawa PUC Networks Inc., Ottawa River Power Corporation, PUC
Distribution Inc., Rideau St. Lawrence Distribution Inc., Sioux Lookout Hydro Inc.,
St. Thomas Energy Inc., Synergy North Corporation, Tillsonburg Hydro Inc., Toronto
Hydro-Electric System Ltd., Wasaga Distribution Inc., Waterloo North Hydro Inc.,
Welland Hydro-Electric System Corp., Westario Power Inc.

Extra utility-site URLs in the archived table: Alectra, Burlington, Hydro One,
Hydro Ottawa, Kitchener-Wilmot, London and Toronto.
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

SaskEnergy has six live records and Centra Gas twelve; the October 6 export includes
FortisBC Energy eleven, Energir five, Heritage/Eastward three and Liberty NB four, all with
source-derived fixtures. The five excluded-region gas utilities remain seed-only. No gas
utility is yet certified complete for its published building catalogue.

| Registry utility | Region / campaign | Latest live records | Implemented path and remaining work |
|---|---|---|---|
| Enbridge Gas | ON / excluded | 0 | Seed verification; legacy rate zones and full component extraction remain deferred |
| Énergir | QC / live, partial catalogue | 5 / Oct 6 | D1/D3/D4 plus interruptible D5 (Oct 1 CST p62 distribution bands $/m3, pp63-65 interruption/minimum volume; Category A/B load-balancing alternatives p49 conditional and non-additive). Optional RNG supply $0.85239/m3 (p38) replaces ordinary supply on D1/D3/D4/D5; missing RNG does not suppress base records. Inventory adjustments customer-specific and unpriced. Load-factor formula p49 published but not computed; fixed-price supply supplier-specific and D5 make-up gas pass-through unpriced |
| FortisBC Energy | BC / live, partial catalogue | 11 / Oct 5 | Rates 1/2/3 for Mainland/Vancouver Island and Fort Nelson (July 1, 2026; $/day basic, $/GJ components) with the BC carbon-tax elimination notice required; Rate 5 General Firm Service (basic $469.00 per month as the tariff prints it) and seasonal Rate 4 (Apr 1-Nov 1) for Mainland/Vancouver Island from the approved schedules. Residential Rate 1 and Commercial Rates 2/3 Revelstoke propane (business classes require the approved tariff index's Revelstoke availability plus residential propane evidence; each class fails independently). Rate 7 building service remains for Wave 2; Rate 6 NGV excluded. Fort Nelson 4/5 have no published price table; marketer prices remain unavailable |
| ATCO Gas | AB / excluded | 0 | Seed verification; current approved delivery classes/riders remain deferred |
| EPCOR Natural Gas | AB registry entry / excluded | 0 | Seed verification; product, jurisdiction and identity still need confirmation |
| Centra Gas Manitoba | MB / live, partial catalogue | 12 / Oct 5 | Residential/commercial Sales/T-service/marketer variants; approved PUB schedule (Nov 1, 2025, Order 138/25) required for volume boundaries, contracts, Mainline pressure, winter demand, T-service nomination and interruptible alternate-supply conditions. Wave 2: remaining building classes; fixed-term commodity prices unpriced |
| SaskEnergy | SK / live, partial catalogue | 6 / Oct 2 | Residential/small/large-commercial full/delivery-only variants; Wave 2 small industrial applicability; fees lack published start date and municipal-payment scope remains under audit |
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

1. Wave 2: NSPower industrial classes, FortisBC Energy Rate 7 (Rate 6 NGV excluded), SaskEnergy small industrial, Centra remaining classes and Maritime Electric 310-340 building-industrial audit.
2. Address BC Hydro transmission pilots, Hydro-Quebec DR Commitment, NL Hydro IND non-firm/wheeling and Manitoba standard service charges/LUBD; source-blocked and unpublished prices remain open. Decide BC Hydro RS1828, FortisBC RS38 and Hydro-Quebec F/FP before adding them.
3. Audit remaining building catalogues and fixtures, maintain SaskPower's audited building schedules, then run a sixteen-utility refresh and class-level reconciliation. ON/AB/YT/NT/NU remain excluded from this campaign.
4. Separate operational track: Chromium installation in source health, test/scrape failure issues, successful Monthly Scrape `workflow_run` deployment from `main`, and release-asset `data-history` database restore/upload after validation/export are implemented, pending first CI run verification. Pages source must be GitHub Actions; `workflow_run` fires from the default branch. Meaningful provenance counts remain open.
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

## History

Detailed checkpoints are kept in the maintainer's local tracker; earlier published
checkpoints are in git history (commits `0e43ca6` through `08531d2`). Batch 9 was
stored and exported October 6. Use the current queue above for next work.
