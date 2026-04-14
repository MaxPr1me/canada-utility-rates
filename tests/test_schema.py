"""
test_schema.py — Tests for schema/create_tables.sql

Uses an in-memory SQLite database to verify:
  - All tables are created by the schema SQL
  - A utility row can be inserted and read back
  - Linked tariff + rate_component rows can be inserted
"""

import sys
import os
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "schema", "create_tables.sql")

EXPECTED_TABLES = [
    "utilities",
    "sources",
    "scrape_runs",
    "tariffs",
    "rate_components",
    "historical_snapshots",
    "missing_data",
    "customer_classes",
]


@pytest.fixture
def db():
    """Create an in-memory SQLite database and run the schema SQL."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    yield conn
    conn.close()


# ─── Table creation ──────────────────────────────────────────────

class TestCreateTables:
    def test_all_expected_tables_exist(self, db):
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        table_names = [row["name"] for row in cursor.fetchall()]
        for expected in EXPECTED_TABLES:
            assert expected in table_names, f"Table '{expected}' not found in schema"

    def test_indexes_created(self, db):
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        indexes = [row["name"] for row in cursor.fetchall()]
        assert len(indexes) >= 7, f"Expected at least 7 custom indexes, got {len(indexes)}"


# ─── Insert utility ─────────────────────────────────────────────

class TestInsertUtility:
    def test_insert_and_read_back(self, db):
        db.execute(
            "INSERT INTO utilities (name, province, utility_type, website) "
            "VALUES (?, ?, ?, ?)",
            ("BC Hydro", "BC", "electricity", "https://www.bchydro.com"),
        )
        db.commit()

        row = db.execute("SELECT * FROM utilities WHERE name = ?", ("BC Hydro",)).fetchone()
        assert row is not None
        assert row["name"] == "BC Hydro"
        assert row["province"] == "BC"
        assert row["utility_type"] == "electricity"
        assert row["website"] == "https://www.bchydro.com"

    def test_unique_constraint(self, db):
        db.execute(
            "INSERT INTO utilities (name, province, utility_type) VALUES (?, ?, ?)",
            ("BC Hydro", "BC", "electricity"),
        )
        db.commit()
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO utilities (name, province, utility_type) VALUES (?, ?, ?)",
                ("BC Hydro", "BC", "electricity"),
            )

    def test_auto_increment_id(self, db):
        db.execute(
            "INSERT INTO utilities (name, province, utility_type) VALUES (?, ?, ?)",
            ("BC Hydro", "BC", "electricity"),
        )
        db.execute(
            "INSERT INTO utilities (name, province, utility_type) VALUES (?, ?, ?)",
            ("Hydro-Québec", "QC", "electricity"),
        )
        db.commit()
        rows = db.execute("SELECT id FROM utilities ORDER BY id").fetchall()
        assert rows[0]["id"] == 1
        assert rows[1]["id"] == 2


# ─── Insert tariff with components ──────────────────────────────

class TestInsertTariffWithComponents:
    def test_insert_linked_records(self, db):
        # Insert a utility first
        db.execute(
            "INSERT INTO utilities (name, province, utility_type) VALUES (?, ?, ?)",
            ("BC Hydro", "BC", "electricity"),
        )
        utility_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Insert a tariff linked to that utility
        db.execute(
            "INSERT INTO tariffs (utility_id, name, tariff_code, utility_type, "
            "customer_class, rate_structure, effective_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (utility_id, "Residential Service (Rate 1101)", "1101",
             "electricity", "residential", "tiered", "2024-04-01"),
        )
        tariff_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Insert rate components linked to the tariff
        components = [
            ("fixed", "Basic Charge", 0.2240, "$/day"),
            ("energy", "Step 1 Energy", 0.0950, "$/kWh"),
            ("energy", "Step 2 Energy", 0.1408, "$/kWh"),
        ]
        for comp_type, comp_name, value, unit in components:
            db.execute(
                "INSERT INTO rate_components "
                "(tariff_id, component_type, component_name, charge_value, charge_unit) "
                "VALUES (?, ?, ?, ?, ?)",
                (tariff_id, comp_type, comp_name, value, unit),
            )
        db.commit()

        # Verify the tariff
        tariff = db.execute(
            "SELECT * FROM tariffs WHERE id = ?", (tariff_id,)
        ).fetchone()
        assert tariff["name"] == "Residential Service (Rate 1101)"
        assert tariff["utility_id"] == utility_id
        assert tariff["rate_structure"] == "tiered"

        # Verify the components
        rows = db.execute(
            "SELECT * FROM rate_components WHERE tariff_id = ? ORDER BY id",
            (tariff_id,),
        ).fetchall()
        assert len(rows) == 3
        assert rows[0]["component_type"] == "fixed"
        assert rows[0]["component_name"] == "Basic Charge"
        assert rows[0]["charge_value"] == pytest.approx(0.2240)
        assert rows[1]["charge_value"] == pytest.approx(0.0950)
        assert rows[2]["charge_value"] == pytest.approx(0.1408)

    def test_foreign_key_linkage(self, db):
        """Verify tariff rows reference the correct utility via JOIN."""
        db.execute(
            "INSERT INTO utilities (name, province, utility_type) VALUES (?, ?, ?)",
            ("Toronto Hydro", "ON", "electricity"),
        )
        utility_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute(
            "INSERT INTO tariffs (utility_id, name, tariff_code, utility_type, "
            "customer_class, rate_structure) VALUES (?, ?, ?, ?, ?, ?)",
            (utility_id, "TOU Residential", "TOU-R", "electricity",
             "residential", "tou"),
        )
        db.commit()

        row = db.execute(
            "SELECT t.name AS tariff_name, u.name AS utility_name "
            "FROM tariffs t JOIN utilities u ON t.utility_id = u.id"
        ).fetchone()
        assert row["tariff_name"] == "TOU Residential"
        assert row["utility_name"] == "Toronto Hydro"
