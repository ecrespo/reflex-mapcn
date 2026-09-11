"""Seismic history of Venezuela, from the USGS catalogue.

The whole catalogue travels to the browser once and every filter runs there as
a MapLibre expression, so moving the time slider redraws thousands of points
without a round trip to the backend.
"""

from __future__ import annotations

import asyncio
import calendar
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import reflex as rx
import reflex_mapcn as mapcn
from reflex_mapcn import match

from ..layout import page, section
from ..services import usgs
from ..venezuela_data import (
    DEPTH_COLOR,
    FAULTS_ATTRIBUTION,
    MAG_RADIUS,
    NOTABLE_QUAKES,
    SLIP_TYPE_COLORS,
    SLIP_TYPE_DEFAULT_COLOR,
    VENEZUELA_CENTER,
    VENEZUELA_FAULTS_URL,
)

CARACAS = ZoneInfo("America/Caracas")
FIRST_YEAR = 1900
BASE_STYLE = "https://tiles.openfreemap.org/styles/positron"

ATTRIBUTION = f"USGS Earthquake Hazards Program · {FAULTS_ATTRIBUTION}"

# The catalogue only covers small events reliably from about 1973 onwards.
COVERAGE_NOTE = (
    "Catálogo USGS: completo aproximadamente desde 1973 para M ≥ 4,5. "
    "La ausencia de sismos antiguos no significa ausencia de actividad."
)

DEPTH_LEGEND = [
    ("Superficial (< 70 km)", "#ef4444"),
    ("Intermedio (70–300 km)", "#f97316"),
    ("Profundo (> 300 km)", "#3b82f6"),
]

DEPTH_BAND_LABELS = {
    "all": "Todas",
    "shallow": "Superficial",
    "intermediate": "Intermedio",
    "deep": "Profundo",
}

EMPTY_COLLECTION: dict = {"type": "FeatureCollection", "features": []}

# Live feed: the backend flags anything under 24 hours old, and the ring layer
# draws only those. MapLibre cannot animate a pulse, and driving one from state
# would flood the websocket, so the ring is static and simply wider.
LIVE_POLL_S = 60
RECENT_FILTER = ["==", ["get", "recent"], True]
LIVE_COLOR = "#facc15"

# Density: a magnitude 8 counts far more than a 4, and the heatmap hands over
# to the point layer as the map is zoomed in.
HEATMAP_WEIGHT_PROPERTY = "mag"
HEATMAP_WEIGHT_RANGE = [4.0, 8.0]
HEATMAP_MAX_ZOOM_FADE = 8

# Faults: colour by the kind of movement, slate for anything unclassified.
FAULT_COLOR = match("slip_type", SLIP_TYPE_COLORS, SLIP_TYPE_DEFAULT_COLOR)

TERRAIN_PRESET = "aws_terrarium"
TERRAIN_EXAGGERATION = 1.3


def depth_band_from_label(label: str) -> str:
    """Turn what the select shows back into the band the filter needs."""
    for band, text in DEPTH_BAND_LABELS.items():
        if text == label:
            return band
    return "all"


def current_year() -> int:
    return datetime.now(tz=timezone.utc).year


def time_cutoff_ms(year: int, month: int) -> int:
    """Last instant of the selected month, in milliseconds since the epoch.

    The slider selects a whole month, and the filter compares against the
    event time, so the cutoff has to be the end of it rather than the start.
    """
    month = min(max(int(month), 1), 12)
    last_day = calendar.monthrange(int(year), month)[1]
    end = datetime(
        int(year), month, last_day, 23, 59, 59, 999_000, tzinfo=timezone.utc
    )
    return int(end.timestamp() * 1000)


