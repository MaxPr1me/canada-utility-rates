# registry.py

> 26 nodes

## Key Concepts

- **registry.py** (20 connections) — `scrapers/registry.py`
- **load_registry()** (13 connections) — `scrapers/registry.py`
- **find_utility()** (8 connections) — `scrapers/registry.py`
- **monthly_price_utilities()** (8 connections) — `scrapers/registry.py`
- **get_active_utilities()** (7 connections) — `scrapers/registry.py`
- **suggest_names()** (7 connections) — `scrapers/registry.py`
- **dispatch_input_errors()** (5 connections) — `scrapers/registry.py`
- **main()** (5 connections) — `scrapers/registry.py`
- **normalize_name()** (5 connections) — `scrapers/registry.py`
- **get_utility()** (4 connections) — `scrapers/registry.py`
- **unicodedata** (4 connections)
- **get_utilities_by_province()** (3 connections) — `scrapers/registry.py`
- **difflib** (2 connections)
- **add()** (1 connections) — `scrapers/registry.py`
- **Path** (1 connections)
- **registry.py — Load and query the source registry. The source registry…** (1 connections) — `scrapers/registry.py`
- **Look up a single utility by name, ignoring accents, case and repeated spaces.** (1 connections) — `scrapers/registry.py`
- **Return all utilities in a given province (2-letter code).** (1 connections) — `scrapers/registry.py`
- **Return only utilities whose status is 'active' or 'partial'.** (1 connections) — `scrapers/registry.py`
- **Active utilities flagged ``monthly_price_refresh``: the Monthly Scrape's run on…** (1 connections) — `scrapers/registry.py`
- **Problems with a manual Monthly Scrape's utility and province inputs, found…** (1 connections) — `scrapers/registry.py`
- **``python3 -m scrapers.registry --utility=... --province=...``: the Monthly…** (1 connections) — `scrapers/registry.py`
- **Load the source registry from JSON. Returns a list of utility entries, each…** (1 connections) — `scrapers/registry.py`
- **A utility name compared without accents, case or repeated spaces ("energir"…** (1 connections) — `scrapers/registry.py`
- **The registry entry for a typed name, or ``(None, closest registry names)`` when…** (1 connections) — `scrapers/registry.py`
- *... and 1 more nodes in this community*

## Relationships

- [run_scrape.py](run_scrape.py.md) (12 shared connections)
- [model_monitoring.py](model_monitoring.py.md) (4 shared connections)
- [coverage_gate.py](coverage_gate.py.md) (2 shared connections)
- [re](re.md) (2 shared connections)
- [BaseScraper](BaseScraper.md) (2 shared connections)
- [ntpc.py](ntpc.py.md) (2 shared connections)

## Source Files

- `scrapers/registry.py`

## Audit Trail

- EXTRACTED: 64 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*