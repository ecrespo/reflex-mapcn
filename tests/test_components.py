"""Smoke tests for the reflex-mapcn component wrappers.

They only exercise the Python side (component creation and JS codegen); the
React module itself is exercised by the demo app in a browser.
"""

from __future__ import annotations

import json

import pytest
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


# ---------------------------------------------------------------------------
# 0.2.0 layers
# ---------------------------------------------------------------------------


def _prop(component: rx.Component, name: str) -> str:
    return str(getattr(component, name))


def test_REQ_RAS_001_raster_layer_renders_inside_a_map():
    rendered = _render(
        mapcn.map(
            mapcn.map_raster_layer(
                id="radar",
                tiles=["https://tiles.example.test/{z}/{x}/{y}.png"],
                opacity=0.6,
                before_id="waterway-name",
            )
        )
    )
    assert "MapcnRasterLayer" in rendered
    assert "tiles" in rendered
    assert "beforeId" in rendered


def test_REQ_RAS_004_tile_size_scheme_and_attribution_reach_the_component():
    layer = mapcn.map_raster_layer(
        tiles=["https://tiles.example.test/{z}/{x}/{y}.png"],
        tile_size=512,
        scheme="tms",
        attribution="© Example",
    )
    assert _prop(layer, "tile_size") == "512"
    assert "tms" in _prop(layer, "scheme")
    assert "Example" in _prop(layer, "attribution")


def test_REQ_RAS_005_preset_fills_tiles_zoom_and_attribution():
    layer = mapcn.map_raster_layer(preset="openseamap")
    assert "tiles.openseamap.org" in _prop(layer, "tiles")
    assert _prop(layer, "tile_size") == "256"
    assert _prop(layer, "max_zoom") == "18"
    assert "OpenSeaMap" in _prop(layer, "attribution")


def test_REQ_RAS_005_an_explicit_prop_overrides_the_preset():
    layer = mapcn.map_raster_layer(preset="openseamap", max_zoom=10, opacity=0.5)
    assert _prop(layer, "max_zoom") == "10"
    assert _prop(layer, "opacity") == "0.5"


def test_REQ_RAS_005_the_preset_name_is_not_forwarded_to_javascript():
    # Presets live in Python only: the JSX always receives resolved tiles.
    rendered = _render(mapcn.map_raster_layer(preset="openseamap"))
    assert "preset" not in rendered


def test_REQ_RAS_005_an_unknown_preset_is_rejected_at_creation():
    with pytest.raises(ValueError, match="unknown preset"):
        mapcn.map_raster_layer(preset="not_a_preset")


def test_REQ_RAS_001_a_layer_without_tiles_preset_or_url_is_rejected():
    with pytest.raises(ValueError, match="provide preset, tiles or url"):
        mapcn.map_raster_layer(opacity=0.5)


def test_REQ_RAS_006_the_rainviewer_preset_demands_tiles_from_the_helper():
    with pytest.raises(ValueError, match="rainviewer_tiles"):
        mapcn.map_raster_layer(preset="rainviewer")

    layer = mapcn.map_raster_layer(
        preset="rainviewer", tiles=["https://tilecache.rainviewer.com/v2/{z}/{x}/{y}.png"]
    )
    assert _prop(layer, "max_zoom") == "7"


def test_REQ_RAS_011_on_load_error_is_wired_as_an_event_handler():
    rendered = _render(
        mapcn.map(
            mapcn.map_raster_layer(preset="openseamap", on_load_error=_State.on_geo)
        )
    )
    assert "onLoadError" in rendered


def test_REQ_LAY_001_generic_layer_renders_with_source_and_layer():
    rendered = _render(
        mapcn.map(
            mapcn.map_layer(
                id="faults",
                source={"type": "geojson", "data": "/faults.geojson"},
                layer={"type": "line", "paint": {"line-color": "#ef4444"}},
                interactive=True,
                on_hover=_State.on_geo,
            )
        )
    )
    assert "MapcnLayer" in rendered
    assert "onHover" in rendered
    assert "interactive" in rendered


def test_REQ_LAY_002_source_can_be_the_id_of_a_style_source():
    layer = mapcn.map_layer(
        source="openmaptiles",
        layer={"type": "fill-extrusion", "source-layer": "building", "minzoom": 14},
    )
    assert "openmaptiles" in _prop(layer, "source")


def test_REQ_LAY_007_a_layer_without_a_type_is_rejected_at_creation():
    with pytest.raises(ValueError, match="layer.type is required"):
        mapcn.map_layer(
            source={"type": "geojson", "data": "/x.geojson"},
            layer={"paint": {"line-color": "#000"}},
        )


def test_REQ_LAY_007_a_source_that_is_neither_dict_nor_id_is_rejected():
    with pytest.raises(ValueError, match="source must be a dict or a source id"):
        mapcn.map_layer(source=42, layer={"type": "line"})