def build_layer_filter(cutoff_ms: int, min_magnitude: float, depth_band: str) -> list:
    """Combine the three filters into one MapLibre expression.

    Everything the user changes ends up here, and the browser applies it with
    `setFilter`: no new request, no new data.
    """
    clauses: list = [
        "all",
        ["<=", ["get", "time"], cutoff_ms],
        [">=", ["get", "mag"], min_magnitude],
    ]
    if depth_band == "shallow":
        clauses.append(["<", ["get", "depth"], 70])
    elif depth_band == "intermediate":
        clauses.append([">=", ["get", "depth"], 70])
        clauses.append(["<", ["get", "depth"], 300])
    elif depth_band == "deep":
        clauses.append([">=", ["get", "depth"], 300])
    return clauses


def format_event_times(time_ms: int) -> dict[str, str]:
    """The same instant in UTC and in Venezuelan time."""
    if not time_ms:
        return {"utc": "—", "caracas": "—"}
    moment = datetime.fromtimestamp(int(time_ms) / 1000, tz=timezone.utc)
    return {
        "utc": moment.strftime("%Y-%m-%d %H:%M UTC"),
        "caracas": moment.astimezone(CARACAS).strftime("%Y-%m-%d %H:%M Caracas"),
    }


class SismosState(rx.State):
    """Catalogue, filters and selection for /sismos."""

    catalog: dict = EMPTY_COLLECTION
    count: int = 0
    fetched_at: str = ""
    error: str = ""
    loading: bool = False

    live: dict = EMPTY_COLLECTION
    live_count: int = 0
    live_fetched_at: str = ""

    year: int = current_year()
    month: int = 12
    min_mag: float = 4.0
    depth_band: str = "all"
    playing: bool = False
    show_notable: bool = True
    show_live: bool = False
    show_heat: bool = False
    show_faults: bool = True
    show_terrain: bool = False
    hovered_fault: str = ""

    selected: dict = {}

    # ---- derived ----------------------------------------------------------

    @rx.var
    def time_cutoff(self) -> int:
        return time_cutoff_ms(self.year, self.month)

    @rx.var
    def layer_filter(self) -> list:
        return build_layer_filter(self.time_cutoff, self.min_mag, self.depth_band)

    @rx.var
    def count_visible(self) -> int:
        cutoff = self.time_cutoff
        return sum(
            1
            for feature in self.catalog.get("features", [])
            if self._passes(feature.get("properties", {}), cutoff)
        )

    @rx.var
    def has_selection(self) -> bool:
        return bool(self.selected)

    @rx.var
    def selected_utc(self) -> str:
        return format_event_times(self.selected.get("time", 0))["utc"]

    @rx.var
    def selected_caracas(self) -> str:
        return format_event_times(self.selected.get("time", 0))["caracas"]

    @rx.var
    def selected_title(self) -> str:
        magnitude = self.selected.get("mag")
        kind = self.selected.get("magType") or ""
        return f"M {magnitude} {kind}".strip() if magnitude else "Sismo"

    @rx.var
    def selected_depth(self) -> str:
        depth = self.selected.get("depth")
        return "—" if depth is None else f"{depth} km"

    @rx.var
    def selected_center(self) -> list[float]:
        return [
            self.selected.get("longitude", VENEZUELA_CENTER[0]),
            self.selected.get("latitude", VENEZUELA_CENTER[1]),
        ]

    @rx.var
    def depth_band_label(self) -> str:
        return DEPTH_BAND_LABELS.get(self.depth_band, DEPTH_BAND_LABELS["all"])

    @rx.var
    def period_label(self) -> str:
        return f"{self.month:02d}/{self.year}"

    def _passes(self, properties: dict, cutoff: int) -> bool:
        if properties.get("time", 0) > cutoff:
            return False
        if (properties.get("mag") or 0) < self.min_mag:
            return False
        depth = properties.get("depth") or 0
        if self.depth_band == "shallow":
            return depth < 70
        if self.depth_band == "intermediate":
            return 70 <= depth < 300
        if self.depth_band == "deep":
            return depth >= 300
        return True

    # ---- events -----------------------------------------------------------

    @rx.event(background=True)
    async def load_catalog(self):
        """Read the historical catalogue once per page load."""
        async with self:
            if self.count:
                return
            self.loading = True

        result = await usgs.fetch_catalog()

        async with self:
            self.catalog = result["features"]
            self.count = result["count"]
            self.fetched_at = result["fetched_at"]
            self.error = result["error"] or ""
            self.loading = False

    @rx.event
    def select_quake(self, event: dict):
        feature = event.get("feature") or {}
        self.selected = {
            **(feature.get("properties") or {}),
            "longitude": event.get("longitude"),
            "latitude": event.get("latitude"),
        }

    @rx.event
    def close_popup(self):
        self.selected = {}

    @rx.event
    def set_year(self, value: list[float]):
        self.year = int(value[0])

    @rx.event
    def set_month(self, value: list[float]):
        self.month = int(value[0])

    @rx.event
    def set_min_mag(self, value: list[float]):
        self.min_mag = float(value[0])

    @rx.event
    def set_depth_band(self, label: str):
        self.depth_band = depth_band_from_label(label)

    @rx.event
    def toggle_notable(self, value: bool):
        self.show_notable = bool(value)

    @rx.event
    def toggle_heat(self, value: bool):
        self.show_heat = bool(value)

    @rx.event
    def toggle_faults(self, value: bool):
        self.show_faults = bool(value)

    @rx.event
    def toggle_terrain(self, value: bool):
        self.show_terrain = bool(value)

    @rx.event
    def show_fault(self, event: dict | None):
        if not event:
            self.hovered_fault = ""
            return
        properties = (event.get("feature") or {}).get("properties") or {}
        name = properties.get("name") or "Falla sin nombre"
        slip = properties.get("slip_type") or "desplazamiento desconocido"
        self.hovered_fault = f"{name} · {slip}"

    @rx.event
    def toggle_live(self, value: bool):
        """Start or stop the live poll."""
        self.show_live = bool(value)
        if self.show_live:
            return SismosState.poll_live

    @rx.event(background=True)
    async def poll_live(self):
        """Refresh the last thirty days while the live switch is on."""
        while True:
            async with self:
                if not self.show_live:
                    return

            result = await usgs.fetch_live()

            async with self:
                if not self.show_live:
                    return
                self.live = result["features"]
                self.live_count = result["count"]
                self.live_fetched_at = result["fetched_at"]
                if result["error"]:
                    self.error = result["error"]

            await asyncio.sleep(LIVE_POLL_S)

    @rx.event
    def stop(self):
        self.playing = False

    @rx.event(background=True)
    async def play(self):
        """Walk the timeline one year every 200 ms until it reaches today."""
        async with self:
            if self.playing:
                self.playing = False
                return
            if self.year >= current_year():
                self.year = FIRST_YEAR
            self.playing = True

        while True:
            await asyncio.sleep(0.2)
            async with self:
                if not self.playing:
                    return
                if self.year >= current_year():
                    self.playing = False
                    return
                self.year += 1


