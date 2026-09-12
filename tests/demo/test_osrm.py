"""Tests for the OSRM client of the demo (T-018).

No network: both endpoints answer from a saved response, so the tests pin the
shape of the request, what is done with a matrix that has holes in it, and
what the page receives when the public demo server is slow or says no.
"""

from __future__ import annotations

import asyncio
import json
import pathlib

import httpx
import pytest
from mapcn_demo.services import osrm
from mapcn_demo.services.cache import TTLCache

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
TABLE = json.loads((FIXTURES / "osrm_table.json").read_text())
ROUTE = json.loads((FIXTURES / "osrm_route.json").read_text())

CARACAS = (-66.9036, 10.4806)
VALENCIA = (-68.0077, 10.1620)
MARACAIBO = (-71.6125, 10.6427)
LA_ASUNCION = (-63.8861, 11.0333)

THREE_DESTINATIONS = [VALENCIA, MARACAIBO, LA_ASUNCION]


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class _FakeClient:
    """Stands in for ``httpx.AsyncClient``; records what was requested."""

    calls: list[dict] = []
    responses: list = []
    raises = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, params=None):
        type(self).calls.append({"url": url, "params": params, "init": self.kwargs})
        if type(self).raises is not None:
            raise type(self).raises
        queued = type(self).responses
        return queued.pop(0) if len(queued) > 1 else queued[0]


