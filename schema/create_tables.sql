/*
 * canada-utility-costs: SQLite Database Schema
 *
 * WHY SQLITE?
 * -----------
 * 1. Zero setup — comes built into Python, no server to install.
 * 2. Single file — easy to commit sample data, share, and back up.
 * 3. Full SQL — supports JOINs, indexes, window functions, CTEs.
 * 4. Portable — works on every OS without configuration.
 * 5. Good enough for this scale — even 100k rate records is tiny for SQLite.
 *
 * The database lives at  data/db/rates.db  and is created by
 *   python pipeline/run_scrape.py --init-db
 *
 * DESIGN PRINCIPLES
 * -----------------
 * - Every table has an integer primary key (id).
 * - All timestamps are ISO-8601 strings in UTC.
 * - Historical data is NEVER deleted — we INSERT new versions.
 * - scrape_runs tracks each execution so we can diff over time.
 * - rate_components is the heart: one row per individual charge line.
 */

-- ============================================================
-- 1. UTILITIES  — one row per distinct utility company
-- ============================================================
CREATE TABLE IF NOT EXISTS utilities (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,                -- e.g. "BC Hydro"
    province        TEXT    NOT NULL,                -- e.g. "BC"
    utility_type    TEXT    NOT NULL,                -- "electricity" | "gas" | "both"
    website         TEXT,                            -- official homepage
    rate_page_url   TEXT,                            -- main rate/tariff page
    regulator       TEXT,                            -- e.g. "BCUC", "OEB"
    notes           TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),

    UNIQUE(name, province)
);

-- ============================================================
-- 2. SOURCES  — where we found (or expect to find) rate data
-- ============================================================
CREATE TABLE IF NOT EXISTS sources (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    utility_id      INTEGER NOT NULL REFERENCES utilities(id),
    url             TEXT    NOT NULL,                -- direct URL to the data
    source_type     TEXT    NOT NULL,                -- "html" | "pdf" | "csv" | "xlsx" | "api" | "mixed"
    description     TEXT,                            -- human note: "Residential rate schedule PDF"
    is_primary      INTEGER NOT NULL DEFAULT 1,      -- 1 = official primary, 0 = fallback
    last_checked    TEXT,                            -- last time we successfully fetched this
    last_hash       TEXT,                            -- hash of content for change detection
    status          TEXT    NOT NULL DEFAULT 'active', -- "active" | "broken" | "moved" | "retired"
    notes           TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 3. SCRAPE RUNS  — one row per execution of the scraper
-- ============================================================
CREATE TABLE IF NOT EXISTS scrape_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TEXT    NOT NULL,
    finished_at     TEXT,
    status          TEXT    NOT NULL DEFAULT 'running', -- "running" | "completed" | "failed"
    utilities_attempted INTEGER DEFAULT 0,
    utilities_succeeded INTEGER DEFAULT 0,
    errors          TEXT,                            -- JSON array of error messages
    notes           TEXT
);

-- ============================================================
-- 4. TARIFFS  — a named rate plan / tariff / schedule
-- ============================================================
CREATE TABLE IF NOT EXISTS tariffs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    utility_id      INTEGER NOT NULL REFERENCES utilities(id),
    scrape_run_id   INTEGER REFERENCES scrape_runs(id),
    name            TEXT    NOT NULL,                -- e.g. "Residential Service (Rate 1101)"
    tariff_code     TEXT,                            -- short code if the utility uses one
    utility_type    TEXT    NOT NULL,                -- "electricity" | "gas"
    customer_class  TEXT    NOT NULL,                -- "residential" | "commercial" | "industrial" | "general_service" | "other"
    sub_class       TEXT,                            -- finer classification if available
    description     TEXT,
    eligibility     TEXT,                            -- who qualifies — text
    demand_min_kw   REAL,                            -- minimum demand for eligibility (kW)
    demand_max_kw   REAL,                            -- maximum demand for eligibility (kW)
    usage_min       REAL,                            -- minimum usage for eligibility
    usage_max       REAL,                            -- maximum usage for eligibility
    usage_unit      TEXT,                            -- "kWh" | "GJ" | "m3" | "therms"
    rate_structure  TEXT,                            -- "flat" | "tiered" | "tou" | "demand" | "market" | "mixed"
    effective_date  TEXT,                            -- when this tariff version became effective
    end_date        TEXT,                            -- NULL if currently active
    source_id       INTEGER REFERENCES sources(id),
    source_url      TEXT,                            -- direct URL that contained this tariff
    source_page     TEXT,                            -- page number or section in PDF
    confidence      TEXT    NOT NULL DEFAULT 'high', -- "high" | "medium" | "low" | "unverified"
    notes           TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),

    UNIQUE(utility_id, tariff_code, effective_date)
);

