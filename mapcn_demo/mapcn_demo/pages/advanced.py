"""Advanced usage: camera commands, event log, 3D view and globe."""

from __future__ import annotations

import reflex as rx
import reflex_mapcn as mapcn

from ..data import DESTINATIONS, HUB
from ..layout import code, demo_frame, page, section

CITIES = [HUB, *DESTINATIONS]


class AdvancedState(rx.State):
    """State for the advanced demo."""

    command: dict = {}
    _seq: int = 0
    events: list[str] = []
    viewport: dict = {}

    def _push(self, command: dict):
        self._seq += 1
        self.command = {**command, "seq": self._seq}

    @rx.event
    def fly_to(self, lng: float, lat: float, name: str):
        self._push(
            mapcn.camera_command("flyTo", center=[lng, lat], zoom=10, duration=2000)
        )
        self._log(f"flyTo {name}")

    @rx.event
    def view_3d(self):
        self._push(mapcn.camera_command("easeTo", pitch=60, bearing=-20, duration=1000))
        self._log("easeTo pitch=60 bearing=-20")

    @rx.event
    def reset_camera(self):
        self._push(mapcn.camera_command("easeTo", pitch=0, bearing=0, duration=1000))
        self._log("easeTo reset")

    @rx.event
    def fit_all(self):
        lngs = [c["lng"] for c in CITIES]
        lats = [c["lat"] for c in CITIES]
        self._push(
            mapcn.camera_command(
                "fitBounds",
                bounds=[[min(lngs), min(lats)], [max(lngs), max(lats)]],
                padding=60,
                duration=1500,
            )
        )
        self._log("fitBounds all cities")

    @rx.event
    def on_move_end(self, viewport: dict):
        self.viewport = viewport
        self._log(
            f"moveend z={viewport['zoom']:.2f} "
            f"c=({viewport['center'][1]:.3f}, {viewport['center'][0]:.3f})"
        )

    @rx.event
    def on_load(self, viewport: dict):
        self.viewport = viewport
        self._log("map loaded")

    @rx.event
    def on_map_click(self, event: dict):
        self._log(f"click ({event['lat']:.3f}, {event['lng']:.3f})")

    @rx.event
    def clear_log(self):
        self.events = []

    def _log(self, message: str):
        self.events = [message, *self.events][:8]

    @rx.var
    def pitch_label(self) -> str:
        return f"{self.viewport.get('pitch', 0):.0f}°"

    @rx.var
    def bearing_label(self) -> str:
        return f"{self.viewport.get('bearing', 0):.0f}°"


def city_button(city: dict) -> rx.Component:
    return rx.button(
        city["name"],
        size="1",
        variant="soft",
        on_click=AdvancedState.fly_to(city["lng"], city["lat"], city["name"]),
    )


