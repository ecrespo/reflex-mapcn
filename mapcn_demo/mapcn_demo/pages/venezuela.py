"""Full-country demo: Venezuela with states, capitals, cities and street detail."""

from __future__ import annotations

import reflex as rx
import reflex_mapcn as mapcn

from ..layout import code, demo_frame, page, section
from ..venezuela_data import (
    CITIES,
    REGION_COLORS,
    STATE_BOUNDS,
    STATE_INFO,
    STATE_NAMES,
    VENEZUELA_BOUNDS,
    VENEZUELA_CENTER,
    VENEZUELA_MAX_BOUNDS,
    VENEZUELA_STATES_URL,
    VENEZUELA_STYLES,
    City,
)

DEFAULT_STYLE = "OpenFreeMap Liberty (calles, POIs)"

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
            "ciudades son aproximadas (centros urbanos).",
        ),
    )
