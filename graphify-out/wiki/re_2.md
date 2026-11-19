# re

> 28 nodes

## Key Concepts

- **re** (244 connections)
- **parse_manual()** (15 connections) — `scrapers/utilities/saint_john_energy.py`
- **_mb_schedule_effective()** (6 connections) — `scrapers/utilities/manitoba_hydro.py`
- **manual_revision()** (6 connections) — `scrapers/utilities/saint_john_energy.py`
- **current_tariff_link()** (5 connections) — `scrapers/utilities/enmax_power.py`
- **_class_blocks()** (5 connections) — `scrapers/utilities/saint_john_energy.py`
- **_energy_rows()** (5 connections) — `scrapers/utilities/saint_john_energy.py`
- **parse_joint_schedules()** (5 connections) — `scrapers/utilities/yukon_energy.py`
- **rider_a_terms()** (5 connections) — `scrapers/utilities/yukon_energy.py`
- **_mb_flat()** (4 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_iso()** (4 connections) — `scrapers/utilities/saint_john_energy.py`
- **_applicability()** (3 connections) — `scrapers/utilities/saint_john_energy.py`
- **clean_number()** (3 connections) — `scrapers/utils/parsing.py`
- **normalize_charge_unit()** (3 connections) — `scrapers/utils/parsing.py`
- **_cents()** (2 connections) — `scrapers/utilities/saint_john_energy.py`
- **_minimum_kw()** (2 connections) — `scrapers/utilities/saint_john_energy.py`
- **add()** (2 connections) — `scrapers/utilities/saint_john_energy.py`
- **date** (1 connections)
- **Return the one ENMAX link labelled as the current distribution tariff, else…** (1 connections) — `scrapers/utilities/enmax_power.py`
- **Cover-page 'EFFECTIVE <date>' and 'APPROVED IN ORDER <n>' -> (iso, printed,…** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **(base, rider, total) in $/kWh for each printed energy block, in order.** (1 connections) — `scrapers/utilities/saint_john_energy.py`
- **Build every in-scope schedule from the manual's Section 9 pages; raise…** (1 connections) — `scrapers/utilities/saint_john_energy.py`
- **ISO date of the manual's 'Document revised as of <date>' cover line.** (1 connections) — `scrapers/utilities/saint_john_energy.py`
- **Text of each in-scope schedule (its first page plus a '... continued' page), by…** (1 connections) — `scrapers/utilities/saint_john_energy.py`
- **Return complete residential/general-service terms by code; incomplete schedules…** (1 connections) — `scrapers/utilities/yukon_energy.py`
- *... and 3 more nodes in this community*

## Relationships

- [BaseScraper](BaseScraper.md) (50 shared connections)
- [enmax_power.py](enmax_power.py.md) (17 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (16 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (15 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (15 shared connections)
- [epcor_distribution.py](epcor_distribution.py.md) (12 shared connections)
- [ntpc.py](ntpc.py.md) (12 shared connections)
- [DocumentPage](DocumentPage.md) (9 shared connections)
- [EPCOROntarioGasScraper](EPCOROntarioGasScraper.md) (9 shared connections)
- [fortisalberta.py](fortisalberta.py.md) (7 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (7 shared connections)
- [._parse_commercial](_parse_commercial.md) (6 shared connections)

## Source Files

- `scrapers/utilities/enmax_power.py`
- `scrapers/utilities/manitoba_hydro.py`
- `scrapers/utilities/saint_john_energy.py`
- `scrapers/utilities/yukon_energy.py`
- `scrapers/utils/parsing.py`

## Audit Trail

- EXTRACTED: 290 (98%)
- INFERRED: 6 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*