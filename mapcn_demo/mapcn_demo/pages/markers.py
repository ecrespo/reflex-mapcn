"""Markers: content, tooltips, popups, labels and dragging."""

from __future__ import annotations

import reflex as rx
import reflex_mapcn as mapcn

from ..data import PLACES, Place
from ..layout import code, demo_frame, page, section

CATEGORY_COLORS = {
    "Landmark": "#f43f5e",
    "Park": "#22c55e",
    "Attraction": "#f59e0b",
    "University": "#3b82f6",
    "Museum": "#a855f7",
}


class MarkersState(rx.State):
    """State for the markers demos."""

    places: list[Place] = PLACES
    selected: str = ""
    hovered: str = ""

    # Draggable marker position.
    drag_lng: float = -66.9036
    drag_lat: float = 10.4806

    @rx.event
    def select(self, name: str):
        self.selected = name

    @rx.event
    def hover(self, name: str):
        self.hovered = name

    @rx.event
    def unhover(self):
        self.hovered = ""

    @rx.event
    def on_drag(self, lng_lat: dict):
        self.drag_lng = lng_lat["lng"]
        self.drag_lat = lng_lat["lat"]

    @rx.var
    def drag_label(self) -> str:
        return f"{self.drag_lat:.4f}, {self.drag_lng:.4f}"


def dot(color: str, size: str = "16px") -> rx.Component:
    """A shadcn-style dot marker."""
    return rx.box(
        width=size,
        height=size,
        border_radius="9999px",
        border="2px solid white",
        background_color=color,
        box_shadow="0 4px 6px -1px rgba(0,0,0,.25)",
        transition="transform 150ms",
        _hover={"transform": "scale(1.15)"},
    )


def place_marker(place: Place) -> rx.Component:
    color = rx.match(
        place.category,
        *[(name, value) for name, value in CATEGORY_COLORS.items()],
        "#64748b",
    )
    return mapcn.map_marker(
        mapcn.marker_content(
            dot(color, "18px"),
            mapcn.marker_label(place.category, position="bottom"),
        ),
        mapcn.marker_tooltip(place.name),
        mapcn.marker_popup(
            rx.vstack(
                rx.text(
                    place.category,
                    size="1",
                    color=rx.color("gray", 10),
                    style={"textTransform": "uppercase", "letterSpacing": "0.04em"},
                ),
                rx.text(place.name, weight="bold", size="2"),
                rx.text(
                    f"{place.lat}, {place.lng}",
                    size="1",
                    color=rx.color("gray", 10),
                    font_family="monospace",
                ),
                spacing="1",
                align="start",
            ),
            close_button=True,
        ),
        longitude=place.lng,
        latitude=place.lat,
        on_click=MarkersState.select(place.name),
        on_mouse_enter=MarkersState.hover(place.name),
        on_mouse_leave=MarkersState.unhover,
    )


@rx.page(route="/markers", title="Markers · reflex-mapcn")
def markers_page() -> rx.Component:
    return page(
        "Markers",
        "Compose `map_marker` with `marker_content`, `marker_tooltip`, "
        "`marker_popup` and `marker_label`. Every marker event delivers the "
        "marker position as {lng, lat}.",
        section(
            "Markers with tooltip, popup and label",
            "Hover a marker for its tooltip, click it for the popup. Events "
            "are wired to state: the selection and hover are shown below.",
            demo_frame(
                mapcn.map(
                    rx.foreach(MarkersState.places, place_marker),
                    mapcn.map_controls(),
                    center=[-66.885, 10.5],
                    zoom=12.4,
                ),
                rx.hstack(
                    rx.badge(
                        rx.icon("mouse-pointer-click", size=12),
                        rx.cond(
                            MarkersState.selected != "",
                            MarkersState.selected,
                            "Click a marker",
                        ),
                        variant="soft",
                    ),
                    rx.badge(
                        rx.icon("pointer", size=12),
                        rx.cond(
                            MarkersState.hovered != "",
                            MarkersState.hovered,
                            "Hover a marker",
                        ),
                        variant="soft",
                        color_scheme="gray",
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
class Place(rx.Base):
    id: int
    name: str
    category: str
    lng: float
    lat: float

def place_marker(place: Place):
    return mapcn.map_marker(
        mapcn.marker_content(
            rx.box(width="18px", height="18px", border_radius="9999px",
                   border="2px solid white", background_color="#f43f5e"),
            mapcn.marker_label(place.category, position="bottom"),
        ),
        mapcn.marker_tooltip(place.name),
        mapcn.marker_popup(rx.text(place.name, weight="bold"), close_button=True),
        longitude=place.lng,
        latitude=place.lat,
        on_click=MarkersState.select(place.name),
    )

mapcn.map(
    rx.foreach(MarkersState.places, place_marker),
    center=[-66.885, 10.5],
    zoom=12.4,
)
"""
            ),
        ),
        section(
            "Draggable marker",
            "Set `draggable=True` and listen to `on_drag` / `on_drag_end`. The "
            "coordinates below update while you drag.",
            demo_frame(
                mapcn.map(
                    mapcn.map_marker(
                        mapcn.marker_content(
                            rx.icon(
                                "map-pin",
                                size=32,
                                color=rx.color("accent", 10),
                                fill=rx.color("accent", 4),
                                style={"cursor": "move"},
                            ),
                        ),
                        mapcn.marker_popup(
                            rx.vstack(
                                rx.text("Coordinates", weight="bold", size="2"),
                                rx.text(
                                    MarkersState.drag_label,
                                    size="1",
                                    font_family="monospace",
                                ),
                                spacing="1",
                                align="start",
                            )
                        ),
                        longitude=MarkersState.drag_lng,
                        latitude=MarkersState.drag_lat,
                        draggable=True,
                        anchor="bottom",
                        on_drag=MarkersState.on_drag.throttle(50),
                        on_drag_end=MarkersState.on_drag,
                    ),
                    center=[-66.9036, 10.4806],
                    zoom=12,
                ),
                rx.badge(
                    rx.icon("move", size=12),
                    MarkersState.drag_label,
                    variant="soft",
                    position="absolute",
                    top="10px",
                    left="10px",
                    z_index="10",
                    font_family="monospace",
                ),
                height="420px",
            ),
            code(
                """
mapcn.map_marker(
    mapcn.marker_content(rx.icon("map-pin", size=32)),
    longitude=MarkersState.drag_lng,
    latitude=MarkersState.drag_lat,
    draggable=True,
    anchor="bottom",
    on_drag=MarkersState.on_drag.throttle(50),
    on_drag_end=MarkersState.on_drag,
)
"""
            ),
        ),
    )
