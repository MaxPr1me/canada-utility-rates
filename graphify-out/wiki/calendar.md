# calendar

> 24 nodes

## Key Concepts

- **workflow_checks()** (12 connections) — `pipeline/model_monitoring.py`
- **calendar** (12 connections)
- **timestamp()** (11 connections) — `pipeline/model_monitoring.py`
- **datetime** (11 connections)
- **_successful_generation()** (7 connections) — `pipeline/model_monitoring.py`
- **_held_until_monthly_price()** (6 connections) — `pipeline/model_monitoring.py`
- **_monthly_occurrences()** (6 connections) — `pipeline/model_monitoring.py`
- **_report_run()** (6 connections) — `pipeline/model_monitoring.py`
- **next_scheduled()** (5 connections) — `pipeline/model_monitoring.py`
- **scheduled_due()** (5 connections) — `pipeline/model_monitoring.py`
- **date** (5 connections)
- **_monthly_price_check()** (4 connections) — `pipeline/model_monitoring.py`
- **_quarter_end()** (4 connections) — `pipeline/model_monitoring.py`
- **source_checks()** (4 connections) — `pipeline/model_monitoring.py`
- **_evidence()** (3 connections) — `pipeline/model_monitoring.py`
- **Validate producer evidence before either history recording or freshness can…** (1 connections) — `pipeline/model_monitoring.py`
- **Occurrences in one month of the repository's fixed UTC day-of-month schedules,…** (1 connections) — `pipeline/model_monitoring.py`
- **The latest occurrence at or before ``now`` of a fixed UTC day-of-month schedule.** (1 connections) — `pipeline/model_monitoring.py`
- **The first occurrence strictly after ``after`` of a fixed UTC day-of-month…** (1 connections) — `pipeline/model_monitoring.py`
- **The monthly-price schedule's own cadence: met by a successful full or monthly-…** (1 connections) — `pipeline/model_monitoring.py`
- **Reject ambiguous clocks instead of treating a local time as UTC.** (1 connections) — `pipeline/model_monitoring.py`
- **Hold a monthly-price utility's failure seen between the full run and the next…** (1 connections) — `pipeline/model_monitoring.py`
- **Use completed-step evidence, including source provenance; a green badge alone…** (1 connections) — `pipeline/model_monitoring.py`
- **Whether this monitoring job belongs to a successful full Monthly Scrape in a…** (1 connections) — `pipeline/model_monitoring.py`

## Relationships

- [model_monitoring.py](model_monitoring.py.md) (26 shared connections)
- [re](re.md) (3 shared connections)
- [parse_html](parse_html.md) (2 shared connections)
- [BaseScraper](BaseScraper.md) (1 shared connections)
- [build_alberta_market.py](build_alberta_market.py.md) (1 shared connections)
- [build_ontario_market.py](build_ontario_market.py.md) (1 shared connections)
- [generate_market_pricing.py](generate_market_pricing.py.md) (1 shared connections)
- [market_quarterly.py](market_quarterly.py.md) (1 shared connections)

## Source Files

- `pipeline/model_monitoring.py`

## Audit Trail

- EXTRACTED: 73 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*