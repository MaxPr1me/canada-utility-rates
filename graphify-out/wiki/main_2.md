# main

> 11 nodes

## Key Concepts

- **main()** (6 connections) — `scripts/generate_market_pricing.py`
- **write_document()** (6 connections) — `scripts/generate_market_pricing.py`
- **http_get()** (5 connections) — `scripts/generate_market_pricing.py`
- **time** (5 connections)
- **parse_args()** (4 connections) — `scripts/generate_market_pricing.py`
- **api_get()** (4 connections) — `scripts/archive_ontario_price.py`
- **.__init__()** (3 connections) — `scripts/generate_market_pricing.py`
- **Path** (3 connections)
- **Namespace** (1 connections)
- **Like generate_market_pricing.http_get, but a 404 (no data for those dates) is…** (1 connections) — `scripts/archive_ontario_price.py`
- **Write the JSON document atomically (temporary file, then os.replace), so a…** (1 connections) — `scripts/generate_market_pricing.py`

## Relationships

- [generate_market_pricing.py](generate_market_pricing.py.md) (6 shared connections)
- [os](os.md) (3 shared connections)
- [archive_ontario_price.py](archive_ontario_price.py.md) (2 shared connections)
- [MarketDataError](MarketDataError.md) (2 shared connections)
- [ReportSource](ReportSource.md) (2 shared connections)
- [argparse](argparse.md) (1 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (1 shared connections)
- [_yearly_files](_yearly_files.md) (1 shared connections)
- [BaseScraper](BaseScraper.md) (1 shared connections)

## Source Files

- `scripts/archive_ontario_price.py`
- `scripts/generate_market_pricing.py`

## Audit Trail

- EXTRACTED: 28 (97%)
- INFERRED: 1 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*