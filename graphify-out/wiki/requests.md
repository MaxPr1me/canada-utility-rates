# requests

> 6 nodes

## Key Concepts

- **main()** (6 connections) — `scripts/generate_market_pricing.py`
- **write_document()** (6 connections) — `scripts/generate_market_pricing.py`
- **http_get()** (5 connections) — `scripts/generate_market_pricing.py`
- **parse_args()** (4 connections) — `scripts/generate_market_pricing.py`
- **Namespace** (1 connections)
- **Write the JSON document atomically (temporary file, then os.replace), so a…** (1 connections) — `scripts/generate_market_pricing.py`

## Relationships

- [generate_market_pricing.py](generate_market_pricing.py.md) (6 shared connections)
- [_yearly_files](_yearly_files.md) (2 shared connections)
- [write_spark_gap](write_spark_gap.md) (2 shared connections)
- [run_scrape.py](run_scrape.py.md) (1 shared connections)
- [json](json.md) (1 shared connections)
- [graphify_hook.py](graphify_hook.py.md) (1 shared connections)

## Source Files

- `scripts/generate_market_pricing.py`

## Audit Trail

- EXTRACTED: 17 (94%)
- INFERRED: 1 (6%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*