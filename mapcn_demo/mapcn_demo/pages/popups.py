"""Standalone popups driven by state."""

from __future__ import annotations

import reflex as rx
import reflex_mapcn as mapcn

from ..layout import code, demo_frame, page, section


class PopupsState(rx.State):
    """State for the standalone popup demo."""

    show_popup: bool = True

    # Popup opened wherever the user clicks on the map.
    click_lng: float = 0.0
    click_lat: float = 0.0
    has_click: bool = False

    @rx.event
    def open_popup(self):
        self.show_popup = True

    @rx.event
    def close_popup(self):
        self.show_popup = False

    @rx.event
    def on_map_click(self, event: dict):
        self.click_lng = event["lng"]
        self.click_lat = event["lat"]
        self.has_click = True

    @rx.event
    def clear_click(self):
        self.has_click = False

    @rx.var
    def click_label(self) -> str:
        return f"{self.click_lat:.5f}, {self.click_lng:.5f}"


@rx.page(route="/popups", title="Popups · reflex-mapcn")
def popups_page() -> rx.Component:
    return page(
        "Popups",
        "`map_popup` renders a popup at a coordinate without a marker. "
        "Control its visibility from state and react to `on_close`.",
        section(
            "Standalone popup",
            "The popup is rendered while `show_popup` is true. Closing it "
            "(close button, click outside) fires `on_close`.",
            demo_frame(
                mapcn.map(
                    rx.cond(
                        PopupsState.show_popup,
                        mapcn.map_popup(
                            rx.vstack(
                                rx.heading("Caracas", size="3"),
                                rx.text(
                                    "Capital of Venezuela, nestled in a valley of the "
                                    "Cordillera de la Costa at ~900 m.",
                                    size="1",
                                    color=rx.color("gray", 11),
                                ),
                                rx.button(
                                    "Close",
                                    size="1",
                                    variant="outline",
                                    width="100%",
                                    on_click=PopupsState.close_popup,
                                ),
                                spacing="2",
                                align="start",
                            ),
                            longitude=-66.9036,
                            latitude=10.4806,
                            close_button=True,
                            close_on_click=False,
                            focus_after_open=False,
                            on_close=PopupsState.close_popup,
                        ),
                    ),
                    center=[-66.9036, 10.4806],
                    zoom=13,
                ),
                rx.cond(
                    ~PopupsState.show_popup,
                    rx.button(
                        "Show popup",
                        size="1",
                        on_click=PopupsState.open_popup,
                        position="absolute",
                        bottom="16px",
                        left="16px",
                        z_index="10",
                    ),
                ),
                height="420px",
            ),
            code(
                """
class PopupsState(rx.State):
    show_popup: bool = True

    @rx.event
    def close_popup(self):
        self.show_popup = False

mapcn.map(
    rx.cond(
        PopupsState.show_popup,
        mapcn.map_popup(
            rx.heading("Caracas", size="3"),
            longitude=-66.9036,
            latitude=10.4806,
            close_button=True,
            close_on_click=False,
            on_close=PopupsState.close_popup,
        ),
    ),
    center=[-66.9036, 10.4806],
    zoom=13,
)
"""
            ),
        ),
        section(
            "Popup on map click",
            "`map.on_click` (a Reflex extra) delivers {lng, lat, point}. "
            "Click anywhere to open a popup at that position.",
            demo_frame(
                mapcn.map(
                    rx.cond(
                        PopupsState.has_click,
                        mapcn.map_popup(
                            rx.vstack(
                                rx.text(
                                    "You clicked at",
                                    size="1",
                                    color=rx.color("gray", 10),
                                ),
                                rx.text(
                                    PopupsState.click_label,
                                    size="2",
                                    font_family="monospace",
                                ),
                                spacing="1",
                                align="start",
                            ),
                            longitude=PopupsState.click_lng,
                            latitude=PopupsState.click_lat,
                            close_button=True,
                            close_on_click=False,
                            focus_after_open=False,
                            on_close=PopupsState.clear_click,
                        ),
                    ),
                    center=[-66.9036, 10.4806],
                    zoom=12,
                    on_click=PopupsState.on_map_click,
                ),
                height="420px",
            ),
            code(
                """
mapcn.map(
    rx.cond(
        PopupsState.has_click,
        mapcn.map_popup(
            rx.text(PopupsState.click_label),
            longitude=PopupsState.click_lng,
            latitude=PopupsState.click_lat,
            close_button=True,
            on_close=PopupsState.clear_click,
        ),
    ),
    on_click=PopupsState.on_map_click,   # receives {"lng", "lat", "point"}
)
"""
            ),
        ),
    )
