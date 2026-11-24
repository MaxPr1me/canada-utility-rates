# .mark_fallback

> 35 nodes

## Key Concepts

- **YukonEnergyScraper** (20 connections) — `scrapers/utilities/yukon_energy.py`
- **._parse_residential_pdfs()** (15 connections) — `scrapers/utilities/yukon_energy.py`
- **.live_records()** (12 connections) — `scrapers/utilities/yukon_energy.py`
- **YukonElectricalScraper** (10 connections) — `scrapers/utilities/yukon_electrical.py`
- **._joint_schedule()** (9 connections) — `scrapers/utilities/yukon_energy.py`
- **._try_live_scrape()** (8 connections) — `scrapers/utilities/yukon_electrical.py`
- **._general_service_records()** (7 connections) — `scrapers/utilities/yukon_energy.py`
- **._try_live_scrape()** (7 connections) — `scrapers/utilities/yukon_energy.py`
- **.scrape()** (6 connections) — `scrapers/utilities/yukon_electrical.py`
- **._seed_data()** (6 connections) — `scrapers/utilities/yukon_electrical.py`
- **_strings()** (6 connections) — `scrapers/utilities/yukon_energy.py`
- **._discover_joint_schedule()** (6 connections) — `scrapers/utilities/yukon_energy.py`
- **.scrape()** (6 connections) — `scrapers/utilities/yukon_energy.py`
- **._seed_data()** (6 connections) — `scrapers/utilities/yukon_energy.py`
- **joint_schedule_editions()** (5 connections) — `scrapers/utilities/yukon_energy.py`
- **._page_of()** (4 connections) — `scrapers/utilities/yukon_energy.py`
- **._residential_base_values()** (3 connections) — `scrapers/utilities/yukon_energy.py`
- **.__init__()** (2 connections) — `scrapers/utilities/yukon_electrical.py`
- **Any** (2 connections)
- **Return seed/fallback data based on known published rates.** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- **Scrape Yukon Electrical Company electricity rates.** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- **Attempt to scrape live Yukon Electrical rates. Falls back to seed data if the…** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- **Reuse the joint-schedule parser; unproven seed classes stay labelled estimates.** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- **Return {absolute link: "YYYY-MM" edition} for joint-book PDFs named anywhere in…** (1 connections) — `scrapers/utilities/yukon_energy.py`
- **Scrape Yukon Energy Corporation electricity rates.** (1 connections) — `scrapers/utilities/yukon_energy.py`
- *... and 10 more nodes in this community*

## Relationships

- [BaseScraper](BaseScraper.md) (13 shared connections)
- [TariffRecord](TariffRecord.md) (11 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (6 shared connections)
- [.fetch_page](fetch_page.md) (5 shared connections)
- [DocumentPage](DocumentPage.md) (4 shared connections)
- [RateComponent](RateComponent.md) (4 shared connections)
- [.now_iso](now_iso.md) (3 shared connections)
- [ntpc.py](ntpc.py.md) (2 shared connections)
- [re](re.md) (2 shared connections)
- [ENMAXPowerScraper](ENMAXPowerScraper.md) (1 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (1 shared connections)

## Source Files

- `scrapers/utilities/yukon_electrical.py`
- `scrapers/utilities/yukon_energy.py`

## Audit Trail

- EXTRACTED: 97 (93%)
- INFERRED: 7 (7%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*