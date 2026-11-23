# BCHydroScraper

> 57 nodes

## Key Concepts

- **TariffRecord** (423 connections) — `scrapers/base.py`
- **BCHydroScraper** (25 connections) — `scrapers/utilities/bc_hydro.py`
- **._try_live_scrape()** (19 connections) — `scrapers/utilities/bc_hydro.py`
- **AESOScraper** (10 connections) — `scrapers/utilities/aeso.py`
- **._parse_business_tariff()** (10 connections) — `scrapers/utilities/bc_hydro.py`
- **TorontoHydroScraper** (9 connections) — `scrapers/utilities/toronto_hydro.py`
- **._numbered_section()** (9 connections) — `scrapers/utilities/bc_hydro.py`
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
- **.scrape()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **._seed_data()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **.scrape()** (5 connections) — `scrapers/utilities/aeso.py`
- **.scrape()** (5 connections) — `scrapers/utilities/enbridge_gas.py`
- **.scrape()** (5 connections) — `scrapers/utilities/enmax_energy.py`
- **.scrape()** (5 connections) — `scrapers/utilities/epcor_energy_alberta.py`
- **.scrape()** (5 connections) — `scrapers/utilities/heritage_gas.py`
- *... and 32 more nodes in this community*

## Relationships

- [fortisbc_electric.py](fortisbc_electric.py.md) (42 shared connections)
- [BaseScraper](BaseScraper.md) (41 shared connections)
- [RateComponent](RateComponent.md) (35 shared connections)
- [.mark_fallback](mark_fallback.md) (28 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (22 shared connections)
- [.fetch_page](fetch_page.md) (20 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (19 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (16 shared connections)
- [maritime_electric.py](maritime_electric.py.md) (15 shared connections)
- [re](re.md) (12 shared connections)
- [EnbridgeGasScraper](EnbridgeGasScraper.md) (12 shared connections)
- [extract_effective_date](extract_effective_date.md) (12 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/aeso.py`
- `scrapers/utilities/bc_hydro.py`
- `scrapers/utilities/enbridge_gas.py`
- `scrapers/utilities/enmax_energy.py`
- `scrapers/utilities/epcor_energy_alberta.py`
- `scrapers/utilities/heritage_gas.py`
- `scrapers/utilities/toronto_hydro.py`

## Audit Trail

- EXTRACTED: 498 (86%)
- INFERRED: 81 (14%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*