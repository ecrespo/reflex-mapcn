"""Tests for the MapLibre expression helpers (T-005).

They are sugar over plain JSON lists, so every test compares against the exact
expression MapLibre expects, as documented in the data model.
"""

from __future__ import annotations

import json

import pytest
from reflex_mapcn.helpers import interpolate, match, step, zoom_interpolate


def test_REQ_HEA_003_interpolate_builds_a_linear_expression_over_a_property():
    assert interpolate("mag", [(4, 4), (7, 24)]) == [
        "interpolate",
        ["linear"],
        ["get", "mag"],
        4,
        4,
        7,
        24,
    ]


def test_REQ_HEA_003_interpolate_accepts_an_exponential_base():
    assert interpolate("mag", [(4, 4), (7, 24)], base=1.5)[1] == ["exponential", 1.5]


def test_REQ_HEA_003_interpolate_rejects_stops_that_do_not_ascend():
    with pytest.raises(ValueError, match="ascending"):
        interpolate("mag", [(7, 24), (4, 4)])


def test_REQ_HEA_003_interpolate_rejects_an_empty_stop_list():
    with pytest.raises(ValueError, match="at least one stop"):
        interpolate("mag", [])


def test_REQ_SIS_001_step_builds_the_depth_colour_ramp():
    assert step("depth", "#ef4444", [(70, "#f97316"), (300, "#3b82f6")]) == [
        "step",
        ["get", "depth"],
        "#ef4444",
        70,
        "#f97316",
        300,
        "#3b82f6",
    ]


def test_REQ_SIS_009_match_builds_a_lookup_with_a_default():
    assert match("slip_type", {"Dextral": "#ef4444"}, "#64748b") == [
        "match",
        ["get", "slip_type"],
        "Dextral",
        "#ef4444",
        "#64748b",
    ]


def test_REQ_HEA_002_zoom_interpolate_interpolates_over_the_zoom_level():
    assert zoom_interpolate([(0, 2), (9, 20)]) == [
        "interpolate",
        ["linear"],
        ["zoom"],
        0,
        2,
        9,
        20,
    ]


def test_REQ_HEA_002_expressions_are_json_serialisable():
    # Article 2: everything crossing into the JSX is plain JSON.
    for expression in (
        interpolate("mag", [(4, 4), (7, 24)]),
        step("depth", "#ef4444", [(70, "#f97316")]),
        match("slip_type", {"Dextral": "#ef4444"}, "#64748b"),
        zoom_interpolate([(0, 2), (9, 20)]),
    ):
        assert json.loads(json.dumps(expression)) == expression
