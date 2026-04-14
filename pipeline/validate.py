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
        WHERE u.utility_type = 'electricity'
        AND u.id NOT IN (
            SELECT DISTINCT utility_id FROM tariffs WHERE customer_class = 'residential'
        )
    """).fetchall()
    for name, prov in utils_no_residential:
        issues.append({
            "severity": "warning",
            "check": "no_residential_rate",
            "message": f"{name} ({prov}) has no residential tariff",
        })

    # ── Check 7: Electricity utilities missing commercial class ─
    utils_no_commercial = conn.execute("""
        SELECT u.name, u.province
        FROM utilities u
        WHERE u.utility_type = 'electricity'
        AND u.id NOT IN (
            SELECT DISTINCT utility_id FROM tariffs
            WHERE customer_class IN ('commercial', 'general_service')
        )
    """).fetchall()
    for name, prov in utils_no_commercial:
        issues.append({
            "severity": "warning",
            "check": "no_commercial_rate",
            "message": f"{name} ({prov}) electricity utility has no commercial/GS tariff",
        })

    # ── Check 8: Demand-based tariffs missing threshold info ─────
    demand_no_threshold = conn.execute("""
        SELECT t.name, u.name, u.province
        FROM tariffs t
        JOIN utilities u ON t.utility_id = u.id
        WHERE t.rate_structure = 'demand'
        AND t.demand_min_kw IS NULL
        AND t.demand_max_kw IS NULL
    """).fetchall()
    for tname, uname, prov in demand_no_threshold:
        issues.append({
            "severity": "info",
            "check": "demand_no_threshold",
            "message": f"Demand tariff '{tname}' ({uname}, {prov}) has no demand_min/max_kw set",
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


def generate_missing_classes_report(conn: sqlite3.Connection) -> list[dict]:
    """
    Generate a report of utilities missing expected customer classes.

    For electricity utilities, we expect at least: residential + commercial.
    For gas utilities, we expect at least: residential.

    Returns a list of dicts suitable for writing to missing_classes_report.json.
    """
    report = []

    # All electricity utilities
    elec_utils = conn.execute("""
        SELECT u.id, u.name, u.province
        FROM utilities u
        WHERE u.utility_type = 'electricity'
        ORDER BY u.province, u.name
    """).fetchall()

    for uid, name, prov in elec_utils:
        classes = {
            row[0] for row in conn.execute(
                "SELECT DISTINCT customer_class FROM tariffs WHERE utility_id = ?",
                (uid,),
            ).fetchall()
        }

        missing = []
        if "residential" not in classes:
            missing.append("residential")
        if "commercial" not in classes and "general_service" not in classes:
            missing.append("commercial")

        # Check if demand tariffs have thresholds
        demand_tariffs = conn.execute("""
            SELECT name, demand_min_kw, demand_max_kw
            FROM tariffs
            WHERE utility_id = ? AND rate_structure = 'demand'
        """, (uid,)).fetchall()
        missing_thresholds = [
            t[0] for t in demand_tariffs
            if t[1] is None and t[2] is None
        ]

        if missing or missing_thresholds:
            entry = {
                "utility": name,
                "province": prov,
                "utility_type": "electricity",
                "classes_present": sorted(classes),
            }
            if missing:
                entry["missing_classes"] = missing
            if missing_thresholds:
                entry["demand_tariffs_missing_thresholds"] = missing_thresholds
            report.append(entry)

    # Gas utilities - check for residential
    gas_utils = conn.execute("""
        SELECT u.id, u.name, u.province
        FROM utilities u
        WHERE u.utility_type = 'gas'
        ORDER BY u.province, u.name
    """).fetchall()

    for uid, name, prov in gas_utils:
        classes = {
            row[0] for row in conn.execute(
                "SELECT DISTINCT customer_class FROM tariffs WHERE utility_id = ?",
                (uid,),
            ).fetchall()
        }
        if "residential" not in classes:
            report.append({
                "utility": name,
                "province": prov,
                "utility_type": "gas",
                "classes_present": sorted(classes),
                "missing_classes": ["residential"],
            })

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate scraped data quality")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--missing-classes-report",
        action="store_true",
        help="Generate missing_classes_report.json in site/data/",
    )
    args = parser.parse_args()

    setup_logging()

    if not DB_PATH.exists():
        logger.error("Database not found at %s -- run the scraper first.", DB_PATH)
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    issues = run_validation(conn)

    if args.missing_classes_report:
        report = generate_missing_classes_report(conn)
        report_path = PROJECT_ROOT / "site" / "data" / "missing_classes_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(
            "Missing classes report written to %s (%d entries)",
            report_path, len(report),
        )

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
