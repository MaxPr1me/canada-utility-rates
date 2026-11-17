# export_json.py

> 27 nodes

## Key Concepts

- **export_json.py** (19 connections) — `pipeline/export_json.py`
- **sys** (19 connections)
- **pathlib** (18 connections)
- **validate.py** (14 connections) — `pipeline/validate.py`
- **setup_logging()** (11 connections) — `scrapers/utils/logging_config.py`
- **sqlite3** (11 connections)
- **logging_config.py** (10 connections) — `scrapers/utils/logging_config.py`
- **export_all()** (9 connections) — `pipeline/export_json.py`
- **main()** (9 connections) — `pipeline/validate.py`
- **generate_missing_classes_report()** (6 connections) — `pipeline/validate.py`
- **derive_provenance()** (5 connections) — `pipeline/export_json.py`
- **write_json()** (5 connections) — `pipeline/export_json.py`
- **run_validation()** (4 connections) — `pipeline/validate.py`
- **print_issues()** (3 connections) — `pipeline/validate.py`
- **Path** (2 connections)
- **Connection** (2 connections)
- **export_json.py — Export database contents to JSON for the static site. The…** (1 connections) — `pipeline/export_json.py`
- **Write data to a JSON file with nice formatting.** (1 connections) — `pipeline/export_json.py`
- **Classify a tariff as live-sourced or seed from its provenance marker.…** (1 connections) — `pipeline/export_json.py`
- **Export all data from the database to JSON files for the site.** (1 connections) — `pipeline/export_json.py`
- **validate.py — Post-scrape validation and data quality checks. Run this after a…** (1 connections) — `pipeline/validate.py`
- **Print validation issues in a readable format.** (1 connections) — `pipeline/validate.py`
- **Generate a report of utilities missing expected customer classes. For…** (1 connections) — `pipeline/validate.py`
- **Run all validation checks and return a list of issues. Each issue is a dict…** (1 connections) — `pipeline/validate.py`
- **logging_config.py — Set up logging for the scraper framework. Call…** (1 connections) — `scrapers/utils/logging_config.py`
- *... and 2 more nodes in this community*

## Relationships

- [run_scrape.py](run_scrape.py.md) (13 shared connections)
- [argparse](argparse.md) (10 shared connections)
- [json](json.md) (7 shared connections)
- [BaseScraper](BaseScraper.md) (5 shared connections)
- [check_db_history.py](check_db_history.py.md) (5 shared connections)
- [build_alberta_market.py](build_alberta_market.py.md) (4 shared connections)
- [os](os.md) (3 shared connections)
- [representative_models.py](representative_models.py.md) (2 shared connections)
- [archive_ontario_price.py](archive_ontario_price.py.md) (2 shared connections)
- [build_ontario_market.py](build_ontario_market.py.md) (2 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (2 shared connections)
- [generate_market_pricing.py](generate_market_pricing.py.md) (2 shared connections)

## Source Files

- `pipeline/export_json.py`
- `pipeline/validate.py`
- `scrapers/utils/logging_config.py`

## Audit Trail

- EXTRACTED: 110 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*