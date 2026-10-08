# Phase 5 Completion Matrix

**Updated:** 2026-10-08 (Ontario batch 2). Scope: all 86 registered utilities (8 Ontario entries
now `merged`), not every utility in the broader Canadian inventory. The export has 1,321 stored
tariff versions / 13,343 components / **841 stored live versions / 480 seed**. Latest-per-name
coverage is **836 live tariffs across 67 utilities** (483 at 46 Ontario distributors); older
versions remain in history. History: 3,013 snapshots (Ontario batch 2 appended 527, prior
snapshots unchanged). All 20 campaign utilities have live output; Alberta (except FortisAlberta
Rate 11), PUC Distribution and the five Ontario/Alberta gas utilities have none.
Counts include retained non-building reference records, not only building tariffs.

## Active Regional Campaign (2026-10-07)

Ten implementation batches cover the 16 registered utilities in BC, QC, MB, SK,
NB, NS, PE and NL (ten electricity and six gas) and, from October 7, the four territorial
utilities (Yukon Energy, ATCO Electric Yukon, NTPC, Qulliq), whose service is non-market
regulated. Ontario and Alberta are excluded from this run, not removed from the database
or website. No additional inventory utilities are being registered.

**Current checkpoint:** Batch 11 close-out refresh implemented, stored and exported (October 7).
There are **243 latest live records at the 16 provincial targets**, **109 at the four
territorial utilities** and **1,052 passing tests across 8 modules**. DB validation reported
0 errors and 2 existing AESO warnings. No target utility is seed-only. The reconciliation table
below classifies every recorded class; no priced, dated in-scope gap remains. Local history
contains 2,142 snapshots; the batch 11 refresh appended 352 without changing prior snapshots.
Excluded-region records remain retained.

A successful scrape or one live residential class does not establish complete
building coverage; counts include optional adjustments and reference records.

| Priority | Utility queue | Next work |
|---|---|---|
| Maintain | Centra Gas Mainline Interruptible | Hash-gated reviewed transcription (batch 11); re-transcribe when Appendix A changes |
| Monitor | Qulliq final GRA instruction; NTPC Snare TPSP saving mismatch | Interim rates stay medium confidence (URRC recommended approval); Snare TPSP omitted until source reconciles |
| Source-blocked | See the reconciliation table below | Published without printed, dated prices; re-check periodically |
| Deferred to market-rate work | FortisBC Electric RS38; BC Hydro RS1892; NSPower one-part real-time pricing; NL Hydro monthly non-firm (5.1L, Island non-thermal) | Market-indexed energy prices handled with the Alberta/Ontario market work |

