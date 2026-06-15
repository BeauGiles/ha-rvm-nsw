"""API helpers for Return and Earn."""
from __future__ import annotations

import math
import logging

import aiohttp

from .const import (
    API_DETAIL_URL,
    API_HEADERS,
    API_LOCATIONS_URL,
    NEARBY_RESULTS,
    NOMINATIM_HEADERS,
    NOMINATIM_URL,
)

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TOMRA API
# ---------------------------------------------------------------------------

async def fetch_all_locations() -> list[dict]:
    """Fetch all NSW RVM locations, filtered to automated machines (ACP) only.

    Excludes:
    - category DEPOT (staffed drop-off depots)
    - locationType ACC (staffed Return and Earn Centres)
    - locationType APS (automated parcel stations / other non-self-service)
    Only category=RVM + locationType=ACP are self-service automated machines.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(
            API_LOCATIONS_URL,
            headers=API_HEADERS,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                raise aiohttp.ClientError(f"HTTP {resp.status}")
            payload = await resp.json(content_type=None)
            all_locations = payload.get("data", [])
            return [
                loc for loc in all_locations
                if loc.get("attributes", {}).get("category") == "RVM"
                and loc.get("attributes", {}).get("locationType") == "ACP"
            ]


async def fetch_location_detail(uuid: str) -> dict | None:
    """Fetch a single location's detail including live status. Returns None on failure."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                API_DETAIL_URL.format(uuid=uuid.strip()),
                headers=API_HEADERS,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    return await resp.json(content_type=None)
                _LOGGER.debug("Location detail returned HTTP %s for %s", resp.status, uuid)
    except Exception as err:
        _LOGGER.debug("Error fetching location detail for %s: %s", uuid, err)
    return None


# ---------------------------------------------------------------------------
# Nominatim geocoding
# ---------------------------------------------------------------------------

async def geocode_address(address: str) -> tuple[float, float] | None:
    """
    Geocode a free-text address using Nominatim, restricted to Australia.
    Returns (lat, lon) or None if nothing found.
    """
    params = {
        "q": address,
        "format": "json",
        "countrycodes": "AU",
        "limit": 1,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                NOMINATIM_URL,
                params=params,
                headers=NOMINATIM_HEADERS,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return None
                results = await resp.json(content_type=None)
                if results:
                    return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as err:
        _LOGGER.debug("Nominatim geocoding failed for %r: %s", address, err)
    return None


# ---------------------------------------------------------------------------
# Location list helpers
# ---------------------------------------------------------------------------

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def locations_sorted_by_distance(
    locations: list[dict], lat: float, lon: float, limit: int = NEARBY_RESULTS
) -> list[dict]:
    """Return up to `limit` locations sorted by distance from (lat, lon)."""
    scored = []
    for loc in locations:
        a = loc.get("attributes", {})
        loclat = a.get("latitude")
        loclon = a.get("longitude")
        if loclat is None or loclon is None:
            continue
        scored.append((haversine_km(lat, lon, loclat, loclon), loc))
    scored.sort(key=lambda x: x[0])
    return [loc for _, loc in scored[:limit]]


def locations_sorted_alphabetically(locations: list[dict]) -> list[dict]:
    """Return all locations sorted by name."""
    return sorted(locations, key=lambda l: l.get("attributes", {}).get("name", "").lower())


def build_choices(locations: list[dict], ref_lat: float | None = None, ref_lon: float | None = None) -> dict[str, str]:
    """
    Build a {uuid: label} dict for a vol.In selector.
    If ref coords are provided, appends distance to each label.
    """
    choices = {}
    for loc in locations:
        uuid = loc["id"]
        a = loc.get("attributes", {})
        name = a.get("name", uuid)
        address = a.get("address", "")
        city = a.get("city", "")

        if ref_lat is not None and ref_lon is not None:
            loclat = a.get("latitude")
            loclon = a.get("longitude")
            if loclat is not None and loclon is not None:
                dist = haversine_km(ref_lat, ref_lon, loclat, loclon)
                label = f"{name} — {address}, {city} ({dist:.1f} km)"
            else:
                label = f"{name} — {address}, {city}"
        else:
            label = f"{name} — {address}, {city}"

        choices[uuid] = label
    return choices


def name_from_location_list(locations: list[dict], uuid: str) -> str:
    """Look up a location name from the full list by UUID."""
    for loc in locations:
        if loc["id"] == uuid:
            return loc.get("attributes", {}).get("name", uuid)
    return uuid


def ensure_uuid_in_choices(
    choices: dict[str, str], uuid: str, locations: list[dict]
) -> dict[str, str]:
    """Make sure a UUID is present in choices even if it's outside the nearby limit."""
    if uuid and uuid not in choices:
        match = next((l for l in locations if l["id"] == uuid), None)
        if match:
            a = match.get("attributes", {})
            choices[uuid] = f"{a.get('name', uuid)} — {a.get('address', '')}, {a.get('city', '')}"
    return choices
