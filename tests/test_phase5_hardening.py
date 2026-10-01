"""Deterministic Phase 5 parser, provenance, and history tests."""

from __future__ import annotations

import sqlite3
from dataclasses import replace

from pipeline.diff_report import diff_runs
from pipeline.run_scrape import canonical_snapshot, store_results
from scrapers.base import BaseScraper, RateComponent, TariffRecord
from scrapers.utils.parsing import (
    DocumentPage,
    clean_currency,
    extract_effective_date,
    find_pdf_section,
    normalize_charge_unit,
    verify_tariff_values,
)


class _Scraper(BaseScraper):
    def __init__(self):
        super().__init__("Fixture Utility", "ON")

    def scrape(self):
        return []


def tariff(value=0.123, *, code=None, effective="2026-01-01", components=None):
    return TariffRecord(
        utility_name="Fixture Utility", province="ON", utility_type="electricity",
        tariff_name="Residential Service", tariff_code=code,
        effective_date=effective, rate_structure="tiered",
        components=components or [RateComponent("energy", "Energy Charge", value, "$/kWh", tier_number=1)],
    )


def database():
    conn = sqlite3.connect(":memory:")
    conn.executescript(open("schema/create_tables.sql", encoding="utf-8").read())
    for run_id in (1, 2):
        conn.execute("INSERT INTO scrape_runs(id, started_at) VALUES (?, '2026-01-01')", (run_id,))
    return conn


def test_currency_units_dates_and_credits():
    assert clean_currency("(1.25) $/kW") == -1.25
    assert clean_currency("-2.50 cents/kWh") == -0.025
    assert normalize_charge_unit("$/kVA") == "$/kVA"
    assert normalize_charge_unit("dollars per cubic metre") == "$/m3"
    assert extract_effective_date("Rates effective July 1, 2026") == "2026-07-01"


def test_pdf_section_requires_label_and_tariff_code_and_keeps_pages():
    pages = [DocumentPage(4, "unrelated 12.3 cents/kWh"), DocumentPage(5, "Residential Rate D11"), DocumentPage(6, "Energy Charge 12.3 cents/kWh")]
    section = find_pdf_section(pages, ["Residential"], tariff_code="D11")
    assert [page.page_number for page in section] == [5, 6]
    assert not find_pdf_section(pages, ["Residential"], tariff_code="D99")
    assert section[0].source_detail == "PDF page 5"


def test_contextual_verification_rejects_same_number_in_wrong_section():
    record = tariff(code="D11")
    wrong = "Commercial Rate D21 Energy Charge 12.3 cents per kWh"
    assert verify_tariff_values(wrong, [record], require_context=True)
    right = "Residential Service D11 Energy Charge 12.3 cents per kWh"
    assert verify_tariff_values(right, [record], require_context=True) == []


def test_fallback_downgrades_tariff_and_critical_components():
    record = _Scraper().mark_fallback([tariff()])[0]
    assert record.confidence == record.components[0].confidence == "unverified"
    assert "seed_fallback" in record.notes


def test_live_parsed_marks_provenance_on_tariff_and_components():
    record = _Scraper().mark_live_parsed(
        [tariff()], source_url="https://example.com/rates", detail="Rate page"
    )[0]
    assert record.notes.startswith("Provenance: live_parsed.")
    assert record.source_url == "https://example.com/rates"
    assert record.components[0].notes.startswith("Provenance: live_parsed.")


def test_derive_provenance_only_trusts_explicit_live_markers():
    from pipeline.export_json import derive_provenance

    assert derive_provenance("high", "Provenance: officially_verified. x") == "live"
    assert derive_provenance("high", "Provenance: live_parsed. x") == "live"
    assert derive_provenance("unverified", "Provenance: seed_fallback. x") == "seed"
    # Conservative: high confidence without an explicit live marker is still seed.
    assert derive_provenance("high", "some note without marker") == "seed"
    assert derive_provenance("high", None) == "seed"


