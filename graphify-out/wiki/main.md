# main

> 25 nodes

## Key Concepts

- **main()** (13 connections) — `pipeline/representative_models.py`
- **export_representative_models()** (12 connections) — `pipeline/export_json.py`
- **write_models()** (12 connections) — `pipeline/representative_models.py`
- **PathLike** (10 connections)
- **start_model_receipt()** (8 connections) — `pipeline/export_json.py`
- **load_subsidies()** (8 connections) — `pipeline/representative_models.py`
- **load_crosswalk()** (7 connections) — `pipeline/representative_models.py`
- **load_taxes()** (7 connections) — `pipeline/representative_models.py`
- **load_usage_levels()** (7 connections) — `pipeline/representative_models.py`
- **_read_config()** (7 connections) — `pipeline/representative_models.py`
- **load_rates()** (6 connections) — `pipeline/representative_models.py`
- **format_coverage()** (3 connections) — `pipeline/representative_models.py`
- **ModuleType** (1 connections)
- **Path** (1 connections)
- **Keep optional monitoring setup out of the primary generation's failure path.** (1 connections) — `pipeline/export_json.py`
- **Build the representative models from the exported tariffs and write them as…** (1 connections) — `pipeline/export_json.py`
- **Reviewed territorial subsidies (default data/models/subsidies.json, owner…** (1 connections) — `pipeline/representative_models.py`
- **Short plain-text summary of a coverage report.** (1 connections) — `pipeline/representative_models.py`
- **Build the models (missing inputs load from their default paths) and write them…** (1 connections) — `pipeline/representative_models.py`
- **CLI: --coverage (Phase 7A) and/or --build [--output PATH] [--zone-policy ...]…** (1 connections) — `pipeline/representative_models.py`
- **Read the crosswalk JSON (default data/models/crosswalk.json).** (1 connections) — `pipeline/representative_models.py`
- **Read the usage-level definitions (default data/models/usage_levels.json).** (1 connections) — `pipeline/representative_models.py`
- **Read an export (list of records) or a fixture ({"records": [...]}).** (1 connections) — `pipeline/representative_models.py`
- **Read the tax and rebate table (default data/models/taxes.json).** (1 connections) — `pipeline/representative_models.py`
- **(document, problem) of a reviewed JSON configuration; a missing, unreadable or…** (1 connections) — `pipeline/representative_models.py`

## Relationships

- [representative_models.py](representative_models.py.md) (12 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (7 shared connections)
- [model_monitoring.py](model_monitoring.py.md) (6 shared connections)
- [build_models](build_models.md) (5 shared connections)
- [run_scrape.py](run_scrape.py.md) (4 shared connections)
- [build_revisions](build_revisions.md) (3 shared connections)
- [os](os.md) (2 shared connections)
- [Any](Any.md) (2 shared connections)

## Source Files

- `pipeline/export_json.py`
- `pipeline/representative_models.py`

## Audit Trail

- EXTRACTED: 77 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*