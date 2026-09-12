"""Tests for the GEM fault asset and the script that builds it (T-015).

The global catalogue is tens of megabytes behind Git LFS, so the demo ships a
clipped, simplified copy built once by `scripts/build_faults.py`. The pure
parts of that script are tested here with synthetic geometry, where a broken
simplification actually shows, plus one test that validates the committed
asset itself.
"""

from __future__ import annotations

import json
import pathlib

from scripts import build_faults

ASSET = pathlib.Path("mapcn_demo/assets/venezuela_fallas.geojson")

# A line with a redundant midpoint and one real corner.
STRAIGHT = [[-70.0, 8.0], [-69.5, 8.0], [-69.0, 8.0]]
CORNERED = [[-70.0, 8.0], [-69.5, 8.5], [-69.0, 8.0]]


def _feature(coordinates, properties=None, kind="LineString"):
    return {
        "type": "Feature",
        "properties": properties
        or {
            "name": "Boconó",
            "slip_type": "Dextral",
            "average_dip": "(90,,)",
            "net_slip_rate": "(9,7,11)",
            "activity_confidence": 1,
            "catalog_id": "GEM-1",
            "notes": "a long field the map never reads",
            "references": "Audemard 2000",
        },
        "geometry": {"type": kind, "coordinates": coordinates},
    }


def test_REQ_SIS_009_simplify_drops_points_that_carry_no_shape():
    assert build_faults.simplify_line(STRAIGHT, 0.005) == [[-70.0, 8.0], [-69.0, 8.0]]


def test_REQ_SIS_009_simplify_keeps_a_corner_above_the_tolerance():
    assert build_faults.simplify_line(CORNERED, 0.005) == CORNERED


def test_REQ_SIS_009_simplify_always_keeps_both_ends():
    simplified = build_faults.simplify_line(CORNERED, 10.0)
    assert simplified[0] == CORNERED[0]
    assert simplified[-1] == CORNERED[-1]
    assert len(simplified) == 2


def test_REQ_SIS_009_clipping_keeps_the_run_inside_plus_the_crossing_point():
    # The crossing vertex is kept so the line still reaches the border instead
    # of stopping short of it.
    points = [[-90.0, 8.0], [-80.0, 8.0], [-70.0, 8.0], [-69.0, 8.0]]

    runs = build_faults.clip_line(points, build_faults.VENEZUELA_FAULT_BBOX)

    assert runs == [[[-80.0, 8.0], [-70.0, 8.0], [-69.0, 8.0]]]


def test_REQ_SIS_009_clipping_splits_a_line_that_leaves_and_returns():
    points = [[-70.0, 8.0], [-70.0, 30.0], [-69.0, 30.0], [-69.0, 8.0]]

    runs = build_faults.clip_line(points, build_faults.VENEZUELA_FAULT_BBOX)

    assert len(runs) == 2, runs
    assert runs[0][0] == [-70.0, 8.0]
    assert runs[1][-1] == [-69.0, 8.0]


def test_REQ_SIS_009_clipping_a_line_fully_outside_returns_nothing():
    far_away = [[10.0, 45.0], [11.0, 46.0]]
    assert build_faults.clip_line(far_away, build_faults.VENEZUELA_FAULT_BBOX) == []


def test_REQ_SIS_009_a_fault_leaving_the_box_becomes_a_multiline():
    leaving = _feature([[-70.0, 8.0], [-70.0, 30.0], [-69.0, 30.0], [-69.0, 8.0]])

    collection = build_faults.build_collection(
        {"type": "FeatureCollection", "features": [leaving]}
    )

    geometry = collection["features"][0]["geometry"]
    assert geometry["type"] == "MultiLineString"
    assert len(geometry["coordinates"]) == 2


def test_REQ_SIS_009_features_outside_the_box_are_dropped():
    inside = _feature([[-70.0, 8.0], [-69.0, 9.0]])
    outside = _feature([[10.0, 45.0], [11.0, 46.0]])

    collection = build_faults.build_collection(
        {"type": "FeatureCollection", "features": [inside, outside]}
    )

    assert len(collection["features"]) == 1
    assert collection["features"][0]["geometry"]["coordinates"][0] == [-70.0, 8.0]


def test_REQ_SIS_009_a_feature_crossing_the_border_is_kept():
    crossing = _feature([[-80.0, 8.0], [-70.0, 8.0]])

    collection = build_faults.build_collection(
        {"type": "FeatureCollection", "features": [crossing]}
    )

    assert len(collection["features"]) == 1


def test_REQ_SIS_009_only_the_documented_properties_survive():
    collection = build_faults.build_collection(
        {"type": "FeatureCollection", "features": [_feature(CORNERED)]}
    )

    assert set(collection["features"][0]["properties"]) == {
        "name",
        "slip_type",
        "average_dip",
        "net_slip_rate",
        "activity_confidence",
        "catalog_id",
    }


def test_REQ_SIS_009_multiline_geometry_is_simplified_part_by_part():
    collection = build_faults.build_collection(
        {
            "type": "FeatureCollection",
            "features": [_feature([STRAIGHT, CORNERED], kind="MultiLineString")],
        }
    )

    parts = collection["features"][0]["geometry"]["coordinates"]
    assert parts[0] == [[-70.0, 8.0], [-69.0, 8.0]]
    assert parts[1] == CORNERED


def test_REQ_SIS_009_the_committed_asset_is_usable():
    assert ASSET.exists(), "run `python scripts/build_faults.py` once, with network"

    size_kb = ASSET.stat().st_size / 1024
    assert size_kb <= 300, f"{size_kb:.0f} KB is too heavy to ship"

    collection = json.loads(ASSET.read_text())
    features = collection["features"]
    assert len(features) >= 30, len(features)

    min_lon, min_lat, max_lon, max_lat = build_faults.VENEZUELA_FAULT_BBOX
    for feature in features:
        assert feature["properties"]["catalog_id"]
        for longitude, latitude in build_faults.iter_points(feature["geometry"]):
            assert min_lon - 1 <= longitude <= max_lon + 1
            assert min_lat - 1 <= latitude <= max_lat + 1


def test_REQ_SIS_012_the_demo_declares_the_fault_source_and_its_licence():
    from mapcn_demo import venezuela_data

    assert venezuela_data.VENEZUELA_FAULTS_URL.endswith(ASSET.name)
    assert "GEM" in venezuela_data.FAULTS_ATTRIBUTION
    assert "CC BY-SA" in venezuela_data.FAULTS_ATTRIBUTION
    # Every slip type in the asset must have a colour, or it draws grey.
    assert set(venezuela_data.SLIP_TYPE_COLORS) >= {
        "Dextral",
        "Sinistral",
        "Reverse",
        "Normal",
    }
