# _actual_rates

> 21 nodes

## Key Concepts

- **_actual_rates()** (10 connections) — `scripts/generate_market_pricing.py`
- **parse_ga_deferral()** (10 connections) — `scripts/generate_market_pricing.py`
- **parse_ga_recovery()** (10 connections) — `scripts/generate_market_pricing.py`
- **ga_adjustments()** (8 connections) — `scripts/generate_market_pricing.py`
- **_cell_number()** (7 connections) — `scripts/generate_market_pricing.py`
- **_cell()** (6 connections) — `scripts/generate_market_pricing.py`
- **_month_columns()** (6 connections) — `scripts/generate_market_pricing.py`
- **_sheet()** (6 connections) — `scripts/generate_market_pricing.py`
- **parse_ga_kwh()** (5 connections) — `scripts/generate_market_pricing.py`
- **parse_ga_mwh()** (5 connections) — `scripts/generate_market_pricing.py`
- **_year_cell()** (5 connections) — `scripts/generate_market_pricing.py`
- **_clean()** (3 connections) — `scripts/generate_market_pricing.py`
- **_join()** (2 connections) — `scripts/generate_market_pricing.py`
- **Workbook text without zero-width or non-breaking spaces (the IESO sheets…** (1 connections) — `scripts/generate_market_pricing.py`
- **Columns first..first+11, which must be headed January to December in order.** (1 connections) — `scripts/generate_market_pricing.py`
- **{"YYYY-MM": value} from the rows labelled actual_label under each year block…** (1 connections) — `scripts/generate_market_pricing.py`
- **Class B actual rates {"YYYY-MM": $/MWh} from the "Actual Rate ($/MWh)" rows.** (1 connections) — `scripts/generate_market_pricing.py`
- **Class B actual rates {"YYYY-MM": cents/kWh} from the "Actual" rows.** (1 connections) — `scripts/generate_market_pricing.py`
- **(Class B cap in $/MWh, {"2020-MM": unadjusted actual rate}) from the 2020…** (1 connections) — `scripts/generate_market_pricing.py`
- **{"2021-MM": actual Class B recovery rate in $/MWh} from the 2021 recovery sheet.** (1 connections) — `scripts/generate_market_pricing.py`
- **What the published actual rates include for the 2020 deferral and the 2021…** (1 connections) — `scripts/generate_market_pricing.py`

## Relationships

- [generate_market_pricing.py](generate_market_pricing.py.md) (20 shared connections)
- [MarketDataError](MarketDataError.md) (8 shared connections)
- [enmax_power.py](enmax_power.py.md) (2 shared connections)
- [market_pricing.py](market_pricing.py.md) (1 shared connections)

## Source Files

- `scripts/generate_market_pricing.py`

## Audit Trail

- EXTRACTED: 61 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*