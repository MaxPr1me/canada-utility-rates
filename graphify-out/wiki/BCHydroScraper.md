# BCHydroScraper

> 57 nodes

## Key Concepts

- **TariffRecord** (400 connections) — `scrapers/base.py`
- **BCHydroScraper** (25 connections) — `scrapers/utilities/bc_hydro.py`
- **._try_live_scrape()** (19 connections) — `scrapers/utilities/bc_hydro.py`
- **AESOScraper** (10 connections) — `scrapers/utilities/aeso.py`
- **._try_live_scrape()** (10 connections) — `scrapers/utilities/nl_hydro.py`
- **._numbered_section()** (9 connections) — `scrapers/utilities/bc_hydro.py`
- **.scrape()** (9 connections) — `scrapers/utilities/fortisalberta.py`
- **._parse_freshet_energy()** (7 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_net_metering_tariff()** (7 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_residential_options()** (7 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_residential_tariff()** (7 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_transmission_pilots()** (7 connections) — `scrapers/utilities/bc_hydro.py`
- **._tariff_document()** (7 connections) — `scrapers/utilities/bc_hydro.py`
- **.scrape()** (7 connections) — `scrapers/utilities/ontario_ldc.py`
- **._parse_business()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_community_generation_tariff()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_self_generation_tariff()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_transmission_tariff()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **.scrape()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **._seed_data()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **.scrape()** (6 connections) — `scrapers/utilities/nl_hydro.py`
- **.scrape()** (6 connections) — `scrapers/utilities/saskpower.py`
- **._seed_data()** (6 connections) — `scrapers/utilities/saskpower.py`
- **.scrape()** (5 connections) — `scrapers/utilities/aeso.py`
- **.scrape()** (5 connections) — `scrapers/utilities/enbridge_gas.py`
- *... and 32 more nodes in this community*

## Relationships

- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (46 shared connections)
- [.mark_fallback](mark_fallback.md) (42 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (40 shared connections)
- [.fetch_page](fetch_page.md) (28 shared connections)
- [BaseScraper](BaseScraper.md) (27 shared connections)
- [.now_iso](now_iso.md) (22 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (18 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (16 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (15 shared connections)
- [MaritimeElectricScraper](MaritimeElectricScraper.md) (13 shared connections)
- [EnbridgeGasScraper](EnbridgeGasScraper.md) (12 shared connections)
- [FortisBCEnergyScraper](FortisBCEnergyScraper.md) (12 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/aeso.py`
- `scrapers/utilities/bc_hydro.py`
- `scrapers/utilities/enbridge_gas.py`
- `scrapers/utilities/fortisalberta.py`
- `scrapers/utilities/fortisbc_energy.py`
- `scrapers/utilities/nl_hydro.py`
- `scrapers/utilities/ontario_ldc.py`
- `scrapers/utilities/saskpower.py`

## Audit Trail

- EXTRACTED: 484 (86%)
- INFERRED: 76 (14%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*