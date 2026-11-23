# ._try_live_scrape

> 16 nodes

## Key Concepts

- **._try_live_scrape()** (12 connections) — `scrapers/utilities/red_deer.py`
- **ENMAXPowerScraper** (10 connections) — `scrapers/utilities/enmax_power.py`
- **.fetch_rendered_page()** (10 connections) — `scrapers/base.py`
- **._try_live_scrape()** (10 connections) — `scrapers/utilities/enmax_power.py`
- **RedDeerScraper** (8 connections) — `scrapers/utilities/red_deer.py`
- **._discover_schedule_url()** (6 connections) — `scrapers/utilities/enmax_power.py`
- **._html()** (5 connections) — `scrapers/utilities/red_deer.py`
- **.scrape()** (3 connections) — `scrapers/utilities/red_deer.py`
- **.__init__()** (2 connections) — `scrapers/utilities/enmax_power.py`
- **.__init__()** (2 connections) — `scrapers/utilities/red_deer.py`
- **Return the fully-rendered HTML of a JS-heavy page via headless Chromium.…** (1 connections) — `scrapers/base.py`
- **Scrape ENMAX Power electricity distribution rates for Calgary.** (1 connections) — `scrapers/utilities/enmax_power.py`
- **Parse the current Distribution Tariff Rate Schedule; None if no class can be…** (1 connections) — `scrapers/utilities/enmax_power.py`
- **Static tariffs page first; the rendered page only if the link is absent or the…** (1 connections) — `scrapers/utilities/enmax_power.py`
- **Parse the City of Red Deer's distribution tariff and Regulated Rate Tariff.** (1 connections) — `scrapers/utilities/red_deer.py`
- **The page over plain HTTP, or rendered by headless Chromium when the expected…** (1 connections) — `scrapers/utilities/red_deer.py`

## Relationships

- [red_deer.py](red_deer.py.md) (6 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (5 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (5 shared connections)
- [BaseScraper](BaseScraper.md) (4 shared connections)
- [RateComponent](RateComponent.md) (4 shared connections)
- [enmax_power.py](enmax_power.py.md) (3 shared connections)
- [extract_effective_date](extract_effective_date.md) (2 shared connections)
- [.fetch_page](fetch_page.md) (2 shared connections)
- [.__init__](__init__.md) (2 shared connections)
- [CentraGasScraper](CentraGasScraper.md) (1 shared connections)
- [fortisalberta.py](fortisalberta.py.md) (1 shared connections)
- [FortisBCEnergyScraper](FortisBCEnergyScraper.md) (1 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/enmax_power.py`
- `scrapers/utilities/red_deer.py`

## Audit Trail

- EXTRACTED: 53 (95%)
- INFERRED: 3 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*