**Decisions (October 7):** BC Hydro RS1828 (biomass-program contract), Hydro-Quebec
Rate F/FP (unmetered) and FortisBC Energy 11RNG are excluded. Territories are reopened for
non-market regulated service. Centra Mainline Interruptible may use a reviewed, hash-gated
transcription; NTPC Taltson retail interruptible heating is implemented as conditional.

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
Centra Gas, FortisBC Energy, Energir, Heritage/Eastward, Liberty NB, Manitoba Hydro, Maritime
Electric, Yukon Energy, NTPC and Qulliq have saved source-derived fixtures in `tests/fixtures/`.
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
| BC Hydro | 17 / Oct 7 | Prior residential/business coverage, RS1830 Transmission Service and closed RS1289 credit, plus batch 10 transmission pilots 2801/2802/2821/2822 (pp187-216, conditional-enrollment alternatives to RS1830 through Mar 31, 2030, separate RS1901/1904 riders, conditional critical-peak prices) and RS2289/2290 conditional -$0.10/kWh generation credits (Jul 1, 2026, pp234-248) | RS1892 freshet energy (Mid-C index) deferred to market-rate work; RS1828 excluded (biomass contract); RS1823 cancelled. Irrigation, lighting, EV and wholesale/reseller excluded |
| FortisBC Electric | 11 / Oct 6 | Prior 1/2A/20/21/22A/23A/30/32/85 plus RS31 transmission (R-31.1 p65: $4,077.97/month, $6.29/kVA wires, $4.39/kVA power supply, $0.06851/kWh) and RS33 transmission TOU (R-33.1 p67: $3,785.34/month, six seasonal TOU prices); Jan 1, 2026 | RS38 Mid-C indexed deferred to market-rate work; RS95 source-blocked (BC Hydro RS3808 Tranche 1 price in effect, not printed here). RS37 standby-only and RS96 EV excluded |
| Hydro-Quebec | 26 / Oct 7 | Prior domestic/general-service options, L/LG/H and DR Leeway, plus batch 10 business Demand Response Commitment Option (articles 6.13-6.36, pp83-93: 20 mutually exclusive sub-options, winter fixed and event-hour credits, multi-year/short-notice credits, capped overrun deductions; conditional adjustments to G/M/L/LG); Apr 1, 2026 | F/FP excluded (unmetered); MA absent from edition; Load Retention, Additional Electricity (monthly announced price), closed Economic Development and Industrial Revitalization are not general published prices. GD backup, BR EV and LD/LP auxiliary/standby excluded |
| Manitoba Hydro | 18 / Oct 7 | HTML residential and GS small/medium/large/seasonal, diesel and government/education, plus batch 10 LUBD 2026-50..55 from the approved Jan 1, 2026 schedule (PUB Order 1/26, pp14-16) as conditional alternatives replacing standard GS charges; schedule and page failures are isolated | Curtailable/surplus lack complete published prices; net-billing export credit $0.07173/kWh has no published start date (not live); standard service charges absent from the approved schedule ($150 reconnection fee undated); lighting excluded |
| SaskPower | **41 / Oct 1** | **Audited building schedules implemented**; six source fixtures; total includes reference records | Monitor current sources; no remaining identified building-schedule parser gap in the audited catalogue |
| NB Power | 10 / Oct 6 | Prior HTML classes plus hardened Small Industrial (both energy tiers, 100 kWh/kW threshold and required $/kW demand) and Large Industrial ($19.98/kW/month, $0.0785/kWh; billing-demand alternatives as conditions), Apr 14, 2026 | Net metering and interruptible/surplus prices source-blocked; GS II merged into GS I. Lighting and charging retained as reference |
| Nova Scotia Power | 18 / Oct 7 | Standard/TOD/conditional pilots, MURB89, two optional solar adjustments; business 10/11/12 and conditional pilots 72/73/82/83; batch 10 Industrial 21/22/23 and Interruptible Rider 25 (book pp40-49, own FAM/DSM/storm rows; conditional distribution cost adder, transformer reduction and -$7.638/kVA interruptible credit) | Pilot restoration status is not assumed; ELIADC and Load Retention contract-specific; one-part RTP deferred to market-rate work; municipal wholesale, shore power and standby excluded; unsupported 2027 dates fail closed |
| Maritime Electric | 10 / Oct 7 | IRAC N-28 PDF plus Section N rates page (dates must match); building classes and Small/Large Industrial 320/310 audited complete (billing-demand rules as conditions; 310 losses/transformation charges conditional) | 330/340 are Summerside wholesale, retained as reference; no curtailable credit published; lighting/unmetered/short-term excluded |
| Newfoundland Power | 11 / Oct 6 | Prior RateBook classes plus Curtailable Service Option 1 for 2.3/2.4 (conditional -$29/kVA May credit, pp30-31) and Domestic 1.1 net metering (conditional -$0.15587/kWh generation credit, pp24, 32-34) | Option 2 load-factor formula, GS/seasonal net-metering credits unmodelled; annual settlement unpriced |
| NL Hydro | 21 / Oct 6 | Prior July Island/Labrador/diesel classes plus Island Industrial Firm (pp9-10, $/kW/month, $/kWh, riders and conditional named-customer charges), Labrador Industrial Firm (pp62-65, conditional 2026 $/MWh blocks, no blended price), and Net Metering Service Option (pp67-70, conditional credit at applicable class energy rate, not standalone price) | 5.1L source-blocked by monthly futures pricing; Island Industrial Non-Firm (pp11-12) source-blocked (futures/fuel formula, no printed price); Wheeling (p13) excluded as transmission service. CP transmission commissioning and UT wholesale excluded |

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

