"""Market Pricing UI contract: the Market Pricing section of site/js/app.js and the market view in site/index.html.

Static checks only. They never read site/data/market_pricing_ontario.json, which the market pipeline rewrites; the
page must render legacy files (2020-2024 HOEP bins) and rolling 60-month files (schema 2) and refuse anything else.
"""
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
APP = (SITE / "js" / "app.js").read_text(encoding="utf-8")
HTML = (SITE / "index.html").read_text(encoding="utf-8")
CSS = (SITE / "css" / "style.css").read_text(encoding="utf-8")
SECTION = APP[APP.index("// \u2500\u2500 Market Pricing View"):APP.index("// \u2500\u2500 Helpers")]
VIEW = HTML[HTML.index('<div id="view-market"'):HTML.index("<!-- /view-market -->")]
ROLLING_METHOD = "observed_rolling_60m_hoep_oemp_ga"
CSS_MARKER = "/* Market Pricing: rolling model (batch 14) */"

# Schema-2 fields the page reads (keep in sync with the market JSON contract).
ROLLING_FIELDS = ("schema_version", "window", "start_month", "end_month", "months", "complete_rule", "change_date",
                  "eras", "gap", "reason", "heatmap_basis", "revisions", "monthly", "month", "era",
                  "energy_arithmetic", "ga_class_b", "total_arithmetic", "hourly_surface", "hours_hoep", "hours_oemp",
                  "hours_count", "avg_energy_price", "avg_ga_class_b", "combined", "sources", "generated_at",
                  "as_of", "coverage", "calendar_hours", "unobserved_hours", "hours_per_bin", "hours_oemp_per_bin",
                  "unobserved_hoep_months", "incomplete_months", "ga_adjustments", "source_codes", "energy_source",
                  "ga_source")
SOURCE_CODES = ("hoep_hourly", "hoep_monthly_report", "oemp_monthly_table", "ga_workbook", "ga_monthly_report")


class _Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def _view_tags():
    parser = _Tags()
    parser.feed(VIEW)
    return parser.tags


def _method_pattern():
    assert APP.count("const OBSERVED_MARKET_METHOD") == 1
    match = re.search(r"const OBSERVED_MARKET_METHOD = /(.+)/;", APP)
    assert match, "OBSERVED_MARKET_METHOD regex not found in app.js"
    return re.compile(match.group(1))


def _literals(source):
    return re.findall(r'"(?:[^"\\\n]|\\.)*"|`(?:[^`\\]|\\.)*`', source)


@pytest.mark.parametrize("method", ["observed_legacy_hoep_2020_2024_average", "observed_legacy_hoep_2019_2023_average",
                                    ROLLING_METHOD])
def test_market_site_method_regex_accepts_legacy_and_rolling_files(method):
    assert _method_pattern().search(method)


@pytest.mark.parametrize("method", ["representative_historical_model", "observed_trailing_12_month_average",
                                    "observed_legacy_hoep_2020_2024", "observed_rolling_12m_hoep_oemp_ga",
                                    ROLLING_METHOD + "_v2", "x_" + ROLLING_METHOD, ""])
def test_market_site_method_regex_rejects_other_files(method):
    assert not _method_pattern().search(method)


def test_market_site_rolling_files_are_checked_against_the_contract_before_rendering():
    assert 'ROLLING_MARKET_PREFIX = "observed_rolling_"' in SECTION
    assert 'ONTARIO_PRICE_START = "2025-05-01"' in SECTION
    assert "meta.schema_version !== 2" in SECTION and "meta.change_date !== ONTARIO_PRICE_START" in SECTION
    assert "surface.length !== 576" in SECTION
    assert "bin.hours_count !== bin.hours_hoep + bin.hours_oemp" in SECTION
    unread = [field for field in ROLLING_FIELDS if not re.search(rf"\b{field}\b", SECTION)]
    assert not unread, f"contract fields not read by the market section: {unread}"


