# MaritimeElectricScraper

> 24 nodes

## Key Concepts

- **MaritimeElectricScraper** (20 connections) — `scrapers/utilities/maritime_electric.py`
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
- **.__init__()** (2 connections) — `scrapers/utilities/maritime_electric.py`
- **Scrape Maritime Electric electricity rates.** (1 connections) — `scrapers/utilities/maritime_electric.py`
- **Attempt to scrape live Maritime Electric rates. Falls back to seed data if the…** (1 connections) — `scrapers/utilities/maritime_electric.py`
- **Parse non-lighting service classes from the rate page; each class fails alone.** (1 connections) — `scrapers/utilities/maritime_electric.py`
- **Build one record; None unless the class has exactly its expected components.** (1 connections) — `scrapers/utilities/maritime_electric.py`
- **Cross-check industrial/wholesale classes against their Section N schedules;…** (1 connections) — `scrapers/utilities/maritime_electric.py`
- **Turn one '... Charge ... $ value' schedule line into a RateComponent.** (1 connections) — `scrapers/utilities/maritime_electric.py`
- **Return seed/fallback data based on known published rates.** (1 connections) — `scrapers/utilities/maritime_electric.py`

## Relationships

- [NBPowerScraper](NBPowerScraper.md) (12 shared connections)
- [re](re.md) (8 shared connections)
- [TariffRecord](TariffRecord.md) (7 shared connections)
- [.fetch_page](fetch_page.md) (4 shared connections)
- [DocumentPage](DocumentPage.md) (2 shared connections)
- [BaseScraper](BaseScraper.md) (1 shared connections)
- [.__init__](__init__.md) (1 shared connections)

## Source Files

- `scrapers/utilities/maritime_electric.py`

## Audit Trail

- EXTRACTED: 71 (96%)
- INFERRED: 3 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*