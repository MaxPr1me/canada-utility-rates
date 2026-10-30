"""Guard: no scraper module or registry entry cites a source URL known to be dead or permanently moved (offline).

URLs are collected from
* every module in scrapers/utilities/ and scrapers/utils/: each module-level string (constants and the module
  docstring), including strings nested in module-level dicts, lists, tuples and sets. The imported values are read,
  not the source text, so split string literals ("https://a/" "b/") are checked after Python joins them;
* every string of every entry in data/sources/registry.json (source URLs, descriptions and notes).

DENYLIST maps each known-bad URL to what should be cited instead; the comment above each entry gives the check date
and the HTTP status seen. A failure names the module constant or registry utility that still cites the URL.
"""
from __future__ import annotations

import importlib
import json
import pkgutil
import re
from collections.abc import Iterable, Iterator
from pathlib import Path
from types import ModuleType

import scrapers.utilities
import scrapers.utils
from scrapers.utilities import aeso, direct_energy_regulated, enmax_energy, epcor_energy_alberta, manitoba_hydro

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / "data" / "sources" / "registry.json").read_text(encoding="utf-8"))
URL_PATTERN = re.compile(r"https?://[^\s\"'<>()\[\]{}]+")

DENYLIST: dict[str, str] = {
    # 2026-10-30: HTTP 404 (AESO retired the page).
    "https://www.aeso.ca/market/market-and-system-reporting/hourly-pool-price-report/":
        "scrapers.utilities.aeso.REPORT_URL (ETS Historical Pool Price report)",
    # 2026-10-30: HTTP 404 (AESO retired the page).
    "https://www.aeso.ca/market/market-and-system-reporting/current-supply-demand-report/":
        "http://ets.aeso.ca/ets_web/ip/Market/Reports/CSDReportServlet (ETS Current Supply and Demand report)",
    # 2026-10-30: HTTP 301 to https://www.hydro.mb.ca/account/rates/residential/.
    "https://www.hydro.mb.ca/accounts_and_services/rates/residential_rates/":
        "https://www.hydro.mb.ca/account/rates/residential/",
    # 2026-10-30: HTTP 301 to https://www.hydro.mb.ca/account/rates/commercial/.
    "https://www.hydro.mb.ca/accounts_and_services/rates/commercial_rates/":
        "https://www.hydro.mb.ca/account/rates/commercial/",
    # 2026-10-30: HTTP 301 to https://www.hydro.mb.ca/account/rates/.
    "https://www.hydro.mb.ca/accounts_and_services/rates/":
        "https://www.hydro.mb.ca/account/rates/",
    # 2026-10-30: HTTP 404 (no redirect).
    "https://www.hydro.mb.ca/accounts_and_services/rates/natural_gas_rates/":
        "https://www.hydro.mb.ca/account/rates/natural-gas/",
    # 2026-10-30: HTTP 404.
    "https://www.hydro.mb.ca/accounts-and-billing/rates/":
        "https://www.hydro.mb.ca/account/rates/",
    # 2026-10-30: HTTP 404.
    "https://www.hydro.mb.ca/regulatory-affairs/electric-rates-and-general-conditions/":
        "no verified replacement: find the current page before citing it",
}


def _normalise(url: str) -> str:
    """Compare URLs without trailing sentence punctuation or a trailing slash."""
    return url.rstrip(".,;:").rstrip("/")


DENIED = {_normalise(url): url for url in DENYLIST}


def _strings(value: object, depth: int = 0) -> Iterator[str]:
    """Strings in a value, descending into plain containers (depth-limited, so self-references cannot loop)."""
    if isinstance(value, str):
        yield value
    elif depth < 6 and isinstance(value, dict):
        for item in value.values():
            yield from _strings(item, depth + 1)
    elif depth < 6 and isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            yield from _strings(item, depth + 1)


def _scraper_modules() -> list[ModuleType]:
    return [importlib.import_module(f"{package.__name__}.{info.name}")
            for package in (scrapers.utilities, scrapers.utils)
            for info in pkgutil.iter_modules(package.__path__)]


