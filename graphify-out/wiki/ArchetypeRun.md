# ArchetypeRun

> 15 nodes

## Key Concepts

- **ArchetypeRun** (20 connections) — `pipeline/archetype_profiles.py`
- **price_run()** (14 connections) — `pipeline/archetype_costs.py`
- **.average_monthly_peak_kw()** (7 connections) — `pipeline/archetype_profiles.py`
- **.annual_gas_gj()** (4 connections) — `pipeline/archetype_profiles.py`
- **.annual_kwh()** (4 connections) — `pipeline/archetype_profiles.py`
- **.kwh_per_kw()** (4 connections) — `pipeline/archetype_profiles.py`
- **_effective()** (4 connections) — `pipeline/archetype_costs.py`
- **.average_monthly_kwh()** (3 connections) — `pipeline/archetype_profiles.py`
- **.unmet_occupied_hours()** (3 connections) — `pipeline/archetype_profiles.py`
- **.max_peak_kw()** (2 connections) — `pipeline/archetype_profiles.py`
- **.quality_flag()** (2 connections) — `pipeline/archetype_profiles.py`
- **One run's published entry: identity, load, each fuel's priced months and the…** (1 connections) — `pipeline/archetype_costs.py`
- **Mean of the 12 monthly highest 15-minute demands: Toronto Hydro's "monthly…** (1 connections) — `pipeline/archetype_profiles.py`
- **Average monthly kWh per kW of average monthly peak (x 100 gives the kWh of a…** (1 connections) — `pipeline/archetype_profiles.py`
- **One validated simulation run; kWh and kW are whole-building electricity, gas in…** (1 connections) — `pipeline/archetype_profiles.py`

## Relationships

- [.price_fuel](price_fuel.md) (13 shared connections)
- [archetype_profiles.py](archetype_profiles.py.md) (3 shared connections)
- [archetype_costs.py](archetype_costs.py.md) (2 shared connections)
- [_energy_estimate](_energy_estimate.md) (1 shared connections)
- [build_archetype_costs](build_archetype_costs.md) (1 shared connections)
- [market_pricing.py](market_pricing.py.md) (1 shared connections)

## Source Files

- `pipeline/archetype_costs.py`
- `pipeline/archetype_profiles.py`

## Audit Trail

- EXTRACTED: 35 (76%)
- INFERRED: 11 (24%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*