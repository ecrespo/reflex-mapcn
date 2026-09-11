"""Helpers for building MapLibre expressions from Python (Reflex extra).

A MapLibre expression is a plain JSON list, so these functions are sugar: they
return exactly what the style specification expects and nothing else. Passing a
raw list to any prop works just as well.

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

from typing import Any

__all__ = ["interpolate", "match", "step", "zoom_interpolate"]

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
