# BCHydroScraper

> 60 nodes

## Key Concepts

- **TariffRecord** (423 connections) — `scrapers/base.py`
- **BCHydroScraper** (25 connections) — `scrapers/utilities/bc_hydro.py`
- **._try_live_scrape()** (19 connections) — `scrapers/utilities/bc_hydro.py`
- **parse_manual()** (11 connections) — `scrapers/utilities/summerside_electric.py`
- **TorontoHydroScraper** (9 connections) — `scrapers/utilities/toronto_hydro.py`
- **._numbered_section()** (9 connections) — `scrapers/utilities/bc_hydro.py`
- **._seed_data()** (8 connections) — `scrapers/utilities/nb_power.py`
- **._parse_freshet_energy()** (7 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_net_metering_tariff()** (7 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_residential_options()** (7 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_residential_tariff()** (7 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_transmission_pilots()** (7 connections) — `scrapers/utilities/bc_hydro.py`
- **._tariff_document()** (7 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_business()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_community_generation_tariff()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_self_generation_tariff()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_transmission_tariff()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **.scrape()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **._seed_data()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **.scrape()** (6 connections) — `scrapers/utilities/manitoba_hydro.py`
- **._seed_data()** (6 connections) — `scrapers/utilities/manitoba_hydro.py`
- **.scrape()** (6 connections) — `scrapers/utilities/nb_power.py`
- **._seed_data_gs1()** (5 connections) — `scrapers/utilities/nb_power.py`
- **._seed_data_residential()** (5 connections) — `scrapers/utilities/nb_power.py`
- **._seed_data_small_industrial()** (5 connections) — `scrapers/utilities/nb_power.py`
- *... and 35 more nodes in this community*

## Relationships

- [RateComponent](RateComponent.md) (55 shared connections)
- [BaseScraper](BaseScraper.md) (34 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (32 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (32 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (26 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (20 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (20 shared connections)
- [extract_effective_date](extract_effective_date.md) (20 shared connections)
- [NewfoundlandPowerScraper](NewfoundlandPowerScraper.md) (13 shared connections)
- [EnbridgeGasScraper](EnbridgeGasScraper.md) (12 shared connections)
- [maritime_electric.py](maritime_electric.py.md) (11 shared connections)
- [FortisBCEnergyScraper](FortisBCEnergyScraper.md) (11 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/bc_hydro.py`
- `scrapers/utilities/enbridge_gas.py`
- `scrapers/utilities/energir.py`
- `scrapers/utilities/manitoba_hydro.py`
- `scrapers/utilities/nb_power.py`
- `scrapers/utilities/summerside_electric.py`
- `scrapers/utilities/toronto_hydro.py`

## Audit Trail

- EXTRACTED: 496 (86%)
- INFERRED: 81 (14%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*