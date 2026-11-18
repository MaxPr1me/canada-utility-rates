# io

> 23 nodes

## Key Concepts

- **io** (36 connections)
- **export_ontario_totals.py** (20 connections) — `scripts/export_ontario_totals.py`
- **collections** (9 connections)
- **main()** (7 connections) — `scripts/export_ontario_totals.py`
- **_extract_pages()** (5 connections) — `scrapers/utilities/maritime_electric.py`
- **build()** (5 connections) — `scripts/export_ontario_totals.py`
- **check_no_loss()** (5 connections) — `scripts/export_ontario_totals.py`
- **read_csv_rows()** (4 connections) — `scrapers/utils/parsing.py`
- **_csv()** (4 connections) — `scripts/export_ontario_totals.py`
- **extract_pdf_tables()** (3 connections) — `scrapers/utils/parsing.py`
- **read_xlsx_tables()** (3 connections) — `scrapers/utils/parsing.py`
- **cents()** (3 connections) — `scripts/export_ontario_totals.py`
- **parse_args()** (3 connections) — `scripts/export_ontario_totals.py`
- **load_supplement()** (2 connections) — `scripts/export_ontario_totals.py`
- **Decimal** (2 connections)
- **_load_market()** (1 connections) — `scripts/export_ontario_totals.py`
- **date** (1 connections)
- **Path** (1 connections)
- **Raw per-page text; the shared normalizer drops repeated rows, which this…** (1 connections) — `scrapers/utilities/maritime_electric.py`
- **Read an Excel file and return a dict of sheet_name -> rows. Each row is a list…** (1 connections) — `scrapers/utils/parsing.py`
- **Read an official UTF-8/UTF-8-BOM CSV into named rows.** (1 connections) — `scrapers/utils/parsing.py`
- **Extract tables from a PDF using pdfplumber. Returns the same format as…** (1 connections) — `scrapers/utils/parsing.py`
- **Export hourly/monthly energy + Class B GA totals in CAD cents/kWh, without…** (1 connections) — `scripts/export_ontario_totals.py`

## Relationships

- [BaseScraper](BaseScraper.md) (7 shared connections)
- [build_alberta_market.py](build_alberta_market.py.md) (7 shared connections)
- [build_ontario_market.py](build_ontario_market.py.md) (6 shared connections)
- [archive_ontario_price.py](archive_ontario_price.py.md) (5 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (3 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (3 shared connections)
- [enmax_power.py](enmax_power.py.md) (3 shared connections)
- [generate_market_pricing.py](generate_market_pricing.py.md) (3 shared connections)
- [aeso.py](aeso.py.md) (3 shared connections)
- [re](re.md) (2 shared connections)
- [os](os.md) (2 shared connections)
- [argparse](argparse.md) (2 shared connections)

## Source Files

- `scrapers/utilities/maritime_electric.py`
- `scrapers/utils/parsing.py`
- `scripts/export_ontario_totals.py`

## Audit Trail

- EXTRACTED: 88 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*