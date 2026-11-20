# .fetch_page

> 46 nodes

## Key Concepts

- **.fetch_page()** (50 connections) — `scrapers/base.py`
- **.fetch_bytes()** (44 connections) — `scrapers/base.py`
- **._try_live_scrape()** (12 connections) — `scrapers/utilities/lethbridge.py`
- **._try_live_scrape()** (11 connections) — `scrapers/utilities/enbridge_gas.py`
- **.parse_schedule_pages()** (11 connections) — `scrapers/utilities/nl_hydro.py`
- **._try_live_scrape()** (11 connections) — `scrapers/utilities/nl_hydro.py`
- **._try_live_scrape()** (10 connections) — `scrapers/utilities/penticton.py`
- **._try_live_scrape()** (9 connections) — `scrapers/utilities/nelson_hydro.py`
- **LethbridgeScraper** (8 connections) — `scrapers/utilities/lethbridge.py`
- **NewWestminsterScraper** (8 connections) — `scrapers/utilities/new_westminster.py`
- **PentictonScraper** (8 connections) — `scrapers/utilities/penticton.py`
- **SummerlandScraper** (8 connections) — `scrapers/utilities/summerland.py`
- **._try_live_scrape()** (8 connections) — `scrapers/utilities/new_westminster.py`
- **._try_live_scrape()** (8 connections) — `scrapers/utilities/summerland.py`
- **NelsonHydroScraper** (7 connections) — `scrapers/utilities/nelson_hydro.py`
- **._log_response()** (6 connections) — `scrapers/base.py`
- **._try_last_known_schedule()** (6 connections) — `scrapers/utilities/nl_hydro.py`
- **._discover_handbook()** (5 connections) — `scrapers/utilities/enbridge_gas.py`
- **describe_response()** (4 connections) — `scrapers/base.py`
- **._discover()** (4 connections) — `scrapers/utilities/lethbridge.py`
- **._discover()** (4 connections) — `scrapers/utilities/new_westminster.py`
- **._discover()** (4 connections) — `scrapers/utilities/penticton.py`
- **._discover()** (4 connections) — `scrapers/utilities/summerland.py`
- **.scrape()** (3 connections) — `scrapers/utilities/lethbridge.py`
- **.scrape()** (3 connections) — `scrapers/utilities/nelson_hydro.py`
- *... and 21 more nodes in this community*

## Relationships

- [BaseScraper](BaseScraper.md) (25 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (24 shared connections)
- [re](re.md) (10 shared connections)
- [RateComponent](RateComponent.md) (8 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (8 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (7 shared connections)
- [.mark_fallback](mark_fallback.md) (5 shared connections)
- [.__init__](__init__.md) (5 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (4 shared connections)
- [EnbridgeGasScraper](EnbridgeGasScraper.md) (4 shared connections)
- [EPCOROntarioGasScraper](EPCOROntarioGasScraper.md) (3 shared connections)
- [parse_schedule](parse_schedule.md) (3 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/enbridge_gas.py`
- `scrapers/utilities/lethbridge.py`
- `scrapers/utilities/nelson_hydro.py`
- `scrapers/utilities/new_westminster.py`
- `scrapers/utilities/nl_hydro.py`
- `scrapers/utilities/penticton.py`
- `scrapers/utilities/summerland.py`

## Audit Trail

- EXTRACTED: 218 (98%)
- INFERRED: 5 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*