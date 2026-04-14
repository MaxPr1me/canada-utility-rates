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
import importlib
import json
import logging
import sqlite3
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path so imports work when run as script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

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

        # Insert tariff
        cursor.execute("""
            INSERT INTO tariffs (
                utility_id, scrape_run_id, name, tariff_code, utility_type,
                customer_class, sub_class, description, eligibility,
                demand_min_kw, demand_max_kw, usage_min, usage_max, usage_unit,
                rate_structure, effective_date, end_date,
                source_url, source_page, confidence, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            utility_id, run_id,
            record.tariff_name, record.tariff_code, record.utility_type,
            record.customer_class, record.sub_class, record.description,
            record.eligibility, record.demand_min_kw, record.demand_max_kw,
            record.usage_min, record.usage_max, record.usage_unit,
            record.rate_structure, record.effective_date, record.end_date,
            record.source_url, record.source_page, record.confidence, record.notes,
        ))
        tariff_id = cursor.lastrowid

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
        tariff_dict = asdict(record)
        tariff_json = json.dumps(tariff_dict, default=str, ensure_ascii=False)
        import hashlib
        snapshot_hash = hashlib.sha256(tariff_json.encode("utf-8")).hexdigest()

        cursor.execute("""
            INSERT INTO historical_snapshots (
                scrape_run_id, tariff_id, snapshot_date, tariff_json, hash
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            run_id, tariff_id,
            datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            tariff_json, snapshot_hash,
        ))

        stored += 1

    conn.commit()
    return stored


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
    attempted = 0
    succeeded = 0

    for entry in entries:
        attempted += 1
        name = entry["name"]
        logger.info("--- Scraping: %s ---", name)

        scraper = load_scraper(entry)
        if scraper is None:
            errors.append(f"{name}: no scraper configured")
            continue

        try:
            records = scraper.scrape()
            valid, invalid = validate_batch(records)

            if invalid:
                errors.append(f"{name}: {len(invalid)} invalid records")

            all_records.extend(valid)
            succeeded += 1

            logger.info(
                "%s: scraped %d tariffs (%d valid, %d invalid)",
                name, len(records), len(valid), len(invalid),
            )

        except Exception as e:
            logger.error("FAILED to scrape %s: %s", name, e, exc_info=True)
            errors.append(f"{name}: {e}")

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
    print()
    print("=" * 60)
    print(f"  Scrape complete: {succeeded}/{attempted} utilities succeeded")
    print(f"  Total tariffs scraped: {len(all_records)}")
    if errors:
        print(f"  Errors: {len(errors)}")
        for err in errors:
            print(f"    - {err}")
    if args.dry_run:
        print("  (dry run — nothing saved to database)")
    print("=" * 60)


if __name__ == "__main__":
    main()
