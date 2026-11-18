# argparse

> 16 nodes

## Key Concepts

- **json** (60 connections)
- **diff_report.py** (13 connections) — `pipeline/diff_report.py`
- **main()** (8 connections) — `pipeline/diff_report.py`
- **canonical_snapshot()** (6 connections) — `pipeline/run_scrape.py`
- **store_results()** (6 connections) — `pipeline/run_scrape.py`
- **diff_runs()** (5 connections) — `pipeline/diff_report.py`
- **get_snapshots_for_run()** (5 connections) — `pipeline/diff_report.py`
- **print_diff_report()** (3 connections) — `pipeline/diff_report.py`
- **Connection** (2 connections)
- **Connection** (1 connections)
- **diff_report.py — Compare two scrape runs and report changes. This tool helps…** (1 connections) — `pipeline/diff_report.py`
- **Get all tariff snapshots for a given scrape run, keyed by tariff_id.** (1 connections) — `pipeline/diff_report.py`
- **Compare two scrape runs and return a diff report. Returns a dict with keys: -…** (1 connections) — `pipeline/diff_report.py`
- **Print a human-readable diff report.** (1 connections) — `pipeline/diff_report.py`
- **Serialize a semantic tariff deterministically for historical hashing. Component…** (1 connections) — `pipeline/run_scrape.py`
- **Store scraped tariff records into the database. Returns the number of records…** (1 connections) — `pipeline/run_scrape.py`

## Relationships

- [run_scrape.py](run_scrape.py.md) (19 shared connections)
- [main](main.md) (7 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (5 shared connections)
- [model_monitoring.py](model_monitoring.py.md) (5 shared connections)
- [graphify_hook.py](graphify_hook.py.md) (5 shared connections)
- [check_db_history.py](check_db_history.py.md) (4 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (2 shared connections)
- [BaseScraper](BaseScraper.md) (2 shared connections)
- [representative_models.py](representative_models.py.md) (2 shared connections)
- [build_models](build_models.md) (2 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (2 shared connections)
- [grand_forks.py](grand_forks.py.md) (2 shared connections)

## Source Files

- `pipeline/diff_report.py`
- `pipeline/run_scrape.py`

## Audit Trail

- EXTRACTED: 92 (98%)
- INFERRED: 2 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*