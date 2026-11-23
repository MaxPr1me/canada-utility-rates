# run_scrape.py

> 68 nodes

## Key Concepts

- **run_scrape.py** (41 connections) — `pipeline/run_scrape.py`
- **main()** (23 connections) — `pipeline/run_scrape.py`
- **registry.py** (20 connections) — `scrapers/registry.py`
- **load_registry()** (13 connections) — `scrapers/registry.py`
- **validation.py** (11 connections) — `scrapers/utils/validation.py`
- **find_utility()** (8 connections) — `scrapers/registry.py`
- **monthly_price_utilities()** (8 connections) — `scrapers/registry.py`
- **get_active_utilities()** (7 connections) — `scrapers/registry.py`
- **suggest_names()** (7 connections) — `scrapers/registry.py`
- **validate_tariff()** (6 connections) — `scrapers/utils/validation.py`
- **canonical_snapshot()** (6 connections) — `pipeline/run_scrape.py`
- **store_results()** (6 connections) — `pipeline/run_scrape.py`
- **tally_provenance()** (6 connections) — `pipeline/run_scrape.py`
- **validate_batch()** (6 connections) — `scrapers/utils/validation.py`
- **load_scraper()** (5 connections) — `pipeline/run_scrape.py`
- **derive_provenance()** (5 connections) — `pipeline/export_json.py`
- **dispatch_input_errors()** (5 connections) — `scrapers/registry.py`
- **main()** (5 connections) — `scrapers/registry.py`
- **normalize_name()** (5 connections) — `scrapers/registry.py`
- **utc_now()** (4 connections) — `pipeline/model_monitoring.py`
- **emit_github_notice()** (4 connections) — `pipeline/run_scrape.py`
- **format_github_notice()** (4 connections) — `pipeline/run_scrape.py`
- **format_summary_markdown()** (4 connections) — `pipeline/run_scrape.py`
- **init_db()** (4 connections) — `pipeline/run_scrape.py`
- **summarize_run()** (4 connections) — `pipeline/run_scrape.py`
- *... and 43 more nodes in this community*

## Relationships

- [argparse](argparse.md) (17 shared connections)
- [BaseScraper](BaseScraper.md) (12 shared connections)
- [model_monitoring.py](model_monitoring.py.md) (10 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (8 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (5 shared connections)
- [graphify_hook.py](graphify_hook.py.md) (2 shared connections)
- [ntpc.py](ntpc.py.md) (2 shared connections)
- [re](re.md) (2 shared connections)
- [RateComponent](RateComponent.md) (2 shared connections)
- [os](os.md) (1 shared connections)

## Source Files

- `pipeline/export_json.py`
- `pipeline/model_monitoring.py`
- `pipeline/run_scrape.py`
- `scrapers/base.py`
- `scrapers/registry.py`
- `scrapers/utils/validation.py`

## Audit Trail

- EXTRACTED: 161 (95%)
- INFERRED: 8 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*