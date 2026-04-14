"""
base.py — Abstract base class for all utility scrapers.

Every utility-specific scraper inherits from BaseScraper and implements
the scrape() method.  The base class provides:

  - HTTP fetching with retries and polite delays
  - Logging
  - Database connection helpers
  - Standard output format (list of TariffRecord objects)

HOW TO ADD A NEW UTILITY SCRAPER
---------------------------------
1. Create a new file in  scrapers/utilities/  (e.g., enmax.py).
2. Import BaseScraper from this module.
3. Create a class that inherits from BaseScraper.
4. Implement the  scrape()  method — it must return a list of TariffRecord.
5. Register the scraper in  data/sources/registry.json.

See  scrapers/utilities/bc_hydro.py  for a complete example.
"""

from __future__ import annotations

import hashlib
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


# ─── Data classes returned by scrapers ────────────────────────────

@dataclass
class RateComponent:
    """One individual charge line within a tariff."""

    component_type: str          # "fixed", "energy", "demand", "delivery", etc.
    component_name: str          # human-readable label
    charge_value: Optional[float] = None
    charge_unit: Optional[str] = None      # "$/kWh", "$/month", "$/GJ", …
    charge_currency: str = "CAD"

    # Tier / TOU / Season
    tier_number: Optional[int] = None
    tier_threshold: Optional[float] = None
    tier_unit: Optional[str] = None
    tou_period: Optional[str] = None       # "on-peak", "off-peak", …
    tou_hours: Optional[str] = None
    season: Optional[str] = None
    season_months: Optional[str] = None

    # Demand
    demand_threshold_kw: Optional[float] = None
    demand_unit: Optional[str] = None

    # Market-indexed
    market_reference: Optional[str] = None
    market_source_url: Optional[str] = None

    sub_component: Optional[str] = None
    effective_date: Optional[str] = None
    end_date: Optional[str] = None
    source_url: Optional[str] = None
    source_detail: Optional[str] = None
    confidence: str = "high"
    notes: Optional[str] = None


@dataclass
class TariffRecord:
    """
    A complete tariff / rate plan scraped from a utility.
    Contains one or more RateComponent entries.
    """

    utility_name: str
    province: str
    utility_type: str            # "electricity" or "gas"
    tariff_name: str
    tariff_code: Optional[str] = None
    customer_class: str = "residential"
    sub_class: Optional[str] = None
    description: Optional[str] = None
    eligibility: Optional[str] = None
    demand_min_kw: Optional[float] = None
    demand_max_kw: Optional[float] = None
    usage_min: Optional[float] = None
    usage_max: Optional[float] = None
    usage_unit: Optional[str] = None
    rate_structure: str = "flat"  # "flat", "tiered", "tou", "demand", "market", "mixed"
    pricing_method: Optional[str] = None  # "regulated", "market_based", etc.
    market_reference: Optional[str] = None  # e.g. "IESO HOEP + Global Adjustment"
    effective_date: Optional[str] = None
    end_date: Optional[str] = None
    source_url: Optional[str] = None
    source_page: Optional[str] = None
    confidence: str = "high"
    notes: Optional[str] = None
    components: list[RateComponent] = field(default_factory=list)


# ─── Base scraper class ──────────────────────────────────────────

class BaseScraper(ABC):
    """
    Abstract base for every utility scraper.

    Subclasses MUST implement:
        scrape() -> list[TariffRecord]

    The base class provides:
        fetch_page(url)  — GET a URL with retries and caching
        fetch_pdf(url)   — download a PDF to a temp file
        content_hash(text) — SHA-256 hash for change detection
    """

    # Identify ourselves politely when scraping
    USER_AGENT = (
        "CanadaUtilityCosts/0.1 "
        "(https://github.com/YOUR_USERNAME/canada-utility-costs; "
        "open data project)"
    )

    def __init__(self, utility_name: str, province: str):
        self.utility_name = utility_name
        self.province = province
        self.logger = logging.getLogger(f"scraper.{utility_name.lower().replace(' ', '_')}")
        self._session = self._build_session()

    # ── HTTP helpers ──────────────────────────────────────────

    def _build_session(self) -> requests.Session:
        """Create a requests Session with retry logic."""
        session = requests.Session()
        session.headers.update({"User-Agent": self.USER_AGENT})

        retries = Retry(
            total=3,
            backoff_factor=1,           # wait 1s, 2s, 4s between retries
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def fetch_page(self, url: str, delay: float = 1.0) -> str:
        """
        GET a URL and return the response text.

        Includes a polite delay between requests so we don't
        hammer utility websites.
        """
        self.logger.info("Fetching %s", url)
        time.sleep(delay)  # be polite
        response = self._session.get(url, timeout=30)
        response.raise_for_status()
        return response.text

    def fetch_bytes(self, url: str, delay: float = 1.0) -> bytes:
        """GET a URL and return raw bytes (for PDFs, spreadsheets)."""
        self.logger.info("Fetching binary %s", url)
        time.sleep(delay)
        response = self._session.get(url, timeout=60)
        response.raise_for_status()
        return response.content

    @staticmethod
    def content_hash(text: str) -> str:
        """SHA-256 hash of text content for change detection."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    # ── Abstract interface ────────────────────────────────────

    @abstractmethod
    def scrape(self) -> list[TariffRecord]:
        """
        Scrape the utility's rate data and return structured records.

        Each subclass implements this with utility-specific logic:
        parsing HTML tables, downloading PDFs, reading spreadsheets, etc.

        Returns:
            A list of TariffRecord objects, each containing one or more
            RateComponent entries representing the full tariff structure.
        """
        ...

    # ── Utilities ─────────────────────────────────────────────

    def now_iso(self) -> str:
        """Current UTC time as ISO-8601 string."""
        return datetime.now(timezone.utc).isoformat()
