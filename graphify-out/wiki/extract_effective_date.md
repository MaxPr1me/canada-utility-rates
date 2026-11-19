# extract_effective_date

> 32 nodes

## Key Concepts

- **extract_effective_date()** (26 connections) — `scrapers/utils/parsing.py`
- **.now_iso()** (19 connections) — `scrapers/base.py`
- **._try_live_scrape()** (17 connections) — `scrapers/utilities/saskpower.py`
- **SaskPowerScraper** (16 connections) — `scrapers/utilities/saskpower.py`
- **._order_context()** (11 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._try_live_commercial()** (9 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._parse_residential_schedules()** (9 connections) — `scrapers/utilities/saskpower.py`
- **._parse_transformation()** (9 connections) — `scrapers/utilities/saskpower.py`
- **._parse_residential_pdf()** (8 connections) — `scrapers/utilities/saskpower.py`
- **._parse_business_pilot_tariffs()** (8 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._parse_business_tariffs()** (8 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._parse_industrial_tariffs()** (8 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._parse_farm_rates()** (8 connections) — `scrapers/utilities/saskpower.py`
- **._parse_supplied_services()** (8 connections) — `scrapers/utilities/saskpower.py`
- **._column_values()** (6 connections) — `scrapers/utilities/saskpower.py`
- **.scrape()** (6 connections) — `scrapers/utilities/saskpower.py`
- **._seed_data()** (6 connections) — `scrapers/utilities/saskpower.py`
- **schedule()** (2 connections) — `scrapers/utilities/bc_hydro.py`
- **schedule()** (2 connections) — `scrapers/utilities/bc_hydro.py`
- **section()** (2 connections) — `scrapers/utilities/bc_hydro.py`
- **Current UTC time as ISO-8601 string.** (1 connections) — `scrapers/base.py`
- **Parse Rate 21/22/23 and the Rate 25 Interruptible Rider independently; a failed…** (1 connections) — `scrapers/utilities/nova_scotia_power.py`
- **Parse Rates 72/73/82/83 independently; a failed pilot is logged and omitted.** (1 connections) — `scrapers/utilities/nova_scotia_power.py`
- **Return (book year, Board-order date, today, year end) when the dated book is…** (1 connections) — `scrapers/utilities/nova_scotia_power.py`
- **Parse Rate 10/11/12 from the tariff book already fetched for residential…** (1 connections) — `scrapers/utilities/nova_scotia_power.py`
- *... and 7 more nodes in this community*

## Relationships

- [BCHydroScraper](BCHydroScraper.md) (23 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (22 shared connections)
- [BaseScraper](BaseScraper.md) (13 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (10 shared connections)
- [RateComponent](RateComponent.md) (6 shared connections)
- [parse_html](parse_html.md) (4 shared connections)
- [.mark_fallback](mark_fallback.md) (3 shared connections)
- [.fetch_page](fetch_page.md) (3 shared connections)
- [._try_live_scrape](_try_live_scrape.md) (2 shared connections)
- [.__init__](__init__.md) (1 shared connections)
- [ntpc.py](ntpc.py.md) (1 shared connections)
- [maritime_electric.py](maritime_electric.py.md) (1 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/bc_hydro.py`
- `scrapers/utilities/nova_scotia_power.py`
- `scrapers/utilities/saskpower.py`
- `scrapers/utils/parsing.py`

## Audit Trail

- EXTRACTED: 142 (98%)
- INFERRED: 3 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*