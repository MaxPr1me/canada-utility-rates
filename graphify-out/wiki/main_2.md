# main

> 5 nodes

## Key Concepts

- **render_document()** (6 connections) — `scripts/build_ontario_market.py`
- **write_outputs()** (5 connections) — `scripts/build_ontario_market.py`
- **Path** (3 connections)
- **The JSON bytes to write, or None when only generated_at would change.** (1 connections) — `scripts/build_ontario_market.py`
- **Write every file to a temporary sibling first, then move them all into place.** (1 connections) — `scripts/build_ontario_market.py`

## Relationships

- [build_ontario_market.py](build_ontario_market.py.md) (5 shared connections)
- [json](json.md) (1 shared connections)
- [model_monitoring.py](model_monitoring.py.md) (1 shared connections)
- [os](os.md) (1 shared connections)

## Source Files

- `scripts/build_ontario_market.py`

## Audit Trail

- EXTRACTED: 12 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*