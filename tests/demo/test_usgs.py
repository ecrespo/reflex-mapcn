"""Tests for the seismic catalogue services of the demo (T-014).

No network: every request is answered from a saved USGS response, so the
tests pin the parsing, the trimming and above all what happens when the
service is slow or down.
"""

from __future__ import annotations

import asyncio
import json
import pathlib

import httpx
import pytest
from mapcn_demo.services import cache as cache_module
from mapcn_demo.services import usgs

FIXTURE = json.loads(
    (pathlib.Path(__file__).parent / "fixtures" / "usgs_sample.json").read_text()
)


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class _FakeClient:
    """Stands in for ``httpx.AsyncClient``; records what was requested."""

    calls: list[dict] = []
    response = None
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
        return type(self).response


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    _FakeClient.calls = []
    _FakeClient.response = _FakeResponse(FIXTURE)
    _FakeClient.raises = None
    monkeypatch.setattr(usgs.httpx, "AsyncClient", _FakeClient)
    usgs.CACHE.clear()
    yield
    usgs.CACHE.clear()


def test_REQ_SIS_001_the_catalog_query_uses_the_venezuela_box():
    catalog = asyncio.run(usgs.fetch_catalog())

    params = _FakeClient.calls[0]["params"]
    assert params["format"] == "geojson"
    assert params["minlongitude"] == -74.0
    assert params["maxlongitude"] == -59.0
    assert params["minlatitude"] == 0.5
    assert params["maxlatitude"] == 13.0
    assert params["minmagnitude"] == 4.5
    assert params["starttime"] == "1900-01-01"
    assert catalog["error"] is None
    assert catalog["source"] == "usgs"


def test_REQ_SIS_001_features_are_trimmed_to_what_the_map_needs():
    catalog = asyncio.run(usgs.fetch_catalog())
    first = catalog["features"]["features"][0]

    assert set(first["properties"]) == {
        "id",
        "mag",
        "magType",
        "depth",
        "time",
        "place",
    }
    assert first["properties"]["id"] == "us7000abcd"
    assert first["properties"]["depth"] == 12.4
    assert first["properties"]["time"] == 1689999000000
    # Four decimals is about 11 m: plenty for a dot on a country map.
    assert first["geometry"]["coordinates"] == [-64.1235, 10.7123]


def test_REQ_SIS_001_events_without_a_magnitude_are_dropped():
    catalog = asyncio.run(usgs.fetch_catalog())

    ids = [f["properties"]["id"] for f in catalog["features"]["features"]]
    assert "us0000zzz" not in ids
    assert catalog["count"] == 3


def test_REQ_SIS_001_a_missing_depth_becomes_zero_and_is_flagged():
    catalog = asyncio.run(usgs.fetch_catalog())
    cariaco = next(
        f
        for f in catalog["features"]["features"]
        if f["properties"]["id"] == "usp0007xyz"
    )

    assert cariaco["properties"]["depth"] == 0.0
    assert cariaco["properties"]["depth_unknown"] is True


def test_REQ_SIS_001_the_trimmed_payload_is_a_fraction_of_the_original():
    catalog = asyncio.run(usgs.fetch_catalog())

    original = len(json.dumps(FIXTURE))
    trimmed = len(json.dumps(catalog["features"]))
    assert trimmed < original * 0.35, f"{trimmed} vs {original}"


def test_REQ_SIS_002_a_second_call_is_served_from_the_cache():
    asyncio.run(usgs.fetch_catalog())
    asyncio.run(usgs.fetch_catalog())

    assert len(_FakeClient.calls) == 1, "the second call hit the network"


def test_REQ_SIS_002_a_different_query_is_not_served_from_the_cache():
    asyncio.run(usgs.fetch_catalog())
    asyncio.run(usgs.fetch_catalog(min_magnitude=5.0))

    assert len(_FakeClient.calls) == 2


def test_REQ_SIS_002_the_cache_expires():
    clock = {"now": 0.0}
    ttl_cache = cache_module.TTLCache(clock=lambda: clock["now"])

    ttl_cache.set("k", "value", ttl_s=600)
    assert ttl_cache.get("k") == "value"

    clock["now"] = 599.0
    assert ttl_cache.get("k") == "value"

    clock["now"] = 601.0
    assert ttl_cache.get("k") is None


