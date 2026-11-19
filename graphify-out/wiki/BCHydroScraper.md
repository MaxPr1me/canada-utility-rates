# BCHydroScraper

> 50 nodes

## Key Concepts

- **extract_effective_date()** (26 connections) — `scrapers/utils/parsing.py`
- **BCHydroScraper** (25 connections) — `scrapers/utilities/bc_hydro.py`
- **.now_iso()** (19 connections) — `scrapers/base.py`
- **._try_live_scrape()** (19 connections) — `scrapers/utilities/bc_hydro.py`
- **._try_live_scrape()** (17 connections) — `scrapers/utilities/saskpower.py`
- **SaskPowerScraper** (16 connections) — `scrapers/utilities/saskpower.py`
- **._parse_business_tariff()** (10 connections) — `scrapers/utilities/bc_hydro.py`
- **._numbered_section()** (9 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_residential_schedules()** (9 connections) — `scrapers/utilities/saskpower.py`
- **._parse_transformation()** (9 connections) — `scrapers/utilities/saskpower.py`
- **._parse_residential_pdf()** (8 connections) — `scrapers/utilities/saskpower.py`
- **._parse_farm_rates()** (8 connections) — `scrapers/utilities/saskpower.py`
- **._parse_supplied_services()** (8 connections) — `scrapers/utilities/saskpower.py`
- **._parse_freshet_energy()** (7 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_net_metering_tariff()** (7 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_residential_options()** (7 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_residential_tariff()** (7 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_transmission_pilots()** (7 connections) — `scrapers/utilities/bc_hydro.py`
- **._tariff_document()** (7 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_standard_charges()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_business()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_community_generation_tariff()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_self_generation_tariff()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_transmission_tariff()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **._column_values()** (6 connections) — `scrapers/utilities/saskpower.py`
- *... and 25 more nodes in this community*

## Relationships

- [TariffRecord](TariffRecord.md) (33 shared connections)
- [BaseScraper](BaseScraper.md) (20 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (20 shared connections)
- [DocumentPage](DocumentPage.md) (17 shared connections)
- [.fetch_page](fetch_page.md) (7 shared connections)
- [.mark_fallback](mark_fallback.md) (4 shared connections)
- [.__init__](__init__.md) (2 shared connections)
- [._parse_building_extras](_parse_building_extras.md) (1 shared connections)
- [ntpc.py](ntpc.py.md) (1 shared connections)
- [graphify_hook.py](graphify_hook.py.md) (1 shared connections)
- [NewfoundlandPowerScraper](NewfoundlandPowerScraper.md) (1 shared connections)
- [re](re.md) (1 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/bc_hydro.py`
- `scrapers/utilities/saskpower.py`
- `scrapers/utils/parsing.py`

## Audit Trail

- EXTRACTED: 201 (97%)
- INFERRED: 6 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*