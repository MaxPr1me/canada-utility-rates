# run_scrape.py

> 65 nodes

## Key Concepts

- **run_scrape.py** (41 connections) — `pipeline/run_scrape.py`
- **argparse** (39 connections)
- **export_json.py** (33 connections) — `pipeline/export_json.py`
- **main()** (23 connections) — `pipeline/run_scrape.py`
- **pathlib** (23 connections)
- **sys** (22 connections)
- **validate.py** (14 connections) — `pipeline/validate.py`
- **export_all()** (13 connections) — `pipeline/export_json.py`
- **diff_report.py** (13 connections) — `pipeline/diff_report.py`
- **setup_logging()** (11 connections) — `scrapers/utils/logging_config.py`
- **sqlite3** (11 connections)
- **logging_config.py** (10 connections) — `scrapers/utils/logging_config.py`
- **main()** (9 connections) — `pipeline/validate.py`
- **main()** (8 connections) — `pipeline/diff_report.py`
- **Path** (7 connections)
- **derive_provenance()** (6 connections) — `pipeline/export_json.py`
- **write_json()** (6 connections) — `pipeline/export_json.py`
- **tally_provenance()** (6 connections) — `pipeline/run_scrape.py`
- **generate_missing_classes_report()** (6 connections) — `pipeline/validate.py`
- **validate_batch()** (6 connections) — `scrapers/utils/validation.py`
- **load_scraper()** (5 connections) — `pipeline/run_scrape.py`
- **export_archetype_costs()** (5 connections) — `pipeline/export_json.py`
- **export_spark_gap()** (5 connections) — `pipeline/export_json.py`
- **emit_github_notice()** (4 connections) — `pipeline/run_scrape.py`
- **format_github_notice()** (4 connections) — `pipeline/run_scrape.py`
- *... and 40 more nodes in this community*

## Relationships

- [write_spark_gap](write_spark_gap.md) (20 shared connections)
- [BaseScraper](BaseScraper.md) (13 shared connections)
- [registry.py](registry.py.md) (12 shared connections)
- [build_revisions](build_revisions.md) (10 shared connections)
- [build_ontario_market.py](build_ontario_market.py.md) (8 shared connections)
- [graphify_hook.py](graphify_hook.py.md) (8 shared connections)
- [check_db_history.py](check_db_history.py.md) (7 shared connections)
- [semantic_models](semantic_models.md) (4 shared connections)
- [TariffRecord](TariffRecord.md) (4 shared connections)
- [spark_gap.py](spark_gap.py.md) (4 shared connections)
- [archetype_costs.py](archetype_costs.py.md) (4 shared connections)
- [archive_ontario_price.py](archive_ontario_price.py.md) (4 shared connections)

## Source Files

- `pipeline/diff_report.py`
- `pipeline/export_json.py`
- `pipeline/run_scrape.py`
- `pipeline/validate.py`
- `scrapers/base.py`
- `scrapers/utils/logging_config.py`
- `scrapers/utils/validation.py`

## Audit Trail

- EXTRACTED: 262 (98%)
- INFERRED: 4 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*