def test_REQ_SIS_003_a_timeout_keeps_the_cached_answer(monkeypatch):
    clock = {"now": 0.0}
    fake_cache = cache_module.TTLCache(clock=lambda: clock["now"])
    monkeypatch.setattr(usgs, "CACHE", fake_cache)

    fresh = asyncio.run(usgs.fetch_catalog())
    assert fresh["count"] == 3

    # The ten minute entry has expired, so the next call goes out again.
    clock["now"] = usgs.CATALOG_TTL_S + 1
    _FakeClient.raises = httpx.TimeoutException("too slow")
    degraded = asyncio.run(usgs.fetch_catalog())

    assert degraded["error"]
    assert "USGS" in degraded["error"]
    assert degraded["count"] == 3, "the last good answer was thrown away"


def test_REQ_SIS_003_a_failing_status_reports_an_error():
    _FakeClient.response = _FakeResponse({}, status_code=503)

    catalog = asyncio.run(usgs.fetch_catalog())

    assert catalog["error"]
    assert catalog["count"] == 0
    assert catalog["features"]["features"] == []


def test_REQ_SIS_007_the_live_feed_asks_for_the_last_thirty_days():
    catalog = asyncio.run(usgs.fetch_live())

    params = _FakeClient.calls[0]["params"]
    assert params["minmagnitude"] == 2.5
    assert params["starttime"] < params.get("endtime", "9999")
    # The worldwide month feed is megabytes; this box is kilobytes.
    assert "all_month" not in _FakeClient.calls[0]["url"]
    assert catalog["source"] == "usgs"


def test_REQ_SIS_007_recent_events_are_flagged():
    now_ms = 1690000000000
    catalog = asyncio.run(usgs.fetch_live(now_ms=now_ms))
    by_id = {f["properties"]["id"]: f for f in catalog["features"]["features"]}

    # 1689999000000 is 17 minutes before `now`; the rest are years old.
    assert by_id["us7000abcd"]["properties"]["recent"] is True
    assert by_id["us1000abcd"]["properties"]["recent"] is False


def test_REQ_SIS_002_the_live_feed_has_its_own_cache_entry():
    asyncio.run(usgs.fetch_catalog())
    asyncio.run(usgs.fetch_live())
    asyncio.run(usgs.fetch_live())

    assert len(_FakeClient.calls) == 2


# ---------------------------------------------------------------------------
# Delta 2026-09-catalog-payload: the history has to fit the network budget
# ---------------------------------------------------------------------------


def test_REQ_SIS_001_the_catalog_defaults_to_the_reliable_threshold():
    # The USGS catalogue is only complete for Venezuela from about 1973 at
    # M >= 4.5, and asking for 4.0 tripled the payload for events the page
    # already warns are missing.
    asyncio.run(usgs.fetch_catalog())

    assert _FakeClient.calls[0]["params"]["minmagnitude"] == 4.5


def test_REQ_SIS_001_the_history_drops_what_it_can_rebuild():
    catalog = asyncio.run(usgs.fetch_catalog())

    for feature in catalog["features"]["features"]:
        assert "url" not in feature["properties"], "rebuildable from the id"
        assert "recent" not in feature["properties"], "always false in history"
        assert "id" not in feature, "duplicated in the properties"


def test_REQ_SIS_007_the_live_feed_keeps_the_recent_flag():
    catalog = asyncio.run(usgs.fetch_live(now_ms=1690000000000))

    for feature in catalog["features"]["features"]:
        assert "recent" in feature["properties"]
        assert "url" not in feature["properties"]


def test_the_history_fits_the_network_budget():
    # 400 KB over about 1600 events at M >= 4.5 leaves 250 bytes each, and
    # the websocket of Reflex negotiates no compression (T-020, H-03).
    catalog = asyncio.run(usgs.fetch_catalog())
    payload = json.dumps(catalog["features"], separators=(",", ":"))
    per_event = len(payload) / catalog["count"]

    assert per_event <= 250, f"{per_event:.0f} bytes per event"
