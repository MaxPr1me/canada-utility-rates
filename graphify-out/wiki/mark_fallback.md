# .mark_fallback

> 47 nodes

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
- **.scrape()** (6 connections) — `scrapers/utilities/atco_electric.py`
- **.scrape()** (6 connections) — `scrapers/utilities/manitoba_hydro.py`
- **._seed_data()** (6 connections) — `scrapers/utilities/manitoba_hydro.py`
- **.scrape()** (6 connections) — `scrapers/utilities/newfoundland_power.py`
- **.scrape()** (6 connections) — `scrapers/utilities/nl_hydro.py`
- **.scrape()** (6 connections) — `scrapers/utilities/yukon_electrical.py`
- **._seed_data()** (6 connections) — `scrapers/utilities/yukon_electrical.py`
- **._discover_joint_schedule()** (6 connections) — `scrapers/utilities/yukon_energy.py`
- **.scrape()** (6 connections) — `scrapers/utilities/yukon_energy.py`
- **._seed_data()** (6 connections) — `scrapers/utilities/yukon_energy.py`
- **._seed_data()** (5 connections) — `scrapers/utilities/atco_electric.py`
- **._seed_data()** (5 connections) — `scrapers/utilities/newfoundland_power.py`
- **._seed_data()** (5 connections) — `scrapers/utilities/nl_hydro.py`
- **._page_of()** (4 connections) — `scrapers/utilities/yukon_energy.py`
- **._residential_base_values()** (3 connections) — `scrapers/utilities/yukon_energy.py`
- **Label seed output conservatively and visibly. A fallback is useful historical…** (1 connections) — `scrapers/base.py`
- *... and 22 more nodes in this community*

## Relationships

- [BCHydroScraper](BCHydroScraper.md) (28 shared connections)
- [BaseScraper](BaseScraper.md) (15 shared connections)
- [RateComponent](RateComponent.md) (11 shared connections)
- [.fetch_page](fetch_page.md) (10 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (7 shared connections)
- [re](re.md) (5 shared connections)
- [extract_effective_date](extract_effective_date.md) (3 shared connections)
- [.__init__](__init__.md) (2 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (2 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (2 shared connections)
- [._parse_commercial](_parse_commercial.md) (2 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (2 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/atco_electric.py`
- `scrapers/utilities/manitoba_hydro.py`
- `scrapers/utilities/newfoundland_power.py`
- `scrapers/utilities/nl_hydro.py`
- `scrapers/utilities/yukon_electrical.py`
- `scrapers/utilities/yukon_energy.py`

## Audit Trail

- EXTRACTED: 165 (96%)
- INFERRED: 7 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*