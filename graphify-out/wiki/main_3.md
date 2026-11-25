# main

> 25 nodes

## Key Concepts

- **main()** (13 connections) — `pipeline/representative_models.py`
- **write_models()** (12 connections) — `pipeline/representative_models.py`
- **PathLike** (10 connections)
- **load_block_periods()** (8 connections) — `pipeline/representative_models.py`
- **load_percentage_riders()** (8 connections) — `pipeline/representative_models.py`
- **load_crosswalk()** (7 connections) — `pipeline/representative_models.py`
- **load_taxes()** (7 connections) — `pipeline/representative_models.py`
- **load_usage_levels()** (7 connections) — `pipeline/representative_models.py`
- **_read_config()** (7 connections) — `pipeline/representative_models.py`
- **load_rates()** (6 connections) — `pipeline/representative_models.py`
- **format_models()** (4 connections) — `pipeline/representative_models.py`
- **format_coverage()** (3 connections) — `pipeline/representative_models.py`
- **_fmt_money()** (2 connections) — `pipeline/representative_models.py`
- **Path** (1 connections)
- **Short plain-text summary of a coverage report.** (1 connections) — `pipeline/representative_models.py`
- **Build the models (missing inputs load from their default paths) and write them…** (1 connections) — `pipeline/representative_models.py`
- **Short plain-text summary of built models: per level n, medians without/with…** (1 connections) — `pipeline/representative_models.py`
- **CLI: --coverage (Phase 7A) and/or --build [--output PATH] [--zone-policy ...]…** (1 connections) — `pipeline/representative_models.py`
- **Read the crosswalk JSON (default data/models/crosswalk.json).** (1 connections) — `pipeline/representative_models.py`
- **Read the usage-level definitions (default data/models/usage_levels.json).** (1 connections) — `pipeline/representative_models.py`
- **Read the tax and rebate table (default data/models/taxes.json).** (1 connections) — `pipeline/representative_models.py`
- **Read an export (list of records) or a fixture ({"records": [...]}).** (1 connections) — `pipeline/representative_models.py`
- **Reviewed periods of bare-'kWh' block thresholds (default…** (1 connections) — `pipeline/representative_models.py`
- **(document, problem) of a reviewed JSON configuration; a missing, unreadable or…** (1 connections) — `pipeline/representative_models.py`
- **Reviewed percentage riders (default data/models/percentage_riders.json, owner…** (1 connections) — `pipeline/representative_models.py`

## Relationships

- [representative_models.py](representative_models.py.md) (12 shared connections)
- [json](json.md) (12 shared connections)
- [build_models](build_models.md) (6 shared connections)
- [main](main.md) (4 shared connections)
- [Any](Any.md) (3 shared connections)
- [model_monitoring.py](model_monitoring.py.md) (2 shared connections)
- [os](os.md) (1 shared connections)

## Source Files

- `pipeline/representative_models.py`

## Audit Trail

- EXTRACTED: 73 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*