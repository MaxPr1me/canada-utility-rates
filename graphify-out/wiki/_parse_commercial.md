# ._parse_commercial

> 32 nodes

## Key Concepts

- **manitoba_hydro.py** (30 connections) — `scrapers/utilities/manitoba_hydro.py`
- **ManitobaHydroScraper** (15 connections) — `scrapers/utilities/manitoba_hydro.py`
- **._parse_commercial()** (11 connections) — `scrapers/utilities/manitoba_hydro.py`
- **._parse_lubd()** (9 connections) — `scrapers/utilities/manitoba_hydro.py`
- **._parse_residential()** (8 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_component()** (6 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_stamp()** (6 connections) — `scrapers/utilities/manitoba_hydro.py`
- **._parse_diesel_commercial()** (6 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_pairs()** (6 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_schedule_effective()** (6 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_effective()** (5 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_lines()** (5 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_number()** (5 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_assign_blocks()** (4 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_assign_demand_blocks()** (4 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_flat()** (4 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_section()** (3 connections) — `scrapers/utilities/manitoba_hydro.py`
- **section()** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **manitoba_hydro.py — Scraper for Manitoba Hydro electricity rates (Manitoba).…** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **Parse a Manitoba Hydro value line into (kind, value, unit); glyph-agnostic for…** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **Build a RateComponent from a label line and the value line that follows it.** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **Turn the parsed energy block rows into 1..n tiers with cumulative upper bounds…** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **Pair the zero-priced first kVA block with its balance row (both carry the same…** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **First 'Rates effective <date>' line ahead of the electricity tables -> (iso,…** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **Pair label/value lines against an exact spec; any unknown, missing or repeated…** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- *... and 7 more nodes in this community*

## Relationships

- [BaseScraper](BaseScraper.md) (11 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (8 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (7 shared connections)
- [re](re.md) (7 shared connections)
- [.mark_fallback](mark_fallback.md) (4 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (4 shared connections)
- [nb_power.py](nb_power.py.md) (4 shared connections)
- [.fetch_page](fetch_page.md) (1 shared connections)

## Source Files

- `scrapers/utilities/manitoba_hydro.py`

## Audit Trail

- EXTRACTED: 90 (93%)
- INFERRED: 7 (7%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*