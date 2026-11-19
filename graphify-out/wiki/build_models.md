# build_models

> 24 nodes

## Key Concepts

- **build_models()** (23 connections) — `pipeline/representative_models.py`
- **coverage_report()** (13 connections) — `pipeline/representative_models.py`
- **load_block_periods()** (8 connections) — `pipeline/representative_models.py`
- **match_record()** (6 connections) — `pipeline/representative_models.py`
- **find_synthetic_profile()** (5 connections) — `pipeline/representative_models.py`
- **key_label()** (5 connections) — `pipeline/representative_models.py`
- **matching_outcomes()** (5 connections) — `pipeline/representative_models.py`
- **rule_matches()** (5 connections) — `pipeline/representative_models.py`
- **latest_live_records()** (4 connections) — `pipeline/representative_models.py`
- **model_keys()** (4 connections) — `pipeline/representative_models.py`
- **_outcome()** (4 connections) — `pipeline/representative_models.py`
- **_signature()** (3 connections) — `pipeline/representative_models.py`
- **_brief()** (2 connections) — `pipeline/representative_models.py`
- **_model_order()** (2 connections) — `pipeline/representative_models.py`
- **(id, entry) of the usage_levels synthetic_profiles entry whose applies_to…** (1 connections) — `pipeline/representative_models.py`
- **Outcomes of every rule that matches ``record``, in rule order.** (1 connections) — `pipeline/representative_models.py`
- **First matching rule's outcome {'rule_id', 'model', 'exclude', 'zone'}; all None…** (1 connections) — `pipeline/representative_models.py`
- **Concrete (province, fuel, sector, structure, size_band) keys of a mapped…** (1 connections) — `pipeline/representative_models.py`
- **Printable model key, e.g. 'ON|electricity|commercial|demand|commercial_large'.** (1 connections) — `pipeline/representative_models.py`
- **Mapped/excluded/unmapped counts per utility and province, unmapped records,…** (1 connections) — `pipeline/representative_models.py`
- **Representative models for every crosswalk model key of the given provinces and…** (1 connections) — `pipeline/representative_models.py`
- **Latest effective_date per (utility_name, name, customer_class), as the site…** (1 connections) — `pipeline/representative_models.py`
- **Reviewed periods of bare-'kWh' block thresholds (default…** (1 connections) — `pipeline/representative_models.py`
- **True when every criterion of ``rule`` holds for ``record`` (regexes use…** (1 connections) — `pipeline/representative_models.py`

## Relationships

- [representative_models.py](representative_models.py.md) (19 shared connections)
- [Any](Any.md) (6 shared connections)
- [main](main.md) (5 shared connections)
- [model_monitoring.py](model_monitoring.py.md) (4 shared connections)
- [run_scrape.py](run_scrape.py.md) (3 shared connections)
- [_fullmatch](_fullmatch.md) (2 shared connections)
- [compose_pairs](compose_pairs.md) (2 shared connections)

## Source Files

- `pipeline/representative_models.py`

## Audit Trail

- EXTRACTED: 70 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*