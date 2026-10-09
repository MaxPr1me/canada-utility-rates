"""
run_scrape.py — Main entry point for running utility scrapers.

Usage:
    # Initialize the database (first time only):
    python -m pipeline.run_scrape --init-db

    # Scrape all active utilities:
    python -m pipeline.run_scrape

    # Scrape one utility by name:
    python -m pipeline.run_scrape --utility "BC Hydro"

    # Scrape all utilities in a province:
    python -m pipeline.run_scrape --province BC

    # Dry run (scrape but don't save to database):
    python -m pipeline.run_scrape --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import logging
import os
import sqlite3
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path so imports work when run as script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.export_json import derive_provenance
from scrapers.base import BaseScraper, TariffRecord
from scrapers.registry import load_registry, get_active_utilities
from scrapers.utils.logging_config import setup_logging
from scrapers.utils.validation import validate_batch

logger = logging.getLogger(__name__)

DB_PATH = PROJECT_ROOT / "data" / "db" / "rates.db"
SCHEMA_PATH = PROJECT_ROOT / "schema" / "create_tables.sql"


# ─── Database initialization ─────────────────────────────────

def init_db() -> None:
    """Create the database and all tables from the SQL schema."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(schema_sql)
    conn.close()
    logger.info("Database initialized at %s", DB_PATH)


# ─── Scraper loader ──────────────────────────────────────────

def load_scraper(registry_entry: dict) -> BaseScraper | None:
    """
    Dynamically load a scraper class from a registry entry.

    The registry entry must have a 'scraper_module' key like
    "scrapers.utilities.bc_hydro" and a 'scraper_class' key like
    "BCHydroScraper".

    If the scraper constructor accepts a registry_entry keyword argument,
    the full registry entry dict is passed in.  This lets data-driven
    scrapers (e.g. the Ontario LDC scraper) know which utility they
    should produce data for.
    """
    module_name = registry_entry.get("scraper_module")
    class_name = registry_entry.get("scraper_class")

    if not module_name or not class_name:
        logger.warning(
            "No scraper configured for %s -- skipping",
            registry_entry.get("name", "?"),
        )
        return None

    try:
        module = importlib.import_module(module_name)
        scraper_cls = getattr(module, class_name)
        # Try passing registry_entry so data-driven scrapers can read it.
        # Fall back to a bare call for scrapers that don't accept it.
        try:
            return scraper_cls(registry_entry=registry_entry)
        except TypeError:
            return scraper_cls()
    except (ImportError, AttributeError) as e:
        logger.error(
            "Could not load scraper %s.%s: %s",
            module_name, class_name, e,
        )
        return None


# ─── Database storage ─────────────────────────────────────────

def canonical_snapshot(record: TariffRecord) -> tuple[str, str]:
    """Serialize a semantic tariff deterministically for historical hashing.

    Component ordering is not meaningful, but every component field (including
    units, tiers, dates, source and structure metadata) is. Sorting canonical
    component dictionaries removes false changes without hiding real ones.
    """
    tariff = asdict(record)
    components = tariff.pop("components")
    tariff["components"] = sorted(
        components,
        key=lambda component: json.dumps(component, sort_keys=True, ensure_ascii=False, separators=(",", ":")),
    )
    payload = json.dumps(tariff, sort_keys=True, default=str, ensure_ascii=False, separators=(",", ":"))
    return payload, hashlib.sha256(payload.encode("utf-8")).hexdigest()


