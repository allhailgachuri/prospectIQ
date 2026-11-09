"""
SQLite storage layer for ProspectIQ.

Provides:
  - Database initialisation / schema migration
  - Batch-efficient upsert with full provenance
  - CSV export
  - Basic query helpers
"""
import csv
import sqlite3
from pathlib import Path
from typing import Any

from .config import DATABASE_PATH
from .logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Column definitions
# ---------------------------------------------------------------------------
# The order here determines INSERT column order.  Keep in sync with the
# CREATE TABLE statement and the normalize_element return dict.

COLUMNS: tuple[str, ...] = (
    "source",
    "source_record_id",
    "name",
    "alt_name",
    "category",
    "subcategory",
    "description",
    "brand",
    "opening_hours",
    # website
    "website",
    "website_presence",
    # contacts
    "email",
    "phone",
    "whatsapp",
    # social
    "facebook",
    "instagram",
    "twitter",
    # location
    "neighbourhood",
    "address",
    "latitude",
    "longitude",
    "map_link",
    # raw OSM data
    "osm_tags_json",
)

# Columns managed automatically — never set in an upsert.
AUTO_COLUMNS: frozenset[str] = frozenset(
    {"source_record_id", "first_seen_at", "last_seen_at"}
)


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def connect() -> sqlite3.Connection:
    """Open (and return) the SQLite connection, creating the data dir if needed."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    # Enable WAL for better concurrent read/write performance
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS businesses (
    -- Primary identity
    source_record_id    TEXT PRIMARY KEY,
    source              TEXT NOT NULL,
    name                TEXT NOT NULL,
    alt_name            TEXT,
    category            TEXT,
    subcategory         TEXT,
    description         TEXT,
    brand               TEXT,
    opening_hours       TEXT,

    -- Website (OSM-sourced; NOT yet verified)
    website             TEXT,
    website_presence    TEXT NOT NULL DEFAULT 'unknown',

    -- Contacts (as published in OSM)
    email               TEXT,
    phone               TEXT,
    whatsapp            TEXT,

    -- Social media (as published in OSM)
    facebook            TEXT,
    instagram           TEXT,
    twitter             TEXT,

    -- Location
    neighbourhood       TEXT,
    address             TEXT,
    latitude            REAL,
    longitude           REAL,
    map_link            TEXT,

    -- Raw provenance
    osm_tags_json       TEXT,

    -- Timestamps (UTC)
    first_seen_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    last_seen_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
"""

_BASE_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_biz_name         ON businesses(name);
CREATE INDEX IF NOT EXISTS idx_biz_category     ON businesses(category);
"""


def initialize_database() -> None:
    """
    Create the database schema if it does not already exist.
    Also migrates older schemas to the current column set.
    """
    log.info("Initialising database at %s", DATABASE_PATH)
    with connect() as conn:
        # Step 1: create table if new (safe for both new and existing DBs)
        conn.executescript(_CREATE_TABLE_SQL)
        # Step 2: add any missing columns to existing tables
        _migrate(conn)
        # Step 3: create indexes (all reference columns that now definitely exist)
        conn.executescript(_BASE_INDEXES_SQL)
        conn.executescript("""
            CREATE INDEX IF NOT EXISTS idx_biz_neighbourhood ON businesses(neighbourhood);
            CREATE INDEX IF NOT EXISTS idx_biz_website      ON businesses(website);
            CREATE INDEX IF NOT EXISTS idx_biz_source       ON businesses(source);
        """)
    log.info("Database ready.")


def _migrate(conn: sqlite3.Connection) -> None:
    """
    Add any columns that are missing from the businesses table
    (forward-compatible, additive-only migration).
    """
    # Get existing columns
    existing = {
        row[1]
        for row in conn.execute("PRAGMA table_info(businesses)").fetchall()
    }

    # All columns that should exist in the current schema
    desired_columns: dict[str, str] = {
        # Phase 1 additions
        "alt_name":              "TEXT",
        "description":           "TEXT",
        "brand":                 "TEXT",
        "opening_hours":         "TEXT",
        "facebook":              "TEXT",
        "instagram":             "TEXT",
        "twitter":               "TEXT",
        "neighbourhood":         "TEXT",
        "map_link":              "TEXT",
        # Phase 3 — website verification + audit
        "website_status":        "TEXT",
        "verified_url":          "TEXT",
        "https":                 "INTEGER",   # 0/1 boolean
        "http_status":           "INTEGER",
        "website_error":         "TEXT",
        "website_checked_at":    "TEXT",
        "audit_score":           "INTEGER",
        "audit_quality_label":   "TEXT",
        "audit_mobile_friendly": "INTEGER",
        "audit_has_contact":     "INTEGER",
        "audit_has_cta":         "INTEGER",
        "audit_findings_json":   "TEXT",
        "audit_recommendations": "TEXT",
        "audit_at":              "TEXT",
    }

    for col, col_type in desired_columns.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE businesses ADD COLUMN {col} {col_type}")
            log.info("Migration: added column '%s' to businesses table.", col)

    # Ensure new indexes exist (CREATE INDEX IF NOT EXISTS is idempotent)
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_biz_neighbourhood ON businesses(neighbourhood);
        CREATE INDEX IF NOT EXISTS idx_biz_website      ON businesses(website);
        CREATE INDEX IF NOT EXISTS idx_biz_source       ON businesses(source);
    """)


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------

