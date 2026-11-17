# _prepare

> 23 nodes

## Key Concepts

- **Any** (23 connections)
- **_prepare()** (12 connections) — `pipeline/representative_models.py`
- **record_monthly_cost()** (11 connections) — `pipeline/representative_models.py`
- **_select_variants()** (9 connections) — `pipeline/representative_models.py`
- **_fullmatch()** (8 connections) — `pipeline/representative_models.py`
- **block_periods_config()** (7 connections) — `pipeline/representative_models.py`
- **_clean()** (5 connections) — `pipeline/representative_models.py`
- **bucket_of()** (5 connections) — `pipeline/representative_models.py`
- **months_from_text()** (5 connections) — `pipeline/representative_models.py`
- **price_basis()** (5 connections) — `pipeline/representative_models.py`
- **season_months()** (5 connections) — `pipeline/representative_models.py`
- **_compiled()** (4 connections) — `pipeline/representative_models.py`
- **_block_period_problem()** (3 connections) — `pipeline/representative_models.py`
- **_stem()** (2 connections) — `pipeline/representative_models.py`
- **Pattern** (1 connections)
- **(chosen variants, indexes of the blockers they resolve) at one usage level. A…** (1 connections) — `pipeline/representative_models.py`
- **Modeled monthly cost of one record at (kWh/month, kW) with an itemized…** (1 connections) — `pipeline/representative_models.py`
- **(basis 'month'|'kwh'|'kw'|'percent', factor to $/month, $/kWh or $/kW-month,…** (1 connections) — `pipeline/representative_models.py`
- **Months named by a season text ('12,1,2', 'Sep-Apr', 'November 1 - April 30');…** (1 connections) — `pipeline/representative_models.py`
- **Months a seasonal component applies in (None = all year) and a problem text…** (1 connections) — `pipeline/representative_models.py`
- **Bucket of a priced component; distribution/delivery charges split by unit basis.** (1 connections) — `pipeline/representative_models.py`
- **Usable entries of a block_periods document ({'entries': [...]}) or entry list;…** (1 connections) — `pipeline/representative_models.py`
- **Classify a record's components once (level-independent): items, priced items,…** (1 connections) — `pipeline/representative_models.py`

## Relationships

- [representative_models.py](representative_models.py.md) (17 shared connections)
- [Any](Any.md) (10 shared connections)
- [_fullmatch](_fullmatch.md) (6 shared connections)
- [build_models](build_models.md) (5 shared connections)
- [match_record](match_record.md) (4 shared connections)
- [re](re.md) (3 shared connections)
- [market_pricing.py](market_pricing.py.md) (1 shared connections)
- [model_monitoring.py](model_monitoring.py.md) (1 shared connections)
- [_fixed_variant_groups](_fixed_variant_groups.md) (1 shared connections)
- [main](main.md) (1 shared connections)

## Source Files

- `pipeline/representative_models.py`

## Audit Trail

- EXTRACTED: 81 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*