def _legend() -> rx.Component:
    return rx.vstack(
        rx.text("Profundidad", size="1", weight="bold"),
        *[
            rx.hstack(
                rx.box(
                width="10px", height="10px", border_radius="50%", background=color
            ),
                rx.text(label, size="1"),
                spacing="2",
                align="center",
            )
            for label, color in DEPTH_LEGEND
        ],
        rx.text("El radio crece con la magnitud", size="1", color=rx.color("gray", 11)),
        spacing="1",
        align="start",
        padding="10px 12px",
        border_radius="8px",
        background=rx.color("gray", 2),
        border=f"1px solid {rx.color('gray', 5)}",
    )


def _controls() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.heading("Sismos de Venezuela", size="4"),
            rx.spacer(),
            rx.badge(SismosState.count_visible, " visibles", color_scheme="blue"),
            width="100%",
            align="center",
        ),
        rx.cond(
            SismosState.error != "",
            rx.callout(
                SismosState.error,
                icon="triangle-alert",
                color_scheme="red",
                size="1",
                width="100%",
            ),
        ),
        rx.hstack(
            rx.button(
                rx.cond(
                    SismosState.playing,
                    rx.icon("pause", size=14),
                    rx.icon("play", size=14),
                ),
                on_click=SismosState.play,
                size="1",
                variant="soft",
            ),
            rx.text("Hasta ", SismosState.period_label, size="2", weight="bold"),
            spacing="2",
            align="center",
        ),
        rx.slider(
            min=FIRST_YEAR,
            max=current_year(),
            step=1,
            default_value=[current_year()],
            value=[SismosState.year],
            on_change=SismosState.set_year,
            width="100%",
        ),
        rx.text("Mes", size="1", color=rx.color("gray", 11)),
        rx.slider(
            min=1,
            max=12,
            step=1,
            default_value=[12],
            value=[SismosState.month],
            on_change=SismosState.set_month,
            width="100%",
        ),
        rx.text("Magnitud mínima: ", SismosState.min_mag, size="1"),
        rx.slider(
            min=4.0,
            max=8.0,
            step=0.1,
            default_value=[4.0],
            value=[SismosState.min_mag],
            on_change=SismosState.set_min_mag,
            width="100%",
        ),
        rx.select(
            list(DEPTH_BAND_LABELS.values()),
            value=SismosState.depth_band_label,
            on_change=SismosState.set_depth_band,
            size="1",
        ),
        rx.hstack(
            rx.checkbox(
                "En vivo",
                checked=SismosState.show_live,
                on_change=SismosState.toggle_live,
                size="1",
            ),
            rx.checkbox(
                "Densidad",
                checked=SismosState.show_heat,
                on_change=SismosState.toggle_heat,
                size="1",
            ),
            spacing="3",
            width="100%",
        ),
        rx.hstack(
            rx.checkbox(
                "Fallas",
                checked=SismosState.show_faults,
                on_change=SismosState.toggle_faults,
                size="1",
            ),
            rx.checkbox(
                "Relieve",
                checked=SismosState.show_terrain,
                on_change=SismosState.toggle_terrain,
                size="1",
            ),
            spacing="3",
            width="100%",
        ),
        rx.checkbox(
            "Sismos notables",
            checked=SismosState.show_notable,
            on_change=SismosState.toggle_notable,
            size="1",
        ),
        rx.cond(
            SismosState.show_live,
            rx.text(
                SismosState.live_count,
                " sismos en 30 días · ",
                SismosState.live_fetched_at,
                size="1",
                color=rx.color("gray", 11),
            ),
        ),
        rx.cond(
            SismosState.hovered_fault != "",
            rx.text(SismosState.hovered_fault, size="1", weight="bold"),
        ),
        rx.text(COVERAGE_NOTE, size="1", color=rx.color("gray", 11)),
        rx.text(ATTRIBUTION, size="1", color=rx.color("gray", 11)),
        spacing="2",
        align="start",
        width="320px",
        padding="14px",
        border_radius="10px",
        background=rx.color("gray", 2),
        border=f"1px solid {rx.color('gray', 5)}",
    )


