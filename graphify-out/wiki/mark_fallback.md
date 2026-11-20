# .mark_fallback

> 30 nodes

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
- **Return only live-parsed records (no seeds), or None when 1160 cannot be proven.** (1 connections) — `scrapers/utilities/yukon_energy.py`
- **Return the newest model-JSON book link not later than the current UTC month;…** (1 connections) — `scrapers/utilities/yukon_energy.py`
- *... and 5 more nodes in this community*

## Relationships

- [BCHydroScraper](BCHydroScraper.md) (11 shared connections)
- [RateComponent](RateComponent.md) (10 shared connections)
- [extract_pdf_pages](extract_pdf_pages.md) (9 shared connections)
- [BaseScraper](BaseScraper.md) (8 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (4 shared connections)
- [.__init__](__init__.md) (2 shared connections)
- [extract_effective_date](extract_effective_date.md) (2 shared connections)
- [parse_html](parse_html.md) (2 shared connections)
- [re](re.md) (2 shared connections)
- [_strings](_strings.md) (1 shared connections)

## Source Files

- `scrapers/utilities/yukon_electrical.py`
- `scrapers/utilities/yukon_energy.py`

## Audit Trail

- EXTRACTED: 89 (93%)
- INFERRED: 7 (7%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*