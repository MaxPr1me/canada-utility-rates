# record_refresh

> 19 nodes

## Key Concepts

- **record_refresh()** (10 connections) — `pipeline/model_monitoring.py`
- **workflow_checks()** (10 connections) — `pipeline/model_monitoring.py`
- **timestamp()** (9 connections) — `pipeline/model_monitoring.py`
- **_successful_generation()** (6 connections) — `pipeline/model_monitoring.py`
- **validate_history()** (6 connections) — `pipeline/model_monitoring.py`
- **manual_update_reviews()** (5 connections) — `pipeline/model_monitoring.py`
- **scheduled_due()** (5 connections) — `pipeline/model_monitoring.py`
- **datetime** (5 connections)
- **copy** (5 connections)
- **source_checks()** (4 connections) — `pipeline/model_monitoring.py`
- **date** (3 connections)
- **_evidence()** (2 connections) — `pipeline/model_monitoring.py`
- **Validate producer evidence before either history recording or freshness can…** (1 connections) — `pipeline/model_monitoring.py`
- **Corrupt or incompatible history cannot be silently reset or extended.** (1 connections) — `pipeline/model_monitoring.py`
- **Advance the last-reported baseline only after an explicitly successful,…** (1 connections) — `pipeline/model_monitoring.py`
- **Evaluate the repository's fixed UTC day-of-month schedules, rejecting other…** (1 connections) — `pipeline/model_monitoring.py`
- **Review dates of the ledger's manual-update utilities; malformed decisions are…** (1 connections) — `pipeline/model_monitoring.py`
- **Use completed-step evidence, including source provenance; a green badge alone…** (1 connections) — `pipeline/model_monitoring.py`
- **Reject ambiguous clocks instead of treating a local time as UTC.** (1 connections) — `pipeline/model_monitoring.py`

## Relationships

- [model_monitoring.py](model_monitoring.py.md) (12 shared connections)
- [main](main.md) (9 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (1 shared connections)
- [re](re.md) (1 shared connections)
- [enmax_power.py](enmax_power.py.md) (1 shared connections)
- [input_checks](input_checks.md) (1 shared connections)
- [BaseScraper](BaseScraper.md) (1 shared connections)
- [build_ontario_market.py](build_ontario_market.py.md) (1 shared connections)

## Source Files

- `pipeline/model_monitoring.py`

## Audit Trail

- EXTRACTED: 52 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*