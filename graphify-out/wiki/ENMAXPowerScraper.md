# ENMAXPowerScraper

> 13 nodes

## Key Concepts

- **ENMAXPowerScraper** (10 connections) — `scrapers/utilities/enmax_power.py`
- **._try_live_scrape()** (10 connections) — `scrapers/utilities/enmax_power.py`
- **.fetch_rendered_page()** (8 connections) — `scrapers/base.py`
- **._discover_schedule_url()** (6 connections) — `scrapers/utilities/enmax_power.py`
- **.scrape()** (6 connections) — `scrapers/utilities/enmax_power.py`
- **._seed_data()** (5 connections) — `scrapers/utilities/enmax_power.py`
- **.__init__()** (2 connections) — `scrapers/utilities/enmax_power.py`
- **Return the fully-rendered HTML of a JS-heavy page via headless Chromium.…** (1 connections) — `scrapers/base.py`
- **Scrape ENMAX Power electricity distribution rates for Calgary.** (1 connections) — `scrapers/utilities/enmax_power.py`
- **Attempt to scrape live ENMAX Power distribution rates. Classes the live…** (1 connections) — `scrapers/utilities/enmax_power.py`
- **Parse the current Distribution Tariff Rate Schedule; None if no class can be…** (1 connections) — `scrapers/utilities/enmax_power.py`
- **Static tariffs page first; the rendered page only if the link is absent or the…** (1 connections) — `scrapers/utilities/enmax_power.py`
- **Return seed/fallback data based on known published rates.** (1 connections) — `scrapers/utilities/enmax_power.py`

## Relationships

- [enmax_power.py](enmax_power.py.md) (4 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (4 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (3 shared connections)
- [.fetch_page](fetch_page.md) (3 shared connections)
- [BaseScraper](BaseScraper.md) (2 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (2 shared connections)
- [CentraGasScraper](CentraGasScraper.md) (1 shared connections)
- [fortisalberta.py](fortisalberta.py.md) (1 shared connections)
- [FortisBCEnergyScraper](FortisBCEnergyScraper.md) (1 shared connections)
- [.__init__](__init__.md) (1 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (1 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/enmax_power.py`

## Audit Trail

- EXTRACTED: 36 (95%)
- INFERRED: 2 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*