# FortisAlbertaScraper

> 23 nodes

## Key Concepts

- **FortisAlbertaScraper** (11 connections) — `scrapers/utilities/fortisalberta.py`
- **ENMAXPowerScraper** (10 connections) — `scrapers/utilities/enmax_power.py`
- **._try_live_scrape()** (10 connections) — `scrapers/utilities/enmax_power.py`
- **._current_schedule()** (10 connections) — `scrapers/utilities/fortisalberta.py`
- **.fetch_rendered_page()** (9 connections) — `scrapers/base.py`
- **.scrape()** (9 connections) — `scrapers/utilities/fortisalberta.py`
- **._discover_schedule_url()** (6 connections) — `scrapers/utilities/enmax_power.py`
- **.scrape()** (6 connections) — `scrapers/utilities/enmax_power.py`
- **._seed_data()** (5 connections) — `scrapers/utilities/enmax_power.py`
- **._read_pdf()** (5 connections) — `scrapers/utilities/fortisalberta.py`
- **._seed_data()** (5 connections) — `scrapers/utilities/fortisalberta.py`
- **.__init__()** (2 connections) — `scrapers/utilities/enmax_power.py`
- **.__init__()** (2 connections) — `scrapers/utilities/fortisalberta.py`
- **Return the fully-rendered HTML of a JS-heavy page via headless Chromium.…** (1 connections) — `scrapers/base.py`
- **Scrape ENMAX Power electricity distribution rates for Calgary.** (1 connections) — `scrapers/utilities/enmax_power.py`
- **Attempt to scrape live ENMAX Power distribution rates. Classes the live…** (1 connections) — `scrapers/utilities/enmax_power.py`
- **Parse the current Distribution Tariff Rate Schedule; None if no class can be…** (1 connections) — `scrapers/utilities/enmax_power.py`
- **Static tariffs page first; the rendered page only if the link is absent or the…** (1 connections) — `scrapers/utilities/enmax_power.py`
- **Return seed/fallback data based on known published rates.** (1 connections) — `scrapers/utilities/enmax_power.py`
- **Scrape FortisAlberta building rate classes from the current Rates, Options and…** (1 connections) — `scrapers/utilities/fortisalberta.py`
- **Only a total fetch/parse failure falls back to the labelled seed estimates.** (1 connections) — `scrapers/utilities/fortisalberta.py`
- **The newest edition already in effect; an older edition is never used in its…** (1 connections) — `scrapers/utilities/fortisalberta.py`
- **Return seed/fallback data based on known published rates.** (1 connections) — `scrapers/utilities/fortisalberta.py`

## Relationships

- [TariffRecord](TariffRecord.md) (7 shared connections)
- [fortisalberta.py](fortisalberta.py.md) (6 shared connections)
- [.mark_fallback](mark_fallback.md) (5 shared connections)
- [enmax_power.py](enmax_power.py.md) (4 shared connections)
- [BaseScraper](BaseScraper.md) (4 shared connections)
- [RateComponent](RateComponent.md) (4 shared connections)
- [.fetch_page](fetch_page.md) (4 shared connections)
- [DocumentPage](DocumentPage.md) (3 shared connections)
- [.now_iso](now_iso.md) (2 shared connections)
- [.__init__](__init__.md) (2 shared connections)
- [CentraGasScraper](CentraGasScraper.md) (1 shared connections)
- [FortisBCEnergyScraper](FortisBCEnergyScraper.md) (1 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/enmax_power.py`
- `scrapers/utilities/fortisalberta.py`

## Audit Trail

- EXTRACTED: 67 (93%)
- INFERRED: 5 (7%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*