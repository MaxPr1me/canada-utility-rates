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
    site/data/rate_history_revisions.json — same-date price corrections from the database snapshots (Rate History tab)
    site/data/representative_models.json — Phase 7 representative models (provinces and territories; Representative Models tab)
    site/data/spark_gap.json — spark gap comparison, electricity vs the usual heating fuel (Across-Canada, Spark gap)
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import math
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.utils.logging_config import setup_logging
from pipeline.validate import generate_missing_classes_report

logger = logging.getLogger(__name__)

DB_PATH = PROJECT_ROOT / "data" / "db" / "rates.db"
SITE_DATA_DIR = PROJECT_ROOT / "site" / "data"
MODEL_PROVINCES = ("ON", "AB", "BC", "MB", "NB", "NL", "NS", "PE", "QC", "SK", "YT", "NT", "NU")

REVISIONS_RULE = (
    "A same-date correction is a price line whose value changed (beyond floating-point rounding) between live "
    "(officially verified or live-parsed) database snapshots while its tariff version and the line itself (type, "
    "name, unit, tier, time-of-use period, season, sub-component and effective date) stayed the same; estimates are "
    "never used. The site shows the latest value with 'revised on <date>' (owner decision 55, 2026-11-23)."
)
# A price line is these fields plus its own effective date (else its tariff's), so a new effective date
# starts a new line: a real price change, never a correction.
REVISION_LINE_FIELDS = ("component_type", "component_name", "charge_unit", "tier_number", "tou_period", "season",
                        "sub_component")
REVISION_SORT_FIELDS = ("province", "utility_name", "tariff_name", "tariff_effective_date", *REVISION_LINE_FIELDS,
                        "effective_date")


def derive_provenance(confidence: str | None, notes: str | None) -> str:
    """Classify a tariff as live-sourced or seed from its provenance marker.

    Conservative on purpose: only records that were verified against, or parsed
    from, a live official source this run count as ``live``. Everything else
    (including legacy seed constants) is ``seed`` so the site never presents a
    static default value as if it were a current, live-sourced rate.
    """
    text = notes or ""
    if "Provenance: officially_verified" in text or "Provenance: live_parsed" in text:
        return "live"
    return "seed"


def export_all(generation_receipt_path: Path | None = None) -> None:
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
        tariff["provenance"] = derive_provenance(tariff.get("confidence"), tariff.get("notes"))

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

    revisions = export_rate_history_revisions(conn, SITE_DATA_DIR / "rate_history_revisions.json")

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
        "live_tariffs": sum(1 for t in tariffs if t.get("provenance") == "live"),
        "seed_tariffs": sum(1 for t in tariffs if t.get("provenance") != "live"),
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
    result = export_representative_models(tariffs, SITE_DATA_DIR / "representative_models.json",
                                         generation_receipt_path=generation_receipt_path)
    spark_gap = export_spark_gap(tariffs, SITE_DATA_DIR / "spark_gap.json")
    print(f"JSON export complete -> {SITE_DATA_DIR}")
    if revisions is None:
        print("Rate history revisions export FAILED; the previous revisions file was retained.")
    if result is None:
        print("Representative model refresh FAILED; the previous model file was retained.")
    if spark_gap is None:
        print("Spark gap refresh FAILED; the previous spark gap file was retained.")


def _number_or_none(value: object) -> bool:
    """A value the revisions file can carry: a finite number, or None for a value-less ("Variable") line."""
    if value is None:
        return True
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _same_value(earlier: object, later: object) -> bool:
    """Equal stored values, ignoring floating-point noise such as 0.10859999999999999 for 0.1086.

    Every same-date difference in the database in November 2026 (11 lines of BC Hydro, Manitoba Hydro, NB Power
    and SaskPower) was such noise, about 1e-16 relative, left before a parser rounded the same published price.
    It is not a correction, so it must not earn a "revised on" note.
    """
    if earlier is None or later is None:
        return earlier is later
    return math.isclose(earlier, later, rel_tol=1e-9, abs_tol=1e-12)


