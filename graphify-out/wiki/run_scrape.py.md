# run_scrape.py

> 58 nodes

## Key Concepts

- **run_scrape.py** (41 connections) — `pipeline/run_scrape.py`
- **main()** (23 connections) — `pipeline/run_scrape.py`
- **registry.py** (20 connections) — `scrapers/registry.py`
- **load_registry()** (13 connections) — `scrapers/registry.py`
- **find_utility()** (8 connections) — `scrapers/registry.py`
- **monthly_price_utilities()** (8 connections) — `scrapers/registry.py`
- **get_active_utilities()** (7 connections) — `scrapers/registry.py`
- **suggest_names()** (7 connections) — `scrapers/registry.py`
- **canonical_snapshot()** (6 connections) — `pipeline/run_scrape.py`
- **store_results()** (6 connections) — `pipeline/run_scrape.py`
- **tally_provenance()** (6 connections) — `pipeline/run_scrape.py`
- **validate_batch()** (6 connections) — `scrapers/utils/validation.py`
- **load_scraper()** (5 connections) — `pipeline/run_scrape.py`
- **dispatch_input_errors()** (5 connections) — `scrapers/registry.py`
- **main()** (5 connections) — `scrapers/registry.py`
- **normalize_name()** (5 connections) — `scrapers/registry.py`
- **emit_github_notice()** (4 connections) — `pipeline/run_scrape.py`
- **format_github_notice()** (4 connections) — `pipeline/run_scrape.py`
- **format_summary_markdown()** (4 connections) — `pipeline/run_scrape.py`
- **init_db()** (4 connections) — `pipeline/run_scrape.py`
- **summarize_run()** (4 connections) — `pipeline/run_scrape.py`
- **is_excluded_class_estimate()** (4 connections) — `scrapers/base.py`
- **get_utility()** (4 connections) — `scrapers/registry.py`
- **unicodedata** (4 connections)
- **append_step_summary()** (3 connections) — `pipeline/run_scrape.py`
- *... and 33 more nodes in this community*

## Relationships

- [json](json.md) (22 shared connections)
- [BaseScraper](BaseScraper.md) (9 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (6 shared connections)
- [main](main.md) (4 shared connections)
- [semantic_models](semantic_models.md) (4 shared connections)
- [os](os.md) (3 shared connections)
- [validate_tariff](validate_tariff.md) (3 shared connections)
- [model_monitoring.py](model_monitoring.py.md) (2 shared connections)
- [re](re.md) (2 shared connections)
- [ntpc.py](ntpc.py.md) (2 shared connections)

## Source Files

- `pipeline/run_scrape.py`
- `scrapers/base.py`
- `scrapers/registry.py`
- `scrapers/utils/validation.py`

## Audit Trail

- EXTRACTED: 144 (96%)
- INFERRED: 6 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*