def store_results(records: list[TariffRecord], run_id: int, conn: sqlite3.Connection) -> int:
    """
    Store scraped tariff records into the database.
    Returns the number of records stored.
    """
    stored = 0
    cursor = conn.cursor()

    for record in records:
        # Upsert utility
        cursor.execute("""
            INSERT INTO utilities (name, province, utility_type)
            VALUES (?, ?, ?)
            ON CONFLICT(name, province) DO UPDATE SET
                utility_type = excluded.utility_type,
                updated_at = datetime('now')
        """, (record.utility_name, record.province, record.utility_type))

        utility_id = cursor.execute(
            "SELECT id FROM utilities WHERE name = ? AND province = ?",
            (record.utility_name, record.province),
        ).fetchone()[0]

        # Upsert tariff
        cursor.execute("""
            INSERT INTO tariffs (
                utility_id, scrape_run_id, name, tariff_code, utility_type,
                customer_class, sub_class, description, eligibility,
                demand_min_kw, demand_max_kw, usage_min, usage_max, usage_unit,
                rate_structure, effective_date, end_date,
                source_url, source_page, confidence, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(utility_id, name, effective_date) DO UPDATE SET
                scrape_run_id = excluded.scrape_run_id,
                tariff_code = excluded.tariff_code,
                utility_type = excluded.utility_type,
                customer_class = excluded.customer_class,
                sub_class = excluded.sub_class,
                description = excluded.description,
                eligibility = excluded.eligibility,
                demand_min_kw = excluded.demand_min_kw,
                demand_max_kw = excluded.demand_max_kw,
                usage_min = excluded.usage_min,
                usage_max = excluded.usage_max,
                usage_unit = excluded.usage_unit,
                rate_structure = excluded.rate_structure,
                end_date = excluded.end_date,
                source_url = excluded.source_url,
                source_page = excluded.source_page,
                confidence = excluded.confidence,
                notes = excluded.notes
        """, (
            utility_id, run_id,
            record.tariff_name, record.tariff_code, record.utility_type,
            record.customer_class, record.sub_class, record.description,
            record.eligibility, record.demand_min_kw, record.demand_max_kw,
            record.usage_min, record.usage_max, record.usage_unit,
            record.rate_structure, record.effective_date, record.end_date,
            record.source_url, record.source_page, record.confidence, record.notes,
        ))

        # Resolve tariff_id by the (utility_id, name, effective_date) identity
        # — the same key the UNIQUE constraint uses — so codeless classes that
        # share a NULL tariff_code don't collide and overwrite each other's
        # components. Use IS for the nullable effective_date.
        tariff_id = cursor.execute(
            "SELECT id FROM tariffs "
            "WHERE utility_id = ? AND name IS ? AND effective_date IS ? "
            "ORDER BY id DESC LIMIT 1",
            (utility_id, record.tariff_name, record.effective_date),
        ).fetchone()[0]

        # Remove old components before re-inserting fresh data
        cursor.execute("DELETE FROM rate_components WHERE tariff_id = ?", (tariff_id,))

        # Insert components
        for comp in record.components:
            cursor.execute("""
                INSERT INTO rate_components (
                    tariff_id, scrape_run_id,
                    component_type, component_name, sub_component,
                    charge_value, charge_unit, charge_currency,
                    tier_number, tier_threshold, tier_unit,
                    tou_period, tou_hours, season, season_months,
                    demand_threshold_kw, demand_unit,
                    market_reference, market_source_url,
                    effective_date, end_date,
                    source_url, source_detail, confidence, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tariff_id, run_id,
                comp.component_type, comp.component_name, comp.sub_component,
                comp.charge_value, comp.charge_unit, comp.charge_currency,
                comp.tier_number, comp.tier_threshold, comp.tier_unit,
                comp.tou_period, comp.tou_hours, comp.season, comp.season_months,
                comp.demand_threshold_kw, comp.demand_unit,
                comp.market_reference, comp.market_source_url,
                comp.effective_date, comp.end_date,
                comp.source_url, comp.source_detail, comp.confidence, comp.notes,
            ))

        # Store historical snapshot
        tariff_json, snapshot_hash = canonical_snapshot(record)

        cursor.execute("""
            INSERT INTO historical_snapshots (
                scrape_run_id, tariff_id, snapshot_date, tariff_json, hash
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            run_id, tariff_id,
            datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            tariff_json, snapshot_hash,
        ))

        # Upsert customer_classes metadata
        cursor.execute("""
            INSERT INTO customer_classes (
                utility_id, class_name, sub_class_name,
                eligibility_rule, threshold_kw_min, threshold_kw_max,
                source_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(utility_id, class_name, sub_class_name)
            DO UPDATE SET
                eligibility_rule = COALESCE(excluded.eligibility_rule, customer_classes.eligibility_rule),
                threshold_kw_min = COALESCE(excluded.threshold_kw_min, customer_classes.threshold_kw_min),
                threshold_kw_max = COALESCE(excluded.threshold_kw_max, customer_classes.threshold_kw_max),
                source_url = COALESCE(excluded.source_url, customer_classes.source_url)
        """, (
            utility_id,
            record.customer_class,
            record.sub_class,
            record.eligibility,
            record.demand_min_kw,
            record.demand_max_kw,
            record.source_url,
        ))

        stored += 1

    conn.commit()
    return stored


