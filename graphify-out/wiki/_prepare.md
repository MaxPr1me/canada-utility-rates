# _prepare

> 17 nodes

## Key Concepts

- **_prepare()** (12 connections) — `pipeline/representative_models.py`
- **_select_variants()** (9 connections) — `pipeline/representative_models.py`
- **bucket_of()** (5 connections) — `pipeline/representative_models.py`
- **months_from_text()** (5 connections) — `pipeline/representative_models.py`
- **price_basis()** (5 connections) — `pipeline/representative_models.py`
- **season_months()** (5 connections) — `pipeline/representative_models.py`
- **_fixed_variant_groups()** (4 connections) — `pipeline/representative_models.py`
- **_unmarked_fixed_variants()** (3 connections) — `pipeline/representative_models.py`
- **_stem()** (2 connections) — `pipeline/representative_models.py`
- **(basis 'month'|'kwh'|'kw'|'percent', factor to $/month, $/kWh or $/kW-month,…** (1 connections) — `pipeline/representative_models.py`
- **Months named by a season text ('12,1,2', 'Sep-Apr', 'November 1 - April 30');…** (1 connections) — `pipeline/representative_models.py`
- **Months a seasonal component applies in (None = all year) and a problem text…** (1 connections) — `pipeline/representative_models.py`
- **Bucket of a priced component; distribution/delivery charges split by unit basis.** (1 connections) — `pipeline/representative_models.py`
- **Fixed-charge items named as variants of one charge ('Stem (qualifier)'), by…** (1 connections) — `pipeline/representative_models.py`
- **Unconditional fixed charges printed as variants of one charge, e.g. 'Basic…** (1 connections) — `pipeline/representative_models.py`
- **Classify a record's components once (level-independent): items, priced items,…** (1 connections) — `pipeline/representative_models.py`
- **(chosen variants, indexes of the blockers they resolve) at one usage level. A…** (1 connections) — `pipeline/representative_models.py`

## Relationships

- [representative_models.py](representative_models.py.md) (11 shared connections)
- [Any](Any.md) (6 shared connections)
- [_fullmatch](_fullmatch.md) (3 shared connections)
- [re](re.md) (2 shared connections)

## Source Files

- `pipeline/representative_models.py`

## Audit Trail

- EXTRACTED: 40 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*