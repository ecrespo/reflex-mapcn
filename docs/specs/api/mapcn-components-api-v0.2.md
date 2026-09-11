# reflex-mapcn 0.2.0 — API Specification (componentes, helpers y servicios de la demo)

## Metadata

| Campo | Valor |
|---|---|
| **Autor** | Ernesto Crespo / Claude |
| **Estado** | `APPROVED` — aprobado 2026-09-11 (checkpoint 2) |
| **Versión API** | 0.2.0 (SemVer del paquete) |
| **Fecha** | 2026-09-11 |
| **PRD relacionado** | `docs/specs/prd/mapcn-layers-0.2.md` |
| **Superficie** | Python: `reflex_mapcn` (componentes, helpers) · JSX: exports de `mapcn.jsx` · Demo: servicios en `mapcn_demo/services/` |

---

## 1. Visión general

Este documento es el **contrato** entre tres consumidores: (a) la app Reflex del usuario, que llama a las factorías Python; (b) el compilador de Reflex, que traduce props a JSX; (c) el módulo `mapcn.jsx`, que implementa el comportamiento. No hay endpoints HTTP propios: la "API" son firmas Python, props JS y payloads de eventos. Los servicios externos (USGS, OSRM, RainViewer) se envuelven en funciones Python de la demo con contrato definido aquí.

Compatibilidad: todo lo publicado en 0.1.0 se conserva sin cambios de firma (Art. 7). Los componentes nuevos son aditivos.

## 2. Convenciones generales

### 2.1 Nombres e ids
- Factoría Python `snake_case` → clase `PascalCase` → tag JSX con alias `Mapcn<Tag>`.
- Cada componente de capa acepta `id: str` opcional; si falta, se usa `useId()`. Ids MapLibre derivados: `{kind}-source-{id}`, `{kind}-layer-{id}` (y sufijos `-hillshade`, `-hit` cuando aplique). Los ids son estables entre re-renders del mismo componente.
- `before_id` se resuelve con `resolveBeforeId` (si la capa no existe → se ignora sin error).

### 2.2 Props
- `snake_case` en Python → `camelCase` en JS (automático). Las props que son propiedades de paint/layout MapLibre se documentan con su nombre MapLibre entre paréntesis.
- Los valores numéricos aceptan **número o expresión MapLibre** (lista JSON) donde MapLibre lo permita; el wrapper los tipa como `rx.Var[float | list]`.
- Props booleanas por defecto `False` salvo que se indique.
- `visible: bool = True` en todas las capas → `layout.visibility` (`visible`/`none`).

### 2.3 Payloads de eventos (Art. 2)

```jsonc
// LayerFeatureEvent — usado por map_layer, map_circle_layer, map_symbol_layer
{
  "feature": {
    "type": "Feature",
    "id": "string | number | null",
    "properties": { },
    "geometry": { "type": "Point", "coordinates": [lng, lat] } | null,
    "source": "string | null",
    "sourceLayer": "string | null"
  },
  "longitude": 0.0,
  "latitude": 0.0
}
// on_hover recibe LayerFeatureEvent o null (cursor sale de la capa)
```

### 2.4 Errores en Python
Validación en `create()` (antes de compilar): `ValueError` con mensaje `"<component>: <prop> <razón>"`. Nunca se valida en tiempo de ejecución del backend.

### 2.5 Ciclo de vida común (aplica a todas las capas nuevas)

| Evento | Comportamiento |
|---|---|
| Montaje con `isLoaded=false` | Espera; no toca el mapa |
| `isLoaded` → true | Añade fuente(s) y capa(s), registra listeners |
| Cambio de props "calientes" | `setData` / `setPaintProperty` / `setLayoutProperty` / `setFilter` / `setLayerZoomRange` |
| Cambio de props "frías" (tipo de fuente, `tiles`, `url`, `encoding`, `promote_id`, `cluster*`) | Teardown + re-add |
| `style.load` (tema/`styles`) | `isLoaded` pasa a false y luego a true ⇒ re-add automático por el mismo efecto |
| Desmontaje | Retira listeners, capas, fuentes, imágenes (orden inverso) |

---

## 3. Componentes

### 3.1 `map_raster_layer` — clase `MapRasterLayer` (F1)

**Descripción:** superpone teselas raster (PNG/JPEG/WebP) de un servicio XYZ/TMS o TileJSON.

