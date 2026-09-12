"""Driving times and routes from the public OSRM demo server.

Two endpoints, both read-only and both polite: a table of durations from one
capital to the others, and the geometry of a single route once the user picks
a row. The demo server asks not to be hammered, so every answer is cached for
an hour and a matrix is never requested with more than 25 destinations at a
time.

Nothing here raises. A refusal, a timeout or a hole in the matrix all come
back as data, because the table has to render either way.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, TypedDict

import httpx

from .cache import TTLCache

logger = logging.getLogger("mapcn_demo.services")

OSRM_HOST = "https://router.project-osrm.org"

#: Destinations per table request. The demo server rejects much longer lists.
MAX_DESTINATIONS = 25

TABLE_TTL_S = 3600
ROUTE_TTL_S = 3600

ATTRIBUTION = "Rutas: OSRM · datos OpenStreetMap (ODbL)"

CACHE = TTLCache()

Coordinate = tuple[float, float]


class TravelMatrix(TypedDict):
    """Durations and distances from one origin, in destination order."""

    origin: Coordinate
    durations: list[float | None]  # seconds
    distances: list[float | None]  # metres
    fetched_at: str
    error: str | None


class RouteResult(TypedDict):
    """One drawn route, or the reason there is none."""

    coordinates: list[list[float]]  # [lng, lat]
    duration: float
    distance: float
    error: str | None


def _iso_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def _path(coordinates: list[Coordinate]) -> str:
    """The ``lng,lat;lng,lat`` path segment OSRM addresses places with."""
    return ";".join(f"{lng:.6f},{lat:.6f}" for lng, lat in coordinates)


def _digest(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:10]


def _batches(destinations: list[Coordinate], size: int) -> list[list[Coordinate]]:
    return [
        destinations[start : start + size]
        for start in range(0, len(destinations), size)
    ]


async def _get(
    url: str, params: dict[str, Any], timeout: float, description: str
) -> tuple[dict[str, Any] | None, str | None]:
    """One OSRM call that answers with data or with a reason, never both."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params)
        if response.status_code != 200:
            raise RuntimeError(f"status {response.status_code}")
        payload = response.json()
        code = payload.get("code")
        if code != "Ok":
            raise RuntimeError(f"OSRM answered {code}")
    except Exception as error:  # noqa: BLE001 - the table must still render
        logger.warning("osrm: %s failed (%s)", description, error)
        return None, f"Could not read the {description} ({error})"
    return payload, None


def _cells(rows: Any, count: int) -> list[float | None]:
    """The one source row, without the column of the origin itself.

    OSRM answers a one-row matrix because the request pins ``sources=0``, and
    that row starts with the origin measured against itself.
    """
    row = rows[0][1:] if isinstance(rows, list) and rows else []
    cells: list[float | None] = [
        float(value) if value is not None else None for value in row[:count]
    ]
    return cells + [None] * (count - len(cells))


async def table(
    origin: Coordinate,
    destinations: list[Coordinate],
    *,
    profile: str = "driving",
    timeout: float = 15.0,
) -> TravelMatrix:
    """Driving durations and distances from ``origin`` to each destination.

    A destination OSRM cannot reach by road, an island for instance, keeps its
    ``None``: the row is still shown, without a time.
    """
    key = (
        f"osrm:table:{profile}:{_path([origin])}"
        f":{_digest(_path(destinations))}:{len(destinations)}"
    )
    cached = CACHE.get(key)
    if cached is not None:
        return cached

    durations: list[float | None] = []
    distances: list[float | None] = []
    error: str | None = None

    for batch in _batches(destinations, MAX_DESTINATIONS):
        payload, failure = await _get(
            f"{OSRM_HOST}/table/v1/{profile}/{_path([origin, *batch])}",
            {"sources": 0, "annotations": "duration,distance"},
            timeout,
            "travel-time matrix",
        )
        if payload is None:
            error = error or failure
            durations += [None] * len(batch)
            distances += [None] * len(batch)
            continue
        durations += _cells(payload.get("durations"), len(batch))
        distances += _cells(payload.get("distances"), len(batch))

    matrix: TravelMatrix = {
        "origin": origin,
        "durations": durations,
        "distances": distances,
        "fetched_at": _iso_now(),
        "error": error,
    }
    # A failed matrix is not worth an hour of cache: the next click retries.
    if error is None:
        CACHE.set(key, matrix, TABLE_TTL_S)
    return matrix


async def route(
    coordinates: list[Coordinate],
    *,
    profile: str = "driving",
    timeout: float = 15.0,
) -> RouteResult:
    """The full geometry of the road route through ``coordinates``."""
    key = f"osrm:route:{profile}:{_digest(_path(coordinates))}"
    cached = CACHE.get(key)
    if cached is not None:
        return cached

    payload, failure = await _get(
        f"{OSRM_HOST}/route/v1/{profile}/{_path(coordinates)}",
        {"overview": "full", "geometries": "geojson"},
        timeout,
        "route",
    )
    routes = (payload or {}).get("routes") or []
    if payload is None or not routes:
        return {
            "coordinates": [],
            "duration": 0.0,
            "distance": 0.0,
            "error": failure or "Could not read the route (no route)",
        }

    best = routes[0]
    result: RouteResult = {
        "coordinates": [
            [float(lng), float(lat)]
            for lng, lat in (best.get("geometry") or {}).get("coordinates") or []
        ],
        "duration": float(best.get("duration") or 0.0),
        "distance": float(best.get("distance") or 0.0),
        "error": None,
    }
    CACHE.set(key, result, ROUTE_TTL_S)
    return result
