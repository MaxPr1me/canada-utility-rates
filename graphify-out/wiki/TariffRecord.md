# TariffRecord

> 42 nodes

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
- **.scrape()** (5 connections) — `scrapers/utilities/toronto_hydro.py`
- **._parse_residential()** (4 connections) — `scrapers/utilities/bc_hydro.py`
- **._seed_data()** (4 connections) — `scrapers/utilities/toronto_hydro.py`
- **._try_live_scrape()** (4 connections) — `scrapers/utilities/toronto_hydro.py`
- **value()** (3 connections) — `scrapers/utilities/bc_hydro.py`
- **._extract_step_rate()** (2 connections) — `scrapers/utilities/bc_hydro.py`
- *... and 17 more nodes in this community*

## Relationships

- [RateComponent](RateComponent.md) (39 shared connections)
- [.fetch_page](fetch_page.md) (28 shared connections)
- [BaseScraper](BaseScraper.md) (27 shared connections)
- [parsing.py](parsing.py.md) (22 shared connections)
- [DocumentPage](DocumentPage.md) (21 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (18 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (17 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (15 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (13 shared connections)
- [.now_iso](now_iso.md) (13 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (12 shared connections)
- [maritime_electric.py](maritime_electric.py.md) (11 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/bc_hydro.py`
- `scrapers/utilities/toronto_hydro.py`

## Audit Trail

- EXTRACTED: 457 (85%)
- INFERRED: 82 (15%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*