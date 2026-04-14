"""
diff_report.py — Compare two scrape runs and report changes.

This tool helps you see what changed between monthly scrape runs:
  - New tariffs that appeared
  - Tariffs that disappeared
  - Rate values that changed
  - New utilities discovered

Usage:
    # Compare the two most recent runs:
    python -m pipeline.diff_report

    # Compare specific runs:
    python -m pipeline.diff_report --run1 5 --run2 6

    # Output as JSON instead of text:
    python -m pipeline.diff_report --json
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


def get_snapshots_for_run(conn: sqlite3.Connection, run_id: int) -> dict[int, dict]:
    """Get all tariff snapshots for a given scrape run, keyed by tariff_id."""
    rows = conn.execute("""
        SELECT tariff_id, tariff_json, hash
        FROM historical_snapshots
        WHERE scrape_run_id = ?
    """, (run_id,)).fetchall()
    return {row[0]: {"json": json.loads(row[1]), "hash": row[2]} for row in rows}


def diff_runs(conn: sqlite3.Connection, run1_id: int, run2_id: int) -> dict:
    """
    Compare two scrape runs and return a diff report.

    Returns a dict with keys:
        - new_tariffs: tariffs in run2 but not run1
        - removed_tariffs: tariffs in run1 but not run2
        - changed_tariffs: tariffs present in both but with different hashes
        - unchanged_count: number of tariffs with identical hashes
    """
    snap1 = get_snapshots_for_run(conn, run1_id)
    snap2 = get_snapshots_for_run(conn, run2_id)

    ids1 = set(snap1.keys())
    ids2 = set(snap2.keys())

    new_ids = ids2 - ids1
    removed_ids = ids1 - ids2
    common_ids = ids1 & ids2

    changed = []
    unchanged = 0
    for tid in common_ids:
        if snap1[tid]["hash"] != snap2[tid]["hash"]:
            changed.append({
                "tariff_id": tid,
                "before": snap1[tid]["json"],
                "after": snap2[tid]["json"],
            })
        else:
            unchanged += 1

    return {
        "run1_id": run1_id,
        "run2_id": run2_id,
        "new_tariffs": [snap2[tid]["json"] for tid in new_ids],
        "removed_tariffs": [snap1[tid]["json"] for tid in removed_ids],
        "changed_tariffs": changed,
        "unchanged_count": unchanged,
        "summary": {
            "new": len(new_ids),
            "removed": len(removed_ids),
            "changed": len(changed),
            "unchanged": unchanged,
        },
    }


def print_diff_report(diff: dict) -> None:
    """Print a human-readable diff report."""
    s = diff["summary"]
    print()
    print("=" * 60)
    print(f"  DIFF REPORT: Run #{diff['run1_id']} → Run #{diff['run2_id']}")
    print("=" * 60)
    print(f"  New tariffs:       {s['new']}")
    print(f"  Removed tariffs:   {s['removed']}")
    print(f"  Changed tariffs:   {s['changed']}")
    print(f"  Unchanged tariffs: {s['unchanged']}")
    print()

    if diff["new_tariffs"]:
        print("── NEW TARIFFS ─────────────────────────────────")
        for t in diff["new_tariffs"]:
            print(f"  + {t.get('utility_name', '?')} / {t.get('tariff_name', '?')}")

    if diff["removed_tariffs"]:
        print("\n── REMOVED TARIFFS ─────────────────────────────")
        for t in diff["removed_tariffs"]:
            print(f"  - {t.get('utility_name', '?')} / {t.get('tariff_name', '?')}")

    if diff["changed_tariffs"]:
        print("\n── CHANGED TARIFFS ─────────────────────────────")
        for c in diff["changed_tariffs"]:
            name = c["after"].get("tariff_name", "?")
            util = c["after"].get("utility_name", "?")
            print(f"  ~ {util} / {name}")
            # Show which components changed
            before_comps = {
                comp.get("component_name"): comp.get("charge_value")
                for comp in c["before"].get("components", [])
            }
            after_comps = {
                comp.get("component_name"): comp.get("charge_value")
                for comp in c["after"].get("components", [])
            }
            for comp_name in set(before_comps) | set(after_comps):
                bv = before_comps.get(comp_name)
                av = after_comps.get(comp_name)
                if bv != av:
                    print(f"      {comp_name}: {bv} → {av}")

    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two scrape runs")
    parser.add_argument("--run1", type=int, help="First run ID (older)")
    parser.add_argument("--run2", type=int, help="Second run ID (newer)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    setup_logging()

    if not DB_PATH.exists():
        logger.error("Database not found at %s", DB_PATH)
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))

    # If runs not specified, use the two most recent
    if args.run1 is None or args.run2 is None:
        runs = conn.execute("""
            SELECT id FROM scrape_runs ORDER BY id DESC LIMIT 2
        """).fetchall()
        if len(runs) < 2:
            print("Need at least 2 scrape runs to compare. Run the scraper again.")
            sys.exit(0)
        run2_id = runs[0][0]
        run1_id = runs[1][0]
    else:
        run1_id = args.run1
        run2_id = args.run2

    diff = diff_runs(conn, run1_id, run2_id)
    conn.close()

    if args.json:
        print(json.dumps(diff, indent=2, default=str))
    else:
        print_diff_report(diff)


if __name__ == "__main__":
    main()
