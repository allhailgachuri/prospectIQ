"""
Unit tests for prospectiq.normalize.

These tests use only in-process logic — no network, no database.
"""
import json
import pytest

# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from prospectiq.normalize import normalize_element, _clean_website, _build_address


# ---------------------------------------------------------------------------
# Fixtures — raw OSM element dicts
# ---------------------------------------------------------------------------

def _node(id_: int, tags: dict, lat: float = -1.28, lon: float = 36.82) -> dict:
    return {"type": "node", "id": id_, "lat": lat, "lon": lon, "tags": tags}


def _way(id_: int, tags: dict, clat: float = -1.28, clon: float = 36.82) -> dict:
    return {"type": "way", "id": id_, "center": {"lat": clat, "lon": clon}, "tags": tags}


# ---------------------------------------------------------------------------
# normalize_element — happy paths
# ---------------------------------------------------------------------------

class TestNormalizeElementHappyPath:
    def test_basic_shop_node(self):
        elem = _node(1001, {"name": "Java House", "shop": "coffee", "phone": "+254722000001"})
        rec = normalize_element(elem)
        assert rec is not None
        assert rec["name"] == "Java House"
        assert rec["source_record_id"] == "node/1001"
        assert rec["source"] == "OpenStreetMap"
        assert rec["category"] == "shop"
        assert rec["subcategory"] == "coffee"
        assert rec["phone"] == "+254722000001"
        assert rec["latitude"] == pytest.approx(-1.28)
        assert rec["longitude"] == pytest.approx(36.82)

    def test_website_is_cleaned(self):
        elem = _node(1002, {"name": "Acme Ltd", "office": "company", "website": "acme.co.ke"})
        rec = normalize_element(elem)
        assert rec["website"] == "https://acme.co.ke"

    def test_website_with_scheme_preserved(self):
        elem = _node(1003, {"name": "Shop", "shop": "general", "website": "https://shop.co.ke"})
        rec = normalize_element(elem)
        assert rec["website"] == "https://shop.co.ke"

    def test_way_uses_center_coords(self):
        elem = _way(2001, {"name": "Big Mall", "amenity": "marketplace"}, clat=-1.30, clon=36.80)
        rec = normalize_element(elem)
        assert rec is not None
        assert rec["latitude"] == pytest.approx(-1.30)
        assert rec["longitude"] == pytest.approx(36.80)
        assert rec["source_record_id"] == "way/2001"

    def test_map_link_generated(self):
        elem = _node(1004, {"name": "Clinic", "healthcare": "clinic"})
        rec = normalize_element(elem)
        assert rec["map_link"] == "https://www.google.com/maps?q=-1.28,36.82"

    def test_address_assembled(self):
        elem = _node(1005, {
            "name": "Office",
            "office": "accountant",
            "addr:housenumber": "14",
            "addr:street": "Kenyatta Ave",
            "addr:suburb": "CBD",
            "addr:city": "Nairobi",
        })
        rec = normalize_element(elem)
        assert rec["address"] == "14, Kenyatta Ave, CBD, Nairobi"

    def test_social_media_extracted(self):
        elem = _node(1006, {
            "name": "Brand",
            "shop": "clothing",
            "contact:facebook": "https://facebook.com/brand",
            "contact:instagram": "https://instagram.com/brand",
        })
        rec = normalize_element(elem)
        assert rec["facebook"] == "https://facebook.com/brand"
        assert rec["instagram"] == "https://instagram.com/brand"

    def test_osm_tags_json_is_valid_json(self):
        elem = _node(1007, {"name": "Test", "amenity": "restaurant", "cuisine": "kenyan"})
        rec = normalize_element(elem)
        parsed = json.loads(rec["osm_tags_json"])
        assert parsed["cuisine"] == "kenyan"

    def test_category_priority_shop_over_amenity(self):
        # shop should win over amenity
        elem = _node(1008, {"name": "Duka", "shop": "general", "amenity": "marketplace"})
        rec = normalize_element(elem)
        assert rec["category"] == "shop"

    def test_website_presence_flag_listed(self):
        elem = _node(1009, {"name": "X", "shop": "x", "website": "https://x.co.ke"})
        rec = normalize_element(elem)
        assert rec["website_presence"] == "listed_in_osm"

    def test_website_presence_flag_not_listed(self):
        elem = _node(1010, {"name": "Y", "shop": "y"})
        rec = normalize_element(elem)
        assert rec["website_presence"] == "not_listed_in_osm"

    def test_description_extracted(self):
        elem = _node(1011, {"name": "Z", "amenity": "bank", "description": "Commercial bank"})
        rec = normalize_element(elem)
        assert rec["description"] == "Commercial bank"

    def test_opening_hours_extracted(self):
        elem = _node(1012, {"name": "Bakery", "shop": "bakery", "opening_hours": "Mo-Fr 08:00-18:00"})
        rec = normalize_element(elem)
        assert rec["opening_hours"] == "Mo-Fr 08:00-18:00"


