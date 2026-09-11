"""Routes: lines, progress tracking, route markers and route selection."""

from __future__ import annotations

import dataclasses

import httpx
import reflex as rx
import reflex_mapcn as mapcn

from ..data import NYC_ROUTE, NYC_STOPS, SF_ROUTE
from ..layout import code, demo_frame, page, section

START = {"name": "Amsterdam", "lng": 4.9041, "lat": 52.3676}
END = {"name": "Rotterdam", "lng": 4.4777, "lat": 51.9244}
ROUTE_COLOR = "#3b82f6"


@dataclasses.dataclass
class RouteOption:
    """One OSRM alternative."""

    index: int
    coordinates: list[list[float]]
    duration: str
    distance: str


class RoutesState(rx.State):
    """State for the routes demos."""

    # Progress demo (0-100).
    progress_pct: int = 45

    # OSRM demo.
    routes: list[RouteOption] = []
    selected_index: int = 0
    loading: bool = False
    error: str = ""

    @rx.event
    def set_progress(self, value: list):
        self.progress_pct = int(value[0])

    @rx.var
    def progress(self) -> float:
        return self.progress_pct / 100

    @rx.var
    def progress_label(self) -> str:
        return f"{self.progress_pct}%"

    @rx.event
    def select_route(self, index: int):
        self.selected_index = index

    @rx.event(background=True)
    async def fetch_routes(self):
        async with self:
            if self.routes:
                return
            self.loading = True
            self.error = ""
        url = (
            "https://router.project-osrm.org/route/v1/driving/"
            f"{START['lng']},{START['lat']};{END['lng']},{END['lat']}"
            "?overview=full&geometries=geojson&alternatives=true"
        )
        options: list[RouteOption] = []
        error = ""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url)
                response.raise_for_status()
                payload = response.json()
            for index, route in enumerate(payload.get("routes", [])):
                options.append(
                    RouteOption(
                        index=index,
                        coordinates=route["geometry"]["coordinates"],
                        duration=_format_duration(route["duration"]),
                        distance=_format_distance(route["distance"]),
                    )
                )
        except Exception as exc:  # noqa: BLE001 - demo only
            error = f"Could not fetch routes from OSRM: {exc}"
        async with self:
            self.routes = options
            self.error = error
            self.loading = False


def _format_duration(seconds: float) -> str:
    mins = round(seconds / 60)
    if mins < 60:
        return f"{mins} min"
    return f"{mins // 60}h {mins % 60}m"


def _format_distance(meters: float) -> str:
    if meters < 1000:
        return f"{round(meters)} m"
    return f"{meters / 1000:.1f} km"


def numbered_marker(stop: dict, index: int) -> rx.Component:
    return mapcn.map_marker(
        mapcn.marker_content(
            rx.center(
                rx.text(index + 1, size="1", weight="bold", color="white"),
                width="20px",
                height="20px",
                border_radius="9999px",
                border="2px solid white",
                background_color=ROUTE_COLOR,
                box_shadow="0 4px 6px -1px rgba(0,0,0,.25)",
            )
        ),
        mapcn.marker_tooltip(stop["name"]),
        longitude=stop["lng"],
        latitude=stop["lat"],
    )


def route_option(route: RouteOption) -> rx.Component:
    is_active = route.index == RoutesState.selected_index
    return rx.hstack(
        rx.box(
            width="2px",
            height="16px",
            border_radius="9999px",
            background_color=ROUTE_COLOR,
            opacity=rx.cond(is_active, "1", "0.35"),
        ),
        rx.text(
            route.duration,
            size="2",
            weight="medium",
            color=rx.cond(is_active, rx.color("gray", 12), rx.color("gray", 10)),
        ),
        rx.spacer(),
        rx.text(route.distance, size="1", color=rx.color("gray", 10)),
        spacing="2",
        align="center",
        width="100%",
        padding="6px 8px",
        border_radius="6px",
        cursor="pointer",
        background_color=rx.cond(is_active, rx.color("gray", 4), "transparent"),
        _hover={"background_color": rx.color("gray", 3)},
        on_click=RoutesState.select_route(route.index),
    )


def osrm_route(route: RouteOption) -> rx.Component:
    return mapcn.map_route(
        coordinates=route.coordinates,
        active=route.index == RoutesState.selected_index,
        color=ROUTE_COLOR,
        width=5,
        opacity=0.35,
        active_width=6,
        active_opacity=1.0,
        on_click=RoutesState.select_route(route.index),
    )


def endpoint_marker(point: dict, filled: bool) -> rx.Component:
    return mapcn.map_marker(
        mapcn.marker_content(
            rx.box(
                width="14px",
                height="14px",
                border_radius="9999px",
                border=f"2px solid {rx.color('gray', 12)}",
                background_color=rx.color("gray", 12)
                if filled
                else rx.color("gray", 1),
                box_shadow="0 2px 4px rgba(0,0,0,.25)",
            )
        ),
        mapcn.marker_tooltip(point["name"]),
        longitude=point["lng"],
        latitude=point["lat"],
    )