def upsert_business(record: dict[str, Any], conn: sqlite3.Connection | None = None) -> None:
    """
    Insert or update a single business record.

    If *conn* is provided, uses it (for batch operations).
    Otherwise opens and closes its own connection.

    On conflict (same source_record_id):
      - Updates all mutable columns.
      - Preserves first_seen_at.
      - Updates last_seen_at to now.
    """
    columns_str = ", ".join(COLUMNS)
    placeholders = ", ".join("?" for _ in COLUMNS)
    updates = ", ".join(
        f"{c}=excluded.{c}"
        for c in COLUMNS
        if c not in AUTO_COLUMNS
    )
    values = [record.get(c) for c in COLUMNS]

    sql = (
        f"INSERT INTO businesses ({columns_str}) VALUES ({placeholders}) "
        f"ON CONFLICT(source_record_id) DO UPDATE SET {updates}, "
        f"last_seen_at=strftime('%Y-%m-%dT%H:%M:%SZ','now')"
    )

    if conn is not None:
        conn.execute(sql, values)
    else:
        with connect() as _conn:
            _conn.execute(sql, values)


def upsert_many(records: list[dict[str, Any]]) -> int:
    """
    Upsert a list of records in a single transaction.
    Returns the number of records successfully upserted.
    """
    if not records:
        return 0

    columns_str = ", ".join(COLUMNS)
    placeholders = ", ".join("?" for _ in COLUMNS)
    updates = ", ".join(
        f"{c}=excluded.{c}"
        for c in COLUMNS
        if c not in AUTO_COLUMNS
    )
    sql = (
        f"INSERT INTO businesses ({columns_str}) VALUES ({placeholders}) "
        f"ON CONFLICT(source_record_id) DO UPDATE SET {updates}, "
        f"last_seen_at=strftime('%Y-%m-%dT%H:%M:%SZ','now')"
    )

    rows = [[r.get(c) for c in COLUMNS] for r in records]
    with connect() as conn:
        conn.executemany(sql, rows)

    log.info("Upserted %d records.", len(records))
    return len(records)


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def count_businesses() -> int:
    """Return the total number of businesses in the database."""
    with connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM businesses").fetchone()[0]


def get_stats() -> dict[str, Any]:
    """Return a summary statistics dict."""
    with connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM businesses").fetchone()[0]
        by_category = conn.execute(
            "SELECT category, COUNT(*) AS n FROM businesses GROUP BY category ORDER BY n DESC"
        ).fetchall()
        by_neighbourhood = conn.execute(
            "SELECT neighbourhood, COUNT(*) AS n FROM businesses "
            "WHERE neighbourhood IS NOT NULL "
            "GROUP BY neighbourhood ORDER BY n DESC LIMIT 20"
        ).fetchall()
        with_website = conn.execute(
            "SELECT COUNT(*) FROM businesses WHERE website IS NOT NULL"
        ).fetchone()[0]
        with_phone = conn.execute(
            "SELECT COUNT(*) FROM businesses WHERE phone IS NOT NULL"
        ).fetchone()[0]
        with_email = conn.execute(
            "SELECT COUNT(*) FROM businesses WHERE email IS NOT NULL"
        ).fetchone()[0]

    return {
        "total": total,
        "with_website": with_website,
        "without_website": total - with_website,
        "with_phone": with_phone,
        "with_email": with_email,
        "by_category": [dict(r) for r in by_category],
        "by_neighbourhood": [dict(r) for r in by_neighbourhood],
    }


