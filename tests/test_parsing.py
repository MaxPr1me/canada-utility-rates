"""
test_parsing.py — Tests for scrapers/utils/parsing.py

Covers: clean_currency, clean_number, normalize_province,
        extract_tables, find_table_by_header.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from scrapers.utils.parsing import (
    clean_currency,
    clean_number,
    normalize_province,
    extract_tables,
    find_table_by_header,
    find_pdf_links,
    parse_html,
    rate_value_appears,
    verify_tariff_values,
)
from scrapers.base import RateComponent, TariffRecord


# ─── clean_currency ─────────────────────────────────────────────

class TestCleanCurrency:
    def test_dollar_sign_decimal(self):
        assert clean_currency("$0.0945") == pytest.approx(0.0945)

    def test_cents_with_unit(self):
        # 12.34 cents -> 0.1234 dollars
        assert clean_currency("12.34¢/kWh") == pytest.approx(0.1234)

    def test_dollar_with_unit(self):
        assert clean_currency("0.0945 $/kWh") == pytest.approx(0.0945)

    def test_whole_dollar(self):
        assert clean_currency("$28.44") == pytest.approx(28.44)

    def test_empty_string(self):
        assert clean_currency("") is None

    def test_none(self):
        assert clean_currency(None) is None


# ─── clean_number ────────────────────────────────────────────────

class TestCleanNumber:
    def test_comma_separated(self):
        assert clean_number("1,234.56") == pytest.approx(1234.56)

    def test_whitespace(self):
        assert clean_number("  42  ") == pytest.approx(42.0)

    def test_empty_string(self):
        assert clean_number("") is None

    def test_none(self):
        assert clean_number(None) is None


# ─── normalize_province ─────────────────────────────────────────

class TestNormalizeProvince:
    def test_full_name(self):
        assert normalize_province("British Columbia") == "BC"

    def test_lowercase_abbreviation(self):
        assert normalize_province("on") == "ON"

    def test_accented_name(self):
        assert normalize_province("québec") == "QC"

    def test_already_uppercase_code(self):
        assert normalize_province("NB") == "NB"


# ─── extract_tables ─────────────────────────────────────────────

class TestExtractTables:
    SIMPLE_HTML = """
    <html><body>
    <table>
        <tr><th>Rate</th><th>Price</th></tr>
        <tr><td>Step 1</td><td>$0.0950</td></tr>
        <tr><td>Step 2</td><td>$0.1408</td></tr>
    </table>
    </body></html>
    """

    def test_extracts_one_table(self):
        tables = extract_tables(self.SIMPLE_HTML)
        assert len(tables) == 1

    def test_table_has_three_rows(self):
        tables = extract_tables(self.SIMPLE_HTML)
        assert len(tables[0]) == 3  # header + 2 data rows

    def test_header_values(self):
        tables = extract_tables(self.SIMPLE_HTML)
        assert tables[0][0] == ["Rate", "Price"]

    def test_data_values(self):
        tables = extract_tables(self.SIMPLE_HTML)
        assert tables[0][1] == ["Step 1", "$0.0950"]
        assert tables[0][2] == ["Step 2", "$0.1408"]

    def test_no_tables(self):
        tables = extract_tables("<html><body><p>No table here</p></body></html>")
        assert tables == []


# ─── find_table_by_header ────────────────────────────────────────

class TestFindTableByHeader:
    TWO_TABLE_HTML = """
    <html><body>
    <table>
        <tr><th>Name</th><th>Age</th></tr>
        <tr><td>Alice</td><td>30</td></tr>
    </table>
    <table>
        <tr><th>Charge Type</th><th>Rate ($/kWh)</th></tr>
        <tr><td>Energy</td><td>0.0950</td></tr>
    </table>
    </body></html>
    """

    def test_finds_matching_table(self):
        table = find_table_by_header(self.TWO_TABLE_HTML, "Charge Type")
        assert table is not None
        assert table[0] == ["Charge Type", "Rate ($/kWh)"]

    def test_case_insensitive(self):
        table = find_table_by_header(self.TWO_TABLE_HTML, "charge type")
        assert table is not None

    def test_substring_match(self):
        table = find_table_by_header(self.TWO_TABLE_HTML, "Rate")
        assert table is not None
        assert "Rate ($/kWh)" in table[0]

    def test_no_match_returns_none(self):
        table = find_table_by_header(self.TWO_TABLE_HTML, "Nonexistent")
        assert table is None


class TestOfficialSourceVerification:
    def test_pdf_links_resolve_relative_urls_and_query_strings(self):
        soup = parse_html(
            '<a href="/documents/rate-schedule.pdf?v=2026">Schedule of Rates</a>'
        )
        assert find_pdf_links(soup, ["schedule"], "https://utility.example/rates/") == [
            "https://utility.example/documents/rate-schedule.pdf?v=2026"
        ]

    @pytest.mark.parametrize(
        ("text", "value", "unit"),
        [
            ("Energy charge 15.213 cents per kWh", 0.15213, "$/kWh"),
            ("Basic charge $24.05/month", 24.05, "$/month"),
            ("Billing demand $14.940 per kW", 14.94, "$/kW"),
        ],
    )
    def test_recognizes_published_rate_formats(self, text, value, unit):
        assert rate_value_appears(text, value, unit)

    def test_does_not_fuzzily_accept_a_changed_rate(self):
        assert not rate_value_appears("Energy charge 15.500 cents per kWh", 0.15213, "$/kWh")

    def test_flags_the_specific_missing_component(self):
        record = TariffRecord(
            utility_name="Example Utility",
            province="ON",
            utility_type="electricity",
            tariff_name="Residential",
            components=[
                RateComponent("fixed", "Basic Charge", 24.05, "$/month"),
                RateComponent("energy", "Energy Charge", 0.15213, "$/kWh"),
            ],
        )
        assert verify_tariff_values("Basic charge $24.05/month", [record]) == [
            "Residential: Energy Charge"
        ]
