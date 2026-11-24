"""Same-date price corrections for the Rate History tab (owner decision 55, 2026-11-23).

Snapshots are stored by the production ``store_results``, so each ``tariff_json`` is the
``canonical_snapshot`` of a real TariffRecord; only their dates are set afterwards, because
``store_results`` stamps the current date.
"""

from __future__ import annotations

import json
import logging
import math
import sqlite3
from pathlib import Path

from pipeline import export_json
from pipeline.export_json import build_revisions, export_rate_history_revisions
from pipeline.run_scrape import store_results
from scrapers.base import BaseScraper, RateComponent, TariffRecord

SCHEMA = Path(__file__).resolve().parent.parent / "schema" / "create_tables.sql"
REVISION_KEYS = ["utility_name", "province", "tariff_name", "tariff_effective_date", "component_type",
                 "component_name", "charge_unit", "tier_number", "tou_period", "season", "sub_component",
                 "effective_date", "value", "revised_on", "earlier"]


class _Scraper(BaseScraper):
    def __init__(self):
        super().__init__("Fixture Hydro", "ON")

    def scrape(self):
        return []


SCRAPER = _Scraper()


def create_schema(conn: sqlite3.Connection) -> sqlite3.Connection:
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    return conn


def energy(value, period="on-peak", *, tier=None, effective=None, name="Energy Charge") -> RateComponent:
    return RateComponent("energy", name, value, "$/kWh", tier_number=tier, tou_period=period,
                         effective_date=effective)


def tariff(*components, utility="Fixture Hydro", province="ON", name="Residential Service",
           effective="2026-11-01") -> TariffRecord:
    return TariffRecord(utility_name=utility, province=province, utility_type="electricity", tariff_name=name,
                        effective_date=effective, rate_structure="tou", components=list(components))


def store(conn: sqlite3.Connection, run_id: int, snapshot_date: str, *records: TariffRecord, live=True) -> None:
    """Store one scrape run dated ``snapshot_date``, labelled live-parsed or as seed estimates."""
    records = list(records)
    if live:
        SCRAPER.mark_live_parsed(records)
    else:
        SCRAPER.mark_fallback(records)
    conn.execute("INSERT INTO scrape_runs (id, started_at, status) VALUES (?, ?, 'completed')",
                 (run_id, f"{snapshot_date}T08:00:00+00:00"))
    store_results(records, run_id, conn)
    conn.execute("UPDATE historical_snapshots SET snapshot_date = ? WHERE scrape_run_id = ?", (snapshot_date, run_id))
    conn.commit()


def test_a_same_date_correction_reports_the_latest_value_and_the_earlier_run():
    conn = create_schema(sqlite3.connect(":memory:"))
    assert build_revisions(conn)["latest_snapshot"] is None
    for run_id, day, on_peak in ((1, "2026-11-01", 0.19), (2, "2026-11-03", 0.19), (3, "2026-11-04", 0.189),
                                 (4, "2026-11-18", 0.189)):
        store(conn, run_id, day, tariff(energy(on_peak), energy(0.098, "off-peak")))

    document = build_revisions(conn)
    assert list(document) == ["version", "kind", "rule", "latest_snapshot", "revisions"]
    assert (document["version"], document["kind"]) == (1, "rate_history_revisions")
    assert "owner decision 55, 2026-11-23" in document["rule"]
    assert document["latest_snapshot"] == {"scrape_run_id": 4, "snapshot_date": "2026-11-18"}
    [revision] = document["revisions"]
    assert list(revision) == REVISION_KEYS
    assert revision == {
        "utility_name": "Fixture Hydro", "province": "ON", "tariff_name": "Residential Service",
        "tariff_effective_date": "2026-11-01", "component_type": "energy", "component_name": "Energy Charge",
        "charge_unit": "$/kWh", "tier_number": None, "tou_period": "on-peak", "season": None, "sub_component": None,
        "effective_date": "2026-11-01", "value": 0.189, "revised_on": "2026-11-04",
        "earlier": [{"value": 0.19, "first_stored": "2026-11-01", "last_stored": "2026-11-03"}],
    }


def test_a_new_effective_date_is_a_price_change_not_a_revision():
    conn = create_schema(sqlite3.connect(":memory:"))
    store(conn, 1, "2026-10-01", tariff(energy(0.203), effective="2026-05-01"),
          tariff(energy(0.30, effective="2026-10-01"), name="Gas Supply", effective="2026-01-01"))
    store(conn, 2, "2026-11-01", tariff(energy(0.189), effective="2026-11-01"),
          tariff(energy(0.25, effective="2026-11-01"), name="Gas Supply", effective="2026-01-01"))
    assert build_revisions(conn)["revisions"] == []