| Prop Python | Tipo | Default | JS / MapLibre | Notas |
|---|---|---|---|---|
| `id` | `str` | auto | `id` | prefijo de ids |
| `preset` | `Literal["rainviewer","openrailwaymap","openseamap","esri_satellite"]` | — | `preset` | rellena `tiles`, `tile_size`, `max_zoom`, `attribution` (§3.7) |
| `tiles` | `list[str]` | — | `tiles` | plantillas `{z}/{x}/{y}`; obligatorio si no hay `url` ni `preset` |
| `url` | `str` | — | `url` | TileJSON |
| `tile_size` | `Literal[256,512]` | 256 | `tileSize` | |
| `scheme` | `Literal["xyz","tms"]` | `"xyz"` | `scheme` | |
| `min_zoom` / `max_zoom` | `int` | 0 / 22 | `minzoom`/`maxzoom` (source y layer) | |
| `bounds` | `list[float]` (w,s,e,n) | — | `bounds` | limita peticiones |
| `attribution` | `str` | preset o "" | `attribution` | HTML permitido por MapLibre |
| `opacity` | `float` | 1.0 | `raster-opacity` | caliente |
| `resampling` | `Literal["linear","nearest"]` | `"linear"` | `raster-resampling` | |
| `saturation`, `contrast`, `brightness_min`, `brightness_max`, `hue_rotate` | `float` | MapLibre defaults | `raster-*` | calientes |
| `fade_duration` | `int` (ms) | 300 | `raster-fade-duration` | |
| `visible` | `bool` | `True` | `layout.visibility` | caliente |
| `before_id` | `str` | — | `beforeId` | |

**Eventos:** `on_load_error: EventHandler[{"source_id": str, "message": str}]` (COULD; throttled 60 s).

**Validación:** exactamente uno de `preset`, `tiles`, `url` presente ⇒ si ninguno: `ValueError("map_raster_layer: provide preset, tiles or url")`. Con `preset="rainviewer"` es obligatorio `tiles` calculado con `rainviewer_tiles(frame)` (ver §4.1) — el preset solo aporta `max_zoom=7`, `tile_size=256` y atribución.

**Ejemplo:**
```python
mapcn.map_raster_layer(preset="openseamap", opacity=0.9, before_id="waterway-name")
mapcn.map_raster_layer(tiles=[f"https://api.tomtom.com/traffic/map/4/tile/flow/relative0/{{z}}/{{x}}/{{y}}.png?key={KEY}"], attribution="© TomTom")
```

### 3.2 `map_layer` — clase `MapLayer` (F2)

| Prop Python | Tipo | Default | Notas |
|---|---|---|---|
| `id` | `str` | auto | |
| `source` | `dict \| str` | requerido | dict = `SourceSpecification` MapLibre; str = id de fuente existente |
| `layer` | `dict` | requerido | `LayerSpecification` sin `id` ni `source` (se inyectan). `type` obligatorio: `fill, line, circle, symbol, heatmap, fill-extrusion, raster, hillshade, background` |
| `before_id` | `str` | — | |
| `interactive` | `bool` | `False` | activa cursor, hover state y eventos |
| `hover_paint` | `dict` | — | fusionado con `case feature-state.hover` sobre `layer.paint` |
| `visible` | `bool` | `True` | |

**Eventos:** `on_click: EventHandler[LayerFeatureEvent]`, `on_hover: EventHandler[LayerFeatureEvent | None]`.

**Calientes:** `source.data` (geojson), `layer.paint`, `layer.layout`, `layer.filter`, `layer.minzoom/maxzoom`. **Frías:** todo lo demás.

**Validación:** `layer` sin `type` ⇒ `ValueError("map_layer: layer.type is required")`; `source` de tipo no soportado ⇒ `ValueError("map_layer: source must be a dict or a source id")`. En runtime, un id de fuente inexistente no lanza: se omite la capa con advertencia y se reintenta tras `style.load` (REQ-LAY-010).

**Defaults de `interactive`:** `False` en `map_layer` (capa genérica, puede ser raster/background) y `True` en `map_circle_layer`/`map_symbol_layer` (capas de puntos, casi siempre clicables). Decisión intencional, documentada en README.