### Ontario batch 1 (October 7, 2026): Hydro One and the larger distributors

There are now 55 registry entries using one `OntarioLDCScraper`: 53 originals plus the
successors **Enova Power Corp.** (Kitchener-Wilmot Hydro + Waterloo North zones) and
**GrandBridge Energy Inc.** (Brantford Power + Energy+ zones). Eight absorbed entries carry
`status: "merged"` and a `merged_into` successor: Kitchener-Wilmot and Waterloo North
(Enova), Brantford (GrandBridge), Guelph (Alectra), St. Thomas (Entegrus), Midland
(Newmarket-Tay), Espanola (North Bay) and Chapleau (Hydro One). Merged entries are left out of
full monthly runs; their stored history and seeds are retained.

**Value source:** each distributor's OEB-approved Tariff of Rates and Charges PDF
(`OEB_TARIFF_DOCUMENTS` in `ontario_ldc.py`, parsed by `scrapers/utils/oeb_tariff.py`). Case
numbers and effective dates must match. The OEB BillData XML is used only for name/zone
mapping and cross-checks, never as a value source (stale zones, merged seasonal charges,
aggregate riders). RPP commodity prices come from the live OEB RPP page (effective
November 1, 2025). Residential and GS<50 records keep TOU/Tiered/ULO names, with live RPP
energy plus tariff delivery charges. Demand classes (GS 50-4,999 kW and Large Use) are
delivery-only; commodity/GA wait for the market-rate work.

**Scope:** Residential, GS<50, GS 50-4,999 kW and Large Use. Street lighting, unmetered
scattered load, embedded distributor, microFIT and standby are excluded. Street lighting
stays a labelled seed. One record set is produced per rate zone; the default zone keeps the legacy
tariff codes and the other zones add "[zone]" to the name. Default zones: Hydro One R1/GSe,
Alectra PowerStream, Elexicon Veridian, ERTH Main, Newmarket-Tay main, North Bay main.
Hydro One ST is included only for the >500 kW load path, with its alternatives conditional.
Open GS classes with a floor at or below 1,000 kW map to commercial, otherwise to large use.

| Distributor | Live / seed | Notes |
|---|---|---|
| Hydro One Networks | 50 / 1 | UR/R1/R2 and seasonal; AUR/AR; UGe/GSe; UGd/GSd/AUGd/AGSd; ST (>500 kW path); Peterborough and Orillia service areas |
| Alectra Utilities | 44 / 1 | All rate zones (default PowerStream) |
| Elexicon Energy | 19 / 1 | Whitby and Veridian zones |
| Erie Thames (ERTH) | 18 / 1 | Main and Goderich zones |
| Enova Power / GrandBridge Energy | 16 / 0 each | Successor zones; no seed |
| North Bay Hydro | 15 / 1 | North Bay and Espanola zones |
| Newmarket-Tay | 14 / 1 | Revised Newmarket-Tay sheet plus Midland zone (Midland GS 50-4,999 re-read at y_tolerance 1, batch 2) |
| Toronto Hydro | 12 / 1 | |
| Hydro Ottawa | 9 / 1 | Implemented June 1, 2026 |
| Milton, Bluewater, Oshawa | 9 / 1 each | |
| Halton Hills, Synergy North, Enwin, London, Entegrus | 8 / 1 each | Enwin Dedicated Transformer Station excluded; London co-generation class excluded |
| Niagara Peninsula, Essex, Greater Sudbury | 7 / 1 each | |
| Kingston Hydro | 8 / 1 | GS 50-4,999 live from batch 2 (re-read at y_tolerance 6) |
| Burlington Hydro | 7 / 1 | Proposed/draft tariff copy in the PDF is ignored |
| Oakville Hydro | 5 / 1 | GS<50 rejected (LRAM rider in $/kW); no estimate re-emitted since batch 2 |

Total after batch 1: 319 live records across 24 distributors (scrape run 25). The table shows
counts after the batch 2 re-store (scrape run 26).

### Ontario batch 2 (October 8, 2026): remaining distributors

