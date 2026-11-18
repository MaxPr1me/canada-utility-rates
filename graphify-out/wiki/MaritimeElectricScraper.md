# MaritimeElectricScraper

> 25 nodes

## Key Concepts

- **MaritimeElectricScraper** (20 connections) — `scrapers/utilities/maritime_electric.py`
- **._try_live_scrape()** (13 connections) — `scrapers/utilities/maritime_electric.py`
- **._apply_large_industrial()** (8 connections) — `scrapers/utilities/maritime_electric.py`
- **._apply_small_industrial()** (7 connections) — `scrapers/utilities/maritime_electric.py`
- **._apply_wholesale()** (7 connections) — `scrapers/utilities/maritime_electric.py`
- **._parse_pages()** (7 connections) — `scrapers/utilities/maritime_electric.py`
- **._build_record()** (6 connections) — `scrapers/utilities/maritime_electric.py`
- **._pdf_parts()** (6 connections) — `scrapers/utilities/maritime_electric.py`
- **.scrape()** (6 connections) — `scrapers/utilities/maritime_electric.py`
- **._parse_component_line()** (5 connections) — `scrapers/utilities/maritime_electric.py`
- **_expect_amounts()** (5 connections) — `scrapers/utilities/maritime_electric.py`
- **._apply_schedules()** (5 connections) — `scrapers/utilities/maritime_electric.py`
- **._cross_checked()** (5 connections) — `scrapers/utilities/maritime_electric.py`
- **._seed_data()** (5 connections) — `scrapers/utilities/maritime_electric.py`
- **._page_component()** (4 connections) — `scrapers/utilities/maritime_electric.py`
- **_require()** (4 connections) — `scrapers/utilities/maritime_electric.py`
- **_section()** (4 connections) — `scrapers/utilities/maritime_electric.py`
- **Scrape Maritime Electric electricity rates.** (1 connections) — `scrapers/utilities/maritime_electric.py`
- **Attempt to scrape live Maritime Electric rates. Falls back to seed data if the…** (1 connections) — `scrapers/utilities/maritime_electric.py`
- **Parse every non-lighting service class from the official Schedule of Adjusted…** (1 connections) — `scrapers/utilities/maritime_electric.py`
- **Parse non-lighting service classes from the rate page; each class fails alone.** (1 connections) — `scrapers/utilities/maritime_electric.py`
- **Build one record; None unless the class has exactly its expected components.** (1 connections) — `scrapers/utilities/maritime_electric.py`
- **Cross-check industrial/wholesale classes against their Section N schedules;…** (1 connections) — `scrapers/utilities/maritime_electric.py`
- **Turn one '... Charge ... $ value' schedule line into a RateComponent.** (1 connections) — `scrapers/utilities/maritime_electric.py`
- **Return seed/fallback data based on known published rates.** (1 connections) — `scrapers/utilities/maritime_electric.py`

## Relationships

- [BCHydroScraper](BCHydroScraper.md) (13 shared connections)
- [re](re.md) (8 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (6 shared connections)
- [BaseScraper](BaseScraper.md) (3 shared connections)
- [.fetch_page](fetch_page.md) (3 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (2 shared connections)
- [.mark_fallback](mark_fallback.md) (2 shared connections)
- [FortisAlbertaScraper](FortisAlbertaScraper.md) (1 shared connections)
- [io](io.md) (1 shared connections)

## Source Files

- `scrapers/utilities/maritime_electric.py`

## Audit Trail

- EXTRACTED: 79 (96%)
- INFERRED: 3 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*