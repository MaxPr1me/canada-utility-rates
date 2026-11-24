# io

> 25 nodes

## Key Concepts

- **io** (40 connections)
- **csv** (22 connections)
- **export_ontario_totals.py** (20 connections) — `scripts/export_ontario_totals.py`
- **parse_lfda_csv()** (10 connections) — `scripts/archive_ontario_price.py`
- **load_hoep_csv()** (8 connections) — `scripts/build_ontario_market.py`
- **main()** (7 connections) — `scripts/export_ontario_totals.py`
- **read_xlsx_tables()** (5 connections) — `scrapers/utils/parsing.py`
- **build()** (5 connections) — `scripts/export_ontario_totals.py`
- **check_no_loss()** (5 connections) — `scripts/export_ontario_totals.py`
- **read_csv_rows()** (4 connections) — `scrapers/utils/parsing.py`
- **_csv()** (4 connections) — `scripts/export_ontario_totals.py`
- **extract_pdf_tables()** (3 connections) — `scrapers/utils/parsing.py`
- **cents()** (3 connections) — `scripts/export_ontario_totals.py`
- **parse_args()** (3 connections) — `scripts/export_ontario_totals.py`
- **load_supplement()** (2 connections) — `scripts/export_ontario_totals.py`
- **Decimal** (2 connections)
- **_load_market()** (1 connections) — `scripts/export_ontario_totals.py`
- **date** (1 connections)
- **Path** (1 connections)
- **Read an Excel file and return a dict of sheet_name -> rows. Each row is a list…** (1 connections) — `scrapers/utils/parsing.py`
- **Read an official UTF-8/UTF-8-BOM CSV into named rows.** (1 connections) — `scrapers/utils/parsing.py`
- **Extract tables from a PDF using pdfplumber. Returns the same format as…** (1 connections) — `scrapers/utils/parsing.py`
- **{(date, hour ending): (LFDA in $/MWh, or None when published blank; status)}…** (1 connections) — `scripts/archive_ontario_price.py`
- **{(date, hour ending): legacy HOEP in $/MWh} from data/market/hoep_hourly.csv;…** (1 connections) — `scripts/build_ontario_market.py`
- **Export hourly/monthly energy + Class B GA totals in CAD cents/kWh, without…** (1 connections) — `scripts/export_ontario_totals.py`

## Relationships

- [archive_ontario_price.py](archive_ontario_price.py.md) (14 shared connections)
- [build_ontario_market.py](build_ontario_market.py.md) (13 shared connections)
- [parsing.py](parsing.py.md) (6 shared connections)
- [build_alberta_market.py](build_alberta_market.py.md) (6 shared connections)
- [aeso.py](aeso.py.md) (5 shared connections)
- [run_scrape.py](run_scrape.py.md) (4 shared connections)
- [BaseScraper](BaseScraper.md) (3 shared connections)
- [generate_market_pricing.py](generate_market_pricing.py.md) (3 shared connections)
- [graphify_hook.py](graphify_hook.py.md) (2 shared connections)
- [check_db_history.py](check_db_history.py.md) (2 shared connections)
- [oeb_tariff.py](oeb_tariff.py.md) (2 shared connections)
- [MarketDataError](MarketDataError.md) (2 shared connections)

## Source Files

- `scrapers/utils/parsing.py`
- `scripts/archive_ontario_price.py`
- `scripts/build_ontario_market.py`
- `scripts/export_ontario_totals.py`

## Audit Trail

- EXTRACTED: 114 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*