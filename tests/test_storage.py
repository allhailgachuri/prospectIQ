"""
Unit tests for prospectiq.storage.

Uses a temporary in-memory or temp-file SQLite database — no real DB touched.
"""
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Patch DATABASE_PATH before importing storage
import prospectiq.config as _cfg


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    """Redirect DATABASE_PATH to a temp file for every test."""
    db_path = tmp_path / "test_prospectiq.db"
    monkeypatch.setattr(_cfg, "DATABASE_PATH", db_path)
    # Re-import storage so it picks up the patched config
    import importlib
    import prospectiq.storage as storage
    importlib.reload(storage)
    storage.initialize_database()
    return storage


def _make_record(name="Test Biz", source_record_id="node/99", **kwargs):
    base = {
        "source": "OpenStreetMap",
        "source_record_id": source_record_id,
        "name": name,
        "alt_name": None,
        "category": "shop",
        "subcategory": "general",
        "description": None,
        "brand": None,
        "opening_hours": None,
        "website": None,
        "website_presence": "not_listed_in_osm",
        "email": None,
        "phone": None,
        "whatsapp": None,
        "facebook": None,
        "instagram": None,
        "twitter": None,
        "neighbourhood": "Westlands",
        "address": "Test St, Nairobi",
        "latitude": -1.28,
        "longitude": 36.82,
        "map_link": "https://www.google.com/maps?q=-1.28,36.82",
        "osm_tags_json": "{}",
    }
    base.update(kwargs)
    return base


class TestDatabaseInit:
    def test_initialize_creates_table(self, tmp_db):
        # Should not raise and count should be 0
        assert tmp_db.count_businesses() == 0

    def test_initialize_is_idempotent(self, tmp_db):
        # Calling again should not raise
        tmp_db.initialize_database()
        assert tmp_db.count_businesses() == 0


class TestUpsert:
    def test_insert_single_record(self, tmp_db):
        tmp_db.upsert_business(_make_record())
        assert tmp_db.count_businesses() == 1

    def test_upsert_does_not_duplicate(self, tmp_db):
        rec = _make_record()
        tmp_db.upsert_business(rec)
        tmp_db.upsert_business(rec)  # same source_record_id
        assert tmp_db.count_businesses() == 1

    def test_upsert_updates_fields(self, tmp_db):
        tmp_db.upsert_business(_make_record(name="Old Name"))
        tmp_db.upsert_business(_make_record(name="New Name"))
        from prospectiq.storage import connect
        with connect() as conn:
            row = conn.execute("SELECT name FROM businesses WHERE source_record_id='node/99'").fetchone()
        assert row["name"] == "New Name"

    def test_upsert_preserves_first_seen_at(self, tmp_db):
        from prospectiq.storage import connect
        tmp_db.upsert_business(_make_record())
        with connect() as conn:
            row1 = conn.execute("SELECT first_seen_at FROM businesses").fetchone()
        import time; time.sleep(1)
        tmp_db.upsert_business(_make_record(name="Updated"))
        with connect() as conn:
            row2 = conn.execute("SELECT first_seen_at FROM businesses").fetchone()
        assert row1["first_seen_at"] == row2["first_seen_at"]

    def test_upsert_many(self, tmp_db):
        records = [_make_record(f"Biz {i}", f"node/{i}") for i in range(10)]
        n = tmp_db.upsert_many(records)
        assert n == 10
        assert tmp_db.count_businesses() == 10

    def test_upsert_many_deduplication(self, tmp_db):
        records = [_make_record("Same Biz", "node/1")] * 5
        tmp_db.upsert_many(records)
        assert tmp_db.count_businesses() == 1

    def test_upsert_many_empty_list(self, tmp_db):
        assert tmp_db.upsert_many([]) == 0


class TestStats:
    def test_stats_empty_db(self, tmp_db):
        stats = tmp_db.get_stats()
        assert stats["total"] == 0
        assert stats["with_website"] == 0
        assert stats["without_website"] == 0

    def test_stats_with_records(self, tmp_db):
        tmp_db.upsert_business(_make_record("A", "node/1", website="https://a.co.ke"))
        tmp_db.upsert_business(_make_record("B", "node/2"))
        tmp_db.upsert_business(_make_record("C", "node/3", phone="+254700000001"))
        stats = tmp_db.get_stats()
        assert stats["total"] == 3
        assert stats["with_website"] == 1
        assert stats["without_website"] == 2
        assert stats["with_phone"] == 1

    def test_stats_by_category(self, tmp_db):
        tmp_db.upsert_business(_make_record("A", "node/1", category="shop"))
        tmp_db.upsert_business(_make_record("B", "node/2", category="amenity"))
        tmp_db.upsert_business(_make_record("C", "node/3", category="shop"))
        stats = tmp_db.get_stats()
        cats = {r["category"]: r["n"] for r in stats["by_category"]}
        assert cats["shop"] == 2
        assert cats["amenity"] == 1


class TestExportCSV:
    def test_export_empty_db(self, tmp_db, tmp_path):
        out = str(tmp_path / "out.csv")
        n = tmp_db.export_csv(out)
        assert n == 0

    def test_export_creates_file(self, tmp_db, tmp_path):
        tmp_db.upsert_business(_make_record())
        out = str(tmp_path / "out.csv")
        n = tmp_db.export_csv(out)
        assert n == 1
        assert (tmp_path / "out.csv").exists()

    def test_export_csv_content(self, tmp_db, tmp_path):
        import csv as csv_mod
        tmp_db.upsert_business(_make_record("Acme Ltd", "node/42", website="https://acme.co.ke"))
        out = str(tmp_path / "out.csv")
        tmp_db.export_csv(out)
        with open(out, encoding="utf-8-sig") as fh:
            rows = list(csv_mod.DictReader(fh))
        assert len(rows) == 1
        assert rows[0]["name"] == "Acme Ltd"
        assert rows[0]["website"] == "https://acme.co.ke"
