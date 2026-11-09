"""
ProspectIQ configuration.

All values can be overridden via environment variables or a .env file.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Nairobi County discovery bounding box
# This is a broad envelope covering Nairobi County.
# south, west, north, east  (decimal degrees)
# NOTE: This is an approximation.  Phase 2 will use a verified county polygon.
# ---------------------------------------------------------------------------
DEFAULT_BBOX: tuple[float, float, float, float] = (-1.45, 36.65, -1.15, 37.10)

# ---------------------------------------------------------------------------
# Overpass API
# ---------------------------------------------------------------------------
OVERPASS_URL: str = os.getenv(
    "OVERPASS_URL", "https://overpass-api.de/api/interpreter"
)

# Comma-separated fallback mirrors tried in order when the primary fails
_raw_mirrors = os.getenv(
    "OVERPASS_MIRRORS",
    "https://overpass.kumi.systems/api/interpreter,"
    "https://overpass.openstreetmap.ru/api/interpreter",
)
OVERPASS_MIRRORS: list[str] = [
    m.strip() for m in _raw_mirrors.split(",") if m.strip()
]

# All endpoints to try: primary first, then mirrors
ALL_OVERPASS_ENDPOINTS: list[str] = [OVERPASS_URL] + [
    m for m in OVERPASS_MIRRORS if m != OVERPASS_URL
]

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
DATABASE_PATH: Path = Path(os.getenv("DATABASE_PATH", "data/prospectiq.db"))

# ---------------------------------------------------------------------------
# HTTP identity
# ---------------------------------------------------------------------------
USER_AGENT: str = os.getenv(
    "USER_AGENT",
    "ProspectIQ/0.2 (Nairobi business research; contact: builtbyrushion@gmail.com)",
)

# ---------------------------------------------------------------------------
# Agency
# ---------------------------------------------------------------------------
AGENCY_NAME: str = "BuiltByRushion"
AGENCY_URL: str = "https://builtbyrushion.vercel.app/"
AGENCY_PORTFOLIO: str = "https://rushionsportfolio.vercel.app/"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE: str = os.getenv("LOG_FILE", "logs/prospectiq.log")
