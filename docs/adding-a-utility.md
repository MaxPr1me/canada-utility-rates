# How to Add a New Utility Scraper

This guide walks through adding a scraper for a new Canadian utility,
step by step.

## 1. Research the utility

Before writing code, find these things:

- **Official rate page** — where rates are published on the utility's website
- **Rate schedule documents** — PDFs or pages with detailed tariff tables
- **Data format** — is it an HTML page, a PDF, a spreadsheet?
- **Rate structure** — flat? tiered? time-of-use? demand? mixed?
- **Customer classes** — residential, commercial, industrial, etc.
- **All charge components** — fixed fees, energy charges, delivery, transmission, riders, etc.

Write down the URLs you find — you'll need them.

## 2. Create the scraper file

Create a new Python file in `scrapers/utilities/`. Name it after the utility
using underscores and lowercase:

```
scrapers/utilities/my_utility.py
```

## 3. Write the scraper class

Use this template:

```python
"""
my_utility.py — Scraper for [Utility Name] ([Province]).

Official source:
  [URL to rate page]
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)


class MyUtilityScraper(BaseScraper):
    """Scrape [Utility Name] rates."""

    def __init__(self):
        super().__init__(utility_name="[Utility Name]", province="[XX]")

    def scrape(self) -> list[TariffRecord]:
        records = []

        # Try live scraping first, fall back to seed data
        live = self._try_live_scrape()
        if live:
            records.extend(live)
        else:
            self.logger.warning("Live scrape failed — using seed data")
            records.extend(self._seed_data())

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        try:
            html = self.fetch_page("https://example.com/rates")
            # Parse the HTML to extract rate data
            # ...
            return None  # Replace with parsed records
        except Exception as e:
            self.logger.warning("Could not fetch: %s", e)
            return None

    def _seed_data(self) -> list[TariffRecord]:
        """Known rate values as fallback."""
        return [
            TariffRecord(
                utility_name="[Utility Name]",
                province="[XX]",
                utility_type="electricity",  # or "gas"
                tariff_name="[Tariff Name]",
                tariff_code="[Code]",
                customer_class="residential",
                rate_structure="flat",
                effective_date="2024-01-01",
                source_url="https://...",
                confidence="high",
                components=[
                    RateComponent(
                        component_type="fixed",
                        component_name="Monthly Charge",
                        charge_value=10.00,
                        charge_unit="$/month",
                    ),
                    RateComponent(
                        component_type="energy",
                        component_name="Energy Charge",
                        charge_value=0.10,
                        charge_unit="$/kWh",
                    ),
                ],
            ),
        ]
```

## 4. Register the scraper

Add an entry to `data/sources/registry.json`:

```json
{
    "name": "[Utility Name]",
    "province": "[XX]",
    "utility_type": "electricity",
    "scraper_module": "scrapers.utilities.my_utility",
    "scraper_class": "MyUtilityScraper",
    "status": "active",
    "sources": [
        {
            "url": "https://...",
            "source_type": "html",
            "description": "Main rate page",
            "is_primary": true
        }
    ],
    "notes": ""
}
```

## 5. Test it

```bash
# Run just your new scraper
python -m pipeline.run_scrape --utility "[Utility Name]"

# Run in dry-run mode (no database changes)
python -m pipeline.run_scrape --utility "[Utility Name]" --dry-run
```

## 6. Verify the data

After scraping, export and check:

```bash
python -m pipeline.export_json
```

Open `site/data/rates.json` and search for your utility to make sure
the data looks correct.

## Tips

- **Start with seed data** — enter known rates manually, then add live parsing
- **Be specific about components** — don't flatten into one "total" number
- **Include source URLs** — link to the exact page or PDF for each value
- **Set confidence** — use "high" for values you've manually verified
- **Add notes** — explain anything unusual about the rate structure
