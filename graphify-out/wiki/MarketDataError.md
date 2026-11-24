# MarketDataError

> 13 nodes

## Key Concepts

- **MarketDataError** (27 connections) — `scripts/generate_market_pricing.py`
- **parse_hoep_csv()** (9 connections) — `scripts/generate_market_pricing.py`
- **load_hoep()** (8 connections) — `scripts/generate_market_pricing.py`
- **_cell_number()** (7 connections) — `scripts/generate_market_pricing.py`
- **_number()** (7 connections) — `scripts/generate_market_pricing.py`
- **parse_hoep_page()** (7 connections) — `scripts/generate_market_pricing.py`
- **date** (6 connections)
- **_parse_date()** (4 connections) — `scripts/generate_market_pricing.py`
- **_text()** (4 connections) — `scripts/generate_market_pricing.py`
- **Exception** (1 connections)
- **Inputs are missing, malformed or inconsistent; the run must not write output.** (1 connections) — `scripts/generate_market_pricing.py`
- **Return {delivery date: {IESO hour-ending 1-24: HOEP in $/MWh}} from a yearly…** (1 connections) — `scripts/generate_market_pricing.py`
- **Require the retirement statement; return {"YYYY-MM": weighted HOEP in…** (1 connections) — `scripts/generate_market_pricing.py`

## Relationships

- [generate_market_pricing.py](generate_market_pricing.py.md) (23 shared connections)
- [_actual_rates](_actual_rates.md) (9 shared connections)
- [_yearly_files](_yearly_files.md) (4 shared connections)
- [parse_hoep_averages](parse_hoep_averages.md) (3 shared connections)
- [market_pricing.py](market_pricing.py.md) (2 shared connections)
- [archive_ontario_price.py](archive_ontario_price.py.md) (1 shared connections)
- [build_alberta_market.py](build_alberta_market.py.md) (1 shared connections)
- [lethbridge.py](lethbridge.py.md) (1 shared connections)
- [re](re.md) (1 shared connections)

## Source Files

- `scripts/generate_market_pricing.py`

## Audit Trail

- EXTRACTED: 63 (98%)
- INFERRED: 1 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*