#!/usr/bin/env python
"""Build the Venezuelan fault asset from the GEM global catalogue.

The GEM Global Active Faults database is tens of megabytes and lives behind
Git LFS, so the demo cannot read it at runtime. This script runs once on a
machine with network, clips the catalogue to a box around Venezuela, keeps the
handful of properties the map reads, simplifies the geometry and writes
``mapcn_demo/assets/venezuela_fallas.geojson``, which is committed.

    python scripts/build_faults.py

The output is licensed CC BY-SA 4.0 and must be credited as
"GEM Global Active Faults" wherever it is drawn.

No geospatial library: the clipping is a bounding-box test and the
simplification is Douglas-Peucker over degrees, which is accurate enough for
lines drawn at country scale.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections.abc import Iterator
from typing import Any

import httpx

GEM_FAULTS_URL = (
    "https://raw.githubusercontent.com/GEMScienceTools/gem-global-active-faults"
    "/master/geojson/gem_active_faults_harmonized.geojson"
)

#: (minlon, minlat, maxlon, maxlat): Venezuela plus a margin, so faults that
#: continue into Colombia or the Caribbean are not cut mid-line.
VENEZUELA_FAULT_BBOX = (-76.0, -1.0, -57.0, 15.0)

#: Degrees. About 500 m, well under the width of a fault line on screen.
SIMPLIFY_TOLERANCE = 0.005

#: Everything the map or the tooltip reads; the rest is dropped.
KEEP_PROPERTIES = (
    "name",
    "slip_type",
    "average_dip",
    "net_slip_rate",
    "activity_confidence",
    "catalog_id",
)

DEFAULT_OUTPUT = pathlib.Path("mapcn_demo/assets/venezuela_fallas.geojson")


def iter_points(geometry: dict[str, Any]) -> Iterator[list[float]]:
    """Yield every coordinate pair of a (Multi)LineString."""
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates") or []
    if kind == "LineString":
        yield from coordinates
    elif kind == "MultiLineString":
        for part in coordinates:
            yield from part


def intersects(
    geometry: dict[str, Any], bbox: tuple[float, float, float, float]
) -> bool:
    """True when any point of the geometry falls inside the box.

    A point test rather than a segment test: a fault long enough to cross the
    box without a vertex inside it does not exist at this scale.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    for point in iter_points(geometry):
        if len(point) < 2:
            continue
        longitude, latitude = point[0], point[1]
        if min_lon <= longitude <= max_lon and min_lat <= latitude <= max_lat:
            return True
    return False


def _inside(point: list[float], bbox: tuple[float, float, float, float]) -> bool:
    min_lon, min_lat, max_lon, max_lat = bbox
    return (
        len(point) >= 2
        and min_lon <= point[0] <= max_lon
        and min_lat <= point[1] <= max_lat
    )


def clip_line(
    points: list[list[float]], bbox: tuple[float, float, float, float]
) -> list[list[list[float]]]:
    """Split a line into the runs that fall inside the box.

    Each run keeps the vertex just before it enters and just after it leaves,
    so the drawn line reaches the border instead of stopping short of it. A
    fault that leaves and comes back becomes two runs, which is why the output
    can be a MultiLineString.
    """
    runs: list[list[list[float]]] = []
    current: list[list[float]] = []

    for index, point in enumerate(points):
        if _inside(point, bbox):
            if not current and index > 0:
                current.append(list(points[index - 1]))
            current.append(list(point))
            continue
        if current:
            current.append(list(point))
            runs.append(current)
            current = []

    if current:
        runs.append(current)
    return [run for run in runs if len(run) >= 2]


def _perpendicular_distance(
    point: list[float], start: list[float], end: list[float]
) -> float:
    """Distance from `point` to the segment `start`-`end`, in degrees."""
    x, y = point[0], point[1]
    x1, y1 = start[0], start[1]
    x2, y2 = end[0], end[1]

    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5

    # Project the point onto the segment, clamped to its ends.
    t = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    px, py = x1 + t * dx, y1 + t * dy
    return ((x - px) ** 2 + (y - py) ** 2) ** 0.5


