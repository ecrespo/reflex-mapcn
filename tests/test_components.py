"""Smoke tests for the reflex-mapcn component wrappers.

They only exercise the Python side (component creation and JS codegen); the
React module itself is exercised by the demo app in a browser.
"""

from __future__ import annotations

import reflex as rx
import reflex_mapcn as mapcn


class _State(rx.State):
    viewport: dict = {}
    selected: str = ""

    @rx.event
    def set_vp(self, viewport: dict):
        self.viewport = viewport

    @rx.event
    def on_lnglat(self, lng_lat: dict):
        self.selected = str(lng_lat)

    @rx.event
    def on_geo(self, event: dict | None):
        self.selected = str(event)

    @rx.event
    def on_point(self, feature: dict, coordinates: list):
        self.selected = str(coordinates)


def _render(component: rx.Component) -> str:
    return str(component.render())


def test_library_points_at_shared_asset():
    assert mapcn.Map.library.startswith("$/public/")
    assert mapcn.Map.library.endswith("mapcn.jsx")
    assert mapcn.MAPLIBRE_GL in mapcn.Map.lib_dependencies


def test_all_tags_are_aliased_to_avoid_global_map_clash():
    for cls in (
        mapcn.Map,
        mapcn.MapMarker,
        mapcn.MarkerContent,
        mapcn.MarkerPopup,
        mapcn.MarkerTooltip,
        mapcn.MarkerLabel,
        mapcn.MapPopup,
        mapcn.MapControls,
        mapcn.MapRoute,
        mapcn.RouteProgress,
        mapcn.RouteMarker,
        mapcn.MapArc,
        mapcn.MapGeoJSON,
        mapcn.MapClusterLayer,
        mapcn.MapCamera,
    ):
        assert cls.alias.startswith("Mapcn"), cls


def test_map_with_children_renders():
    component = mapcn.map(
        mapcn.map_controls(position="top-right", show_compass=True),
        mapcn.map_marker(
            mapcn.marker_content(),
            mapcn.marker_tooltip("hi"),
            mapcn.marker_popup("body", close_button=True),
            longitude=1.0,
            latitude=2.0,
            draggable=True,
            on_drag_end=_State.on_lnglat,
        ),
        center=[1.0, 2.0],
        zoom=3,
        viewport=_State.viewport,
        on_viewport_change=_State.set_vp.throttle(100),
        on_click=_State.on_lnglat,
    )
    rendered = _render(component)
    assert "MapcnMap" in rendered
    assert "MapcnMapMarker" in rendered
    assert "showCompass" in rendered
    assert "onViewportChange" in rendered
    assert "onDragEnd" in rendered


def test_layers_render():
    component = mapcn.map(
        mapcn.map_route(
            mapcn.route_progress(color="#0f0"),
            mapcn.route_marker(mapcn.marker_content(), at="progress"),
            coordinates=[[0, 0], [1, 1]],
            progress=0.5,
            dash_array=[1, 2],
            on_click=_State.on_lnglat,
        ),
        mapcn.map_arc(
            data=[{"id": "a", "from": [0, 0], "to": [1, 1]}], on_hover=_State.on_geo
        ),
        mapcn.map_geojson(
            data={"type": "FeatureCollection", "features": []},
            fill_paint={"fill-color": "#000"},
            line_paint=False,
            interactive=True,
            on_click=_State.on_geo,
        ),
        mapcn.map_cluster_layer(
            data="https://example.com/x.geojson", on_point_click=_State.on_point
        ),
        mapcn.map_camera(
            command=mapcn.camera_command("flyTo", center=[0, 0], zoom=2, seq=1)
        ),
        blank=True,
    )
    rendered = _render(component)
    for tag in (
        "MapcnMapRoute",
        "MapcnRouteProgress",
        "MapcnRouteMarker",
        "MapcnMapArc",
        "MapcnMapGeoJSON",
        "MapcnMapClusterLayer",
        "MapcnMapCamera",
    ):
        assert tag in rendered, tag
    assert "linePaint" in rendered
    assert "onPointClick" in rendered


def test_namespace_mirrors_factories():
    assert isinstance(mapcn.mapcn.marker(longitude=0.0, latitude=0.0), mapcn.MapMarker)
    assert isinstance(mapcn.mapcn.geojson(data="x.geojson"), mapcn.MapGeoJSON)
    assert isinstance(mapcn.mapcn(center=[0, 0]), mapcn.Map)


def test_camera_command_helper():
    command = mapcn.camera_command(
        "fitBounds", bounds=[[0, 0], [1, 1]], padding=10, seq=3
    )
    assert command == {
        "type": "fitBounds",
        "bounds": [[0, 0], [1, 1]],
        "padding": 10,
        "seq": 3,
    }
