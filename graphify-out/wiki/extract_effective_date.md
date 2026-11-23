# extract_effective_date

> 16 nodes

## Key Concepts

- **.now_iso()** (19 connections) — `scrapers/base.py`
- **SaskPowerScraper** (16 connections) — `scrapers/utilities/saskpower.py`
- **._parse_residential_schedules()** (9 connections) — `scrapers/utilities/saskpower.py`
- **._parse_transformation()** (9 connections) — `scrapers/utilities/saskpower.py`
- **._parse_residential_pdf()** (8 connections) — `scrapers/utilities/saskpower.py`
- **._parse_farm_rates()** (8 connections) — `scrapers/utilities/saskpower.py`
- **._parse_supplied_services()** (8 connections) — `scrapers/utilities/saskpower.py`
- **._column_values()** (6 connections) — `scrapers/utilities/saskpower.py`
- **.scrape()** (6 connections) — `scrapers/utilities/saskpower.py`
- **._seed_data()** (6 connections) — `scrapers/utilities/saskpower.py`
- **.__init__()** (2 connections) — `scrapers/utilities/saskpower.py`
- **Current UTC time as ISO-8601 string.** (1 connections) — `scrapers/base.py`
- **Keep the combined E01/E03 identity only while both source columns match.** (1 connections) — `scrapers/utilities/saskpower.py`
- **Return seed/fallback data based on known published rates.** (1 connections) — `scrapers/utilities/saskpower.py`
- **Scrape SaskPower electricity rates.** (1 connections) — `scrapers/utilities/saskpower.py`
- **Attempt to scrape live SaskPower rates. Falls back to seed data if the live…** (1 connections) — `scrapers/utilities/saskpower.py`

## Relationships

- [BCHydroScraper](BCHydroScraper.md) (12 shared connections)
- [BaseScraper](BaseScraper.md) (9 shared connections)
- [RateComponent](RateComponent.md) (9 shared connections)
- [.fetch_page](fetch_page.md) (7 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (5 shared connections)
- [.mark_fallback](mark_fallback.md) (3 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (1 shared connections)
- [ntpc.py](ntpc.py.md) (1 shared connections)
- [.__init__](__init__.md) (1 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/saskpower.py`

## Audit Trail

- EXTRACTED: 72 (96%)
- INFERRED: 3 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*