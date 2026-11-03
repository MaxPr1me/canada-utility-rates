# json

> 25 nodes

## Key Concepts

- **json** (54 connections)
- **build_models()** (22 connections) — `pipeline/representative_models.py`
- **main()** (12 connections) — `pipeline/representative_models.py`
- **write_models()** (12 connections) — `pipeline/representative_models.py`
- **export_representative_models()** (11 connections) — `pipeline/export_json.py`
- **load_crosswalk()** (7 connections) — `pipeline/representative_models.py`
- **load_taxes()** (7 connections) — `pipeline/representative_models.py`
- **load_usage_levels()** (7 connections) — `pipeline/representative_models.py`
- **PathLike** (7 connections)
- **load_block_periods()** (6 connections) — `pipeline/representative_models.py`
- **load_rates()** (6 connections) — `pipeline/representative_models.py`
- **load_market_document()** (5 connections) — `pipeline/representative_models.py`
- **_market_context()** (4 connections) — `pipeline/representative_models.py`
- **format_coverage()** (3 connections) — `pipeline/representative_models.py`
- **Build the representative models from the exported tariffs and write them as…** (1 connections) — `pipeline/export_json.py`
- **The observed Ontario market history (default…** (1 connections) — `pipeline/representative_models.py`
- **Representative models for every crosswalk model key of the given provinces and…** (1 connections) — `pipeline/representative_models.py`
- **Build the models (missing inputs load from their default paths) and write them…** (1 connections) — `pipeline/representative_models.py`
- **CLI: --coverage (Phase 7A) and/or --build [--output PATH] [--zone-policy ...]…** (1 connections) — `pipeline/representative_models.py`
- **Short plain-text summary of a coverage report.** (1 connections) — `pipeline/representative_models.py`
- **Read the crosswalk JSON (default data/models/crosswalk.json).** (1 connections) — `pipeline/representative_models.py`
- **Read the tax and rebate table (default data/models/taxes.json).** (1 connections) — `pipeline/representative_models.py`
- **Read the usage-level definitions (default data/models/usage_levels.json).** (1 connections) — `pipeline/representative_models.py`
- **Read an export (list of records) or a fixture ({"records": [...]}).** (1 connections) — `pipeline/representative_models.py`
- **Reviewed periods of bare-'kWh' block thresholds (default…** (1 connections) — `pipeline/representative_models.py`

## Relationships

- [run_scrape.py](run_scrape.py.md) (17 shared connections)
- [representative_models.py](representative_models.py.md) (16 shared connections)
- [Any](Any.md) (8 shared connections)
- [coverage_report](coverage_report.md) (6 shared connections)
- [graphify_hook.py](graphify_hook.py.md) (5 shared connections)
- [check_db_history.py](check_db_history.py.md) (4 shared connections)
- [market_pricing.py](market_pricing.py.md) (3 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (3 shared connections)
- [os](os.md) (2 shared connections)
- [_fullmatch](_fullmatch.md) (2 shared connections)
- [compose_pairs](compose_pairs.md) (2 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (2 shared connections)

## Source Files

- `pipeline/export_json.py`
- `pipeline/representative_models.py`

## Audit Trail

- EXTRACTED: 129 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*