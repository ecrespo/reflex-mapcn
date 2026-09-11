"""Reflex custom component wrapping mapcn (https://www.mapcn.dev).

mapcn is a set of MapLibre GL map components (map, markers, popups, controls,
routes, arcs, GeoJSON layers and clusters) originally distributed as a shadcn
registry item. This package ships a self-contained port of that component
(``mapcn.jsx`` + ``mapcn.css``) and exposes every piece as a Reflex component.

Usage::

    import reflex as rx
    import reflex_mapcn as mapcn

    def index():
        return rx.box(
            mapcn.map(
                mapcn.map_controls(position="top-right", show_compass=True),
                mapcn.map_marker(
                    mapcn.marker_content(),
                    mapcn.marker_tooltip("Caracas"),
                    longitude=-66.9036,
                    latitude=10.4806,
                ),
                center=[-66.9036, 10.4806],
                zoom=11,
            ),
            height="420px",
        )

All callbacks deliver JSON-serialisable payloads so they can be bound directly
to Reflex event handlers.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

import reflex as rx
from reflex.components.component import NoSSRComponent
from reflex.event import passthrough_event_spec

from .presets import RASTER_PRESETS

# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------

# The port of mapcn's map.tsx and its stylesheet live next to this file and are
# copied into the app's `assets/external/reflex_mapcn/` folder at compile time.
_MAPCN_JS = rx.asset("mapcn.jsx", shared=True)
_MAPCN_CSS = rx.asset("mapcn.css", shared=True)


def _importable(asset_path: Any) -> str:
    """Return the build-time import path for a shared asset.

    Newer Reflex versions expose ``importable_path`` on the value returned by
    ``rx.asset``; older ones return a plain string that must be prefixed with
    ``$/public``.
    """
    importable = getattr(asset_path, "importable_path", None)
    if importable:
        return importable
    raw = str(asset_path).split("?", 1)[0]
    return f"$/public{raw}"


# Inlined instead of ``_importable(_MAPCN_JS)``: `reflex component build`
# copies module-level assignments into ``mapcn.pyi`` verbatim but drops
# private helpers, so a call here would leave an undefined name in the stub.
MAPCN_LIBRARY: str = getattr(_MAPCN_JS, "importable_path", None) or (
    f"$/public{str(_MAPCN_JS).split('?', 1)[0]}"
)

#: npm package required by the JS module.
MAPLIBRE_GL = "maplibre-gl@^6.3.0"


# ---------------------------------------------------------------------------
# Typed payloads (documentation for event handlers)
# ---------------------------------------------------------------------------


class LngLat(TypedDict):
    """A coordinate pair as delivered by marker / route events."""

    lng: float
    lat: float


class MapClickEvent(TypedDict):
    """Payload of ``Map.on_click``."""

    lng: float
    lat: float
    point: dict[str, float]


class MapViewport(TypedDict):
    """Map viewport state (``center`` is ``[longitude, latitude]``)."""

    center: list[float]
    zoom: float
    bearing: float
    pitch: float


class LocateCoords(TypedDict):
    """Payload of ``MapControls.on_locate``."""

    longitude: float
    latitude: float


class GeoJSONFeature(TypedDict):
    """Serialised GeoJSON feature delivered by layer events."""

    type: str
    id: Any
    properties: dict[str, Any]
    geometry: dict[str, Any] | None
    source: str | None
    sourceLayer: str | None


class MapGeoJSONEvent(TypedDict):
    """Payload of ``MapGeoJSON.on_click`` / ``on_hover``."""

    feature: GeoJSONFeature
    longitude: float
    latitude: float


class MapArcEvent(TypedDict):
    """Payload of ``MapArc.on_click`` / ``on_hover``."""

    arc: dict[str, Any]
    longitude: float
    latitude: float


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class MapcnComponent(NoSSRComponent):
    """Base class shared by all mapcn components.

    Every component is loaded client-side only (MapLibre needs ``window``).
    """

    library = MAPCN_LIBRARY

    lib_dependencies: list[str] = [MAPLIBRE_GL]

    def add_imports(self) -> dict[str, str | list[str]]:
        """Make sure the stylesheet is bundled with the app."""
        return {"": [_importable(_MAPCN_CSS)]}


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------


class Map(MapcnComponent):
    """Root map container.

    Initialises MapLibre GL, resolves the light/dark theme automatically (it
    follows Reflex's color mode) and provides context to every child component.

    Give the map a size through its parent or with ``height`` / ``width``.
    Any extra MapLibre ``MapOptions`` can be passed as props (``center``,
    ``zoom``, ``pitch``, ``max_bounds``, ``scroll_zoom`` ...).
    """

    tag = "Map"
    alias = "MapcnMap"

    # ---- mapcn props -----------------------------------------------------

    # Force a theme instead of following the document / system preference.
    theme: rx.Var[Literal["light", "dark"]]

    # Custom map styles per theme: {"light": url_or_spec, "dark": url_or_spec}.
    styles: rx.Var[dict[str, Any]]

    # Transparent, tile-less basemap for data visualisations.
    blank: rx.Var[bool]

    # Map projection, e.g. {"type": "globe"}.
    projection: rx.Var[dict[str, Any]]

    # Controlled viewport: {"center": [lng, lat], "zoom", "bearing", "pitch"}.
    # Use together with `on_viewport_change` for controlled mode.
    viewport: rx.Var[dict[str, Any]]

    # Show a loading overlay on top of the map.
    loading: rx.Var[bool]

    # ---- MapLibre MapOptions (passed through) ----------------------------

    # Initial center as [longitude, latitude].
    center: rx.Var[list[float]]
    zoom: rx.Var[float]
    bearing: rx.Var[float]
    pitch: rx.Var[float]
    min_zoom: rx.Var[float]
    max_zoom: rx.Var[float]
    min_pitch: rx.Var[float]
    max_pitch: rx.Var[float]
    # [[west, south], [east, north]]
    max_bounds: rx.Var[list[list[float]]]
    interactive: rx.Var[bool]
    scroll_zoom: rx.Var[bool]
    drag_pan: rx.Var[bool]
    drag_rotate: rx.Var[bool]
    double_click_zoom: rx.Var[bool]
    touch_zoom_rotate: rx.Var[bool]
    touch_pitch: rx.Var[bool]
    keyboard: rx.Var[bool]
    box_zoom: rx.Var[bool]
    cooperative_gestures: rx.Var[bool]
    hash: rx.Var[bool | str]
    render_world_copies: rx.Var[bool]
    fade_duration: rx.Var[int]
    pixel_ratio: rx.Var[float]
    canvas_context_attributes: rx.Var[dict[str, Any]]
    attribution_control: rx.Var[bool | dict[str, Any]]
    locale: rx.Var[dict[str, str]]

    # ---- Reflex-only extras ---------------------------------------------

    # URL of the MapLibre web worker (defaults to unpkg CDN).
    worker_url: rx.Var[str]

    # ---- Events ----------------------------------------------------------

    # Fires continuously while the map moves (pan/zoom/rotate/pitch).
    # Combine with `.throttle(ms)` to limit backend traffic.
    on_viewport_change: rx.EventHandler[passthrough_event_spec(MapViewport)]

    # Fires once the camera settles (Reflex extra).
    on_move_end: rx.EventHandler[passthrough_event_spec(MapViewport)]

    # Fires when the base map is clicked (Reflex extra).
    on_click: rx.EventHandler[passthrough_event_spec(MapClickEvent)]

    # Fires when MapLibre finished loading the style (Reflex extra).
    on_load: rx.EventHandler[passthrough_event_spec(MapViewport)]


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------


class MapMarker(MapcnComponent):
    """Marker anchored at a coordinate.

    Compose with ``marker_content``, ``marker_popup``, ``marker_tooltip`` and
    ``marker_label``.
    """

    tag = "MapMarker"
    alias = "MapcnMapMarker"

    longitude: rx.Var[float]
    latitude: rx.Var[float]

    # Enable dragging (fires on_drag_start / on_drag / on_drag_end).
    draggable: rx.Var[bool]

    # ---- MapLibre MarkerOptions -----------------------------------------
    anchor: rx.Var[
        Literal[
            "center",
            "top",
            "bottom",
            "left",
            "right",
            "top-left",
            "top-right",
            "bottom-left",
            "bottom-right",
        ]
    ]
    offset: rx.Var[list[float]]
    rotation: rx.Var[float]
    rotation_alignment: rx.Var[Literal["map", "viewport", "auto"]]
    pitch_alignment: rx.Var[Literal["map", "viewport", "auto"]]
    opacity: rx.Var[str]
    opacity_when_covered: rx.Var[str]
    click_tolerance: rx.Var[int]
    subpixel_positioning: rx.Var[bool]

    # ---- Events (each receives {"lng": float, "lat": float}) ------------
    on_click: rx.EventHandler[passthrough_event_spec(LngLat)]
    on_mouse_enter: rx.EventHandler[passthrough_event_spec(LngLat)]
    on_mouse_leave: rx.EventHandler[passthrough_event_spec(LngLat)]
    on_drag_start: rx.EventHandler[passthrough_event_spec(LngLat)]
    on_drag: rx.EventHandler[passthrough_event_spec(LngLat)]
    on_drag_end: rx.EventHandler[passthrough_event_spec(LngLat)]


class MarkerContent(MapcnComponent):
    """Visual representation of a marker. Defaults to a blue dot."""

    tag = "MarkerContent"
    alias = "MapcnMarkerContent"


class MarkerPopup(MapcnComponent):
    """Popup attached to a marker, toggled by clicking the marker."""

    tag = "MarkerPopup"
    alias = "MapcnMarkerPopup"

    # Render an explicit close button.
    close_button: rx.Var[bool]

    # ---- MapLibre PopupOptions ------------------------------------------
    offset: rx.Var[int | list[float] | dict[str, list[float]]]
    max_width: rx.Var[str]
    anchor: rx.Var[str]
    close_on_click: rx.Var[bool]
    close_on_move: rx.Var[bool]
    focus_after_open: rx.Var[bool]


class MarkerTooltip(MapcnComponent):
    """Hover tooltip attached to a marker."""

    tag = "MarkerTooltip"
    alias = "MapcnMarkerTooltip"

    offset: rx.Var[int | list[float] | dict[str, list[float]]]
    max_width: rx.Var[str]
    anchor: rx.Var[str]


class MarkerLabel(MapcnComponent):
    """Text label rendered above or below a marker (inside ``marker_content``)."""

    tag = "MarkerLabel"
    alias = "MapcnMarkerLabel"

    position: rx.Var[Literal["top", "bottom"]]


# ---------------------------------------------------------------------------
# Popup & controls
# ---------------------------------------------------------------------------


class MapPopup(MapcnComponent):
    """Standalone popup at a coordinate (not attached to a marker)."""

    tag = "MapPopup"
    alias = "MapcnMapPopup"

    longitude: rx.Var[float]
    latitude: rx.Var[float]

    close_button: rx.Var[bool]

    # ---- MapLibre PopupOptions ------------------------------------------
    offset: rx.Var[int | list[float] | dict[str, list[float]]]
    max_width: rx.Var[str]
    anchor: rx.Var[str]
    close_on_click: rx.Var[bool]
    close_on_move: rx.Var[bool]
    focus_after_open: rx.Var[bool]

    # Fires when the popup is closed (close button, outside click, ...).
    on_close: rx.EventHandler[rx.event.no_args_event_spec]


class MapControls(MapcnComponent):
    """Zoom / compass / locate / fullscreen buttons."""

    tag = "MapControls"
    alias = "MapcnMapControls"

    position: rx.Var[Literal["top-left", "top-right", "bottom-left", "bottom-right"]]
    show_zoom: rx.Var[bool]
    show_compass: rx.Var[bool]
    show_locate: rx.Var[bool]
    show_fullscreen: rx.Var[bool]

    # Receives {"longitude": float, "latitude": float} after geolocation.
    on_locate: rx.EventHandler[passthrough_event_spec(LocateCoords)]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


class MapRoute(MapcnComponent):
    """Line connecting a list of ``[longitude, latitude]`` coordinates.

    Compose with ``route_progress`` and ``route_marker``.
    """

    tag = "MapRoute"
    alias = "MapcnMapRoute"

    # Explicit layer id (auto-generated when omitted).
    coordinates: rx.Var[list[list[float]]]
    color: rx.Var[str]
    width: rx.Var[float]
    opacity: rx.Var[float]
    dash_array: rx.Var[list[float]]
    # Fraction (0-1) of the route already covered.
    progress: rx.Var[float]
    active: rx.Var[bool]
    active_color: rx.Var[str]
    active_width: rx.Var[float]
    active_opacity: rx.Var[float]
    active_dash_array: rx.Var[list[float]]
    before_id: rx.Var[str]
    interactive: rx.Var[bool]

    on_click: rx.EventHandler[passthrough_event_spec(LngLat)]
    on_mouse_enter: rx.EventHandler[passthrough_event_spec(LngLat)]
    on_mouse_leave: rx.EventHandler[rx.event.no_args_event_spec]


class RouteProgress(MapcnComponent):
    """Draws the traveled portion of the parent ``map_route``."""

    tag = "RouteProgress"
    alias = "MapcnRouteProgress"

    color: rx.Var[str]
    width: rx.Var[float]
    opacity: rx.Var[float]
    dash_array: rx.Var[list[float]]


class RouteMarker(MapMarker):
    """A marker pinned along the parent ``map_route``.

    ``at`` is ``"start"``, ``"end"``, ``"progress"`` or a 0-1 fraction.
    """

    tag = "RouteMarker"
    alias = "MapcnRouteMarker"

    at: rx.Var[str | float]


# ---------------------------------------------------------------------------
# Layers
# ---------------------------------------------------------------------------


class MapArc(MapcnComponent):
    """Curved arcs between coordinate pairs.

    ``data`` is a list of ``{"id": ..., "from": [lng, lat], "to": [lng, lat],
    ...extra_properties}``. Extra properties are exposed to MapLibre
    expressions via ``["get", "<name>"]``.
    """

    tag = "MapArc"
    alias = "MapcnMapArc"

    data: rx.Var[list[dict[str, Any]]]
    curvature: rx.Var[float]
    samples: rx.Var[int]
    paint: rx.Var[dict[str, Any]]
    layout: rx.Var[dict[str, Any]]
    hover_paint: rx.Var[dict[str, Any]]
    interactive: rx.Var[bool]
    before_id: rx.Var[str]

    on_click: rx.EventHandler[passthrough_event_spec(MapArcEvent)]
    # Receives the event or None when the cursor leaves the last hovered arc.
    on_hover: rx.EventHandler[passthrough_event_spec(MapArcEvent)]


class MapGeoJSON(MapcnComponent):
    """Render GeoJSON (FeatureCollection / Feature / Geometry / URL) as
    fill + outline layers."""

    tag = "MapGeoJSON"
    alias = "MapcnMapGeoJSON"

    data: rx.Var[dict[str, Any] | str]
    # Feature property promoted to the feature id (needed for hover state).
    promote_id: rx.Var[str]
    # Paint for the fill layer, or False to omit it.
    fill_paint: rx.Var[dict[str, Any] | bool]
    # Paint for the outline layer, or False to omit it.
    line_paint: rx.Var[dict[str, Any] | bool]
    fill_hover_paint: rx.Var[dict[str, Any]]
    interactive: rx.Var[bool]
    before_id: rx.Var[str]

    on_click: rx.EventHandler[passthrough_event_spec(MapGeoJSONEvent)]
    # Receives the event or None when the cursor leaves.
    on_hover: rx.EventHandler[passthrough_event_spec(MapGeoJSONEvent)]


class MapClusterLayer(MapcnComponent):
    """Native MapLibre clustering for point FeatureCollections (or a URL)."""

    tag = "MapClusterLayer"
    alias = "MapcnMapClusterLayer"

    data: rx.Var[dict[str, Any] | str]
    cluster_max_zoom: rx.Var[int]
    cluster_radius: rx.Var[int]
    # [small, medium, large]
    cluster_colors: rx.Var[list[str]]
    # [medium, large]
    cluster_thresholds: rx.Var[list[int]]
    point_color: rx.Var[str]

    # (feature, [lng, lat])
    on_point_click: rx.EventHandler[passthrough_event_spec(GeoJSONFeature, list)]
    # (cluster_id, [lng, lat], point_count). Overrides the default zoom-in.
    on_cluster_click: rx.EventHandler[passthrough_event_spec(int, list, int)]


# ---------------------------------------------------------------------------
# 0.2.0 layers (Reflex extras, not part of mapcn upstream)
# ---------------------------------------------------------------------------


class RasterLoadError(TypedDict):
    """Payload of ``map_raster_layer.on_load_error``."""

    source_id: str
    message: str


class MapRasterLayer(MapcnComponent):
    """Third-party raster tiles on top of the basemap (Reflex extra).

    Radar, railways, nautical charts, satellite imagery or a traffic service of
    your own: anything published as ``{z}/{x}/{y}`` tiles or as TileJSON.

    Pass ``preset`` for a service that needs no API key, or ``tiles`` / ``url``
    for any other. A preset only fills in what you leave out::

        mapcn.map_raster_layer(preset="openseamap", opacity=0.9)
        mapcn.map_raster_layer(
            tiles=[f"https://api.example.com/{{z}}/{{x}}/{{y}}.png?key={KEY}"],
            attribution="© Example",
        )

    Presets live in ``reflex_mapcn.presets`` so you can read them, copy them and
    check the attribution each service requires. ``preset="rainviewer"`` is the
    exception: radar frame paths expire, so build the tiles with
    ``rainviewer_tiles()`` and pass them explicitly.
    """

    tag = "RasterLayer"
    alias = "MapcnRasterLayer"

    # Tile templates, e.g. ["https://host/{z}/{x}/{y}.png"].
    tiles: rx.Var[list[str]]
    # TileJSON url, as an alternative to `tiles`.
    url: rx.Var[str]
    tile_size: rx.Var[Literal[256, 512]]
    scheme: rx.Var[Literal["xyz", "tms"]]
    min_zoom: rx.Var[int]
    max_zoom: rx.Var[int]
    # [west, south, east, north]: stops requests outside the covered area.
    bounds: rx.Var[list[float]]
    # Rendered by MapLibre in the attribution control; HTML is allowed.
    attribution: rx.Var[str]

    # ---- paint (applied without recreating the source) -------------------

    opacity: rx.Var[float]
    resampling: rx.Var[Literal["linear", "nearest"]]
    saturation: rx.Var[float]
    contrast: rx.Var[float]
    brightness_min: rx.Var[float]
    brightness_max: rx.Var[float]
    hue_rotate: rx.Var[float]
    fade_duration: rx.Var[int]

    visible: rx.Var[bool]
    before_id: rx.Var[str]

    # Fires at most once a minute while the tiles of this layer fail to load.
    on_load_error: rx.EventHandler[passthrough_event_spec(RasterLoadError)]

    @classmethod
    def create(cls, *children, **props) -> rx.Component:
        """Resolve the preset and reject a layer with nothing to render."""
        preset_name = props.pop("preset", None)
        if preset_name is not None:
            preset = RASTER_PRESETS.get(preset_name)
            if preset is None:
                known = ", ".join(sorted(RASTER_PRESETS))
                raise ValueError(
                    f"map_raster_layer: unknown preset {preset_name!r} (known: {known})"
                )
            for key, value in preset.as_props().items():
                if value in (None, []) or props.get(key) is not None:
                    continue
                props[key] = value
            if preset.name == "rainviewer" and props.get("tiles") is None:
                raise ValueError(
                    "map_raster_layer: preset 'rainviewer' needs tiles built with "
                    "rainviewer_tiles(); frame paths expire and cannot be hard-coded"
                )

        if props.get("tiles") is None and props.get("url") is None:
            raise ValueError("map_raster_layer: provide preset, tiles or url")

        return super().create(*children, **props)


# ---------------------------------------------------------------------------
# Reflex extra: imperative camera
# ---------------------------------------------------------------------------


class MapCamera(MapcnComponent):
    """Drive the camera from state (Reflex extra, not part of mapcn).

    Place it inside ``map`` and bind ``command`` to a state var. Every time
    the command changes it is executed, e.g.::

        command = {"type": "flyTo", "center": [lng, lat], "zoom": 12, "seq": 1}
        command = {
            "type": "fitBounds",
            "bounds": [[w, s], [e, n]],
            "padding": 40,
            "seq": 2,
        }

    Supported types: ``flyTo`` (default), ``easeTo``, ``jumpTo``, ``fitBounds``.
    Use ``seq`` to re-issue an identical command.
    """

    tag = "MapCamera"
    alias = "MapcnMapCamera"

    command: rx.Var[dict[str, Any]]


def camera_command(
    type: str = "flyTo",
    *,
    seq: int | None = None,
    **options: Any,
) -> dict[str, Any]:
    """Build a ``MapCamera`` command dict.

    Args:
        type: ``flyTo`` | ``easeTo`` | ``jumpTo`` | ``fitBounds``.
        seq: Monotonic counter so identical commands re-run.
        **options: MapLibre camera options (``center``, ``zoom``, ``bounds`` ...).
    """
    command: dict[str, Any] = {"type": type, **options}
    if seq is not None:
        command["seq"] = seq
    return command


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

map = Map.create  # noqa: A001 - mirrors mapcn's `Map`
map_marker = MapMarker.create
marker_content = MarkerContent.create
marker_popup = MarkerPopup.create
marker_tooltip = MarkerTooltip.create
marker_label = MarkerLabel.create
map_popup = MapPopup.create
map_controls = MapControls.create
map_route = MapRoute.create
route_progress = RouteProgress.create
route_marker = RouteMarker.create
map_arc = MapArc.create
map_geojson = MapGeoJSON.create
map_cluster_layer = MapClusterLayer.create
map_camera = MapCamera.create
map_raster_layer = MapRasterLayer.create


class MapcnNamespace(rx.ComponentNamespace):
    """``mapcn.map(...)``-style namespace mirroring the mapcn exports."""

    __call__ = staticmethod(Map.create)
    map = staticmethod(Map.create)
    marker = staticmethod(MapMarker.create)
    marker_content = staticmethod(MarkerContent.create)
    marker_popup = staticmethod(MarkerPopup.create)
    marker_tooltip = staticmethod(MarkerTooltip.create)
    marker_label = staticmethod(MarkerLabel.create)
    popup = staticmethod(MapPopup.create)
    controls = staticmethod(MapControls.create)
    route = staticmethod(MapRoute.create)
    route_progress = staticmethod(RouteProgress.create)
    route_marker = staticmethod(RouteMarker.create)
    arc = staticmethod(MapArc.create)
    geojson = staticmethod(MapGeoJSON.create)
    cluster_layer = staticmethod(MapClusterLayer.create)
    camera = staticmethod(MapCamera.create)


mapcn = MapcnNamespace()

__all__ = [
    "MAPLIBRE_GL",
    "GeoJSONFeature",
    "LngLat",
    "LocateCoords",
    "Map",
    "MapArc",
    "MapArcEvent",
    "MapCamera",
    "MapClickEvent",
    "MapClusterLayer",
    "MapControls",
    "MapGeoJSON",
    "MapGeoJSONEvent",
    "RasterLoadError",
    "MapMarker",
    "MapPopup",
    "MapRasterLayer",
    "MapRoute",
    "MapViewport",
    "MapcnComponent",
    "MapcnNamespace",
    "MarkerContent",
    "MarkerLabel",
    "MarkerPopup",
    "MarkerTooltip",
    "RouteMarker",
    "RouteProgress",
    "camera_command",
    "map",
    "map_arc",
    "map_camera",
    "map_cluster_layer",
    "map_controls",
    "map_geojson",
    "map_marker",
    "map_popup",
    "map_raster_layer",
    "map_route",
    "mapcn",
    "marker_content",
    "marker_label",
    "marker_popup",
    "marker_tooltip",
    "route_marker",
    "route_progress",
]
