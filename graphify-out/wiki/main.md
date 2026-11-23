# main

> 19 nodes

## Key Concepts

- **io** (40 connections)
- **csv** (22 connections)
- **main()** (10 connections) — `scripts/build_ontario_market.py`
- **output_bytes()** (7 connections) — `scripts/build_alberta_market.py`
- **render_document()** (6 connections) — `scripts/build_ontario_market.py`
- **serialize_monthly()** (5 connections) — `scripts/build_ontario_market.py`
- **write_outputs()** (5 connections) — `scripts/build_ontario_market.py`
- **parse_args()** (4 connections) — `scripts/build_ontario_market.py`
- **read_csv_rows()** (4 connections) — `scrapers/utils/parsing.py`
- **csv_bytes()** (4 connections) — `scripts/build_alberta_market.py`
- **serialize_hoep()** (4 connections) — `scripts/build_ontario_market.py`
- **extract_pdf_tables()** (3 connections) — `scrapers/utils/parsing.py`
- **_read()** (3 connections) — `scripts/build_ontario_market.py`
- **Path** (3 connections)
- **Namespace** (1 connections)
- **Read an official UTF-8/UTF-8-BOM CSV into named rows.** (1 connections) — `scrapers/utils/parsing.py`
- **Extract tables from a PDF using pdfplumber. Returns the same format as…** (1 connections) — `scrapers/utils/parsing.py`
- **The JSON bytes to write, or None when only generated_at would change.** (1 connections) — `scripts/build_ontario_market.py`
- **Write every file to a temporary sibling first, then move them all into place.** (1 connections) — `scripts/build_ontario_market.py`

## Relationships

- [build_ontario_market.py](build_ontario_market.py.md) (17 shared connections)
- [build_alberta_market.py](build_alberta_market.py.md) (8 shared connections)
- [archive_ontario_price.py](archive_ontario_price.py.md) (8 shared connections)
- [BaseScraper](BaseScraper.md) (7 shared connections)
- [io](io.md) (6 shared connections)
- [aeso.py](aeso.py.md) (5 shared connections)
- [generate_market_pricing.py](generate_market_pricing.py.md) (3 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (2 shared connections)
- [MarketDataError](MarketDataError.md) (2 shared connections)
- [re](re.md) (2 shared connections)
- [enmax_power.py](enmax_power.py.md) (2 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (2 shared connections)

## Source Files

- `scrapers/utils/parsing.py`
- `scripts/build_alberta_market.py`
- `scripts/build_ontario_market.py`

## Audit Trail

- EXTRACTED: 100 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*