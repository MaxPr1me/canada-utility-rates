# run_scrape.py

> 74 nodes

## Key Concepts

- **run_scrape.py** (41 connections) — `pipeline/run_scrape.py`
- **export_json.py** (31 connections) — `pipeline/export_json.py`
- **main()** (23 connections) — `pipeline/run_scrape.py`
- **pathlib** (22 connections)
- **sys** (21 connections)
- **validate.py** (14 connections) — `pipeline/validate.py`
- **export_all()** (12 connections) — `pipeline/export_json.py`
- **export_representative_models()** (12 connections) — `pipeline/export_json.py`
- **setup_logging()** (11 connections) — `scrapers/utils/logging_config.py`
- **sqlite3** (11 connections)
- **logging_config.py** (10 connections) — `scrapers/utils/logging_config.py`
- **build_revisions()** (9 connections) — `pipeline/export_json.py`
- **export_rate_history_revisions()** (9 connections) — `pipeline/export_json.py`
- **main()** (9 connections) — `pipeline/validate.py`
- **start_model_receipt()** (8 connections) — `pipeline/export_json.py`
- **derive_provenance()** (6 connections) — `pipeline/export_json.py`
- **write_json()** (6 connections) — `pipeline/export_json.py`
- **tally_provenance()** (6 connections) — `pipeline/run_scrape.py`
- **generate_missing_classes_report()** (6 connections) — `pipeline/validate.py`
- **validate_batch()** (6 connections) — `scrapers/utils/validation.py`
- **Path** (6 connections)
- **load_scraper()** (5 connections) — `pipeline/run_scrape.py`
- **export_spark_gap()** (5 connections) — `pipeline/export_json.py`
- **_number_or_none()** (4 connections) — `pipeline/export_json.py`
- **_same_value()** (4 connections) — `pipeline/export_json.py`
- *... and 49 more nodes in this community*

## Relationships

- [json](json.md) (23 shared connections)
- [BaseScraper](BaseScraper.md) (14 shared connections)
- [registry.py](registry.py.md) (10 shared connections)
- [os](os.md) (7 shared connections)
- [write_spark_gap](write_spark_gap.md) (5 shared connections)
- [check_db_history.py](check_db_history.py.md) (5 shared connections)
- [market_pricing.py](market_pricing.py.md) (4 shared connections)
- [semantic_models](semantic_models.md) (4 shared connections)
- [TariffRecord](TariffRecord.md) (4 shared connections)
- [build_ontario_market.py](build_ontario_market.py.md) (4 shared connections)
- [main](main.md) (3 shared connections)
- [_build_model](_build_model.md) (3 shared connections)

## Source Files

- `pipeline/export_json.py`
- `pipeline/run_scrape.py`
- `pipeline/validate.py`
- `scrapers/base.py`
- `scrapers/utils/logging_config.py`
- `scrapers/utils/validation.py`

## Audit Trail

- EXTRACTED: 240 (98%)
- INFERRED: 4 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*