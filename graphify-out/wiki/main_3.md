# main

> 15 nodes

## Key Concepts

- **main()** (13 connections) — `pipeline/representative_models.py`
- **write_models()** (12 connections) — `pipeline/representative_models.py`
- **load_crosswalk()** (7 connections) — `pipeline/representative_models.py`
- **load_taxes()** (7 connections) — `pipeline/representative_models.py`
- **load_usage_levels()** (7 connections) — `pipeline/representative_models.py`
- **PathLike** (7 connections)
- **load_rates()** (6 connections) — `pipeline/representative_models.py`
- **format_coverage()** (3 connections) — `pipeline/representative_models.py`
- **Build the models (missing inputs load from their default paths) and write them…** (1 connections) — `pipeline/representative_models.py`
- **CLI: --coverage (Phase 7A) and/or --build [--output PATH] [--zone-policy ...]…** (1 connections) — `pipeline/representative_models.py`
- **Short plain-text summary of a coverage report.** (1 connections) — `pipeline/representative_models.py`
- **Read the crosswalk JSON (default data/models/crosswalk.json).** (1 connections) — `pipeline/representative_models.py`
- **Read the tax and rebate table (default data/models/taxes.json).** (1 connections) — `pipeline/representative_models.py`
- **Read the usage-level definitions (default data/models/usage_levels.json).** (1 connections) — `pipeline/representative_models.py`
- **Read an export (list of records) or a fixture ({"records": [...]}).** (1 connections) — `pipeline/representative_models.py`

## Relationships

- [run_scrape.py](run_scrape.py.md) (10 shared connections)
- [representative_models.py](representative_models.py.md) (9 shared connections)
- [build_models](build_models.md) (3 shared connections)
- [os](os.md) (1 shared connections)
- [Any](Any.md) (1 shared connections)
- [input_checks](input_checks.md) (1 shared connections)

## Source Files

- `pipeline/representative_models.py`

## Audit Trail

- EXTRACTED: 47 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*