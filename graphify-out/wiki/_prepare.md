# _prepare

> 25 nodes

## Key Concepts

- **_prepare()** (16 connections) — `pipeline/representative_models.py`
- **_period_and_tier_checks()** (6 connections) — `pipeline/representative_models.py`
- **_tier_windows()** (6 connections) — `pipeline/representative_models.py`
- **_annual_band_groups()** (5 connections) — `pipeline/representative_models.py`
- **_block_windows()** (5 connections) — `pipeline/representative_models.py`
- **_demand_tier_factor()** (5 connections) — `pipeline/representative_models.py`
- **_demand_windows()** (5 connections) — `pipeline/representative_models.py`
- **price_basis()** (5 connections) — `pipeline/representative_models.py`
- **reference_customer_match()** (5 connections) — `pipeline/representative_models.py`
- **_fixed_variant_groups()** (4 connections) — `pipeline/representative_models.py`
- **_note_body()** (4 connections) — `pipeline/representative_models.py`
- **_unmarked_fixed_variants()** (3 connections) — `pipeline/representative_models.py`
- **_stem()** (2 connections) — `pipeline/representative_models.py`
- **annual()** (1 connections) — `pipeline/representative_models.py`
- **Fixed-charge items named as variants of one charge ('Stem (qualifier)'), by…** (1 connections) — `pipeline/representative_models.py`
- **Unconditional fixed charges printed as variants of one charge, e.g. 'Basic…** (1 connections) — `pipeline/representative_models.py`
- **Fixed charges published as bands of annual volume (tier numbers with a per-year…** (1 connections) — `pipeline/representative_models.py`
- **Classify a record's components once (level-independent): items, priced items,…** (1 connections) — `pipeline/representative_models.py`
- **Id of the first entry whose notes_regex/name_regex all fully match the…** (1 connections) — `pipeline/representative_models.py`
- **(basis 'month'|'kwh'|'kw'|'percent', factor to $/month, $/kWh or $/kW-month,…** (1 connections) — `pipeline/representative_models.py`
- **kW per threshold unit for demand blocks (kVA bounds at the power factor); None…** (1 connections) — `pipeline/representative_models.py`
- **Windows per tier number: two-block schedules share one boundary (an item may…** (1 connections) — `pipeline/representative_models.py`
- **Set tier_lower/tier_upper (kWh/month, or kWh per kW/kVA) on one season's energy…** (1 connections) — `pipeline/representative_models.py`
- **Set demand_lower/demand_upper (kW) on one season's demand block items.** (1 connections) — `pipeline/representative_models.py`
- **Attach TOU shares, block windows and demand thresholds to priced items;…** (1 connections) — `pipeline/representative_models.py`

## Relationships

- [representative_models.py](representative_models.py.md) (14 shared connections)
- [Any](Any.md) (8 shared connections)
- [date](date.md) (4 shared connections)
- [re](re.md) (2 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (1 shared connections)

## Source Files

- `pipeline/representative_models.py`

## Audit Trail

- EXTRACTED: 56 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*