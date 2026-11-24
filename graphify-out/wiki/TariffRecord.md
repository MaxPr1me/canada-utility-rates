# TariffRecord

> 39 nodes

## Key Concepts

- **TariffRecord** (423 connections) — `scrapers/base.py`
- **BCHydroScraper** (25 connections) — `scrapers/utilities/bc_hydro.py`
- **._try_live_scrape()** (19 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_business_tariff()** (10 connections) — `scrapers/utilities/bc_hydro.py`
- **._numbered_section()** (9 connections) — `scrapers/utilities/bc_hydro.py`
- **._try_live_scrape()** (9 connections) — `scrapers/utilities/nelson_hydro.py`
- **NelsonHydroScraper** (7 connections) — `scrapers/utilities/nelson_hydro.py`
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
- **._parse_residential()** (4 connections) — `scrapers/utilities/bc_hydro.py`
- **.scrape()** (3 connections) — `scrapers/base.py`
- **.scrape()** (3 connections) — `scrapers/utilities/nelson_hydro.py`
- **._extract_step_rate()** (2 connections) — `scrapers/utilities/bc_hydro.py`
- **.__init__()** (2 connections) — `scrapers/utilities/nelson_hydro.py`
- *... and 14 more nodes in this community*

## Relationships

- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (34 shared connections)
- [BaseScraper](BaseScraper.md) (32 shared connections)
- [DocumentPage](DocumentPage.md) (29 shared connections)
- [.now_iso](now_iso.md) (21 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (19 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (18 shared connections)
- [.fetch_page](fetch_page.md) (18 shared connections)
- [RateComponent](RateComponent.md) (17 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (16 shared connections)
- [maritime_electric.py](maritime_electric.py.md) (16 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (16 shared connections)
- [re](re.md) (14 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/bc_hydro.py`
- `scrapers/utilities/nelson_hydro.py`

## Audit Trail

- EXTRACTED: 457 (85%)
- INFERRED: 79 (15%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*