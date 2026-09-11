"""Map controls: zoom, compass, locate and fullscreen."""

from __future__ import annotations

import reflex as rx
import reflex_mapcn as mapcn

from ..layout import code, demo_frame, page, section


class ControlsState(rx.State):
    """State for the controls demo."""

    position: str = "top-right"
    show_zoom: bool = True
    show_compass: bool = True
    show_locate: bool = True
    show_fullscreen: bool = True
    located: str = ""

    @rx.event
    def set_position(self, value: str):
        self.position = value

    @rx.event
    def toggle_zoom(self, value: bool):
        self.show_zoom = value

    @rx.event
    def toggle_compass(self, value: bool):
        self.show_compass = value

    @rx.event
    def toggle_locate(self, value: bool):
        self.show_locate = value

    @rx.event
    def toggle_fullscreen(self, value: bool):
        self.show_fullscreen = value

    @rx.event
    def on_locate(self, coords: dict):
        self.located = f"{coords['latitude']:.4f}, {coords['longitude']:.4f}"


def toggle(label: str, checked: rx.Var, on_change) -> rx.Component:
    return rx.hstack(
        rx.switch(checked=checked, on_change=on_change, size="1"),
        rx.text(label, size="2"),
        spacing="2",
        align="center",
    )


@rx.page(route="/controls", title="Controls · reflex-mapcn")
def controls_page() -> rx.Component:
    return page(
        "Controls",
        "`map_controls` adds zoom, compass, geolocate and fullscreen buttons. "
        "Choose the corner and which buttons to show.",
        section(
            "Configurable controls",
            "Use the switches to toggle each control. `on_locate` receives the "
            "user's coordinates after a successful geolocation.",
            rx.hstack(
                rx.select(
                    ["top-left", "top-right", "bottom-left", "bottom-right"],
                    value=ControlsState.position,
                    on_change=ControlsState.set_position,
                    size="1",
                ),
                toggle("Zoom", ControlsState.show_zoom, ControlsState.toggle_zoom),
                toggle(
                    "Compass", ControlsState.show_compass, ControlsState.toggle_compass
                ),
                toggle(
                    "Locate", ControlsState.show_locate, ControlsState.toggle_locate
                ),
                toggle(
                    "Fullscreen",
                    ControlsState.show_fullscreen,
                    ControlsState.toggle_fullscreen,
                ),
                rx.spacer(),
                rx.cond(
                    ControlsState.located != "",
                    rx.badge(
                        rx.icon("locate", size=12),
                        ControlsState.located,
                        variant="soft",
                    ),
                ),
                spacing="4",
                align="center",
                width="100%",
                wrap="wrap",
            ),
            demo_frame(
                mapcn.map(
                    mapcn.map_controls(
                        position=ControlsState.position,
                        show_zoom=ControlsState.show_zoom,
                        show_compass=ControlsState.show_compass,
                        show_locate=ControlsState.show_locate,
                        show_fullscreen=ControlsState.show_fullscreen,
                        on_locate=ControlsState.on_locate,
                    ),
                    center=[2.3522, 48.8566],
                    zoom=10,
                    pitch=30,
                    bearing=-15,
                ),
            ),
            code(
                """
mapcn.map(
    mapcn.map_controls(
        position="top-right",
        show_zoom=True,
        show_compass=True,
        show_locate=True,
        show_fullscreen=True,
        on_locate=ControlsState.on_locate,   # {"longitude": ..., "latitude": ...}
    ),
    center=[2.3522, 48.8566],
    zoom=10,
)
"""
            ),
        ),
    )
