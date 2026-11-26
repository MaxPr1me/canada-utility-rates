# build_revisions

> 12 nodes

## Key Concepts

- **build_revisions()** (9 connections) — `pipeline/export_json.py`
- **export_rate_history_revisions()** (9 connections) — `pipeline/export_json.py`
- **_number_or_none()** (4 connections) — `pipeline/export_json.py`
- **_same_value()** (4 connections) — `pipeline/export_json.py`
- **contextlib** (4 connections)
- **_none_first()** (3 connections) — `pipeline/export_json.py`
- **Connection** (2 connections)
- **A value the revisions file can carry: a finite number, or None for a value-less…** (1 connections) — `pipeline/export_json.py`
- **Equal stored values, ignoring floating-point noise such as 0.10859999999999999…** (1 connections) — `pipeline/export_json.py`
- **Sort key that puts None first and never compares a number with text.** (1 connections) — `pipeline/export_json.py`
- **Find the same-date price corrections in the database snapshots (owner decision…** (1 connections) — `pipeline/export_json.py`
- **Write the same-date corrections for the Rate History tab (owner decision 55,…** (1 connections) — `pipeline/export_json.py`

## Relationships

- [run_scrape.py](run_scrape.py.md) (10 shared connections)
- [write_spark_gap](write_spark_gap.md) (3 shared connections)
- [market_pricing.py](market_pricing.py.md) (2 shared connections)
- [check_db_history.py](check_db_history.py.md) (1 shared connections)

## Source Files

- `pipeline/export_json.py`

## Audit Trail

- EXTRACTED: 28 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*