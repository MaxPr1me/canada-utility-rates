# NovaScotiaPowerScraper

> 87 nodes

## Key Concepts

- **RateComponent** (276 connections) — `scrapers/base.py`
- **NovaScotiaPowerScraper** (39 connections) — `scrapers/utilities/nova_scotia_power.py`
- **parse_rates()** (11 connections) — `scrapers/utilities/nelson_hydro.py`
- **._order_context()** (11 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._parse_residential_tariffs()** (11 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._parse_industrial_tariff()** (10 connections) — `scrapers/utilities/nova_scotia_power.py`
- **parse_appendix()** (10 connections) — `scrapers/utilities/penticton.py`
- **._parse_business_pilot()** (9 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._parse_business_tariff()** (9 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._business_rider_components()** (9 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._continuous_pages()** (9 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._seed_data()** (9 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._try_live_commercial()** (9 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._parse_rtp_tariff()** (8 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._parse_business_pilot_tariffs()** (8 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._parse_business_tariffs()** (8 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._parse_industrial_tariffs()** (8 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._parse_rtp_tariffs()** (8 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._parse_community_solar_rider()** (7 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._parse_murb_tariff()** (7 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._parse_solar_garden_rider()** (7 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._footer_effective_date()** (7 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._murb_rider_components()** (7 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._rtp_rider_components()** (7 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._parse_residential()** (6 connections) — `scrapers/utilities/nova_scotia_power.py`
- *... and 62 more nodes in this community*

## Relationships

- [TariffRecord](TariffRecord.md) (56 shared connections)
- [BaseScraper](BaseScraper.md) (44 shared connections)
- [DocumentPage](DocumentPage.md) (25 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (20 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (15 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (13 shared connections)
- [FortisBCEnergyScraper](FortisBCEnergyScraper.md) (13 shared connections)
- [fortisalberta.py](fortisalberta.py.md) (12 shared connections)
- [.fetch_page](fetch_page.md) (9 shared connections)
- [NewfoundlandPowerScraper](NewfoundlandPowerScraper.md) (9 shared connections)
- [re](re.md) (8 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (8 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/fortisalberta.py`
- `scrapers/utilities/nelson_hydro.py`
- `scrapers/utilities/nova_scotia_power.py`
- `scrapers/utilities/ontario_ldc.py`
- `scrapers/utilities/penticton.py`

## Audit Trail

- EXTRACTED: 428 (89%)
- INFERRED: 53 (11%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*