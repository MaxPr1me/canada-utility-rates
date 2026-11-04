"""Guard: no scraper module, registry entry or reference data file cites a source URL known to be dead or permanently
moved (offline).

URLs are collected from
* every module in scrapers/utilities/ and scrapers/utils/: each module-level string (constants and the module
  docstring), including strings nested in module-level dicts, lists, tuples and sets. The imported values are read,
  not the source text, so split string literals ("https://a/" "b/") are checked after Python joins them;
* every string of every entry in data/sources/registry.json (source URLs, descriptions and notes);
* every string value of the REFERENCE_FILES (not the dated audit site/data/source_review_report.json or the exported
  site/data/rates.json).

DENYLIST maps each known-bad URL to what should be cited instead; the comment above each entry gives the check date
and the HTTP status seen. A failure names the module constant, registry utility or JSON path that still cites the URL.
KEPT_DEAD maps dead seed citations kept on purpose (user decision 2026-10-30: no archived copy shows the seed values)
to the reason; each must still be cited by a scraper module and must not also be denied.
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
REFERENCE_FILES = ("data/inventory/utilities.json", "site/data/market_structure_notes.json")

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
        "https://www.hydro.mb.ca/docs/billing/electricity-rate-schedule.pdf (approved Electric Rate Schedule)",
    # 2026-10-30: HTTP 301, then 404.
    "https://www.epcor.com/products-services/power/rates-tariffs/Pages/distribution-tariff.aspx":
        "https://www.epcor.com/ca/en/ab/edmonton/account/rates/special-fees-charges/electricity-tariffs.html",
    # 2026-10-30: HTTP 301 to https://www.directenergy.ca/en/regulated.
    "https://www.directenergyregulatedservices.com/regulated-rates":
        "https://www.directenergy.ca/en/regulated/residential-electricity-rates",
    # Batch 18 inventory refresh (2026-11-04). HTTP 404.
    "https://www.nelson.ca/220/Nelson-Hydro":
        "https://www.nelson.ca/3137/Electric-Nelson-Hydro",
    # 2026-11-04: HTTP 301 to /221/Services-Standards (no rates).
    "https://www.nelson.ca/221/Rates":
        "https://www.nelson.ca/231/Electrical-Rates",
    # 2026-11-04: HTTP 404.
    "https://www.newwestcity.ca/electricity":
        "https://www.newwestcity.ca/services/electrical-utility",
    # 2026-11-04: HTTP 404.
    "https://www.newwestcity.ca/electricity/rates-and-charges":
        "Electrical Utility Bylaw No. 6502 via https://www.newwestcity.ca/city_hall/bylaws/main/131/site_bylaws.php?sw=e",
    # 2026-11-04: HTTP 404.
    "https://www.penticton.ca/our-services/electric-utility":
        "https://www.penticton.ca/city-services/utility-electrical-services",
    # 2026-11-04: HTTP 404.
    "https://www.penticton.ca/our-services/electric-utility/rates":
        "Fees and Charges Bylaw No. 2014-07 via https://www.penticton.ca/city-hall/bylaw-directory",
    # 2026-11-04: HTTP 301 to the District home page.
    "https://www.summerland.ca/city-services/electrical":
        "https://www.summerland.ca/city-services/utilities/electrical",
    # 2026-11-04: HTTP 301 to https://sjenergy.ca/ (domain moved).
    "https://www.sjenergy.com":
        "https://sjenergy.ca",
    # 2026-11-04: HTTP 301 to https://sjenergy.ca/residential/rates/ (rates now at /about/our-rates).
    "https://www.sjenergy.com/residential/rates/":
        "https://sjenergy.ca/about/our-rates",
    # 2026-11-04: HTTP 301 to https://www.nakapower.com/en-ca.html (Northland Utilities is now Naka Power).
    "https://www.northlandutilities.com":
        "https://www.nakapower.com/en-ca.html",
    # 2026-11-04: HTTP 301 to .../rates-tariffs.html, then 404.
    "https://www.northlandutilities.com/about/rates-tariffs":
        "https://www.nakapower.com/en-ca/customer-billing-rates/rates-regulations.html",
}

# Kept dead seed citations (see the docstring); each comment gives the check date, HTTP status and archive result.
KEPT_DEAD: dict[str, str] = {
    # 2026-10-30: HTTP 404; no Wayback Machine capture of any variant.
    "https://www.enmax.com/home/rates-and-billing/understand-your-bill/regulated-rate-option":
        "page removed (checked 2026-10-30); no archived copy shows these values",
    # 2026-10-30: HTTP 301, then 404; no Wayback Machine capture of any variant.
    "https://www.epcor.com/products-services/power/rates-tariffs/Pages/regulated-rate-option.aspx":
        "page removed (checked 2026-10-30); no archived copy shows these values",
    # 2026-10-30: HTTP 301, then 404; no Wayback Machine capture of any variant.
    "https://www.epcor.com/products-services/power/rates-tariffs/Pages/default.aspx":
        "page removed (checked 2026-10-30); no archived copy shows these values",
    # 2026-10-30: HTTP 301 to https://www.directenergy.ca/en/regulated (redirecting since 2024-01); the last captures
    # before that (2023-10, 2023-12) and the 2024-10-01 capture of the target lack the seed values.
    "https://www.directenergyregulatedservices.com/":
        "page removed (checked 2026-10-30); no archived copy shows these values",
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


def _json_citations(document: object, label: str) -> dict[str, set[str]]:
    """Normalised URL -> {"label:path.to[0].value", ...} over every string value of a parsed JSON document."""
    found: dict[str, set[str]] = {}
    stack: list[tuple[object, str]] = [(document, "")]
    while stack:
        node, path = stack.pop()
        if isinstance(node, str):
            for url in URL_PATTERN.findall(node):
                found.setdefault(_normalise(url), set()).add(f"{label}:{path}")
        elif isinstance(node, dict):
            stack.extend((item, f"{path}.{key}" if path else str(key)) for key, item in node.items())
        elif isinstance(node, list):
            stack.extend((item, f"{path}[{index}]") for index, item in enumerate(node))
    return found


def _reference_citations() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for relative in REFERENCE_FILES:
        document = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        for url, where in _json_citations(document, relative).items():
            found.setdefault(url, set()).update(where)
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


def test_json_collector_reads_every_string_value_with_its_path():
    document = {"provinces": {"MB": {"utilities": [{"rate_page": "https://x.example.ca/rates/", "tariff_page": None}],
                                     "notes": "See https://y.example.ca/a and https://y.example.ca/b."}}}
    assert _json_citations(document, "inventory.json") == {
        "https://x.example.ca/rates": {"inventory.json:provinces.MB.utilities[0].rate_page"},
        "https://y.example.ca/a": {"inventory.json:provinces.MB.notes"},
        "https://y.example.ca/b": {"inventory.json:provinces.MB.notes"},
    }


def test_collector_sees_the_real_reference_data_urls():
    citations = _reference_citations()
    assert citations[_normalise(manitoba_hydro.SCHEDULE_URL)] == {
        "data/inventory/utilities.json:provinces.MB.utilities[0].tariff_page"}
    assert citations[aeso.REPORT_URL] == {
        "site/data/market_structure_notes.json:provinces.AB.pricing_components.pool_price.source_url"}
    assert len(citations) > 100


def test_no_scraper_module_cites_a_known_dead_url():
    hits = _denied_hits(_module_citations(_scraper_modules()))
    assert not hits, "\n".join(hits)


def test_no_registry_entry_cites_a_known_dead_url():
    hits = _denied_hits(_registry_citations())
    assert not hits, "\n".join(hits)


def test_no_reference_data_file_cites_a_known_dead_url():
    hits = _denied_hits(_reference_citations())
    assert not hits, "\n".join(hits)


def test_kept_dead_seed_citations_are_still_cited_and_not_denied():
    modules = _module_citations(_scraper_modules())
    stale = sorted(url for url in KEPT_DEAD if _normalise(url) not in modules)
    assert not stale, f"no scraper module cites these any more; move them from KEPT_DEAD to DENYLIST: {stale}"
    assert not {_normalise(url) for url in KEPT_DEAD} & DENIED.keys()


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
