"""Raster tile services and symbol layers, one source at a time.

Every tile service the package knows about is here behind a selector: the
three presets that need no credentials, the RainViewer radar, and the three
that only answer with an API key of your own. Picking one rebuilds the layer,
and the opacity and visibility controls change it in place, without touching
the source.
"""

from __future__ import annotations

import asyncio
import dataclasses
from datetime import datetime, timezone

import reflex as rx
import reflex_mapcn as mapcn
from reflex_mapcn import rainviewer_frames, rainviewer_tiles

from ..layout import code, demo_frame, page, section
from ..services import env as env_service
from ..venezuela_data import CITIES, VENEZUELA_CENTER

# The keys of the optional services live in `mapcn_demo/.env`; anything
# already exported in the shell wins over that file.
env_service.load_env_file()

BASE_STYLE = "https://tiles.openfreemap.org/styles/positron"

# Labels need the style to say where its fonts come from, and the blank
# basemap does not, so the symbol demo hands the map these glyphs.
GLYPHS_URL = "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf"

ICON_NAME = "pin"
ICON_URL = "/pin.png"

# `absolute` colours every road by its current speed. The `relative0` style
# of the README recipe only paints what is slower than free flow, which on a
# quiet afternoon means an empty layer.
TOMTOM_TEMPLATE = (
    "https://api.tomtom.com/traffic/map/4/tile/flow/absolute/"
    "{{z}}/{{x}}/{{y}}.png?key={key}"
)
OPENWEATHER_TEMPLATE = (
    "https://tile.openweathermap.org/map/{layer}/{{z}}/{{x}}/{{y}}.png?appid={key}"
)


@dataclasses.dataclass(frozen=True)
class Source:
    """One tile service the page can switch to."""

    key: str
    label: str
    description: str
    preset: str | None = None
    env_var: str | None = None
    template: str | None = None
    layer: str = ""
    attribution: str | None = None
    signup: str = ""
    # Where this service actually shows something: traffic needs a city,
    # clouds need a country.
    center: tuple[float, float] | None = None
    zoom: float = 5.2


SOURCES: list[Source] = [
    Source(
        key="openrailwaymap",
        label="OpenRailwayMap · vías férreas",
        description=(
            "La red ferroviaria mundial dibujada sobre el basemap. Preset del "
            "paquete: trae sus teselas, su zoom máximo y su atribución."
        ),
        preset="openrailwaymap",
        center=(-68.5, 10.1),
        zoom=7.5,
    ),
    Source(
        key="openseamap",
        label="OpenSeaMap · cartas náuticas",
        description=(
            "Boyas, faros y señales marítimas. Se ve mejor sobre la costa, "
            "así que acércate al Caribe."
        ),
        preset="openseamap",
        center=(-66.95, 10.62),
        zoom=9.5,
    ),
    Source(
        key="esri_satellite",
        label="Esri World Imagery · satélite",
        description=(
            "Imagen satelital opaca: baja la opacidad para mezclarla con el "
            "basemap y comparar."
        ),
        preset="esri_satellite",
    ),
    Source(
        key="rainviewer",
        label="RainViewer · radar de lluvia",
        description=(
            "Radar meteorológico en tiempo casi real. Las rutas de cada "
            "fotograma caducan, así que el backend las pide con "
            "rainviewer_frames() y construye las teselas con rainviewer_tiles()."
        ),
        preset="rainviewer",
    ),
    Source(
        key="tomtom_traffic",
        label="TomTom · tráfico (requiere clave)",
        description=(
            "Velocidad absoluta del tráfico. No hay preset porque el servicio "
            "es comercial: la clave se queda en el entorno y solo viaja "
            "dentro de la plantilla de teselas. TomTom no cubre Venezuela, "
            "así que esta capa se muestra sobre Bogotá."
        ),
        env_var="TOMTOM_API_KEY",
        template=TOMTOM_TEMPLATE,
        attribution="© TomTom",
        signup="https://developer.tomtom.com/",
        # Measured: a flow tile over Caracas is an empty 1.2 KB image and the
        # same tile over Bogota is 48 KB. The service has no data here.
        center=(-74.072, 4.711),
        zoom=12.0,
    ),
    Source(
        key="openweather_clouds",
        label="OpenWeather · nubosidad (requiere clave)",
        description="Cobertura de nubes del mapa meteorológico de OpenWeather.",
        env_var="OPENWEATHER_API_KEY",
        template=OPENWEATHER_TEMPLATE,
        layer="clouds_new",
        attribution="© OpenWeather",
        signup="https://openweathermap.org/api",
    ),
    Source(
        key="openweather_rain",
        label="OpenWeather · precipitación (requiere clave)",
        description="La misma clave, otra capa: precipitación acumulada.",
        env_var="OPENWEATHER_API_KEY",
        template=OPENWEATHER_TEMPLATE,
        layer="precipitation_new",
        attribution="© OpenWeather",
        signup="https://openweathermap.org/api",
    ),
]

