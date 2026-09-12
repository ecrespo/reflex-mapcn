"""Tests for the MapLibre expression helpers (T-005).

They are sugar over plain JSON lists, so every test compares against the exact
expression MapLibre expects, as documented in the data model.
"""

from __future__ import annotations

import json
import logging

import httpx
import pytest
from reflex_mapcn import helpers
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


# ---------------------------------------------------------------------------
# RainViewer (T-007)
# ---------------------------------------------------------------------------

INDEX_PAYLOAD = {
    "version": "2.0",
    "generated": 1690000000,
    "host": "https://tilecache.rainviewer.com",
    "radar": {
        "past": [
            {"time": 1689999000, "path": "/v2/radar/1689999000"},
            {"time": 1689999600, "path": "/v2/radar/1689999600"},
        ],
        "nowcast": [{"time": 1690000600, "path": "/v2/radar/nowcast_1690000600"}],
    },
    "satellite": {"infrared": []},
}


class _FakeResponse:
    def __init__(self, payload=None, error=None, status_code=200):
        self._payload = payload
        self._error = error
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code != 200:
            raise httpx.HTTPStatusError(
                f"status {self.status_code}", request=None, response=None
            )

    def json(self):
        if self._error is not None:
            raise self._error
        return self._payload


def _fake_get(monkeypatch, response=None, raises=None, calls=None):
    def fake(url, **kwargs):
        if calls is not None:
            calls.append({"url": url, **kwargs})
        if raises is not None:
            raise raises
        return response

    monkeypatch.setattr(helpers.httpx, "get", fake)


def test_REQ_RAS_006_rainviewer_frames_returns_host_past_and_nowcast(monkeypatch):
    calls = []
    _fake_get(monkeypatch, response=_FakeResponse(INDEX_PAYLOAD), calls=calls)

    frames = helpers.rainviewer_frames()

    assert frames["host"] == "https://tilecache.rainviewer.com"
    assert frames["generated"] == 1690000000
    assert frames["past"] == [
        {"time": 1689999000, "path": "/v2/radar/1689999000"},
        {"time": 1689999600, "path": "/v2/radar/1689999600"},
    ]
    assert frames["nowcast"] == [
        {"time": 1690000600, "path": "/v2/radar/nowcast_1690000600"}
    ]
    assert "weather-maps.json" in calls[0]["url"]
    assert calls[0]["timeout"] == 10.0


def test_REQ_RAS_007_a_timeout_returns_empty_frames_and_warns(monkeypatch, caplog):
    _fake_get(monkeypatch, raises=httpx.TimeoutException("too slow"))

    with caplog.at_level(logging.WARNING, logger="reflex_mapcn"):
        frames = helpers.rainviewer_frames(timeout=0.1)

    assert frames == {"host": "", "generated": 0, "past": [], "nowcast": []}
    assert any("rainviewer" in record.message.lower() for record in caplog.records)


def test_REQ_RAS_007_invalid_json_returns_empty_frames(monkeypatch, caplog):
    _fake_get(monkeypatch, response=_FakeResponse(error=ValueError("not json")))

    with caplog.at_level(logging.WARNING, logger="reflex_mapcn"):
        frames = helpers.rainviewer_frames()

    assert frames["past"] == []
    assert caplog.records


def test_REQ_RAS_007_a_failing_status_returns_empty_frames(monkeypatch, caplog):
    _fake_get(monkeypatch, response=_FakeResponse(INDEX_PAYLOAD, status_code=503))

    with caplog.at_level(logging.WARNING, logger="reflex_mapcn"):
        frames = helpers.rainviewer_frames()

    assert frames["past"] == []


def test_REQ_RAS_007_a_payload_without_radar_returns_empty_frames(monkeypatch):
    payload = {"host": "https://x", "generated": 1}
    _fake_get(monkeypatch, response=_FakeResponse(payload))

    frames = helpers.rainviewer_frames()

    assert frames["past"] == []
    assert frames["nowcast"] == []


def test_REQ_RAS_006_rainviewer_tiles_builds_the_tile_template():
    frame = {"time": 1689999000, "path": "/v2/radar/1689999000"}

    tiles = helpers.rainviewer_tiles(frame, "https://tilecache.rainviewer.com")

    assert tiles == [
        "https://tilecache.rainviewer.com/v2/radar/1689999000/256/{z}/{x}/{y}/2/1_1.png"
    ]


def test_REQ_RAS_006_rainviewer_tiles_honours_its_options():
    frame = {"time": 1, "path": "/v2/radar/1"}

    tiles = helpers.rainviewer_tiles(
        frame, "https://host", size=512, color=4, smooth=False, snow=False
    )

    assert tiles == ["https://host/v2/radar/1/512/{z}/{x}/{y}/4/0_0.png"]


def test_REQ_RAS_006_rainviewer_tiles_needs_a_frame_with_a_path():
    with pytest.raises(ValueError, match="path"):
        helpers.rainviewer_tiles({"time": 1}, "https://host")