**Ejemplo (edificios 3D sobre OpenFreeMap):**
```python
mapcn.map_layer(
    source="openmaptiles",                      # fuente del estilo Liberty
    layer={"type": "fill-extrusion", "source-layer": "building", "minzoom": 14,
           "paint": {"fill-extrusion-height": ["get", "render_height"], "fill-extrusion-color": "#94a3b8", "fill-extrusion-opacity": 0.8}},
)
```

### 3.3 `map_heatmap_layer` — clase `MapHeatmapLayer` (F3)

| Prop Python | Tipo | Default | MapLibre |
|---|---|---|---|
| `id` | `str` | auto | |
| `data` | `dict \| str` | requerido | fuente geojson (FeatureCollection de puntos o URL) |
| `weight` | `float \| list` | 1 | `heatmap-weight` |
| `weight_property` + `weight_range` | `str`, `list[float]` | — | genera `heatmap-weight` interpolado (REQ-HEA-003); ignorado si `weight` explícito |
| `intensity` | `float \| list` | `["interpolate",["linear"],["zoom"],0,1,9,3]` | `heatmap-intensity` |
| `radius` | `float \| list` | `["interpolate",["linear"],["zoom"],0,2,9,20]` | `heatmap-radius` |
| `color` | `list` | rampa azul→amarillo→rojo (ver Data Model §5) | `heatmap-color` |
| `opacity` | `float \| list` | 0.8 | `heatmap-opacity` |
| `max_zoom_fade` | `float` | — | genera `heatmap-opacity` que desvanece entre `Z-1` y `Z` (REQ-HEA-004) |
| `before_id`, `visible` | | | |

**Eventos:** ninguno (heatmap no es interactivo en MapLibre).

### 3.4 `map_circle_layer` — clase `MapCircleLayer` (F4)

| Prop Python | Tipo | Default | MapLibre |
|---|---|---|---|
| `id` | `str` | auto | |
| `data` | `dict \| str` | requerido | fuente geojson |
| `promote_id` | `str` | — | fuente; necesario para hover state estable |
| `radius` | `float \| list` | 5 | `circle-radius` |
| `color` | `str \| list` | `#3b82f6` | `circle-color` |
| `opacity` | `float \| list` | 0.85 | `circle-opacity` |
| `stroke_color` | `str \| list` | `#ffffff` | `circle-stroke-color` |
| `stroke_width` | `float \| list` | 1 | `circle-stroke-width` |
| `stroke_opacity` | `float \| list` | 1 | `circle-stroke-opacity` |
| `blur` | `float \| list` | 0 | `circle-blur` |
| `pitch_scale` | `Literal["map","viewport"]` | `"map"` | `circle-pitch-scale` |
| `sort_key` | `list` | — | `circle-sort-key` |
| `filter` | `list` | — | `filter` (caliente) |
| `min_zoom` / `max_zoom` | `float` | — | `minzoom`/`maxzoom` |
| `cluster`, `cluster_radius`, `cluster_max_zoom` | `bool`, `int`, `int` | `False`, 50, 14 | fuente (COULD) |
| `hover_paint` | `dict` | — | fusión con `feature-state.hover` |
| `interactive` | `bool` | `True` | |
| `before_id`, `visible` | | | |

**Eventos:** `on_click`, `on_hover` (LayerFeatureEvent).

### 3.5 `map_symbol_layer` — clase `MapSymbolLayer` (F4)

| Prop Python | Tipo | Default | MapLibre |
|---|---|---|---|
| `id`, `data`, `promote_id`, `filter`, `min_zoom`, `max_zoom`, `before_id`, `visible`, `interactive`, `hover_paint` | como circle | | |
| `images` | `dict[str, str]` | — | `loadImage`/`addImage` por clave; valor = URL o data URI PNG/SVG rasterizado |
| `icon_image` | `str \| list` | — | `icon-image` |
| `icon_size` | `float \| list` | 1 | `icon-size` |
| `icon_anchor` | `str` | `"center"` | `icon-anchor` |
| `icon_offset` | `list[float]` | `[0,0]` | `icon-offset` |
| `icon_rotate` | `float \| list` | 0 | `icon-rotate` |
| `icon_allow_overlap` | `bool` | `False` | `icon-allow-overlap` |
| `text_field` | `str \| list` | — | `text-field` (p. ej. `["get","name"]` o `"{name}"`) |
| `text_font` | `list[str]` | `["Noto Sans Regular"]` | `text-font` — debe existir en los glyphs del estilo |
| `text_size` | `float \| list` | 12 | `text-size` |
| `text_offset` | `list[float]` | `[0, 1.2]` | `text-offset` |
| `text_anchor` | `str` | `"top"` | `text-anchor` |
| `text_color` | `str \| list` | `#111827` | `text-color` |
| `text_halo_color` | `str` | `#ffffff` | `text-halo-color` |
| `text_halo_width` | `float` | 1 | `text-halo-width` |
| `text_allow_overlap` | `bool` | `False` | `text-allow-overlap` |
| `text_optional` | `bool` | `True` | `text-optional` |

