# write_spark_gap

> 38 nodes

## Key Concepts

- **json** (75 connections)
- **write_spark_gap()** (15 connections) — `pipeline/spark_gap.py`
- **input_checks()** (14 connections) — `pipeline/model_monitoring.py`
- **main()** (13 connections) — `pipeline/representative_models.py`
- **export_representative_models()** (12 connections) — `pipeline/export_json.py`
- **write_models()** (12 connections) — `pipeline/representative_models.py`
- **main()** (12 connections) — `pipeline/spark_gap.py`
- **PathLike** (10 connections)
- **load_crosswalk()** (9 connections) — `pipeline/representative_models.py`
- **load_taxes()** (9 connections) — `pipeline/representative_models.py`
- **load_usage_levels()** (9 connections) — `pipeline/representative_models.py`
- **load_json()** (8 connections) — `pipeline/spark_gap.py`
- **start_model_receipt()** (8 connections) — `pipeline/export_json.py`
- **load_block_periods()** (8 connections) — `pipeline/representative_models.py`
- **load_percentage_riders()** (8 connections) — `pipeline/representative_models.py`
- **load_rates()** (8 connections) — `pipeline/representative_models.py`
- **load_subsidies()** (8 connections) — `pipeline/representative_models.py`
- **_read_config()** (7 connections) — `pipeline/representative_models.py`
- **load_config()** (6 connections) — `pipeline/spark_gap.py`
- **Path** (4 connections)
- **format_coverage()** (3 connections) — `pipeline/representative_models.py`
- **ModuleType** (1 connections)
- **Path** (1 connections)
- **Keep optional monitoring setup out of the primary generation's failure path.** (1 connections) — `pipeline/export_json.py`
- **Build the representative models from the exported tariffs and write them as…** (1 connections) — `pipeline/export_json.py`
- *... and 13 more nodes in this community*

## Relationships

- [representative_models.py](representative_models.py.md) (26 shared connections)
- [run_scrape.py](run_scrape.py.md) (22 shared connections)
- [spark_gap.py](spark_gap.py.md) (14 shared connections)
- [model_monitoring.py](model_monitoring.py.md) (14 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (4 shared connections)
- [_prepare](_prepare.md) (4 shared connections)
- [check_db_history.py](check_db_history.py.md) (4 shared connections)
- [json](json.md) (4 shared connections)
- [Path](Path.md) (4 shared connections)
- [os](os.md) (3 shared connections)
- [market_pricing.py](market_pricing.py.md) (3 shared connections)
- [BaseScraper](BaseScraper.md) (3 shared connections)

## Source Files

- `pipeline/export_json.py`
- `pipeline/model_monitoring.py`
- `pipeline/representative_models.py`
- `pipeline/spark_gap.py`

## Audit Trail

- EXTRACTED: 202 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*