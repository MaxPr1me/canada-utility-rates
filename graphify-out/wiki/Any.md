# Any

> 25 nodes

## Key Concepts

- **Any** (23 connections)
- **date** (12 connections)
- **record_monthly_cost()** (11 connections) — `pipeline/representative_models.py`
- **_context()** (9 connections) — `pipeline/representative_models.py`
- **_as_of()** (8 connections) — `pipeline/representative_models.py`
- **tax_lines()** (8 connections) — `pipeline/representative_models.py`
- **_as_date()** (7 connections) — `pipeline/representative_models.py`
- **block_periods_config()** (7 connections) — `pipeline/representative_models.py`
- **component_exclusion()** (7 connections) — `pipeline/representative_models.py`
- **find_tou_shares()** (7 connections) — `pipeline/representative_models.py`
- **_clean()** (5 connections) — `pipeline/representative_models.py`
- **_tou_share_in_force()** (5 connections) — `pipeline/representative_models.py`
- **fixed_charge_variant_rules()** (4 connections) — `pipeline/representative_models.py`
- **reference_customer_entries()** (4 connections) — `pipeline/representative_models.py`
- **_block_period_problem()** (3 connections) — `pipeline/representative_models.py`
- **_threshold_problem()** (2 connections) — `pipeline/representative_models.py`
- **Modeled monthly cost of one record at (kWh/month, kW) with an itemized…** (1 connections) — `pipeline/representative_models.py`
- **(applied, not_applied) tax/rebate lines for a level: sector, dates and…** (1 connections) — `pipeline/representative_models.py`
- **Reason a component is left out of a modeled cost (see EXCLUSION_TEXT), or None…** (1 connections) — `pipeline/representative_models.py`
- **usage_levels 'reference_customer' entries for a province, fuel (missing = any…** (1 connections) — `pipeline/representative_models.py`
- **usage_levels 'fixed_charge_variants' rules for a fuel (missing = any fuel) and…** (1 connections) — `pipeline/representative_models.py`
- **Whether a tou_shares entry is in force on ``as_of``: effective_date <= as_of <…** (1 connections) — `pipeline/representative_models.py`
- **(id, entry) of the usage_levels 'tou_shares' set in force for a model key;…** (1 connections) — `pipeline/representative_models.py`
- **Pricing inputs shared by every record of one model key at the as-of date.…** (1 connections) — `pipeline/representative_models.py`
- **Usable entries of a block_periods document ({'entries': [...]}) or entry list;…** (1 connections) — `pipeline/representative_models.py`

## Relationships

- [representative_models.py](representative_models.py.md) (22 shared connections)
- [json](json.md) (7 shared connections)
- [_prepare](_prepare.md) (6 shared connections)
- [_fullmatch](_fullmatch.md) (4 shared connections)
- [match_record](match_record.md) (3 shared connections)
- [generate_market_pricing.py](generate_market_pricing.py.md) (1 shared connections)

## Source Files

- `pipeline/representative_models.py`

## Audit Trail

- EXTRACTED: 87 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*