def _map() -> rx.Component:
    return mapcn.map(
        mapcn.map_circle_layer(
            id="quakes",
            data=SismosState.catalog,
            promote_id="id",
            radius=MAG_RADIUS,
            color=DEPTH_COLOR,
            opacity=0.75,
            stroke_color="#ffffff",
            stroke_width=0.5,
            filter=SismosState.layer_filter,
            hover_paint={"circle-stroke-width": 2},
            on_click=SismosState.select_quake,
        ),
        rx.cond(
            SismosState.show_heat,
            mapcn.map_heatmap_layer(
                id="density",
                data=SismosState.catalog,
                filter=SismosState.layer_filter,
                weight_property=HEATMAP_WEIGHT_PROPERTY,
                weight_range=HEATMAP_WEIGHT_RANGE,
                max_zoom_fade=HEATMAP_MAX_ZOOM_FADE,
            ),
        ),
        rx.cond(
            SismosState.show_faults,
            mapcn.map_layer(
                id="faults",
                source={"type": "geojson", "data": VENEZUELA_FAULTS_URL},
                layer={
                    "type": "line",
                    "paint": {
                        "line-color": FAULT_COLOR,
                        "line-width": 1.4,
                        "line-opacity": 0.9,
                    },
                },
                interactive=True,
                hover_paint={"line-width": 3},
                on_hover=SismosState.show_fault,
            ),
        ),
        rx.cond(
            SismosState.show_live,
            rx.fragment(
                mapcn.map_circle_layer(
                    id="live",
                    data=SismosState.live,
                    promote_id="id",
                    radius=MAG_RADIUS,
                    color=LIVE_COLOR,
                    opacity=0.9,
                    stroke_color="#78350f",
                    stroke_width=0.8,
                    on_click=SismosState.select_quake,
                ),
                mapcn.map_circle_layer(
                    id="live-ring",
                    data=SismosState.live,
                    filter=RECENT_FILTER,
                    radius=18,
                    color="rgba(0,0,0,0)",
                    opacity=0,
                    stroke_color=LIVE_COLOR,
                    stroke_width=2,
                    stroke_opacity=0.5,
                    interactive=False,
                ),
            ),
        ),
        rx.cond(
            SismosState.show_terrain,
            mapcn.map_terrain(
                preset=TERRAIN_PRESET,
                hillshade=True,
                exaggeration=TERRAIN_EXAGGERATION,
            ),
        ),
        rx.cond(
            SismosState.show_notable,
            rx.fragment(
                *[
                    mapcn.map_marker(
                        mapcn.marker_content(
                            rx.box(
                                width="14px",
                                height="14px",
                                border_radius="9999px",
                                border="2px solid white",
                                background_color="#7c3aed",
                                box_shadow="0 2px 4px rgba(0,0,0,.35)",
                            )
                        ),
                        mapcn.marker_tooltip(
                            f"{quake.name} · M {quake.magnitude} · {quake.date}"
                        ),
                        longitude=quake.longitude,
                        latitude=quake.latitude,
                    )
                    for quake in NOTABLE_QUAKES
                ]
            ),
        ),
        rx.cond(
            SismosState.has_selection,
            mapcn.map_popup(
                rx.vstack(
                    rx.text(SismosState.selected_title, weight="bold", size="2"),
                    rx.text(SismosState.selected["place"], size="1"),
                    rx.text("Profundidad: ", SismosState.selected_depth, size="1"),
                    rx.text(SismosState.selected_utc, size="1"),
                    rx.text(SismosState.selected_caracas, size="1"),
                    rx.link(
                        "Ficha del USGS",
                        href=SismosState.selected["url"],
                        is_external=True,
                        size="1",
                    ),
                    spacing="1",
                    align="start",
                ),
                longitude=SismosState.selected_center[0],
                latitude=SismosState.selected_center[1],
                on_close=SismosState.close_popup,
            ),
        ),
        mapcn.map_controls(position="top-right", show_compass=True),
        center=VENEZUELA_CENTER,
        zoom=5.4,
        max_bounds=[[-80.0, -3.0], [-53.0, 18.0]],
        styles={"light": BASE_STYLE, "dark": BASE_STYLE},
        height="680px",
        width="100%",
    )


@rx.page(
    route="/sismos",
    title="Sismos · reflex-mapcn",
    on_load=SismosState.load_catalog,
)
def sismos_page() -> rx.Component:
    return page(
        "Sismos",
        "Catálogo histórico del USGS para Venezuela desde 1900, dibujado con "
        "map_circle_layer: el radio sigue la magnitud y el color la profundidad. "
        "Los filtros se aplican en el navegador con setFilter, sin volver al backend.",
        section(
            "Mapa sísmico",
            "Mueve el deslizador temporal o pulsa reproducir para ver la "
            "secuencia por años. Haz clic en un sismo para ver su ficha.",
            rx.hstack(
                _controls(),
                rx.box(_map(), flex="1", min_width="0"),
                spacing="3",
                align="start",
                width="100%",
            ),
            rx.hstack(_legend(), spacing="3", align="start"),
        ),
    )
