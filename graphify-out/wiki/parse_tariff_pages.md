# parse_tariff_pages

> 25 nodes

## Key Concepts

- **parse_tariff_pages()** (22 connections) — `scrapers/utils/oeb_tariff.py`
- **TariffSheet** (10 connections) — `scrapers/utils/oeb_tariff.py`
- **parse_tariff_zones()** (8 connections) — `scrapers/utils/oeb_tariff.py`
- **_approved_copies()** (7 connections) — `scrapers/utils/oeb_tariff.py`
- **_dedupe_classifications()** (6 connections) — `scrapers/utils/oeb_tariff.py`
- **add_line()** (5 connections) — `scrapers/utils/oeb_tariff.py`
- **_signature()** (4 connections) — `scrapers/utils/oeb_tariff.py`
- **_today_iso()** (4 connections) — `scrapers/utils/oeb_tariff.py`
- **date** (4 connections)
- **.classification()** (3 connections) — `scrapers/utils/oeb_tariff.py`
- **extend_tail()** (3 connections) — `scrapers/utils/oeb_tariff.py`
- **flush_allowance()** (3 connections) — `scrapers/utils/oeb_tariff.py`
- **start_class()** (3 connections) — `scrapers/utils/oeb_tariff.py`
- **_split_footnotes()** (3 connections) — `scrapers/utils/oeb_tariff.py`
- **_tail_split()** (3 connections) — `scrapers/utils/oeb_tariff.py`
- **proposed()** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **single()** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **start_charges()** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Parse every rate zone in a (possibly multi-zone) tariff document.** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Split "<previous label tail>) <new label>" glued together by row joining.** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Split a numbered NOTES section ("1. ... 2. ..." or "1) ... 2) ...") into {"1":…** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Drop tariff copies printed under a "Proposed/Draft Tariff of Rates and Charges"…** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Published values only: copies may word rider labels differently (Entegrus draft…** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Identical repeated classes collapse to the first; differing repeats are…** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Parse OEB tariff pages for one distributor (and, if given, one rate zone). Non-…** (1 connections) — `scrapers/utils/oeb_tariff.py`

## Relationships

- [oeb_tariff.py](oeb_tariff.py.md) (16 shared connections)
- [build_demand_records](build_demand_records.md) (9 shared connections)
- [close_class](close_class.md) (3 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (3 shared connections)
- [._energy_entries](_energy_entries.md) (2 shared connections)
- [ontario_ldc.py](ontario_ldc.py.md) (1 shared connections)

## Source Files

- `scrapers/utils/oeb_tariff.py`

## Audit Trail

- EXTRACTED: 63 (95%)
- INFERRED: 3 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*