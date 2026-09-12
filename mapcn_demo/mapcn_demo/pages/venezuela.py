"""Full-country demo: Venezuela with states, capitals, cities and street detail."""

from __future__ import annotations

import dataclasses

import reflex as rx
import reflex_mapcn as mapcn

from ..layout import code, demo_frame, page, section
from ..services import osrm
from ..venezuela_data import (
    CAPITALS,
    CITIES,
    CONTINENTAL_CAPITALS,
    REGION_COLORS,
    STATE_BOUNDS,
    STATE_INFO,
    STATE_NAMES,
    VENEZUELA_BOUNDS,
    VENEZUELA_CENTER,
    VENEZUELA_MAX_BOUNDS,
    VENEZUELA_STATES_URL,
    VENEZUELA_STYLES,
    Capital,
    City,
)

DEFAULT_STYLE = "OpenFreeMap Liberty (calles, POIs)"

# Travel times: read from the public OSRM demo server, so the licence of the
# underlying road network has to travel with them.
TRAVEL_ATTRIBUTION = (
    "Tiempos y rutas: OSRM (router.project-osrm.org) · red vial de OpenStreetMap (ODbL)"
)
MAX_DESTINATIONS = osrm.MAX_DESTINATIONS
ROUTE_COLOR = "#2563eb"
NO_ROUTE_LABEL = "sin ruta"

REGION_COLOR_EXPRESSION = [
    "match",
    ["get", "region"],
    *[item for region, color in REGION_COLORS.items() for item in (region, color)],
    "#9ca3af",
]

KIND_COLORS = {"nacional": "#ef4444", "estadal": "#2563eb", "ciudad": "#64748b"}
KIND_LABELS = {
    "nacional": "Capital nacional",
    "estadal": "Capital de estado",
    "ciudad": "Ciudad",
}


@dataclasses.dataclass
class TravelRow:
    """One line of the travel-time table."""

    state: str
    capital: str
    lng: float
    lat: float
    duration_s: float | None
    distance_m: float | None
    duration_label: str
    distance_label: str


def capital_of(state: str) -> Capital | None:
    """The capital to drive from or to, when the state has one."""
    return CAPITALS.get(state)


def destinations_for(state: str) -> list[Capital]:
    """Every mainland capital other than the one being driven from."""
    if capital_of(state) is None:
        return []
    return [capital for capital in CONTINENTAL_CAPITALS if capital.state != state]


def format_duration(seconds: float | None) -> str:
    """A drive as ``5h 30m``, or as the reason there is no drive."""
    if seconds is None:
        return NO_ROUTE_LABEL
    minutes = int(round(seconds / 60))
    if minutes < 60:
        return f"{minutes} min"
    return f"{minutes // 60}h {minutes % 60}m"


def format_distance(metres: float | None) -> str:
    if metres is None:
        return "—"
    return f"{metres / 1000:.0f} km"


def build_travel_rows(
    destinations: list[Capital],
    durations: list[float | None],
    distances: list[float | None],
) -> list[TravelRow]:
    """Pair each destination with its cell, nearest first, holes last."""
    rows = [
        TravelRow(
            state=capital.state,
            capital=capital.name,
            lng=capital.lng,
            lat=capital.lat,
            duration_s=durations[index] if index < len(durations) else None,
            distance_m=distances[index] if index < len(distances) else None,
            duration_label=format_duration(
                durations[index] if index < len(durations) else None
            ),
            distance_label=format_distance(
                distances[index] if index < len(distances) else None
            ),
        )
        for index, capital in enumerate(destinations)
    ]
    rows.sort(key=lambda row: (row.duration_s is None, row.duration_s or 0.0))
    return rows


def bounds_of(coordinates: list[list[float]]) -> list[list[float]] | None:
    """The box the camera has to fit to show a whole route."""
    if not coordinates:
        return None
    longitudes = [point[0] for point in coordinates]
    latitudes = [point[1] for point in coordinates]
    return [
        [min(longitudes), min(latitudes)],
        [max(longitudes), max(latitudes)],
    ]