def test_consecutive_identical_values_are_not_revisions():
    conn = create_schema(sqlite3.connect(":memory:"))
    for run_id, day in ((1, "2026-11-01"), (2, "2026-11-04"), (3, "2026-11-18")):
        store(conn, run_id, day, tariff(energy(0.189), energy(0.098, "off-peak")))
    assert build_revisions(conn)["revisions"] == []


def test_floating_point_noise_is_not_a_revision_and_the_newest_stored_form_is_the_value():
    """0.10859999999999999 -> 0.1086 is a parser rounding the same price (BC Hydro, October 2026)."""
    conn = create_schema(sqlite3.connect(":memory:"))
    noisy = math.nextafter(0.189, 0)
    store(conn, 1, "2026-11-01", tariff(energy(0.10859999999999999), energy(0.19, "off-peak")))
    store(conn, 2, "2026-11-04", tariff(energy(0.1086), energy(0.189, "off-peak")))
    store(conn, 3, "2026-11-18", tariff(energy(0.1086), energy(noisy, "off-peak")))
    [revision] = build_revisions(conn)["revisions"]
    assert (revision["tou_period"], revision["value"], revision["revised_on"]) == ("off-peak", noisy, "2026-11-04")
    assert revision["earlier"] == [{"value": 0.19, "first_stored": "2026-11-01", "last_stored": "2026-11-01"}]


def test_a_seed_snapshot_between_live_ones_neither_starts_nor_ends_a_run():
    conn = create_schema(sqlite3.connect(":memory:"))
    store(conn, 1, "2026-11-01", tariff(energy(0.19)))
    store(conn, 2, "2026-11-02", tariff(energy(0.25)), live=False)
    store(conn, 3, "2026-11-03", tariff(energy(0.19)))
    store(conn, 4, "2026-11-04", tariff(energy(0.18)))
    [revision] = build_revisions(conn)["revisions"]
    assert (revision["value"], revision["revised_on"]) == (0.18, "2026-11-04")
    assert revision["earlier"] == [{"value": 0.19, "first_stored": "2026-11-01", "last_stored": "2026-11-03"}]


def test_a_tariff_whose_newest_snapshot_is_an_estimate_is_skipped():
    conn = create_schema(sqlite3.connect(":memory:"))
    store(conn, 1, "2026-11-01", tariff(energy(0.19)), tariff(energy(0.19), name="Small Business"))
    store(conn, 2, "2026-11-04", tariff(energy(0.18)), tariff(energy(0.18), name="Small Business"))
    store(conn, 3, "2026-11-18", tariff(energy(0.18)), live=False)
    document = build_revisions(conn)
    assert [revision["tariff_name"] for revision in document["revisions"]] == ["Small Business"]
    assert document["latest_snapshot"] == {"scrape_run_id": 3, "snapshot_date": "2026-11-18"}


def test_a_line_that_becomes_value_less_is_a_revision():
    conn = create_schema(sqlite3.connect(":memory:"))
    store(conn, 1, "2026-11-01", tariff(RateComponent("energy", "Market Energy", 0.052, "$/kWh")))
    store(conn, 2, "2026-11-04", tariff(RateComponent("energy", "Market Energy", None, "$/kWh",
                                                      market_reference="IESO Ontario Price")))
    [revision] = build_revisions(conn)["revisions"]
    assert (revision["value"], revision["revised_on"]) == (None, "2026-11-04")
    assert revision["earlier"] == [{"value": 0.052, "first_stored": "2026-11-01", "last_stored": "2026-11-01"}]


def test_two_successive_corrections_list_both_earlier_runs():
    conn = create_schema(sqlite3.connect(":memory:"))
    for run_id, day, value in ((1, "2026-11-01", 0.19), (2, "2026-11-02", 0.18), (3, "2026-11-03", 0.18),
                               (4, "2026-11-04", 0.185)):
        store(conn, run_id, day, tariff(energy(value)))
    [revision] = build_revisions(conn)["revisions"]
    assert (revision["value"], revision["revised_on"]) == (0.185, "2026-11-04")
    assert revision["earlier"] == [{"value": 0.19, "first_stored": "2026-11-01", "last_stored": "2026-11-01"},
                                   {"value": 0.18, "first_stored": "2026-11-02", "last_stored": "2026-11-03"}]


