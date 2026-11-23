# date

> 20 nodes

## Key Concepts

- **_prepare()** (16 connections) — `pipeline/representative_models.py`
- **date** (12 connections)
- **_as_of()** (9 connections) — `pipeline/representative_models.py`
- **_as_date()** (8 connections) — `pipeline/representative_models.py`
- **tax_lines()** (8 connections) — `pipeline/representative_models.py`
- **component_exclusion()** (7 connections) — `pipeline/representative_models.py`
- **find_tou_shares()** (7 connections) — `pipeline/representative_models.py`
- **_annual_band_groups()** (5 connections) — `pipeline/representative_models.py`
- **price_basis()** (5 connections) — `pipeline/representative_models.py`
- **_tou_share_in_force()** (5 connections) — `pipeline/representative_models.py`
- **_stem()** (2 connections) — `pipeline/representative_models.py`
- **_threshold_problem()** (2 connections) — `pipeline/representative_models.py`
- **annual()** (1 connections) — `pipeline/representative_models.py`
- **Fixed charges published as bands of annual volume (tier numbers with a per-year…** (1 connections) — `pipeline/representative_models.py`
- **Classify a record's components once (level-independent): items, priced items,…** (1 connections) — `pipeline/representative_models.py`
- **(applied, not_applied) tax/rebate lines for a level: sector, dates and…** (1 connections) — `pipeline/representative_models.py`
- **Reason a component is left out of a modeled cost (see EXCLUSION_TEXT), or None…** (1 connections) — `pipeline/representative_models.py`
- **(basis 'month'|'kwh'|'kw'|'percent', factor to $/month, $/kWh or $/kW-month,…** (1 connections) — `pipeline/representative_models.py`
- **Whether a tou_shares entry is in force on ``as_of``: effective_date <= as_of <…** (1 connections) — `pipeline/representative_models.py`
- **(id, entry) of the usage_levels 'tou_shares' set in force for a model key;…** (1 connections) — `pipeline/representative_models.py`

## Relationships

- [representative_models.py](representative_models.py.md) (17 shared connections)
- [Any](Any.md) (12 shared connections)
- [_prepare](_prepare.md) (4 shared connections)
- [build_models](build_models.md) (2 shared connections)
- [re](re.md) (1 shared connections)

## Source Files

- `pipeline/representative_models.py`

## Audit Trail

- EXTRACTED: 65 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*