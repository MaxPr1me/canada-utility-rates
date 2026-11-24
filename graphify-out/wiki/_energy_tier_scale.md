# _energy_tier_scale

> 12 nodes

## Key Concepts

- **_energy_tier_scale()** (6 connections) — `pipeline/representative_models.py`
- **_period_and_tier_checks()** (6 connections) — `pipeline/representative_models.py`
- **_tier_windows()** (6 connections) — `pipeline/representative_models.py`
- **_block_windows()** (5 connections) — `pipeline/representative_models.py`
- **_demand_tier_factor()** (5 connections) — `pipeline/representative_models.py`
- **_demand_windows()** (5 connections) — `pipeline/representative_models.py`
- **(scale 'month'|'kw'|'kva', factor to the scale, conversions, problem,…** (1 connections) — `pipeline/representative_models.py`
- **kW per threshold unit for demand blocks (kVA bounds at the power factor); None…** (1 connections) — `pipeline/representative_models.py`
- **Windows per tier number: two-block schedules share one boundary (an item may…** (1 connections) — `pipeline/representative_models.py`
- **Set tier_lower/tier_upper (kWh/month, or kWh per kW/kVA) on one season's energy…** (1 connections) — `pipeline/representative_models.py`
- **Set demand_lower/demand_upper (kW) on one season's demand block items.** (1 connections) — `pipeline/representative_models.py`
- **Attach TOU shares, block windows and demand thresholds to priced items;…** (1 connections) — `pipeline/representative_models.py`

## Relationships

- [representative_models.py](representative_models.py.md) (6 shared connections)
- [_prepare](_prepare.md) (3 shared connections)
- [re](re.md) (2 shared connections)
- [Any](Any.md) (2 shared connections)
- [_after_subsidy_record](_after_subsidy_record.md) (1 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (1 shared connections)

## Source Files

- `pipeline/representative_models.py`

## Audit Trail

- EXTRACTED: 27 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*