class VenezuelaState(rx.State):
    """State for the Venezuela country demo."""

    style_name: str = DEFAULT_STYLE
    show_states: bool = True
    show_cities: bool = True

    hovered_state: str = ""
    selected_state: str = ""
    zoom: float = 5.6

    command: dict = {}
    _seq: int = 0

    # ---- travel times ------------------------------------------------------

    travel_origin: str = ""
    travel_rows: list[TravelRow] = []
    travel_error: str = ""
    travel_loading: bool = False

    selected_travel: str = ""
    route_coordinates: list[list[float]] = []
    route_error: str = ""
    route_loading: bool = False

    # ---- camera -----------------------------------------------------------

    def _push(self, command: dict):
        self._seq += 1
        self.command = {**command, "seq": self._seq}

    @rx.event
    def fit_country(self):
        self.selected_state = ""
        self._push(
            mapcn.camera_command(
                "fitBounds", bounds=VENEZUELA_BOUNDS, padding=30, duration=1500
            )
        )

    @rx.event
    def go_to_state(self, name: str):
        if name not in STATE_BOUNDS:
            return
        self.selected_state = name
        w, s, e, n = STATE_BOUNDS[name]
        self._push(
            mapcn.camera_command(
                "fitBounds",
                bounds=[[w, s], [e, n]],
                padding=60,
                duration=1500,
                maxZoom=11,
            )
        )

    @rx.event
    def go_to_city(self, lng: float, lat: float, state: str):
        self.selected_state = state
        self._push(
            mapcn.camera_command("flyTo", center=[lng, lat], zoom=12.5, duration=2000)
        )

    # ---- map events ---------------------------------------------------------

    @rx.event
    def on_state_hover(self, event: dict | None):
        self.hovered_state = (
            "" if event is None else str(event["feature"]["properties"].get("name", ""))
        )

    @rx.event
    def on_state_click(self, event: dict):
        name = str(event["feature"]["properties"].get("name", ""))
        return VenezuelaState.go_to_state(name)

    @rx.event
    def on_move_end(self, viewport: dict):
        self.zoom = float(viewport.get("zoom", 0))

    # ---- settings -----------------------------------------------------------

    @rx.event
    def set_style_name(self, value: str):
        self.style_name = value

    @rx.event
    def set_show_states(self, value: bool):
        self.show_states = value

    @rx.event
    def set_show_cities(self, value: bool):
        self.show_cities = value

    # ---- travel times -------------------------------------------------------

    @rx.event(background=True)
    async def load_travel_times(self):
        """Ask OSRM how long it takes to drive to every other capital."""
        async with self:
            origin_state = self.selected_state
            origin = capital_of(origin_state)
            if origin is None:
                self.travel_error = "Ese estado no tiene capital por carretera."
                return
            self.travel_loading = True
            self.travel_error = ""
            self.travel_origin = origin_state
            self.travel_rows = []
            self.selected_travel = ""
            self.route_coordinates = []
            self.route_error = ""

        destinations = destinations_for(origin_state)
        matrix = await osrm.table(
            (origin.lng, origin.lat),
            [(capital.lng, capital.lat) for capital in destinations],
        )

        async with self:
            self.travel_rows = build_travel_rows(
                destinations, matrix["durations"], matrix["distances"]
            )
            self.travel_error = matrix["error"] or ""
            self.travel_loading = False

    @rx.event(background=True)
    async def select_travel_row(self, state_name: str):
        """Draw the road route to one capital and frame it."""
        async with self:
            origin = capital_of(self.travel_origin)
            destination = capital_of(state_name)
            if origin is None or destination is None:
                return
            self.selected_travel = state_name
            self.route_loading = True
            self.route_error = ""
            self.route_coordinates = []

        result = await osrm.route(
            [(origin.lng, origin.lat), (destination.lng, destination.lat)]
        )

        async with self:
            self.route_coordinates = result["coordinates"]
            self.route_error = result["error"] or ""
            self.route_loading = False
            box = bounds_of(result["coordinates"])
            if box is not None:
                self._push(
                    mapcn.camera_command(
                        "fitBounds", bounds=box, padding=60, duration=1500
                    )
                )

    @rx.event
    def clear_travel(self):
        self.travel_rows = []
        self.travel_origin = ""
        self.travel_error = ""
        self.selected_travel = ""
        self.route_coordinates = []
        self.route_error = ""

    # ---- computed -----------------------------------------------------------

    @rx.var
    def styles(self) -> dict[str, str]:
        url = VENEZUELA_STYLES.get(self.style_name, "")
        return {"light": url, "dark": url} if url else {}

    @rx.var
    def fill_paint(self) -> dict:
        # The selected state is painted stronger; everything else stays
        # translucent so streets and labels remain readable underneath.
        return {
            "fill-color": REGION_COLOR_EXPRESSION,
            "fill-opacity": [
                "case",
                ["==", ["get", "name"], self.selected_state or "__none__"],
                0.45,
                0.16,
            ],
        }

    @rx.var
    def has_selection(self) -> bool:
        return self.selected_state in STATE_INFO

    @rx.var
    def selected_capital(self) -> str:
        return STATE_INFO.get(self.selected_state, {}).get("capital", "")

    @rx.var
    def selected_region(self) -> str:
        return STATE_INFO.get(self.selected_state, {}).get("region", "")

    @rx.var
    def selected_color(self) -> str:
        return REGION_COLORS.get(self.selected_region, "#9ca3af")

    @rx.var
    def can_route(self) -> bool:
        return self.selected_state in CAPITALS

    @rx.var
    def has_travel_rows(self) -> bool:
        return len(self.travel_rows) > 0

    @rx.var
    def has_route(self) -> bool:
        return len(self.route_coordinates) > 1

    @rx.var
    def travel_origin_capital(self) -> str:
        capital = CAPITALS.get(self.travel_origin)
        return capital.name if capital is not None else ""

    @rx.var
    def zoom_label(self) -> str:
        return f"zoom {self.zoom:.1f}"

    @rx.var
    def zoom_hint(self) -> str:
        if self.zoom < 7:
            return "Acércate para ver carreteras y ciudades"
        if self.zoom < 11:
            return "Carreteras y poblaciones visibles"
        return "Nivel de calles: nombres de vías y puntos de interés"