@rx.page(route="/advanced", title="Advanced · reflex-mapcn")
def advanced_page() -> rx.Component:
    return page(
        "Advanced",
        "Reflex-specific extras on top of mapcn: an imperative `map_camera` "
        "driven from state, lifecycle events (`on_load`, `on_move_end`, "
        "`on_click`) and the globe projection.",
        section(
            "Camera commands and event log",
            "`map_camera(command=State.command)` runs flyTo / easeTo / jumpTo / "
            "fitBounds whenever the command changes. The panel on the right "
            "logs the events the map sends back to the backend.",
            rx.hstack(
                *[city_button(city) for city in CITIES],
                rx.spacer(),
                rx.button(
                    rx.icon("mountain", size=14),
                    "3D view",
                    size="1",
                    on_click=AdvancedState.view_3d,
                ),
                rx.button(
                    rx.icon("rotate-ccw", size=14),
                    "Reset",
                    size="1",
                    variant="outline",
                    on_click=AdvancedState.reset_camera,
                ),
                rx.button(
                    rx.icon("maximize", size=14),
                    "Fit all",
                    size="1",
                    variant="outline",
                    on_click=AdvancedState.fit_all,
                ),
                spacing="2",
                wrap="wrap",
                width="100%",
            ),
            demo_frame(
                mapcn.map(
                    mapcn.map_camera(command=AdvancedState.command),
                    mapcn.map_controls(show_compass=True),
                    *[
                        mapcn.map_marker(
                            mapcn.marker_content(
                                rx.box(
                                    width="12px",
                                    height="12px",
                                    border_radius="9999px",
                                    border="2px solid white",
                                    background_color="#3b82f6",
                                    box_shadow="0 2px 4px rgba(0,0,0,.3)",
                                ),
                                mapcn.marker_label(city["name"], position="top"),
                            ),
                            mapcn.marker_tooltip(city["name"]),
                            longitude=city["lng"],
                            latitude=city["lat"],
                            on_click=AdvancedState.fly_to(
                                city["lng"], city["lat"], city["name"]
                            ),
                        )
                        for city in CITIES
                    ],
                    center=[HUB["lng"], HUB["lat"]],
                    zoom=2.5,
                    on_load=AdvancedState.on_load,
                    on_move_end=AdvancedState.on_move_end,
                    on_click=AdvancedState.on_map_click,
                ),
                rx.vstack(
                    rx.hstack(
                        rx.text("Events", size="1", weight="medium"),
                        rx.spacer(),
                        rx.text(
                            "pitch ",
                            AdvancedState.pitch_label,
                            " · bearing ",
                            AdvancedState.bearing_label,
                            size="1",
                            color=rx.color("gray", 10),
                            font_family="monospace",
                        ),
                        rx.icon_button(
                            rx.icon("trash-2", size=12),
                            size="1",
                            variant="ghost",
                            on_click=AdvancedState.clear_log,
                        ),
                        width="100%",
                        align="center",
                    ),
                    rx.foreach(
                        AdvancedState.events,
                        lambda event: rx.text(
                            event,
                            size="1",
                            font_family="monospace",
                            color=rx.color("gray", 11),
                        ),
                    ),
                    spacing="1",
                    align="start",
                    width="300px",
                    position="absolute",
                    top="12px",
                    left="12px",
                    padding="10px 12px",
                    border_radius="10px",
                    background_color=rx.color("gray", 1),
                    border=f"1px solid {rx.color('gray', 5)}",
                    z_index="10",
                ),
                height="520px",
            ),
            code(
                """
class AdvancedState(rx.State):
    command: dict = {}
    _seq: int = 0

    @rx.event
    def fly_to(self, lng: float, lat: float):
        self._seq += 1
        self.command = mapcn.camera_command(
            "flyTo", center=[lng, lat], zoom=10, duration=2000, seq=self._seq
        )

    @rx.event
    def on_move_end(self, viewport: dict):
        ...

mapcn.map(
    mapcn.map_camera(command=AdvancedState.command),
    on_load=AdvancedState.on_load,
    on_move_end=AdvancedState.on_move_end,
    on_click=AdvancedState.on_map_click,
)
"""
            ),
        ),
        section(
            "Globe projection with a custom style",
            "`projection={'type': 'globe'}` plus the OpenFreeMap Liberty style "
            "and a tilted initial camera.",
            demo_frame(
                mapcn.map(
                    mapcn.map_controls(show_compass=True, position="top-right"),
                    center=[-66.9, 10.5],
                    zoom=3,
                    pitch=35,
                    projection={"type": "globe"},
                    styles={
                        "light": "https://tiles.openfreemap.org/styles/liberty",
                        "dark": "https://tiles.openfreemap.org/styles/liberty",
                    },
                ),
                height="460px",
            ),
            code(
                """
mapcn.map(
    center=[-66.9, 10.5],
    zoom=3,
    pitch=35,
    projection={"type": "globe"},
    styles={"light": LIBERTY, "dark": LIBERTY},
)
"""
            ),
        ),
    )
