# YukonEnergyScraper

> 38 nodes

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
- **parse_joint_schedules()** (5 connections) — `scrapers/utilities/yukon_energy.py`
- **rider_a_terms()** (5 connections) — `scrapers/utilities/yukon_energy.py`
- **._page_of()** (4 connections) — `scrapers/utilities/yukon_energy.py`
- **._residential_base_values()** (3 connections) — `scrapers/utilities/yukon_energy.py`
- **Any** (2 connections)
- **Return seed/fallback data based on known published rates.** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- **Scrape Yukon Electrical Company electricity rates.** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- **Attempt to scrape live Yukon Electrical rates. Falls back to seed data if the…** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- **Reuse the joint-schedule parser; unproven seed classes stay labelled estimates.** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- **Return {absolute link: "YYYY-MM" edition} for joint-book PDFs named anywhere in…** (1 connections) — `scrapers/utilities/yukon_energy.py`
- *... and 13 more nodes in this community*

## Relationships

- [TariffRecord](TariffRecord.md) (15 shared connections)
- [BaseScraper](BaseScraper.md) (12 shared connections)
- [extract_pdf_pages](extract_pdf_pages.md) (7 shared connections)
- [RateComponent](RateComponent.md) (6 shared connections)
- [DocumentPage](DocumentPage.md) (6 shared connections)
- [.__init__](__init__.md) (2 shared connections)
- [re](re.md) (2 shared connections)
- [.now_iso](now_iso.md) (2 shared connections)
- [parse_html](parse_html.md) (2 shared connections)
- [parse_rolr_page](parse_rolr_page.md) (1 shared connections)
- [ENMAXEnergyScraper](ENMAXEnergyScraper.md) (1 shared connections)

## Source Files

- `scrapers/utilities/yukon_electrical.py`
- `scrapers/utilities/yukon_energy.py`

## Audit Trail

- EXTRACTED: 102 (92%)
- INFERRED: 9 (8%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*