**Eventos:** `on_click`, `on_hover`.

**Nota de glyphs (REQ-PNT-004/005):** `Map` gana la prop `glyphs_url: str` (Reflex extra). Con `blank=True` y sin `glyphs_url`, `text_field` se omite con advertencia `mapcn: symbol text needs style glyphs; pass glyphs_url to Map`. Valor recomendado: `https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf` con `text_font=["Noto Sans Regular"]`; CARTO usa `["Open Sans Regular"]`.

### 3.6 `map_terrain` — clase `MapTerrain` (F5)

| Prop Python | Tipo | Default | Notas |
|---|---|---|---|
| `id` | `str` | auto | |
| `preset` | `Literal["aws_terrarium"]` | — | rellena `tiles`, `encoding`, `tile_size`, `max_zoom`, `attribution` |
| `tiles` / `url` | `list[str]` / `str` | — | fuente `raster-dem` |
| `encoding` | `Literal["terrarium","mapbox"]` | `"terrarium"` | |
| `tile_size` | `int` | 256 | |
| `max_zoom` | `int` | 15 | |
| `attribution` | `str` | preset | |
| `exaggeration` | `float` | 1.0 | `setTerrain({exaggeration})` (caliente) |
| `hillshade` | `bool` | `False` | añade capa `hillshade` |
| `hillshade_paint` | `dict` | `{"hillshade-exaggeration": 0.5}` | fusionado; `hillshade-shadow-color`, `-highlight-color`, `-accent-color`, `-illumination-direction` |
| `before_id` | `str` | — | para la capa hillshade |
| `visible` | `bool` | `True` | oculta hillshade y `setTerrain(null)` |

**Eventos:** ninguno. Extra en `Map`: cuando hay terreno activo, `on_move_end`/`on_viewport_change` añaden `"elevation": number | null` (COULD, REQ-TER-008).

### 3.7 Tabla de presets

| Preset | Componente | `tiles` | `tile_size` | `max_zoom` | Atribución | Licencia |
|---|---|---|---|---|---|---|
| `openrailwaymap` | raster | `https://{a,b,c}.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png` (3 URLs) | 256 | 19 | `© OpenRailwayMap contributors, CC BY-SA 2.0 · © OpenStreetMap` | CC BY-SA |
| `openseamap` | raster | `https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png` | 256 | 18 | `© OpenSeaMap contributors` | CC BY-SA |
| `esri_satellite` | raster | `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}` | 256 | 19 | `Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community` | Esri ToU |
| `rainviewer` | raster | construido con `rainviewer_tiles()` | 256 | 7 | `© RainViewer` | RainViewer ToU (gratuito no comercial) |
| `aws_terrarium` | terrain | `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png` | 256 | 15 | `Terrain: Mapzen/AWS Terrain Tiles` | Open (ver Mapzen attribution) |

Los presets viven en Python (`reflex_mapcn/presets.py`) para que el usuario pueda inspeccionarlos y copiarlos; el JSX no conoce presets.

---

## 4. Helpers Python (paquete)

### 4.1 RainViewer
```python
def rainviewer_frames(timeout: float = 10.0) -> RainViewerFrames  # {"host": str, "past": [Frame], "nowcast": [Frame], "generated": int}
def rainviewer_tiles(frame: Frame, host: str, *, size: int = 256, color: int = 2, smooth: bool = True, snow: bool = True) -> list[str]
```
`Frame = {"time": int (epoch s), "path": str}`. Fallo de red ⇒ `RainViewerFrames` vacío + `logging.warning` (REQ-RAS-007). Uso típico: en un `@rx.event(background=True)` cada 5 min guardar `tiles` en estado.