# ─── Run provenance summary ──────────────────────────────────

# Ranked problems first; the summary table is sorted in this order.
SUMMARY_STATUS_ORDER = ("failed", "no valid records", "seed only", "live + seed", "live")


def tally_provenance(records: list[TariffRecord]) -> dict[str, int]:
    """Count records the way the site labels them: ``live`` or ``seed`` (estimated)."""
    counts = {"live": 0, "seed": 0}
    for record in records:
        counts[derive_provenance(record.confidence, record.notes)] += 1
    return counts


def summarize_run(per_utility: dict[str, dict]) -> dict:
    """Aggregate per-utility tallies into totals, problem lists and problems-first rows.

    Each value holds ``live``/``seed`` counts of valid records, an ``invalid``
    count and ``error``, which is set only when the utility failed (no scraper
    configured or an exception).
    """
    rows = []
    for name, tally in per_utility.items():
        live, seed = tally.get("live", 0), tally.get("seed", 0)
        error = tally.get("error")
        if error is not None:
            status = "failed"
        elif live + seed == 0:
            status = "no valid records"
        elif live == 0:
            status = "seed only"
        else:
            status = "live + seed" if seed else "live"
        rows.append({"utility": name, "live": live, "seed": seed,
                     "invalid": tally.get("invalid", 0), "status": status, "error": error})
    rows.sort(key=lambda row: (
        SUMMARY_STATUS_ORDER.index(row["status"]), not row["invalid"], row["utility"].lower(),
    ))

    def names_with(status: str) -> list[str]:
        return sorted((row["utility"] for row in rows if row["status"] == status), key=str.lower)

    return {
        "utilities": len(rows),
        "live": sum(row["live"] for row in rows),
        "seed": sum(row["seed"] for row in rows),
        "invalid": sum(row["invalid"] for row in rows),
        "failed": names_with("failed"),
        "no_records": names_with("no valid records"),
        "seed_only": names_with("seed only"),
        "rows": rows,
    }


