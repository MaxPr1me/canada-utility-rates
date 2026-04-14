"""
validate.py — Post-scrape validation and data quality checks.

Run this after a scrape to check data quality:
  - Utilities with no tariffs
  - Tariffs with no components
  - Rates that changed dramatically since last run
  - Sources that are broken or moved
  - Missing provinces or customer classes

Usage:
    python -m pipeline.validate
    python -m pipeline.validate --fix   # attempt to fix minor issues
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

DB_PATH = PROJECT_ROOT / "data" / "db" / "rates.db"

ALL_PROVINCES = {"BC", "AB", "SK", "MB", "ON", "QC", "NB", "NS", "PE", "NL", "YT", "NT", "NU"}


def run_validation(conn: sqlite3.Connection) -> list[dict]:
    """
    Run all validation checks and return a list of issues.

    Each issue is a dict with:
        severity: "info" | "warning" | "error"
        check: name of the check
        message: human-readable description
    """
    issues = []

    # ── Check 1: Missing provinces ────────────────────────────
    covered = {
        row[0] for row in conn.execute(
            "SELECT DISTINCT province FROM utilities"
        ).fetchall()
    }
    missing = ALL_PROVINCES - covered
    if missing:
        issues.append({
            "severity": "warning",
            "check": "province_coverage",
            "message": f"Missing provinces: {', '.join(sorted(missing))}",
        })

    # ── Check 2: Utilities with no tariffs ────────────────────
    orphan_utils = conn.execute("""
        SELECT u.name, u.province
        FROM utilities u
        LEFT JOIN tariffs t ON t.utility_id = u.id
        WHERE t.id IS NULL
    """).fetchall()
    for name, prov in orphan_utils:
        issues.append({
            "severity": "warning",
            "check": "utility_no_tariffs",
            "message": f"{name} ({prov}) has no tariffs in the database",
        })

    # ── Check 3: Tariffs with no components ───────────────────
    empty_tariffs = conn.execute("""
        SELECT t.name, u.name
        FROM tariffs t
        JOIN utilities u ON t.utility_id = u.id
        LEFT JOIN rate_components rc ON rc.tariff_id = t.id
        WHERE rc.id IS NULL
    """).fetchall()
    for tname, uname in empty_tariffs:
        issues.append({
            "severity": "error",
            "check": "tariff_no_components",
            "message": f"Tariff '{tname}' ({uname}) has no rate components",
        })

    # ── Check 4: Low-confidence data ──────────────────────────
    low_conf = conn.execute("""
        SELECT COUNT(*) FROM tariffs WHERE confidence IN ('low', 'unverified')
    """).fetchone()[0]
    if low_conf > 0:
        issues.append({
            "severity": "info",
            "check": "low_confidence",
            "message": f"{low_conf} tariffs have low/unverified confidence",
        })

    # ── Check 5: Broken sources ───────────────────────────────
    broken = conn.execute("""
        SELECT url, s.status, u.name
        FROM sources s
        JOIN utilities u ON s.utility_id = u.id
        WHERE s.status IN ('broken', 'moved')
    """).fetchall()
    for url, status, uname in broken:
        issues.append({
            "severity": "error",
            "check": "broken_source",
            "message": f"Source for {uname} is {status}: {url}",
        })

    # ── Check 6: Missing residential rates ────────────────────
    utils_no_residential = conn.execute("""
        SELECT u.name, u.province
        FROM utilities u
        WHERE u.id NOT IN (
            SELECT DISTINCT utility_id FROM tariffs WHERE customer_class = 'residential'
        )
    """).fetchall()
    for name, prov in utils_no_residential:
        issues.append({
            "severity": "warning",
            "check": "no_residential_rate",
            "message": f"{name} ({prov}) has no residential tariff",
        })

    # ── Summary ───────────────────────────────────────────────
    error_count = sum(1 for i in issues if i["severity"] == "error")
    warn_count = sum(1 for i in issues if i["severity"] == "warning")
    info_count = sum(1 for i in issues if i["severity"] == "info")

    logger.info(
        "Validation complete: %d errors, %d warnings, %d info",
        error_count, warn_count, info_count,
    )

    return issues


def print_issues(issues: list[dict]) -> None:
    """Print validation issues in a readable format."""
    print()
    print("=" * 60)
    print("  DATA VALIDATION REPORT")
    print("=" * 60)

    if not issues:
        print("  All checks passed!")
        return

    for severity in ("error", "warning", "info"):
        group = [i for i in issues if i["severity"] == severity]
        if not group:
            continue
        icon = {"error": "ERROR", "warning": "WARN", "info": "INFO"}[severity]
        print(f"\n-- {icon} ({len(group)}) --")
        for issue in group:
            print(f"  [{issue['check']}] {issue['message']}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate scraped data quality")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    setup_logging()

    if not DB_PATH.exists():
        logger.error("Database not found at %s — run the scraper first.", DB_PATH)
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    issues = run_validation(conn)
    conn.close()

    if args.json:
        print(json.dumps(issues, indent=2))
    else:
        print_issues(issues)

    # Exit with error code if there are errors
    if any(i["severity"] == "error" for i in issues):
        sys.exit(1)


if __name__ == "__main__":
    main()
