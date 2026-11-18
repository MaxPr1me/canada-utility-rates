# .now_iso

> 20 nodes

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
- **add()** (3 connections) — `scrapers/utilities/bc_hydro.py`
- **schedule()** (2 connections) — `scrapers/utilities/bc_hydro.py`
- **amount()** (1 connections) — `scrapers/utilities/bc_hydro.py`
- **Current UTC time as ISO-8601 string.** (1 connections) — `scrapers/base.py`
- **Keep the combined E01/E03 identity only while both source columns match.** (1 connections) — `scrapers/utilities/saskpower.py`
- **Scrape SaskPower electricity rates.** (1 connections) — `scrapers/utilities/saskpower.py`
- **Discover independent schedules and retain per-class fallback provenance.** (1 connections) — `scrapers/utilities/saskpower.py`
- **Extract an explicitly labelled effective date as ISO-8601.** (1 connections) — `scrapers/utils/parsing.py`

## Relationships

- [BCHydroScraper](BCHydroScraper.md) (22 shared connections)
- [BaseScraper](BaseScraper.md) (14 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (11 shared connections)
- [.mark_fallback](mark_fallback.md) (9 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (8 shared connections)
- [.fetch_page](fetch_page.md) (3 shared connections)
- [FortisAlbertaScraper](FortisAlbertaScraper.md) (2 shared connections)
- [ntpc.py](ntpc.py.md) (1 shared connections)
- [re](re.md) (1 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/bc_hydro.py`
- `scrapers/utilities/saskpower.py`
- `scrapers/utils/parsing.py`

## Audit Trail

- EXTRACTED: 109 (97%)
- INFERRED: 3 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*