def _none_first(value: object) -> tuple:
    """Sort key that puts None first and never compares a number with text."""
    if value is None:
        return (0, 0, "")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return (1, value, "")
    return (2, 0, str(value))


def build_revisions(conn: sqlite3.Connection) -> dict:
    """Find the same-date price corrections in the database snapshots (owner decision 55, 2026-11-23).

    ``rates.json`` cannot show them: each stored scrape upserts a tariff version keyed by (utility, name,
    effective date) and replaces its components, so only a version's latest values survive there. Every
    stored scrape also appends the full TariffRecord to ``historical_snapshots``, which keeps the earlier ones.

    Snapshots are read in (snapshot_date, scrape_run_id, id) order and only live ones (``derive_provenance``)
    give values, so an estimate between two live snapshots neither starts nor ends a run of equal values
    (``_same_value``). A line with more than one run is a correction, including a change between a number and
    no value. A tariff version whose newest snapshot is not live is left out, because the site does not chart
    it. A line repeated within one snapshot (in November 2026, BC Hydro's power factor surcharge steps, told
    apart only by their notes) or whose value is neither a finite number nor null cannot be followed, so it is
    left out rather than guessed.
    """
    latest = None
    newest_is_live: dict[tuple, bool] = {}
    runs: dict[tuple, list[list]] = {}  # (tariff, line, line date) -> [[value, first_stored, last_stored], ...]
    unusable: set[tuple] = set()
    cursor = conn.cursor()
    cursor.row_factory = None
    cursor.execute("SELECT scrape_run_id, snapshot_date, tariff_json FROM historical_snapshots "
                   "ORDER BY snapshot_date, scrape_run_id, id")
    for run_id, snapshot_date, tariff_json in cursor:
        latest = {"scrape_run_id": run_id, "snapshot_date": snapshot_date}
        snapshot = json.loads(tariff_json)
        tariff = (snapshot.get("utility_name"), snapshot.get("province"), snapshot.get("tariff_name"),
                  snapshot.get("effective_date"))
        live = derive_provenance(snapshot.get("confidence"), snapshot.get("notes")) == "live"
        newest_is_live[tariff] = live
        if not live:
            continue
        seen: set[tuple] = set()
        for component in snapshot.get("components") or ():
            key = (tariff, tuple(component.get(name) for name in REVISION_LINE_FIELDS),
                   component.get("effective_date") or tariff[3])
            value = component.get("charge_value")
            if key in seen or not _number_or_none(value):
                unusable.add(key)
                continue
            seen.add(key)
            history = runs.setdefault(key, [])
            if history and _same_value(history[-1][0], value):
                # The newest stored form, so the latest value matches rates.json exactly.
                history[-1][0] = value
                history[-1][2] = snapshot_date
            else:
                history.append([value, snapshot_date, snapshot_date])
    cursor.close()

    revisions = []
    for key, history in runs.items():
        tariff, line, effective_date = key
        if len(history) < 2 or key in unusable or not newest_is_live[tariff]:
            continue
        utility_name, province, tariff_name, tariff_effective_date = tariff
        value, revised_on, _ = history[-1]
        revisions.append({
            "utility_name": utility_name, "province": province, "tariff_name": tariff_name,
            "tariff_effective_date": tariff_effective_date, **dict(zip(REVISION_LINE_FIELDS, line)),
            "effective_date": effective_date, "value": value, "revised_on": revised_on,
            "earlier": [{"value": earlier, "first_stored": first, "last_stored": last}
                        for earlier, first, last in history[:-1]],
        })
    revisions.sort(key=lambda revision: tuple(_none_first(revision[name]) for name in REVISION_SORT_FIELDS))
    left_out = sum(1 for key in unusable if newest_is_live[key[0]])
    if left_out:
        logger.info("Rate history revisions: %d price lines left out (repeated within one snapshot or not a number)",
                    left_out)
    return {"version": 1, "kind": "rate_history_revisions", "rule": REVISIONS_RULE,
            "latest_snapshot": latest, "revisions": revisions}


