"""Clusters: native MapLibre clustering for large point datasets."""

from __future__ import annotations

import reflex as rx
import reflex_mapcn as mapcn

from ..data import EARTHQUAKES_URL
from ..layout import code, demo_frame, page, section


class ClustersState(rx.State):
    """State for the clusters demo."""

    selected_lng: float = 0.0
    selected_lat: float = 0.0
    magnitude: str = ""
    tsunami: str = ""
    has_selection: bool = False

    @rx.event
    def on_point_click(self, feature: dict, coordinates: list):
        props = feature.get("properties", {})
        self.selected_lng = coordinates[0]
        self.selected_lat = coordinates[1]
        self.magnitude = str(props.get("mag", "?"))
        self.tsunami = "Yes" if props.get("tsunami") == 1 else "No"
        self.has_selection = True

    @rx.event
    def close(self):
        self.has_selection = False


@rx.page(route="/clusters", title="Clusters · reflex-mapcn")
def clusters_page() -> rx.Component:
    return page(
        "Clusters",
        "`map_cluster_layer` uses MapLibre's native clustering to render "
        "thousands of points efficiently. Clicking a cluster zooms into it; "
        "clicking a point fires `on_point_click`.",
        section(
            "Earthquakes",
            "The USGS earthquakes sample (~1,000 points) loaded from a URL. "
            "Click a single point to open a popup with its properties.",
            demo_frame(
                mapcn.map(
                    mapcn.map_cluster_layer(
                        data=EARTHQUAKES_URL,
                        cluster_radius=50,
                        cluster_max_zoom=14,
                        on_point_click=ClustersState.on_point_click,
                    ),
                    rx.cond(
                        ClustersState.has_selection,
                        mapcn.map_popup(
                            rx.vstack(
                                rx.hstack(
                                    rx.text(
                                        "Magnitude",
                                        size="1",
                                        color=rx.color("gray", 10),
                                    ),
                                    rx.text(
                                        ClustersState.magnitude,
                                        size="1",
                                        weight="medium",
                                    ),
                                    spacing="1",
                                ),
                                rx.hstack(
                                    rx.text(
                                        "Tsunami", size="1", color=rx.color("gray", 10)
                                    ),
                                    rx.text(ClustersState.tsunami, size="1"),
                                    spacing="1",
                                ),
                                spacing="1",
                                align="start",
                            ),
                            longitude=ClustersState.selected_lng,
                            latitude=ClustersState.selected_lat,
                            close_button=True,
                            close_on_click=False,
                            focus_after_open=False,
                            on_close=ClustersState.close,
                            width="140px",
                        ),
                    ),
                    mapcn.map_controls(),
                    center=[-103.59, 40.66],
                    zoom=3.4,
                    fade_duration=0,
                ),
            ),
            code(
                """
mapcn.map(
    mapcn.map_cluster_layer(
        data="https://maplibre.org/maplibre-gl-js/docs/assets/earthquakes.geojson",
        cluster_radius=50,
        cluster_max_zoom=14,
        on_point_click=ClustersState.on_point_click,   # (feature, [lng, lat])
    ),
    rx.cond(
        ClustersState.has_selection,
        mapcn.map_popup(
            ...,
            longitude=ClustersState.selected_lng,
            latitude=ClustersState.selected_lat,
        ),
    ),
    center=[-103.59, 40.66],
    zoom=3.4,
)
"""
            ),
        ),
        section(
            "Custom colors and thresholds",
            "`cluster_colors` and `cluster_thresholds` control the step "
            "scale for the cluster circles; `point_color` styles single points.",
            demo_frame(
                mapcn.map(
                    mapcn.map_cluster_layer(
                        data=EARTHQUAKES_URL,
                        cluster_radius=70,
                        cluster_colors=["#f59e0b", "#ea580c", "#b91c1c"],
                        cluster_thresholds=[50, 300],
                        point_color="#f59e0b",
                    ),
                    mapcn.map_controls(),
                    center=[-150, 55],
                    zoom=2.5,
                    fade_duration=0,
                ),
                height="420px",
            ),
            code(
                """
mapcn.map_cluster_layer(
    data=EARTHQUAKES_URL,
    cluster_radius=70,
    cluster_colors=["#f59e0b", "#ea580c", "#b91c1c"],   # small, medium, large
    cluster_thresholds=[50, 300],                       # medium, large
    point_color="#f59e0b",
)
"""
            ),
        ),
    )