| Distributor | Live / seed | Notes |
|---|---|---|
| Algoma Power | 10 / 1 | R1 split into (i) year-round dwellings (fully fixed, legacy codes) and (ii) O. Reg. 445/07; Seasonal; R2 (>=50 kW, per kW) delivery-only; no GS class, so no GS estimates |
| Tillsonburg Hydro | 9 / 1 | GS 50-499, 500-1,499 and >=1,500 kW |
| Festival Hydro | 8 / 1 | Includes Large Use |
| Lakefront Utilities | 8 / 1 | GS 50-2,999 and 3,000-4,999 kW |
| Hearst Power | 8 / 1 | GS 50-1,499 kW and Intermediate User (1,500-4,999 kW) |
| Grimsby Power | 7 / 1 | Re-read at y_tolerance 4 |
| Northern Ontario Wires | 7 / 1 | Case number only on the Schedule A cover |
| Atikokan Hydro | 7 / 1 | Single Transformation Connection rate is the standard rate |
| Lakeland Power | 7 / 1 | Final rate order effective September 1, 2026 |
| Canadian Niagara, Welland, Centre Wellington, Westario, Orangeville, Wasaga, InnPower, Hydro 2000, Hydro Hawkesbury, Ottawa River, Rideau St. Lawrence, Fort Frances, Sioux Lookout | 7 / 1 each | |

Total: **483 live records across 46 distributors** (scrape run 26, October 8, 2026). A configured
distributor with a rejected class, or whose tariff has no such class, emits no estimate for it; a
failed download or whole-sheet rejection still emits labelled estimates. Street lighting stays a
labelled estimate. **PUC Distribution** stays unconfigured (its tariff prints only a network
transmission rate, no connection rate; user decision October 8).