def export_rate_history_revisions(conn: sqlite3.Connection, out_path: Path) -> dict | None:
    """Write the same-date corrections for the Rate History tab (owner decision 55, 2026-11-23).

    Never raises: on any failure the error is logged, ``None`` is returned and an existing file is left
    untouched (written to a temporary file, then swapped in), like the representative models.
    """
    out_path = Path(out_path)
    tmp_path = out_path.with_name(out_path.name + ".tmp")
    try:
        document = build_revisions(conn)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(tmp_path, document)
        os.replace(tmp_path, out_path)
    except Exception:
        logger.exception("Rate history revisions export failed; %s left unchanged", out_path)
        with contextlib.suppress(OSError):
            tmp_path.unlink(missing_ok=True)
        return None
    logger.info("Exported %d same-date price revisions to %s", len(document["revisions"]), out_path)
    return document


def start_model_receipt(receipt_path: Path | None, output: Path) -> tuple[ModuleType | None, dict]:
    """Keep optional monitoring setup out of the primary generation's failure path."""
    if receipt_path is not None:
        try:
            from pipeline import model_monitoring
            return model_monitoring, model_monitoring.observe_previous(output)
        except Exception:
            logger.exception("Model monitoring setup failed; continuing the primary generation without a receipt")
    return None, {}


def export_representative_models(tariffs: list[dict], out_path: Path, *,
                                 generation_receipt_path: Path | None = None) -> dict | None:
    """Build the representative models from the exported tariffs and write them as compact JSON.

    Never raises: on any failure the error is logged, ``None`` is returned and an existing file is left untouched.
    """
    out_path = Path(out_path)
    tmp_path = out_path.with_name(out_path.name + ".tmp")
    monitor, previous = start_model_receipt(generation_receipt_path, out_path)
    inputs = {}
    try:
        # Imported here so a broken models module cannot break the main export.
        from pipeline import representative_models as models

        inputs = {"crosswalk": models.load_crosswalk(), "usage_levels": models.load_usage_levels(),
                  "taxes": models.load_taxes()}
        result = models.build_models(
            tariffs, inputs["crosswalk"], inputs["usage_levels"], inputs["taxes"],
            provinces=MODEL_PROVINCES, zone_policy="median_of_zones", input_label="site/data/rates.json",
        )
        text = json.dumps(result, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(text + "\n", encoding="utf-8")
        os.replace(tmp_path, out_path)
    except Exception as exc:
        logger.exception("Representative models export failed; %s left unchanged", out_path)
        with contextlib.suppress(OSError):
            tmp_path.unlink(missing_ok=True)
        if monitor is not None:
            monitor.save_generation_receipt(generation_receipt_path, None, previous=previous,
                                            error=f"{type(exc).__name__}: {exc}")
        return None
    if monitor is not None:
        monitor.save_generation_receipt(generation_receipt_path, result, previous=previous, inputs=inputs)
    logger.info("Exported %d representative models to %s", len(result["models"]), out_path)
    return result


def export_spark_gap(tariffs: list[dict], out_path: Path) -> dict | None:
    """Build the spark gap comparison (pipeline.spark_gap, method SG-1) right after the models and write it.

    Never raises: on any failure the error is logged, ``None`` is returned and an existing file is left untouched
    (owner decision 143, 2026-11-26). The simulated buildings are cached per process, so they are read once.
    """
    try:
        # Imported here so a broken spark gap module cannot break the main export.
        from pipeline import spark_gap

        result = spark_gap.write_spark_gap(out_path, rates=tariffs)
    except Exception:
        logger.exception("Spark gap export failed; %s left unchanged", out_path)
        return None
    logger.info("Exported the spark gap comparison to %s", out_path)
    return result


def write_json(path: Path, data: object) -> None:
    """Write data to a JSON file with nice formatting."""
    # newline="\n": the repository stores text with LF, and Windows text mode would otherwise write CRLF.
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation-receipt", type=Path, help="write an explicit model refresh outcome for CI")
    export_all(generation_receipt_path=parser.parse_args().generation_receipt)
