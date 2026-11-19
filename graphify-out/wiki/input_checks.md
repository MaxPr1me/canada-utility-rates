# input_checks

> 13 nodes

## Key Concepts

- **input_checks()** (10 connections) — `pipeline/model_monitoring.py`
- **write_json()** (10 connections) — `pipeline/model_monitoring.py`
- **read_json()** (8 connections) — `pipeline/model_monitoring.py`
- **load_block_periods()** (8 connections) — `pipeline/representative_models.py`
- **observe_previous()** (7 connections) — `pipeline/model_monitoring.py`
- **Path** (6 connections)
- **save_generation_receipt()** (5 connections) — `pipeline/model_monitoring.py`
- **reject_constant()** (1 connections) — `pipeline/model_monitoring.py`
- **Capture the replaced generation so a missed monitoring run can be disclosed…** (1 connections) — `pipeline/model_monitoring.py`
- **A monitoring defect must not break the primary exporter; missing receipts stay…** (1 connections) — `pipeline/model_monitoring.py`
- **Reuse coverage and observed-market validity rules; a documented missing model…** (1 connections) — `pipeline/model_monitoring.py`
- **Replace only a complete JSON document; retain earlier history on failure.** (1 connections) — `pipeline/model_monitoring.py`
- **Reviewed periods of bare-'kWh' block thresholds (default…** (1 connections) — `pipeline/representative_models.py`

## Relationships

- [main](main.md) (10 shared connections)
- [model_monitoring.py](model_monitoring.py.md) (7 shared connections)
- [run_scrape.py](run_scrape.py.md) (5 shared connections)
- [build_models](build_models.md) (2 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (1 shared connections)
- [market_pricing.py](market_pricing.py.md) (1 shared connections)
- [record_refresh](record_refresh.md) (1 shared connections)
- [os](os.md) (1 shared connections)
- [Any](Any.md) (1 shared connections)
- [representative_models.py](representative_models.py.md) (1 shared connections)

## Source Files

- `pipeline/model_monitoring.py`
- `pipeline/representative_models.py`

## Audit Trail

- EXTRACTED: 44 (98%)
- INFERRED: 1 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*