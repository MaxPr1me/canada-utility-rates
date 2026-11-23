# BCHydroScraper

> 72 nodes

## Key Concepts

- **TariffRecord** (423 connections) — `scrapers/base.py`
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
- **.scrape()** (7 connections) — `scrapers/utilities/ontario_ldc.py`
- **._parse_standard_charges()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_business()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_community_generation_tariff()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_self_generation_tariff()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- *... and 47 more nodes in this community*

## Relationships

- [RateComponent](RateComponent.md) (82 shared connections)
- [.fetch_page](fetch_page.md) (43 shared connections)
- [BaseScraper](BaseScraper.md) (43 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (43 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (18 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (16 shared connections)
- [.mark_fallback](mark_fallback.md) (14 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (13 shared connections)
- [.__init__](__init__.md) (13 shared connections)
- [EnbridgeGasScraper](EnbridgeGasScraper.md) (12 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (12 shared connections)
- [maritime_electric.py](maritime_electric.py.md) (11 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/atco_gas.py`
- `scrapers/utilities/bc_hydro.py`
- `scrapers/utilities/enbridge_gas.py`
- `scrapers/utilities/energir.py`
- `scrapers/utilities/epcor_energy_alberta.py`
- `scrapers/utilities/heritage_gas.py`
- `scrapers/utilities/liberty_gas_nb.py`
- `scrapers/utilities/ontario_ldc.py`
- `scrapers/utilities/saskenergy.py`
- `scrapers/utilities/saskpower.py`
- `scrapers/utils/parsing.py`

## Audit Trail

- EXTRACTED: 580 (88%)
- INFERRED: 81 (12%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*