def test_snapshot_hash_ignores_component_order_but_tracks_semantics():
    a = RateComponent("fixed", "Monthly", 10, "$/month")
    b = RateComponent("energy", "Energy", 0.1, "$/kWh", tier_number=1)
    _, first = canonical_snapshot(tariff(components=[a, b]))
    _, reordered = canonical_snapshot(tariff(components=[b, a]))
    _, changed_unit = canonical_snapshot(tariff(components=[a, replace(b, charge_unit="$/GJ")]))
    _, changed_tier = canonical_snapshot(tariff(components=[a, replace(b, tier_number=2)]))
    assert first == reordered
    assert first != changed_unit != changed_tier


def test_snapshots_are_append_only_and_diff_changed_unchanged_and_none_code():
    conn = database()
    original = tariff(code=None)
    store_results([original], 1, conn)
    store_results([tariff(code=None)], 2, conn)
    first_diff = diff_runs(conn, 1, 2)
    assert first_diff["summary"] == {"new": 0, "removed": 0, "changed": 0, "unchanged": 1}
    assert conn.execute("SELECT count(*) FROM historical_snapshots").fetchone()[0] == 2

    conn.execute("INSERT INTO scrape_runs(id, started_at) VALUES (3, '2026-02-01')")
    store_results([tariff(0.2, code=None)], 3, conn)
    changed = diff_runs(conn, 2, 3)
    assert changed["summary"]["changed"] == 1
    assert conn.execute("SELECT count(*) FROM historical_snapshots").fetchone()[0] == 3


def test_new_effective_version_preserves_old_tariff_and_is_reported_new():
    conn = database()
    store_results([tariff(code="R", effective="2026-01-01")], 1, conn)
    store_results([tariff(code="R", effective="2026-04-01")], 2, conn)
    report = diff_runs(conn, 1, 2)
    assert report["summary"] == {"new": 1, "removed": 1, "changed": 0, "unchanged": 0}
    assert conn.execute("SELECT count(*) FROM tariffs").fetchone()[0] == 2


def test_saskpower_classes_keep_components_and_history_through_export(tmp_path, monkeypatch):
    import json
    from pathlib import Path
    from pipeline import export_json
    from scrapers.utilities.saskpower import SaskPowerScraper

    scraper = SaskPowerScraper()
    monkeypatch.setattr(scraper, "now_iso", lambda: "2026-10-01T00:00:00+00:00")
    records = []
    for name in ("supplied", "customer_owned"):
        fixture_path = Path(__file__).parent / "fixtures" / f"saskpower_{name}_transformation.json"
        document = json.loads(fixture_path.read_text(encoding="utf-8"))
        pages = [DocumentPage(**page) for page in document["pages"]]
        records.extend(scraper.mark_live_parsed(
            scraper._parse_transformation(pages, document["source_url"]),
            source_url=document["source_url"],
        ))
    assert len(records) == 25
    records[:2] = [replace(record, tariff_code=None) for record in records[:2]]
    connection = database()
    for run_id in (1, 2):
        assert store_results(records, run_id, connection) == 25
    assert connection.execute("SELECT count(*) FROM tariffs").fetchone()[0] == 25
    assert connection.execute("SELECT count(*) FROM historical_snapshots").fetchone()[0] == 50
    assert diff_runs(connection, 1, 2)["summary"]["unchanged"] == 25
    component_counts = dict(connection.execute(
        "SELECT tariffs.name, count(rate_components.id) FROM tariffs "
        "JOIN rate_components ON rate_components.tariff_id = tariffs.id GROUP BY tariffs.id"
    ))
    assert component_counts == {record.tariff_name: len(record.components) for record in records}

    db_path = tmp_path / "rates.db"
    persisted = sqlite3.connect(db_path)
    connection.backup(persisted)
    persisted.close()
    connection.close()
    monkeypatch.setattr(export_json, "DB_PATH", db_path)
    monkeypatch.setattr(export_json, "SITE_DATA_DIR", tmp_path / "site")
    export_json.export_all()
    exported = json.loads((tmp_path / "site" / "rates.json").read_text(encoding="utf-8"))
    assert len(exported) == 25
    assert all(record["provenance"] == "live" for record in exported)
    assert {record["name"]: len(record["components"]) for record in exported} == component_counts
    assert all(component["source_url"] and component["source_detail"] for record in exported for component in record["components"])
