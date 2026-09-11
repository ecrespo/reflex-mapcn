"""GeoJSON layers: world choropleth on a blank map and inline polygons."""

from __future__ import annotations

import reflex as rx
import reflex_mapcn as mapcn

from ..data import CARACAS_PARKS, WORLD_GEOJSON_URL
from ..layout import code, demo_frame, page, section

VISITED = {
    "Venezuela": "#1d4ed8",
    "Spain": "#2563eb",
    "Colombia": "#3b82f6",
    "United States": "#60a5fa",
    "Mexico": "#93c5fd",
    "Argentina": "#93c5fd",
    "Portugal": "#bfdbfe",
}

# Color countries by name; everything else keeps the theme-aware default.
WORLD_FILL_COLOR = [
    "match",
    ["get", "NAME_LONG"],
    *[item for name, color in VISITED.items() for item in (name, color)],
    "#9ca3af",
]


class GeoJSONState(rx.State):
    """State for the GeoJSON demos."""

    hovered_country: str = ""
    clicked_country: str = ""
    hovered_park: str = ""
    park_area: str = ""

    @rx.event
    def on_country_hover(self, event: dict | None):
        if event is None:
            self.hovered_country = ""
            return
        self.hovered_country = str(event["feature"]["properties"].get("NAME_LONG", ""))

    @rx.event
    def on_country_click(self, event: dict):
        self.clicked_country = str(event["feature"]["properties"].get("NAME_LONG", ""))

    @rx.event
    def on_park_hover(self, event: dict | None):
        if event is None:
            self.hovered_park = ""
            self.park_area = ""
            return
        props = event["feature"]["properties"]
        self.hovered_park = str(props.get("name", ""))
        self.park_area = f"{props.get('area_ha', '?')} ha"


@rx.page(route="/geojson", title="GeoJSON · reflex-mapcn")
def geojson_page() -> rx.Component:
    return page(
        "GeoJSON",
        "`map_geojson` renders a FeatureCollection, Feature, Geometry or URL "
        "as fill + outline layers. Style them with MapLibre paint objects, "
        "and use `promote_id` + `fill_hover_paint` for hover highlighting.",
        section(
            "World map on a blank basemap",
            "Countries loaded from a Natural Earth GeoJSON URL on a `blank` "
            "map. The fill uses a `match` expression, hover highlights the "
            "feature under the cursor and the events report its properties.",
            demo_frame(
                mapcn.map(
                    mapcn.map_geojson(
                        data=WORLD_GEOJSON_URL,
                        promote_id="NAME_LONG",
                        fill_paint={
                            "fill-color": WORLD_FILL_COLOR,
                            "fill-opacity": 0.85,
                        },
                        line_paint={"line-color": "#ffffff", "line-width": 0.5},
                        fill_hover_paint={"fill-color": "#f59e0b"},
                        interactive=True,
                        on_hover=GeoJSONState.on_country_hover,
                        on_click=GeoJSONState.on_country_click,
                    ),
                    mapcn.map_controls(show_zoom=True),
                    blank=True,
                    center=[-30, 20],
                    zoom=1.4,
                ),
                rx.hstack(
                    rx.badge(
                        rx.icon("pointer", size=12),
                        rx.cond(
                            GeoJSONState.hovered_country != "",
                            GeoJSONState.hovered_country,
                            "Hover a country",
                        ),
                        variant="soft",
                        color_scheme="gray",
                    ),
                    rx.badge(
                        rx.icon("mouse-pointer-click", size=12),
                        rx.cond(
                            GeoJSONState.clicked_country != "",
                            GeoJSONState.clicked_country,
                            "Click a country",
                        ),
                        variant="soft",
                    ),
                    spacing="2",
                    position="absolute",
                    top="10px",
                    left="10px",
                    z_index="10",
                ),
            ),
            code(
                """
mapcn.map(
    mapcn.map_geojson(
        data="https://.../ne_110m_admin_0_countries.geojson",
        promote_id="NAME_LONG",
        fill_paint={
            "fill-color": [
                "match", ["get", "NAME_LONG"],
                "Venezuela", "#1d4ed8",
                "#9ca3af",
            ],
        },
        line_paint={"line-color": "#ffffff", "line-width": 0.5},
        fill_hover_paint={"fill-color": "#f59e0b"},
        interactive=True,
        # payload: {"feature": {...}, "longitude", "latitude"} or None
        on_hover=GeoJSONState.on_country_hover,
        on_click=GeoJSONState.on_country_click,
    ),
    blank=True,
    center=[-30, 20],
    zoom=1.4,
)
"""
            ),
        ),
        section(
            "Inline polygons over the basemap",
            "A FeatureCollection defined in Python, rendered as translucent "
            "polygons with an outline on top of the street basemap.",
            demo_frame(
                mapcn.map(
                    mapcn.map_geojson(
                        data=CARACAS_PARKS,
                        promote_id="name",
                        fill_paint={"fill-color": "#22c55e", "fill-opacity": 0.3},
                        line_paint={"line-color": "#16a34a", "line-width": 2},
                        fill_hover_paint={"fill-opacity": 0.55},
                        interactive=True,
                        on_hover=GeoJSONState.on_park_hover,
                    ),
                    center=[-66.87, 10.495],
                    zoom=13,
                ),
                rx.cond(
                    GeoJSONState.hovered_park != "",
                    rx.hstack(
                        rx.icon("trees", size=14, color="#16a34a"),
                        rx.text(GeoJSONState.hovered_park, size="2", weight="medium"),
                        rx.text(
                            GeoJSONState.park_area, size="1", color=rx.color("gray", 10)
                        ),
                        spacing="2",
                        align="center",
                        position="absolute",
                        bottom="12px",
                        left="12px",
                        padding="6px 12px",
                        border_radius="8px",
                        background_color=rx.color("gray", 1),
                        border=f"1px solid {rx.color('gray', 5)}",
                        z_index="10",
                    ),
                ),
                height="420px",
            ),
            code(
                """
parks = {"type": "FeatureCollection", "features": [...]}

mapcn.map(
    mapcn.map_geojson(
        data=parks,
        promote_id="name",
        fill_paint={"fill-color": "#22c55e", "fill-opacity": 0.3},
        line_paint={"line-color": "#16a34a", "line-width": 2},
        fill_hover_paint={"fill-opacity": 0.55},
        interactive=True,
        on_hover=GeoJSONState.on_park_hover,
    ),
    center=[-66.87, 10.495],
    zoom=13,
)
"""
            ),
        ),
    )
