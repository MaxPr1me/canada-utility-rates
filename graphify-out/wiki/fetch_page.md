# .fetch_page

> 13 nodes

## Key Concepts

- **.fetch_page()** (50 connections) — `scrapers/base.py`
- **._try_live_scrape()** (11 connections) — `scrapers/utilities/enbridge_gas.py`
- **._try_live_scrape()** (10 connections) — `scrapers/utilities/penticton.py`
- **PentictonScraper** (8 connections) — `scrapers/utilities/penticton.py`
- **._discover()** (5 connections) — `scrapers/utilities/atco_electric.py`
- **._discover_handbook()** (5 connections) — `scrapers/utilities/enbridge_gas.py`
- **._discover()** (4 connections) — `scrapers/utilities/penticton.py`
- **.scrape()** (3 connections) — `scrapers/utilities/penticton.py`
- **.__init__()** (2 connections) — `scrapers/utilities/penticton.py`
- **GET a URL and return the response text. Includes a polite delay between…** (1 connections) — `scrapers/base.py`
- **Current price-schedules link (and its printed edition date) plus current rider…** (1 connections) — `scrapers/utilities/atco_electric.py`
- **Parse the current handbook (discovered from the rate pages) plus CRA carbon…** (1 connections) — `scrapers/utilities/enbridge_gas.py`
- **Parse the City of Penticton electric rates (Fees and Charges Bylaw, Appendix 7).** (1 connections) — `scrapers/utilities/penticton.py`

## Relationships

- [BaseScraper](BaseScraper.md) (11 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (8 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (7 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (3 shared connections)
- [._try_live_scrape](_try_live_scrape.md) (3 shared connections)
- [.mark_fallback](mark_fallback.md) (3 shared connections)
- [re](re.md) (3 shared connections)
- [EnbridgeGasScraper](EnbridgeGasScraper.md) (3 shared connections)
- [EPCOROntarioGasScraper](EPCOROntarioGasScraper.md) (2 shared connections)
- [parse_schedule](parse_schedule.md) (2 shared connections)
- [RateComponent](RateComponent.md) (2 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (2 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/atco_electric.py`
- `scrapers/utilities/enbridge_gas.py`
- `scrapers/utilities/penticton.py`

## Audit Trail

- EXTRACTED: 85 (99%)
- INFERRED: 1 (1%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*