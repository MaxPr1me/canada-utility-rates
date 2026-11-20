# run_scrape.py

> 45 nodes

## Key Concepts

- **run_scrape.py** (39 connections) — `pipeline/run_scrape.py`
- **main()** (21 connections) — `pipeline/run_scrape.py`
- **registry.py** (10 connections) — `scrapers/registry.py`
- **load_registry()** (9 connections) — `scrapers/registry.py`
- **store_results()** (6 connections) — `pipeline/run_scrape.py`
- **tally_provenance()** (6 connections) — `pipeline/run_scrape.py`
- **validate_batch()** (6 connections) — `scrapers/utils/validation.py`
- **load_scraper()** (5 connections) — `pipeline/run_scrape.py`
- **derive_provenance()** (5 connections) — `pipeline/export_json.py`
- **run_identity()** (5 connections) — `pipeline/model_monitoring.py`
- **get_active_utilities()** (5 connections) — `scrapers/registry.py`
- **utc_now()** (4 connections) — `pipeline/model_monitoring.py`
- **emit_github_notice()** (4 connections) — `pipeline/run_scrape.py`
- **format_github_notice()** (4 connections) — `pipeline/run_scrape.py`
- **format_summary_markdown()** (4 connections) — `pipeline/run_scrape.py`
- **init_db()** (4 connections) — `pipeline/run_scrape.py`
- **summarize_run()** (4 connections) — `pipeline/run_scrape.py`
- **is_excluded_class_estimate()** (4 connections) — `scrapers/base.py`
- **append_step_summary()** (3 connections) — `pipeline/run_scrape.py`
- **get_utilities_by_province()** (3 connections) — `scrapers/registry.py`
- **get_utility()** (3 connections) — `scrapers/registry.py`
- **importlib** (2 connections)
- **names()** (1 connections) — `pipeline/run_scrape.py`
- **cell()** (1 connections) — `pipeline/run_scrape.py`
- **names_with()** (1 connections) — `pipeline/run_scrape.py`
- *... and 20 more nodes in this community*

## Relationships

- [argparse](argparse.md) (15 shared connections)
- [BaseScraper](BaseScraper.md) (11 shared connections)
- [model_monitoring.py](model_monitoring.py.md) (7 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (5 shared connections)
- [main](main.md) (4 shared connections)
- [graphify_hook.py](graphify_hook.py.md) (3 shared connections)
- [validation.py](validation.py.md) (1 shared connections)
- [os](os.md) (1 shared connections)

## Source Files

- `pipeline/export_json.py`
- `pipeline/model_monitoring.py`
- `pipeline/run_scrape.py`
- `scrapers/base.py`
- `scrapers/registry.py`
- `scrapers/utils/validation.py`

## Audit Trail

- EXTRACTED: 108 (96%)
- INFERRED: 5 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*