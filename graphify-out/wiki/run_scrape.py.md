# run_scrape.py

> 63 nodes

## Key Concepts

- **run_scrape.py** (41 connections) — `pipeline/run_scrape.py`
- **argparse** (33 connections)
- **export_json.py** (29 connections) — `pipeline/export_json.py`
- **main()** (23 connections) — `pipeline/run_scrape.py`
- **pathlib** (19 connections)
- **sys** (19 connections)
- **validate.py** (14 connections) — `pipeline/validate.py`
- **diff_report.py** (13 connections) — `pipeline/diff_report.py`
- **export_all()** (11 connections) — `pipeline/export_json.py`
- **setup_logging()** (11 connections) — `scrapers/utils/logging_config.py`
- **sqlite3** (11 connections)
- **logging_config.py** (10 connections) — `scrapers/utils/logging_config.py`
- **main()** (9 connections) — `pipeline/validate.py`
- **main()** (8 connections) — `pipeline/diff_report.py`
- **derive_provenance()** (6 connections) — `pipeline/export_json.py`
- **canonical_snapshot()** (6 connections) — `pipeline/run_scrape.py`
- **store_results()** (6 connections) — `pipeline/run_scrape.py`
- **tally_provenance()** (6 connections) — `pipeline/run_scrape.py`
- **generate_missing_classes_report()** (6 connections) — `pipeline/validate.py`
- **validate_batch()** (6 connections) — `scrapers/utils/validation.py`
- **load_scraper()** (5 connections) — `pipeline/run_scrape.py`
- **emit_github_notice()** (4 connections) — `pipeline/run_scrape.py`
- **format_github_notice()** (4 connections) — `pipeline/run_scrape.py`
- **format_summary_markdown()** (4 connections) — `pipeline/run_scrape.py`
- **init_db()** (4 connections) — `pipeline/run_scrape.py`
- *... and 38 more nodes in this community*

## Relationships

- [BaseScraper](BaseScraper.md) (15 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (12 shared connections)
- [registry.py](registry.py.md) (12 shared connections)
- [build_revisions](build_revisions.md) (11 shared connections)
- [model_monitoring.py](model_monitoring.py.md) (10 shared connections)
- [os](os.md) (8 shared connections)
- [build_alberta_market.py](build_alberta_market.py.md) (8 shared connections)
- [TariffRecord](TariffRecord.md) (6 shared connections)
- [check_db_history.py](check_db_history.py.md) (6 shared connections)
- [main](main.md) (4 shared connections)
- [archive_ontario_price.py](archive_ontario_price.py.md) (4 shared connections)
- [build_ontario_market.py](build_ontario_market.py.md) (4 shared connections)

## Source Files

- `pipeline/diff_report.py`
- `pipeline/export_json.py`
- `pipeline/run_scrape.py`
- `pipeline/validate.py`
- `scrapers/base.py`
- `scrapers/utils/logging_config.py`
- `scrapers/utils/validation.py`

## Audit Trail

- EXTRACTED: 236 (98%)
- INFERRED: 6 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*