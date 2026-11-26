# find_text_near_label

> 8 nodes

## Key Concepts

- **._parse_residential()** (6 connections) — `scrapers/utilities/nova_scotia_power.py`
- **extract_rate_from_text()** (6 connections) — `scrapers/utils/parsing.py`
- **._extract_basic_charge()** (5 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._extract_energy_rate()** (5 connections) — `scrapers/utilities/nova_scotia_power.py`
- **Parse residential rate values from the standard residential page. Expected HTML…** (1 connections) — `scrapers/utilities/nova_scotia_power.py`
- **Extract the monthly base/fixed charge from the page.** (1 connections) — `scrapers/utilities/nova_scotia_power.py`
- **Extract the per-kWh energy charge from the page.** (1 connections) — `scrapers/utilities/nova_scotia_power.py`
- **Extract a rate value from free-form text. Handles patterns like: "$0.0945/kWh"…** (1 connections) — `scrapers/utils/parsing.py`

## Relationships

- [BaseScraper](BaseScraper.md) (4 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (3 shared connections)
- [RateComponent](RateComponent.md) (1 shared connections)
- [TariffRecord](TariffRecord.md) (1 shared connections)
- [re](re.md) (1 shared connections)

## Source Files

- `scrapers/utilities/nova_scotia_power.py`
- `scrapers/utils/parsing.py`

## Audit Trail

- EXTRACTED: 18 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*