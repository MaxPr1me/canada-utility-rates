# _prepare

> 28 nodes

## Key Concepts

- **_prepare()** (20 connections) — `pipeline/representative_models.py`
- **_after_subsidy_record()** (18 connections) — `pipeline/representative_models.py`
- **record_monthly_cost()** (16 connections) — `pipeline/representative_models.py`
- **date** (12 connections)
- **_as_of()** (10 connections) — `pipeline/representative_models.py`
- **_context()** (10 connections) — `pipeline/representative_models.py`
- **_as_date()** (8 connections) — `pipeline/representative_models.py`
- **component_exclusion()** (8 connections) — `pipeline/representative_models.py`
- **tax_lines()** (8 connections) — `pipeline/representative_models.py`
- **find_tou_shares()** (7 connections) — `pipeline/representative_models.py`
- **season_months()** (6 connections) — `pipeline/representative_models.py`
- **_tou_share_in_force()** (5 connections) — `pipeline/representative_models.py`
- **_is_percentage()** (4 connections) — `pipeline/representative_models.py`
- **_dates_text()** (2 connections) — `pipeline/representative_models.py`
- **_stem()** (2 connections) — `pipeline/representative_models.py`
- **_threshold_problem()** (2 connections) — `pipeline/representative_models.py`
- **failed()** (1 connections) — `pipeline/representative_models.py`
- **skip()** (1 connections) — `pipeline/representative_models.py`
- **True for a component priced as a percentage or fraction (price_basis 'percent').** (1 connections) — `pipeline/representative_models.py`
- **Classify a record's components once (level-independent): items, priced items,…** (1 connections) — `pipeline/representative_models.py`
- **Modeled monthly cost of one record at (kWh/month, kW) with an itemized…** (1 connections) — `pipeline/representative_models.py`
- **One zone record's cost after the reviewed automatic subsidies at one usage…** (1 connections) — `pipeline/representative_models.py`
- **(applied, not_applied) tax/rebate lines for a level: sector, dates and…** (1 connections) — `pipeline/representative_models.py`
- **Reason a component is left out of a modeled cost (see EXCLUSION_TEXT), or None…** (1 connections) — `pipeline/representative_models.py`
- **Months a seasonal component applies in (None = all year) and a problem text…** (1 connections) — `pipeline/representative_models.py`
- *... and 3 more nodes in this community*

## Relationships

- [representative_models.py](representative_models.py.md) (24 shared connections)
- [Any](Any.md) (15 shared connections)
- [_select_variants](_select_variants.md) (5 shared connections)
- [_fullmatch](_fullmatch.md) (4 shared connections)
- [_energy_tier_scale](_energy_tier_scale.md) (4 shared connections)
- [re](re.md) (2 shared connections)
- [_price](_price.md) (2 shared connections)
- [build_models](build_models.md) (2 shared connections)
- [market_pricing.py](market_pricing.py.md) (1 shared connections)
- [_fixed_variant_groups](_fixed_variant_groups.md) (1 shared connections)

## Source Files

- `pipeline/representative_models.py`

## Audit Trail

- EXTRACTED: 105 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*