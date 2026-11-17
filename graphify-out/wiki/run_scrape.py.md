# run_scrape.py

> 65 nodes

## Key Concepts

- **run_scrape.py** (38 connections) — `pipeline/run_scrape.py`
- **export_json.py** (23 connections) — `pipeline/export_json.py`
- **main()** (21 connections) — `pipeline/run_scrape.py`
- **pathlib** (19 connections)
- **sys** (19 connections)
- **validate.py** (14 connections) — `pipeline/validate.py`
- **setup_logging()** (11 connections) — `scrapers/utils/logging_config.py`
- **sqlite3** (11 connections)
- **export_all()** (10 connections) — `pipeline/export_json.py`
- **registry.py** (10 connections) — `scrapers/registry.py`
- **logging_config.py** (10 connections) — `scrapers/utils/logging_config.py`
- **main()** (9 connections) — `pipeline/validate.py`
- **load_registry()** (9 connections) — `scrapers/registry.py`
- **generate_missing_classes_report()** (6 connections) — `pipeline/validate.py`
- **validate_batch()** (6 connections) — `scrapers/utils/validation.py`
- **load_scraper()** (5 connections) — `pipeline/run_scrape.py`
- **derive_provenance()** (5 connections) — `pipeline/export_json.py`
- **write_json()** (5 connections) — `pipeline/export_json.py`
- **tally_provenance()** (5 connections) — `pipeline/run_scrape.py`
- **get_active_utilities()** (5 connections) — `scrapers/registry.py`
- **utc_now()** (4 connections) — `pipeline/model_monitoring.py`
- **emit_github_notice()** (4 connections) — `pipeline/run_scrape.py`
- **format_github_notice()** (4 connections) — `pipeline/run_scrape.py`
- **format_summary_markdown()** (4 connections) — `pipeline/run_scrape.py`
- **init_db()** (4 connections) — `pipeline/run_scrape.py`
- *... and 40 more nodes in this community*

## Relationships

- [BaseScraper](BaseScraper.md) (15 shared connections)
- [argparse](argparse.md) (13 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (10 shared connections)
- [model_monitoring.py](model_monitoring.py.md) (8 shared connections)
- [main](main.md) (6 shared connections)
- [os](os.md) (5 shared connections)
- [TariffRecord](TariffRecord.md) (4 shared connections)
- [check_db_history.py](check_db_history.py.md) (4 shared connections)
- [canonical_snapshot](canonical_snapshot.md) (3 shared connections)
- [representative_models.py](representative_models.py.md) (2 shared connections)
- [archive_ontario_price.py](archive_ontario_price.py.md) (2 shared connections)
- [build_alberta_market.py](build_alberta_market.py.md) (2 shared connections)

## Source Files

- `pipeline/export_json.py`
- `pipeline/model_monitoring.py`
- `pipeline/run_scrape.py`
- `pipeline/validate.py`
- `scrapers/registry.py`
- `scrapers/utils/logging_config.py`
- `scrapers/utils/validation.py`

## Audit Trail

- EXTRACTED: 199 (98%)
- INFERRED: 4 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*