### 4.2 Expresiones
```python
def interpolate(prop: str, stops: list[tuple[float, float | str]], *, base: float | None = None) -> list   # ["interpolate", ["linear"|"exponential", base], ["get", prop], ...]
def step(prop: str, base: float | str, stops: list[tuple[float, float | str]]) -> list
def match(prop: str, cases: dict[str, Any], default: Any) -> list
def zoom_interpolate(stops: list[tuple[float, float]]) -> list
```
Azúcar opcional; los usuarios pueden pasar listas crudas.

---

## 5. Servicios de la demo (`mapcn_demo/services/`)

No forman parte del paquete publicado. Contratos:

### 5.1 `usgs.py`
```python
VENEZUELA_BBOX = (-74.0, 0.5, -59.0, 13.0)   # (minlon, minlat, maxlon, maxlat)

async def fetch_catalog(*, min_magnitude: float = 4.0, start: str = "1900-01-01", end: str | None = None,
                        bbox: tuple = VENEZUELA_BBOX, timeout: float = 15.0) -> SeismicCatalog
async def fetch_live(*, days: int = 30, min_magnitude: float = 2.5,
                     bbox: tuple = VENEZUELA_BBOX, timeout: float = 15.0) -> SeismicCatalog   # FDSN query con starttime = now - days
```
`SeismicCatalog = {"features": FeatureCollection recortada (Data Model §3), "count": int, "fetched_at": ISO-8601 UTC, "source": "usgs", "error": str | None}`. Caché: `functools`-like TTL en módulo (10 min catálogo, 60 s live) con clave = parámetros. Errores ⇒ `error` relleno, `features` = último valor cacheado o colección vacía (REQ-SIS-003).

URL construida: `https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&minlatitude=0.5&maxlatitude=13&minlongitude=-74&maxlongitude=-59&starttime=1900-01-01&minmagnitude=4.0&orderby=time&limit=20000`.

### 5.2 `osrm.py`
```python
async def table(origin: tuple[float, float], destinations: list[tuple[float, float]], *, profile: str = "driving", timeout: float = 15.0) -> TravelMatrix
async def route(coords: list[tuple[float, float]], *, profile: str = "driving", timeout: float = 15.0) -> RouteResult
```
`TravelMatrix = {"durations": list[float | None] (s), "distances": list[float | None] (m), "error": str | None}`; `RouteResult = {"coordinates": list[[lng, lat]], "duration": float, "distance": float, "error": str | None}`. Máx. 25 destinos por llamada (REQ-TVJ-001). Caché 1 h por `(origin, profile)`.

### 5.3 `faults.py` (script de build, no runtime)
`scripts/build_faults.py`: descarga `gem_active_faults_harmonized.geojson` del repo GEM, recorta a `[-76, -1, -57, 15]`, conserva `name, slip_type, average_dip, net_slip_rate, activity_confidence, catalog_id`, simplifica (tolerancia 0.005°) y escribe `mapcn_demo/assets/venezuela_fallas.geojson` (objetivo ≤ 300 KB). Ejecutado manualmente; el resultado se versiona.

---

## 6. Códigos de advertencia (consola JSX)

| Código | Cuándo |
|---|---|
| `mapcn: before_id "<id>" not found; layer appended` | REQ-LAY-008 |
| `mapcn: symbol text needs style glyphs; pass glyphs_url to Map` | REQ-PNT-004 |
| `mapcn: only one map_terrain per map is supported; replacing` | REQ-TER-007 |
| `mapcn: raster source "<id>" failed to load tiles` | REQ-RAS-011 / REQ-TER-009 |
| `mapcn: source "<id>" not found` | REQ-LAY-010 |
| `mapcn: image "<name>" failed to load` | REQ-PNT-010 |

## 7. Versionado

SemVer. 0.2.0 es aditivo. Deprecaciones futuras: aviso en `create()` (`DeprecationWarning`) durante una minor antes de retirar.

---

## Historial de cambios

| Versión | Fecha | Cambios |
|---|---|---|
| 0.2.0-draft | 2026-09-11 | Versión inicial |
| 0.2.0-draft.2 | 2026-09-11 | Analyze: advertencias LAY-010/PNT-010, defaults de `interactive` explicados |
