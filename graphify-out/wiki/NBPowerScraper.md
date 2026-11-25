# NBPowerScraper

> 74 nodes

## Key Concepts

- **TariffRecord** (423 connections) — `scrapers/base.py`
- **NBPowerScraper** (24 connections) — `scrapers/utilities/nb_power.py`
- **._try_live_scrape()** (19 connections) — `scrapers/utilities/nb_power.py`
- **_clean()** (11 connections) — `scrapers/utilities/nb_power.py`
- **AESOScraper** (10 connections) — `scrapers/utilities/aeso.py`
- **._parse_small_industrial()** (10 connections) — `scrapers/utilities/nb_power.py`
- **TorontoHydroScraper** (9 connections) — `scrapers/utilities/toronto_hydro.py`
- **_component()** (8 connections) — `scrapers/utilities/nb_power.py`
- **._parse_gs1()** (8 connections) — `scrapers/utilities/nb_power.py`
- **._seed_data()** (8 connections) — `scrapers/utilities/nb_power.py`
- **._parse_residential()** (7 connections) — `scrapers/utilities/nb_power.py`
- **.scrape()** (7 connections) — `scrapers/utilities/ontario_ldc.py`
- **._parse_fast_charging()** (6 connections) — `scrapers/utilities/nb_power.py`
- **._parse_large_industrial()** (6 connections) — `scrapers/utilities/nb_power.py`
- **._parse_recreational_lighting()** (6 connections) — `scrapers/utilities/nb_power.py`
- **._parse_rural_residential()** (6 connections) — `scrapers/utilities/nb_power.py`
- **._parse_sureconnect()** (6 connections) — `scrapers/utilities/nb_power.py`
- **._parse_water_heater()** (6 connections) — `scrapers/utilities/nb_power.py`
- **.scrape()** (6 connections) — `scrapers/utilities/epcor_distribution.py`
- **_money()** (6 connections) — `scrapers/utilities/nb_power.py`
- **._parse_additional()** (6 connections) — `scrapers/utilities/nb_power.py`
- **.scrape()** (6 connections) — `scrapers/utilities/nb_power.py`
- **_table_after()** (6 connections) — `scrapers/utilities/nb_power.py`
- **._seed_data_gs1()** (5 connections) — `scrapers/utilities/nb_power.py`
- **._seed_data_residential()** (5 connections) — `scrapers/utilities/nb_power.py`
- *... and 49 more nodes in this community*

## Relationships

- [RateComponent](RateComponent.md) (82 shared connections)
- [BaseScraper](BaseScraper.md) (50 shared connections)
- [extract_pdf_pages](extract_pdf_pages.md) (45 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (23 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (17 shared connections)
- [re](re.md) (17 shared connections)
- [.__init__](__init__.md) (16 shared connections)
- [DocumentPage](DocumentPage.md) (15 shared connections)
- [maritime_electric.py](maritime_electric.py.md) (12 shared connections)
- [EnbridgeGasScraper](EnbridgeGasScraper.md) (12 shared connections)
- [nl_hydro.py](nl_hydro.py.md) (11 shared connections)
- [FortisBCEnergyScraper](FortisBCEnergyScraper.md) (10 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/aeso.py`
- `scrapers/utilities/atco_gas.py`
- `scrapers/utilities/centra_gas.py`
- `scrapers/utilities/enbridge_gas.py`
- `scrapers/utilities/energir.py`
- `scrapers/utilities/epcor_distribution.py`
- `scrapers/utilities/fortisbc_energy.py`
- `scrapers/utilities/heritage_gas.py`
- `scrapers/utilities/liberty_gas_nb.py`
- `scrapers/utilities/nb_power.py`
- `scrapers/utilities/ontario_ldc.py`
- `scrapers/utilities/saskenergy.py`
- `scrapers/utilities/toronto_hydro.py`

## Audit Trail

- EXTRACTED: 546 (87%)
- INFERRED: 80 (13%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*