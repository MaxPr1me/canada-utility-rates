# BCHydroScraper

> 48 nodes

## Key Concepts

- **TariffRecord** (423 connections) — `scrapers/base.py`
- **BCHydroScraper** (25 connections) — `scrapers/utilities/bc_hydro.py`
- **._try_live_scrape()** (19 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_business_tariff()** (10 connections) — `scrapers/utilities/bc_hydro.py`
- **EPCORGasScraper** (9 connections) — `scrapers/utilities/epcor_gas.py`
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
- **._try_live_scrape()** (6 connections) — `scrapers/utilities/epcor_gas.py`
- **.scrape()** (5 connections) — `scrapers/utilities/epcor_gas.py`
- **._seed_data()** (5 connections) — `scrapers/utilities/epcor_gas.py`
- **.scrape()** (5 connections) — `scrapers/utilities/toronto_hydro.py`
- **._parse_residential()** (4 connections) — `scrapers/utilities/bc_hydro.py`
- *... and 23 more nodes in this community*

## Relationships

- [RateComponent](RateComponent.md) (51 shared connections)
- [extract_pdf_pages](extract_pdf_pages.md) (47 shared connections)
- [BaseScraper](BaseScraper.md) (37 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (33 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (18 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (17 shared connections)
- [.__init__](__init__.md) (16 shared connections)
- [maritime_electric.py](maritime_electric.py.md) (15 shared connections)
- [NewfoundlandPowerScraper](NewfoundlandPowerScraper.md) (13 shared connections)
- [extract_effective_date](extract_effective_date.md) (13 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (11 shared connections)
- [.mark_fallback](mark_fallback.md) (11 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/bc_hydro.py`
- `scrapers/utilities/epcor_gas.py`
- `scrapers/utilities/toronto_hydro.py`

## Audit Trail

- EXTRACTED: 472 (85%)
- INFERRED: 81 (15%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*