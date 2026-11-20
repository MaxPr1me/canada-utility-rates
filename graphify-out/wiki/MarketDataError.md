# MarketDataError

> 17 nodes

## Key Concepts

- **MarketDataError** (27 connections) — `scripts/generate_market_pricing.py`
- **parse_hoep_csv()** (9 connections) — `scripts/generate_market_pricing.py`
- **parse_hoep_averages()** (8 connections) — `scripts/generate_market_pricing.py`
- **_number()** (7 connections) — `scripts/generate_market_pricing.py`
- **parse_hoep_page()** (7 connections) — `scripts/generate_market_pricing.py`
- **date** (6 connections)
- **_parse_xml()** (5 connections) — `scripts/generate_market_pricing.py`
- **_parse_date()** (4 connections) — `scripts/generate_market_pricing.py`
- **_text()** (4 connections) — `scripts/generate_market_pricing.py`
- **validate_document()** (4 connections) — `scripts/generate_market_pricing.py`
- **_find_text()** (3 connections) — `scripts/generate_market_pricing.py`
- **Element** (2 connections)
- **Exception** (1 connections)
- **Inputs are missing, malformed or inconsistent; the run must not write output.** (1 connections) — `scripts/generate_market_pricing.py`
- **Return {delivery date: {IESO hour-ending 1-24: HOEP in $/MWh}} from a yearly…** (1 connections) — `scripts/generate_market_pricing.py`
- **Return {"YYYY-MM": {"arithmetic", "weighted"}} in $/MWh from a yearly HOEP…** (1 connections) — `scripts/generate_market_pricing.py`
- **Require the retirement statement; return {"YYYY-MM": weighted HOEP in…** (1 connections) — `scripts/generate_market_pricing.py`

## Relationships

- [generate_market_pricing.py](generate_market_pricing.py.md) (25 shared connections)
- [_actual_rates](_actual_rates.md) (8 shared connections)
- [_yearly_files](_yearly_files.md) (6 shared connections)
- [market_pricing.py](market_pricing.py.md) (2 shared connections)
- [io](io.md) (2 shared connections)
- [parse_rpp_page](parse_rpp_page.md) (1 shared connections)
- [re](re.md) (1 shared connections)

## Source Files

- `scripts/generate_market_pricing.py`

## Audit Trail

- EXTRACTED: 68 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*