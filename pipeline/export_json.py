"""
export_json.py — Export database contents to JSON for the static site.

The static GitHub Pages site can't query SQLite directly, so we
export the data as JSON files that the JavaScript app loads.

Usage:
    python -m pipeline.export_json

Output:
    site/data/utilities.json    — list of all utilities
    site/data/rates.json        — all tariffs with components
    site/data/summary.json      — high-level stats and metadata
"""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.utils.logging_config import setup_logging
from pipeline.validate import generate_missing_classes_report

logger = logging.getLogger(__name__)

DB_PATH = PROJECT_ROOT / "data" / "db" / "rates.db"
SITE_DATA_DIR = PROJECT_ROOT / "site" / "data"


def export_all() -> None:
    """Export all data from the database to JSON files for the site."""
    setup_logging()

    if not DB_PATH.exists():
        logger.error("Database not found at %s -- run the scraper first.", DB_PATH)
        sys.exit(1)

    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # ── Export utilities.json ─────────────────────────────────
    utilities = [dict(row) for row in conn.execute("""
        SELECT id, name, province, utility_type, website, rate_page_url, regulator, notes
        FROM utilities
        ORDER BY province, name
    """).fetchall()]

    write_json(SITE_DATA_DIR / "utilities.json", utilities)
    logger.info("Exported %d utilities", len(utilities))

    # ── Export rates.json (tariffs + components) ──────────────
    tariffs = []
    for row in conn.execute("""
        SELECT t.*, u.name AS utility_name, u.province
        FROM tariffs t
        JOIN utilities u ON t.utility_id = u.id
        ORDER BY u.province, u.name, t.customer_class, t.name
    """).fetchall():
        tariff = dict(row)
        tariff_id = tariff["id"]

        # Fetch components for this tariff
        components = [dict(c) for c in conn.execute("""
            SELECT * FROM rate_components
            WHERE tariff_id = ?
            ORDER BY component_type, tier_number, tou_period
        """, (tariff_id,)).fetchall()]

        tariff["components"] = components
        tariffs.append(tariff)

    write_json(SITE_DATA_DIR / "rates.json", tariffs)
    logger.info("Exported %d tariffs with components", len(tariffs))

    # ── Export summary.json ───────────────────────────────────
    stats = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_utilities": len(utilities),
        "total_tariffs": len(tariffs),
        "total_components": sum(len(t["components"]) for t in tariffs),
        "provinces_covered": sorted(set(u["province"] for u in utilities)),
        "utility_types": {
            "electricity": sum(1 for u in utilities if u["utility_type"] in ("electricity", "both")),
            "gas": sum(1 for u in utilities if u["utility_type"] in ("gas", "both")),
        },
        "customer_classes": sorted(set(t["customer_class"] for t in tariffs)),
    }

    # Last scrape run info
    last_run = conn.execute("""
        SELECT * FROM scrape_runs ORDER BY id DESC LIMIT 1
    """).fetchone()
    if last_run:
        stats["last_scrape_run"] = dict(last_run)

    # Missing data summary
    missing = [dict(m) for m in conn.execute("""
        SELECT * FROM missing_data WHERE resolved = 0
        ORDER BY severity DESC
    """).fetchall()]
    stats["missing_data_count"] = len(missing)

    write_json(SITE_DATA_DIR / "summary.json", stats)
    logger.info("Exported summary stats")

    # ── Export missing.json ───────────────────────────────────
    write_json(SITE_DATA_DIR / "missing.json", missing)
    logger.info("Exported %d missing data entries", len(missing))

    # ── Export missing_classes_report.json ────────────────────
    classes_report = generate_missing_classes_report(conn)
    write_json(SITE_DATA_DIR / "missing_classes_report.json", classes_report)
    logger.info("Exported missing classes report (%d entries)", len(classes_report))

    conn.close()
    print(f"JSON export complete -> {SITE_DATA_DIR}")


def write_json(path: Path, data: object) -> None:
    """Write data to a JSON file with nice formatting."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


if __name__ == "__main__":
    export_all()