def format_summary_markdown(summary: dict, dry_run: bool = False) -> str:
    """Render a run summary as a short Markdown section with problem utilities first."""
    def cell(text: str) -> str:
        return " ".join(text.split()).replace("|", "\\|")

    lines = ["## Scrape provenance summary", ""]
    if dry_run:
        lines += ["_Dry run: nothing saved to the database._", ""]
    lines += [
        f"- Live records: {summary['live']}; seed (estimated) records: {summary['seed']}; "
        f"invalid records: {summary['invalid']}",
        f"- Utilities: {summary['utilities']}; failed: {len(summary['failed'])}; "
        f"no valid records: {len(summary['no_records'])}; seed only: {len(summary['seed_only'])}",
        "",
        "| Utility | Live | Seed | Invalid | Status |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in summary["rows"]:
        status = row["status"]
        if row["error"]:
            reason = " ".join(row["error"].split())
            status += ": " + (reason if len(reason) <= 120 else reason[:117] + "...")
        lines.append(f"| {cell(row['utility'])} | {row['live']} | {row['seed']} | {row['invalid']} | {cell(status)} |")
    return "\n".join(lines) + "\n"


def append_step_summary(markdown: str) -> None:
    """Append Markdown to the GitHub Actions job summary; a write failure only logs a warning."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8", errors="replace") as handle:
            handle.write(markdown)
    except (OSError, ValueError) as exc:
        logger.warning("Could not append the run summary to GITHUB_STEP_SUMMARY (%s): %s", path, exc)


# ─── Main ─────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run utility rate scrapers for Canada",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--init-db", action="store_true", help="Initialize the database (first time)")
    parser.add_argument("--utility", type=str, help="Scrape a single utility by name")
    parser.add_argument("--province", type=str, help="Scrape all utilities in a province")
    parser.add_argument("--dry-run", action="store_true", help="Scrape but don't save to database")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    setup_logging(level=logging.DEBUG if args.verbose else logging.INFO)

    if args.init_db:
        init_db()
        if not args.utility and not args.province:
            return

    # Ensure DB exists
    if not DB_PATH.exists() and not args.dry_run:
        logger.info("Database not found — initializing…")
        init_db()

    # Load registry
    registry = load_registry()
    if not registry:
        logger.error("No utilities found in registry. Add entries to data/sources/registry.json")
        sys.exit(1)

    # Filter utilities
    if args.utility:
        entries = [e for e in registry if e["name"].lower() == args.utility.lower()]
        if not entries:
            logger.error("Utility %r not found in registry", args.utility)
            sys.exit(1)
    elif args.province:
        entries = [e for e in registry if e.get("province", "").upper() == args.province.upper()]
        if not entries:
            logger.error("No utilities found for province %r", args.province)
            sys.exit(1)
    else:
        entries = get_active_utilities(registry)

    logger.info("Will scrape %d utilities", len(entries))

    # Open database connection
    conn = None
    run_id = None
    if not args.dry_run:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scrape_runs (started_at, status)
            VALUES (?, 'running')
        """, (datetime.now(timezone.utc).isoformat(),))
        run_id = cursor.lastrowid
        conn.commit()

    # Run scrapers
    all_records: list[TariffRecord] = []
    errors: list[str] = []
    per_utility: dict[str, dict] = {}
    attempted = 0
    succeeded = 0

    for entry in entries:
        attempted += 1
        name = entry["name"]
        logger.info("--- Scraping: %s ---", name)

        scraper = load_scraper(entry)
        if scraper is None:
            errors.append(f"{name}: no scraper configured")
            per_utility[name] = {"error": "no scraper configured"}
            continue

        try:
            records = scraper.scrape()
            valid, invalid = validate_batch(records)
            counts = tally_provenance(valid)

            if invalid:
                errors.append(f"{name}: {len(invalid)} invalid records")

            all_records.extend(valid)
            succeeded += 1

            logger.info(
                "%s: scraped %d tariffs (%d valid, %d invalid)",
                name, len(records), len(valid), len(invalid),
            )
            per_utility[name] = {**counts, "invalid": len(invalid), "error": None}
            logger.log(
                logging.INFO if counts["live"] else logging.WARNING,
                "%s: %d live, %d seed, %d invalid",
                name, counts["live"], counts["seed"], len(invalid),
            )

        except Exception as e:
            logger.error("FAILED to scrape %s: %s", name, e, exc_info=True)
            errors.append(f"{name}: {e}")
            per_utility[name] = {"error": str(e) or type(e).__name__}

    # Store results
    if conn and run_id and all_records:
        stored = store_results(all_records, run_id, conn)
        logger.info("Stored %d tariff records in database", stored)

    # Update scrape run status
    if conn and run_id:
        conn.execute("""
            UPDATE scrape_runs SET
                finished_at = ?,
                status = ?,
                utilities_attempted = ?,
                utilities_succeeded = ?,
                errors = ?
            WHERE id = ?
        """, (
            datetime.now(timezone.utc).isoformat(),
            "completed" if not errors else "completed_with_errors",
            attempted, succeeded,
            json.dumps(errors) if errors else None,
            run_id,
        ))
        conn.commit()
        conn.close()

    # Summary
    summary = summarize_run(per_utility)
    print()
    print("=" * 60)
    print(f"  Scrape complete: {succeeded}/{attempted} utilities succeeded")
    print(f"  Total tariffs scraped: {len(all_records)}")
    print(f"  Live records: {summary['live']} | Seed (estimated) records: {summary['seed']}")
    if summary["seed_only"]:
        print(f"  Seed-only utilities ({len(summary['seed_only'])}): {', '.join(summary['seed_only'])}")
    if summary["no_records"]:
        print(f"  Utilities with no valid records ({len(summary['no_records'])}): "
              f"{', '.join(summary['no_records'])}")
    if errors:
        print(f"  Errors: {len(errors)}")
        for err in errors:
            print(f"    - {err}")
    if args.dry_run:
        print("  (dry run — nothing saved to database)")
    print("=" * 60)

    append_step_summary(format_summary_markdown(summary, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
