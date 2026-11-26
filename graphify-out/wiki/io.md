# io

> 24 nodes

## Key Concepts

- **io** (40 connections)
- **csv** (24 connections)
- **export_ontario_totals.py** (20 connections) — `scripts/export_ontario_totals.py`
- **collections** (10 connections)
- **output_bytes()** (9 connections) — `scripts/build_alberta_market.py`
- **main()** (7 connections) — `scripts/export_ontario_totals.py`
- **build()** (5 connections) — `scripts/export_ontario_totals.py`
- **check_no_loss()** (5 connections) — `scripts/export_ontario_totals.py`
- **read_csv_rows()** (4 connections) — `scrapers/utils/parsing.py`
- **csv_bytes()** (4 connections) — `scripts/build_alberta_market.py`
- **serialize_hoep()** (4 connections) — `scripts/build_ontario_market.py`
- **_csv()** (4 connections) — `scripts/export_ontario_totals.py`
- **extract_pdf_tables()** (3 connections) — `scrapers/utils/parsing.py`
- **cents()** (3 connections) — `scripts/export_ontario_totals.py`
- **parse_args()** (3 connections) — `scripts/export_ontario_totals.py`
- **load_supplement()** (2 connections) — `scripts/export_ontario_totals.py`
- **Decimal** (2 connections)
- **_load_market()** (1 connections) — `scripts/export_ontario_totals.py`
- **date** (1 connections)
- **Path** (1 connections)
- **Read an official UTF-8/UTF-8-BOM CSV into named rows.** (1 connections) — `scrapers/utils/parsing.py`
- **Extract tables from a PDF using pdfplumber. Returns the same format as…** (1 connections) — `scrapers/utils/parsing.py`
- **Every output's bytes, built only after the archived months passed review;…** (1 connections) — `scripts/build_alberta_market.py`
- **Export hourly/monthly energy + Class B GA totals in CAD cents/kWh, without…** (1 connections) — `scripts/export_ontario_totals.py`

## Relationships

- [build_alberta_market.py](build_alberta_market.py.md) (10 shared connections)
- [archive_ontario_price.py](archive_ontario_price.py.md) (9 shared connections)
- [build_ontario_market.py](build_ontario_market.py.md) (8 shared connections)
- [BaseScraper](BaseScraper.md) (6 shared connections)
- [aeso.py](aeso.py.md) (5 shared connections)
- [run_scrape.py](run_scrape.py.md) (4 shared connections)
- [generate_market_pricing.py](generate_market_pricing.py.md) (4 shared connections)
- [write_spark_gap](write_spark_gap.md) (3 shared connections)
- [main](main.md) (3 shared connections)
- [parse_html](parse_html.md) (3 shared connections)
- [os](os.md) (2 shared connections)
- [enmax_power.py](enmax_power.py.md) (2 shared connections)

## Source Files

- `scrapers/utils/parsing.py`
- `scripts/build_alberta_market.py`
- `scripts/build_ontario_market.py`
- `scripts/export_ontario_totals.py`

## Audit Trail

- EXTRACTED: 118 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*