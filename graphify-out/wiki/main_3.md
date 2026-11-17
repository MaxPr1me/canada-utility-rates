# main

> 21 nodes

## Key Concepts

- **main()** (13 connections) — `pipeline/representative_models.py`
- **export_representative_models()** (12 connections) — `pipeline/export_json.py`
- **write_models()** (12 connections) — `pipeline/representative_models.py`
- **start_model_receipt()** (8 connections) — `pipeline/export_json.py`
- **load_crosswalk()** (7 connections) — `pipeline/representative_models.py`
- **load_taxes()** (7 connections) — `pipeline/representative_models.py`
- **load_usage_levels()** (7 connections) — `pipeline/representative_models.py`
- **PathLike** (7 connections)
- **load_rates()** (6 connections) — `pipeline/representative_models.py`
- **format_coverage()** (3 connections) — `pipeline/representative_models.py`
- **contextlib** (3 connections)
- **ModuleType** (1 connections)
- **Keep optional monitoring setup out of the primary generation's failure path.** (1 connections) — `pipeline/export_json.py`
- **Build the representative models from the exported tariffs and write them as…** (1 connections) — `pipeline/export_json.py`
- **Build the models (missing inputs load from their default paths) and write them…** (1 connections) — `pipeline/representative_models.py`
- **CLI: --coverage (Phase 7A) and/or --build [--output PATH] [--zone-policy ...]…** (1 connections) — `pipeline/representative_models.py`
- **Short plain-text summary of a coverage report.** (1 connections) — `pipeline/representative_models.py`
- **Read the crosswalk JSON (default data/models/crosswalk.json).** (1 connections) — `pipeline/representative_models.py`
- **Read the tax and rebate table (default data/models/taxes.json).** (1 connections) — `pipeline/representative_models.py`
- **Read the usage-level definitions (default data/models/usage_levels.json).** (1 connections) — `pipeline/representative_models.py`
- **Read an export (list of records) or a fixture ({"records": [...]}).** (1 connections) — `pipeline/representative_models.py`

## Relationships

- [representative_models.py](representative_models.py.md) (9 shared connections)
- [run_scrape.py](run_scrape.py.md) (6 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (6 shared connections)
- [build_models](build_models.md) (5 shared connections)
- [os](os.md) (2 shared connections)
- [model_monitoring.py](model_monitoring.py.md) (2 shared connections)
- [argparse](argparse.md) (1 shared connections)
- [_prepare](_prepare.md) (1 shared connections)
- [check_db_history.py](check_db_history.py.md) (1 shared connections)

## Source Files

- `pipeline/export_json.py`
- `pipeline/representative_models.py`

## Audit Trail

- EXTRACTED: 64 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*