def city_marker(city: City) -> rx.Component:
    color = KIND_COLORS[city.kind]
    size = {"nacional": "16px", "estadal": "12px", "ciudad": "9px"}[city.kind]
    return mapcn.map_marker(
        mapcn.marker_content(
            rx.box(
                width=size,
                height=size,
                border_radius="9999px",
                border="2px solid white",
                background_color=color,
                box_shadow="0 2px 4px rgba(0,0,0,.35)",
                transition="transform 150ms",
                _hover={"transform": "scale(1.25)"},
            ),
            mapcn.marker_label(
                city.name,
                position="top",
                font_weight="700" if city.kind == "nacional" else "500",
                text_shadow="0 0 3px var(--mapcn-bg), 0 0 3px var(--mapcn-bg)",
            ),
        ),
        mapcn.marker_tooltip(f"{city.name} · {KIND_LABELS[city.kind]}"),
        mapcn.marker_popup(
            rx.vstack(
                rx.text(
                    KIND_LABELS[city.kind],
                    size="1",
                    color=rx.color("gray", 10),
                    style={"textTransform": "uppercase", "letterSpacing": "0.04em"},
                ),
                rx.text(city.name, weight="bold", size="3"),
                rx.text(f"Estado {city.state}", size="1", color=rx.color("gray", 11)),
                rx.text(
                    f"{city.lat:.4f}, {city.lng:.4f}",
                    size="1",
                    color=rx.color("gray", 10),
                    font_family="monospace",
                ),
                rx.button(
                    rx.icon("zoom-in", size=12),
                    "Ver calles",
                    size="1",
                    variant="soft",
                    width="100%",
                    on_click=VenezuelaState.go_to_city(city.lng, city.lat, city.state),
                ),
                spacing="1",
                align="start",
            ),
            close_button=True,
        ),
        longitude=city.lng,
        latitude=city.lat,
        anchor="center",
    )


