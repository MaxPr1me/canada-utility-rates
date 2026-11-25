# Phase 5 Completion Matrix

## Completed - Phase 8 monitoring

Owner decision (November 17): implement model change/freshness monitoring while municipal
publication remains pending. The implementation passes the full local suite; automated generation,
history publication, monitoring and the deployed desktop/mobile views are verified. See the
[approved model policy](../.github/instructions/representative-models.instructions.md#change-monitoring-phase-8-owner-decision-2026-11-17)
and [workflow rules](../.github/instructions/ci-data-history.instructions.md#model-monitoring).
This does not waive source checks or authorize a Monthly Scrape merely to test monitoring.

## Current milestone - building archetype costs (planned November 24)

Owner decisions 86-114 (November 24, seven question rounds): the owner's building simulations
arrived on the `dev` branch: 68 runs of NRCan's BTAP tool for NECB 2020 archetype buildings (17
building types in Toronto and Calgary, each heated by electricity or by natural gas, CWEC 2020
typical weather), with the whole building's electricity and gas use every 15 minutes for a year. The
plan, built next:
- merge the simulation outputs into `main` unchanged (about 370 MB of timestep files, which the
  workflows read directly);
- store ENMAX Energy's Medium and Large Commercial Rate of Last Resort schedules (D300 and
  D310/D410), which the rate schedule PDF the scraper already reads publishes;
- price each simulated building for a whole year, month by month, with the stored tariffs of the
  utilities serving its city: Toronto Hydro and Enbridge Gas in Toronto; ENMAX Power, with ENMAX
  Energy's Rate of Last Resort below 250,000 kWh a year or the pool-price benchmark above it, and
  ATCO Gas South with the default gas rate in Calgary. Each building takes the rate class its own
  simulated load qualifies for under the tariff's published limits, quoted with the reason;
  apartments are one bulk-metered building account. Ontario accounts that qualify for the
  Regulated Price Plan pay Time-of-Use prices, the others the market price plus Class B Global
  Adjustment from the observed hourly averages of the 60-month window; loss factors are applied as
  the OEB bill calculator applies them; taxes and the Ontario Electricity Rebate follow their
  published rules. Prices are those in force when the file is built: a comparison at today's
  prices, not a forecast or a bill;
- publish the results in a new "Building Archetypes" tab after Representative Models, labelled
  SIMULATED and rebuilt by every export. Simulated costs never enter the models' medians,
  Across-Canada, Compare, Rate History or change checks (safeguard 8 is amended with the build);
- afterwards, replace the made-up profile of the illustrative estimate with archetype shapes, after
  its own decision round.

Open: whether an official Enbridge source puts apartment buildings of more than six units on Rate 6
(until one is found, those three runs show gas as not computable). The dated December and January
checks keep priority when they fall due.

## Previous milestone - the one-year check, territorial models and the Rate History tab (done November 24)

Owner decisions (November 23): with the Phase 7 gas models and January 1 readiness published, the
order of work is a check for data that has not been updated in a year, then models for the
territories, then the Rate History tab (all three done November 24); the dated December and January
checks take priority when they fall due. The other Phase 9 items still follow the coverage-complete
claim. January 1 readiness (published November 23):
- ATCO Gas joins the monthly-price run on the 4th (its default gas rate must also be in the UCA
  table, which may post the month after the run on the 1st);
- Nelson Hydro reads its bylaw's current-year schedules from January 1, even while its rates page
  still shows the previous year; prices labelled with a year (Nelson, Penticton) end December 31;
- NS Power keeps failing closed: its 2027 DSM and storm riders are not published yet, so the Nova
  Scotia models are expected to be missing from January 1 until NS Power posts a complete 2027 book
  (in 2026 its book came in May); the owner then starts its run;
- record notes take dates and orders from the documents (NS Power's book, Centra's class-definition
  pages, Medicine Hat's brochure).

Standing guidance (owner, November 23): keep the rates up to date, but a lag of a few months is
acceptable; data not updated in a year is the key concern; scrapers should find new editions by
themselves and a flagged error should be quick to fix.

The one-year check (built November 24; design approved November 23, build details November 24):
- each official document behind a utility's current live prices (a tariff sheet, a rate page, a
  supply-price page) is dated by its last real price change: a new value, a changed tier or demand
  threshold, or a price line added or removed; a version that only re-dates the same values, or a
  line renamed with the same value, does not count; $0 lines, value-less "Variable" lines and ended
  prices are ignored. Once that date's anniversary passes, the coverage gate warns (never fails).
  Checking each document separately (owner decision November 24) means a stale tariff sheet cannot
  hide behind Ontario's regulated prices or a monthly gas supply price;
- exempt, with no end date: the Alberta Electric System Operator (a value-less market reference with
  no price to change) and Maritime Electric (estimates refreshed by hand under their own yearly
  review); both exemptions are recorded, with reason and date, in the coverage ledger, the CI rules
  and AGENTS.md;
- a dated ledger review note (the finding: legitimate, parser fixed, or the utility moved on) clears
  the flags that exist on its date for a year (or until an earlier date it names), and a real price
  change clears a flag by itself;
- reporting: one separate GitHub issue per quarter, "Rates not updated in a year", opened after the
  first successful full Monthly Scrape of January, April, July and October when something is
  flagged; every monitoring run refreshes its list and it closes itself when the list is empty. The
  first report is in January 2027. On November 24 eight utilities were flagged: Direct Energy
  Regulated Services, ENMAX Energy and EPCOR Energy (fixed Rate of Last Resort term), SaskEnergy,
  Qulliq (interim rates since April 2025), Liberty NB (distribution charges from January 2025) and
  Yukon Energy and ATCO Electric Yukon (base rates dated 2011, adjusted through riders). The first
  review round (owner decision November 24) found all eight legitimate after checking each official
  source and dry run; the dated ledger notes clear them for a year (the three Rate of Last Resort
  providers until December 31, the end of their term).

Territorial models (built November 24 as method 7T-1, owner decisions 64-79; published by the push):
Yukon (the joint rate book of Yukon Energy and ATCO Electric Yukon, counted once), the Northwest
Territories (NTPC and Naka Power, each the median of its zones) and Nunavut (Qulliq, interim rates
labelled), for homes and small businesses. Percentage riders of the base charges (Yukon's Riders R, J
and J1; Naka's Riders R, E and H, whose base includes the fuel charge) are applied through a reviewed
list, never guessed; government rates stay out of the medians. Each territory shows its cost before
subsidies (with GST) and, for homes, after the automatic subsidies, before tax: the NWT power support
program's first block at 36.50 cents/kWh all-in (NTPC's riders and Cost of Living Subsidy apply above
it), month-weighted by season; Naka's rate equalization for Thermal-zone homes; Yukon's dated
affordability relief. NTPC's Snare-zone first block is not applied (its stated saving does not
reconcile), and Nunavut is shown before subsidy only, because the subsidised price is not published.
After-subsidy figures stay before tax until the tax base on subsidised bills is confirmed. At 1,000
kWh, before tax: Yukon $323.62 before and $253.66 after subsidy; Northwest Territories $542.73 and
$429.16; Nunavut $785.40 (before subsidy only). All 85 provincial models are unchanged.

The Rate History tab (built November 24; owner decisions 44-57 of November 23 and 80-84 of November
24): a sixth view, right after the Rate Browser, with four sub-tabs (tariff prices, regulated and
default prices, market prices, model costs) under a "Recent price changes" list. It charts only live
data the project has collected since September 29, 2026, plus the full stored market history (complete
quarters, hour-weighted) and the quarter-end model costs rebuilt from the model change log. It never
charts estimates, never extends an ended price (a price also ends with its tariff version) and never
adds charges together; regulator and government decisions are marked from a reviewed list with their
official sources. Stored history is still short: by November 20 the only real price changes were
effective November 1, 2026 (Ontario's regulated prices and the monthly or quarterly gas supply
prices), plus one NS Power change of May 1, 2026. Its quarterly market and model files and its
same-date correction notes appear after the next data runs.

### Phase 7 gas (done November 23)

Owner decisions (November 20): the order of work is Phase 7 commercial gas, then models for the
territories, then Phase 9 after the coverage-complete claim. Phase 6E (gas supply-price freshness)
is done as part of the gas work. Gas decisions:
- volume-billed general-service classes first; contract-demand and interruptible classes later,
  with their own decision;
- Ontario and Alberta commercial gas are included (Enbridge and EPCOR general service; ATCO Gas Mid
  Use with the Direct Energy Regulated Services default rate);
- the example customers use typical volumes published by utilities or regulators, in m³ and GJ;
  the owner approves the levels before any code;
- New Brunswick uses Liberty Utility Gas as the reference supply (customers may choose a marketer);
- Énergir D1: one meter; the annual volume is 12 times the monthly level (basic-fee band, load
  balancing below 75,000 m³); the daily blocks use the monthly volume divided by 30.4375; the
  renewable-gas riders are checked in the tariff first;
- Saskatchewan commercial gas carries no PST (building-heating exemption).

