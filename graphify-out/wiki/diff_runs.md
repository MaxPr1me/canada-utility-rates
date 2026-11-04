# diff_runs

> 5 nodes

## Key Concepts

- **diff_runs()** (5 connections) — `pipeline/diff_report.py`
- **get_snapshots_for_run()** (5 connections) — `pipeline/diff_report.py`
- **Connection** (2 connections)
- **Get all tariff snapshots for a given scrape run, keyed by tariff_id.** (1 connections) — `pipeline/diff_report.py`
- **Compare two scrape runs and return a diff report. Returns a dict with keys: -…** (1 connections) — `pipeline/diff_report.py`

## Relationships

- [export_json.py](export_json.py.md) (3 shared connections)
- [json](json.md) (1 shared connections)

## Source Files

- `pipeline/diff_report.py`

## Audit Trail

- EXTRACTED: 9 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*