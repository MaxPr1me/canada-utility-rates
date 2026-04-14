"""
parsing.py — Shared parsing utilities for HTML, PDF, and spreadsheet sources.

These helpers are used by utility-specific scrapers so common logic
(extracting tables from HTML, reading PDF tables, cleaning numeric
strings) lives in one place.
"""

from __future__ import annotations

import io
import re
import logging
from typing import Optional

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ─── HTML helpers ──────────────────────────────────────────────

def parse_html(html: str) -> BeautifulSoup:
    """Parse HTML into a BeautifulSoup tree using the fast lxml parser."""
    return BeautifulSoup(html, "lxml")


def extract_tables(html: str) -> list[list[list[str]]]:
    """
    Extract all <table> elements from HTML and return them as
    a list of tables, where each table is a list of rows, and
    each row is a list of cell text strings.

    Example return:
        [
            [                          # table 0
                ["Header 1", "Header 2"],
                ["Value 1",  "Value 2"],
            ],
            [                          # table 1
                ...
            ],
        ]
    """
    soup = parse_html(html)
    tables = []
    for table_tag in soup.find_all("table"):
        rows = []
        for tr in table_tag.find_all("tr"):
            cells = []
            for cell in tr.find_all(["td", "th"]):
                text = cell.get_text(strip=True)
                cells.append(text)
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables


def find_table_by_header(html: str, header_text: str) -> Optional[list[list[str]]]:
    """
    Find the first table whose first row contains header_text
    (case-insensitive substring match).
    """
    tables = extract_tables(html)
    header_lower = header_text.lower()
    for table in tables:
        if table and any(header_lower in cell.lower() for cell in table[0]):
            return table
    return None


# ─── PDF helpers ───────────────────────────────────────────────

def extract_pdf_tables(pdf_bytes: bytes) -> list[list[list[str]]]:
    """
    Extract tables from a PDF using pdfplumber.

    Returns the same format as extract_tables():
    list of tables, each a list of rows, each a list of cell strings.

    Requires:  pip install pdfplumber
    """
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber not installed — run: pip install pdfplumber")
        return []

    tables = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_tables = page.extract_tables()
            if page_tables:
                for table in page_tables:
                    cleaned = []
                    for row in table:
                        cleaned_row = [cell.strip() if cell else "" for cell in row]
                        cleaned.append(cleaned_row)
                    tables.append(cleaned)
    return tables


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract raw text from all pages of a PDF."""
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber not installed — run: pip install pdfplumber")
        return ""

    text_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


# ─── Spreadsheet helpers ──────────────────────────────────────

def read_xlsx_tables(xlsx_bytes: bytes) -> dict[str, list[list[str]]]:
    """
    Read an Excel file and return a dict of sheet_name -> rows.
    Each row is a list of cell values as strings.

    Requires:  pip install openpyxl
    """
    try:
        import openpyxl
    except ImportError:
        logger.error("openpyxl not installed — run: pip install openpyxl")
        return {}

    workbook = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), read_only=True, data_only=True)
    result = {}
    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        rows = []
        for row in sheet.iter_rows(values_only=True):
            rows.append([str(cell) if cell is not None else "" for cell in row])
        result[sheet_name] = rows
    return result


# ─── Numeric / text cleaning ─────────────────────────────────

def clean_currency(text: str) -> Optional[float]:
    """
    Parse a currency string like "$0.0945", "12.34¢/kWh", "0.0945 $/kWh"
    into a float (always in dollars, not cents).

    Returns None if parsing fails.
    """
    if not text:
        return None

    text = text.strip()

    # Remove common non-numeric decorations
    text = text.replace(",", "")
    text = text.replace(" ", "")

    # Check for cents
    is_cents = "¢" in text or "cents" in text.lower()

    # Extract numeric value
    match = re.search(r"(\d+\.?\d*)", text)
    if not match:
        return None

    value = float(match.group(1))

    # Convert cents to dollars
    if is_cents:
        value = value / 100.0

    return value


def clean_number(text: str) -> Optional[float]:
    """Parse a numeric string, stripping commas and whitespace."""
    if not text:
        return None
    text = text.strip().replace(",", "").replace(" ", "")
    match = re.search(r"-?\d+\.?\d*", text)
    if match:
        return float(match.group(0))
    return None


def normalize_province(text: str) -> str:
    """
    Normalize a province name to its standard 2-letter code.
    Accepts full names, common abbreviations, and 2-letter codes.
    """
    mapping = {
        "british columbia": "BC", "bc": "BC",
        "alberta": "AB", "ab": "AB",
        "saskatchewan": "SK", "sk": "SK",
        "manitoba": "MB", "mb": "MB",
        "ontario": "ON", "on": "ON",
        "quebec": "QC", "québec": "QC", "qc": "QC",
        "new brunswick": "NB", "nb": "NB",
        "nova scotia": "NS", "ns": "NS",
        "prince edward island": "PE", "pei": "PE", "pe": "PE",
        "newfoundland and labrador": "NL", "newfoundland": "NL", "nl": "NL",
        "yukon": "YT", "yt": "YT",
        "northwest territories": "NT", "nwt": "NT", "nt": "NT",
        "nunavut": "NU", "nu": "NU",
    }
    return mapping.get(text.strip().lower(), text.strip().upper())
