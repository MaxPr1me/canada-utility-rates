# BCHydroScraper

> 61 nodes

## Key Concepts

- **RateComponent** (257 connections) — `scrapers/base.py`
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
- *... and 36 more nodes in this community*

## Relationships

- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (61 shared connections)
- [BaseScraper](BaseScraper.md) (38 shared connections)
- [RateComponent](RateComponent.md) (26 shared connections)
- [DocumentPage](DocumentPage.md) (25 shared connections)
- [.fetch_page](fetch_page.md) (22 shared connections)
- [FortisBCEnergyScraper](FortisBCEnergyScraper.md) (13 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (12 shared connections)
- [fortisalberta.py](fortisalberta.py.md) (11 shared connections)
- [re](re.md) (10 shared connections)
- [NewfoundlandPowerScraper](NewfoundlandPowerScraper.md) (10 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (8 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (8 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/bc_hydro.py`
- `scrapers/utilities/nova_scotia_power.py`
- `scrapers/utilities/ontario_ldc.py`
- `scrapers/utilities/saskpower.py`
- `scrapers/utils/parsing.py`

## Audit Trail

- EXTRACTED: 407 (88%)
- INFERRED: 54 (12%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*