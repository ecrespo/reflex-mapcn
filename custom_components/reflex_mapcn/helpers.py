"""Helpers for building MapLibre expressions from Python (Reflex extra).

A MapLibre expression is a plain JSON list, so these functions are sugar: they
return exactly what the style specification expects and nothing else. Passing a
raw list to any prop works just as well.

It also holds the RainViewer helpers: radar tiles need a frame index that is
fetched at runtime, and article 5 keeps that request in the application, never
at import time.

Usage::

    import reflex_mapcn as mapcn
    from reflex_mapcn.helpers import interpolate, step

    mapcn.map_circle_layer(
        data=State.quakes,
        radius=interpolate("mag", [(4, 4), (7, 24)]),
        color=step("depth", "#ef4444", [(70, "#f97316"), (300, "#3b82f6")]),
    )
"""

from __future__ import annotations

import logging
from typing import Any, TypedDict

import httpx

__all__ = [
    "RAINVIEWER_INDEX_URL",
    "RainViewerFrame",
    "RainViewerFrames",
    "interpolate",
    "match",
    "rainviewer_frames",
    "rainviewer_tiles",
    "step",
    "zoom_interpolate",
]

logger = logging.getLogger("reflex_mapcn")


class RainViewerFrame(TypedDict):
    """One radar frame: when it was taken and where its tiles live."""

    time: int
    path: str


class RainViewerFrames(TypedDict):
    """The RainViewer radar index."""

    host: str
    generated: int
    past: list[RainViewerFrame]
    nowcast: list[RainViewerFrame]

Stop = tuple[float, Any]


def _check_stops(stops: list[Stop]) -> None:
    """Reject stop lists MapLibre would refuse at style load."""
    if not stops:
        raise ValueError("expression helpers need at least one stop")
    inputs = [stop[0] for stop in stops]
    pairs = zip(inputs, inputs[1:], strict=False)
    if any(later <= earlier for earlier, later in pairs):
        raise ValueError(f"stops must be in ascending input order, got {inputs}")


def _flatten(stops: list[Stop]) -> list[Any]:
    return [value for stop in stops for value in stop]


def interpolate(
    prop: str,
    stops: list[Stop],
    *,
    base: float | None = None,
) -> list[Any]:
    """Interpolate an output over the values of a feature property.

    Args:
        prop: Feature property to read, e.g. ``"mag"``.
        stops: ``(input, output)`` pairs in ascending input order.
        base: Exponential base; omit it for linear interpolation.

    Returns:
        ``["interpolate", ["linear"], ["get", prop], in, out, ...]``
    """
    _check_stops(stops)
    interpolation = ["exponential", base] if base is not None else ["linear"]
    return ["interpolate", interpolation, ["get", prop], *_flatten(stops)]


def zoom_interpolate(stops: list[Stop], *, base: float | None = None) -> list[Any]:
    """Interpolate an output over the zoom level.

    Args:
        stops: ``(zoom, output)`` pairs in ascending zoom order.
        base: Exponential base; omit it for linear interpolation.
    """
    _check_stops(stops)
    interpolation = ["exponential", base] if base is not None else ["linear"]
    return ["interpolate", interpolation, ["zoom"], *_flatten(stops)]


def step(prop: str, base: Any, stops: list[Stop]) -> list[Any]:
    """Pick an output from a staircase over a feature property.

    Args:
        prop: Feature property to read, e.g. ``"depth"``.
        base: Output below the first threshold.
        stops: ``(threshold, output)`` pairs in ascending threshold order.
    """
    _check_stops(stops)
    return ["step", ["get", prop], base, *_flatten(stops)]


def match(prop: str, cases: dict[str, Any], default: Any) -> list[Any]:
    """Map the values of a feature property to outputs.

    Args:
        prop: Feature property to read, e.g. ``"slip_type"``.
        cases: Value to output, e.g. ``{"Dextral": "#ef4444"}``.
        default: Output for anything not listed, including ``null``.
    """
    if not cases:
        raise ValueError("match needs at least one case")
    flattened = [item for pair in cases.items() for item in pair]
    return ["match", ["get", prop], *flattened, default]


# ---------------------------------------------------------------------------
# RainViewer
# ---------------------------------------------------------------------------

#: Index of available radar frames. Free for non-commercial use; see
#: https://www.rainviewer.com/api.html for the terms and the attribution.
RAINVIEWER_INDEX_URL = "https://api.rainviewer.com/public/weather-maps.json"

_EMPTY_FRAMES: RainViewerFrames = {
    "host": "",
    "generated": 0,
    "past": [],
    "nowcast": [],
}


def _frame_list(frames: Any) -> list[RainViewerFrame]:
    if not isinstance(frames, list):
        return []
    return [
        {"time": int(frame["time"]), "path": str(frame["path"])}
        for frame in frames
        if isinstance(frame, dict) and "time" in frame and "path" in frame
    ]


def rainviewer_frames(timeout: float = 10.0) -> RainViewerFrames:
    """Read the RainViewer radar index.

    Radar frame paths expire after roughly two hours, so an application asks
    for them periodically, usually from a background event handler::

        @rx.event(background=True)
        async def refresh_radar(self):
            while True:
                frames = rainviewer_frames()
                if frames["past"]:
                    async with self:
                        self.radar_tiles = rainviewer_tiles(
                            frames["past"][-1], frames["host"]
                        )
                await asyncio.sleep(300)

    A service that is slow, down or answering with something other than JSON
    returns empty frames and logs a warning: a page showing radar must not go
    down because the radar did.

    Args:
        timeout: Seconds to wait for the whole request.

    Returns:
        The host, the generation timestamp, the past frames and the forecast
        frames. Every field is empty when the request failed.
    """
    try:
        response = httpx.get(RAINVIEWER_INDEX_URL, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    # Deliberately broad: no failure of this service may reach the caller.
    except Exception as error:
        logger.warning("rainviewer: could not read the frame index (%s)", error)
        return dict(_EMPTY_FRAMES)  # type: ignore[return-value]

    if not isinstance(payload, dict):
        logger.warning("rainviewer: unexpected frame index payload")
        return dict(_EMPTY_FRAMES)  # type: ignore[return-value]

    radar = payload.get("radar")
    radar = radar if isinstance(radar, dict) else {}
    return {
        "host": str(payload.get("host", "")),
        "generated": int(payload.get("generated", 0) or 0),
        "past": _frame_list(radar.get("past")),
        "nowcast": _frame_list(radar.get("nowcast")),
    }


def rainviewer_tiles(
    frame: RainViewerFrame,
    host: str,
    *,
    size: int = 256,
    color: int = 2,
    smooth: bool = True,
    snow: bool = True,
) -> list[str]:
    """Build the tile templates of one radar frame.

    Args:
        frame: A frame from ``rainviewer_frames()``.
        host: The host from the same call.
        size: Tile size, 256 or 512.
        color: RainViewer colour scheme, 0 to 8.
        smooth: Smooth the radar data.
        snow: Show snow in its own colour.

    Returns:
        A single tile template, ready for ``map_raster_layer(tiles=...)``.
    """
    path = frame.get("path") if isinstance(frame, dict) else None
    if not path:
        raise ValueError("rainviewer_tiles: the frame has no path")
    options = f"{1 if smooth else 0}_{1 if snow else 0}"
    return [f"{host}{path}/{size}/{{z}}/{{x}}/{{y}}/{color}/{options}.png"]
