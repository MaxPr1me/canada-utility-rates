# extract_effective_date

> 26 nodes

## Key Concepts

- **extract_effective_date()** (26 connections) — `scrapers/utils/parsing.py`
- **.now_iso()** (19 connections) — `scrapers/base.py`
- **._try_live_scrape()** (17 connections) — `scrapers/utilities/saskpower.py`
- **SaskPowerScraper** (16 connections) — `scrapers/utilities/saskpower.py`
- **._parse_business_tariff()** (10 connections) — `scrapers/utilities/bc_hydro.py`
- **._parse_residential_schedules()** (9 connections) — `scrapers/utilities/saskpower.py`
- **._parse_transformation()** (9 connections) — `scrapers/utilities/saskpower.py`
- **._parse_residential_pdf()** (8 connections) — `scrapers/utilities/saskpower.py`
- **._parse_farm_rates()** (8 connections) — `scrapers/utilities/saskpower.py`
- **._parse_supplied_services()** (8 connections) — `scrapers/utilities/saskpower.py`
- **._parse_standard_charges()** (6 connections) — `scrapers/utilities/bc_hydro.py`
- **._column_values()** (6 connections) — `scrapers/utilities/saskpower.py`
- **.scrape()** (6 connections) — `scrapers/utilities/saskpower.py`
- **._seed_data()** (6 connections) — `scrapers/utilities/saskpower.py`
- **add()** (3 connections) — `scrapers/utilities/bc_hydro.py`
- **schedule()** (2 connections) — `scrapers/utilities/bc_hydro.py`
- **schedule()** (2 connections) — `scrapers/utilities/bc_hydro.py`
- **section()** (2 connections) — `scrapers/utilities/bc_hydro.py`
- **amount()** (1 connections) — `scrapers/utilities/bc_hydro.py`
- **Current UTC time as ISO-8601 string.** (1 connections) — `scrapers/base.py`
- **Keep the combined E01/E03 identity only while both source columns match.** (1 connections) — `scrapers/utilities/saskpower.py`
- **Return seed/fallback data based on known published rates.** (1 connections) — `scrapers/utilities/saskpower.py`
- **Scrape SaskPower electricity rates.** (1 connections) — `scrapers/utilities/saskpower.py`
- **Attempt to scrape live SaskPower rates. Falls back to seed data if the live…** (1 connections) — `scrapers/utilities/saskpower.py`
- **Discover independent schedules and retain per-class fallback provenance.** (1 connections) — `scrapers/utilities/saskpower.py`
- *... and 1 more nodes in this community*

## Relationships

- [BCHydroScraper](BCHydroScraper.md) (20 shared connections)
- [RateComponent](RateComponent.md) (15 shared connections)
- [BaseScraper](BaseScraper.md) (14 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (10 shared connections)
- [.mark_fallback](mark_fallback.md) (3 shared connections)
- [._try_live_scrape](_try_live_scrape.md) (2 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (2 shared connections)
- [.__init__](__init__.md) (1 shared connections)
- [ntpc.py](ntpc.py.md) (1 shared connections)
- [.fetch_page](fetch_page.md) (1 shared connections)
- [NewfoundlandPowerScraper](NewfoundlandPowerScraper.md) (1 shared connections)
- [re](re.md) (1 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/bc_hydro.py`
- `scrapers/utilities/saskpower.py`
- `scrapers/utils/parsing.py`

## Audit Trail

- EXTRACTED: 118 (98%)
- INFERRED: 3 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*