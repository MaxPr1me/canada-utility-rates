"""
registry.py — Load and query the source registry.

The source registry (data/sources/registry.json) is the central config
that tells the scraper framework:
  - Which utilities exist
  - Where their rate data lives (URLs)
  - What format the data is in (HTML, PDF, CSV, etc.)
  - Which scraper class handles each utility

This module loads that registry and provides lookup helpers.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default path to the registry file
REGISTRY_PATH = Path(__file__).resolve().parent.parent / "data" / "sources" / "registry.json"


def load_registry(path: Optional[Path] = None) -> list[dict]:
    """
    Load the source registry from JSON.

    Returns a list of utility entries, each with keys like:
        name, province, utility_type, scraper_module, sources, status, …
    """
    registry_file = path or REGISTRY_PATH
    if not registry_file.exists():
        logger.warning("Registry file not found at %s", registry_file)
        return []

    with open(registry_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    utilities = data.get("utilities", [])
    logger.info("Loaded %d utilities from registry", len(utilities))
    return utilities


def get_utility(name: str, registry: Optional[list[dict]] = None) -> Optional[dict]:
    """Look up a single utility by name (case-insensitive)."""
    if registry is None:
        registry = load_registry()
    name_lower = name.lower()
    for entry in registry:
        if entry.get("name", "").lower() == name_lower:
            return entry
    return None


def get_utilities_by_province(province: str, registry: Optional[list[dict]] = None) -> list[dict]:
    """Return all utilities in a given province (2-letter code)."""
    if registry is None:
        registry = load_registry()
    province_upper = province.upper()
    return [u for u in registry if u.get("province", "").upper() == province_upper]


def get_active_utilities(registry: Optional[list[dict]] = None) -> list[dict]:
    """Return only utilities whose status is 'active' or 'partial'."""
    if registry is None:
        registry = load_registry()
    return [u for u in registry if u.get("status") in ("active", "partial")]
