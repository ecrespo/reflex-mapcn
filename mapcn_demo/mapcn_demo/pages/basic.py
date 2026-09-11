"""Basic map, controlled viewport, blank basemap and custom styles."""

from __future__ import annotations

import reflex as rx
import reflex_mapcn as mapcn

from ..data import CARACAS, MAP_STYLES, WORLD_GEOJSON_URL
from ..layout import code, demo_frame, page, section


class BasicState(rx.State):
    """State for the controlled viewport and style switcher demos."""

    viewport: dict = {
        "center": [-66.9036, 10.4806],
        "zoom": 11,
        "bearing": 0,
        "pitch": 0,
    }
    style_name: str = "Default (CARTO)"

    @rx.event
    def set_viewport(self, viewport: dict):
        self.viewport = viewport

    @rx.event
    def set_style(self, name: str):
        self.style_name = name

    @rx.event
    def reset_view(self):
        self.viewport = {
            "center": [-66.9036, 10.4806],
            "zoom": 11,
            "bearing": 0,
            "pitch": 0,
        }

    @rx.event
    def tilt(self):
        self.viewport = {**self.viewport, "pitch": 60, "bearing": -25}

    @rx.var
    def styles(self) -> dict[str, str]:
        url = MAP_STYLES.get(self.style_name, "")
        if not url:
            # Empty dict == use the default CARTO basemap.
            return {}
        return {"light": url, "dark": url}

    @rx.var
    def center_label(self) -> str:
        center = self.viewport.get("center", [0, 0])
        return f"{center[1]:.4f}, {center[0]:.4f}"

    @rx.var
    def zoom_label(self) -> str:
        return f"{self.viewport.get('zoom', 0):.2f}"

    @rx.var
    def bearing_label(self) -> str:
        return f"{self.viewport.get('bearing', 0):.0f}°"

    @rx.var
    def pitch_label(self) -> str:
        return f"{self.viewport.get('pitch', 0):.0f}°"


def stat(label: str, value: rx.Var) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="1", color=rx.color("gray", 10)),
        rx.text(value, size="2", weight="medium", font_family="monospace"),
        spacing="0",
        align="start",
    )


@rx.page(route="/", title="Basic map · reflex-mapcn")
def basic_page() -> rx.Component:
    return page(
        "Basic map",
        "The Map component handles MapLibre GL setup, light/dark theming "
        "(it follows the Reflex color mode) and provides context to every "
        "child component. Give it a size through its parent box.",
        section(
            "Default basemap",
            "Free CARTO tiles. Toggle the color mode in the sidebar to see the "
            "basemap switch between Positron and Dark Matter.",
            demo_frame(mapcn.map(center=CARACAS, zoom=12)),
            code(
                """
import reflex_mapcn as mapcn

rx.box(
    mapcn.map(center=[-66.9036, 10.4806], zoom=12),
    height="420px",
)
"""
            ),
        ),
        section(
            "Controlled viewport",
            "Bind `viewport` and `on_viewport_change` to state. The map is "
            "driven by your state and reports every pan / zoom / rotate back. "
            "`on_viewport_change` fires continuously, so throttle it.",
            demo_frame(
                mapcn.map(
                    mapcn.map_controls(position="top-right", show_compass=True),
                    viewport=BasicState.viewport,
                    on_viewport_change=BasicState.set_viewport.throttle(100),
                ),
                rx.hstack(
                    stat("Center (lat, lng)", BasicState.center_label),
                    stat("Zoom", BasicState.zoom_label),
                    stat("Bearing", BasicState.bearing_label),
                    stat("Pitch", BasicState.pitch_label),
                    rx.spacer(),
                    rx.button(
                        "Tilt 3D", on_click=BasicState.tilt, size="1", variant="soft"
                    ),
                    rx.button(
                        "Reset",
                        on_click=BasicState.reset_view,
                        size="1",
                        variant="soft",
                    ),
                    spacing="5",
                    align="center",
                    position="absolute",
                    bottom="12px",
                    left="12px",
                    right="12px",
                    padding="10px 14px",
                    border_radius="10px",
                    background_color=rx.color("gray", 1),
                    border=f"1px solid {rx.color('gray', 5)}",
                    z_index="10",
                ),
            ),
            code(
                """
class BasicState(rx.State):
    viewport: dict = {"center": [-66.9, 10.48], "zoom": 11, "bearing": 0, "pitch": 0}

    @rx.event
    def set_viewport(self, viewport: dict):
        self.viewport = viewport

mapcn.map(
    viewport=BasicState.viewport,
    on_viewport_change=BasicState.set_viewport.throttle(100),
)
"""
            ),
        ),
        section(
            "Blank basemap",
            "`blank=True` renders a transparent, tile-less canvas - ideal for "
            "data visualisations where you draw your own layers.",
            demo_frame(
                mapcn.map(
                    mapcn.map_geojson(data=WORLD_GEOJSON_URL, line_paint=False),
                    blank=True,
                    center=[10, 25],
                    zoom=1,
                ),
                height="420px",
            ),
            code(
                """
mapcn.map(
    mapcn.map_geojson(data=WORLD_GEOJSON_URL, line_paint=False),
    blank=True,
    center=[10, 25],
)
"""
            ),
        ),
        section(
            "Custom styles",
            "Pass `styles={'light': ..., 'dark': ...}` with any MapLibre style "
            "URL or specification to replace the default CARTO basemap.",
            demo_frame(
                mapcn.map(
                    mapcn.map_controls(),
                    center=[-0.1276, 51.5074],
                    zoom=14,
                    styles=BasicState.styles,
                ),
                rx.box(
                    rx.select(
                        list(MAP_STYLES.keys()),
                        value=BasicState.style_name,
                        on_change=BasicState.set_style,
                        size="1",
                    ),
                    position="absolute",
                    top="10px",
                    left="10px",
                    z_index="10",
                ),
                height="420px",
            ),
            code(
                """
mapcn.map(
    center=[-0.1276, 51.5074],
    zoom=14,
    styles={
        "light": "https://tiles.openfreemap.org/styles/bright",
        "dark": "https://tiles.openfreemap.org/styles/bright",
    },
)
"""
            ),
        ),
    )
