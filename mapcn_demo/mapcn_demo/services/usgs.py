"""The USGS earthquake catalogue, trimmed for the browser.

Two queries against the same FDSN endpoint: the historical catalogue for
Venezuela, which travels to the browser once and is then filtered there, and
the last thirty days, which is polled while the live switch is on.

The raw response carries about four times the data the map needs, so features
are cut down to seven properties before they leave the backend. Time stays in
milliseconds because the time slider filters on it with a MapLibre expression,
which cannot parse a date.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, TypedDict

import httpx

from .cache import TTLCache

logger = logging.getLogger("mapcn_demo.services")

FDSN_QUERY_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

#: (minlon, minlat, maxlon, maxlat) around Venezuela.
VENEZUELA_BBOX = (-74.0, 0.5, -59.0, 13.0)

CATALOG_TTL_S = 600
LIVE_TTL_S = 60
RECENT_MS = 24 * 60 * 60 * 1000

ATTRIBUTION = "USGS Earthquake Hazards Program"

CACHE = TTLCache()

EMPTY_COLLECTION: dict[str, Any] = {"type": "FeatureCollection", "features": []}


class SeismicCatalog(TypedDict):
    """What a page receives, whether the service answered or not."""

    features: dict
    count: int
    fetched_at: str
    source: Literal["usgs"]
    min_magnitude: float
    start: str
    end: str | None
    error: str | None


def _now_ms() -> int:
    return int(datetime.now(tz=timezone.utc).timestamp() * 1000)


def _iso_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def _trim(
    feature: dict[str, Any], now_ms: int, mark_recent: bool
) -> dict[str, Any] | None:
    """Cut one USGS feature down to what the map draws.

    Returns None for an event without a magnitude: the radius and the colour
    of every layer are driven by it, so it has nothing to draw.

    Three fields the raw response carries are left behind: the event page url,
    which is the id in a template; the feature-level id, which repeats
    ``properties.id``, the one ``promote_id`` promotes; and ``recent`` outside
    the live feed. Together they were a third of what crossed the wire.
    """
    properties = feature.get("properties") or {}
    magnitude = properties.get("mag")
    if magnitude is None:
        return None

    coordinates = (feature.get("geometry") or {}).get("coordinates") or []
    if len(coordinates) < 2:
        return None

    longitude, latitude = coordinates[0], coordinates[1]
    depth = coordinates[2] if len(coordinates) > 2 else None
    time_ms = int(properties.get("time") or 0)

    trimmed: dict[str, Any] = {
        "id": feature.get("id"),
        "mag": round(float(magnitude), 2),
        "magType": properties.get("magType"),
        "depth": round(float(depth), 1) if depth is not None else 0.0,
        "time": time_ms,
        "place": properties.get("place"),
    }
    if depth is None:
        trimmed["depth_unknown"] = True
    # Only the live feed rings the last day; in the history the flag would be
    # false 3500 times over (Delta 2026-09-catalog-payload).
    if mark_recent:
        trimmed["recent"] = now_ms - time_ms < RECENT_MS

    return {
        "type": "Feature",
        "properties": trimmed,
        "geometry": {
            "type": "Point",
            "coordinates": [round(float(longitude), 4), round(float(latitude), 4)],
        },
    }


def _collection(
    payload: dict[str, Any], now_ms: int, mark_recent: bool
) -> dict[str, Any]:
    features = [
        trimmed
        for feature in payload.get("features") or []
        if (trimmed := _trim(feature, now_ms, mark_recent)) is not None
    ]
    return {"type": "FeatureCollection", "features": features}


async def _query(
    params: dict[str, Any],
    *,
    cache_key: str,
    ttl_s: float,
    timeout: float,
    mark_recent: bool,
    now_ms: int | None,
    description: str,
) -> tuple[dict[str, Any], str | None]:
    """Run one FDSN query, cache it, and never raise.

    On failure the last good answer is returned with an error message beside
    it, so a page that already showed the catalogue keeps showing it.
    """
    cached = CACHE.get(cache_key)
    if cached is not None:
        return cached, None

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(FDSN_QUERY_URL, params=params)
        if response.status_code != 200:
            raise RuntimeError(f"status {response.status_code}")
        payload = response.json()
    except Exception as error:  # noqa: BLE001 - the page must still render
        logger.warning("usgs: %s failed (%s)", description, error)
        last_good = CACHE.get(f"{cache_key}:last-good")
        return (
            last_good if last_good is not None else dict(EMPTY_COLLECTION),
            f"Could not read the USGS catalogue ({description})",
        )

    collection = _collection(payload, now_ms or _now_ms(), mark_recent)
    CACHE.set(cache_key, collection, ttl_s)
    # Kept well past the query itself: it is what a failure falls back to.
    CACHE.set(f"{cache_key}:last-good", collection, ttl_s * 100)
    return collection, None


async def fetch_catalog(
    *,
    min_magnitude: float = 4.5,
    start: str = "1900-01-01",
    end: str | None = None,
    bbox: tuple[float, float, float, float] = VENEZUELA_BBOX,
    timeout: float = 15.0,
    now_ms: int | None = None,
) -> SeismicCatalog:
    """Read the historical catalogue for the given box.

    The whole catalogue travels to the browser once; the time, magnitude and
    depth filters then run there, which is why this is cached for ten minutes
    rather than queried per interaction. It also has to fit in 400 KB, and
    the websocket of Reflex negotiates no compression, so the default asks for
    the magnitude from which this catalogue is complete rather than for
    everything it holds.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    params: dict[str, Any] = {
        "format": "geojson",
        "minlongitude": min_lon,
        "maxlongitude": max_lon,
        "minlatitude": min_lat,
        "maxlatitude": max_lat,
        "minmagnitude": min_magnitude,
        "starttime": start,
        "orderby": "time",
        "limit": 20000,
    }
    if end:
        params["endtime"] = end

    collection, error = await _query(
        params,
        cache_key=f"usgs:catalog:{min_magnitude}:{start}:{end}:{bbox}",
        ttl_s=CATALOG_TTL_S,
        timeout=timeout,
        mark_recent=False,
        now_ms=now_ms,
        description="historical catalogue",
    )

    return {
        "features": collection,
        "count": len(collection["features"]),
        "fetched_at": _iso_now(),
        "source": "usgs",
        "min_magnitude": min_magnitude,
        "start": start,
        "end": end,
        "error": error,
    }


