# TariffRecord

> 40 nodes

## Key Concepts

- **TariffRecord** (400 connections) — `scrapers/base.py`
- **._try_live_scrape()** (12 connections) — `scrapers/utilities/aeso.py`
- **parse_manual()** (11 connections) — `scrapers/utilities/summerside_electric.py`
- **AESOScraper** (10 connections) — `scrapers/utilities/aeso.py`
- **EPCORGasScraper** (9 connections) — `scrapers/utilities/epcor_gas.py`
- **TorontoHydroScraper** (9 connections) — `scrapers/utilities/toronto_hydro.py`
- **SummersideElectricScraper** (8 connections) — `scrapers/utilities/summerside_electric.py`
- **._try_live_scrape()** (8 connections) — `scrapers/utilities/summerside_electric.py`
- **._try_live_scrape()** (6 connections) — `scrapers/utilities/epcor_gas.py`
- **.scrape()** (5 connections) — `scrapers/utilities/aeso.py`
- **.scrape()** (5 connections) — `scrapers/utilities/centra_gas.py`
- **.scrape()** (5 connections) — `scrapers/utilities/enbridge_gas.py`
- **.scrape()** (5 connections) — `scrapers/utilities/epcor_gas.py`
- **._seed_data()** (5 connections) — `scrapers/utilities/epcor_gas.py`
- **.scrape()** (5 connections) — `scrapers/utilities/heritage_gas.py`
- **.scrape()** (5 connections) — `scrapers/utilities/saskenergy.py`
- **.scrape()** (5 connections) — `scrapers/utilities/toronto_hydro.py`
- **._market_reference()** (4 connections) — `scrapers/utilities/aeso.py`
- **._seed_data()** (4 connections) — `scrapers/utilities/aeso.py`
- **._seed_data()** (4 connections) — `scrapers/utilities/centra_gas.py`
- **._seed_data()** (4 connections) — `scrapers/utilities/enbridge_gas.py`
- **._seed_data()** (4 connections) — `scrapers/utilities/heritage_gas.py`
- **._seed_data()** (4 connections) — `scrapers/utilities/saskenergy.py`
- **._discover()** (4 connections) — `scrapers/utilities/summerside_electric.py`
- **._seed_data()** (4 connections) — `scrapers/utilities/toronto_hydro.py`
- *... and 15 more nodes in this community*

## Relationships

- [BaseScraper](BaseScraper.md) (31 shared connections)
- [.mark_fallback](mark_fallback.md) (24 shared connections)
- [RateComponent](RateComponent.md) (22 shared connections)
- [.fetch_page](fetch_page.md) (22 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (22 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (18 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (17 shared connections)
- [re](re.md) (16 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (16 shared connections)
- [DocumentPage](DocumentPage.md) (16 shared connections)
- [MaritimeElectricScraper](MaritimeElectricScraper.md) (13 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (13 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/aeso.py`
- `scrapers/utilities/centra_gas.py`
- `scrapers/utilities/enbridge_gas.py`
- `scrapers/utilities/epcor_gas.py`
- `scrapers/utilities/heritage_gas.py`
- `scrapers/utilities/saskenergy.py`
- `scrapers/utilities/summerside_electric.py`
- `scrapers/utilities/toronto_hydro.py`

## Audit Trail

- EXTRACTED: 425 (85%)
- INFERRED: 77 (15%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*