def _module_citations(modules: Iterable[ModuleType]) -> dict[str, set[str]]:
    """Normalised URL -> {"module.NAME", ...} over every module-level string (dunder names other than __doc__ skipped)."""
    found: dict[str, set[str]] = {}
    for module in modules:
        for name, value in vars(module).items():
            if name.startswith("__") and name != "__doc__":
                continue
            for text in _strings(value):
                for url in URL_PATTERN.findall(text):
                    found.setdefault(_normalise(url), set()).add(f"{module.__name__}.{name}")
    return found


def _registry_citations() -> dict[str, set[str]]:
    """Normalised URL -> {registry utility name, ...} over every string of every registry entry."""
    found: dict[str, set[str]] = {}
    for entry in REGISTRY["utilities"]:
        for text in _strings(entry):
            for url in URL_PATTERN.findall(text):
                found.setdefault(_normalise(url), set()).add(entry["name"])
    return found


def _denied_hits(citations: dict[str, set[str]]) -> list[str]:
    return [f"{DENIED[url]} is still cited by {', '.join(sorted(where))}; cite {DENYLIST[DENIED[url]]} instead"
            for url, where in sorted(citations.items()) if url in DENIED]


def test_collector_joins_split_literals_and_reads_nested_values_and_docstrings():
    module = ModuleType("synthetic_scraper", "Rates from https://docs.example.ca/rates/.")
    exec('SPLIT = ("https://a.example.ca/market/" "report/")\n'
         'AREAS = {"edmonton": {"home_url": "https://b.example.ca/home/"}}\n'
         'EDITIONS = {"DAS": (("January 2026", "https://c.example.ca/das.pdf"),)}\n', module.__dict__)
    assert _module_citations([module]) == {
        "https://docs.example.ca/rates": {"synthetic_scraper.__doc__"},
        "https://a.example.ca/market/report": {"synthetic_scraper.SPLIT"},
        "https://b.example.ca/home": {"synthetic_scraper.AREAS"},
        "https://c.example.ca/das.pdf": {"synthetic_scraper.EDITIONS"},
    }


def test_collector_sees_the_real_scraper_and_registry_urls():
    modules, registry = _module_citations(_scraper_modules()), _registry_citations()
    for url in (aeso.REPORT_URL, manitoba_hydro.RESIDENTIAL_URL, manitoba_hydro.COMMERCIAL_URL,
                manitoba_hydro.SCHEDULE_URL):
        assert _normalise(url) in modules and _normalise(url) in registry
    assert len(modules) > 100 and len(registry) > 100


def test_no_scraper_module_cites_a_known_dead_url():
    hits = _denied_hits(_module_citations(_scraper_modules()))
    assert not hits, "\n".join(hits)


def test_no_registry_entry_cites_a_known_dead_url():
    hits = _denied_hits(_registry_citations())
    assert not hits, "\n".join(hits)


def test_alberta_rolr_seed_pool_price_citations_reuse_the_ets_report_url():
    rolr_scrapers = (direct_energy_regulated.DirectEnergyRegulatedScraper(), enmax_energy.ENMAXEnergyScraper(),
                     epcor_energy_alberta.EPCOREnergyAlbertaScraper())
    for module in (direct_energy_regulated, enmax_energy, epcor_energy_alberta):
        assert module.AESO_MARKET_URL == aeso.REPORT_URL
    market = [c for s in rolr_scrapers for r in s._seed_data() for c in r.components if c.market_reference]
    assert market and all(c.market_source_url == aeso.REPORT_URL for c in market)


def test_manitoba_hydro_registry_sources_match_the_scraper_constants():
    (entry,) = [u for u in REGISTRY["utilities"] if u["name"] == "Manitoba Hydro"]
    assert [s["url"] for s in entry["sources"]] == [
        manitoba_hydro.RESIDENTIAL_URL, manitoba_hydro.COMMERCIAL_URL, manitoba_hydro.SCHEDULE_URL]