A scratch representative model (median of each distributor's default-zone record) shows typical
monthly delivery varies about 15-20% (CV ~0.18) for Residential, GS<50 and GS 50-4,999 kW, with
Hydro One the main high outlier. It is not published; any site artifact would be labelled
modeled and hidden by default.

Rejected classes get no new estimate (decision October 7: follow live sources); older estimates
stored earlier remain in history, labelled as estimates and hidden by default. Every failure is
per class (fail-closed).

**Confirmed decisions (October 7):** the open-GS rule above. Hydro One Seasonal: the R2 page
prints a Seasonal service charge ($92.43) beside the year-round charge ($151.14); Seasonal
records use it with R2's shared lines and no RRRP credit, while year-round R2 records show the
RRRP credit (-$60.50) as conditional. Seasonal properties in UR/R1 areas use the UR/R1 records.
The R2 Distribution Rate Protection cap is not modelled.

**Remaining Ontario:** PUC Distribution (unconfigured, see above).

Original registry distributors: Alectra Utilities, Algoma Power Inc., Atikokan Hydro Inc., Bluewater
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

Legacy `toronto_hydro.py` is unregistered; do not duplicate Toronto's current registry
entry. No interim mixed-live tariff label should bypass missing delivery data.

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
| FortisBC Energy | BC / live, partial catalogue | 27 / Oct 7 | Rates 1/2/3 for Mainland/Vancouver Island and Fort Nelson (July 1, 2026; $/day basic, $/GJ components) with the BC carbon-tax elimination notice required; Rate 5 General Firm Service (basic $469.00 per month as the tariff prints it) and seasonal Rate 4 (Apr 1-Nov 1) for Mainland/Vancouver Island from the approved schedules. Residential Rate 1 and Commercial Rates 2/3 Revelstoke propane (business classes require the approved tariff index's Revelstoke availability plus residential propane evidence; each class fails independently). Batch 10: Rate 7 General Interruptible ($880/month as printed; curtailment-limited delivery; Sumas-indexed overrun as a condition) and delivery-only transportation 22/23/25/27 (marketer commodity excluded; Rate 22 firm/interruptible charges conditional). Rates 6/6P/26 NGV and 22A/22B excluded. Fort Nelson 4/5/7/22-27 have no published price table. Batch 11: Customer Choice 1U/2U/3U (delivery-only; not offered in Fort Nelson) and RNG 1RNG/2RNG/3RNG (Mainland/VI and Fort Nelson) plus 5RNG/7RNG, with Cost of Gas and RNG Charge as conditional alternatives on the chosen share; RNG Blend Service percentage unpublished; 11RNG and vehicle RNG excluded |
| ATCO Gas | AB / excluded | 0 | Seed verification; current approved delivery classes/riders remain deferred |
| EPCOR Natural Gas | AB registry entry / excluded | 0 | Seed verification; product, jurisdiction and identity still need confirmation |
| Centra Gas Manitoba | MB / live, partial catalogue | 13 / Oct 7 | Residential/commercial Sales/T-service/marketer variants; approved PUB schedule (Nov 1, 2025, Order 138/25) required for volume boundaries, contracts, Mainline pressure, winter demand, T-service nomination and interruptible alternate-supply conditions. Batch 10 class audit runs every scrape: Special Contract and Power Station excluded with schedule evidence (p20); Mainline Interruptible with firm delivery built in batch 11 from a reviewed, hash-gated transcription of scanned Appendix A p82 (medium confidence; Sales only); fixed-term commodity prices unpriced |
| SaskEnergy | SK / live, partial catalogue | 8 / Oct 7 | Residential/small/large-commercial full/delivery-only variants; batch 10 closed Small Industrial (660,001-970,000 m3/yr, full service only, monthly delivery blocks; carbon from the general April 1, 2025 Part I row). New firm delivery above 660,000 m3 is TransGas; batch 11 adds service fees T&C-C from Appendix C (effective March 1, 2018); municipal-payment scope remains under audit |
| Heritage Gas / Eastward Energy | NS / live, partial catalogue | 3 / Oct 5 | Residential and tiered General Service from the October 2026 monthly rate table linked by 'View Rates', cross-checked with page summaries; dated zero federal charge note required; municipal riders A/B as percentages; Rate Class 3 ($1,995.54/month, $0.167/GJ, $30.85 per GJ Billing Demand/month, unit and rule from the approved tariff PDF). Rate Class 4 is negotiated per site and unpublished (exclusion, not a parser gap) |
| Liberty Utilities NB / Natural Gas NB | NB / live, partial catalogue | 4 / Oct 5 | SGS, MGS, LGS (January 1, 2025 distribution; alternative customer charges; LGS seasonal blocks) and Off-Peak Service ($50.00/month, April-November eligibility, December-March overrun note) with the current Liberty Utility Gas month and CRA New Brunswick evidence. CGS/ICGS are process-load exclusions; marketer prices not included |

Preserve m3/GJ, volume tiers and component source ownership. Verify current tax/carbon
applicability rather than copying obsolete charges. Incomplete commodity/delivery
coverage must not be hidden under a live tariff label; do not invent unit conversions.

## Northern Electricity

This section is in the active campaign from October 7 (non-market regulated service).

Observed counts below use the latest tariff versions from the batch 10 store.

| Utility | Live tariffs | Implemented path | Required work |
|---|---|---|---|
| Yukon Energy | 20 / Oct 7 | 1160 base + separate R/J/J1, F and dated relief; batch 10 adds 1180-1480 residential and 2160-2480 general service from ATCO's text joint YECL/YEC book (Board Order 2011-06), each reconciled with the R/J cross-reference; minimum bills, billing demand and power factor as conditions | Riders R1/S/E (currently zero), winter rebate (unpriced) and Rider B not modelled; book URL changes monthly |
| Yukon Electrical Company (ATCO Electric Yukon) | 20 / Oct 7 | Same joint parser and evidence as Yukon Energy for ATCO service areas; old rates.html 404 replaced | Same 20 schedules as Yukon Energy, not additional classes; renderer stalls on ATCO's JS page so the book URL is static |
| Northwest Territories Power Corporation | 63 / Oct 7 | PUB June 1, 2026 schedule via node/796: residential/GS by zone (Taltson split) and government per community; riders separate; GNWT Cost of Living Subsidy conditional credit and TPSP printed first-block price as conditional alternative, only when the residential page reconciles; batch 11 conditional Taltson retail interruptible heating (6.30 cents/kWh, Fort Smith/Fort Resolution GS/industrial, T&C Schedule D) | Snare TPSP saving does not reconcile (omitted); no published GS/government subsidy amounts; Yellowknife is Naka Power |
| Qulliq Energy Corporation | 6 / Oct 7 | April 1, 2025 interim rates for non-government, government and municipal residential/commercial; NESP seasonal allowances conditional and unpriced; medium confidence | Final GRA decision; government/municipal commercial base charges and fuel rider unpublished |

Yukon Energy's own detailed schedule PDFs remain image-only and are never read into live
values. If the joint book is missing, renamed or disagrees with the cross-reference, only
1160 remains live (or the affected rate is dropped).

## Class-Level Reconciliation (2026-10-07, batch 11)

Every published class or option recorded for the 20 campaign utilities is classified
below. "Live" counts are latest live records after the batch 11 refresh (they include
conditional adjustments and retained references). Items not listed under the other
columns are live. Excluded = outside building scope or not a general published price;
blocked = published without a printed, dated price; deferred = market-indexed (Alberta/Ontario
market-rate work). **No in-scope, priced, dated gap remains unimplemented.**

| Utility | Live | Excluded | Source-blocked / unpublished | Deferred / monitor |
|---|---|---|---|---|
| BC Hydro | 17 | RS1828 biomass contract; RS1823 cancelled; irrigation, lighting, EV, IPP, wholesale/reseller, standby | RS1289 indexed cash settlement | RS1892 (Mid-C) |
| FortisBC Electric | 11 | RS37 standby; RS96 EV; RS91 financing | RS95 (references BC Hydro RS3808 Tranche 1, not printed) | RS38 (Mid-C) |
| Hydro-Quebec | 26 | F/FP unmetered; GD backup; BR EV; LD/LP auxiliary/standby; Load Retention, Additional Electricity, Economic Development (closed), Industrial Revitalization; MA not in edition | - | - |
| Manitoba Hydro | 18 | Lighting | Curtailable and surplus programs; net-billing credit (no start date); service charges (not in approved schedule; $150 reconnection undated) | - |
| SaskPower | 41 | Lighting, reseller (farm/oil-field retained as reference) | - | - |
| NB Power | 10 | Lighting/charging retained as reference; one-time fees (labelled $/month) | Net metering ($ value), interruptible/surplus (unpublished hourly incremental cost) | - |
| Nova Scotia Power | 18 | ELIADC, Load Retention, municipal wholesale, shore power, standby, generation replacement/load following | Pilot participant restoration status | One-part real-time pricing |
| Maritime Electric | 10 | 330/340 Summerside wholesale (reference); lighting, unmetered, short-term | - | - |
| Newfoundland Power | 11 | Lighting | Curtailable Option 2 (customer load-factor formula); GS/seasonal net-metering credits (class rate, no value) | - |
| NL Hydro | 21 | CP commissioning; UT wholesale; Island Industrial Wheeling; lighting | Island thermal non-firm (fuel formula) | 5.1L and Island non-thermal non-firm (monthly market-indexed price, backed out by decision) |
| SaskEnergy | 8 | SI delivery-only (not offered); TransGas firm delivery | Municipal payments | - |
| Centra Gas | 13 | Special Contract; Power Station; MLI T-Service (identical to Mainline Firm T-Service) | Fixed-term/private commodity | MLI transcription (re-transcribe on new Appendix A) |
| FortisBC Energy | 27 | Rates 6/6P/26, 3VRNG/5VRNG (vehicles); 22A/22B; 11RNG; 11/14A/30/36/46/48; 1U-3U in Fort Nelson (not offered) | Fort Nelson 4/5/7/22-27 tables; RNG Blend Service percentage; marketer prices | - |
| Energir | 5 | - | Fixed-price supply (supplier-specific); load-factor formula (uncomputed); inventory adjustments; D5 make-up gas | - |
| Heritage/Eastward | 3 | Rate Class 4 (negotiated) | - | - |
| Liberty NB | 4 | CGS/ICGS process loads | Marketer prices | - |
| Yukon Energy | 20 | Lighting; Rates 32/39/42/43 | Riders R1/S/E (published at zero); winter rebate (replaced by Affordability Rate Relief) | Book file name changes monthly |
| ATCO Electric Yukon | 20 | Same as Yukon Energy (same 20 joint schedules) | Same | Same |
| NTPC | 63 | Standby; Naka wholesale; Con Mine; streetlighting; Taltson wholesale heating | Snare TPSP (does not reconcile); GS/government subsidy amounts | - |
| Qulliq Energy | 6 | Streetlights; standby | Government/municipal commercial base charges; fuel rider | Final 2025/26 GRA instruction (URRC recommended approval) |

## Next Batches and Acceptance

0. **Ontario (batches 1-2 done):** 46 distributors live. Open: PUC Distribution (needs a
   no-connection-rate decision); demand-class commodity/GA with the market-rate work. Next
   blocks: Alberta wires (ENMAX, ATCO Electric, EPCOR) and ON/AB gas (ATCO Gas, Enbridge, EPCOR
   Natural Gas, which is actually Ontario's Aylmer/Southern Bruce utility); source research done
   October 8, open scope questions recorded in the local task tracker.

1. The campaign's priced, dated gaps are closed (batch 11). Monitor: Qulliq final GRA instruction, NTPC Snare TPSP reconciliation, Centra Appendix A edition changes, monthly Yukon joint-book file name.
2. Re-check source-blocked items periodically (reconciliation table). Market-indexed FortisBC RS38, BC Hydro RS1892, NSPower real-time pricing and NL Hydro monthly non-firm prices wait for the Alberta/Ontario market-rate work.
3. Audit remaining building catalogues and fixtures, maintain SaskPower's audited building schedules, then run a twenty-utility refresh and class-level reconciliation. ON/AB remain excluded from this campaign.
4. Separate operational track: Chromium installation in source health, test/scrape failure issues, successful Monthly Scrape `workflow_run` deployment from `main`, and release-asset `data-history` database restore/upload after validation/export are implemented, pending first CI run verification (Deploy Site for `1b05a2f` succeeded; Source Health still needs a manual dispatch). Pages source must be GitHub Actions; `workflow_run` fires from the default branch. Meaningful provenance counts remain open.
5. Deferred product track: market-model UI/metadata correction, real observation ingestion,
   historical charts and AI export. Calculator/API requirements are separate.
6. Conditional Alberta extension: if its market-pricing variation or complexity warrants
    a dedicated view, add Alberta as a region in the existing Market Pricing dashboard.
    Use Alberta-specific values, sources, dates and methodology; reuse the interface,
    not Ontario's HOEP-plus-GA assumptions. Keep wholesale, retail and wires distinct,
    with any modeled estimates clearly identified. This remains deferred work.
7. Phase 6 also includes the separate Across-Canada comparison view described in
    [README](../README.md#phase-6-provenance-and-product-follow-up): common residential
    structures, monthly charges and commercial demand-class ladders, with provincial values
    taken from the Phase 7 representative models. It is a roadmap item, not an implemented feature.
8. **Phase 7: Representative Models** (planned October 8; design and sub-phases 7A-7G in
    [README](../README.md#phase-7-representative-models-planned)). One modeled tariff per
    province/territory, sector and offered rate structure: median across utilities,
    single-source where only one utility exists, full all-in energy once the market model
    supports it, its own site view and generated method statements. Start with 7A (category
    crosswalk) after the open decisions are settled; the Ontario scratch prototype is
    `logs/_on2_r_model.py`.

Each batch requires source-derived positive/negative tests, a source-inspected dry run,
validated storage/export, preserved history and a ledger update. Record observation dates
separately from parser capability, keep unsupported classes visible, and never delete a
database or invent rates to make completion metrics look better.

## History

Detailed checkpoints are kept in the maintainer's local tracker; earlier published
checkpoints are in git history (commits `0e43ca6` through `08531d2`). Batch 9 was
stored and exported October 6. Ontario batch 1 was stored and pushed October 7 (`1f3ae6c`);
the log cap and recorded decisions followed in `91c15cc`. Use the current queue above for next work.