def legend() -> rx.Component:
    return rx.vstack(
        rx.text("Regiones", size="1", weight="medium"),
        rx.grid(
            *[
                rx.hstack(
                    rx.box(
                        width="8px",
                        height="8px",
                        border_radius="2px",
                        background_color=color,
                    ),
                    rx.text(region, size="1"),
                    spacing="1",
                    align="center",
                )
                for region, color in REGION_COLORS.items()
            ],
            columns="3",
            spacing="1",
        ),
        rx.divider(),
        rx.hstack(
            *[
                rx.hstack(
                    rx.box(
                        width="8px",
                        height="8px",
                        border_radius="9999px",
                        background_color=color,
                        border="1.5px solid white",
                    ),
                    rx.text(KIND_LABELS[kind], size="1"),
                    spacing="1",
                    align="center",
                )
                for kind, color in KIND_COLORS.items()
            ],
            spacing="3",
        ),
        spacing="2",
        align="start",
        position="absolute",
        bottom="12px",
        left="12px",
        padding="10px 12px",
        border_radius="10px",
        background_color=rx.color("gray", 1),
        border=f"1px solid {rx.color('gray', 5)}",
        z_index="10",
    )


def travel_row(row: TravelRow) -> rx.Component:
    """One capital, how long the drive takes and how far it is."""
    selected = VenezuelaState.selected_travel == row.state
    return rx.hstack(
        rx.text(row.capital, size="1", weight="medium"),
        rx.spacer(),
        rx.text(
            row.duration_label,
            size="1",
            color=rx.cond(
                row.duration_label == NO_ROUTE_LABEL,
                rx.color("gray", 9),
                rx.color("gray", 12),
            ),
            weight="medium",
        ),
        rx.text(
            row.distance_label,
            size="1",
            color=rx.color("gray", 10),
            width="58px",
            text_align="right",
        ),
        width="100%",
        align="center",
        spacing="2",
        padding="4px 8px",
        border_radius="6px",
        cursor="pointer",
        background_color=rx.cond(selected, rx.color("blue", 3), "transparent"),
        _hover={"background_color": rx.color("gray", 3)},
        on_click=VenezuelaState.select_travel_row(row.state),
    )


def travel_panel() -> rx.Component:
    """The travel-time table, shown once a matrix has been read."""
    return rx.cond(
        VenezuelaState.has_travel_rows | VenezuelaState.travel_loading,
        rx.vstack(
            rx.hstack(
                rx.icon("car", size=14, color=ROUTE_COLOR),
                rx.text(
                    "Desde ",
                    rx.text.strong(VenezuelaState.travel_origin_capital),
                    size="1",
                ),
                rx.spacer(),
                rx.icon_button(
                    rx.icon("x", size=12),
                    size="1",
                    variant="ghost",
                    color_scheme="gray",
                    on_click=VenezuelaState.clear_travel,
                ),
                width="100%",
                align="center",
            ),
            rx.cond(
                VenezuelaState.travel_error != "",
                rx.callout(
                    "No se pudo leer la matriz de tiempos. Inténtalo de nuevo.",
                    icon="triangle_alert",
                    size="1",
                    color_scheme="amber",
                    width="100%",
                ),
            ),
            rx.cond(
                VenezuelaState.travel_loading,
                rx.hstack(
                    rx.spinner(size="1"),
                    rx.text("Consultando OSRM…", size="1"),
                    spacing="2",
                    align="center",
                ),
                rx.vstack(
                    rx.foreach(VenezuelaState.travel_rows, travel_row),
                    spacing="0",
                    width="100%",
                    max_height="300px",
                    overflow_y="auto",
                ),
            ),
            rx.text(
                "Pulsa una fila para dibujar la ruta.",
                size="1",
                color=rx.color("gray", 10),
            ),
            spacing="2",
            align="start",
            width="270px",
            position="absolute",
            right="12px",
            bottom="12px",
            padding="12px",
            border_radius="10px",
            background_color=rx.color("gray", 1),
            border=f"1px solid {rx.color('gray', 5)}",
            z_index="10",
        ),
    )


