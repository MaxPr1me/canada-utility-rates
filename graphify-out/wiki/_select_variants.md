# _select_variants

> 16 nodes

## Key Concepts

- **_select_variants()** (11 connections) — `pipeline/representative_models.py`
- **_variant_rule_applies()** (6 connections) — `pipeline/representative_models.py`
- **bucket_of()** (5 connections) — `pipeline/representative_models.py`
- **fixed_charge_variant_rules()** (5 connections) — `pipeline/representative_models.py`
- **months_from_text()** (5 connections) — `pipeline/representative_models.py`
- **price_basis()** (5 connections) — `pipeline/representative_models.py`
- **season_months()** (5 connections) — `pipeline/representative_models.py`
- **_variant_rule_kind()** (5 connections) — `pipeline/representative_models.py`
- **Whether a fixed_charge_variants rule applies to a prepared record at one level:…** (1 connections) — `pipeline/representative_models.py`
- **(chosen variants, indexes of the blockers they resolve) at one usage level. A…** (1 connections) — `pipeline/representative_models.py`
- **levels' (selected by usage-level id), 'peak_month' (by the level's monthly…** (1 connections) — `pipeline/representative_models.py`
- **usage_levels 'fixed_charge_variants' rules for a fuel (missing = any fuel),…** (1 connections) — `pipeline/representative_models.py`
- **(basis 'month'|'kwh'|'kw'|'percent', factor to $/month, $/kWh or $/kW-month,…** (1 connections) — `pipeline/representative_models.py`
- **Months named by a season text ('12,1,2', 'Sep-Apr', 'November 1 - April 30');…** (1 connections) — `pipeline/representative_models.py`
- **Months a seasonal component applies in (None = all year) and a problem text…** (1 connections) — `pipeline/representative_models.py`
- **Bucket of a priced component; distribution/delivery charges split by unit basis.** (1 connections) — `pipeline/representative_models.py`

## Relationships

- [representative_models.py](representative_models.py.md) (8 shared connections)
- [_build_model](_build_model.md) (6 shared connections)
- [Any](Any.md) (5 shared connections)
- [re](re.md) (2 shared connections)
- [_prepare](_prepare.md) (1 shared connections)
- [_price](_price.md) (1 shared connections)

## Source Files

- `pipeline/representative_models.py`

## Audit Trail

- EXTRACTED: 39 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*