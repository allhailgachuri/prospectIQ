"""
Overpass API client for ProspectIQ.

Fetches named business elements from OpenStreetMap using the Overpass API.
Implements:
  - Automatic fallback across multiple API mirrors
  - Exponential backoff with jitter on transient errors
  - Detection of Overpass-specific partial/error responses
  - Progress logging
"""
import time
import random
from typing import Any

import requests

from .config import ALL_OVERPASS_ENDPOINTS, USER_AGENT
from .logger import get_logger

log = get_logger(__name__)

# OSM tag keys that indicate a named business / commercial place.
# Used both to build the query and to determine category priority.
BUSINESS_TAGS: tuple[str, ...] = (
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

# Overpass QL timeout (seconds) — the API enforces this server-side.
OVERPASS_TIMEOUT: int = 90

# requests connect / read timeouts (seconds)
HTTP_CONNECT_TIMEOUT: int = 15
HTTP_READ_TIMEOUT: int = 130  # slightly more than the Overpass server timeout


def build_query(bbox: tuple[float, float, float, float]) -> str:
    """
    Build an Overpass QL query for all named business elements in *bbox*.

    bbox: (south, west, north, east) in decimal degrees.

    Returns a full Overpass QL query string.
    """
    south, west, north, east = bbox
    # Use a union of nwr queries, one per business tag key.
    # nwr = node + way + relation (all element types).
    # ["name"] ensures we only get named elements.
    selectors = "\n".join(
        f'  nwr["name"]["{key}"]({south},{west},{north},{east});'
        for key in BUSINESS_TAGS
        # Avoid duplicate selectors for tag keys that are also in the base list
        # (restaurant, hotel, clinic are subtypes of amenity but queried separately
        # to ensure we don't miss them if the amenity tag is absent).
    )
    query = (
        f"[out:json][timeout:{OVERPASS_TIMEOUT}];\n"
        f"(\n{selectors}\n);\n"
        f"out center tags;"
    )
    log.debug("Built Overpass query:\n%s", query)
    return query


def _try_fetch(
    endpoint: str,
    query: str,
    attempt: int,
) -> list[dict[str, Any]]:
    """
    Attempt a single POST to *endpoint*.  Returns elements list on success.
    Raises requests.RequestException or ValueError on failure.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    log.debug("POST %s (attempt %d)", endpoint, attempt + 1)
    response = requests.post(
        endpoint,
        data={"data": query},
        headers=headers,
        timeout=(HTTP_CONNECT_TIMEOUT, HTTP_READ_TIMEOUT),
    )
    response.raise_for_status()

    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError(f"Non-JSON response from {endpoint}: {exc}") from exc

    # Detect Overpass-level warnings / partial results
    remark = payload.get("remark", "")
    if remark:
        log.warning("Overpass remark from %s: %s", endpoint, remark)

    if "elements" not in payload:
        raise ValueError(
            f"Overpass response from {endpoint} had no 'elements' key. "
            f"Keys present: {list(payload.keys())}"
        )

    elements = payload["elements"]
    log.info(
        "Received %d elements from %s", len(elements), endpoint
    )
    return elements


def fetch_business_elements(
    bbox: tuple[float, float, float, float],
    retries: int = 3,
) -> list[dict[str, Any]]:
    """
    Fetch all named business elements for *bbox* from the Overpass API.

    Tries ALL_OVERPASS_ENDPOINTS in sequence.  For each endpoint, retries
    up to *retries* times with exponential backoff + jitter before moving
    to the next mirror.

    Raises RuntimeError if all endpoints and retries are exhausted.
    """
    query = build_query(bbox)
    last_error: Exception | None = None

    for endpoint in ALL_OVERPASS_ENDPOINTS:
        for attempt in range(retries):
            try:
                return _try_fetch(endpoint, query, attempt)
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                log.warning(
                    "Overpass request failed [endpoint=%s, attempt=%d/%d]: %s",
                    endpoint, attempt + 1, retries, exc,
                )
                if attempt < retries - 1:
                    # Exponential backoff + small random jitter to avoid thundering herd
                    wait = (2 ** attempt) * 3 + random.uniform(0, 1)
                    log.info("Waiting %.1fs before retry...", wait)
                    time.sleep(wait)
        log.warning("All %d attempts exhausted for %s, trying next mirror.", retries, endpoint)

    raise RuntimeError(
        f"All Overpass endpoints failed after {retries} attempts each. "
        f"Last error: {last_error}"
    )