def test_lines_that_cannot_be_followed_are_left_out():
    """Steps told apart only by their notes (BC Hydro's power factor surcharge) and non-finite values."""
    def record(steps, on_peak, off_peak):
        return tariff(*(RateComponent("adjustment", "Power Factor Surcharge", step, "fraction",
                                      sub_component="conditional", notes=f"Band {band}")
                        for band, step in enumerate(steps)),
                      energy(on_peak), energy(off_peak, "off-peak"))

    conn = create_schema(sqlite3.connect(":memory:"))
    store(conn, 1, "2026-11-01", record((0.02, 0.04), 0.19, float("nan")))
    store(conn, 2, "2026-11-04", record((0.03, 0.05), 0.18, float("nan")))
    assert [(r["component_name"], r["tou_period"]) for r in build_revisions(conn)["revisions"]] == [
        ("Energy Charge", "on-peak")]


def test_revisions_are_sorted_with_none_first_and_written_identically(tmp_path):
    def lines(value):
        return (energy(value, "off-peak", tier=None), energy(value, None, tier=2), energy(value, None, tier=1),
                energy(value, None, tier=None))

    conn = create_schema(sqlite3.connect(":memory:"))
    for run_id, day, value in ((1, "2026-11-01", 0.10), (2, "2026-11-04", 0.11)):
        store(conn, run_id, day,
              tariff(energy(value * 3), utility="Énergir", province="QC", name="Rate D1"),
              tariff(energy(value), utility="Zeta Hydro"),
              tariff(*lines(value), utility="Alpha Hydro"),
              tariff(energy(value / 2), utility="Beta Power", province="AB"))

    document = build_revisions(conn)
    assert [(r["province"], r["utility_name"], r["tier_number"], r["tou_period"]) for r in document["revisions"]] == [
        ("AB", "Beta Power", None, "on-peak"),
        ("ON", "Alpha Hydro", None, None), ("ON", "Alpha Hydro", None, "off-peak"),
        ("ON", "Alpha Hydro", 1, None), ("ON", "Alpha Hydro", 2, None),
        ("ON", "Zeta Hydro", None, "on-peak"),
        ("QC", "Énergir", None, "on-peak"),
    ]
    first, second = tmp_path / "a" / "rate_history_revisions.json", tmp_path / "b" / "rate_history_revisions.json"
    assert export_rate_history_revisions(conn, first) == document == build_revisions(conn)
    export_rate_history_revisions(conn, second)
    data = first.read_bytes()
    assert data == second.read_bytes()
    assert b"\r" not in data and not data.startswith(b"\xef\xbb\xbf") and "Énergir".encode("utf-8") in data
    assert json.loads(data.decode("utf-8")) == document


def test_export_all_keeps_the_previous_revisions_file_when_building_fails(tmp_path, monkeypatch, caplog):
    db_path, site = tmp_path / "rates.db", tmp_path / "site"
    conn = create_schema(sqlite3.connect(db_path))
    store(conn, 1, "2026-11-01", tariff(energy(0.19)))
    store(conn, 2, "2026-11-04", tariff(energy(0.189)))
    conn.close()
    monkeypatch.setattr(export_json, "DB_PATH", db_path)
    monkeypatch.setattr(export_json, "SITE_DATA_DIR", site)
    export_json.export_all()
    revisions_path = site / "rate_history_revisions.json"
    previous = revisions_path.read_bytes()
    assert [revision["value"] for revision in json.loads(previous)["revisions"]] == [0.189]

    def broken(conn):
        raise RuntimeError("snapshot read failed")

    monkeypatch.setattr(export_json, "build_revisions", broken)
    (site / "rates.json").unlink()
    with caplog.at_level(logging.ERROR, logger="pipeline.export_json"):
        export_json.export_all()
    assert revisions_path.read_bytes() == previous and not list(site.glob("*.tmp"))
    assert [t["name"] for t in json.loads((site / "rates.json").read_text(encoding="utf-8"))] == ["Residential Service"]
    assert "Rate history revisions export failed" in caplog.text


def test_an_interrupted_write_keeps_the_previous_revisions_file(tmp_path, monkeypatch):
    conn = create_schema(sqlite3.connect(":memory:"))
    store(conn, 1, "2026-11-01", tariff(energy(0.19)))
    out = tmp_path / "rate_history_revisions.json"
    out.write_text('{"previous": true}', encoding="utf-8")

    def interrupted(path, data):
        Path(path).write_text("{", encoding="utf-8")
        raise OSError("disk full")

    monkeypatch.setattr(export_json, "write_json", interrupted)
    assert export_rate_history_revisions(conn, out) is None
    assert out.read_text(encoding="utf-8") == '{"previous": true}' and not list(tmp_path.glob("*.tmp"))
