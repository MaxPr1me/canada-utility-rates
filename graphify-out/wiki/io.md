# io

> 16 nodes

## Key Concepts

- **io** (36 connections)
- **csv** (22 connections)
- **load_hoep_csv()** (8 connections) — `scripts/build_ontario_market.py`
- **output_bytes()** (7 connections) — `scripts/build_alberta_market.py`
- **serialize_monthly()** (5 connections) — `scripts/build_ontario_market.py`
- **check_no_loss()** (5 connections) — `scripts/export_ontario_totals.py`
- **read_csv_rows()** (4 connections) — `scrapers/utils/parsing.py`
- **csv_bytes()** (4 connections) — `scripts/build_alberta_market.py`
- **_csv()** (4 connections) — `scripts/export_ontario_totals.py`
- **extract_pdf_tables()** (3 connections) — `scrapers/utils/parsing.py`
- **read_xlsx_tables()** (3 connections) — `scrapers/utils/parsing.py`
- **Path** (1 connections)
- **Read an Excel file and return a dict of sheet_name -> rows. Each row is a list…** (1 connections) — `scrapers/utils/parsing.py`
- **Read an official UTF-8/UTF-8-BOM CSV into named rows.** (1 connections) — `scrapers/utils/parsing.py`
- **Extract tables from a PDF using pdfplumber. Returns the same format as…** (1 connections) — `scrapers/utils/parsing.py`
- **{(date, hour ending): legacy HOEP in $/MWh} from data/market/hoep_hourly.csv;…** (1 connections) — `scripts/build_ontario_market.py`

## Relationships

- [build_ontario_market.py](build_ontario_market.py.md) (10 shared connections)
- [build_alberta_market.py](build_alberta_market.py.md) (8 shared connections)
- [archive_ontario_price.py](archive_ontario_price.py.md) (8 shared connections)
- [BaseScraper](BaseScraper.md) (7 shared connections)
- [io](io.md) (6 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (5 shared connections)
- [main](main.md) (3 shared connections)
- [generate_market_pricing.py](generate_market_pricing.py.md) (3 shared connections)
- [MarketDataError](MarketDataError.md) (2 shared connections)
- [.fetch_page](fetch_page.md) (2 shared connections)
- [extract_schedule_pages](extract_schedule_pages.md) (2 shared connections)
- [run_scrape.py](run_scrape.py.md) (1 shared connections)

## Source Files

- `scrapers/utils/parsing.py`
- `scripts/build_alberta_market.py`
- `scripts/build_ontario_market.py`
- `scripts/export_ontario_totals.py`

## Audit Trail

- EXTRACTED: 85 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*