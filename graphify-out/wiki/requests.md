# requests

> 7 nodes

## Key Concepts

- **main()** (6 connections) — `scripts/generate_market_pricing.py`
- **write_document()** (6 connections) — `scripts/generate_market_pricing.py`
- **http_get()** (5 connections) — `scripts/generate_market_pricing.py`
- **time** (5 connections)
- **parse_args()** (4 connections) — `scripts/generate_market_pricing.py`
- **Namespace** (1 connections)
- **Write the JSON document atomically (temporary file, then os.replace), so a…** (1 connections) — `scripts/generate_market_pricing.py`

## Relationships

- [generate_market_pricing.py](generate_market_pricing.py.md) (7 shared connections)
- [json](json.md) (2 shared connections)
- [os](os.md) (2 shared connections)
- [_yearly_files](_yearly_files.md) (2 shared connections)
- [archive_ontario_price.py](archive_ontario_price.py.md) (2 shared connections)
- [BaseScraper](BaseScraper.md) (1 shared connections)

## Source Files

- `scripts/generate_market_pricing.py`

## Audit Trail

- EXTRACTED: 21 (95%)
- INFERRED: 1 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*