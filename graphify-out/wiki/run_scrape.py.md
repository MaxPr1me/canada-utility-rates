# run_scrape.py

> 43 nodes

## Key Concepts

- **run_scrape.py** (35 connections) — `pipeline/run_scrape.py`
- **main()** (18 connections) — `pipeline/run_scrape.py`
- **registry.py** (10 connections) — `scrapers/registry.py`
- **load_registry()** (9 connections) — `scrapers/registry.py`
- **canonical_snapshot()** (6 connections) — `pipeline/run_scrape.py`
- **store_results()** (6 connections) — `pipeline/run_scrape.py`
- **validate_batch()** (6 connections) — `scrapers/utils/validation.py`
- **load_scraper()** (5 connections) — `pipeline/run_scrape.py`
- **derive_provenance()** (5 connections) — `pipeline/export_json.py`
- **tally_provenance()** (5 connections) — `pipeline/run_scrape.py`
- **get_active_utilities()** (5 connections) — `scrapers/registry.py`
- **emit_github_notice()** (4 connections) — `pipeline/run_scrape.py`
- **format_github_notice()** (4 connections) — `pipeline/run_scrape.py`
- **format_summary_markdown()** (4 connections) — `pipeline/run_scrape.py`
- **init_db()** (4 connections) — `pipeline/run_scrape.py`
- **summarize_run()** (4 connections) — `pipeline/run_scrape.py`
- **append_step_summary()** (3 connections) — `pipeline/run_scrape.py`
- **get_utilities_by_province()** (3 connections) — `scrapers/registry.py`
- **get_utility()** (3 connections) — `scrapers/registry.py`
- **importlib** (2 connections)
- **names()** (1 connections) — `pipeline/run_scrape.py`
- **cell()** (1 connections) — `pipeline/run_scrape.py`
- **names_with()** (1 connections) — `pipeline/run_scrape.py`
- **Connection** (1 connections)
- **Path** (1 connections)
- *... and 18 more nodes in this community*

## Relationships

- [export_json.py](export_json.py.md) (15 shared connections)
- [BaseScraper](BaseScraper.md) (8 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (6 shared connections)
- [json](json.md) (5 shared connections)
- [os](os.md) (3 shared connections)
- [validation.py](validation.py.md) (3 shared connections)

## Source Files

- `pipeline/export_json.py`
- `pipeline/run_scrape.py`
- `scrapers/registry.py`
- `scrapers/utils/validation.py`

## Audit Trail

- EXTRACTED: 96 (94%)
- INFERRED: 6 (6%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*