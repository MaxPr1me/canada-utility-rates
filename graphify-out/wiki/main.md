# main

> 23 nodes

## Key Concepts

- **main()** (18 connections) — `pipeline/model_monitoring.py`
- **input_checks()** (13 connections) — `pipeline/model_monitoring.py`
- **write_json()** (10 connections) — `pipeline/model_monitoring.py`
- **read_json()** (8 connections) — `pipeline/model_monitoring.py`
- **load_percentage_riders()** (8 connections) — `pipeline/representative_models.py`
- **Path** (8 connections)
- **observe_previous()** (7 connections) — `pipeline/model_monitoring.py`
- **save_cost_quarterly()** (7 connections) — `pipeline/model_monitoring.py`
- **read_evidence_archive()** (6 connections) — `pipeline/model_monitoring.py`
- **_replace_text()** (6 connections) — `pipeline/model_monitoring.py`
- **manual_update_reviews()** (5 connections) — `pipeline/model_monitoring.py`
- **save_generation_receipt()** (5 connections) — `pipeline/model_monitoring.py`
- **zipfile** (3 connections)
- **reject_constant()** (1 connections) — `pipeline/model_monitoring.py`
- **Read only named JSON receipts from a small Actions artifact; never extract…** (1 connections) — `pipeline/model_monitoring.py`
- **Replace only a complete JSON document; retain earlier history on failure.** (1 connections) — `pipeline/model_monitoring.py`
- **Replace only a complete file; retain the earlier file on failure.** (1 connections) — `pipeline/model_monitoring.py`
- **Capture the replaced generation so a missed monitoring run can be disclosed…** (1 connections) — `pipeline/model_monitoring.py`
- **A monitoring defect must not break the primary exporter; missing receipts stay…** (1 connections) — `pipeline/model_monitoring.py`
- **Rewrite the quarter-end model costs from a recorded history; True when the file…** (1 connections) — `pipeline/model_monitoring.py`
- **Reuse coverage and observed-market validity rules; a documented missing model…** (1 connections) — `pipeline/model_monitoring.py`
- **Review dates of the ledger's manual-update utilities; malformed decisions are…** (1 connections) — `pipeline/model_monitoring.py`
- **Reviewed percentage riders (default data/models/percentage_riders.json, owner…** (1 connections) — `pipeline/representative_models.py`

## Relationships

- [model_monitoring.py](model_monitoring.py.md) (13 shared connections)
- [semantic_models](semantic_models.md) (12 shared connections)
- [json](json.md) (6 shared connections)
- [representative_models.py](representative_models.py.md) (4 shared connections)
- [workflow_checks](workflow_checks.md) (4 shared connections)
- [run_scrape.py](run_scrape.py.md) (4 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (2 shared connections)
- [load_subsidies](load_subsidies.md) (2 shared connections)
- [market_pricing.py](market_pricing.py.md) (1 shared connections)
- [rate_history.py](rate_history.py.md) (1 shared connections)
- [os](os.md) (1 shared connections)
- [Any](Any.md) (1 shared connections)

## Source Files

- `pipeline/model_monitoring.py`
- `pipeline/representative_models.py`

## Audit Trail

- EXTRACTED: 82 (99%)
- INFERRED: 1 (1%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*