async def fetch_live(
    *,
    days: int = 30,
    min_magnitude: float = 2.5,
    bbox: tuple[float, float, float, float] = VENEZUELA_BBOX,
    timeout: float = 15.0,
    now_ms: int | None = None,
) -> SeismicCatalog:
    """Read the recent events for the given box.

    Deliberately the same FDSN query rather than one of the global feeds: the
    worldwide month feed is several megabytes, and this box is a few dozen
    kilobytes.
    """
    reference = datetime.fromtimestamp((now_ms or _now_ms()) / 1000, tz=timezone.utc)
    start = (reference - timedelta(days=days)).date().isoformat()
    end = reference.date().isoformat()

    min_lon, min_lat, max_lon, max_lat = bbox
    params: dict[str, Any] = {
        "format": "geojson",
        "minlongitude": min_lon,
        "maxlongitude": max_lon,
        "minlatitude": min_lat,
        "maxlatitude": max_lat,
        "minmagnitude": min_magnitude,
        "starttime": start,
        "endtime": end,
        "orderby": "time",
        "limit": 2000,
    }

    collection, error = await _query(
        params,
        cache_key=f"usgs:live:{days}:{min_magnitude}:{bbox}",
        ttl_s=LIVE_TTL_S,
        timeout=timeout,
        mark_recent=True,
        now_ms=now_ms,
        description="live feed",
    )

    return {
        "features": collection,
        "count": len(collection["features"]),
        "fetched_at": _iso_now(),
        "source": "usgs",
        "min_magnitude": min_magnitude,
        "start": start,
        "end": end,
        "error": error,
    }
