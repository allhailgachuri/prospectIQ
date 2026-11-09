"""
Nairobi County tiled discovery.

Splits the Nairobi County envelope into smaller tiles so each Overpass
request is fast and unlikely to time out.  Tiles are processed
sequentially with a small sleep between requests to be respectful of the
public Overpass service.

Nairobi County authoritative boundary (approximate envelope):
  south=-1.445, west=36.645, north=-1.145, east=37.105

The tiles below are hand-crafted 0.05° × 0.05° cells that together cover
the full county envelope.  Any business whose centroid falls outside the
county will have its location noted; Phase 3 will verify coordinates.
"""
import time
from typing import Generator

from .logger import get_logger
from .normalize import normalize_element
from .overpass import fetch_business_elements
from .storage import upsert_many, count_businesses

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Nairobi County bounding box (degrees)
# ---------------------------------------------------------------------------
NAIROBI_SOUTH:  float = -1.445
NAIROBI_WEST:   float = 36.645
NAIROBI_NORTH:  float = -1.145
NAIROBI_EAST:   float = 37.105

# Tile size in degrees (~5 km × ~5 km at Nairobi's latitude)
TILE_SIZE: float = 0.05

# Seconds to sleep between tile requests
INTER_TILE_SLEEP: float = 8.0


def generate_tiles(
    south: float = NAIROBI_SOUTH,
    west:  float = NAIROBI_WEST,
    north: float = NAIROBI_NORTH,
    east:  float = NAIROBI_EAST,
    tile_size: float = TILE_SIZE,
) -> Generator[tuple[float, float, float, float], None, None]:
    """
    Yield (tile_south, tile_west, tile_north, tile_east) tuples covering
    the given envelope.  Tiles are generated row by row, west to east.
    """
    lat = south
    while lat < north:
        tile_north = min(lat + tile_size, north)
        lon = west
        while lon < east:
            tile_east = min(lon + tile_size, east)
            yield (round(lat, 6), round(lon, 6),
                   round(tile_north, 6), round(tile_east, 6))
            lon += tile_size
        lat += tile_size


def count_tiles(
    south: float = NAIROBI_SOUTH,
    west:  float = NAIROBI_WEST,
    north: float = NAIROBI_NORTH,
    east:  float = NAIROBI_EAST,
    tile_size: float = TILE_SIZE,
) -> int:
    """Return the total number of tiles for the given envelope."""
    return sum(1 for _ in generate_tiles(south, west, north, east, tile_size))


def run_full_sweep(
    south: float = NAIROBI_SOUTH,
    west:  float = NAIROBI_WEST,
    north: float = NAIROBI_NORTH,
    east:  float = NAIROBI_EAST,
    tile_size: float = TILE_SIZE,
    sleep: float = INTER_TILE_SLEEP,
    progress_callback=None,
) -> dict:
    """
    Run a full tiled discovery sweep across the Nairobi County envelope.

    Returns a summary dict with totals.
    """
    tiles = list(generate_tiles(south, west, north, east, tile_size))
    total_tiles = len(tiles)
    log.info("Full sweep: %d tiles to process (tile size=%.3f°)", total_tiles, tile_size)

    total_elements = 0
    total_records  = 0
    tile_errors    = 0

    for idx, bbox in enumerate(tiles, 1):
        tile_label = f"Tile {idx}/{total_tiles} {bbox}"
        log.info("Processing %s", tile_label)

        if progress_callback:
            progress_callback(idx, total_tiles, bbox)

        try:
            elements = fetch_business_elements(bbox, retries=3)
        except RuntimeError as exc:
            log.error("Tile %d/%d failed: %s", idx, total_tiles, exc)
            tile_errors += 1
            # Don't abort the whole sweep — skip this tile and continue
            continue

        records = []
        for elem in elements:
            try:
                rec = normalize_element(elem)
                if rec:
                    records.append(rec)
            except Exception as exc:  # noqa: BLE001
                log.warning("Normalisation error on element %s: %s", elem.get("id"), exc)

        upserted = upsert_many(records)
        total_elements += len(elements)
        total_records  += upserted

        log.info(
            "Tile %d/%d: %d elements → %d records stored. DB total: %d",
            idx, total_tiles, len(elements), upserted, count_businesses(),
        )

        # Be polite to the public Overpass service
        if idx < total_tiles:
            time.sleep(sleep)

    summary = {
        "total_tiles":    total_tiles,
        "tile_errors":    tile_errors,
        "total_elements": total_elements,
        "total_records":  total_records,
        "db_total":       count_businesses(),
    }
    log.info("Sweep complete: %s", summary)
    return summary
