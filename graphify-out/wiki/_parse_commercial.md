# ._parse_commercial

> 29 nodes

## Key Concepts

- **ManitobaHydroScraper** (15 connections) — `scrapers/utilities/manitoba_hydro.py`
- **._parse_commercial()** (11 connections) — `scrapers/utilities/manitoba_hydro.py`
- **._parse_lubd()** (9 connections) — `scrapers/utilities/manitoba_hydro.py`
- **._parse_residential()** (8 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_component()** (6 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_stamp()** (6 connections) — `scrapers/utilities/manitoba_hydro.py`
- **._parse_diesel_commercial()** (6 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_pairs()** (6 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_effective()** (5 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_lines()** (5 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_number()** (5 connections) — `scrapers/utilities/manitoba_hydro.py`
- **._lubd_record()** (4 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_assign_blocks()** (4 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_assign_demand_blocks()** (4 connections) — `scrapers/utilities/manitoba_hydro.py`
- **_mb_section()** (3 connections) — `scrapers/utilities/manitoba_hydro.py`
- **.__init__()** (2 connections) — `scrapers/utilities/manitoba_hydro.py`
- **section()** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **Parse a Manitoba Hydro value line into (kind, value, unit); glyph-agnostic for…** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **Build a RateComponent from a label line and the value line that follows it.** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **Turn the parsed energy block rows into 1..n tiers with cumulative upper bounds…** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **Pair the zero-priced first kVA block with its balance row (both carry the same…** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **First 'Rates effective <date>' line ahead of the electricity tables -> (iso,…** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **Pair label/value lines against an exact spec; any unknown, missing or repeated…** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **Scrape Manitoba Hydro electricity rates.** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **Parse residential rates from the Manitoba Hydro residential page text.** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- *... and 4 more nodes in this community*

## Relationships

- [BaseScraper](BaseScraper.md) (12 shared connections)
- [TariffRecord](TariffRecord.md) (9 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (6 shared connections)
- [re](re.md) (6 shared connections)
- [.fetch_page](fetch_page.md) (2 shared connections)
- [DocumentPage](DocumentPage.md) (2 shared connections)
- [.__init__](__init__.md) (1 shared connections)

## Source Files

- `scrapers/utilities/manitoba_hydro.py`

## Audit Trail

- EXTRACTED: 69 (92%)
- INFERRED: 6 (8%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*