def simplify_line(points: list[list[float]], tolerance: float) -> list[list[float]]:
    """Douglas-Peucker: drop the points that carry no shape.

    Both ends always survive, so a simplified fault still starts and ends where
    the catalogue says it does.
    """
    if len(points) <= 2:
        return [list(point) for point in points]

    first, last = points[0], points[-1]
    index, worst = 0, 0.0
    for i in range(1, len(points) - 1):
        distance = _perpendicular_distance(points[i], first, last)
        if distance > worst:
            index, worst = i, distance

    if worst <= tolerance:
        return [list(first), list(last)]

    left = simplify_line(points[: index + 1], tolerance)
    right = simplify_line(points[index:], tolerance)
    return left[:-1] + right


def clip_and_simplify(
    geometry: dict[str, Any],
    bbox: tuple[float, float, float, float],
    tolerance: float,
) -> dict[str, Any] | None:
    """Clip a (Multi)LineString to the box, simplify it and round it.

    Returns None when nothing of the geometry falls inside the box, and a
    MultiLineString whenever the clipping produced more than one run.
    """
    kind = geometry.get("type")
    if kind == "LineString":
        parts = [geometry.get("coordinates") or []]
    elif kind == "MultiLineString":
        parts = geometry.get("coordinates") or []
    else:
        return None

    runs: list[list[list[float]]] = []
    for part in parts:
        for run in clip_line(part, bbox):
            simplified = simplify_line(run, tolerance)
            rounded = [[round(point[0], 4), round(point[1], 4)] for point in simplified]
            if len(rounded) >= 2:
                runs.append(rounded)

    if not runs:
        return None
    if len(runs) == 1:
        return {"type": "LineString", "coordinates": runs[0]}
    return {"type": "MultiLineString", "coordinates": runs}


def trim_properties(properties: dict[str, Any]) -> dict[str, Any]:
    """Keep only what the layer paints and the tooltip shows."""
    return {key: properties.get(key) for key in KEEP_PROPERTIES}


def build_collection(
    payload: dict[str, Any],
    *,
    bbox: tuple[float, float, float, float] = VENEZUELA_FAULT_BBOX,
    tolerance: float = SIMPLIFY_TOLERANCE,
) -> dict[str, Any]:
    """Clip, trim and simplify the global catalogue."""
    features = []
    for feature in payload.get("features") or []:
        geometry = feature.get("geometry") or {}
        if not intersects(geometry, bbox):
            continue
        simplified = clip_and_simplify(geometry, bbox, tolerance)
        if simplified is None:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": trim_properties(feature.get("properties") or {}),
                "geometry": simplified,
            }
        )
    return {"type": "FeatureCollection", "features": features}


def download(url: str = GEM_FAULTS_URL, timeout: float = 120.0) -> dict[str, Any]:
    """Fetch the global catalogue."""
    response = httpx.get(url, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    return response.json()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=GEM_FAULTS_URL)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--tolerance", type=float, default=SIMPLIFY_TOLERANCE)
    parser.add_argument(
        "--input",
        type=pathlib.Path,
        help="read the catalogue from a local file instead of downloading it",
    )
    args = parser.parse_args(argv)

    if args.input:
        payload = json.loads(args.input.read_text())
    else:
        print(f"downloading {args.url}")
        payload = download(args.url)

    collection = build_collection(payload, tolerance=args.tolerance)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(collection, separators=(",", ":")))

    size_kb = args.output.stat().st_size / 1024
    print(f"{len(collection['features'])} faults -> {args.output} ({size_kb:.0f} KB)")
    if size_kb > 300:
        print(
            "warning: larger than the 300 KB budget; raise --tolerance",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
