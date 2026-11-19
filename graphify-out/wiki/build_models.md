# build_models

> 23 nodes

## Key Concepts

- **build_models()** (23 connections) — `pipeline/representative_models.py`
- **coverage_report()** (13 connections) — `pipeline/representative_models.py`
- **compose_pairs()** (5 connections) — `pipeline/representative_models.py`
- **find_synthetic_profile()** (5 connections) — `pipeline/representative_models.py`
- **key_label()** (5 connections) — `pipeline/representative_models.py`
- **pair_config()** (5 connections) — `pipeline/representative_models.py`
- **apply_usage_bounds()** (4 connections) — `pipeline/representative_models.py`
- **latest_live_records()** (4 connections) — `pipeline/representative_models.py`
- **model_keys()** (4 connections) — `pipeline/representative_models.py`
- **_pair_composite()** (3 connections) — `pipeline/representative_models.py`
- **_signature()** (3 connections) — `pipeline/representative_models.py`
- **_brief()** (2 connections) — `pipeline/representative_models.py`
- **_model_order()** (2 connections) — `pipeline/representative_models.py`
- **(id, entry) of the usage_levels synthetic_profiles entry whose applies_to…** (1 connections) — `pipeline/representative_models.py`
- **Concrete (province, fuel, sector, structure, size_band) keys of a mapped…** (1 connections) — `pipeline/representative_models.py`
- **Printable model key, e.g. 'ON|electricity|commercial|demand|commercial_large'.** (1 connections) — `pipeline/representative_models.py`
- **Mapped/excluded/unmapped counts per utility and province, unmapped records,…** (1 connections) — `pipeline/representative_models.py`
- **The crosswalk 'pairs' section (wires + retail units), or {}.** (1 connections) — `pipeline/representative_models.py`
- **One wires + retail (variant 'retail') or wires-only (variant 'market') record…** (1 connections) — `pipeline/representative_models.py`
- **Pair variants per paired wires record (keyed by id(record)), wires utility ->…** (1 connections) — `pipeline/representative_models.py`
- **Copy of a record with reviewed annual-use eligibility bounds (crosswalk…** (1 connections) — `pipeline/representative_models.py`
- **Representative models for every crosswalk model key of the given provinces and…** (1 connections) — `pipeline/representative_models.py`
- **Latest effective_date per (utility_name, name, customer_class), as the site…** (1 connections) — `pipeline/representative_models.py`

## Relationships

- [representative_models.py](representative_models.py.md) (18 shared connections)
- [Any](Any.md) (4 shared connections)
- [run_scrape.py](run_scrape.py.md) (3 shared connections)
- [match_record](match_record.md) (3 shared connections)
- [main](main.md) (3 shared connections)
- [date](date.md) (2 shared connections)
- [input_checks](input_checks.md) (2 shared connections)
- [model_monitoring.py](model_monitoring.py.md) (1 shared connections)

## Source Files

- `pipeline/representative_models.py`

## Audit Trail

- EXTRACTED: 62 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*