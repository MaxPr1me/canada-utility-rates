# NBPowerScraper

> 51 nodes

## Key Concepts

- **TariffRecord** (400 connections) — `scrapers/base.py`
- **NBPowerScraper** (24 connections) — `scrapers/utilities/nb_power.py`
- **._try_live_scrape()** (19 connections) — `scrapers/utilities/nb_power.py`
- **_clean()** (11 connections) — `scrapers/utilities/nb_power.py`
- **._parse_small_industrial()** (10 connections) — `scrapers/utilities/nb_power.py`
- **TorontoHydroScraper** (9 connections) — `scrapers/utilities/toronto_hydro.py`
- **_component()** (8 connections) — `scrapers/utilities/nb_power.py`
- **._parse_gs1()** (8 connections) — `scrapers/utilities/nb_power.py`
- **._seed_data()** (8 connections) — `scrapers/utilities/nb_power.py`
- **._parse_residential()** (7 connections) — `scrapers/utilities/nb_power.py`
- **_cents_total()** (7 connections) — `scrapers/utilities/nb_power.py`
- **._parse_fast_charging()** (6 connections) — `scrapers/utilities/nb_power.py`
- **._parse_large_industrial()** (6 connections) — `scrapers/utilities/nb_power.py`
- **._parse_recreational_lighting()** (6 connections) — `scrapers/utilities/nb_power.py`
- **._parse_rural_residential()** (6 connections) — `scrapers/utilities/nb_power.py`
- **._parse_sureconnect()** (6 connections) — `scrapers/utilities/nb_power.py`
- **._parse_water_heater()** (6 connections) — `scrapers/utilities/nb_power.py`
- **_money()** (6 connections) — `scrapers/utilities/nb_power.py`
- **._parse_additional()** (6 connections) — `scrapers/utilities/nb_power.py`
- **.scrape()** (6 connections) — `scrapers/utilities/nb_power.py`
- **_table_after()** (6 connections) — `scrapers/utilities/nb_power.py`
- **._seed_data_gs1()** (5 connections) — `scrapers/utilities/nb_power.py`
- **._seed_data_residential()** (5 connections) — `scrapers/utilities/nb_power.py`
- **._seed_data_small_industrial()** (5 connections) — `scrapers/utilities/nb_power.py`
- **._get_business_sections()** (5 connections) — `scrapers/utilities/nb_power.py`
- *... and 26 more nodes in this community*

## Relationships

- [BaseScraper](BaseScraper.md) (53 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (33 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (33 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (29 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (27 shared connections)
- [.fetch_page](fetch_page.md) (26 shared connections)
- [re](re.md) (18 shared connections)
- [RateComponent](RateComponent.md) (16 shared connections)
- [MaritimeElectricScraper](MaritimeElectricScraper.md) (13 shared connections)
- [FortisBCEnergyScraper](FortisBCEnergyScraper.md) (11 shared connections)
- [EnbridgeGasScraper](EnbridgeGasScraper.md) (10 shared connections)
- [ntpc.py](ntpc.py.md) (9 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/nb_power.py`
- `scrapers/utilities/toronto_hydro.py`

## Audit Trail

- EXTRACTED: 456 (86%)
- INFERRED: 75 (14%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*