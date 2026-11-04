# io

> 30 nodes

## Key Concepts

- **io** (36 connections)
- **aeso.py** (24 connections) — `scrapers/utilities/aeso.py`
- **csv** (22 connections)
- **._try_live_scrape()** (12 connections) — `scrapers/utilities/aeso.py`
- **parse_pool_price_csv()** (12 connections) — `scrapers/utilities/aeso.py`
- **AESOVerificationError** (8 connections) — `scrapers/utilities/aeso.py`
- **parse_metadata()** (7 connections) — `scrapers/utilities/aeso.py`
- **report_csv_url()** (7 connections) — `scrapers/utilities/aeso.py`
- **verify_recent_prices()** (5 connections) — `scrapers/utilities/aeso.py`
- **serialize_monthly()** (5 connections) — `scripts/build_ontario_market.py`
- **check_no_loss()** (5 connections) — `scripts/export_ontario_totals.py`
- **read_csv_rows()** (4 connections) — `scrapers/utils/parsing.py`
- **get_hours()** (4 connections) — `scripts/build_alberta_market.py`
- **csv_bytes()** (4 connections) — `scripts/build_alberta_market.py`
- **serialize_hoep()** (4 connections) — `scripts/build_ontario_market.py`
- **date** (4 connections)
- **_today()** (3 connections) — `scrapers/utilities/aeso.py`
- **extract_pdf_tables()** (3 connections) — `scrapers/utils/parsing.py`
- **read_xlsx_tables()** (3 connections) — `scrapers/utils/parsing.py`
- **ValueError** (1 connections)
- **Path** (1 connections)
- **aeso.py -- Scraper for Alberta Electric System Operator (AESO) pool price. AESO…** (1 connections) — `scrapers/utilities/aeso.py`
- **Require enough recent posted hours; returns the latest posted date.** (1 connections) — `scrapers/utilities/aeso.py`
- **Check the metadata text still defines the pool price and return the document…** (1 connections) — `scrapers/utilities/aeso.py`
- **An official AESO source is missing, changed shape or is out of date.** (1 connections) — `scrapers/utilities/aeso.py`
- *... and 5 more nodes in this community*

## Relationships

- [build_alberta_market.py](build_alberta_market.py.md) (20 shared connections)
- [BaseScraper](BaseScraper.md) (12 shared connections)
- [build_ontario_market.py](build_ontario_market.py.md) (9 shared connections)
- [archive_ontario_price.py](archive_ontario_price.py.md) (8 shared connections)
- [generate_market_pricing.py](generate_market_pricing.py.md) (7 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (6 shared connections)
- [export_ontario_totals.py](export_ontario_totals.py.md) (6 shared connections)
- [re](re.md) (3 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (3 shared connections)
- [.fetch_page](fetch_page.md) (2 shared connections)
- [main](main.md) (2 shared connections)
- [EnbridgeGasScraper](EnbridgeGasScraper.md) (2 shared connections)

## Source Files

- `scrapers/utilities/aeso.py`
- `scrapers/utils/parsing.py`
- `scripts/build_alberta_market.py`
- `scripts/build_ontario_market.py`
- `scripts/export_ontario_totals.py`

## Audit Trail

- EXTRACTED: 134 (99%)
- INFERRED: 2 (1%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*