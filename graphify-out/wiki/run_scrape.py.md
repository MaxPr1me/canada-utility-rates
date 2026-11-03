# run_scrape.py

> 80 nodes

## Key Concepts

- **run_scrape.py** (35 connections) — `pipeline/run_scrape.py`
- **argparse** (28 connections)
- **export_json.py** (19 connections) — `pipeline/export_json.py`
- **sys** (19 connections)
- **main()** (18 connections) — `pipeline/run_scrape.py`
- **pathlib** (18 connections)
- **validate.py** (14 connections) — `pipeline/validate.py`
- **diff_report.py** (13 connections) — `pipeline/diff_report.py`
- **setup_logging()** (11 connections) — `scrapers/utils/logging_config.py`
- **sqlite3** (11 connections)
- **registry.py** (10 connections) — `scrapers/registry.py`
- **logging_config.py** (10 connections) — `scrapers/utils/logging_config.py`
- **export_all()** (9 connections) — `pipeline/export_json.py`
- **main()** (9 connections) — `pipeline/validate.py`
- **load_registry()** (9 connections) — `scrapers/registry.py`
- **main()** (8 connections) — `pipeline/diff_report.py`
- **canonical_snapshot()** (6 connections) — `pipeline/run_scrape.py`
- **store_results()** (6 connections) — `pipeline/run_scrape.py`
- **generate_missing_classes_report()** (6 connections) — `pipeline/validate.py`
- **validate_batch()** (6 connections) — `scrapers/utils/validation.py`
- **load_scraper()** (5 connections) — `pipeline/run_scrape.py`
- **diff_runs()** (5 connections) — `pipeline/diff_report.py`
- **get_snapshots_for_run()** (5 connections) — `pipeline/diff_report.py`
- **derive_provenance()** (5 connections) — `pipeline/export_json.py`
- **write_json()** (5 connections) — `pipeline/export_json.py`
- *... and 55 more nodes in this community*

## Relationships

- [json](json.md) (17 shared connections)
- [BaseScraper](BaseScraper.md) (14 shared connections)
- [os](os.md) (8 shared connections)
- [check_db_history.py](check_db_history.py.md) (7 shared connections)
- [TariffRecord](TariffRecord.md) (6 shared connections)
- [archive_ontario_price.py](archive_ontario_price.py.md) (4 shared connections)
- [build_alberta_market.py](build_alberta_market.py.md) (4 shared connections)
- [build_ontario_market.py](build_ontario_market.py.md) (4 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (4 shared connections)
- [export_ontario_totals.py](export_ontario_totals.py.md) (4 shared connections)
- [generate_market_pricing.py](generate_market_pricing.py.md) (4 shared connections)
- [graphify_hook.py](graphify_hook.py.md) (4 shared connections)

## Source Files

- `pipeline/diff_report.py`
- `pipeline/export_json.py`
- `pipeline/run_scrape.py`
- `pipeline/validate.py`
- `scrapers/registry.py`
- `scrapers/utils/logging_config.py`
- `scrapers/utils/validation.py`

## Audit Trail

- EXTRACTED: 233 (97%)
- INFERRED: 6 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*