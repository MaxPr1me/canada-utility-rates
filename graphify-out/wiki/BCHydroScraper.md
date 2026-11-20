# BCHydroScraper

> 46 nodes

## Key Concepts

- **TariffRecord** (423 connections) — `scrapers/base.py`
- **BCHydroScraper** (25 connections) — `scrapers/utilities/bc_hydro.py`
- **._try_live_scrape()** (19 connections) — `scrapers/utilities/bc_hydro.py`
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
- **.scrape()** (6 connections) — `scrapers/utilities/nl_hydro.py`
- **.scrape()** (5 connections) — `scrapers/utilities/enbridge_gas.py`
- **._seed_data()** (5 connections) — `scrapers/utilities/nl_hydro.py`
- **.scrape()** (5 connections) — `scrapers/utilities/toronto_hydro.py`
- **._parse_residential()** (4 connections) — `scrapers/utilities/bc_hydro.py`
- **._seed_data()** (4 connections) — `scrapers/utilities/enbridge_gas.py`
- *... and 21 more nodes in this community*

## Relationships

- [fortisbc_electric.py](fortisbc_electric.py.md) (45 shared connections)
- [RateComponent](RateComponent.md) (41 shared connections)
- [BaseScraper](BaseScraper.md) (37 shared connections)
- [.fetch_page](fetch_page.md) (24 shared connections)
- [extract_effective_date](extract_effective_date.md) (22 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (21 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (20 shared connections)
- [maritime_electric.py](maritime_electric.py.md) (14 shared connections)
- [EnbridgeGasScraper](EnbridgeGasScraper.md) (12 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (12 shared connections)
- [FortisBCEnergyScraper](FortisBCEnergyScraper.md) (11 shared connections)
- [.mark_fallback](mark_fallback.md) (11 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/bc_hydro.py`
- `scrapers/utilities/enbridge_gas.py`
- `scrapers/utilities/nl_hydro.py`
- `scrapers/utilities/toronto_hydro.py`

## Audit Trail

- EXTRACTED: 470 (85%)
- INFERRED: 80 (15%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*