PRESET_SOURCES = [s for s in SOURCES if s.preset and s.key != "rainviewer"]

SOURCE_LABELS = [source.label for source in SOURCES]


def source_by_key(key: str) -> Source:
    """The source with that id, or the first one."""
    for source in SOURCES:
        if source.key == key:
            return source
    return SOURCES[0]


def key_from_label(label: str) -> str:
    """Turn what the selector shows back into the id the state keeps."""
    for source in SOURCES:
        if source.label == label:
            return source.key
    return SOURCES[0].key


def is_ready(source: Source, environ: dict[str, str]) -> bool:
    """Whether this source can draw anything right now."""
    if source.env_var is None:
        return True
    return bool(environ.get(source.env_var, "").strip())


def tiles_for(source: Source, api_key: str) -> list[str]:
    """The tile templates of a keyed source; a preset brings its own."""
    if source.template is None or not api_key:
        return []
    return [source.template.format(key=api_key, layer=source.layer)]


def radar_tiles(frames: dict) -> tuple[list[str], str]:
    """The newest radar frame as tiles, with the time it was captured."""
    past = frames.get("past") or []
    if not past:
        return [], "El radar de RainViewer no devolvió fotogramas."
    frame = past[-1]
    tiles = rainviewer_tiles(frame, frames.get("host", ""))
    moment = datetime.fromtimestamp(int(frame["time"]), tz=timezone.utc)
    return tiles, f"Fotograma de las {moment:%H:%M} UTC"


def view_for(source: Source) -> dict:
    """Where to stand to see this service."""
    center = source.center or tuple(VENEZUELA_CENTER)
    return {"center": [center[0], center[1]], "zoom": source.zoom}


def camera_for(source: Source, seq: int) -> dict:
    """The camera command that brings that view into place."""
    view = view_for(source)
    return mapcn.camera_command(
        "flyTo", center=view["center"], zoom=view["zoom"], duration=1200
    ) | {"seq": seq}


def symbol_features() -> dict:
    """A handful of capitals as a FeatureCollection for the symbol layer."""
    chosen = [city for city in CITIES if city.kind in ("nacional", "estadal")][:10]
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": index,
                "properties": {"name": city.name, "kind": city.kind},
                "geometry": {"type": "Point", "coordinates": [city.lng, city.lat]},
            }
            for index, city in enumerate(chosen)
        ],
    }


SYMBOL_DATA = symbol_features()


class RasterState(rx.State):
    """The selected tile service and how it is painted."""

    source_key: str = SOURCES[0].key
    opacity: float = 0.85
    visible: bool = True

    radar: list[str] = []
    radar_note: str = ""
    radar_loading: bool = False

    blank_basemap: bool = False
    show_labels: bool = True

    command: dict = {}
    _seq: int = 0

    # ---- derived ----------------------------------------------------------

    @rx.var
    def source_label(self) -> str:
        return source_by_key(self.source_key).label

    @rx.var
    def description(self) -> str:
        return source_by_key(self.source_key).description

    @rx.var
    def is_radar(self) -> bool:
        return self.source_key == "rainviewer"

    @rx.var
    def missing_key(self) -> str:
        """The variable this source needs and does not have."""
        source = source_by_key(self.source_key)
        if source.env_var is None or env_service.api_key(source.env_var):
            return ""
        return source.env_var

    @rx.var
    def signup_url(self) -> str:
        return source_by_key(self.source_key).signup

    @rx.var
    def keyed_tiles(self) -> list[str]:
        source = source_by_key(self.source_key)
        if source.env_var is None:
            return []
        return tiles_for(source, env_service.api_key(source.env_var))

    @rx.var
    def has_keyed_tiles(self) -> bool:
        return len(self.keyed_tiles) > 0

    @rx.var
    def has_radar(self) -> bool:
        return self.is_radar and len(self.radar) > 0

    @rx.var
    def attribution(self) -> str:
        return source_by_key(self.source_key).attribution or ""

    @rx.var
    def opacity_label(self) -> str:
        return f"Opacidad: {int(self.opacity * 100)} %"

    # ---- events -----------------------------------------------------------

    @rx.event
    def select_source(self, label: str):
        self.source_key = key_from_label(label)
        self._seq += 1
        self.command = camera_for(source_by_key(self.source_key), self._seq)
        if self.source_key == "rainviewer" and not self.radar:
            return RasterState.load_radar

    @rx.event(background=True)
    async def load_radar(self):
        """Read the radar index; its frame paths expire every couple of hours."""
        async with self:
            if self.radar_loading:
                return
            self.radar_loading = True

        frames = await asyncio.to_thread(rainviewer_frames)
        tiles, note = radar_tiles(frames)

        async with self:
            self.radar = tiles
            self.radar_note = note
            self.radar_loading = False

    @rx.event
    def set_opacity(self, value: list[float]):
        self.opacity = float(value[0]) / 100

    @rx.event
    def toggle_visible(self, value: bool):
        self.visible = bool(value)

    @rx.event
    def toggle_blank(self, value: bool):
        self.blank_basemap = bool(value)

    @rx.event
    def toggle_labels(self, value: bool):
        self.show_labels = bool(value)


