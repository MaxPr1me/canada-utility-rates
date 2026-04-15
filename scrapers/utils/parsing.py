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


# ─── Live-scraping helpers ───────────────────────────────────

def find_text_near_label(
    soup: BeautifulSoup,
    label_text: str,
    search_radius: int = 3,
) -> Optional[str]:
    """
    Find a label (like "Basic Charge") in the page and return numeric
    text found near it. Searches next siblings, parent's next siblings,
    and adjacent table cells within *search_radius* hops.

    Returns the first string that looks like it contains a number,
    or None if nothing is found.
    """
    label_lower = label_text.lower()

    # Search all text nodes containing the label
    for tag in soup.find_all(string=re.compile(re.escape(label_lower), re.IGNORECASE)):
        element = tag.parent if tag.parent else tag

        # Strategy 1: next siblings of the element
        candidates = []
        sib = element.next_sibling
        for _ in range(search_radius):
            if sib is None:
                break
            text = sib.get_text(strip=True) if hasattr(sib, "get_text") else str(sib).strip()
            if text:
                candidates.append(text)
            sib = sib.next_sibling

        # Strategy 2: if element is inside a <td>/<th>, check the next <td>/<th> in the row
        cell = element.find_parent(["td", "th"])
        if cell:
            for next_cell in cell.find_next_siblings(["td", "th"])[:search_radius]:
                text = next_cell.get_text(strip=True)
                if text:
                    candidates.append(text)

        # Strategy 3: parent's next sibling (common in <dt>/<dd> or <div> layouts)
        parent = element.parent
        if parent:
            psib = parent.next_sibling
            for _ in range(search_radius):
                if psib is None:
                    break
                text = psib.get_text(strip=True) if hasattr(psib, "get_text") else str(psib).strip()
                if text:
                    candidates.append(text)
                psib = psib.next_sibling

        # Return the first candidate that contains a digit
        for cand in candidates:
            if re.search(r"\d", cand):
                return cand

    return None


def extract_rate_from_text(text: str) -> Optional[float]:
    """
    Extract a rate value from free-form text. Handles patterns like:
      "$0.0945/kWh"  "12.34 ¢/kWh"  "$25.00/month"  "0.0945 $/GJ"
      "9.45 cents per kWh"  "$6.89 per kW"

    Always returns the value in dollars (converts cents automatically).
    Returns None if no numeric rate is found.
    """
    if not text:
        return None

    text = text.strip()

    # Detect cents
    is_cents = bool(re.search(r"[¢]|cents?\b", text, re.IGNORECASE))

    # Try to extract a dollar amount like $X.XXXX
    match = re.search(r"\$\s*(\d+\.?\d*)", text)
    if match:
        return float(match.group(1))

    # Try bare number (possibly with cents indicator)
    match = re.search(r"(\d+\.?\d*)\s*(?:[¢]|cents?|/|\$|per\b)", text, re.IGNORECASE)
    if not match:
        # Last resort: any number in the text
        match = re.search(r"(\d+\.?\d*)", text)

    if not match:
        return None

    value = float(match.group(1))
    if is_cents:
        value /= 100.0

    return value


def detect_js_rendered(html: str) -> bool:
    """
    Heuristic check for JS-rendered pages. Returns True if the page
    appears to rely on client-side JavaScript for content rendering.

    Indicators:
      - Very little visible text in <body> relative to page size
      - Many <script> tags
      - References to common SPA frameworks (React, Angular, Vue, Next.js)
      - Presence of div#root, div#app, or div#__next with no content
    """
    soup = parse_html(html)
    body = soup.find("body")
    if not body:
        return False

    body_text = body.get_text(strip=True)
    scripts = body.find_all("script")

    # Very little text but lots of scripts
    if len(body_text) < 200 and len(scripts) > 3:
        return True

    # Low text-to-HTML ratio
    html_len = len(html)
    if html_len > 5000 and len(body_text) < html_len * 0.05:
        return True

    # SPA framework markers
    spa_markers = [
        "__NEXT_DATA__", "__next", "react-root", "_react",
        "ng-app", "ng-version", "Vue.js", "nuxt",
    ]
    html_lower = html.lower()
    if any(marker.lower() in html_lower for marker in spa_markers):
        # Check if body has substantive content despite framework markers
        if len(body_text) < 500:
            return True

    # Empty root containers
    for div_id in ["root", "app", "__next", "main-content"]:
        div = body.find("div", id=div_id)
        if div and len(div.get_text(strip=True)) < 50:
            return True

    return False


def find_pdf_links(
    soup: BeautifulSoup,
    keywords: Optional[list[str]] = None,
) -> list[str]:
    """
    Extract all href values linking to PDF files from a parsed page.

    Args:
        soup: BeautifulSoup object of the parsed page.
        keywords: Optional list of keywords to filter by. If provided,
                  only links where the href or link text contains at
                  least one keyword (case-insensitive) are returned.

    Returns:
        List of PDF URLs (may be relative paths).
    """
    pdf_links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if not href.lower().endswith(".pdf"):
            continue

        if keywords:
            link_text = a_tag.get_text(strip=True).lower()
            href_lower = href.lower()
            if not any(kw.lower() in link_text or kw.lower() in href_lower for kw in keywords):
                continue

        pdf_links.append(href)

    return pdf_links