class _Clock:
    """A hand-wound clock, so a one-hour cache can expire in a test."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> _Clock:
    return _Clock()


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, clock):
    _FakeClient.calls = []
    _FakeClient.responses = [_FakeResponse(TABLE)]
    _FakeClient.raises = None
    monkeypatch.setattr(osrm.httpx, "AsyncClient", _FakeClient)
    monkeypatch.setattr(osrm, "CACHE", TTLCache(clock=clock))
    yield


def _coordinates(call: dict) -> list[list[float]]:
    """The coordinate list OSRM was asked about, as numbers."""
    pairs = call["url"].rsplit("/", 1)[-1].split(";")
    return [[round(float(value), 4) for value in pair.split(",")] for pair in pairs]


# ---------------------------------------------------------------------------
# The matrix (REQ-TVJ-001)
# ---------------------------------------------------------------------------


def test_REQ_TVJ_001_the_table_is_asked_for_durations_and_distances_from_one_source():
    asyncio.run(osrm.table(CARACAS, THREE_DESTINATIONS))

    call = _FakeClient.calls[0]
    assert "/table/v1/driving/" in call["url"]
    assert call["params"]["sources"] == 0
    assert call["params"]["annotations"] == "duration,distance"
    assert _coordinates(call) == [
        [-66.9036, 10.4806],
        [-68.0077, 10.162],
        [-71.6125, 10.6427],
        [-63.8861, 11.0333],
    ]


def test_REQ_TVJ_001_the_matrix_drops_the_column_of_the_origin_itself():
    matrix = asyncio.run(osrm.table(CARACAS, THREE_DESTINATIONS))

    assert matrix["durations"] == [7200.5, 19800.2, None]
    assert matrix["distances"] == [154000.0, 412300.5, None]
    assert matrix["origin"] == CARACAS
    assert matrix["error"] is None
    assert matrix["fetched_at"]


def test_REQ_TVJ_001_more_than_25_destinations_are_split_across_requests():
    many = [(-70.0 + index / 100, 9.0) for index in range(30)]
    row = [0] + [60.0] * 25
    first = _FakeResponse({"code": "Ok", "durations": [row], "distances": [row]})
    tail = [0] + [90.0] * 5
    second = _FakeResponse({"code": "Ok", "durations": [tail], "distances": [tail]})
    _FakeClient.responses = [first, second]

    matrix = asyncio.run(osrm.table(CARACAS, many))

    assert len(_FakeClient.calls) == 2
    assert len(_coordinates(_FakeClient.calls[0])) == 26, "origin + 25 destinations"
    assert len(_coordinates(_FakeClient.calls[1])) == 6, "origin + the last 5"
    assert len(matrix["durations"]) == 30
    assert matrix["durations"][:25] == [60.0] * 25
    assert matrix["durations"][25:] == [90.0] * 5
    assert matrix["error"] is None


def test_REQ_TVJ_001_the_profile_reaches_the_url():
    asyncio.run(osrm.table(CARACAS, [VALENCIA], profile="bike"))

    assert "/table/v1/bike/" in _FakeClient.calls[0]["url"]


# ---------------------------------------------------------------------------
# Holes and failures (REQ-TVJ-002)
# ---------------------------------------------------------------------------


def test_REQ_TVJ_002_a_refused_matrix_is_all_holes_and_explains_itself():
    _FakeClient.responses = [_FakeResponse({"code": "NoTable", "message": "no"})]

    matrix = asyncio.run(osrm.table(CARACAS, THREE_DESTINATIONS))

    assert matrix["durations"] == [None, None, None]
    assert matrix["distances"] == [None, None, None]
    assert matrix["error"]
    assert "NoTable" in matrix["error"]


def test_REQ_TVJ_002_a_timeout_does_not_reach_the_page_as_an_exception():
    _FakeClient.raises = httpx.TimeoutException("too slow")

    matrix = asyncio.run(osrm.table(CARACAS, THREE_DESTINATIONS))

    assert matrix["durations"] == [None, None, None]
    assert matrix["error"]


def test_REQ_TVJ_002_a_bad_status_is_an_error_and_not_a_matrix():
    _FakeClient.responses = [_FakeResponse({"code": "Ok"}, status_code=429)]

    matrix = asyncio.run(osrm.table(CARACAS, THREE_DESTINATIONS))

    assert matrix["durations"] == [None, None, None]
    assert "429" in matrix["error"]


def test_REQ_TVJ_002_one_failed_batch_leaves_the_rest_of_the_matrix_standing():
    many = [(-70.0 + index / 100, 9.0) for index in range(30)]
    row = [0] + [60.0] * 25
    ok = _FakeResponse({"code": "Ok", "durations": [row], "distances": [row]})
    refused = _FakeResponse({"code": "NoRoute"})
    _FakeClient.responses = [ok, refused]

    matrix = asyncio.run(osrm.table(CARACAS, many))

    assert matrix["durations"][:25] == [60.0] * 25
    assert matrix["durations"][25:] == [None] * 5
    assert matrix["error"]


def test_REQ_TVJ_002_a_failure_is_not_cached():
    _FakeClient.responses = [_FakeResponse({"code": "NoTable"})]
    asyncio.run(osrm.table(CARACAS, THREE_DESTINATIONS))

    _FakeClient.responses = [_FakeResponse(TABLE)]
    matrix = asyncio.run(osrm.table(CARACAS, THREE_DESTINATIONS))

    assert len(_FakeClient.calls) == 2
    assert matrix["error"] is None


# ---------------------------------------------------------------------------
# The cache (REQ-TVJ-004)
# ---------------------------------------------------------------------------


def test_REQ_TVJ_004_the_matrix_of_an_origin_is_read_once_an_hour(clock):
    asyncio.run(osrm.table(CARACAS, THREE_DESTINATIONS))
    clock.now = 3599
    asyncio.run(osrm.table(CARACAS, THREE_DESTINATIONS))

    assert len(_FakeClient.calls) == 1

    clock.now = 3601
    asyncio.run(osrm.table(CARACAS, THREE_DESTINATIONS))

    assert len(_FakeClient.calls) == 2


def test_REQ_TVJ_004_another_origin_is_another_entry():
    asyncio.run(osrm.table(CARACAS, THREE_DESTINATIONS))
    asyncio.run(osrm.table(VALENCIA, THREE_DESTINATIONS))

    assert len(_FakeClient.calls) == 2


def test_REQ_TVJ_004_the_same_origin_with_other_destinations_is_another_entry():
    # Otherwise a second table for the same capital would silently read back
    # durations measured to somewhere else.
    asyncio.run(osrm.table(CARACAS, THREE_DESTINATIONS))
    asyncio.run(osrm.table(CARACAS, [VALENCIA]))

    assert len(_FakeClient.calls) == 2


# ---------------------------------------------------------------------------
# The drawn route (REQ-TVJ-003)
# ---------------------------------------------------------------------------


def test_REQ_TVJ_003_a_route_is_asked_for_as_a_full_geojson_line():
    _FakeClient.responses = [_FakeResponse(ROUTE)]

    asyncio.run(osrm.route([CARACAS, VALENCIA]))

    call = _FakeClient.calls[0]
    assert "/route/v1/driving/" in call["url"]
    assert call["params"]["overview"] == "full"
    assert call["params"]["geometries"] == "geojson"
    assert _coordinates(call) == [[-66.9036, 10.4806], [-68.0077, 10.162]]


def test_REQ_TVJ_003_a_route_carries_its_line_its_duration_and_its_distance():
    _FakeClient.responses = [_FakeResponse(ROUTE)]

    result = asyncio.run(osrm.route([CARACAS, VALENCIA]))

    assert result["coordinates"][0] == [-66.9036, 10.4806]
    assert len(result["coordinates"]) == 3
    assert result["duration"] == 7200.5
    assert result["distance"] == 154000.0
    assert result["error"] is None


def test_REQ_TVJ_003_a_route_that_does_not_exist_is_empty_and_explains_itself():
    _FakeClient.responses = [_FakeResponse({"code": "NoRoute", "routes": []})]

    result = asyncio.run(osrm.route([CARACAS, LA_ASUNCION]))

    assert result["coordinates"] == []
    assert result["duration"] == 0.0
    assert result["distance"] == 0.0
    assert "NoRoute" in result["error"]


def test_REQ_TVJ_003_a_route_that_times_out_does_not_raise():
    _FakeClient.raises = httpx.TimeoutException("too slow")

    result = asyncio.run(osrm.route([CARACAS, VALENCIA]))

    assert result["coordinates"] == []
    assert result["error"]


def test_REQ_TVJ_004_the_same_route_is_only_drawn_from_one_request():
    _FakeClient.responses = [_FakeResponse(ROUTE)]

    asyncio.run(osrm.route([CARACAS, VALENCIA]))
    asyncio.run(osrm.route([CARACAS, VALENCIA]))

    assert len(_FakeClient.calls) == 1
