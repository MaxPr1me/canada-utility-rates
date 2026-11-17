# .mark_fallback

> 39 nodes

## Key Concepts

- **.mark_fallback()** (44 connections) — `scrapers/base.py`
- **.fetch_bytes()** (37 connections) — `scrapers/base.py`
- **YukonEnergyScraper** (20 connections) — `scrapers/utilities/yukon_energy.py`
- **._parse_residential_pdfs()** (15 connections) — `scrapers/utilities/yukon_energy.py`
- **.live_records()** (12 connections) — `scrapers/utilities/yukon_energy.py`
- **YukonElectricalScraper** (10 connections) — `scrapers/utilities/yukon_electrical.py`
- **._try_live_scrape()** (9 connections) — `scrapers/utilities/atco_electric.py`
- **._joint_schedule()** (9 connections) — `scrapers/utilities/yukon_energy.py`
- **._try_live_scrape()** (8 connections) — `scrapers/utilities/yukon_electrical.py`
- **._general_service_records()** (7 connections) — `scrapers/utilities/yukon_energy.py`
- **._try_live_scrape()** (7 connections) — `scrapers/utilities/yukon_energy.py`
- **.scrape()** (6 connections) — `scrapers/utilities/atco_electric.py`
- **.scrape()** (6 connections) — `scrapers/utilities/yukon_electrical.py`
- **._seed_data()** (6 connections) — `scrapers/utilities/yukon_electrical.py`
- **._discover_joint_schedule()** (6 connections) — `scrapers/utilities/yukon_energy.py`
- **.scrape()** (6 connections) — `scrapers/utilities/yukon_energy.py`
- **._seed_data()** (6 connections) — `scrapers/utilities/yukon_energy.py`
- **._seed_data()** (5 connections) — `scrapers/utilities/atco_electric.py`
- **._page_of()** (4 connections) — `scrapers/utilities/yukon_energy.py`
- **._residential_base_values()** (3 connections) — `scrapers/utilities/yukon_energy.py`
- **GET a URL and return raw bytes (for PDFs, spreadsheets).** (1 connections) — `scrapers/base.py`
- **Label seed output conservatively and visibly. A fallback is useful historical…** (1 connections) — `scrapers/base.py`
- **Parse the current official price schedules and riders. Falls back to labelled…** (1 connections) — `scrapers/utilities/atco_electric.py`
- **Return live-parsed classes only; classes that fail are dropped, never replaced…** (1 connections) — `scrapers/utilities/atco_electric.py`
- **Return seed/fallback data based on known published rates.** (1 connections) — `scrapers/utilities/atco_electric.py`
- *... and 14 more nodes in this community*

## Relationships

- [TariffRecord](TariffRecord.md) (24 shared connections)
- [BaseScraper](BaseScraper.md) (16 shared connections)
- [.fetch_page](fetch_page.md) (11 shared connections)
- [re](re.md) (8 shared connections)
- [RateComponent](RateComponent.md) (7 shared connections)
- [DocumentPage](DocumentPage.md) (7 shared connections)
- [FortisAlbertaScraper](FortisAlbertaScraper.md) (5 shared connections)
- [.now_iso](now_iso.md) (5 shared connections)
- [.__init__](__init__.md) (3 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (3 shared connections)
- [._try_live_scrape](_try_live_scrape.md) (3 shared connections)
- [._parse_commercial](_parse_commercial.md) (3 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/atco_electric.py`
- `scrapers/utilities/yukon_electrical.py`
- `scrapers/utilities/yukon_energy.py`

## Audit Trail

- EXTRACTED: 179 (96%)
- INFERRED: 7 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*