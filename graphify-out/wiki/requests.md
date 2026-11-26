# requests

> 9 nodes

## Key Concepts

- **time** (7 connections)
- **main()** (6 connections) — `scripts/generate_market_pricing.py`
- **write_document()** (6 connections) — `scripts/generate_market_pricing.py`
- **http_get()** (5 connections) — `scripts/generate_market_pricing.py`
- **parse_args()** (4 connections) — `scripts/generate_market_pricing.py`
- **api_get()** (4 connections) — `scripts/archive_ontario_price.py`
- **Namespace** (1 connections)
- **Like generate_market_pricing.http_get, but a 404 (no data for those dates) is…** (1 connections) — `scripts/archive_ontario_price.py`
- **Write the JSON document atomically (temporary file, then os.replace), so a…** (1 connections) — `scripts/generate_market_pricing.py`

## Relationships

- [generate_market_pricing.py](generate_market_pricing.py.md) (6 shared connections)
- [json](json.md) (4 shared connections)
- [os](os.md) (3 shared connections)
- [archive_ontario_price.py](archive_ontario_price.py.md) (2 shared connections)
- [_yearly_files](_yearly_files.md) (2 shared connections)
- [MarketDataError](MarketDataError.md) (1 shared connections)
- [BaseScraper](BaseScraper.md) (1 shared connections)

## Source Files

- `scripts/archive_ontario_price.py`
- `scripts/generate_market_pricing.py`

## Audit Trail

- EXTRACTED: 26 (96%)
- INFERRED: 1 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*