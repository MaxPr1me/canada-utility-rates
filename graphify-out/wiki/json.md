# json

> 22 nodes

## Key Concepts

- **json** (68 connections)
- **main()** (13 connections) — `pipeline/representative_models.py`
- **export_representative_models()** (12 connections) — `pipeline/export_json.py`
- **write_models()** (12 connections) — `pipeline/representative_models.py`
- **PathLike** (10 connections)
- **start_model_receipt()** (8 connections) — `pipeline/export_json.py`
- **load_crosswalk()** (7 connections) — `pipeline/representative_models.py`
- **load_taxes()** (7 connections) — `pipeline/representative_models.py`
- **load_usage_levels()** (7 connections) — `pipeline/representative_models.py`
- **write_json()** (6 connections) — `pipeline/export_json.py`
- **load_rates()** (6 connections) — `pipeline/representative_models.py`
- **Path** (5 connections)
- **ModuleType** (1 connections)
- **Keep optional monitoring setup out of the primary generation's failure path.** (1 connections) — `pipeline/export_json.py`
- **Build the representative models from the exported tariffs and write them as…** (1 connections) — `pipeline/export_json.py`
- **Write data to a JSON file with nice formatting.** (1 connections) — `pipeline/export_json.py`
- **Build the models (missing inputs load from their default paths) and write them…** (1 connections) — `pipeline/representative_models.py`
- **CLI: --coverage (Phase 7A) and/or --build [--output PATH] [--zone-policy ...]…** (1 connections) — `pipeline/representative_models.py`
- **Read the crosswalk JSON (default data/models/crosswalk.json).** (1 connections) — `pipeline/representative_models.py`
- **Read the usage-level definitions (default data/models/usage_levels.json).** (1 connections) — `pipeline/representative_models.py`
- **Read the tax and rebate table (default data/models/taxes.json).** (1 connections) — `pipeline/representative_models.py`
- **Read an export (list of records) or a fixture ({"records": [...]}).** (1 connections) — `pipeline/representative_models.py`

## Relationships

- [representative_models.py](representative_models.py.md) (19 shared connections)
- [json](json.md) (17 shared connections)
- [main](main.md) (5 shared connections)
- [graphify_hook.py](graphify_hook.py.md) (5 shared connections)
- [run_scrape.py](run_scrape.py.md) (4 shared connections)
- [check_db_history.py](check_db_history.py.md) (4 shared connections)
- [os](os.md) (3 shared connections)
- [load_subsidies](load_subsidies.md) (3 shared connections)
- [build_alberta_market.py](build_alberta_market.py.md) (3 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (3 shared connections)
- [archetype_profiles.py](archetype_profiles.py.md) (2 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (2 shared connections)

## Source Files

- `pipeline/export_json.py`
- `pipeline/representative_models.py`

## Audit Trail

- EXTRACTED: 132 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*