def test_market_site_view_has_every_element_the_script_uses():
    tags = _view_tags()
    ids = {attrs["id"]: (tag, attrs) for tag, attrs in tags if attrs.get("id")}
    used = set(re.findall(r'getElementById\("([^"]+)"\)', SECTION))
    assert used and not used - set(ids), sorted(used - set(ids))
    for required in ("market-intro", "market-window", "market-note-scope", "market-notice", "market-content",
                     "market-headline", "market-headline-body", "market-monthly", "market-monthly-canvas",
                     "market-day-type", "market-display", "market-heatmap-basis", "heatmap-container",
                     "market-chart-canvas", "market-table-container", "methodology-container"):
        assert required in ids, required
    assert ids["market-monthly-canvas"][0] == "canvas" and ids["market-chart-canvas"][0] == "canvas"
    assert ids["market-notice"][1].get("role") == "status"
    by_schema = {attrs["id"]: attrs["data-market-schema"] for _, attrs in tags if "data-market-schema" in attrs}
    assert by_schema == {"market-headline": "rolling", "market-monthly": "rolling",
                         "market-heatmap-basis": "rolling", "market-chart": "legacy"}
    options = [attrs.get("value") for tag, attrs in tags if tag == "option"]
    assert options[-3:] == ["avg_energy_price", "avg_ga_class_b", "combined"]


def test_market_site_restores_the_legacy_option_labels_and_renames_them_for_rolling_files():
    assert ('legacy: { avg_energy_price: "HOEP (legacy)", avg_ga_class_b: "Class B GA (actual)", '
            'combined: "Combined" }') in SECTION
    for label in ("HOEP (legacy)", "Class B GA (actual)", "Combined"):
        assert f">{label}</option>" in VIEW
    assert 'avg_energy_price: "Energy (legacy HOEP, then Ontario Price)"' in SECTION


def test_market_site_explains_the_rolling_model_gap_and_limits():
    for text in ("no longer publishes the hourly Ontario Price", "never filled in", "the monthly chart and table still",
                 "May 1, 2025", "April 30, 2025", "Observed hours only", "peak demand factor",
                 "not a tariff, a bill or a forecast", "legacy HOEP hours", "Ontario Price hours", "newest first"):
        assert text in SECTION, text
    view_text = " ".join(re.sub(r"<[^>]+>", " ", VIEW).split())
    for text in ("retired on April 30, 2025", "Since May 1, 2025", "Class A customers pay by their peak demand factor",
                 "not a tariff, a bill or a forecast", "The dark vertical line marks May 2025"):
        assert text in view_text, text


def test_market_site_names_monthly_sources_and_discloses_unused_and_pending_months():
    labels = SECTION[SECTION.index("const MARKET_SOURCE_LABELS"):]
    labels = labels[:labels.index("};")]
    for code in SOURCE_CODES:
        assert re.search(rf'\b{code}: "[^"]+"', labels), code
    assert "marketPricingON.metadata.source_codes" in SECTION, "full source descriptions come from the file"
    assert 'headerRow(["Month", "Era", "Energy", "Class B GA", "Total", "Sources"]' in SECTION
    for text in ("is not used either", "Hourly legacy HOEP not used", "Not complete yet", "Monthly Sources",
                 "have no observed hourly price", "as of "):
        assert text in SECTION, text


def test_market_site_labels_every_hoep_mention_as_legacy_or_retired():
    sentences = [sentence for literal in _literals(SECTION) for sentence in re.split(r"(?<=[.;])\s+", literal)
                 if "HOEP" in sentence or "Hourly Ontario Energy Price" in sentence]
    assert sentences
    unlabelled = [s for s in sentences if "retire" not in s.lower() and "legacy" not in s.lower()]
    assert not unlabelled, unlabelled


def test_market_site_builds_dom_without_html_strings_and_links_only_http_urls():
    assert not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write", SECTION)
    assert "escapeHtml(" not in SECTION, "DOM text nodes need no escaping; escaping them would show entities"
    assert SECTION.count(".href = ") == 1
    assert re.search(r"if \(!/\^https\?:\\/\\//i\.test\(href\)\) return document\.createTextNode", SECTION)


def test_market_site_reuses_one_chart_instance():
    assert SECTION.count("new Chart(") == 2
    assert SECTION.count("marketChart = new Chart(") == 2
    assert SECTION.count("resetMarketChart();") == 2
    assert "marketChart.destroy();" in SECTION


def test_market_site_css_block_is_appended_once():
    assert CSS.count(CSS_MARKER) == 1
    block = CSS.split(CSS_MARKER, 1)[1]
    assert "#view-market .hidden { display: none; }" in block
    assert re.search(r"\.market-basis-note\s*\{", block)
    assert re.search(r"#market-table-container \.market-num\s*\{[^}]*text-align:\s*right", block)
