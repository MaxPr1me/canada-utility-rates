# ._try_live_scrape

> 17 nodes

## Key Concepts

- **._try_live_scrape()** (11 connections) — `scrapers/utilities/centra_gas.py`
- **ENMAXPowerScraper** (10 connections) — `scrapers/utilities/enmax_power.py`
- **.fetch_rendered_page()** (10 connections) — `scrapers/base.py`
- **._try_live_scrape()** (10 connections) — `scrapers/utilities/enmax_power.py`
- **._discover_schedule_url()** (6 connections) — `scrapers/utilities/enmax_power.py`
- **.scrape()** (6 connections) — `scrapers/utilities/enmax_power.py`
- **.scrape()** (5 connections) — `scrapers/utilities/centra_gas.py`
- **._seed_data()** (5 connections) — `scrapers/utilities/enmax_power.py`
- **._seed_data()** (4 connections) — `scrapers/utilities/centra_gas.py`
- **.__init__()** (2 connections) — `scrapers/utilities/enmax_power.py`
- **Return the fully-rendered HTML of a JS-heavy page via headless Chromium.…** (1 connections) — `scrapers/base.py`
- **Fetch each official page independently and parse complete classes.** (1 connections) — `scrapers/utilities/centra_gas.py`
- **Scrape ENMAX Power electricity distribution rates for Calgary.** (1 connections) — `scrapers/utilities/enmax_power.py`
- **Attempt to scrape live ENMAX Power distribution rates. Classes the live…** (1 connections) — `scrapers/utilities/enmax_power.py`
- **Parse the current Distribution Tariff Rate Schedule; None if no class can be…** (1 connections) — `scrapers/utilities/enmax_power.py`
- **Static tariffs page first; the rendered page only if the link is absent or the…** (1 connections) — `scrapers/utilities/enmax_power.py`
- **Return seed/fallback data based on known published rates.** (1 connections) — `scrapers/utilities/enmax_power.py`

## Relationships

- [BCHydroScraper](BCHydroScraper.md) (7 shared connections)
- [CentraGasScraper](CentraGasScraper.md) (7 shared connections)
- [enmax_power.py](enmax_power.py.md) (4 shared connections)
- [.fetch_page](fetch_page.md) (4 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (3 shared connections)
- [maritime_electric.py](maritime_electric.py.md) (3 shared connections)
- [BaseScraper](BaseScraper.md) (2 shared connections)
- [extract_effective_date](extract_effective_date.md) (2 shared connections)
- [RateComponent](RateComponent.md) (2 shared connections)
- [fortisalberta.py](fortisalberta.py.md) (1 shared connections)
- [red_deer.py](red_deer.py.md) (1 shared connections)
- [.mark_fallback](mark_fallback.md) (1 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/centra_gas.py`
- `scrapers/utilities/enmax_power.py`

## Audit Trail

- EXTRACTED: 55 (96%)
- INFERRED: 2 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*