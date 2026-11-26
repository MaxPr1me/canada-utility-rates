# aeso.py

> 19 nodes

## Key Concepts

- **aeso.py** (24 connections) — `scrapers/utilities/aeso.py`
- **._try_live_scrape()** (12 connections) — `scrapers/utilities/aeso.py`
- **parse_pool_price_csv()** (12 connections) — `scrapers/utilities/aeso.py`
- **AESOVerificationError** (8 connections) — `scrapers/utilities/aeso.py`
- **parse_metadata()** (7 connections) — `scrapers/utilities/aeso.py`
- **report_csv_url()** (7 connections) — `scrapers/utilities/aeso.py`
- **metadata_document()** (6 connections) — `scrapers/utilities/aeso.py`
- **verify_recent_prices()** (5 connections) — `scrapers/utilities/aeso.py`
- **get_hours()** (4 connections) — `scripts/build_alberta_market.py`
- **date** (4 connections)
- **_today()** (3 connections) — `scrapers/utilities/aeso.py`
- **ValueError** (1 connections)
- **aeso.py -- Scraper for Alberta Electric System Operator (AESO) pool price. AESO…** (1 connections) — `scrapers/utilities/aeso.py`
- **Require enough recent posted hours; returns the latest posted date.** (1 connections) — `scrapers/utilities/aeso.py`
- **Check the metadata text still defines the pool price and return the document…** (1 connections) — `scrapers/utilities/aeso.py`
- **(text, PDF modification date such as "D:20250528113723-06'00'").** (1 connections) — `scrapers/utilities/aeso.py`
- **An official AESO source is missing, changed shape or is out of date.** (1 connections) — `scrapers/utilities/aeso.py`
- **ETS report URL; the end date is exclusive.** (1 connections) — `scrapers/utilities/aeso.py`
- **Posted hourly prices as (date, hour-ending label, $/MWh). Hours not yet posted…** (1 connections) — `scrapers/utilities/aeso.py`

## Relationships

- [build_alberta_market.py](build_alberta_market.py.md) (13 shared connections)
- [RateComponent](RateComponent.md) (5 shared connections)
- [io](io.md) (5 shared connections)
- [BaseScraper](BaseScraper.md) (5 shared connections)
- [re](re.md) (3 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (3 shared connections)
- [parse_html](parse_html.md) (2 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (2 shared connections)
- [market_pricing.py](market_pricing.py.md) (2 shared connections)

## Source Files

- `scrapers/utilities/aeso.py`
- `scripts/build_alberta_market.py`

## Audit Trail

- EXTRACTED: 68 (97%)
- INFERRED: 2 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*