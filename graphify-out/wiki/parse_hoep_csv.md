# parse_hoep_csv

> 8 nodes

## Key Concepts

- **parse_hoep_csv()** (9 connections) — `scripts/generate_market_pricing.py`
- **build_surface()** (7 connections) — `scripts/generate_market_pricing.py`
- **month_dates()** (6 connections) — `scripts/generate_market_pricing.py`
- **date** (6 connections)
- **describe_months()** (5 connections) — `scripts/generate_market_pricing.py`
- **day_type()** (4 connections) — `scripts/generate_market_pricing.py`
- **_parse_date()** (4 connections) — `scripts/generate_market_pricing.py`
- **Return {delivery date: {IESO hour-ending 1-24: HOEP in $/MWh}} from a yearly…** (1 connections) — `scripts/generate_market_pricing.py`

## Relationships

- [generate_market_pricing.py](generate_market_pricing.py.md) (16 shared connections)
- [_yearly_files](_yearly_files.md) (3 shared connections)
- [build_ontario_market.py](build_ontario_market.py.md) (2 shared connections)
- [market_pricing.py](market_pricing.py.md) (1 shared connections)

## Source Files

- `scripts/generate_market_pricing.py`

## Audit Trail

- EXTRACTED: 32 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*