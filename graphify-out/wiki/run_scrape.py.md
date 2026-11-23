# run_scrape.py

> 72 nodes

## Key Concepts

- **run_scrape.py** (41 connections) — `pipeline/run_scrape.py`
- **argparse** (33 connections)
- **main()** (23 connections) — `pipeline/run_scrape.py`
- **export_json.py** (23 connections) — `pipeline/export_json.py`
- **pathlib** (19 connections)
- **sys** (19 connections)
- **validate.py** (14 connections) — `pipeline/validate.py`
- **diff_report.py** (13 connections) — `pipeline/diff_report.py`
- **setup_logging()** (11 connections) — `scrapers/utils/logging_config.py`
- **validation.py** (11 connections) — `scrapers/utils/validation.py`
- **sqlite3** (11 connections)
- **export_all()** (10 connections) — `pipeline/export_json.py`
- **logging_config.py** (10 connections) — `scrapers/utils/logging_config.py`
- **main()** (9 connections) — `pipeline/validate.py`
- **main()** (8 connections) — `pipeline/diff_report.py`
- **validate_tariff()** (6 connections) — `scrapers/utils/validation.py`
- **canonical_snapshot()** (6 connections) — `pipeline/run_scrape.py`
- **store_results()** (6 connections) — `pipeline/run_scrape.py`
- **tally_provenance()** (6 connections) — `pipeline/run_scrape.py`
- **generate_missing_classes_report()** (6 connections) — `pipeline/validate.py`
- **validate_batch()** (6 connections) — `scrapers/utils/validation.py`
- **load_scraper()** (5 connections) — `pipeline/run_scrape.py`
- **derive_provenance()** (5 connections) — `pipeline/export_json.py`
- **utc_now()** (4 connections) — `pipeline/model_monitoring.py`
- **emit_github_notice()** (4 connections) — `pipeline/run_scrape.py`
- *... and 47 more nodes in this community*

## Relationships

- [BaseScraper](BaseScraper.md) (16 shared connections)
- [main](main.md) (15 shared connections)
- [registry.py](registry.py.md) (12 shared connections)
- [model_monitoring.py](model_monitoring.py.md) (10 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (8 shared connections)
- [check_db_history.py](check_db_history.py.md) (7 shared connections)
- [graphify_hook.py](graphify_hook.py.md) (6 shared connections)
- [os](os.md) (6 shared connections)
- [archive_ontario_price.py](archive_ontario_price.py.md) (4 shared connections)
- [build_alberta_market.py](build_alberta_market.py.md) (4 shared connections)
- [build_ontario_market.py](build_ontario_market.py.md) (4 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (4 shared connections)

## Source Files

- `pipeline/diff_report.py`
- `pipeline/export_json.py`
- `pipeline/model_monitoring.py`
- `pipeline/run_scrape.py`
- `pipeline/validate.py`
- `scrapers/base.py`
- `scrapers/utils/logging_config.py`
- `scrapers/utils/validation.py`

## Audit Trail

- EXTRACTED: 244 (97%)
- INFERRED: 8 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*