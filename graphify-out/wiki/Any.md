# Any

> 28 nodes

## Key Concepts

- **Any** (26 connections)
- **record_monthly_cost()** (12 connections) — `pipeline/representative_models.py`
- **_select_variants()** (11 connections) — `pipeline/representative_models.py`
- **_fullmatch()** (8 connections) — `pipeline/representative_models.py`
- **block_periods_config()** (7 connections) — `pipeline/representative_models.py`
- **_energy_tier_scale()** (6 connections) — `pipeline/representative_models.py`
- **_variant_rule_applies()** (6 connections) — `pipeline/representative_models.py`
- **_clean()** (5 connections) — `pipeline/representative_models.py`
- **bucket_of()** (5 connections) — `pipeline/representative_models.py`
- **fixed_charge_variant_rules()** (5 connections) — `pipeline/representative_models.py`
- **months_from_text()** (5 connections) — `pipeline/representative_models.py`
- **season_months()** (5 connections) — `pipeline/representative_models.py`
- **_variant_rule_kind()** (5 connections) — `pipeline/representative_models.py`
- **_compiled()** (4 connections) — `pipeline/representative_models.py`
- **block_period_entry()** (4 connections) — `pipeline/representative_models.py`
- **_block_period_problem()** (3 connections) — `pipeline/representative_models.py`
- **Pattern** (1 connections)
- **Whether a fixed_charge_variants rule applies to a prepared record at one level:…** (1 connections) — `pipeline/representative_models.py`
- **(chosen variants, indexes of the blockers they resolve) at one usage level. A…** (1 connections) — `pipeline/representative_models.py`
- **Modeled monthly cost of one record at (kWh/month, kW) with an itemized…** (1 connections) — `pipeline/representative_models.py`
- **levels' (selected by usage-level id), 'peak_month' (by the level's monthly…** (1 connections) — `pipeline/representative_models.py`
- **usage_levels 'fixed_charge_variants' rules for a fuel (missing = any fuel),…** (1 connections) — `pipeline/representative_models.py`
- **Months named by a season text ('12,1,2', 'Sep-Apr', 'November 1 - April 30');…** (1 connections) — `pipeline/representative_models.py`
- **Months a seasonal component applies in (None = all year) and a problem text…** (1 connections) — `pipeline/representative_models.py`
- **Bucket of a priced component; distribution/delivery charges split by unit basis.** (1 connections) — `pipeline/representative_models.py`
- *... and 3 more nodes in this community*

## Relationships

- [representative_models.py](representative_models.py.md) (18 shared connections)
- [date](date.md) (10 shared connections)
- [_prepare](_prepare.md) (8 shared connections)
- [build_models](build_models.md) (5 shared connections)
- [apply_usage_bounds](apply_usage_bounds.md) (4 shared connections)
- [re](re.md) (3 shared connections)
- [main](main.md) (2 shared connections)
- [_price](_price.md) (2 shared connections)
- [market_pricing.py](market_pricing.py.md) (1 shared connections)

## Source Files

- `pipeline/representative_models.py`

## Audit Trail

- EXTRACTED: 91 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*