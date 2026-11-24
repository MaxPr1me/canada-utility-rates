# .now_iso

> 32 nodes

## Key Concepts

- **extract_effective_date()** (26 connections) — `scrapers/utils/parsing.py`
- **.now_iso()** (19 connections) — `scrapers/base.py`
- **._try_live_scrape()** (17 connections) — `scrapers/utilities/saskpower.py`
- **SaskPowerScraper** (16 connections) — `scrapers/utilities/saskpower.py`
- **._order_context()** (11 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._parse_residential_tariffs()** (11 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._parse_residential_schedules()** (9 connections) — `scrapers/utilities/saskpower.py`
- **._parse_transformation()** (9 connections) — `scrapers/utilities/saskpower.py`
- **._parse_residential_pdf()** (8 connections) — `scrapers/utilities/saskpower.py`
- **._parse_farm_rates()** (8 connections) — `scrapers/utilities/saskpower.py`
- **._parse_supplied_services()** (8 connections) — `scrapers/utilities/saskpower.py`
- **._parse_building_option_tariffs()** (6 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._column_values()** (6 connections) — `scrapers/utilities/saskpower.py`
- **.scrape()** (6 connections) — `scrapers/utilities/saskpower.py`
- **._seed_data()** (6 connections) — `scrapers/utilities/saskpower.py`
- **amounts()** (3 connections) — `scrapers/utilities/nova_scotia_power.py`
- **schedule()** (2 connections) — `scrapers/utilities/bc_hydro.py`
- **schedule()** (2 connections) — `scrapers/utilities/bc_hydro.py`
- **section()** (2 connections) — `scrapers/utilities/bc_hydro.py`
- **numeric_line()** (2 connections) — `scrapers/utilities/nova_scotia_power.py`
- **rider_row()** (2 connections) — `scrapers/utilities/nova_scotia_power.py`
- **current_charge()** (1 connections) — `scrapers/utilities/nova_scotia_power.py`
- **Current UTC time as ISO-8601 string.** (1 connections) — `scrapers/base.py`
- **Return (book year, Board-order date, today, year end) when the dated book is…** (1 connections) — `scrapers/utilities/nova_scotia_power.py`
- **Parse the current approved book, separating tariff phases and rider totals.** (1 connections) — `scrapers/utilities/nova_scotia_power.py`
- *... and 7 more nodes in this community*

## Relationships

- [TariffRecord](TariffRecord.md) (21 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (18 shared connections)
- [BaseScraper](BaseScraper.md) (15 shared connections)
- [DocumentPage](DocumentPage.md) (9 shared connections)
- [RateComponent](RateComponent.md) (5 shared connections)
- [.mark_fallback](mark_fallback.md) (3 shared connections)
- [.fetch_page](fetch_page.md) (2 shared connections)
- [ENMAXPowerScraper](ENMAXPowerScraper.md) (2 shared connections)
- [ntpc.py](ntpc.py.md) (2 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (1 shared connections)
- [re](re.md) (1 shared connections)
- [bc_hydro.py](bc_hydro.py.md) (1 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/bc_hydro.py`
- `scrapers/utilities/nova_scotia_power.py`
- `scrapers/utilities/saskpower.py`
- `scrapers/utils/parsing.py`

## Audit Trail

- EXTRACTED: 132 (98%)
- INFERRED: 3 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*