# .mark_fallback

> 32 nodes

## Key Concepts

- **.fetch_bytes()** (37 connections) — `scrapers/base.py`
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
- **GET a URL and return raw bytes (for PDFs, spreadsheets).** (1 connections) — `scrapers/base.py`
- **Return seed/fallback data based on known published rates.** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- **Scrape Yukon Electrical Company electricity rates.** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- **Attempt to scrape live Yukon Electrical rates. Falls back to seed data if the…** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- **Reuse the joint-schedule parser; unproven seed classes stay labelled estimates.** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- **Scrape Yukon Energy Corporation electricity rates.** (1 connections) — `scrapers/utilities/yukon_energy.py`
- **Attempt to scrape live Yukon Energy rates. Falls back to seed data if the live…** (1 connections) — `scrapers/utilities/yukon_energy.py`
- **Parse live residential/general-service schedules; unparsed seed classes stay…** (1 connections) — `scrapers/utilities/yukon_energy.py`
- *... and 7 more nodes in this community*

## Relationships

- [BaseScraper](BaseScraper.md) (13 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (13 shared connections)
- [.fetch_page](fetch_page.md) (11 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (7 shared connections)
- [.mark_fallback](mark_fallback.md) (6 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (5 shared connections)
- [.now_iso](now_iso.md) (4 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (2 shared connections)
- [FortisAlbertaScraper](FortisAlbertaScraper.md) (2 shared connections)
- [ntpc.py](ntpc.py.md) (2 shared connections)
- [re](re.md) (2 shared connections)
- [aeso.py](aeso.py.md) (1 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/yukon_electrical.py`
- `scrapers/utilities/yukon_energy.py`

## Audit Trail

- EXTRACTED: 124 (95%)
- INFERRED: 7 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*