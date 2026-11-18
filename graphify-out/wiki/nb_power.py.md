# nb_power.py

> 26 nodes

## Key Concepts

- **nb_power.py** (28 connections) — `scrapers/utilities/nb_power.py`
- **change_detection.py** (18 connections) — `scrapers/utils/change_detection.py`
- **compare_to_seed()** (14 connections) — `scrapers/utils/change_detection.py`
- **has_critical_alerts()** (11 connections) — `scrapers/utils/change_detection.py`
- **log_change_alerts()** (11 connections) — `scrapers/utils/change_detection.py`
- **extract_tables()** (7 connections) — `scrapers/utils/parsing.py`
- **bs4** (7 connections)
- **ChangeAlert** (6 connections) — `scrapers/utils/change_detection.py`
- **_compare_components()** (6 connections) — `scrapers/utils/change_detection.py`
- **_pair_records()** (5 connections) — `scrapers/utils/change_detection.py`
- **_match_key()** (4 connections) — `scrapers/utils/change_detection.py`
- **_cents_triplet()** (3 connections) — `scrapers/utilities/nb_power.py`
- **_classify_severity()** (3 connections) — `scrapers/utils/change_detection.py`
- **find_table_by_header()** (3 connections) — `scrapers/utils/parsing.py`
- **nb_power.py — Scraper for NB Power electricity rates (New Brunswick). NB Power…** (1 connections) — `scrapers/utilities/nb_power.py`
- **change_detection.py — Compare live-parsed tariff records against seed data.…** (1 connections) — `scrapers/utils/change_detection.py`
- **Compare individual rate components between a live and seed record.** (1 connections) — `scrapers/utils/change_detection.py`
- **Compare live-parsed tariff records against seed/fallback data. Returns a list…** (1 connections) — `scrapers/utils/change_detection.py`
- **Log each ChangeAlert at the appropriate severity level.** (1 connections) — `scrapers/utils/change_detection.py`
- **Check if any alerts are critical (likely parsing errors).** (1 connections) — `scrapers/utils/change_detection.py`
- **A single detected difference between live and seed data.** (1 connections) — `scrapers/utils/change_detection.py`
- **Classify the severity of a change based on % and absolute value.** (1 connections) — `scrapers/utils/change_detection.py`
- **Build a matching key for pairing live records to seed records. Uses tariff_code…** (1 connections) — `scrapers/utils/change_detection.py`
- **Pair live and seed records by matching key. Returns list of (live, seed)…** (1 connections) — `scrapers/utils/change_detection.py`
- **Extract all <table> elements from HTML and return them as a list of tables,…** (1 connections) — `scrapers/utils/parsing.py`
- *... and 1 more nodes in this community*

## Relationships

- [BaseScraper](BaseScraper.md) (23 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (16 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (9 shared connections)
- [.mark_fallback](mark_fallback.md) (6 shared connections)
- [._parse_commercial](_parse_commercial.md) (4 shared connections)
- [re](re.md) (2 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (1 shared connections)
- [EPCOROntarioGasScraper](EPCOROntarioGasScraper.md) (1 shared connections)
- [ntpc.py](ntpc.py.md) (1 shared connections)
- [archive_ontario_price.py](archive_ontario_price.py.md) (1 shared connections)
- [build_alberta_market.py](build_alberta_market.py.md) (1 shared connections)
- [generate_market_pricing.py](generate_market_pricing.py.md) (1 shared connections)

## Source Files

- `scrapers/utilities/nb_power.py`
- `scrapers/utils/change_detection.py`
- `scrapers/utils/parsing.py`

## Audit Trail

- EXTRACTED: 98 (96%)
- INFERRED: 4 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*