Small fixes approved the same day: Alberta's model coverage no longer counts AESO (a value-less
price reference, not a seller), the diff report compares only the utilities the newer run scraped,
and the console log writes UTF-8. Research only: observed 50-4,999 kW load profiles in OEB rate
applications (none qualifies; Alectra's combined 50-4,999 kW raw hourly class data comes closest).

Second decision round (November 20), from the commercial gas research:
- Commercial gas levels (average month), two building sizes per unit with half and double
  sensitivity levels: 1,000 m³ (500, 2,000) and 5,000 m³ (2,500, 10,000); 30 GJ (15, 60) and 200 GJ
  (100, 400). Each utility is priced on the general-service class whose published annual limits
  contain 12 times the level. Backing: Enbridge, SaskEnergy, Énergir, FortisBC, ATCO, Eastward and
  Liberty typical-customer figures, Statistics Canada deliveries and NRCan's 2019 commercial
  building survey.
- Liberty's class and customer charge follow its monthly peak, taken as 1.85 times the level
  (Statistics Canada New Brunswick commercial January deliveries); Enbridge Union Rate 01/M1 and
  ATCO Gas Low Use also feed the commercial models; Centra uses the cheaper of SGS and LGS.
- Supply prices carry their period: quarter end for Enbridge, EPCOR and Énergir cap-and-trade, the
  day before Centra's next quarterly date, month end for Énergir supply, Eastward General Service and
  Liberty, the six-month block end for Eastward residential, none for FortisBC and SaskEnergy. A
  second scheduled Monthly Scrape refreshes the monthly-priced utilities, Medicine Hat included,
  instead of the owner's manual run. Decided November 23: it runs at 08:00 UTC on the 4th; model
  monitoring holds those utilities' failures from the 1st until it; a manual run stopped by its input
  check is not a monitoring problem.
- Énergir's supply price is fixed first (done November 20: read monthly from Énergir's
  supply-price page, checked against its price history workbooks; stored the same day by the
  owner's Énergir Monthly Scrape, scrape run 45); its two renewable-gas socialization charges count
  for the default customer.
- Taxes as published (all eight provinces checked); Saskatchewan keeps 0% PST with a note on water
  heating and cooking; Alberta's Natural Gas Rebate Program is named, not modelled, below its
  $6.50/GJ trigger.
- Owner rule: every usage level and load profile documents its decision, reason and what it
  represents, with official and peer-reviewed sources. Electricity levels documented the same day:
  residential 1,000 kWh is the reference and 500/2,000 kWh are labelled sensitivity levels; small
  business s1 becomes 2,000 kWh at 14 kW and s2 10,000 kWh at 40 kW (Hydro-Québec and NB Power
  comparison levels; the OEB's standard small-business customer is 2,000 kWh); m1 and l1 stay. These
  ship with the commercial gas model release.
- Archetype load profiles: the owner runs BTAP commercial archetypes (Toronto and Calgary) and
  supplies simulated meter data, first for the opt-in illustrative estimate (after the commercial
  gas models are published), later for a Phase 9 archetype comparison. Simulated values stay out of
  the base models. Update November 24: the data has arrived and the order is reversed: the archetype
  cost comparison comes first, ahead of the coverage claim, and the illustrative estimate's profile
  is replaced afterwards (see the current milestone above).

Progress (November 23): the small fixes are published. Énergir's monthly supply price was stored by
scrape run 45, and the other supply-price period ends by the owner's full run on November 20 (scrape
run 46). The monthly-price run on the 4th is added: the registry flag `monthly_price_refresh` on
Énergir, Eastward (Heritage Gas), Liberty and Medicine Hat (ATCO Gas added later the same day),
clearer input checks before anything is
installed (utility names matched without accents or case, with the closest registry names) and its
own monitoring check; its first run is December 4.

Commercial gas models (method 7D-2, November 23): built and tested, published with the push of the
same day (the Market Benchmarks run republishes the models). Every general-service class of a gas
utility now feeds one model per building size, priced at each level on the class whose reviewed
limits contain it (with each tariff's wording on whether a limit itself is included); Énergir D1
(one meter, basic-fee band, daily blocks, load balancing below 75,000 m³) and Liberty Utility Gas
are priced, so Québec and New Brunswick homes are modelled too; the small-business electricity levels
moved to 14 and 40 kW (BC Hydro is priced on Rate 1500 at 40 kW; FortisBC Electric Rate 20 is "not
more than 40 kW"). Owner decision November 23: the Rate Browser shows a dated price's period and an
"Ended" tag once it has passed. The model preview against the published models showed only these
intended changes. Next: the building archetype costs (planned November 24; see the current milestone
above), with the dated December checks taking priority when due, then the January renewals and the
Ontario January batch, the coverage wording and the rest of Phase 9 (the one-year check, its first
review round, the territorial models and the Rate History tab were done November 24).

Dated checks (owner decisions, November 19) take priority when they fall due. Batch 18 continued
was published on November 19 (see [Registered municipal additions](#registered-municipal-additions)),
so every registered utility has stored live output:
- December 1: the scheduled Monthly Scrape; Medicine Hat is expected to fail closed until the City
  posts December's default rate, and monitoring holds it for the next run.
- December 4: the first monthly-price run (Énergir, Eastward, Liberty, Medicine Hat and ATCO Gas).
- December 15: twelve ledger monitor reviews (Yukon Energy, ATCO Electric Yukon, NTPC, Qulliq, EPCOR
  Distribution, the three Rate of Last Resort providers, Naka Power, Medicine Hat, Lethbridge and
  Red Deer). The strict gate fails from December 16 for any not reviewed.
- December 31: the Alberta Rate of Last Resort term ends (no 2027 term published yet), with the
  Lethbridge and Red Deer city prices and Medicine Hat's large-customer fixed rate.
- January: other January editions, and the Ontario January rate orders (added once in effect, then
  one Ontario Monthly Scrape). NS Power is expected to return estimates from January 1 until it posts
  a complete 2027 book; Penticton's 2027 prices count once its fees bylaw prints a 2027 column.
- Ledger audits expire February 4 (14) and February 27 (62) under the gate's 120-day rule.

## Completed - source reliability and Batch 18 publication (November 17-19)

Owner decision (November 17): repair and verify Maritime Electric, Grand Forks and New Westminster
source discovery, then publish the already-registered municipal additions below. The additions,
Grand Forks and New Westminster are published (November 18); NL Hydro and Heritage Gas were verified
on GitHub on November 19, and Maritime Electric became a manual-update utility (below). Current
figures are in the [README status](../README.md#current-status).

The November 15 Source Health log returned estimates for Maritime and no records for Grand Forks,
despite a green workflow. New Westminster's old index returned 404. The repairs retry Maritime's
official page through Chromium after HTTP 403, prefer Grand Forks' dated document library and follow
New Westminster's migrated bylaw page. No rate arithmetic, source/date checks or provenance rules
were relaxed.

Acceptance order: inspect a fresh GitHub Source Health log; run the unfiltered Monthly Scrape only
after target sources are healthy; verify preserved history, the strict coverage gate, zero unmapped
live tariffs, model contributors/limitations and the deployed data. A stored live record or green
workflow alone does not close a source problem.

Monitoring issue #6 (November 18): it first listed the seven unpublished additions, a Monthly Scrape
without receipts and the overdue November 15 Source Health. Owner decisions (November 18): source
checks ignore only labelled excluded-class estimates, so the 45 Ontario distributors that keep
their street-lighting estimate are not permanently unhealthy, and the Centra monitor is closed.
Those three problem groups are now cleared; the issue's remaining source problems are listed below.

The November 18 Source Health confirmed the street-lighting rule on GitHub but found three sources
that work locally and fail only on GitHub's runners. Owner decisions (November 18):
- Grand Forks: Cloudflare returns 403 for its document library and media search but not for the
  uploaded PDFs. The scraper now reads the last known copy of the amending bylaw that Schedule G
  names, with a note on the records; an amendment with no known copy still fails closed.
- Maritime Electric: Cloudflare also blocks the Chromium retry. Accepted for now: its labelled
  estimates keep issue #6 open until Maritime Electric allows automated access or another official
  route is found (superseded November 19, below).
- FortisBC Energy: the B.C. carbon-tax page dropped the connection once; recheck it without a code
  change.
Then run Source Health again, then the unfiltered Monthly Scrape.

Publication (November 18): the owner's unfiltered Monthly Scrape (run 44365197451) stored every
utility, but on GitHub's runners New Westminster and Penticton returned no valid records and Heritage
Gas, Liberty NB, Maritime Electric and NL Hydro returned estimates only. All except Maritime had been
live locally and in Source Health shortly before. Owner decision (November 18): rerun each with a
single-utility Monthly Scrape, one at a time, with no code change. New Westminster (44377933899),
Penticton (44381098574), Heritage Gas (44384556313) and Liberty NB (44386489358) were stored live;
every run verified the preserved history. The strict coverage gate passes for all 85 utilities,
the crosswalk has 0 unmapped live tariffs and the published models match the November 4 preview.

Still open on November 18 (owner decision: stop here and revisit):
- NL Hydro (rerun 44388480702 failed again): GitHub's runner gets a rates page without the Schedule
  of Rates link that the page shows locally. The cause is not confirmed because the logs recorded
  no response details.
- Maritime Electric: the Cloudflare block on GitHub, accepted above.
- Eastward Energy (Heritage Gas) General Service: the business page still says "as of October 1,
  2026" while the rate table is effective November 1, 2026 with the same fixed charge, delivery
  and gas-cost values. The date check rejected the class, so November stored no General Service
  record and the October record stays.

Owner decisions (November 19), implemented and verified locally (all tests pass; dry runs fully
live: NL Hydro 23, Maritime 10, Heritage 3) and then on GitHub:
- Every fetch logs its response (status, final URL, type, size, server, `cf-ray`, title), and the
  `User-Agent` names the repository, so the next GitHub log shows why a runner was refused.
- NL Hydro: when the page fails or links no schedule, read the last known Schedule of Rates PDF with
  a note. A discovered link always wins.
- Maritime Electric: only when the 403 retry yields no schedule link, read the last known N-28 PDF
  with a note. Residential and general service stay live; Section N classes still fail closed.
- Both known copies stop counting as live after November 19, 2027 unless reviewed, so a stale copy
  cannot stay live indefinitely.
- Eastward General Service: an older page date is accepted only when every value matches the rate
  table; a newer one is rejected. Residential stays strict.
Rules: [regional](../.github/instructions/regional-utilities.instructions.md#maritime-electric) and
[gas](../.github/instructions/gas-utilities.instructions.md#eastward-heritage-gas).

GitHub verification (November 19): Source Health (44548652298) returned 950 live and 47 estimated
records, with Maritime the only estimates-only utility. Single-utility Monthly Scrapes stored NL Hydro
(44551268822, 23 live from the last known Schedule of Rates) and Heritage Gas (44555379607, 3 live,
General Service refreshed). Maritime Electric (44552590090) stored 2 estimates: Cloudflare returns 403
on GitHub for the rates page, the Chromium retry and the N-28 PDF itself.

Owner decisions (November 19, Maritime): treat it as a manual-update utility. IRAC orders are not
used as a live source and Maritime is not asked to unblock the runners. The seed estimates now mirror
the current N-28 Rate 110/232 values (still labelled Estimated); the coverage ledger records a
`manual_update` reviewed by September 1, 2027, which model monitoring honours until then, with no new
workflow. Its 10 live August 2026 tariffs stay published; a rate change before the review is
noticed only by the yearly local check. Procedure:
[regional rules](../.github/instructions/regional-utilities.instructions.md#maritime-electric).

Result (November 19): the Market Benchmarks run started by that push (44562265776) re-checked the
receipts with the ledger rule, found no remaining problem and closed issue #6 itself. The source
reliability milestone is complete. Batch 18 continued (Naka Power, Medicine Hat, Lethbridge, Red
Deer and the Alberta city pairing) followed and was published the same day; see
[Registered municipal additions](#registered-municipal-additions).

### Registered municipal additions

Owner decision (November 4): add the easy and medium electricity utilities to the inventory and register
each one once its parser is live and audited; they join their province's model medians.

Registered with live parsers (status `partial`) and stored live on November 18:

| Utility | Prov. | Dry run | Classes | Held back or excluded |
|---|---|---|---|---|
| Saint John Energy | NB | 8 live | 001, 006, 002, 202, 004, 008, 009, 010 | Municipal Related rates, rentals, lighting, EV, fees |
| Nelson Hydro | BC | 4 live (interim) | A1, A3, B1, B4 | C1/C4 source-blocked (">25 kVA" wording); E1, EV1, F1/F2, G-3, M1/M2 |
| City of New Westminster | BC | 10 live | 101-103, 131, 134, 201, 202, 210-212 | 203/213, 241 pilot, lighting, net metering |
| City of Penticton | BC | 5 live | 10, 20, 25, 30, 35 | 45 City accounts, 55 lighting/unmetered |
| City of Grand Forks | BC | 3 live | Schedule G items 1-3 | Unmetered service |
| District of Summerland | BC | 5 live | E01-E08, E10, E15, E17, 19 | E12/E14, E20, E22, E25, E26, lighting |
| Summerside Electric | PE | 8 live | Residential urban/rural/seasonal/option, GS I and seasonal, SI, LI | GS II (closed), HFLN, unmetered, lighting, EV; ECAM source-blocked |

Model preview with the parsed fixtures (as of November 4): crosswalk 584 mapped / 376 excluded / 0
unmapped; 69 models instead of 64. BC residential grows from 2 to 7 utilities (1,000 kWh median
$157.21 to $168.74 before tax); NB and PE residential and commercial models gain a second utility;
five new BC/NB commercial groups appear. The November 18 publication matched this preview.

The first-seven provisional choices were confirmed by the owner on November 17; see the
[municipal rules](../.github/instructions/regional-utilities.instructions.md#municipal-utilities-batch-18).

Batch 18 continued (owner decisions November 19), registered with live parsers (status `partial`)
and stored live on November 19:

| Utility | Prov. | Stored (Nov 19) | Classes | Held back or excluded |
|---|---|---|---|---|
| Naka Power Utilities (NWT) | NT | 6 live (interim riders, medium) | Snare residential and GS; Taltson residential, GS and LGS; Thermal residential | Thermal GS source-blocked ($14.00/kW demand vs $10.00/kW total); lighting, Taltson interruptible, Hay River wheeling |
| City of Medicine Hat Electric Utility | AB | 5 live | 1.1, 3.1, 3.3 (monthly default rate), 4.1, 5.1 (fixed rate to December 31, 2026) | Farm, temporary, irrigation, unmetered, lighting; MCAF a note |
| City of Lethbridge Electric Utility | AB | 8 live | 991, 992, 994, 995, 996, 997; City Rate of Last Resort (RoLR-Res, RoLR-SB) | 998-1000; Rider A a note; undefined "RDS" price source-blocked |
| City of Red Deer Electric Light & Power | AB | 8 live | 61, 63, 64, 78; Rate of Last Resort RRT-61/63/64/78 | 81-83; Local Access Fee a note |

Owner decisions (November 19):
- Red Deer's administration charge comes from Schedule D ($0.3035/day), with a note; its 12.06
  cents/kWh applies to every rate.
- Medicine Hat 4.1/5.1 are complete records kept out of the models.
- The Going Green surcharge is dated to the month it was read.
- Medicine Hat's monthly row is required: the owner starts a Medicine Hat run each month once the
  City posts it. Replaced on November 23 by the Monthly Scrape on the 4th; the owner's run is needed
  only when the City posts later.
- Each Medicine Hat record ends with its shortest-lived price, and models leave out records past
  their end date.
- Medicine Hat 1.1 is flat; 3.1/3.3 are not modelled (class limits unpublished).
- Lethbridge 991 is used at every residential level, and Lethbridge is not computable at s1 (994 is
  three-phase only).
- Alberta model contributors are called "service areas"; the method version stays 7D-1.
- Naka's interim monitor is reviewed December 15.

Model preview with the frozen parser records (`tests/fixtures/rm_records_b18_ab.json`) added to the
November 19 export:
- Crosswalk: 591 mapped, 396 excluded, 0 unmapped (987 records).
- Still 69 models. Only five Alberta electricity models change; every other model is identical.
- Residential: 4 to 7 service areas; median at 1,000 kWh $225.16 to $209.78 before tax.
- Commercial small: flat s1 2 to 3, flat s2 1 to 2, demand s2 2 to 3.
- Demand: m1 4 to 6 (median unchanged); l1 3 to 4.

Publication (November 19): the owner's Monthly Scrapes for province AB (44601990144, scrape run 43:
60 live, no estimates, the 21 city records new) and for Naka Power (44603496943, scrape run 44: 6
live) verified the preserved history. The strict coverage gate passes 89/89, the crosswalk has 0
unmapped live tariffs and the published models equal this preview. Monitoring issue #7, opened when
the push registered the four before storage, closed itself after the Naka run. The AB run's
non-blocking model-history step exited 1 because Naka was not stored yet; the history was still
recorded.

Remaining:
- Medicine Hat each month: the run on the 1st usually comes before the City posts the month's row and
  fails closed; its 1.1/3.1/3.3 records then end and leave the models until the Monthly Scrape on the
  4th stores the row (monitoring holds the failure until then). If the City posts after that run, the
  owner starts a Medicine Hat run. On January 1 the 4.1/5.1 fixed-rate term ends too, so until the
  January row (and the City's 2027 rate) is stored Medicine Hat has no live record and the strict
  gate fails for it. The City recalculates on Monday January 4, probably after the run that morning.
- Lethbridge and Red Deer Rate of Last Resort records end December 31, 2026 with the provincial
  term; the next term is a December 15 ledger review.

## Previous checkpoint - November 4, 2026

The owner's targeted Monthly Scrapes stored both corrections.
- **Centra:** run [41867595672](https://github.com/MaxPr1me/canada-utility-rates/actions/runs/41867595672),
  scrape run 31, bot commit `b51710a`. It stored 13 November records from the v1126 PDF, including HVF
  -$0.0018 and MLI -$0.0017/m3 transport.
- **Maritime:** run 41867644701, scrape run 32, was queued behind Centra by the shared
  `utility-data-updates` concurrency group, so the runs never overlapped and its database update was
  stored and verified. But it built `site/data` on its dispatch-time checkout (`848ef28`), and its final
  `git pull --rebase` conflicted with `b51710a` (issue #5, closed). The re-dispatch
  ([41873587254](https://github.com/MaxPr1me/canada-utility-rates/actions/runs/41873587254), scrape run 33,
  `ad656bc`; Market Benchmarks `b5502524`) published both corrections.

Verified on the pulled mirror and export:
- History: 10 snapshots added, 5,557 earlier unchanged (33 runs, 5,567 snapshots, sha256 `0d2a9531…`).
- Maritime: rates 232/233 carry the first 20 kW free; PE 232 pre-tax costs are 462.17 / 1,617.12 /
  7,225.97 / 85,460.97 at s1/s2/m1/l1.
- Strict gate 78/78; crosswalk 557 / 360 / 0 unmapped.
- Full model parity after normalizing only timestamps and input paths.

Remaining:
- The owner's approval of the scoped coverage-complete README wording.
- The Centra HTML-difference monitor (November 30).

Done since: the `scrape.yml` stale-checkout fix. The Monthly Scrape now runs `git pull --ff-only`
before exporting and pushes without rebasing, as the market workflows do (owner decision, November 4).

## Checkpoint - November 2, 2026

The November 1 automation succeeded:
[Monthly Scrape](https://github.com/MaxPr1me/canada-utility-rates/actions/runs/41317063703),
[Ontario Price Archive](https://github.com/MaxPr1me/canada-utility-rates/actions/runs/41308759280)
and both follow-on deployments (41318171963 / 41308851987). Pulled bot commits `f9d68d3`,
`81e099c`, `20c73d4`; refreshed the digest-verified read-only mirror. Run 30: **917 live,
45 seed, 0 invalid, 78 utilities**, no failures/seed-only utilities; **5,534 snapshots**,
with all 4,572 previous rows unchanged; 1,803 tariff versions / 20,430 components /
1,323 historical live versions / 480 retained estimates. Latest-live regional count: 249,
territories 109, Ontario electricity 490, Alberta wires/RoLR 28, ON/AB gas 40, AESO 1.

Strict gate **78/78** on November 1 and 2, crosswalk **0 unmapped**. All substantive
model fields, including illustrative values, match CI after normalizing only generation
timestamps and equivalent input paths. Published method 7C-3: 55 models, **18 modeled /
26 single-source / 6 pending / 5 not computable**. These are not live tariff counts.

Implementation commit `b2bb72d` was pushed to `main`; its
[Deploy Site run](https://github.com/MaxPr1me/canada-utility-rates/actions/runs/41468505293)
succeeded. This publishes the code and website, not the corrected Centra/Maritime rate data.

### Implemented and verified; corrected rates await CI

- **Centra:** the passing run stored 13 August-priced records because current HTML mixed
  old headings with new prices. Owner-approved source policy: the supported current quarterly
  PDF is authoritative. All 13 November records now parse live at high confidence, including
  HVF -$0.0018 and MLI -$0.0017/m3 transport. Exact PDF/fixture hash and pages 80/81/82 verified;
  headers, columns, units, totals, eligibility, carbon and marketer evidence stay strict.
  Stale commercial/supply headings and the HTML Interruptible total discrepancy are reported.
  Generic negative-transmission warnings remain visible; 0 invalid records.
- **Maritime:** corrected a parser bug, not a missing source: N-28 prints the first 20 kW
  free for 232/233. Dry run 10 live / 0 seed / 0 invalid. Parser-to-model tests produce
  pre-tax 232 costs 462.17 / 1,617.12 / 7,225.97 / 85,460.97 at s1/s2/m1/l1. Seasonal
  exclusions remain. No model engine, method-version or schema change.
- **Site:** existing fixed-charge assumptions now visible for all supplied levels and
  selected contributor components. Separate Across-Canada residential electricity view:
  500/1,000/2,000 kWh, default 1,000, separate structures, 13 jurisdictions and explicit
  missing/pending/withheld states; no synthetic values. Existing Compare remains two tariffs.
- **Verification:** 2,124 regression tests / 28 modules passed; actual served site checked
  at 1280 and 390 px, all five views, correct model totals, no page errors/overflow.
  New source/ledger integration additionally checked with the URL and coverage-gate suites.

### Exact remaining queue / publication gate

The subsequent November 2 Ontario totals/retention work adds permanent combined hourly
and monthly cents/kWh CSVs plus the requested 2020-2025 extract (52,608 slots: 46,728
totals, 5,880 explicit gaps). April's official hourly observations are included with a
monthly-discrepancy warning, without changing the existing heatmap/models. Original
sources remain. Raw IESO reports are now captured separately before price validation:
94 initial original reports saved; SHA-256-checked replay passes the strict archive dry
run. The schedule remains the 1st and 15th by user choice; raw saves survive validation
failures, and failed Git saves get a recovery artifact and an issue. Focused regression:
168 tests passed; full regression **2,237 tests / 35 modules passed**. Every one of the
52,608 historical rows was independently checked for units, formula and gap labels.
No database or local validated-archive writes.

Published implementation `9ea26f5`; [Ontario Price Archive 41506258594](https://github.com/MaxPr1me/canada-utility-rates/actions/runs/41506258594)
passed and saved `2eda534` (archive) and `633cf2e` (totals/market/models). All 2,736 prior
DA-OZP hours remain; 48 new hours and 96 LFDA/status updates were saved, with all 94 raw
objects intact. Follow-on Market Benchmarks saved `0c941b9`; deployment `41506631351`
succeeded. Pulled those bot commits and proved total CSV/metadata parity; no change to the
verified 2020-2025 extract. The source-correction queue below is independent.

The additional November 2 market/chart implementation adds method 7C-4, separate Ontario/
Alberta historical benchmarks, an Alberta dashboard/history builder, grouped province-color
comparison bars and CI model refreshes. AESO owner-confirmed permission covers raw and derived
publication (grant not independently inspected). Live validation: November 2021-October 2026,
43,824 hours, 576 bins, all 60 monthly means within $0.01/MWh of official summaries (largest
error $0.00485215/MWh). Ontario benchmark 10.4199167 cents/kWh; Alberta 8.990570347 cents/kWh.
These are equal-month historical energy means, not customer-weighted bills.
Release validation: **2,186 tests / 33 modules passed**; actual 1280/390 px previews
rendered Chart.js, both benchmarks and grouped national bars with no page errors or overflow.
Implementation `d194efe` was pushed. [Market Benchmarks](https://github.com/MaxPr1me/canada-utility-rates/actions/runs/41488097739)
passed its Python 3.12 tests, source checks and model build, publishing `6cbb988`;
[Deploy Site](https://github.com/MaxPr1me/canada-utility-rates/actions/runs/41488260353) succeeded.
The bot commit was pulled; live JSON and JS match canonical Git blobs. Real desktop/mobile
checks passed with Chart.js, 60 Alberta rows, 13 comparison groups and both benchmarks.
Published method 7C-4 retains the 55 base states above; four demand models now have benchmarks.
Post-pull: 141 focused tests passed, strict gate 78/78 (Centra monitor due soon), crosswalk
557 mapped / 360 excluded / 0 unmapped. No database writes. Current source-correction
actions below remain independent.

1. Issues #3 and #4 are closed (verified against GitHub November 2). The evidence remains
   the `math.fsum` fix (`a89e436`), successful November 1 tests/archive and `f9d68d3` / `81e099c`.
2. After the implementation push, owner dispatches **Monthly Scrape**, branch `main`,
   `utility = Centra Gas Manitoba`, empty `province`; wait for success and deployment.
   Then dispatch `utility = Maritime Electric`, also with empty `province`.
3. Check provenance, unchanged old snapshots, backups, bot commits, corrected Centra
   dates/values and Maritime free tier/model costs. Fast-forward bot commits, refresh the
   read-only DB, rerun strict gate/crosswalk and full model parity at the new export date.
4. **Only then** publish the scoped coverage-complete README status. A green gate cannot
   dismiss the known Centra contradiction; local dry runs are not publication.
5. Centra monitor stays due **November 30**, including HTML discrepancy review. Yukon still
   advertises October's book; run 30 stored 20 records for each utility, not a newer edition.
   Both December 15 monitors remain open; no speculative discovery change was made.
   **November 4 sweep** (ledger notes): no newer Yukon book (11- and 12-2026 return 404);
   NTPC Snare, Qulliq (interim) and EPCOR Distribution (interim) unchanged; no next RoLR term
   on the UCA or provider pages. Centra's residential and commercial pages now show November 1
   headings; the HVF composition sentence and Interruptible Sales HTML prices still differ
   from the authoritative PDF. Dry runs: Yukon 20/20, NTPC 63, Qulliq 6, EPCOR Distribution 5,
   Centra 13 live, all 0 seed / 0 invalid. New `tests/test_rolr_next_term.py` pins the
   January 1 switch and the fail-closed cases. **January readiness (November 4 audit):** the OEB
   BillData feeds said `YEAR=2026` on November 4 (corrected November 19: the feed is only a
   cross-check, so a January run on a 2026-labelled feed only logs cross-check warnings and the
   tariff-sheet records still refresh; no decision is needed).
   January-rate-year Ontario tariffs need `OEB_TARIFF_DOCUMENTS` updates on or after January 1,
   or the 2026 sheets stay accepted until their 500-day cutoff. Centra needs its February 1
   `SCHEDULE_EDITIONS` entry. Pinned by `tests/test_edition_rollover.py`.
6. Manitoba Small (Non-Demand) is calculable from stored corrected data; Small (Demand)
   remains unavailable without phase and qualifying demand-history assumptions.
7. Gas usage/unit and Phase 8 monitoring were initially proposals. Gas:
   separate native m3/GJ tracks, source-backed residential examples; commercial demand
   needs explicit annual/history inputs. **Gas update (November 4, owner decisions):** 7D-1
   implements residential default-supply gas models in native units (m3 100/200/400, GJ
   4/8/16); commercial gas withheld; Energir (banded per-device fees) and Liberty NB
   (optional utility supply) fail closed; gas tax lines audited unchanged. Phase 8 was approved on
   November 17 and is implemented and verified above; the former threshold/issue proposal is superseded.
   Synthetic sensitivity remains queued. Historical Alberta market work is implemented above;
   real-profile weighting remains unavailable. Toronto Hydro's published numeric example is
   illustrative; FortisAlberta settlement profiles are assigned shapes, not verified observed
   commercial loads. Exact datasets and reuse terms still need qualification; geographic
   proxies remain a separate option.

## Active Regional Campaign (2026-10-09)

Implementation batches through batch 11 cover the 16 registered utilities in BC, QC, MB, SK,
NB, NS, PE and NL (ten electricity and six gas) and, from October 7, the four territorial
utilities (Yukon Energy, ATCO Electric Yukon, NTPC, Qulliq), whose service is non-market
regulated. Ontario electricity distribution ran as a separate block (batches 1-2, October 7-8;
PUC Distribution October 9; see the Ontario section). Batch 12 (October 9) added Alberta
electricity (four wires utilities and three Rate of Last Resort providers) and Ontario/Alberta gas
(Enbridge Gas, ATCO Gas and a new EPCOR Natural Gas (Ontario) entry that replaces a retired,
mis-registered Alberta entry). No other inventory utilities are being registered; Apex Utilities
(an Alberta gas distributor) is an open question.

**Current checkpoint (October 9):** batch 12 stored and exported (scrape runs 27 and 28):
**910 latest live records across 77 utilities**: **243 at the 16 provincial targets**, **109 at
the four territorial utilities**, **490 at 47 Ontario distributors**, **28 at seven Alberta
electricity utilities** and **40 at three Ontario/Alberta gas utilities**; **1,683 passing tests
across 8 modules** (including the Phase 7A/7B and Phase 6A tests). DB validation reported 0 errors and 2 existing AESO warnings
(`pipeline.validate` now reconfigures its output so Windows consoles no longer crash on
non-ASCII names). No campaign utility is seed-only; the reconciliation table below classifies
every recorded class of the 20 campaign utilities, and no priced, dated in-scope gap remains
there. Local history contains 3,616 snapshots; prior snapshots and non-target tariffs unchanged.
Phase 7A/7B were done for Ontario that day; since October 16 (7C) every export writes
electricity representative models for all ten provinces to `site/data/representative_models.json`
(modeled comparison indicators, not live coverage; shown on the site's Representative Models tab).
Phase 6A was done the same day (observed legacy HOEP 2020-2024 plus Class B Global Adjustment);
since October 16 the Market Pricing view shows the rolling 60-month history (legacy HOEP, then the
Ontario Price, plus Class B GA), never copied into a tariff.

**October 15 and 16:** October 15: CI fixes
(`1b10d9a`), the Ontario Price hourly archive and its workflow (`8561352`), the Representative
Models tab (Phase 7F, Ontario) and an old-vs-new Ontario market comparison. October 16 (batch 14):
Lane F (`a919684`: EPCOR Energy Alberta's moved Rate of Last Resort pages; dry run 4 live, 0 seed),
CI as the only writer of the history database and the rolling five-year Ontario market history
(`b070725`), and Phase 7C for all ten provinces plus the 7E illustrative sidecar (`49a0daa`),
exact float sums (`a89e436`), then the first stored CI scrape (run 29, below) and the archive
workflow change; **1,867 passing tests across 14 modules**.

**CI (October 16):** Deploy Site succeeds on every push. Workflow steps run under
`bash -o pipefail`, runners are pinned to `ubuntu-24.04`, and every scrape run posts a public
provenance notice. Source Health
[run #6](https://github.com/MaxPr1me/canada-utility-rates/actions/runs/38808829718) (dispatched on
`1b10d9a` on October 15, 13 minutes) passed: "Dry run. Live 909, seed 46, invalid 0; utilities 78
(45 live + seed); failed: none; no valid records: none; seed only: Alberta Electric System
Operator". A local dry run gave the same totals. The one record missing from the export's 910
latest live was EPCOR Energy Alberta's residential Rate of Last Resort for the FortisAlberta area:
its page had moved and returned 404, so the record failed closed; Lane F registered the new
addresses on October 16 (dry run 4 live). The "git exited with code 128" warning on every run comes
from the checkout clean-up step: two `.claude/worktrees` folders are committed as submodule links
without a `.gitmodules` file (harmless). The first Monthly Scrape under the new database rules
(October 16, run 38939983665) restored and checked the database correctly, then stopped at the
tests (4 failures: Python 3.12 adds up decimals slightly differently from 3.11, which moved one
median by a cent), so nothing was saved (issue #3); the calculation now uses exact sums (`math.fsum`).
The owner created the `data-history` release from
the local database on October 15 (same SHA-256). **Since October 16 the Monthly Scrape is the only
writer of the history database** (user decision): the restore must succeed and match the asset's
SHA-256 digest (only a missing release starts a new database); `scripts/check_db_history.py`
checks integrity and that history only grows (snapshots, tariff versions and scrape runs not
fewer; earlier snapshots unchanged) before the upload; a dated gzip backup is uploaded with
`rates.db` and backups are pruned to the newest 12; a public "Database history" notice is posted;
a `province` dispatch input was added. Local copies are read-only mirrors
(`python scripts/pull_history_db.py`); nobody stores scrapes locally or uploads by hand. Deleting
the release would delete the database and all backups. Monthly Scrape
[run #11](https://github.com/MaxPr1me/canada-utility-rates/actions/runs/38944665359) (dispatched
on `a89e436`, October 16, 14 minutes) then passed every step: digest-checked restore, tests,
scrape run 29 ("Live 910, seed 46, invalid 0; ... seed only: Alberta Electric System Operator";
EPCOR Energy Alberta 4 live), "History verified, 3,616 earlier snapshots unchanged: tariff
versions 1,396 (+0), snapshots 4,572 (+956), scrape runs 29 (+1)", upload of
`rates-2026-10-16.db.gz` (3,716,941 bytes) and `rates.db` (60,391,424 bytes), bot commit
`ac1b35e`, pruning (nothing to delete) and Deploy Site through `workflow_run`. The first Ontario
Price Archive run (run 38948395749, dispatched October 16) failed closed and wrote nothing
(issue #4): the IESO's `PUB_HourlyLFDA_2026.csv` and `_v1.csv` were empty (0 bytes, last modified
13:21 GMT that day). User decisions (October 16): an empty or unreadable LFDA file keeps stopping
the whole archive run (re-run once the IESO republishes it; the error now says "the IESO published
this file empty"), and the market history build runs even when the archive step fails (a local
market dry run that day passed with no changes). Never exercised: a scheduled run, pruning with
more than 12 backups and the market history build in CI. Deploy Site follows only Monthly Scrape,
and pushes made by a workflow start no other workflow, so a market update from the 15th reaches
the site with the next deployment.

The historical queue below records the October 30 checkpoint. It is superseded by the
November 2 queue above, including the corrected finding that Maritime's demand threshold
was published but discarded by the parser.

A successful scrape or one live residential class does not establish complete
building coverage; counts include optional adjustments and reference records.

| Priority | Utility queue | Next work |
|---|---|---|
| 1. November 1 Monthly Scrape check (runs the batch 15 and 16 code, pushed October 30) | Monthly Scrape as the only database writer passed on October 16 (run #11). The first Ontario Price Archive run failed closed because the IESO published its 2026 LFDA files empty (issue #4); the IESO published the file again on October 30 (13:21 GMT) and local archive and market dry runs pass | Check the scheduled November 1 runs (archive 06:00 UTC, Monthly Scrape 08:00 UTC; do not start a Monthly Scrape earlier): use the local batch 16 kit (`logs/_b16_kit_README.txt`): coverage gate 78 of 78, live 917 (916 if Centra's pages have switched: High Volume Firm's negative transport rider is then rejected); models with the 15.7% rebate, the 2026 share sets and method 7C-3. Then mirror the database and pull; close issues #3 and #4 after a successful archive run. Deploy Site also follows successful archive runs (pushed October 30, user decision). See Next Batches item 1 |
| 1b. Centra and Yukon follow-ups (batch 15 monitor checks) | Centra: the v1126 schedule (PUB Order 150/26, effective November 1, 2026) prints Appendix A as text, not scans; the rate pages still showed August 1 rates on October 30. Yukon: the joint rate book is found only through its hard-coded October address; replaced books are deleted (08- and 09-2026 return 404) | **Done October 30 (batch 16, pushed):** Centra picks the schedule edition from the commercial "Rates effective" date and parses the v1126 text Appendix A at high confidence (user decision); Yukon finds the book through `understanding-rates.model.json`, with the page link and the October address as fallbacks. After the switch: confirm the Centra text path and decide how to read High Volume Firm's negative transport rider (-$0.0018, rejected today); confirm a stored Yukon run uses a newer edition |
| 2. Manitoba Hydro block parser fix (7C blocker) | **Done October 30.** Blocks numbered 1..n with cumulative kWh bounds; phase variants stored as alternatives; "First 50 kVA no charge" a $0 tier (GS Medium had been overcharged $619.50 once tiers were fixed) | GS Medium is computable (single source; 30.4375-day months kept, decided October 30); GS Small (Non-Demand) becomes computable with the reference customer (decided October 30); GS Small (Demand) is in the 50-499 kW band, which has no variant rule. The next Monthly Scrape stores new versions of the two demand classes |
| 3. Decisions (user; decided October 30) | (a) NB Power GS1 and Maritime Electric block thresholds are per "Billing Period", whose length is not stated (`block_periods.json` period `null`); (b) a reference customer for amperage/phase fixed-charge alternatives (Newfoundland Power 1.1, NL Hydro, Manitoba Hydro basic charges); (c) 30-day versus 30.4375-day months (Hydro-Quebec and Manitoba Hydro define a month as 30 days); (d) replacements for dead seed citations (ENMAX Energy and EPCOR Energy Alberta seed `SOURCE_URL` 404, EPCOR Distribution's 301 to a 404, DERS's 301; batch 15 left them unchanged) | **Decided October 30 (batch 16):** (a) per month, because both utilities' billing pages confirm monthly billing (Maritime Electric's seasonal 133/233 stay null); (b) homes single-phase 200 A, under 50 kW single phase at 10 kW and three phase at 25 kW (`usage_levels.json` `fixed_charge_variants`); (c) 30.4375 kept; (d) kept with a "page removed" note in `KEPT_DEAD` (no archived copy shows the values). Method 7C-3 at the October 16 data: NB 0/4/0/0, NL 4/1/0/1, PE 0/1/0/3; still not computable: Manitoba commercial (3), NL commercial <50 kW flat-rate, PE business (3; Maritime Electric 232 prints no demand block thresholds) |
| 4. 7E further analysis | The illustrative synthetic-profile estimate for the Ontario 50-499 kW and 500-4,999 kW models | Compare with real commercial load profiles; test business-hours sensitivity; use an Ontario Price-era hourly shape once 12 archived months exist (August 2027 at the earliest); consider Class A and loss factors. The owner's simulated BTAP archetypes (delivered November 24) replace the made-up profile after the archetype cost tab, with their own decision round. Until then it stays hidden by default, labelled SYNTHETIC and out of medians and comparisons |
| Lane C: Phase 6D market-indexed products | **Done October 30** (stored by the next Monthly Scrape): BC Hydro RS1892 (`1892`); FortisBC Electric RS38 (`38`, pilot to 2028-07-31, medium confidence); NSPower One-Part Real Time Pricing (`RTP-T`, `RTP-D`; adders from scanned pages, user-approved); NL Hydro 5.1L and IND-NONFIRM | Each market energy line is a value-less "Variable" component; six crosswalk rules exclude them from the models (`tests/fixtures/rm_records_ws_6d.json`). NL Hydro's Island thermal non-firm stays source-blocked |
| Lane E: optional items | **Decided October 30 (user):** excluded: DERS RoLR admin charge, ENMAX D700, EPCOR Edmonton local access fee (stays a note), Enbridge Rate 135, ATCO Gas ATA commodity and DERS gas admin charge; kept live: EPCOR Aylmer Rates 2/4/5; Oakville GS<50 stays rejected (source-blocked); Apex Utilities is outside the chosen scope | Recorded as dated exclusions in `data/sources/coverage_ledger.json`. FortisAlberta Rate 65 and ATCO T31 stay live partial records (decided October 9) |
| Lane D: Phase 6C | **Market reference done October 30:** AESO is a live value-less "Variable" pool price record verified against the ETS report and its metadata (the old aeso.ca page 404s) | The Alberta Market Pricing view waits for AESO's written permission (terms: non-commercial, unmodified use). The Alberta 50-499 kW and larger models stay *market energy pending* |
| Done (October 30, batch 15; pushed with batch 16) | Dated model inputs (`tou_shares` effective/end dates; ULO 41/20/26/13 and Ontario Electricity Rebate 15.7% from November 1, 2026); Manitoba Hydro pages moved to `/account/rates/...`; Alberta Rate of Last Resort seed citations now cite the ETS pool price report; `tests/test_source_urls.py` dead-address guard; legacy market generator default `logs/market_pricing_legacy_2020_2024.json`; Deploy Site after successful Ontario Price Archive runs; monitor checks recorded in the coverage ledger | 2,032 tests across 24 modules. Models rebuilt for the committed as-of date are unchanged |
| Done (October 30, batch 16; pushed October 30) | W1 Yukon book discovery through the page model JSON; W2 Centra schedule edition by rates date and the v1126 text Appendix A (high confidence); W3 dead seed citations kept with notes (`KEPT_DEAD`), inventory and AESO pool-price links fixed, guard scans reference data; W4 local check kit (`logs/_b16_kit_*`, untracked); W5 model decisions (method 7C-3) | 2,090 tests across 27 modules. Dry runs: Yukon 20 and 20, Centra 13, Alberta 2/4/5/2 live. Gate 77 of 78 on the committed export (AESO, stored by the next Monthly Scrape) |
| Done (October 15-16) | Lane B (7F site view, October 15); Lane F (EPCOR Energy Alberta's moved pages), CI as the only database writer (first stored run: Monthly Scrape #11, scrape run 29), the Ontario market continuation (rolling 60-month history), Lane A (7C, all ten provinces) and the 7E illustrative sidecar (all October 16) | See Next Batches item 0 |
| Open defaults (the user may change them) | Market history: GA for April-June 2020 (published capped 115 $/MWh, not the unadjusted values); the separate 2021 Class B recovery rates (5.01-7.09 $/MWh, excluded); statutory holidays counted as weekdays. Models: each utility counts once as the median of its standard zones; the 7E synthetic profile (Monday-Friday hours beginning 7-18 EST). | Both market builds use the same GA values and day-type rule; after a change, the archive workflow (or `python scripts/build_ontario_market.py`) rebuilds the rolling history. Known deviation: April 2025 uses the IESO HOEP monthly report value (the yearly hourly file's April mean, 39.181 $/MWh, disagrees with the report's 39.22), so it has no observed hours |
| Planned (order decided November 20, updated November 23 and 24) | Commercial gas models (done November 23 as method 7D-2, with 6E gas supply-price freshness); January 1 readiness (published November 23); the one-year check (built November 24, first review round done the same day); then territorial models (built November 24, method 7T-1); then the Rate History tab (moved ahead of the coverage claim, November 23; built November 24); then the building archetype costs (planned November 24, ahead of the coverage claim), followed by the archetype replacement of the illustrative estimate's profile; then the rest of the Phase 9 product follow-up (the residential Across-Canada comparison is done and never uses illustrative values) | See the current milestone above and Next Batches items 7-10; Phase 8 is completed above |
| Maintain | Centra Gas Mainline Interruptible | Hash-gated reviewed transcription (batch 11) while the rate pages show August 1, 2026 rates; from the November 1, 2026 rates the v1126 text Appendix A is parsed at high confidence (batch 16, row 1b) |
| Monitor | Qulliq final GRA instruction; NTPC Snare TPSP saving mismatch; Centra Appendix A editions; Yukon joint-book file name; EPCOR Distribution final 2026 rates; Oakville GS<50 rejection; Alberta RoLR term end (December 31, 2026) | Checked October 30 (ledger notes): Qulliq, NTPC Snare, EPCOR Distribution (2026 tariffs still interim) and the next Rate of Last Resort term (the UCA table shows only the 2025-2026 term) unchanged, next review December 15; Centra and Yukon changed (row 1b); the Centra monitor was closed November 18 (owner decision) and Yukon's review is December 15. Interim rates stay medium confidence (Qulliq: URRC recommended approval); Snare TPSP omitted until the source reconciles; Oakville GS<50 stays rejected (fail-closed) until its tariff is reissued; RoLR records fail closed after the term until the next term is published. Dates are in the calendar below |
| Source-blocked | See the reconciliation table below, plus ENMAX D700 | Published without printed, dated prices; re-check periodically |

**Calendar:**

- **October 15-16 (done):** scheduled Source Health run #5 and dispatched run #6 passed (October
  15); batch 14 was pushed and Monthly Scrape run #11 stored scrape run 29 (October 16); the first
  Ontario Price Archive run failed closed on an empty IESO LFDA file (October 16).
- **November 1 (done):** scheduled archive/market build, Monthly Scrape and both deployments
  succeeded with the batch 15/16 code already pushed October 30. Stored models use the new
  OEB shares and 15.7% rebate. The pull, mirror and parity check are complete.
- **November 15:** Ontario Price Archive (with the market history build) and Source Health. Risk:
  the IESO table's October LFDA may still be preliminary while the archive holds final values (all
  three monthly checks are strict).
- **November 30 (closed November 18):** Centra stored November correction and HTML-discrepancy
  review. CI storage was verified November 4; after a fresh 13-live dry run from the v1126 PDF the
  owner closed the monitor (November 18). The two HTML differences stay logged; the PDF stays
  authoritative.
- **December 1:** Monthly Scrape; the coverage gate warns `live_expiring` for the eight Alberta
  Rate of Last Resort records.
- **December 15:** monitor reviews for both Yukon utilities, Qulliq, NTPC Snare, EPCOR Distribution and the next Rate of
  Last Resort term.
- **December 31, 2026:** the Alberta Rate of Last Resort fixed term ends; its records fail closed
  until the 2027-2028 term is published and appears in the UCA table.
- **January 1, 2027:** Alberta quarterly riders; Enbridge and EPCOR Ontario QRAM; 2027 tariffs for
  Ontario distributors with January rate years (update their `OEB_TARIFF_DOCUMENTS` entries).
- **May 1, 2027:** 2027 tariffs for Ontario distributors with May rate years.
- **August 2027:** the Ontario Price archive can hold 12 complete months (August 2026-July 2027),
  enough for an Ontario Price-era hourly shape for the 7E analysis. The heatmap's Ontario Price
  share grows by itself as archived months enter the rolling window.
- **No fixed date:** Qulliq final GRA, NTPC Snare TPSP, Centra Appendix A editions, Yukon joint-book
  file name, EPCOR Distribution final 2026 rates, Oakville GS<50 rejection (Monitor row above).

**Decisions (October 7):** BC Hydro RS1828 (biomass-program contract), Hydro-Quebec
Rate F/FP (unmetered) and FortisBC Energy 11RNG are excluded. Territories are reopened for
non-market regulated service. Centra Mainline Interruptible may use a reviewed, hash-gated
transcription; NTPC Taltson retail interruptible heating is implemented as conditional.

**Decisions (October 9):** Alberta transmission (System Access Service) charges are separate
components and current riders separate dated components; EPCOR Distribution's interim rates are
live at medium confidence with a note; transmission-connected ATCO T31 and ENMAX D700 are in
scope only where priced; D22/D24/D34 are out. EPCOR gas is a new Ontario entry and the Alberta
entry is retired. ATCO Gas commodity is Direct Energy Regulated Services' monthly Default Rate
Tariff; priced firm/interruptible gas classes are in, storage/transport-only service is out and
negotiated ranges are conditions. PUC Distribution is configured with a no-connection-rate note.
Market-indexed parts are value-less components. Later on October 9: FortisAlberta Rate 65 and
ATCO T31 stay live partial records (transmission is an AESO pass-through, noted); the Phase 6A
hourly view uses observed legacy HOEP hourly history for 2020-2024 plus actual monthly Class B
Global Adjustment rates, labelled as the market before May 2025; representative models count each
utility once as the median of its standard zones and use the approved usage levels,
reference-customer list and tax defaults.

**Decisions (October 16):** the Monthly Scrape is the only writer of `data/db/rates.db` (the
`data-history` release copy is the master; local copies are read-only mirrors; no local stored
scrapes or manual uploads). Market Pricing shows the latest 60 complete months (legacy HOEP, then
the Ontario Price, plus Class B GA); heatmap option (a): observed hours only, with the May 1,
2025-July 10, 2026 gap disclosed and never filled. 7C: Alberta pairs (ENMAX Power + ENMAX Energy,
ATCO Electric + Direct Energy Regulated Services without its admin charge, EPCOR Distribution +
EPCOR Energy Alberta, FortisAlberta + EPCOR Energy Alberta), the Rate of Last Resort only below
250,000 kWh a year and larger Alberta loads as wires + market energy pending; optional
TOU/peak-event products and pilots outside Ontario out of medians; no assumed unit conversions;
FortisBC "$/two months" halved; reviewed block periods (`data/models/block_periods.json`);
amperage/phase fixed-charge alternatives stay not computable; the Newfoundland and Labrador
residential model is withheld while Newfoundland Power is not computable; per-day energy blocks
x 30.4375. 7E: only an illustrative sidecar from a synthetic business-hours load profile, made
very obviously synthetic (representative only; needs further analysis). October 30 (batch 16):
NB Power and Maritime Electric "per Billing Period" blocks count as per month (their billing pages
confirm monthly billing); phase/amperage fixed-charge variants are priced for a reference customer
(single-phase 200 A home; under 50 kW single phase at 10 kW and three phase at 25 kW); 30.4375-day
months kept; Centra's text Appendix A is high confidence; dead seed citations without an archived
copy are kept with a note.

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
Electric, Yukon Energy, NTPC and Qulliq have saved source-derived fixtures in `tests/fixtures/`,
as do the Ontario OEB tariff sheets (including PUC Distribution) and, from batch 12, ENMAX Power,
ATCO Electric, EPCOR Distribution, FortisAlberta, the Alberta Rate of Last Resort providers,
Enbridge Gas, ATCO Gas and EPCOR Natural Gas (Ontario).
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
| FortisBC Electric | 11 / Oct 6 | Prior 1/2A/20/21/22A/23A/30/32/85 plus RS31 transmission (R-31.1 p65: $4,077.97/month, $6.29/kVA wires, $4.39/kVA power supply, $0.06851/kWh) and RS33 transmission TOU (R-33.1 p67: $3,785.34/month, six seasonal TOU prices); Jan 1, 2026 | RS38 interruptible pilot live since October 30 (Mid-C value-less; 12 live); RS95 source-blocked (BC Hydro RS3808 Tranche 1 price in effect, not printed here). RS37 standby-only and RS96 EV excluded |
| Hydro-Quebec | 26 / Oct 7 | Prior domestic/general-service options, L/LG/H and DR Leeway, plus batch 10 business Demand Response Commitment Option (articles 6.13-6.36, pp83-93: 20 mutually exclusive sub-options, winter fixed and event-hour credits, multi-year/short-notice credits, capped overrun deductions; conditional adjustments to G/M/L/LG); Apr 1, 2026 | F/FP excluded (unmetered); MA absent from edition; Load Retention, Additional Electricity (monthly announced price), closed Economic Development and Industrial Revitalization are not general published prices. GD backup, BR EV and LD/LP auxiliary/standby excluded |
| Manitoba Hydro | 18 / Oct 7 | HTML residential and GS small/medium/large/seasonal, diesel and government/education, plus batch 10 LUBD 2026-50..55 from the approved Jan 1, 2026 schedule (PUB Order 1/26, pp14-16) as conditional alternatives replacing standard GS charges; schedule and page failures are isolated | Curtailable/surplus lack complete published prices; net-billing export credit $0.07173/kWh has no published start date (not live); standard service charges absent from the approved schedule ($150 reconnection fee undated); lighting excluded. Representative models (October 16): the stored commercial blocks are malformed (queue item 2) |
| SaskPower | **41 / Oct 1** | **Audited building schedules implemented**; six source fixtures; total includes reference records | Monitor current sources; no remaining identified building-schedule parser gap in the audited catalogue |
| NB Power | 10 / Oct 6 | Prior HTML classes plus hardened Small Industrial (both energy tiers, 100 kWh/kW threshold and required $/kW demand) and Large Industrial ($19.98/kW/month, $0.0785/kWh; billing-demand alternatives as conditions), Apr 14, 2026 | Net metering and interruptible/surplus prices source-blocked; GS II merged into GS I. Lighting and charging retained as reference. Representative models (October 16): GS I blocks are per "Billing Period" with no stated length (decision 3a) |
| Nova Scotia Power | 18 / Oct 7 | Standard/TOD/conditional pilots, MURB89, two optional solar adjustments; business 10/11/12 and conditional pilots 72/73/82/83; batch 10 Industrial 21/22/23 and Interruptible Rider 25 (book pp40-49, own FAM/DSM/storm rows; conditional distribution cost adder, transformer reduction and -$7.638/kVA interruptible credit) | Pilot restoration status is not assumed; ELIADC and Load Retention contract-specific; One-Part Real Time Pricing RTP-T/RTP-D live since October 30 (hourly energy value-less; adders from scanned pages, user-approved, medium confidence; 20 live); municipal wholesale, shore power and standby excluded; unsupported 2027 dates fail closed |
| Maritime Electric | 10 / Oct 7 | IRAC N-28 PDF plus Section N rates page (dates must match); building classes and Small/Large Industrial 320/310 audited complete (billing-demand rules as conditions; 310 losses/transformation charges conditional) | 330/340 are Summerside wholesale, retained as reference; no curtailable credit published; lighting/unmetered/short-term excluded. Representative models (October 16): blocks are per "Billing Period" with no stated length (decision 3a) |
| Newfoundland Power | 11 / Oct 6 | Prior RateBook classes plus Curtailable Service Option 1 for 2.3/2.4 (conditional -$29/kVA May credit, pp30-31) and Domestic 1.1 net metering (conditional -$0.15587/kWh generation credit, pp24, 32-34) | Option 2 load-factor formula, GS/seasonal net-metering credits unmodelled; annual settlement unpriced. Representative models: since October 30 Domestic 1.1's basic charge is priced for a single-phase 200 A home (decision 3b), so the Newfoundland and Labrador residential model is no longer withheld |
| NL Hydro | 21 / Oct 6 | Prior July Island/Labrador/diesel classes plus Island Industrial Firm (pp9-10, $/kW/month, $/kWh, riders and conditional named-customer charges), Labrador Industrial Firm (pp62-65, conditional 2026 $/MWh blocks, no blended price), and Net Metering Service Option (pp67-70, conditional credit at applicable class energy rate, not standalone price) | Rate 5.1L and Island Industrial Non-Firm (non-thermal) live since October 30 (value-less monthly market-indexed energy; 23 live); Island thermal non-firm source-blocked (fuel formula, no printed price); Wheeling (p13) excluded as transmission service. CP transmission commissioning and UT wholesale excluded |

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
energy plus tariff delivery charges. Demand classes (GS 50-4,999 kW and Large Use) carry tariff
delivery charges plus, since batch 12, a value-less market energy component (Phase 6B, below);
the observed market history (Phase 6A; the rolling 60 months since October 16) is shown only in
the Market Pricing view, never stored in a tariff.

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
labelled estimate. **PUC Distribution** stayed unconfigured in batch 2 (its tariff prints only a
network transmission rate, no connection rate; user decision October 8); it was configured on
October 9 (below).

A scratch representative model (October 8; median of each distributor's default-zone record)
showed typical monthly delivery varying about 15-20% (CV ~0.18) for Residential, GS<50 and GS
50-4,999 kW, with Hydro One the main high outlier. It was superseded by the Phase 7 models
(published for Ontario since October 9 and for all ten provinces since October 16).

Rejected classes get no new estimate (decision October 7: follow live sources); older estimates
stored earlier remain in history, labelled as estimates and hidden by default. Every failure is
per class (fail-closed).

**Confirmed decisions (October 7):** the open-GS rule above. Hydro One Seasonal: the R2 page
prints a Seasonal service charge ($92.43) beside the year-round charge ($151.14); Seasonal
records use it with R2's shared lines and no RRRP credit, while year-round R2 records show the
RRRP credit (-$60.50) as conditional. Seasonal properties in UR/R1 areas use the UR/R1 records.
The R2 Distribution Rate Protection cap is not modelled.

### PUC Distribution and market energy (October 9, 2026; batch 12)

| Distributor | Live / seed | Notes |
|---|---|---|
| PUC Distribution | 7 / 1 | Residential TOU/Tiered/ULO, GS<50 TOU/Tiered/ULO and GS 50-4,999 kW (delivery charges plus value-less market energy); labelled Street Lighting estimate. Configured with `"connection_rate": "not_printed"` (user decision October 9): the approved tariff (EB-2025-0012) prints no Retail Transmission Connection Service Rate, and each record carries a note. All other documents stay strict |

Total: **490 live records across all 47 active distributors** (scrape run 27, October 9, 2026,
which re-stored every distributor). Phase 6B: non-RPP demand classes (GS 50-4,999 kW and its
sub-ranges, open-ended GS 50 kW and over, Large Use, Hydro One UGd/GSd/AUGd/AGSd and ST) carry
"Market Energy (Ontario Electricity Market Price + Class B Global Adjustment)" with no stored
value, a market reference and the IESO source URL (the site shows "Variable"); `pricing_method` is
market_based. The HOEP was retired April 30, 2025; since May 1, 2025 the Ontario Electricity
Market Price is the Day-Ahead Ontario Zonal Price plus the Load Forecast Deviation Adjustment.
Class A Global Adjustment (peak demand factor) and the O. Reg. 95/05 s. 4(2) RPP-eligibility
caveat are conditional notes. Algoma R2 has no market component (residential dwelling accounts
remain RPP-eligible).

**Remaining Ontario:** no active distributor is unconfigured. The Market Pricing view shows
observed market history only (Phase 6A on October 9; since October 16 the rolling 60 months of
legacy HOEP, then the Ontario Price, plus Class B GA); tariff market energy stays value-less. The
hourly Ontario Price has been archived since October 15. The Ontario demand-class models stay
*market energy pending*; 7E adds only an illustrative synthetic-profile estimate beside them.

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

Gas entries are tracked once in the next section. Batch 12 (scrape run 27, October 9) made the
four wires utilities and the three Rate of Last Resort providers live, each with a saved
source-derived fixture (`tests/fixtures/enmax_power.json`, `atco_electric.json`,
`epcor_distribution.json`, `fortisalberta.json`, `alberta_rolr.json`). Transmission (System Access
Service) charges are separate components; current riders are separate dated components, and an
expired rider is excluded by its date. kVA limits stay in eligibility text.

| Utility | Live tariffs / source-check date | Implemented path | Required work |
|---|---|---|---|
| ENMAX Power | 5 / Oct 9 | D100 Residential, D200 Small Commercial, D300 Medium Commercial, D310 Large Commercial Secondary and D410 Large Commercial Primary from the current Distribution Tariff Rate Schedule (rates in effect October 1, 2026; DAS and SAS rates AUC Decision 30299-D01-2025, effective January 1, 2026). Balancing Pool Allocation, quarterly TAC Adjustment (Q4 2026) and TAC Deferral Account riders dated; D300 transformation credits conditional; Calgary Local Access Fee a note | D700 transmission-connected source-blocked (only a service charge printed; transmission is an ISO cost flow-through); partial-record decision open. D500 streetlights and D600 distributed generation excluded. New schedule edition each quarter |
| ATCO Electric | 5 / Oct 9 | D11 Standard Residential, D13 Time of Use Residential (by request; on-peak 4-9 p.m.), D21 Standard Small General Service (up to 500 kW), D31 Large General Service - Distribution Connected, T31 Large General Service - Transmission Connected from the 2026 price schedules (AUC Decision 30300-D01-2025). Rows must reconcile to each printed TOTAL PRICE; Riders B, G and S (Q4 2026) dated and cross-checked against the copies bound into the price schedules; Rider J expired (note); Rider A municipal and price options F/H/P are notes | T31 transmission is an AESO tariff flow-through, noted without a component; T31 stays a live partial record (user decision, October 9). Excluded: D22, D23, D24/D34, D25/D26, D32, D33/T33, D41/D44, D51/D52/D56, D61/D63 |
| EPCOR Distribution | 5 / Oct 9 | DAS-R, DAS-SC (<50 kVA), DAS-MC (50 to <150 kVA), DAS-TOU (150 to <5,000 kVA secondary), DAS-TOUP (primary, 150 kVA and over) from the 2026 DAS and SAS tariffs stamped "2026 INTERIM RATE": medium confidence with an interim note (user decision). Values must match the tariffs' lookup tables; Riders G, J and K (October 2026) dated; SAS operating reserve (8.09% of the AESO pool price; 7.99% for TOUP) is a value-less market component | Final rates after the interim approval. Edmonton local access fee ($0.01388/kWh) is a note; conditional-rider decision open. Excluded: CS/CST (closed, customer-specific), DC (AESO flow-through), DGEN, lighting |
| FortisAlberta | 5 / Oct 9 | Rates 11 Residential (existing identity kept), 41 Small General Service, 61 General Service, 63 Large General Service and 65 Transmission Connected from the newest in-effect Rates, Options and Riders PDF (October 1, 2026; link date must match the printed effective date). Transmission and distribution separate; kW/kVA demand pairs alternatives; Base Transmission Adjustment, Quarterly Transmission Adjustment and Balancing Pool Allocation riders dated; Options A/I conditional; municipal riders notes; Rate 65 transmission is the AESO tariff passed through (value-less) | Rate 65 stays a live partial record (user decision, October 9). Excluded: farm 21/22/23, irrigation 26, lighting 31/33/38, oil and gas 44/45, EV 62, opportunity 66, distributed generation (Option M), Rider E, REA charges. Old D10/D20/D30 seeds are no longer emitted when live |
| Direct Energy Regulated Services | 2 / Oct 9 | Rate of Last Resort for the ATCO Electric area: residential and small business at 12.02 cents/kWh, fixed January 1, 2025 to December 31, 2026; UCA default-rates table required | Daily administration charge not emitted (website value undated; last dated schedule differs); decision open. Next term after December 31, 2026 |
| ENMAX Energy Corporation | 2 stored, 4 in the Nov 25 dry run / Nov 25 | Rate of Last Resort for the ENMAX Power area: D100/D200 at 12.06 cents/kWh plus daily administration charges from the Interim 2026 rate schedule (medium confidence); UCA table required. Since November 25 (owner decision 102) the scraper also reads the Medium (D300) and Large (D310/D410) Commercial schedules (same prices, sites under 250 MWh a year), which the representative models pair with ENMAX Power D300 and D310 | The next Monthly Scrape stores the two new records. Municipally set RoLR areas (Cardston, Ponoka) not covered; Red Deer's (provided by ENMAX Energy) is stored with the City from batch 18 continued. Next term after December 31, 2026 |
| EPCOR Energy Alberta | 4 / Oct 9 (dry run Oct 16) | Rate of Last Resort for the EPCOR Distribution and FortisAlberta areas: residential and small business (250,000 kWh/year limit) per area at 12.01 cents/kWh plus each area's administration charge from price schedules effective July 1, 2026; UCA table required | Pages moved (the FortisAlberta-area residential page returned 404 from October 15): fixed October 16 (Lane F) with the new `.../start-services/home/compare-electricity-rates/rate-of-last-resort.html` addresses in the registry, scraper and fixture; dry run 4 live, 0 seed; stored by CI scrape run 29 (October 16). REA price schedule not covered. Next term after December 31, 2026 |
| Alberta Electric System Operator | 0 | Seed/market reference | Dated official pool-price observations with published units and cadence (Phase 6C) |
| City of Medicine Hat Electric Utility | 5 / Nov 19 | Bundled City records: 2026 Utility Rates brochure delivery charges (read column by column) plus the monthly default rate (current month's row required) and Going Green surcharge for 1.1/3.1/3.3, or the fixed 2025-2026 rate for 4.1/5.1; each record ends with its shortest-lived price | The Monthly Scrape on the 4th stores the month's row (the run on the 1st usually comes first and fails closed); an owner's run only if the City posts later. 3.1/3.3 class limits unpublished (not modelled). Next large-customer fixed rate after December 31, 2026 |
| City of Lethbridge Electric Utility | 8 / Nov 19 | Bylaw 6364 rate codes 991-997 checked against the 2026 Rate Table by column; Riders B and C dated; the City's 2026 Rate of Last Resort (9.975 cents/kWh) | "RDS" price undefined (not stored); Rider A a note. Next Rate of Last Resort price after December 31, 2026 |
| City of Red Deer Electric Light & Power | 8 / Nov 19 | Schedule A rates 61/63/64/78 matched to the delivery page; quarterly Transmission Rider; Rate of Last Resort records with the term's 12.06 cents/kWh and Schedule D's $0.3035/day administration charge | The Rate of Last Resort page still shows $0.2498/day (noted). Next term after December 31, 2026 |

The Rate of Last Resort replaced the Regulated Rate Option on January 1, 2025. Prices are fixed
to December 31, 2026 and must match the Utilities Consumer Advocate default-rates table (shared
helper `scrapers/utils/alberta_rolr.py`); records fail closed after the term ends until the next
term is published. Old RRO seeds remain labelled history. Keep wires, retail and wholesale
references separate; never add them into one price.

## Natural Gas

Latest live gas records: SaskEnergy 8, Centra Gas 13, FortisBC Energy 27, Energir 5,
Heritage/Eastward 3 and Liberty NB 4 and, from batch 12 (scrape run 28, October 9), Enbridge Gas
20, ATCO Gas 10 and EPCOR Natural Gas (Ontario) 10, all with source-derived fixtures. The Alberta
"EPCOR Natural Gas" entry is retired (mis-registration; history kept). No gas utility is yet
certified complete for its published building catalogue.

| Registry utility | Region / campaign | Latest live records | Implemented path and remaining work |
|---|---|---|---|
| Enbridge Gas | ON / live (batch 12), partial catalogue | 20 / Oct 9 | Rate Handbook (EB-2026-0221, effective October 1, 2026): EGD Rates 1/6/100/110/115/145/170; Union North Rates 01/10/20/100 for the North West and North East zones plus Rate 25; Union South Rates M1/M2/M4/M5. Customer charges, block delivery charges in $/m3, contract demand, quarterly gas supply (QRAM) commodity and transportation, Rider C, Rider J federal carbon (zero, with CRA evidence) and the facility carbon charge are separate components; Rider I expansion surcharges and marketer-only Dawn transportation conditional; negotiated prices/ranges are conditions. A PDF split-digit text artefact is repaired and tested. Excluded storage/transport-only, unbundled and wholesale service: EGD 125/135/200/300/315/316/320/401; Union M7/M9/T1-T3 (Rate 135 decision open) |
| Énergir | QC / live, partial catalogue | 5 / Oct 6 | D1/D3/D4 plus interruptible D5 (Oct 1 CST p62 distribution bands $/m3, pp63-65 interruption/minimum volume; Category A/B load-balancing alternatives p49 conditional and non-additive). Supply and cap-and-trade prices from the monthly supply-price page with its price history workbooks (from November 20; supply to month end, cap-and-trade to quarter end; a month not yet posted leaves supply out). Optional RNG supply $0.85239/m3 (p38) replaces ordinary supply on D1/D3/D4/D5; missing RNG does not suppress base records. Inventory adjustments customer-specific and unpriced. Load-factor formula p49 published but not computed; fixed-price supply supplier-specific and D5 make-up gas pass-through unpriced |
| FortisBC Energy | BC / live, partial catalogue | 27 / Oct 7 | Rates 1/2/3 for Mainland/Vancouver Island and Fort Nelson (July 1, 2026; $/day basic, $/GJ components) with the BC carbon-tax elimination notice required; Rate 5 General Firm Service (basic $469.00 per month as the tariff prints it) and seasonal Rate 4 (Apr 1-Nov 1) for Mainland/Vancouver Island from the approved schedules. Residential Rate 1 and Commercial Rates 2/3 Revelstoke propane (business classes require the approved tariff index's Revelstoke availability plus residential propane evidence; each class fails independently). Batch 10: Rate 7 General Interruptible ($880/month as printed; curtailment-limited delivery; Sumas-indexed overrun as a condition) and delivery-only transportation 22/23/25/27 (marketer commodity excluded; Rate 22 firm/interruptible charges conditional). Rates 6/6P/26 NGV and 22A/22B excluded. Fort Nelson 4/5/7/22-27 have no published price table. Batch 11: Customer Choice 1U/2U/3U (delivery-only; not offered in Fort Nelson) and RNG 1RNG/2RNG/3RNG (Mainland/VI and Fort Nelson) plus 5RNG/7RNG, with Cost of Gas and RNG Charge as conditional alternatives on the chosen share; RNG Blend Service percentage unpublished; 11RNG and vehicle RNG excluded |
| ATCO Gas | AB / live (batch 12), partial catalogue | 10 / Oct 9 | North and South Low, Mid, High and Ultra High Use and ATA from the rate schedule PDFs (base January 1, 2026, AUC Decision 30301-D01-2025); Riders L and T and South Rider W dated; Direct Energy Regulated Services' monthly Default Rate Tariff (October 2026: $1.458/GJ) as a dated commodity on Low/Mid/High Use, required to match the UCA table; CRA zero-carbon evidence; Riders A/B and South Rider E notes. Excluded: irrigation, producer receipt, unmetered gas lights. Open: ATA commodity and DERS gas admin charge |
| EPCOR Natural Gas (Ontario) | ON / live (new entry, batch 12), partial catalogue | 10 / Oct 9 | Aylmer Rates 1 (residential and general service), 2, 3, 4, 5 and Southern Bruce Rates 1 (residential and commercial), 6, 11. Every value must appear in the OEB Decision and Rate Order Appendix A (EB-2026-0225 / EB-2026-0226); the gas supply price must match the OEB QRAM notice; CRA evidence required. No seed: returns nothing if sources fail. Excluded: Aylmer Rate 6 (single ethanol facility), Southern Bruce Rate 16 (direct purchase; rider basis unclear). Open: Aylmer Rates 2/4/5 inclusion |
| EPCOR Natural Gas | AB registry entry / retired | 0 | Retired October 9: mis-registration (EPCOR does not distribute gas in Alberta). Skipped by monthly runs; stored seed history kept. Apex Utilities, an Alberta gas distributor, is not registered (open question) |
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
| Naka Power Utilities (NWT) | 6 / Nov 19 | PUB July 1, 2026 Rate Schedule found from both zone tabs: Snare residential/GS, Taltson residential/GS/LGS, Thermal residential; base rows reconciled to each total; dated riders per zone (percentages and the Yellowknife franchise tax as `%`); TPSP and GREP conditional alternatives; interim riders at medium confidence | Thermal GS source-blocked (printed demand charge and total disagree); Cost of Living Subsidy has no published value; final 2026-2028 GRA rates (review December 15) |

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
| BC Hydro | 18 | RS1828 biomass contract; RS1823 cancelled; irrigation, lighting, EV, IPP, wholesale/reseller, standby | RS1289 indexed cash settlement | RS1892 now live (Mid-C, value-less) |
| FortisBC Electric | 12 | RS37 standby; RS96 EV; RS91 financing | RS95 (references BC Hydro RS3808 Tranche 1, not printed) | RS38 now live (Mid-C, value-less) |
| Hydro-Quebec | 26 | F/FP unmetered; GD backup; BR EV; LD/LP auxiliary/standby; Load Retention, Additional Electricity, Economic Development (closed), Industrial Revitalization; MA not in edition | - | - |
| Manitoba Hydro | 18 | Lighting | Curtailable and surplus programs; net-billing credit (no start date); service charges (not in approved schedule; $150 reconnection undated) | - |
| SaskPower | 41 | Lighting, reseller (farm/oil-field retained as reference) | - | - |
| NB Power | 10 | Lighting/charging retained as reference; one-time fees (labelled $/month) | Net metering ($ value), interruptible/surplus (unpublished hourly incremental cost) | - |
| Nova Scotia Power | 20 | ELIADC, Load Retention, municipal wholesale, shore power, standby, generation replacement/load following | Pilot participant restoration status | One-part real-time pricing now live (RTP-T, RTP-D) |
| Maritime Electric | 10 | 330/340 Summerside wholesale (reference); lighting, unmetered, short-term | - | - |
| Newfoundland Power | 11 | Lighting | Curtailable Option 2 (customer load-factor formula); GS/seasonal net-metering credits (class rate, no value) | - |
| NL Hydro | 23 | CP commissioning; UT wholesale; Island Industrial Wheeling; lighting | Island thermal non-firm (fuel formula) | 5.1L and Island non-thermal non-firm now live (value-less monthly market-indexed energy) |
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

0. **Done.** Batch 12 (October 9): Alberta wires and Rate of Last Resort, ON/AB gas (Enbridge, ATCO
   Gas, EPCOR Natural Gas (Ontario)), PUC Distribution (all 47 active Ontario distributors live)
   and Phase 6B value-less market energy. The per-run live/seed summary, Phase 7A/7B and Phase 6A
   (observed legacy market history) followed the same day (items 7 and 8). October 15: CI fixes,
   the Ontario Price archive and **Lane B, Phase 7F**: the Representative Models tab next to Rate
   Browser, Market Pricing and Compare reads `site/data/representative_models.json` for whichever
   provinces it contains (selectors, a table with range bars, tax lines, method and coverage
   disclosure); desktop (1365 px) and phone (390 px) checks passed with no JavaScript errors.
   October 16 (batch 14): **Lane F** (`a919684`: EPCOR Energy Alberta's moved Rate of Last Resort
   pages; dry run 4 live, 0 seed), **CI as the only writer of the history database** and the
   **rolling five-year Ontario market history** (`b070725`), and **Lane A, Phase 7C** for all ten
   provinces with the **7E illustrative sidecar** (`49a0daa`); exact float sums (`a89e436`); the
   first stored CI scrape (Monthly Scrape #11, scrape run 29); 1,867 tests across 14 modules.

**Coverage-complete plan (October 30, user decisions).** Goal: the README may say live-rate coverage
is complete. Scope: the 78 active registered utilities (not every Canadian utility); depth: live
output for main building classes with every exclusion, source-blocked and deferred item written
down; AESO (6C) and the four 6D products must be done first; representative-model gaps do not
block. `python scripts/coverage_gate.py` is the measure, reading `data/sources/coverage_ledger.json`
(workstreams 0 and 1 done October 30: all 78 active utilities have a ledger audit). Workstream 1 evidence: a dry run of all 47 Ontario distributors
(date set to 2026-11-01, see the calendar note below) gave 490 live records equal to the stored
export with one real class gap, Oakville GS<50 (its approved tariff prints the LRAM rider as
$/kW on an energy-billed class), and Algoma's by-design absent GS classes; dry
runs of the ten Alberta and gas utilities matched the class inventories above. **Workstreams 2-5
were completed the same day (October 30):** the Manitoba Hydro block fix, the four Phase 6D
market-indexed products, the AESO live market reference (option A; the Alberta Market Pricing view
needs AESO's written permission) and the Lane E and Oakville decisions (all excluded or kept; user).
The committed export lacks the new records, so the gate reads 77 of 78 (AESO) until the Monthly
Scrape stores them; with them included it reads 78 of 78. **Remaining:** (6) after the November 1
scheduled scrape stores the new records, re-run the gate on the new export, then the November 15
runs and the December 31 Rate of Last Resort term end (the gate warns 30 days before records
expire); (7) the README flip and a final documentation review.

**Calendar note (found October 30):** the OEB RPP page already lists prices effective November 1,
2026, and the Ontario parser rejects an RPP page dated in the future. Until November 1 a scrape
builds no Residential or GS<50 records for any Ontario distributor (the stored versions stay the
latest; nothing is lost). Do not start a Monthly Scrape for Ontario before November 1; the
scheduled November 1 run (08:00 UTC) is unaffected. The November 1 TOU/ULO share update in
`data/models/usage_levels.json` is still manual.

Items 1-6 follow the order agreed on October 16. Independent work may proceed in parallel; shared
registry, crosswalk, database, export and documentation changes are integrated serially in this
order.

1. **Ontario Price Archive re-run (owner).** Monthly Scrape passed every step on October 16
   (run #11; see the CI paragraph above). The first Ontario Price Archive run failed closed because
   the IESO published its 2026 LFDA files empty (issue #4). Once the file is non-empty again, start
   Ontario Price Archive by hand (archive commit, then the market history build and its commit;
   the build now also runs when the archive step fails); otherwise it runs on November 1. Verify
   the commits through the public API and close issues #3 and #4. Open question for the owner:
   should Deploy Site also follow the archive workflow, so the 15th's market update is published?
   Never upload a database by hand; local copies come from
   `python scripts/pull_history_db.py`.
2. **Manitoba Hydro block parser fix (done October 30; stored by the next Monthly Scrape).** The stored commercial energy blocks are malformed (tier
   numbers 1 and 3; "Next 8,500 kWh" stored as a cumulative bound; single- and three-phase basic
   charge variants), so three Manitoba commercial models are not computable. Fix the parser and its
   fixture, then rebuild and re-check the models (0 unmapped, Ontario unchanged).
3. **Decisions (user; decided October 30, batch 16, see queue row 3).** The length of NB Power GS1's and Maritime Electric's "Billing Period"; a
   reference customer for amperage/phase fixed-charge alternatives; 30-day versus 30.4375-day
   months (Hydro-Quebec and Manitoba Hydro define a month as 30 days).
4. **7E further analysis.** Real commercial load profiles, business-hours sensitivity, an Ontario
   Price-era hourly shape once 12 archived months exist, Class A and loss factors. The illustrative
   estimate stays out of medians, outliers, closest utility, Phase 8 and Phase 9.
5. **Remaining lanes.** **C (Phase 6D):** BC Hydro RS1892 (freshet energy, Mid-C index), FortisBC
   Electric RS38 (Mid-C index), NSPower one-part real-time pricing and NL Hydro monthly non-firm
   prices (5.1L, Island non-thermal) become value-less "Variable" components with a market reference
   and source URL, as for Ontario demand-class market energy (6B); no averaged or guessed number
   goes into a tariff. **E:** optional items, each after a yes/no decision (details in the Lane E
   queue row). **D (Phase 6C):** AESO pool price history; research the official data source first.
   Rate of Last Resort fixed prices are already live (5F) and EPCOR Distribution's operating reserve
   charge is stored value-less. An optional Alberta region in the Market Pricing dashboard, only if
   its variation warrants it, follows 6C.
6. **Calendar.** November 1: new OEB RPP prices (the 2026 TOU/ULO share sets are already dated in
   `data/models/usage_levels.json`, batch 15). November 15: Ontario Price Archive and Source
   Health.

Every lane milestone needs the acceptance checks at the end of this section where they apply. New
live records also need crosswalk rules: after export,
`python -m pipeline.representative_models --coverage` must report 0 unmapped.

7. **Phase 6: Market Integration** ([README](../README.md#roadmap)):
    6B (Ontario demand-class energy) is implemented as value-less components (batch 12). **6A is
    done.** October 9: `scripts/generate_market_pricing.py` replaced the fixed model inputs with
    observed legacy HOEP hourly history for 2020-2024 plus actual monthly Class B Global Adjustment
    rates (user decision October 9), cross-checked against the IESO HOEP Monthly Averages report
    (60 months) and failing closed. The IESO keeps only about 90 days of hourly day-ahead zonal
    price files, so `scripts/archive_ontario_price.py` and the Ontario Price Archive workflow keep
    them from October 15 (hourly from July 11, 2026; every complete month must match the IESO
    monthly table for DA-OZP, LFDA and OEMP). The October 15 comparison found what Class B
    customers pay (energy + GA) similar before and after May 2025 while energy alone is not, so
    October 16 added the rolling five-year history (`scripts/build_ontario_market.py`, run by the
    archive workflow): the latest 60 complete months (September 2021-August 2026 on October 16;
    10.40 cents/kWh on average), a permanent monthly CSV since January 2020 and a heatmap from
    observed hours only. Open defaults are in the queue. Still planned: Alberta market and
    the conditional Alberta Market Pricing region (6C, Lane D), the deferred market-indexed
    products (6D, Lane C) and the rest of gas commodity cadence (6E; current QRAM and
    default-supply prices are already dated commodity components). Every market price needs an
    official source, period and freshness date.
8. **Phase 7: Representative Models** ([README](../README.md#roadmap);
    sub-phases 7A-7F). One modeled tariff per province, sector and offered rate structure: median
    across utilities, single-source where only one utility exists, all-in energy from Phase 6, its
    own site view and generated method statements. Decided: prices without and with tax; a model per
    common usage level; major outliers named with their deviation, no "excluding" variants;
    provinces first, then the territories (method 7T-1, November 24, 2026); each utility counts
    once as the median of its standard zones. **7A and 7B were done for Ontario on October 9 and 7C on October 16:**
    `data/models/crosswalk.json` (240 ordered rules with Alberta `pairs` and
    `required_contributors`; 557 of 910 latest live records mapped, 353 excluded with reasons, 0
    unmapped), `usage_levels.json` (user-approved levels, a reviewed reference-customer list and the
    7E synthetic profile), `block_periods.json` (21 reviewed entries), `taxes.json` and the engine
    `pipeline/representative_models.py` (method 7C-2; 7C-3 since October 30), which every export runs to write
    `site/data/representative_models.json` for the ten provinces (and the three territories since
    November 24; labelled modeled, never live
    coverage; shown on the Representative Models tab, 7F). 55 models: 16 modeled, 20 single-source,
    6 *market energy pending* (Ontario and Alberta demand classes), 13 not computable (Manitoba
    commercial, NB Power GS1, Maritime Electric, Newfoundland and Labrador residential and small
    commercial). With the October 30 decisions (7C-3): 18, 24, 6 and 7 (not computable: Manitoba
    commercial, Maritime Electric business, Newfoundland and Labrador flat-rate small business).
    7E is only an illustrative synthetic-profile sidecar on the two Ontario demand
    models (hidden by default; never in medians or comparisons). Next: 7D gas; a source-backed 7E
    needs further analysis (Ontario) and 6C (Alberta).
9. **Phase 8: Representative Model Refresh Automation** ([README](../README.md#roadmap)):
    Implemented and verified locally, in CI and on the deployed site. The existing builds produce
    explicit receipts and a public change history; a reusable non-blocking job checks inputs,
    source results and refresh cadence. No additional daily job or database writer. Details:
    [model policy](../.github/instructions/representative-models.instructions.md#change-monitoring-phase-8-owner-decision-2026-11-17)
    and [workflow rules](../.github/instructions/ci-data-history.instructions.md#model-monitoring).
10. **Phase 9: Product Follow-up** ([README](../README.md#roadmap)):
    historical charts (the Rate History tab, owner decisions of November 23 and 24, built November 24
    ahead of the coverage claim) and the Across-Canada comparison view built on the Phase 7 models
    (done for residential electricity; it never uses illustrative values) are done. A cost comparison
    of simulated building archetypes (owner decisions of November 24) is planned next, ahead of the
    coverage claim. AI exports and calculator/API scoping remain roadmap items, not implemented
    features.
11. **Monitoring and maintenance:** the campaign's priced, dated gaps are closed (batch 11).
    Monitor the queue's Monitor row and the calendar (Qulliq final GRA instruction, NTPC Snare TPSP
    reconciliation, Centra Appendix A edition changes, monthly Yukon joint-book file name, EPCOR
    Distribution final 2026 rates, Oakville GS<50 rejection, Alberta RoLR term end). Re-check
    source-blocked items periodically (reconciliation table). Audit remaining building catalogues
    and fixtures, maintain SaskPower's audited building schedules, then run a full refresh and
    class-level reconciliation that now includes the Alberta and ON/AB gas utilities (their
    exclusions and open questions are in their tables above).

Each batch requires source-derived positive/negative tests, a source-inspected dry run,
validated storage/export, preserved history and a ledger update. Record observation dates
separately from parser capability, keep unsupported classes visible, and never delete a
database or invent rates to make completion metrics look better.

## History

Dated checkpoints and batch history are kept in the maintainer's local, git-ignored history
file. Earlier published versions of this matrix, including its former history sections,
remain in git history.
