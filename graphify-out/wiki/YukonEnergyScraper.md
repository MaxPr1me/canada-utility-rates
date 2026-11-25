# YukonEnergyScraper

> 28 nodes

## Key Concepts

- **YukonEnergyScraper** (20 connections) — `scrapers/utilities/yukon_energy.py`
- **._parse_residential_pdfs()** (15 connections) — `scrapers/utilities/yukon_energy.py`
- **YukonElectricalScraper** (10 connections) — `scrapers/utilities/yukon_electrical.py`
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
- **.__init__()** (2 connections) — `scrapers/utilities/yukon_electrical.py`
- **Return seed/fallback data based on known published rates.** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- **Scrape Yukon Electrical Company electricity rates.** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- **Attempt to scrape live Yukon Electrical rates. Falls back to seed data if the…** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- **Reuse the joint-schedule parser; unproven seed classes stay labelled estimates.** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- **Scrape Yukon Energy Corporation electricity rates.** (1 connections) — `scrapers/utilities/yukon_energy.py`
- **Attempt to scrape live Yukon Energy rates. Falls back to seed data if the live…** (1 connections) — `scrapers/utilities/yukon_energy.py`
- **Parse live residential/general-service schedules; unparsed seed classes stay…** (1 connections) — `scrapers/utilities/yukon_energy.py`
- **Return the newest model-JSON book link not later than the current UTC month;…** (1 connections) — `scrapers/utilities/yukon_energy.py`
- **Fetch the joint YECL/YEC rate-schedule book; None if unavailable or not the…** (1 connections) — `scrapers/utilities/yukon_energy.py`
- **Return residential schedules only when 1160, percentage riders, fuel and relief…** (1 connections) — `scrapers/utilities/yukon_energy.py`
- *... and 3 more nodes in this community*

## Relationships

- [RateComponent](RateComponent.md) (13 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (10 shared connections)
- [extract_pdf_pages](extract_pdf_pages.md) (10 shared connections)
- [BaseScraper](BaseScraper.md) (6 shared connections)
- [DocumentPage](DocumentPage.md) (4 shared connections)
- [.__init__](__init__.md) (2 shared connections)
- [re](re.md) (2 shared connections)
- [_strings](_strings.md) (1 shared connections)

## Source Files

- `scrapers/utilities/yukon_electrical.py`
- `scrapers/utilities/yukon_energy.py`

## Audit Trail

- EXTRACTED: 81 (92%)
- INFERRED: 7 (8%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*