def control_panel() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.icon("flag", size=14, color="#ef4444"),
            rx.text("Venezuela", size="2", weight="bold"),
            rx.spacer(),
            rx.badge(VenezuelaState.zoom_label, variant="soft", color_scheme="gray"),
            width="100%",
            align="center",
        ),
        rx.text(VenezuelaState.zoom_hint, size="1", color=rx.color("gray", 10)),
        rx.select(
            list(VENEZUELA_STYLES.keys()),
            value=VenezuelaState.style_name,
            on_change=VenezuelaState.set_style_name,
            size="1",
            width="100%",
        ),
        rx.select(
            STATE_NAMES,
            placeholder="Ir a un estado…",
            value=VenezuelaState.selected_state,
            on_change=VenezuelaState.go_to_state,
            size="1",
            width="100%",
        ),
        rx.hstack(
            rx.hstack(
                rx.switch(
                    checked=VenezuelaState.show_states,
                    on_change=VenezuelaState.set_show_states,
                    size="1",
                ),
                rx.text("Estados", size="1"),
                spacing="1",
                align="center",
            ),
            rx.hstack(
                rx.switch(
                    checked=VenezuelaState.show_cities,
                    on_change=VenezuelaState.set_show_cities,
                    size="1",
                ),
                rx.text("Ciudades", size="1"),
                spacing="1",
                align="center",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("maximize", size=12),
                "Todo el país",
                size="1",
                variant="outline",
                on_click=VenezuelaState.fit_country,
            ),
            spacing="3",
            align="center",
            width="100%",
        ),
        rx.cond(
            VenezuelaState.has_selection,
            rx.vstack(
                rx.hstack(
                    rx.box(
                        width="10px",
                        height="10px",
                        border_radius="2px",
                        background_color=VenezuelaState.selected_color,
                    ),
                    rx.text(VenezuelaState.selected_state, size="2", weight="bold"),
                    spacing="2",
                    align="center",
                ),
                rx.text(
                    "Capital: ",
                    rx.text.strong(VenezuelaState.selected_capital),
                    size="1",
                ),
                rx.text(
                    "Región: ", rx.text.strong(VenezuelaState.selected_region), size="1"
                ),
                rx.button(
                    rx.icon("car", size=12),
                    "Tiempos de viaje",
                    size="1",
                    variant="soft",
                    width="100%",
                    disabled=~VenezuelaState.can_route,
                    loading=VenezuelaState.travel_loading,
                    on_click=VenezuelaState.load_travel_times,
                ),
                spacing="1",
                align="start",
                width="100%",
                padding="8px 10px",
                border_radius="8px",
                background_color=rx.color("gray", 3),
            ),
            rx.text(
                rx.cond(
                    VenezuelaState.hovered_state != "",
                    VenezuelaState.hovered_state,
                    "Pasa el cursor o haz clic sobre un estado",
                ),
                size="1",
                color=rx.color("gray", 11),
            ),
        ),
        spacing="2",
        align="start",
        width="290px",
        position="absolute",
        top="12px",
        left="12px",
        padding="12px",
        border_radius="10px",
        background_color=rx.color("gray", 1),
        border=f"1px solid {rx.color('gray', 5)}",
        z_index="10",
    )


