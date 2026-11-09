"""
Reverse geocoding for ProspectIQ.

Uses the Nominatim API (OpenStreetMap) to look up neighbourhood / suburb
information for businesses that have coordinates but no OSM address tags.

Rate limit: Nominatim's usage policy requires at most 1 request per second.
We enforce this with a minimum sleep of 1.1 seconds between calls.

Reference: https://nominatim.org/release-docs/develop/api/Reverse/
"""
import time
from typing import Any

import requests

from .config import USER_AGENT
from .logger import get_logger

log = get_logger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
MIN_REQUEST_INTERVAL = 1.1  # seconds — Nominatim 1 req/s policy

_last_call: float = 0.0


def _throttle() -> None:
    """Sleep if needed to respect Nominatim's rate limit."""
    global _last_call
    elapsed = time.monotonic() - _last_call
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    _last_call = time.monotonic()


def reverse_geocode(lat: float, lon: float) -> dict[str, Any]:
    """
    Look up address details for a coordinate pair using Nominatim.

    Returns a dict with keys:
      neighbourhood, suburb, city_district, county, city, postcode,
      display_name, place_id, osm_type, osm_id

    Returns an empty dict on error or if coordinates are invalid.
    """
    if lat is None or lon is None:
        return {}

    _throttle()

    params = {
        "lat":    lat,
        "lon":    lon,
        "format": "jsonv2",
        "zoom":   16,       # neighbourhood level
        "addressdetails": 1,
    }
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en"}

    try:
        resp = requests.get(
            NOMINATIM_URL,
            params=params,
            headers=headers,
            timeout=(10, 20),
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.warning("Reverse geocode failed for (%.5f, %.5f): %s", lat, lon, exc)
        return {}

    address = data.get("address", {})

    # Extract the most useful neighbourhood-level fields
    neighbourhood = (
        address.get("suburb")
        or address.get("neighbourhood")
        or address.get("quarter")
        or address.get("city_district")
        or address.get("county")
        or None
    )

    return {
        "neighbourhood":  neighbourhood,
        "suburb":         address.get("suburb"),
        "city_district":  address.get("city_district"),
        "county":         address.get("county"),
        "city":           address.get("city") or address.get("town"),
        "postcode":       address.get("postcode"),
        "display_name":   data.get("display_name"),
        "place_id":       data.get("place_id"),
        "osm_type":       data.get("osm_type"),
        "osm_id":         data.get("osm_id"),
    }


def enrich_neighbourhood(record: dict[str, Any]) -> dict[str, Any]:
    """
    If *record* has coordinates but no neighbourhood, attempt reverse geocoding.
    Returns the record with neighbourhood filled in (or unchanged if it already has one).
    """
    if record.get("neighbourhood"):
        return record  # already set

    lat = record.get("latitude")
    lon = record.get("longitude")

    if lat is None or lon is None:
        return record

    geo = reverse_geocode(lat, lon)
    if geo.get("neighbourhood"):
        record["neighbourhood"] = geo["neighbourhood"]
        log.debug(
            "Reverse geocoded %s → neighbourhood=%s",
            record.get("source_record_id"), geo["neighbourhood"],
        )

    return record
