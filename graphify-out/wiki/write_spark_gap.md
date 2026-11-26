# write_spark_gap

> 28 nodes

## Key Concepts

- **write_spark_gap()** (15 connections) — `pipeline/spark_gap.py`
- **main()** (13 connections) — `pipeline/representative_models.py`
- **write_models()** (12 connections) — `pipeline/representative_models.py`
- **main()** (12 connections) — `pipeline/spark_gap.py`
- **PathLike** (10 connections)
- **load_crosswalk()** (9 connections) — `pipeline/representative_models.py`
- **load_taxes()** (9 connections) — `pipeline/representative_models.py`
- **load_usage_levels()** (9 connections) — `pipeline/representative_models.py`
- **load_json()** (8 connections) — `pipeline/spark_gap.py`
- **load_percentage_riders()** (8 connections) — `pipeline/representative_models.py`
- **load_rates()** (8 connections) — `pipeline/representative_models.py`
- **load_subsidies()** (8 connections) — `pipeline/representative_models.py`
- **_read_config()** (7 connections) — `pipeline/representative_models.py`
- **load_config()** (6 connections) — `pipeline/spark_gap.py`
- **Path** (4 connections)
- **format_coverage()** (3 connections) — `pipeline/representative_models.py`
- **Path** (1 connections)
- **Reviewed territorial subsidies (default data/models/subsidies.json, owner…** (1 connections) — `pipeline/representative_models.py`
- **Short plain-text summary of a coverage report.** (1 connections) — `pipeline/representative_models.py`
- **Build the models (missing inputs load from their default paths) and write them…** (1 connections) — `pipeline/representative_models.py`
- **CLI: --coverage (Phase 7A) and/or --build [--output PATH] [--zone-policy ...]…** (1 connections) — `pipeline/representative_models.py`
- **Read the crosswalk JSON (default data/models/crosswalk.json).** (1 connections) — `pipeline/representative_models.py`
- **Read the usage-level definitions (default data/models/usage_levels.json).** (1 connections) — `pipeline/representative_models.py`
- **Read the tax and rebate table (default data/models/taxes.json).** (1 connections) — `pipeline/representative_models.py`
- **Read an export (list of records) or a fixture ({"records": [...]}).** (1 connections) — `pipeline/representative_models.py`
- *... and 3 more nodes in this community*

## Relationships

- [spark_gap.py](spark_gap.py.md) (12 shared connections)
- [_build_model](_build_model.md) (12 shared connections)
- [json](json.md) (10 shared connections)
- [representative_models.py](representative_models.py.md) (6 shared connections)
- [run_scrape.py](run_scrape.py.md) (5 shared connections)
- [Any](Any.md) (3 shared connections)
- [main](main.md) (2 shared connections)
- [model_monitoring.py](model_monitoring.py.md) (2 shared connections)
- [os](os.md) (2 shared connections)
- [BaseScraper](BaseScraper.md) (1 shared connections)

## Source Files

- `pipeline/representative_models.py`
- `pipeline/spark_gap.py`

## Audit Trail

- EXTRACTED: 104 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*