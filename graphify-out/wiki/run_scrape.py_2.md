# run_scrape.py

> 51 nodes

## Key Concepts

- **argparse** (37 connections)
- **export_json.py** (31 connections) — `pipeline/export_json.py`
- **pathlib** (22 connections)
- **sys** (21 connections)
- **validate.py** (14 connections) — `pipeline/validate.py`
- **diff_report.py** (13 connections) — `pipeline/diff_report.py`
- **export_all()** (12 connections) — `pipeline/export_json.py`
- **setup_logging()** (11 connections) — `scrapers/utils/logging_config.py`
- **sqlite3** (11 connections)
- **logging_config.py** (10 connections) — `scrapers/utils/logging_config.py`
- **build_revisions()** (9 connections) — `pipeline/export_json.py`
- **export_rate_history_revisions()** (9 connections) — `pipeline/export_json.py`
- **main()** (9 connections) — `pipeline/validate.py`
- **main()** (8 connections) — `pipeline/diff_report.py`
- **write_json()** (6 connections) — `pipeline/export_json.py`
- **generate_missing_classes_report()** (6 connections) — `pipeline/validate.py`
- **Path** (6 connections)
- **diff_runs()** (5 connections) — `pipeline/diff_report.py`
- **get_snapshots_for_run()** (5 connections) — `pipeline/diff_report.py`
- **export_spark_gap()** (5 connections) — `pipeline/export_json.py`
- **_number_or_none()** (4 connections) — `pipeline/export_json.py`
- **_same_value()** (4 connections) — `pipeline/export_json.py`
- **run_validation()** (4 connections) — `pipeline/validate.py`
- **contextlib** (4 connections)
- **print_diff_report()** (3 connections) — `pipeline/diff_report.py`
- *... and 26 more nodes in this community*

## Relationships

- [run_scrape.py](run_scrape.py.md) (18 shared connections)
- [write_spark_gap](write_spark_gap.md) (17 shared connections)
- [check_db_history.py](check_db_history.py.md) (7 shared connections)
- [os](os.md) (6 shared connections)
- [BaseScraper](BaseScraper.md) (6 shared connections)
- [market_pricing.py](market_pricing.py.md) (4 shared connections)
- [model_monitoring.py](model_monitoring.py.md) (4 shared connections)
- [spark_gap.py](spark_gap.py.md) (4 shared connections)
- [archive_ontario_price.py](archive_ontario_price.py.md) (4 shared connections)
- [build_alberta_market.py](build_alberta_market.py.md) (4 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (4 shared connections)
- [io](io.md) (4 shared connections)

## Source Files

- `pipeline/diff_report.py`
- `pipeline/export_json.py`
- `pipeline/validate.py`
- `scrapers/utils/logging_config.py`

## Audit Trail

- EXTRACTED: 204 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*