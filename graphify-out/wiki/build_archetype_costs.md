# build_archetype_costs

> 10 nodes

## Key Concepts

- **build_archetype_costs()** (16 connections) — `pipeline/archetype_costs.py`
- **archetype_fingerprint()** (9 connections) — `pipeline/archetype_profiles.py`
- **_digest()** (6 connections) — `pipeline/archetype_costs.py`
- **hourly_fingerprint()** (5 connections) — `pipeline/archetype_costs.py`
- **load_market_documents()** (5 connections) — `pipeline/archetype_costs.py`
- **number()** (1 connections) — `pipeline/archetype_profiles.py`
- **SHA-256 of every run's hourly kWh and monthly gas (rounded to six decimals),…** (1 connections) — `pipeline/archetype_costs.py`
- **The observed market histories the estimates price with: Ontario through the…** (1 connections) — `pipeline/archetype_costs.py`
- **The archetype costs document (method AC-1); raises ValueError on unusable…** (1 connections) — `pipeline/archetype_costs.py`
- **SHA-256 of every value the models read from the validated runs (identity, size,…** (1 connections) — `pipeline/archetype_profiles.py`

## Relationships

- [archetype_costs.py](archetype_costs.py.md) (9 shared connections)
- [archetype_profiles.py](archetype_profiles.py.md) (5 shared connections)
- [write_spark_gap](write_spark_gap.md) (4 shared connections)
- [representative_models.py](representative_models.py.md) (3 shared connections)
- [check_db_history.py](check_db_history.py.md) (2 shared connections)
- [_prepare](_prepare.md) (1 shared connections)
- [.price_fuel](price_fuel.md) (1 shared connections)
- [ArchetypeRun](ArchetypeRun.md) (1 shared connections)

## Source Files

- `pipeline/archetype_costs.py`
- `pipeline/archetype_profiles.py`

## Audit Trail

- EXTRACTED: 36 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*