"""Arcs: curved connections on a globe and interactive hover/click."""

from __future__ import annotations

import reflex as rx
import reflex_mapcn as mapcn

from ..data import ARCS, DESTINATIONS, HUB, LANE_ENDPOINTS, LANES, MODE_COLORS
from ..layout import code, demo_frame, page, section

MODE_COLOR_EXPRESSION = [
    "match",
    ["get", "mode"],
    "air",
    MODE_COLORS["air"],
    "sea",
    MODE_COLORS["sea"],
    "#888",
]


class ArcsState(rx.State):
    """State for the interactive arcs demo."""

    hovered: dict = {}
    hover_lng: float = 0.0
    hover_lat: float = 0.0
    clicked: str = ""

    @rx.event
    def on_hover(self, event: dict | None):
        if event is None:
            self.hovered = {}
            return
        self.hovered = event["arc"]
        self.hover_lng = event["longitude"]
        self.hover_lat = event["latitude"]

    @rx.event
    def on_click(self, event: dict):
        arc = event["arc"]
        self.clicked = f"{arc['origin']} → {arc['destination']} ({arc['volume']})"

    @rx.var
    def has_hover(self) -> bool:
        return bool(self.hovered)

    @rx.var
    def hover_title(self) -> str:
        if not self.hovered:
            return ""
        return f"{self.hovered.get('origin')} → {self.hovered.get('destination')}"

    @rx.var
    def hover_volume(self) -> str:
        return str(self.hovered.get("volume", ""))

    @rx.var
    def hover_color(self) -> str:
        return MODE_COLORS.get(self.hovered.get("mode", ""), "#888")


def city_marker(name: str, lng: float, lat: float, size: str = "8px") -> rx.Component:
    return mapcn.map_marker(
        mapcn.marker_content(
            rx.box(
                width=size,
                height=size,
                border_radius="9999px",
                border="2px solid white",
                background_color="#3b82f6",
            ),
            mapcn.marker_label(name, position="top"),
        ),
        longitude=lng,
        latitude=lat,
    )


def legend_item(label: str, color: str) -> rx.Component:
    return rx.hstack(
        rx.box(
            width="6px", height="6px", border_radius="9999px", background_color=color
        ),
        rx.text(label, size="1"),
        spacing="1",
        align="center",
    )


@rx.page(route="/arcs", title="Arcs · reflex-mapcn")
def arcs_page() -> rx.Component:
    return page(
        "Arcs",
        "`map_arc` draws curved lines between coordinate pairs. Each datum "
        "needs an `id`, `from` and `to`; any other field is available to "
        "MapLibre expressions via ['get', 'field'].",
        section(
            "Globe with arcs",
            "Flights from Caracas rendered with `projection={'type': 'globe'}` "
            "and a dashed line paint.",
            demo_frame(
                mapcn.map(
                    mapcn.map_arc(
                        data=ARCS,
                        paint={"line-color": "#3b82f6", "line-dasharray": [2, 2]},
                        interactive=False,
                    ),
                    city_marker(HUB["name"], HUB["lng"], HUB["lat"], size="12px"),
                    *[city_marker(d["name"], d["lng"], d["lat"]) for d in DESTINATIONS],
                    center=[HUB["lng"], HUB["lat"]],
                    zoom=1.4,
                    projection={"type": "globe"},
                ),
            ),
            code(
                """
arcs = [
    {"id": "MAD", "from": [-66.9036, 10.4806], "to": [-3.7038, 40.4168]},
    {"id": "MIA", "from": [-66.9036, 10.4806], "to": [-80.1918, 25.7617]},
]

mapcn.map(
    mapcn.map_arc(data=arcs, paint={"line-color": "#3b82f6", "line-dasharray": [2, 2]}),
    center=[-66.9, 10.48],
    zoom=1.4,
    projection={"type": "globe"},
)
"""
            ),
        ),
        section(
            "Interactive arcs",
            "Per-feature colors through a `match` expression, `hover_paint` "
            "for the hovered arc and `on_hover` / `on_click` events that "
            "deliver the arc datum plus the cursor position.",
            demo_frame(
                mapcn.map(
                    mapcn.map_arc(
                        data=LANES,
                        paint={"line-color": MODE_COLOR_EXPRESSION, "line-width": 1.5},
                        hover_paint={"line-width": 3, "line-opacity": 1},
                        on_hover=ArcsState.on_hover,
                        on_click=ArcsState.on_click,
                    ),
                    *[
                        mapcn.map_marker(
                            mapcn.marker_content(
                                rx.box(
                                    width="8px",
                                    height="8px",
                                    border_radius="9999px",
                                    background_color=rx.color("gray", 12),
                                    opacity="0.8",
                                ),
                                mapcn.marker_label(p["name"], position="top"),
                            ),
                            longitude=p["lng"],
                            latitude=p["lat"],
                        )
                        for p in LANE_ENDPOINTS
                    ],
                    rx.cond(
                        ArcsState.has_hover,
                        mapcn.map_popup(
                            rx.hstack(
                                rx.box(
                                    width="6px",
                                    height="6px",
                                    border_radius="9999px",
                                    background_color=ArcsState.hover_color,
                                ),
                                rx.text(
                                    ArcsState.hover_title, size="1", weight="medium"
                                ),
                                rx.text(
                                    ArcsState.hover_volume,
                                    size="1",
                                    color=rx.color("gray", 10),
                                    border_left=f"1px solid {rx.color('gray', 6)}",
                                    padding_left="8px",
                                ),
                                spacing="2",
                                align="center",
                            ),
                            longitude=ArcsState.hover_lng,
                            latitude=ArcsState.hover_lat,
                            offset=12,
                            close_on_click=False,
                            focus_after_open=False,
                            padding="6px 10px",
                        ),
                    ),
                    center=[20, 20],
                    zoom=0.8,
                ),
                rx.hstack(
                    legend_item("Air", MODE_COLORS["air"]),
                    rx.box(
                        width="1px", height="12px", background_color=rx.color("gray", 6)
                    ),
                    legend_item("Sea", MODE_COLORS["sea"]),
                    spacing="3",
                    align="center",
                    position="absolute",
                    bottom="12px",
                    left="12px",
                    padding="2px 12px",
                    border_radius="9999px",
                    background_color=rx.color("gray", 1),
                    border=f"1px solid {rx.color('gray', 5)}",
                    z_index="10",
                ),
                rx.cond(
                    ArcsState.clicked != "",
                    rx.badge(
                        rx.icon("mouse-pointer-click", size=12),
                        ArcsState.clicked,
                        variant="soft",
                        position="absolute",
                        top="12px",
                        left="12px",
                        z_index="10",
                    ),
                ),
            ),
            code(
                """
mapcn.map_arc(
    data=LANES,   # each lane has id/from/to plus origin/destination/volume/mode
    paint={
        "line-color": [
            "match", ["get", "mode"],
            "air", "#a78bfa",
            "sea", "#34d399",
            "#888",
        ],
        "line-width": 1.5,
    },
    hover_paint={"line-width": 3, "line-opacity": 1},
    on_hover=ArcsState.on_hover,   # event dict or None
    on_click=ArcsState.on_click,   # {"arc": {...}, "longitude": ..., "latitude": ...}
)
"""
            ),
        ),
    )