def _preset_layer(source: Source) -> rx.Component:
    """One preset layer, mounted only while its source is the selected one."""
    return rx.cond(
        RasterState.source_key == source.key,
        mapcn.map_raster_layer(
            id=f"raster-{source.key}",
            preset=source.preset,
            opacity=RasterState.opacity,
            visible=RasterState.visible,
        ),
    )


def _raster_map() -> rx.Component:
    return mapcn.map(
        mapcn.map_camera(command=RasterState.command),
        *[_preset_layer(source) for source in PRESET_SOURCES],
        rx.cond(
            RasterState.has_radar,
            mapcn.map_raster_layer(
                id="raster-radar",
                preset="rainviewer",
                tiles=RasterState.radar,
                opacity=RasterState.opacity,
                visible=RasterState.visible,
            ),
        ),
        rx.cond(
            RasterState.has_keyed_tiles,
            mapcn.map_raster_layer(
                id="raster-keyed",
                tiles=RasterState.keyed_tiles,
                attribution=RasterState.attribution,
                opacity=RasterState.opacity,
                visible=RasterState.visible,
            ),
        ),
        mapcn.map_controls(position="top-right"),
        center=VENEZUELA_CENTER,
        zoom=5.2,
        styles={"light": BASE_STYLE, "dark": BASE_STYLE},
    )


def _raster_panel() -> rx.Component:
    return rx.vstack(
        rx.text("Fuente de datos", size="1", weight="bold"),
        rx.select(
            SOURCE_LABELS,
            value=RasterState.source_label,
            on_change=RasterState.select_source,
            size="1",
            width="100%",
        ),
        rx.text(RasterState.description, size="1", color=rx.color("gray", 11)),
        rx.cond(
            RasterState.missing_key != "",
            rx.callout(
                rx.text(
                    "Falta ",
                    rx.code(RasterState.missing_key),
                    " en mapcn_demo/.env. Añádela y reinicia la demo.",
                    size="1",
                ),
                icon="key-round",
                color_scheme="amber",
                size="1",
                width="100%",
            ),
        ),
        rx.cond(
            RasterState.is_radar & (RasterState.radar_note != ""),
            rx.text(RasterState.radar_note, size="1", color=rx.color("gray", 11)),
        ),
        rx.divider(),
        rx.text(RasterState.opacity_label, size="1"),
        rx.slider(
            min=0,
            max=100,
            step=5,
            default_value=85,
            on_change=RasterState.set_opacity,
            width="100%",
        ),
        rx.hstack(
            rx.switch(
                checked=RasterState.visible,
                on_change=RasterState.toggle_visible,
                size="1",
            ),
            rx.text("Capa visible", size="1"),
            spacing="2",
            align="center",
        ),
        rx.text(
            "La opacidad y la visibilidad se aplican sin recrear la fuente; "
            "cambiar de servicio sí la reconstruye.",
            size="1",
            color=rx.color("gray", 10),
        ),
        spacing="2",
        align="start",
        width="320px",
        flex="0 0 auto",
        padding="14px",
        border_radius="10px",
        background=rx.color("gray", 2),
        border=f"1px solid {rx.color('gray', 5)}",
    )


