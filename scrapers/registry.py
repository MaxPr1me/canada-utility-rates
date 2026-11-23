"""
registry.py — Load and query the source registry.

The source registry (data/sources/registry.json) is the central config
that tells the scraper framework:
  - Which utilities exist
  - Where their rate data lives (URLs)
  - What format the data is in (HTML, PDF, CSV, etc.)
  - Which scraper class handles each utility

This module loads that registry and provides lookup helpers. It uses the
standard library only: the Monthly Scrape checks a manual run's inputs with
``python3 -m scrapers.registry`` before any dependency is installed, and the
model monitor reads the monthly-price group with a bare Python.
"""

from __future__ import annotations

import argparse
import difflib
import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default path to the registry file
REGISTRY_PATH = Path(__file__).resolve().parent.parent / "data" / "sources" / "registry.json"

# Registry flag for utilities whose default price changes every month and is usually posted after the 1st
# (owner decisions 2026-11-20 and 2026-11-23). The Monthly Scrape runs them again on the 4th
# (``run_scrape --monthly-price-refresh``), and receipts name that run by this group name.
MONTHLY_PRICE_FLAG = "monthly_price_refresh"
PROVINCE_CODE = re.compile(r"[A-Za-z]{2}")


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


def normalize_name(name: str) -> str:
    """A utility name compared without accents, case or repeated spaces ("energir" finds "Énergir").

    Owner decision 2026-11-20: a name typed in the Monthly Scrape form without its accent must still find
    the registry entry (the first Énergir run stopped because only the accented spelling matched).
    """
    decomposed = unicodedata.normalize("NFKD", name)
    return " ".join("".join(char for char in decomposed if not unicodedata.combining(char)).casefold().split())


def find_utility(name: str, registry: list[dict]) -> tuple[Optional[dict], list[str]]:
    """The registry entry for a typed name, or ``(None, closest registry names)`` when there is none.

    Raises ValueError when several registry names normalize alike, so a typed name never picks one of them.
    """
    key = normalize_name(name)
    matches = [entry for entry in registry if normalize_name(entry.get("name", "")) == key]
    if len(matches) > 1:
        raise ValueError("registry names differ only by accents, case or spaces: "
                         + "; ".join(sorted(entry.get("name", "") for entry in matches)))
    if matches:
        return matches[0], []
    return None, suggest_names(name, registry)


def suggest_names(name: str, registry: list[dict], limit: int = 3) -> list[str]:
    """Up to ``limit`` registry names for a name that matched none.

    In order: names containing the typed text; entries whose name and notes contain every typed word, so a
    former or trading name recorded in the notes is found ("Eastward Energy" is registered as Heritage Gas);
    then close spellings. The 0.7 cutoff keeps unrelated names out ("Eastward Energy" is not SaskEnergy).
    """
    key = normalize_name(name)
    words = [word for word in re.findall(r"\w+", key) if len(word) >= 3]
    found: list[str] = []

    def add(registry_name: str) -> None:
        if registry_name not in found and len(found) < limit:
            found.append(registry_name)

    if len(key) >= 3:
        for entry in registry:
            if key in normalize_name(entry.get("name", "")):
                add(entry.get("name", ""))
    if words:
        for entry in registry:
            text = normalize_name(f"{entry.get('name', '')} {entry.get('notes') or ''}")
            if all(re.search(rf"\b{re.escape(word)}\b", text) for word in words):
                add(entry.get("name", ""))
    names = {normalize_name(entry.get("name", "")): entry.get("name", "") for entry in registry}
    for normal in difflib.get_close_matches(key, list(names), n=limit, cutoff=0.7):
        add(names[normal])
    return found


def get_utility(name: str, registry: Optional[list[dict]] = None) -> Optional[dict]:
    """Look up a single utility by name, ignoring accents, case and repeated spaces."""
    if registry is None:
        registry = load_registry()
    return find_utility(name, registry)[0]


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


def monthly_price_utilities(registry: Optional[list[dict]] = None) -> list[dict]:
    """Active utilities flagged ``monthly_price_refresh``: the Monthly Scrape's run on the 4th (decision 2026-11-20).

    A flag that is not a JSON boolean is a registry error (ValueError), never silently read as false.
    """
    if registry is None:
        registry = load_registry()
    for entry in registry:
        if type(entry.get(MONTHLY_PRICE_FLAG, False)) is not bool:
            raise ValueError(f"{entry.get('name')}: '{MONTHLY_PRICE_FLAG}' must be true or false")
    return [entry for entry in get_active_utilities(registry) if entry.get(MONTHLY_PRICE_FLAG) is True]


def dispatch_input_errors(utility: str, province: str, registry: list[dict]) -> list[str]:
    """Problems with a manual Monthly Scrape's utility and province inputs, found before anything is installed.

    Owner decision 2026-11-20: a utility name typed in the province box used to stop the run with only
    "Province must be a two-letter code"; each message now says what to type instead. Any non-empty text
    counts as set, as in the workflow's shell.
    """
    if utility and province:
        return ["Set either utility or province, not both."]
    try:
        if province:
            if not PROVINCE_CODE.fullmatch(province):
                entry = find_utility(province, registry)[0]
                hint = (f'"{entry["name"]}" is a utility: type it in the utility box and leave the province box '
                        "empty." if entry else "To scrape one utility, type its name in the utility box instead.")
                return [f"Province must be a two-letter code such as ON. {hint}"]
            codes = sorted({str(entry.get("province", "")).upper() for entry in get_active_utilities(registry)
                            if entry.get("province")})
            if province.upper() not in codes:
                return [f"No active utility is registered in province {province.upper()}. "
                        f"Valid codes: {', '.join(codes)}."]
        elif utility:
            entry, close = find_utility(utility, registry)
            if entry is None:
                if PROVINCE_CODE.fullmatch(utility):
                    hint = "To scrape a province, type its two-letter code in the province box instead."
                elif close:
                    hint = "Closest registry names: " + "; ".join(close) + "."
                else:
                    hint = "Check the spelling in data/sources/registry.json."
                return [f'Utility "{utility}" is not in the registry. {hint}']
    except ValueError as exc:
        return [f"The registry cannot be searched: {exc}"]
    return []


def main(argv: Optional[list[str]] = None) -> int:
    """``python3 -m scrapers.registry --utility=... --province=...``: the Monthly Scrape's input check."""
    parser = argparse.ArgumentParser(description="Check a manual Monthly Scrape's inputs against the registry.")
    parser.add_argument("--utility", default="", help="the utility box (empty when not set)")
    parser.add_argument("--province", default="", help="the province box (empty when not set)")
    args = parser.parse_args(argv)
    errors = dispatch_input_errors(args.utility, args.province, load_registry())
    for message in errors:
        # A workflow command: a typed %, CR or LF must not end or forge the annotation.
        print("::error title=Inputs::" + message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A"))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
