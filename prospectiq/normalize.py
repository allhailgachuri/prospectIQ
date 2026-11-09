"""
Normalise raw OSM elements into ProspectIQ business records.

Each record maps directly to a row in the `businesses` table.
"""
import json
import re
from typing import Any

from .logger import get_logger

log = get_logger(__name__)

# Priority order for choosing the primary category from OSM tag keys.
# First match wins.
CATEGORY_PRIORITY: tuple[str, ...] = (
    "shop",
    "amenity",
    "office",
    "craft",
    "healthcare",
    "tourism",
    "leisure",
    "restaurant",
    "hotel",
    "clinic",
)

# Tags that carry an explicit human-readable description of what the place does.
DESCRIPTION_KEYS: tuple[str, ...] = (
    "description",
    "description:en",
    "note",
    "comment",
)

# Social / contact channel keys
SOCIAL_KEYS: dict[str, tuple[str, ...]] = {
    "facebook":  ("contact:facebook", "facebook"),
    "instagram": ("contact:instagram", "instagram"),
    "twitter":   ("contact:twitter", "twitter", "contact:x"),
    "linkedin":  ("contact:linkedin", "linkedin"),
    "youtube":   ("contact:youtube", "youtube"),
}

# Simple regex to reject obviously garbage website values
_GARBAGE_WEBSITE = re.compile(
    r"^(none|n/a|na|no|yes|true|false|-+|\.+|http://\s*|https://\s*)$",
    re.IGNORECASE,
)

# Nairobi neighbourhood names extracted from common OSM suburb/district tags.
# Used for quick sanity checks; not exhaustive.
NAIROBI_NEIGHBOURHOODS: frozenset[str] = frozenset({
    "nairobi cbd", "westlands", "parklands", "kilimani", "kileleshwa",
    "lavington", "karen", "lang'ata", "langata", "south c", "south b",
    "upper hill", "hurlingham", "ngara", "pangani", "eastleigh",
    "industrial area", "embakasi", "donholm", "umoja", "buruburu",
    "kasarani", "roysambu", "ruaraka", "githurai", "kahawa", "zimmerman",
    "gigiri", "runda", "muthaiga", "spring valley", "ruaka",
})


def _first(tags: dict, keys: tuple[str, ...]) -> str | None:
    """Return the first non-empty value from *tags* matching any of *keys*."""
    for key in keys:
        val = tags.get(key, "").strip()
        if val:
            return val
    return None


def _clean_website(raw: str | None) -> str | None:
    """Return a cleaned URL or None if the value looks invalid."""
    if not raw:
        return None
    raw = raw.strip()
    if _GARBAGE_WEBSITE.match(raw):
        log.debug("Rejected garbage website value: %r", raw)
        return None
    # Prepend scheme if missing
    if not re.match(r"^https?://", raw, re.IGNORECASE):
        raw = "https://" + raw
    return raw


def _build_address(tags: dict) -> str | None:
    """Assemble an address string from OSM addr:* tags."""
    parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:suburb"),
        tags.get("addr:city"),
        tags.get("addr:postcode"),
    ]
    return ", ".join(p.strip() for p in parts if p and p.strip()) or None


def _get_neighbourhood(tags: dict) -> str | None:
    """
    Extract neighbourhood / area from OSM tags.
    Returns the most specific available value.
    """
    for key in ("addr:suburb", "addr:neighbourhood", "addr:quarter",
                "addr:district", "addr:city"):
        val = tags.get(key, "").strip()
        if val:
            return val
    return None


def _get_map_link(lat: float | None, lon: float | None) -> str | None:
    """Generate a Google Maps link for the given coordinates."""
    if lat is not None and lon is not None:
        return f"https://www.google.com/maps?q={lat},{lon}"
    return None


def _extract_socials(tags: dict) -> dict[str, str | None]:
    """Extract social media profile URLs from OSM tags."""
    return {
        platform: _first(tags, keys)
        for platform, keys in SOCIAL_KEYS.items()
    }


def normalize_element(element: dict[str, Any]) -> dict[str, Any] | None:
    """
    Normalise a single OSM element dict into a ProspectIQ business record.

    Returns a dict ready for upsert into the `businesses` table, or None
    if the element should be skipped (no name, no valid ID, etc.).
    """
    tags: dict = element.get("tags") or {}

    # ----- Required fields -----
    name = (tags.get("name") or tags.get("name:en") or "").strip()
    if not name:
        return None

    element_id = element.get("id")
    if element_id is None:
        return None

    element_type = element.get("type", "unknown")
    source_record_id = f"{element_type}/{element_id}"

    # ----- Coordinates -----
    lat = element.get("lat")
    lon = element.get("lon")
    if lat is None or lon is None:
        center = element.get("center") or {}
        lat = center.get("lat")
        lon = center.get("lon")

    # ----- Category -----
    category = next(
        (key for key in CATEGORY_PRIORITY if tags.get(key)), None
    )
    subcategory = tags.get(category) if category else None

    # ----- Website -----
    raw_website = _first(tags, ("website", "contact:website", "url"))
    website = _clean_website(raw_website)
    if raw_website and not website:
        log.debug(
            "Discarded invalid website tag for %s: %r", source_record_id, raw_website
        )

    # ----- Address & location -----
    address = _build_address(tags)
    neighbourhood = _get_neighbourhood(tags)
    map_link = _get_map_link(lat, lon)

    # ----- Contacts -----
    email = _first(tags, ("contact:email", "email"))
    phone = _first(tags, ("contact:phone", "phone", "mobile"))
    whatsapp = _first(tags, ("contact:whatsapp", "whatsapp"))

    # ----- Social media -----
    socials = _extract_socials(tags)

    # ----- Enrichment fields -----
    description = _first(tags, DESCRIPTION_KEYS)
    opening_hours = tags.get("opening_hours")
    brand = tags.get("brand") or tags.get("operator")
    alt_name = tags.get("alt_name") or tags.get("short_name")

    # ----- Website presence status (raw OSM signal only) -----
    # This is NOT a verified status — that happens in Phase 3.
    # "listed" = OSM has a website tag; "not_listed_in_osm" = it doesn't.
    # Neither value is proof of whether the business actually has a website.
    website_presence_osm = "listed_in_osm" if website else "not_listed_in_osm"

    record = {
        "source":            "OpenStreetMap",
        "source_record_id":  source_record_id,
        "name":              name,
        "alt_name":          alt_name,
        "category":          category,
        "subcategory":       subcategory,
        "description":       description,
        "brand":             brand,
        "opening_hours":     opening_hours,
        # Website
        "website":           website,
        "website_presence":  website_presence_osm,
        # Contacts
        "email":             email,
        "phone":             phone,
        "whatsapp":          whatsapp,
        # Social media
        "facebook":          socials["facebook"],
        "instagram":         socials["instagram"],
        "twitter":           socials["twitter"],
        # Location
        "neighbourhood":     neighbourhood,
        "address":           address,
        "latitude":          lat,
        "longitude":         lon,
        "map_link":          map_link,
        # Raw OSM data (full provenance)
        "osm_tags_json":     json.dumps(tags, ensure_ascii=False, sort_keys=True),
    }

    log.debug("Normalised element %s → %s", source_record_id, name)
    return record