@rx.page(route="/venezuela", title="Venezuela · reflex-mapcn")
def venezuela_page() -> rx.Component:
    return page(
        "Venezuela",
        "Mapa completo del país con detalle de calles, carreteras, ciudades y "
        "estados: basemap OpenFreeMap (datos OpenStreetMap), capa GeoJSON con "
        "los 23 estados, el Distrito Capital y las Dependencias Federales, y "
        "marcadores para capitales y ciudades principales.",
        section(
            "Mapa interactivo",
            "Haz clic en un estado para enfocarlo, elige uno en el selector o "
            "abre el popup de una ciudad y pulsa «Ver calles». Cambia el estilo "
            "del basemap para comparar niveles de detalle; el zoom está "
            "limitado al entorno del país.",
            demo_frame(
                mapcn.map(
                    mapcn.map_camera(command=VenezuelaState.command),
                    rx.cond(
                        VenezuelaState.show_states,
                        mapcn.map_geojson(
                            id="venezuela-estados",
                            data=VENEZUELA_STATES_URL,
                            promote_id="iso",
                            fill_paint=VenezuelaState.fill_paint,
                            fill_hover_paint={"fill-opacity": 0.38},
                            line_paint={
                                "line-color": "#334155",
                                "line-width": 1.2,
                                "line-opacity": 0.8,
                            },
                            interactive=True,
                            on_hover=VenezuelaState.on_state_hover,
                            on_click=VenezuelaState.on_state_click,
                        ),
                    ),
                    rx.cond(
                        VenezuelaState.show_cities,
                        rx.fragment(*[city_marker(city) for city in CITIES]),
                    ),
                    rx.cond(
                        VenezuelaState.has_route,
                        mapcn.map_route(
                            coordinates=VenezuelaState.route_coordinates,
                            color=ROUTE_COLOR,
                            width=5,
                            opacity=0.95,
                        ),
                    ),
                    mapcn.map_controls(
                        position="top-right",
                        show_zoom=True,
                        show_compass=True,
                        show_locate=True,
                        show_fullscreen=True,
                    ),
                    center=VENEZUELA_CENTER,
                    zoom=5.6,
                    min_zoom=4.5,
                    max_bounds=VENEZUELA_MAX_BOUNDS,
                    styles=VenezuelaState.styles,
                    on_move_end=VenezuelaState.on_move_end,
                ),
                control_panel(),
                travel_panel(),
                legend(),
                height="680px",
            ),
            code(
                """
mapcn.map(
    mapcn.map_camera(command=VenezuelaState.command),
    mapcn.map_geojson(
        data="/venezuela_estados.geojson",        # file in the app's assets/ folder
        promote_id="iso",
        fill_paint={
            "fill-color": [
                "match", ["get", "region"],
                "Capital", "#ef4444", ...,
                "#9ca3af",
            ],
            "fill-opacity": 0.16,
        },
        fill_hover_paint={"fill-opacity": 0.38},
        line_paint={"line-color": "#334155", "line-width": 1.2},
        interactive=True,
        on_hover=VenezuelaState.on_state_hover,
        on_click=VenezuelaState.on_state_click,   # -> fitBounds of the state
    ),
    *[city_marker(city) for city in CITIES],      # capitals + main cities
    mapcn.map_controls(position="top-right", show_compass=True, show_fullscreen=True),
    center=[-66.2, 7.9],
    zoom=5.6,
    min_zoom=4.5,
    max_bounds=[[-80.0, -3.0], [-53.0, 18.0]],
    styles={"light": "https://tiles.openfreemap.org/styles/liberty",
            "dark": "https://tiles.openfreemap.org/styles/liberty"},
)
"""
            ),
        ),
        section(
            "Sobre los datos",
            "El basemap OpenFreeMap sirve teselas vectoriales de OpenStreetMap "
            "sin API key: incluye red vial completa, nombres de calles, "
            "poblaciones y puntos de interés hasta el nivel de calle. Los "
            "polígonos de estados provienen del plugin country-map de Apache "
            "Superset (Apache-2.0) y se sirven como un archivo estático de "
            "~100 KB desde la carpeta assets/ del demo; las coordenadas de "
            "ciudades son aproximadas (centros urbanos). Los tiempos de viaje "
            "y las rutas los calcula el servidor público de demostración de "
            f"OSRM sobre la red vial de OpenStreetMap. {TRAVEL_ATTRIBUTION}.",
        ),
    )