def _symbol_map() -> rx.Component:
    return mapcn.map(
        mapcn.map_symbol_layer(
            id="capitales",
            data=SYMBOL_DATA,
            images={ICON_NAME: ICON_URL},
            icon_image=ICON_NAME,
            icon_size=0.7,
            icon_allow_overlap=True,
            text_field=["get", "name"],
            text_size=12,
            text_offset=[0, 1.4],
            text_anchor="top",
            text_color="#0f172a",
            text_halo_color="#ffffff",
            text_halo_width=1.2,
            text_opacity=rx.cond(RasterState.show_labels, 1.0, 0.0),
        ),
        mapcn.map_controls(position="top-right", show_zoom=True),
        center=VENEZUELA_CENTER,
        zoom=5.2,
        blank=RasterState.blank_basemap,
        glyphs_url=GLYPHS_URL,
        styles={"light": BASE_STYLE, "dark": BASE_STYLE},
    )


def _symbol_panel() -> rx.Component:
    return rx.hstack(
        rx.hstack(
            rx.switch(
                checked=RasterState.blank_basemap,
                on_change=RasterState.toggle_blank,
                size="1",
            ),
            rx.text("Basemap transparente", size="1"),
            spacing="2",
            align="center",
        ),
        rx.hstack(
            rx.switch(
                checked=RasterState.show_labels,
                on_change=RasterState.toggle_labels,
                size="1",
            ),
            rx.text("Etiquetas", size="1"),
            spacing="2",
            align="center",
        ),
        rx.text(
            "Sin tipografías en el estilo, el texto se omitiría con un aviso; "
            "el mapa recibe glyphs_url para que no ocurra.",
            size="1",
            color=rx.color("gray", 10),
        ),
        spacing="4",
        align="center",
        width="100%",
        wrap="wrap",
    )


@rx.page(route="/raster", title="Raster · reflex-mapcn")
def raster_page() -> rx.Component:
    return page(
        "Capas raster y símbolos",
        "`map_raster_layer` pone cualquier servicio de teselas sobre el "
        "basemap: presets sin credenciales, el radar de RainViewer, o el "
        "servicio comercial que tengas contratado. `map_symbol_layer` dibuja "
        "iconos y etiquetas sobre datos de puntos.",
        section(
            "Un servicio de teselas cada vez",
            "Elige la fuente en el panel. Los tres primeros presets y el "
            "radar funcionan sin registrarte; el tráfico y el clima piden una "
            "clave propia y avisan cuando no está en el entorno.",
            rx.hstack(
                _raster_panel(),
                rx.box(
                    demo_frame(_raster_map(), height="560px"), flex="1", min_width="0"
                ),
                spacing="3",
                align="start",
                width="100%",
            ),
            code(
                """
# a preset carries its tiles, its zoom range and its attribution
mapcn.map_raster_layer(preset="openseamap", opacity=0.85)

# a commercial service: the key stays in the environment
mapcn.map_raster_layer(
    tiles=[f"https://api.tomtom.com/traffic/map/4/tile/flow/absolute/"
           f"{z}/{x}/{y}.png?key={KEY}"],
    attribution="© TomTom",
)

# radar paths expire, so the backend refreshes them
frames = rainviewer_frames()
tiles = rainviewer_tiles(frames["past"][-1], frames["host"])
mapcn.map_raster_layer(preset="rainviewer", tiles=tiles, opacity=0.7)
"""
            ),
        ),
        section(
            "Iconos y etiquetas",
            "El icono viaja en `images` y se retira con la capa. Las "
            "etiquetas necesitan las tipografías del estilo, así que el mapa "
            "recibe `glyphs_url` y siguen dibujándose incluso con el basemap "
            "transparente.",
            _symbol_panel(),
            demo_frame(_symbol_map(), height="520px"),
            code(
                """
mapcn.map(
    mapcn.map_symbol_layer(
        data=CAPITALES,                   # FeatureCollection of points
        images={"pin": "/pin.png"},       # loaded with the layer, removed with it
        icon_image="pin",
        icon_allow_overlap=True,
        text_field=["get", "name"],
        text_offset=[0, 1.4],
        text_halo_color="#ffffff",
    ),
    blank=True,
    glyphs_url="https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf",
)
"""
            ),
        ),
        section(
            "Sobre las fuentes",
            "OpenRailwayMap y OpenSeaMap sirven teselas derivadas de "
            "OpenStreetMap (ODbL); Esri World Imagery se usa bajo los "
            "términos de Esri; RainViewer publica su radar gratis para uso no "
            "comercial. TomTom y OpenWeather requieren una clave propia y su "
            "capa gratuita basta para esta demo. Cada preset lleva su "
            "atribución, y MapLibre la muestra en el control de abajo a la "
            "derecha.",
        ),
    )