def test_REQ_LAY_007_source_and_layer_are_both_required():
    with pytest.raises(ValueError, match="source is required"):
        mapcn.map_layer(layer={"type": "line"})
    with pytest.raises(ValueError, match="layer is required"):
        mapcn.map_layer(source={"type": "geojson", "data": "/x.geojson"})


def test_REQ_LAY_007_a_state_var_source_is_not_validated_eagerly():
    # A Var resolves in the browser; validating it here would reject valid code.
    component = mapcn.map_layer(source=_State.viewport, layer={"type": "line"})
    assert isinstance(component, mapcn.MapLayer)


def test_REQ_HEA_003_weight_property_becomes_an_interpolated_weight():
    layer = mapcn.map_heatmap_layer(
        data={"type": "FeatureCollection", "features": []},
        weight_property="mag",
        weight_range=[4.0, 8.0],
    )
    assert json.loads(str(layer.weight)) == [
        "interpolate",
        ["linear"],
        ["get", "mag"],
        4.0,
        0,
        8.0,
        1,
    ]


def test_REQ_HEA_003_an_explicit_weight_wins_over_the_property():
    layer = mapcn.map_heatmap_layer(
        data="/quakes.geojson",
        weight=0.5,
        weight_property="mag",
        weight_range=[4.0, 8.0],
    )
    assert _prop(layer, "weight") == "0.5"


def test_REQ_HEA_003_a_weight_property_without_a_range_is_rejected():
    with pytest.raises(ValueError, match="weight_range"):
        mapcn.map_heatmap_layer(data="/quakes.geojson", weight_property="mag")


def test_REQ_HEA_004_max_zoom_fade_becomes_a_fading_opacity():
    layer = mapcn.map_heatmap_layer(data="/quakes.geojson", max_zoom_fade=8)
    assert json.loads(str(layer.opacity)) == [
        "interpolate",
        ["linear"],
        ["zoom"],
        7,
        1,
        8,
        0,
    ]


def test_REQ_HEA_004_an_explicit_opacity_wins_over_the_fade():
    layer = mapcn.map_heatmap_layer(
        data="/quakes.geojson", opacity=0.4, max_zoom_fade=8
    )
    assert _prop(layer, "opacity") == "0.4"


def test_REQ_HEA_001_a_heatmap_without_data_is_rejected():
    with pytest.raises(ValueError, match="data is required"):
        mapcn.map_heatmap_layer(radius=20)


def test_REQ_HEA_002_the_python_only_props_are_not_forwarded():
    rendered = _render(
        mapcn.map_heatmap_layer(
            data="/quakes.geojson",
            weight_property="mag",
            weight_range=[4.0, 8.0],
            max_zoom_fade=8,
        )
    )
    assert "MapcnHeatmapLayer" in rendered
    assert "weightProperty" not in rendered
    assert "maxZoomFade" not in rendered


def test_REQ_PNT_001_circle_layer_renders_with_data_driven_paint():
    rendered = _render(
        mapcn.map(
            mapcn.map_circle_layer(
                id="quakes",
                data={"type": "FeatureCollection", "features": []},
                promote_id="id",
                radius=["interpolate", ["linear"], ["get", "mag"], 4, 4, 7, 24],
                color=["step", ["get", "depth"], "#ef4444", 70, "#f97316"],
                hover_paint={"circle-stroke-width": 3},
                filter=["<=", ["get", "time"], 1690000000000],
                on_click=_State.on_geo,
            )
        )
    )
    assert "MapcnCircleLayer" in rendered
    assert "promoteId" in rendered
    assert "hoverPaint" in rendered
    assert "onClick" in rendered


def test_REQ_PNT_001_a_circle_layer_without_data_is_rejected():
    with pytest.raises(ValueError, match="data is required"):
        mapcn.map_circle_layer(radius=5)


def test_REQ_PNT_008_cluster_options_reach_the_component():
    layer = mapcn.map_circle_layer(
        data="/quakes.geojson", cluster=True, cluster_radius=80, cluster_max_zoom=12
    )
    assert _prop(layer, "cluster") == "true"
    assert _prop(layer, "cluster_radius") == "80"
    assert _prop(layer, "cluster_max_zoom") == "12"


def test_REQ_PNT_002_symbol_layer_renders_icons_and_text():
    rendered = _render(
        mapcn.map(
            mapcn.map_symbol_layer(
                id="cities",
                data={"type": "FeatureCollection", "features": []},
                images={"pin": "/pin.png"},
                icon_image="pin",
                icon_size=1.2,
                icon_allow_overlap=True,
                text_field=["get", "name"],
                text_size=12,
                text_color="#111827",
                on_click=_State.on_geo,
            ),
            glyphs_url="https://tiles.openfreemap.org/fonts",
        )
    )
    assert "MapcnSymbolLayer" in rendered
    assert "iconImage" in rendered
    assert "textField" in rendered
    assert "glyphsUrl" in rendered


def test_REQ_PNT_002_a_symbol_layer_without_data_is_rejected():
    with pytest.raises(ValueError, match="data is required"):
        mapcn.map_symbol_layer(icon_image="pin")
