# io

> 11 nodes

## Key Concepts

- **io** (36 connections)
- **load_archive()** (13 connections) — `scripts/archive_ontario_price.py`
- **Row** (4 connections) — `scripts/archive_ontario_price.py`
- **read_csv_rows()** (4 connections) — `scrapers/utils/parsing.py`
- **.oemp()** (3 connections) — `scripts/archive_ontario_price.py`
- **extract_pdf_tables()** (3 connections) — `scrapers/utils/parsing.py`
- **read_xlsx_tables()** (3 connections) — `scrapers/utils/parsing.py`
- **Read an Excel file and return a dict of sheet_name -> rows. Each row is a list…** (1 connections) — `scrapers/utils/parsing.py`
- **Read an official UTF-8/UTF-8-BOM CSV into named rows.** (1 connections) — `scrapers/utils/parsing.py`
- **Extract tables from a PDF using pdfplumber. Returns the same format as…** (1 connections) — `scrapers/utils/parsing.py`
- **Rows of an existing archive file; any inconsistency fails closed instead of…** (1 connections) — `scripts/archive_ontario_price.py`

## Relationships

- [archive_ontario_price.py](archive_ontario_price.py.md) (11 shared connections)
- [build_alberta_market.py](build_alberta_market.py.md) (7 shared connections)
- [BaseScraper](BaseScraper.md) (6 shared connections)
- [build_ontario_market.py](build_ontario_market.py.md) (5 shared connections)
- [export_ontario_totals.py](export_ontario_totals.py.md) (3 shared connections)
- [generate_market_pricing.py](generate_market_pricing.py.md) (3 shared connections)
- [main](main.md) (2 shared connections)
- [EnbridgeGasScraper](EnbridgeGasScraper.md) (2 shared connections)
- [enmax_power.py](enmax_power.py.md) (2 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (2 shared connections)
- [MaritimeElectricScraper](MaritimeElectricScraper.md) (2 shared connections)
- [re](re.md) (1 shared connections)

## Source Files

- `scrapers/utils/parsing.py`
- `scripts/archive_ontario_price.py`

## Audit Trail

- EXTRACTED: 58 (98%)
- INFERRED: 1 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*