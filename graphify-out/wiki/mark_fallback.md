# .mark_fallback

> 39 nodes

## Key Concepts

- **.mark_fallback()** (44 connections) — `scrapers/base.py`
- **YukonEnergyScraper** (20 connections) — `scrapers/utilities/yukon_energy.py`
- **._parse_residential_pdfs()** (15 connections) — `scrapers/utilities/yukon_energy.py`
- **.live_records()** (12 connections) — `scrapers/utilities/yukon_energy.py`
- **YukonElectricalScraper** (10 connections) — `scrapers/utilities/yukon_electrical.py`
- **._joint_schedule()** (9 connections) — `scrapers/utilities/yukon_energy.py`
- **._try_live_scrape()** (8 connections) — `scrapers/utilities/yukon_electrical.py`
- **._general_service_records()** (7 connections) — `scrapers/utilities/yukon_energy.py`
- **._try_live_scrape()** (7 connections) — `scrapers/utilities/yukon_energy.py`
- **.scrape()** (6 connections) — `scrapers/utilities/nl_hydro.py`
- **.scrape()** (6 connections) — `scrapers/utilities/yukon_electrical.py`
- **._seed_data()** (6 connections) — `scrapers/utilities/yukon_electrical.py`
- **._discover_joint_schedule()** (6 connections) — `scrapers/utilities/yukon_energy.py`
- **.scrape()** (6 connections) — `scrapers/utilities/yukon_energy.py`
- **._seed_data()** (6 connections) — `scrapers/utilities/yukon_energy.py`
- **._seed_data()** (5 connections) — `scrapers/utilities/nl_hydro.py`
- **parse_joint_schedules()** (5 connections) — `scrapers/utilities/yukon_energy.py`
- **rider_a_terms()** (5 connections) — `scrapers/utilities/yukon_energy.py`
- **._page_of()** (4 connections) — `scrapers/utilities/yukon_energy.py`
- **._residential_base_values()** (3 connections) — `scrapers/utilities/yukon_energy.py`
- **Label seed output conservatively and visibly. A fallback is useful historical…** (1 connections) — `scrapers/base.py`
- **Return seed/fallback data based on known published rates.** (1 connections) — `scrapers/utilities/nl_hydro.py`
- **Attempt to scrape live NL Hydro rates. Classes the live schedule cannot prove…** (1 connections) — `scrapers/utilities/nl_hydro.py`
- **Return seed/fallback data based on known published rates.** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- **Scrape Yukon Electrical Company electricity rates.** (1 connections) — `scrapers/utilities/yukon_electrical.py`
- *... and 14 more nodes in this community*

## Relationships

- [BCHydroScraper](BCHydroScraper.md) (26 shared connections)
- [BaseScraper](BaseScraper.md) (12 shared connections)
- [.fetch_page](fetch_page.md) (11 shared connections)
- [RateComponent](RateComponent.md) (9 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (8 shared connections)
- [.__init__](__init__.md) (2 shared connections)
- [FortisAlbertaScraper](FortisAlbertaScraper.md) (2 shared connections)
- [._parse_commercial](_parse_commercial.md) (2 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (2 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (2 shared connections)
- [enmax_power.py](enmax_power.py.md) (2 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (1 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/nl_hydro.py`
- `scrapers/utilities/yukon_electrical.py`
- `scrapers/utilities/yukon_energy.py`

## Audit Trail

- EXTRACTED: 143 (94%)
- INFERRED: 9 (6%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*