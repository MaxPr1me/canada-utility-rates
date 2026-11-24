# main

> 32 nodes

## Key Concepts

- **main()** (13 connections) — `pipeline/representative_models.py`
- **input_checks()** (12 connections) — `pipeline/model_monitoring.py`
- **write_models()** (12 connections) — `pipeline/representative_models.py`
- **PathLike** (10 connections)
- **load_block_periods()** (8 connections) — `pipeline/representative_models.py`
- **load_percentage_riders()** (8 connections) — `pipeline/representative_models.py`
- **load_subsidies()** (8 connections) — `pipeline/representative_models.py`
- **load_crosswalk()** (7 connections) — `pipeline/representative_models.py`
- **load_taxes()** (7 connections) — `pipeline/representative_models.py`
- **load_usage_levels()** (7 connections) — `pipeline/representative_models.py`
- **_read_config()** (7 connections) — `pipeline/representative_models.py`
- **load_rates()** (6 connections) — `pipeline/representative_models.py`
- **load_market_document()** (5 connections) — `pipeline/representative_models.py`
- **format_models()** (4 connections) — `pipeline/representative_models.py`
- **_market_context()** (4 connections) — `pipeline/representative_models.py`
- **format_coverage()** (3 connections) — `pipeline/representative_models.py`
- **_fmt_money()** (2 connections) — `pipeline/representative_models.py`
- **Path** (1 connections)
- **Reuse coverage and observed-market validity rules; a documented missing model…** (1 connections) — `pipeline/model_monitoring.py`
- **Reviewed territorial subsidies (default data/models/subsidies.json, owner…** (1 connections) — `pipeline/representative_models.py`
- **The observed Ontario market history (default…** (1 connections) — `pipeline/representative_models.py`
- **Short plain-text summary of a coverage report.** (1 connections) — `pipeline/representative_models.py`
- **Build the models (missing inputs load from their default paths) and write them…** (1 connections) — `pipeline/representative_models.py`
- **Short plain-text summary of built models: per level n, medians without/with…** (1 connections) — `pipeline/representative_models.py`
- **CLI: --coverage (Phase 7A) and/or --build [--output PATH] [--zone-policy ...]…** (1 connections) — `pipeline/representative_models.py`
- *... and 7 more nodes in this community*

## Relationships

- [representative_models.py](representative_models.py.md) (15 shared connections)
- [run_scrape.py](run_scrape.py.md) (12 shared connections)
- [model_monitoring.py](model_monitoring.py.md) (8 shared connections)
- [build_models](build_models.md) (8 shared connections)
- [Any](Any.md) (5 shared connections)
- [market_pricing.py](market_pricing.py.md) (2 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (1 shared connections)
- [os](os.md) (1 shared connections)

## Source Files

- `pipeline/model_monitoring.py`
- `pipeline/representative_models.py`

## Audit Trail

- EXTRACTED: 95 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*