# ---------------------------------------------------------------------------
# Website check update
# ---------------------------------------------------------------------------

def update_website_check(result: dict[str, Any]) -> None:
    """
    Store website verification + audit results back into the businesses table.
    *result* must contain 'source_record_id' and the audit fields.
    """
    fields = [
        "website_status", "verified_url", "https", "http_status",
        "website_error", "website_checked_at", "audit_score",
        "audit_quality_label", "audit_mobile_friendly", "audit_has_contact",
        "audit_has_cta", "audit_findings_json", "audit_recommendations", "audit_at",
    ]
    updates = ", ".join(f"{f}=?" for f in fields)
    values  = [result.get(f) for f in fields]
    values.append(result["source_record_id"])

    with connect() as conn:
        conn.execute(
            f"UPDATE businesses SET {updates} WHERE source_record_id=?",
            values,
        )


def get_businesses_for_website_check(limit: int = 500) -> list[dict[str, Any]]:
    """
    Return businesses that have a website URL but haven't been checked yet,
    plus businesses without any website at all (for NOT_FOUND tracking).
    Returns up to *limit* records.
    """
    with connect() as conn:
        # First: businesses with a website URL that haven't been checked
        with_url = conn.execute(
            "SELECT * FROM businesses "
            "WHERE website IS NOT NULL AND website_status IS NULL "
            "ORDER BY RANDOM() LIMIT ?",
            (limit,),
        ).fetchall()

        remaining = limit - len(with_url)
        if remaining <= 0:
            return [dict(r) for r in with_url]

        # Second: businesses without any website URL (track as UNKNOWN → NOT_FOUND)
        without_url = conn.execute(
            "SELECT * FROM businesses "
            "WHERE website IS NULL AND website_status IS NULL "
            "ORDER BY RANDOM() LIMIT ?",
            (remaining,),
        ).fetchall()

    return [dict(r) for r in with_url] + [dict(r) for r in without_url]


def get_qualified_prospects(
    min_score: int = 30,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """
    Return businesses that are qualified prospects, sorted by lead_score DESC.
    These are businesses with website issues OR strong software/analytics needs.
    """
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM businesses
            WHERE (
                website_status IN ('WEBSITE_NOT_FOUND_AFTER_CHECKS','WEBSITE_UNREACHABLE')
                OR website_presence = 'not_listed_in_osm'
                OR audit_quality_label IN ('POOR','WEAK','FAIR')
                OR (website IS NULL AND website_status IS NULL)
            )
            AND name IS NOT NULL
            ORDER BY
                CASE website_status
                    WHEN 'WEBSITE_NOT_FOUND_AFTER_CHECKS' THEN 1
                    WHEN 'WEBSITE_UNREACHABLE' THEN 2
                    ELSE 3
                END,
                CASE audit_quality_label
                    WHEN 'POOR' THEN 1
                    WHEN 'WEAK' THEN 2
                    WHEN 'FAIR' THEN 3
                    ELSE 4
                END,
                CASE WHEN phone IS NOT NULL THEN 0 ELSE 1 END,
                CASE WHEN email IS NOT NULL THEN 0 ELSE 1 END
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]

def export_csv(output_path: str = "exports/businesses.csv") -> int:
    """
    Export all businesses to a UTF-8-with-BOM CSV (Excel-safe).
    Returns the number of rows exported.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM businesses ORDER BY name COLLATE NOCASE"
        ).fetchall()

    if not rows:
        log.warning("No businesses in the database — nothing to export.")
        return 0

    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows([dict(r) for r in rows])

    log.info("Exported %d businesses to %s", len(rows), path)
    return len(rows)
