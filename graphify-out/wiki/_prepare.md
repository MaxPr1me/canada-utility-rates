# _prepare

> 22 nodes

## Key Concepts

- **_fullmatch()** (8 connections) — `pipeline/representative_models.py`
- **_energy_tier_scale()** (6 connections) — `pipeline/representative_models.py`
- **_period_and_tier_checks()** (6 connections) — `pipeline/representative_models.py`
- **_tier_windows()** (6 connections) — `pipeline/representative_models.py`
- **_block_windows()** (5 connections) — `pipeline/representative_models.py`
- **_demand_tier_factor()** (5 connections) — `pipeline/representative_models.py`
- **_demand_windows()** (5 connections) — `pipeline/representative_models.py`
- **reference_customer_match()** (5 connections) — `pipeline/representative_models.py`
- **rule_matches()** (5 connections) — `pipeline/representative_models.py`
- **_compiled()** (4 connections) — `pipeline/representative_models.py`
- **block_period_entry()** (4 connections) — `pipeline/representative_models.py`
- **_note_body()** (4 connections) — `pipeline/representative_models.py`
- **Pattern** (1 connections)
- **Id of the first entry whose notes_regex/name_regex all fully match the…** (1 connections) — `pipeline/representative_models.py`
- **True when every criterion of ``rule`` holds for ``record`` (regexes use…** (1 connections) — `pipeline/representative_models.py`
- **First block_periods entry for the record: same utility, every match criterion…** (1 connections) — `pipeline/representative_models.py`
- **(scale 'month'|'kw'|'kva', factor to the scale, conversions, problem,…** (1 connections) — `pipeline/representative_models.py`
- **kW per threshold unit for demand blocks (kVA bounds at the power factor); None…** (1 connections) — `pipeline/representative_models.py`
- **Windows per tier number: two-block schedules share one boundary (an item may…** (1 connections) — `pipeline/representative_models.py`
- **Set tier_lower/tier_upper (kWh/month, or kWh per kW/kVA) on one season's energy…** (1 connections) — `pipeline/representative_models.py`
- **Set demand_lower/demand_upper (kW) on one season's demand block items.** (1 connections) — `pipeline/representative_models.py`
- **Attach TOU shares, block windows and demand thresholds to priced items;…** (1 connections) — `pipeline/representative_models.py`

## Relationships

- [representative_models.py](representative_models.py.md) (12 shared connections)
- [_build_model](_build_model.md) (4 shared connections)
- [Any](Any.md) (4 shared connections)
- [re](re.md) (3 shared connections)
- [build_models](build_models.md) (2 shared connections)
- [_select_variants](_select_variants.md) (1 shared connections)
- [check_db_history.py](check_db_history.py.md) (1 shared connections)

## Source Files

- `pipeline/representative_models.py`

## Audit Trail

- EXTRACTED: 50 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*