@rx.page(
    route="/routes", title="Routes · reflex-mapcn", on_load=RoutesState.fetch_routes
)
def routes_page() -> rx.Component:
    return page(
        "Routes",
        "`map_route` draws a line through `[lng, lat]` coordinates. Add "
        "`route_progress` and `route_marker` children to visualise progress "
        "along it, and use `active` to highlight one of several routes.",
        section(
            "Basic route with stops",
            "A polyline plus numbered markers at each stop.",
            demo_frame(
                mapcn.map(
                    mapcn.map_route(
                        coordinates=NYC_ROUTE, color=ROUTE_COLOR, width=4, opacity=0.8
                    ),
                    *[numbered_marker(stop, i) for i, stop in enumerate(NYC_STOPS)],
                    mapcn.map_controls(),
                    center=[-73.98, 40.75],
                    zoom=11.2,
                ),
                height="420px",
            ),
            code(
                """
route = [
    [-74.006, 40.7128], [-73.9857, 40.7484],
    [-73.9772, 40.7527], [-73.9654, 40.7829],
]

mapcn.map(
    mapcn.map_route(coordinates=route, color="#3b82f6", width=4, opacity=0.8),
    center=[-73.98, 40.75],
    zoom=11.2,
)
"""
            ),
        ),
        section(
            "Route progress",
            "Bind `progress` (0-1) to state. `route_progress` paints the "
            "traveled part and `route_marker(at='progress')` follows it.",
            demo_frame(
                mapcn.map(
                    mapcn.map_route(
                        mapcn.route_progress(color=ROUTE_COLOR, width=5, opacity=1.0),
                        mapcn.route_marker(
                            mapcn.marker_content(
                                rx.box(
                                    width="14px",
                                    height="14px",
                                    border_radius="9999px",
                                    border=f"2px solid {rx.color('gray', 12)}",
                                    background_color=rx.color("gray", 1),
                                )
                            ),
                            at="start",
                        ),
                        mapcn.route_marker(
                            mapcn.marker_content(
                                rx.center(
                                    rx.icon("car", size=12, color="white"),
                                    width="24px",
                                    height="24px",
                                    border_radius="9999px",
                                    background_color=ROUTE_COLOR,
                                    box_shadow=f"0 0 0 2px {rx.color('gray', 1)}",
                                ),
                                mapcn.marker_label(
                                    RoutesState.progress_label,
                                    position="top",
                                    padding="2px 6px",
                                    border_radius="6px",
                                    background_color=rx.color("gray", 1),
                                    border=f"1px solid {rx.color('gray', 5)}",
                                ),
                            ),
                            at="progress",
                        ),
                        mapcn.route_marker(
                            mapcn.marker_content(
                                rx.box(
                                    width="14px",
                                    height="14px",
                                    border_radius="9999px",
                                    background_color=rx.color("gray", 12),
                                    box_shadow=f"0 0 0 2px {rx.color('gray', 1)}",
                                )
                            ),
                            at="end",
                        ),
                        coordinates=SF_ROUTE,
                        progress=RoutesState.progress,
                        color="#94a3b8",
                        width=5,
                        opacity=0.8,
                        dash_array=[0.5, 1.5],
                    ),
                    center=[-122.4008, 37.7996],
                    zoom=14.2,
                ),
                rx.vstack(
                    rx.hstack(
                        rx.text("Progress", size="1", weight="medium"),
                        rx.spacer(),
                        rx.text(
                            RoutesState.progress_label,
                            size="1",
                            color=rx.color("gray", 10),
                        ),
                        width="100%",
                    ),
                    rx.slider(
                        default_value=[45],
                        min=0,
                        max=100,
                        step=1,
                        size="1",
                        on_change=RoutesState.set_progress.throttle(50),
                    ),
                    spacing="2",
                    width="220px",
                    position="absolute",
                    bottom="12px",
                    left="12px",
                    padding="12px",
                    border_radius="10px",
                    background_color=rx.color("gray", 1),
                    border=f"1px solid {rx.color('gray', 5)}",
                    z_index="10",
                ),
                height="420px",
            ),
            code(
                """
mapcn.map_route(
    mapcn.route_progress(color="#3b82f6", width=5, opacity=1),
    mapcn.route_marker(mapcn.marker_content(...), at="start"),
    mapcn.route_marker(mapcn.marker_content(rx.icon("car")), at="progress"),
    mapcn.route_marker(mapcn.marker_content(...), at="end"),
    coordinates=SF_ROUTE,
    progress=RoutesState.progress,      # 0-1
    color="#94a3b8",
    width=5,
    dash_array=[0.5, 1.5],
)
"""
            ),
        ),
        section(
            "Route selection (OSRM)",
            "Alternatives fetched on the backend with httpx from the public "
            "OSRM demo server. Click a route on the map or in the list; the "
            "`active` route is raised above its siblings.",
            demo_frame(
                mapcn.map(
                    rx.foreach(RoutesState.routes, osrm_route),
                    endpoint_marker(START, filled=False),
                    endpoint_marker(END, filled=True),
                    center=[4.69, 52.14],
                    zoom=8.5,
                    loading=RoutesState.loading,
                ),
                rx.cond(
                    RoutesState.routes.length() > 0,
                    rx.vstack(
                        rx.foreach(RoutesState.routes, route_option),
                        spacing="1",
                        width="200px",
                        position="absolute",
                        top="12px",
                        left="12px",
                        padding="4px",
                        border_radius="10px",
                        background_color=rx.color("gray", 1),
                        border=f"1px solid {rx.color('gray', 5)}",
                        z_index="10",
                    ),
                ),
                rx.cond(
                    RoutesState.error != "",
                    rx.callout(
                        RoutesState.error,
                        icon="triangle-alert",
                        color_scheme="red",
                        size="1",
                        position="absolute",
                        top="12px",
                        left="12px",
                        z_index="10",
                    ),
                ),
                height="480px",
            ),
            code(
                """
def osrm_route(route: RouteOption):
    return mapcn.map_route(
        coordinates=route.coordinates,
        active=route.index == RoutesState.selected_index,
        color="#3b82f6", width=5, opacity=0.35,
        active_width=6, active_opacity=1.0,
        on_click=RoutesState.select_route(route.index),
    )

mapcn.map(
    rx.foreach(RoutesState.routes, osrm_route),
    loading=RoutesState.loading,
)
"""
            ),
        ),
    )
