# ManitobaHydroScraper

> 23 nodes

## Key Concepts

- **._parse_commercial()** (11 connections) — `scrapers/utilities/manitoba_hydro.py`
- **._parse_residential()** (8 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_component()** (6 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_stamp()** (6 connections) — `scrapers/utilities/manitoba_hydro.py`
- **._parse_diesel_commercial()** (6 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_pairs()** (6 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_effective()** (5 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_lines()** (5 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_number()** (5 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_assign_blocks()** (4 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_assign_demand_blocks()** (4 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_section()** (3 connections) — `scrapers/utilities/manitoba_hydro.py`
- **section()** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **Parse a Manitoba Hydro value line into (kind, value, unit); glyph-agnostic for…** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **Build a RateComponent from a label line and the value line that follows it.** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **Turn the parsed energy block rows into 1..n tiers with cumulative upper bounds…** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **Pair the zero-priced first kVA block with its balance row (both carry the same…** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **First 'Rates effective <date>' line ahead of the electricity tables -> (iso,…** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **Pair label/value lines against an exact spec; any unknown, missing or repeated…** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **Parse residential rates from the Manitoba Hydro residential page text.** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **Parse every general-service class from the Manitoba Hydro commercial rates…** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **Parse the diesel-zone general service and government/First Nation education…** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **Map a header line to a commercial section index (see _MB_COMMERCIAL), else None.** (1 connections) — `scrapers/utilities/manitoba_hydro.py`

## Relationships

- [BaseScraper](BaseScraper.md) (9 shared connections)
- [re](re.md) (4 shared connections)
- [RateComponent](RateComponent.md) (4 shared connections)
- [ManitobaHydroScraper](ManitobaHydroScraper.md) (4 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (4 shared connections)
- [parse_html](parse_html.md) (1 shared connections)

## Source Files

- `scrapers/utilities/manitoba_hydro.py`

## Audit Trail

- EXTRACTED: 50 (94%)
- INFERRED: 3 (6%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*