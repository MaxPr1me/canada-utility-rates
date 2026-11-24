# main

> 27 nodes

## Key Concepts

- **os** (24 connections)
- **main()** (13 connections) — `pipeline/representative_models.py`
- **export_representative_models()** (12 connections) — `pipeline/export_json.py`
- **write_models()** (12 connections) — `pipeline/representative_models.py`
- **start_model_receipt()** (8 connections) — `pipeline/export_json.py`
- **load_block_periods()** (8 connections) — `pipeline/representative_models.py`
- **load_crosswalk()** (7 connections) — `pipeline/representative_models.py`
- **load_taxes()** (7 connections) — `pipeline/representative_models.py`
- **load_usage_levels()** (7 connections) — `pipeline/representative_models.py`
- **PathLike** (7 connections)
- **load_rates()** (6 connections) — `pipeline/representative_models.py`
- **write_document()** (6 connections) — `scripts/generate_market_pricing.py`
- **write_json()** (5 connections) — `pipeline/export_json.py`
- **Path** (4 connections)
- **contextlib** (3 connections)
- **ModuleType** (1 connections)
- **Keep optional monitoring setup out of the primary generation's failure path.** (1 connections) — `pipeline/export_json.py`
- **Build the representative models from the exported tariffs and write them as…** (1 connections) — `pipeline/export_json.py`
- **Write data to a JSON file with nice formatting.** (1 connections) — `pipeline/export_json.py`
- **Build the models (missing inputs load from their default paths) and write them…** (1 connections) — `pipeline/representative_models.py`
- **CLI: --coverage (Phase 7A) and/or --build [--output PATH] [--zone-policy ...]…** (1 connections) — `pipeline/representative_models.py`
- **Read the crosswalk JSON (default data/models/crosswalk.json).** (1 connections) — `pipeline/representative_models.py`
- **Read the usage-level definitions (default data/models/usage_levels.json).** (1 connections) — `pipeline/representative_models.py`
- **Read an export (list of records) or a fixture ({"records": [...]}).** (1 connections) — `pipeline/representative_models.py`
- **Read the tax and rebate table (default data/models/taxes.json).** (1 connections) — `pipeline/representative_models.py`
- *... and 2 more nodes in this community*

## Relationships

- [check_db_history.py](check_db_history.py.md) (11 shared connections)
- [representative_models.py](representative_models.py.md) (11 shared connections)
- [run_scrape.py](run_scrape.py.md) (10 shared connections)
- [build_models](build_models.md) (5 shared connections)
- [model_monitoring.py](model_monitoring.py.md) (5 shared connections)
- [graphify_hook.py](graphify_hook.py.md) (5 shared connections)
- [Any](Any.md) (3 shared connections)
- [generate_market_pricing.py](generate_market_pricing.py.md) (3 shared connections)
- [archive_ontario_price.py](archive_ontario_price.py.md) (2 shared connections)
- [build_alberta_market.py](build_alberta_market.py.md) (2 shared connections)
- [build_ontario_market.py](build_ontario_market.py.md) (2 shared connections)
- [preserve_ieso_reports.py](preserve_ieso_reports.py.md) (2 shared connections)

## Source Files

- `pipeline/export_json.py`
- `pipeline/representative_models.py`
- `scripts/generate_market_pricing.py`

## Audit Trail

- EXTRACTED: 102 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*