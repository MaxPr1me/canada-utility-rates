# find_text_near_label

> 11 nodes

## Key Concepts

- **find_text_near_label()** (7 connections) — `scrapers/utils/parsing.py`
- **._parse_residential()** (6 connections) — `scrapers/utilities/nova_scotia_power.py`
- **extract_rate_from_text()** (6 connections) — `scrapers/utils/parsing.py`
- **._extract_basic_charge()** (5 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._extract_energy_rate()** (5 connections) — `scrapers/utilities/nova_scotia_power.py`
- **BeautifulSoup** (3 connections)
- **Parse residential rate values from the standard residential page. Expected HTML…** (1 connections) — `scrapers/utilities/nova_scotia_power.py`
- **Extract the monthly base/fixed charge from the page.** (1 connections) — `scrapers/utilities/nova_scotia_power.py`
- **Extract the per-kWh energy charge from the page.** (1 connections) — `scrapers/utilities/nova_scotia_power.py`
- **Find a label (like "Basic Charge") in the page and return numeric text found…** (1 connections) — `scrapers/utils/parsing.py`
- **Extract a rate value from free-form text. Handles patterns like: "$0.0945/kWh"…** (1 connections) — `scrapers/utils/parsing.py`

## Relationships

- [BaseScraper](BaseScraper.md) (6 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (4 shared connections)
- [re](re.md) (2 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (1 shared connections)

## Source Files

- `scrapers/utilities/nova_scotia_power.py`
- `scrapers/utils/parsing.py`

## Audit Trail

- EXTRACTED: 25 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*