# ---------------------------------------------------------------------------
# normalize_element — edge cases and filtering
# ---------------------------------------------------------------------------

class TestNormalizeElementFiltering:
    def test_no_name_returns_none(self):
        elem = _node(2001, {"shop": "bakery"})
        assert normalize_element(elem) is None

    def test_empty_name_returns_none(self):
        elem = _node(2002, {"name": "   ", "shop": "bakery"})
        assert normalize_element(elem) is None

    def test_no_id_returns_none(self):
        elem = {"type": "node", "lat": -1.28, "lon": 36.82, "tags": {"name": "Shop"}}
        assert normalize_element(elem) is None

    def test_missing_lat_lon_uses_center(self):
        elem = {"type": "way", "id": 3001, "center": {"lat": -1.29, "lon": 36.81},
                "tags": {"name": "Mall", "amenity": "marketplace"}}
        rec = normalize_element(elem)
        assert rec["latitude"] == pytest.approx(-1.29)

    def test_missing_all_coords_gives_none(self):
        elem = {"type": "way", "id": 3002, "tags": {"name": "NoCoords", "shop": "general"}}
        rec = normalize_element(elem)
        assert rec is not None  # Still valid record
        assert rec["latitude"] is None
        assert rec["longitude"] is None
        assert rec["map_link"] is None

    def test_garbage_website_rejected(self):
        for garbage in ("none", "N/A", "yes", "no", "-", "http://"):
            elem = _node(4000, {"name": "Biz", "shop": "general", "website": garbage})
            rec = normalize_element(elem)
            assert rec["website"] is None, f"Expected None for website={garbage!r}"

    def test_name_from_name_en_fallback(self):
        elem = _node(5001, {"name:en": "English Name", "shop": "general"})
        rec = normalize_element(elem)
        assert rec is not None
        assert rec["name"] == "English Name"


# ---------------------------------------------------------------------------
# _clean_website
# ---------------------------------------------------------------------------

class TestCleanWebsite:
    def test_adds_https_to_bare_domain(self):
        assert _clean_website("example.co.ke") == "https://example.co.ke"

    def test_preserves_https(self):
        assert _clean_website("https://example.co.ke") == "https://example.co.ke"

    def test_preserves_http(self):
        assert _clean_website("http://example.co.ke") == "http://example.co.ke"

    def test_none_input(self):
        assert _clean_website(None) is None

    def test_empty_string(self):
        assert _clean_website("") is None

    def test_garbage_values(self):
        for val in ("none", "N/A", "yes", "no", "true", "false", "---", "..."):
            assert _clean_website(val) is None, f"Expected None for {val!r}"


# ---------------------------------------------------------------------------
# _build_address
# ---------------------------------------------------------------------------

class TestBuildAddress:
    def test_full_address(self):
        tags = {
            "addr:housenumber": "10",
            "addr:street": "Moi Avenue",
            "addr:suburb": "CBD",
            "addr:city": "Nairobi",
        }
        assert _build_address(tags) == "10, Moi Avenue, CBD, Nairobi"

    def test_partial_address(self):
        tags = {"addr:street": "Ngong Road", "addr:city": "Nairobi"}
        assert _build_address(tags) == "Ngong Road, Nairobi"

    def test_empty_tags(self):
        assert _build_address({}) is None

    def test_whitespace_only_parts_excluded(self):
        tags = {"addr:street": "   ", "addr:city": "Nairobi"}
        assert _build_address(tags) == "Nairobi"