-- ============================================================
-- 5. RATE COMPONENTS  — one row per individual charge line
--    This is the core table.  A tariff has MANY components.
-- ============================================================
CREATE TABLE IF NOT EXISTS rate_components (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tariff_id       INTEGER NOT NULL REFERENCES tariffs(id),
    scrape_run_id   INTEGER REFERENCES scrape_runs(id),

    -- What kind of charge is this?
    component_type  TEXT    NOT NULL,
    /*  Allowed values for component_type:
        "fixed"              — fixed monthly/daily charge ($)
        "energy"             — per-unit energy charge
        "demand"             — demand charge (per kW or kVA)
        "delivery"           — delivery / distribution volumetric
        "transmission"       — transmission charge
        "distribution"       — distribution charge
        "regulatory"         — regulatory / admin charge
        "rider"              — rider / adjustment / adder
        "carbon"             — carbon levy / charge
        "commodity"          — commodity / supply charge
        "market"             — market-indexed component
        "rebate"             — credit or rebate (negative value)
        "tax"                — tax component (GST/HST/PST if broken out)
        "other"              — anything else
    */

    component_name  TEXT    NOT NULL,               -- human-readable label
    sub_component   TEXT,                            -- further detail if nested

    -- Charge value
    charge_value    REAL,                            -- the rate / price / amount
    charge_unit     TEXT,                            -- "$/kWh" | "$/GJ" | "$/m3" | "$/kW" | "$/day" | "$/month" | "%"
    charge_currency TEXT    NOT NULL DEFAULT 'CAD',

    -- Tier / TOU / Season structure
    tier_number     INTEGER,                         -- 1, 2, 3… for tiered rates
    tier_threshold  REAL,                            -- usage threshold for this tier
    tier_unit       TEXT,                            -- "kWh" | "GJ" | "m3"
    tou_period      TEXT,                            -- "on-peak" | "mid-peak" | "off-peak" | "ultra-low-overnight" | NULL
    tou_hours       TEXT,                            -- description of TOU window
    season          TEXT,                            -- "summer" | "winter" | "shoulder" | NULL
    season_months   TEXT,                            -- "May-Oct" or similar

    -- Demand-specific fields
    demand_threshold_kw REAL,
    demand_unit     TEXT,                            -- "kW" | "kVA"

    -- Market-indexed component fields
    market_reference TEXT,                           -- e.g. "AESO pool price", "IESO HOEP"
    market_source_url TEXT,                          -- URL to the market price source

    -- Metadata
    effective_date  TEXT,                            -- inherited from tariff or overridden
    end_date        TEXT,
    source_url      TEXT,
    source_detail   TEXT,                            -- page number, table name, etc.
    confidence      TEXT    NOT NULL DEFAULT 'high',
    notes           TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 6. HISTORICAL SNAPSHOTS  — archived tariff+component state
--    Each scrape run can produce a snapshot.  We never delete.
-- ============================================================
CREATE TABLE IF NOT EXISTS historical_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    scrape_run_id   INTEGER NOT NULL REFERENCES scrape_runs(id),
    tariff_id       INTEGER NOT NULL REFERENCES tariffs(id),
    snapshot_date   TEXT    NOT NULL,                -- date of the snapshot
    tariff_json     TEXT    NOT NULL,                -- full JSON of tariff + components at that point
    hash            TEXT,                            -- hash of tariff_json for quick diff
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 7. MISSING DATA LOG  — tracks what we know is incomplete
-- ============================================================
CREATE TABLE IF NOT EXISTS missing_data (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    utility_id      INTEGER REFERENCES utilities(id),
    utility_name    TEXT,                            -- in case utility not yet in DB
    province        TEXT,
    description     TEXT    NOT NULL,                -- what's missing
    severity        TEXT    NOT NULL DEFAULT 'medium', -- "low" | "medium" | "high" | "critical"
    reason          TEXT,                            -- why it's missing
    workaround      TEXT,                            -- any available fallback
    resolved        INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    resolved_at     TEXT
);

-- ============================================================
-- 8. CUSTOMER CLASSES  — structured class/threshold metadata
--    One row per customer class per utility.
-- ============================================================
CREATE TABLE IF NOT EXISTS customer_classes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    utility_id          INTEGER NOT NULL REFERENCES utilities(id),
    class_name          TEXT    NOT NULL,        -- "residential" | "commercial" | "industrial" | "general_service"
    sub_class_name      TEXT,                    -- "GS < 50 kW", "Large Use", "Street Lighting", etc.
    eligibility_rule    TEXT,                    -- structured eligibility description
    threshold_kw_min    REAL,                    -- minimum demand threshold (kW)
    threshold_kw_max    REAL,                    -- maximum demand threshold (kW)
    threshold_other     TEXT,                    -- any non-kW eligibility threshold (JSON or text)
    rule_text_raw       TEXT,                    -- verbatim tariff rule text from source
    source_url          TEXT,                    -- where the class definition was found
    notes               TEXT,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),

    UNIQUE(utility_id, class_name, sub_class_name)
);

-- ============================================================
-- INDEXES for common queries
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_tariffs_utility    ON tariffs(utility_id);
CREATE INDEX IF NOT EXISTS idx_tariffs_class      ON tariffs(customer_class);
CREATE INDEX IF NOT EXISTS idx_tariffs_type       ON tariffs(utility_type);
CREATE INDEX IF NOT EXISTS idx_components_tariff  ON rate_components(tariff_id);
CREATE INDEX IF NOT EXISTS idx_components_type    ON rate_components(component_type);
CREATE INDEX IF NOT EXISTS idx_snapshots_tariff   ON historical_snapshots(tariff_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_run      ON historical_snapshots(scrape_run_id);
CREATE INDEX IF NOT EXISTS idx_sources_utility    ON sources(utility_id);
CREATE INDEX IF NOT EXISTS idx_customer_classes_utility ON customer_classes(utility_id);
CREATE INDEX IF NOT EXISTS idx_customer_classes_name    ON customer_classes(class_name);
