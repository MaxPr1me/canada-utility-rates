# .mark_fallback

> 32 nodes

## Key Concepts

- **YukonEnergyScraper** (20 connections) — `scrapers/utilities/yukon_energy.py`
- **._parse_residential_pdfs()** (15 connections) — `scrapers/utilities/yukon_energy.py`
- **.live_records()** (12 connections) — `scrapers/utilities/yukon_energy.py`
- **YukonElectricalScraper** (10 connections) — `scrapers/utilities/yukon_electrical.py`
- **.fetch_rendered_page()** (9 connections) — `scrapers/base.py`
- **._joint_schedule()** (9 connections) — `scrapers/utilities/yukon_energy.py`
- **._try_live_scrape()** (8 connections) — `scrapers/utilities/yukon_electrical.py`
- **._general_service_records()** (7 connections) — `scrapers/utilities/yukon_energy.py`
- **._try_live_scrape()** (7 connections) — `scrapers/utilities/yukon_energy.py`
- **.scrape()** (6 connections) — `scrapers/utilities/yukon_electrical.py`
- **._seed_data()** (6 connections) — `scrapers/utilities/yukon_electrical.py`
- **._discover_joint_schedule()** (6 connections) — `scrapers/utilities/yukon_energy.py`
- **.scrape()** (6 connections) — `scrapers/utilities/yukon_energy.py`
- **._seed_data()** (6 connections) — `scrapers/utilities/yukon_energy.py`
- **._page_of()** (4 connections) — `scrapers/utilities/yukon_energy.py`
- **._residential_base_values()** (3 connections) — `scrapers/utilities/yukon_energy.py`
- **.__init__()** (2 connections) — `scrapers/utilities/yukon_energy.py`
- **Return the fully-rendered HTML of a JS-heavy page via headless Chromium.…** (1 connections) — `scrapers/base.py`
- **Return seed/fallback data based on known published rates.** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- **Scrape Yukon Electrical Company electricity rates.** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- **Attempt to scrape live Yukon Electrical rates. Falls back to seed data if the…** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- **Reuse the joint-schedule parser; unproven seed classes stay labelled estimates.** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- **Scrape Yukon Energy Corporation electricity rates.** (1 connections) — `scrapers/utilities/yukon_energy.py`
- **Attempt to scrape live Yukon Energy rates. Falls back to seed data if the live…** (1 connections) — `scrapers/utilities/yukon_energy.py`
- **Parse live residential/general-service schedules; unparsed seed classes stay…** (1 connections) — `scrapers/utilities/yukon_energy.py`
- *... and 7 more nodes in this community*

## Relationships

- [TariffRecord](TariffRecord.md) (15 shared connections)
- [BaseScraper](BaseScraper.md) (12 shared connections)
- [.fetch_page](fetch_page.md) (7 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (6 shared connections)
- [DocumentPage](DocumentPage.md) (4 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (4 shared connections)
- [.__init__](__init__.md) (2 shared connections)
- [re](re.md) (2 shared connections)
- [CentraGasScraper](CentraGasScraper.md) (1 shared connections)
- [fortisalberta.py](fortisalberta.py.md) (1 shared connections)
- [FortisBCEnergyScraper](FortisBCEnergyScraper.md) (1 shared connections)
- [maritime_electric.py](maritime_electric.py.md) (1 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/yukon_electrical.py`
- `scrapers/utilities/yukon_energy.py`

## Audit Trail

- EXTRACTED: 97 (93%)
- INFERRED: 7 (7%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*