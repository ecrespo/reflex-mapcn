# reflex-mapcn 0.2.0 — Data Model Specification

## Metadata

| Campo | Valor |
|---|---|
| **Autor** | Ernesto Crespo / Claude |
| **Estado** | `APPROVED` — aprobado 2026-09-11 (checkpoint 4) |
| **Versión** | 1.0 |
| **Fecha** | 2026-09-11 |
| **Almacenamiento** | Sin base de datos. Datos en: props/estado Reflex (JSON), archivos estáticos en `assets/`, caché TTL en memoria de proceso, y esquemas de servicios externos |
| **Tech Design** | `docs/specs/technical/mapcn-layers-architecture.md` |

---

## 1. Visión general

Todo dato del sistema es JSON serializable que cruza tres fronteras: **servicio externo → backend** (USGS, OSRM, RainViewer), **backend → estado Reflex → props JSX** (GeoJSON recortado, expresiones, filtros) y **JSX → backend** (payloads de eventos). Este documento fija los esquemas en cada frontera, los tipos Python (`TypedDict`/dataclasses) que los representan y las convenciones (orden `[lng, lat]`, epochs en ms, UTC).

```
USGS FDSN ──▶ SeismicCatalog ──▶ SismosState.catalog ──▶ MapCircleLayer.data
OSRM table ─▶ TravelMatrix ────▶ VenezuelaState.travel_rows ─▶ tabla UI
RainViewer ─▶ RainViewerFrames ▶ State.rain_tiles ─────────▶ MapRasterLayer.tiles
GEM (build) ▶ assets/venezuela_fallas.geojson ─────────────▶ MapLayer.source.data (URL)
JSX evento ─▶ LayerFeatureEvent ▶ handler Python
```

## 2. Esquemas de props (frontera Python → JSX)

### 2.1 `LayerSpec` interno (lo que `useMapLayer` recibe)

```jsonc
{
  "id": "string",
  "source": { "type": "geojson|raster|raster-dem|vector|image|video", /* SourceSpecification */ },
  "sourceId": "string | undefined",          // cuando se reutiliza una fuente existente
  "layers": [ { "id": "string", "type": "...", "paint": {}, "layout": {}, "filter": [] , "minzoom": 0, "maxzoom": 24, "source-layer": "..." } ],
  "beforeId": "string | undefined",
  "interactive": false,
  "hoverPaint": { },                          // fusionado sobre layers[0].paint
  "images": { "name": "url|dataURI" },        // symbol
  "hotKeys": ["data", "paint", "layout", "filter", "zoomRange"]   // qué grupos de props sincroniza el efecto caliente; un componente puede excluir grupos (p. ej. raster no tiene "data")
}
```

Campos calientes vs. fríos (Tech Design DD-002):

| Campo | Caliente (set*) | Frío (recrear) |
|---|---|---|
| `source.data` (geojson) | ✔ `setData` | |
| `source.tiles`, `source.url`, `source.type`, `promoteId`, `cluster*`, `encoding`, `tileSize`, `scheme`, `bounds` | | ✔ |
| `layers[i].paint.*` | ✔ `setPaintProperty` | |
| `layers[i].layout.*` (incl. `visibility`) | ✔ `setLayoutProperty` | |
| `layers[i].filter` | ✔ `setFilter` | |
| `layers[i].minzoom/maxzoom` | ✔ `setLayerZoomRange` | |
| `layers[i].type`, `source-layer` | | ✔ |
| `beforeId` | ✔ `moveLayer` | |
| `images` | ✔ add/remove por clave | |

### 2.2 Presets (Python, `presets.py`)

```python
@dataclass(frozen=True)
class RasterPreset:
    name: str
    tiles: tuple[str, ...]
    tile_size: int
    max_zoom: int
    attribution: str
    license: str
    min_zoom: int = 0

@dataclass(frozen=True)
class TerrainPreset:
    name: str
    tiles: tuple[str, ...]
    encoding: Literal["terrarium", "mapbox"]
    tile_size: int
    max_zoom: int
    attribution: str
    license: str
```

Valores: ver API Spec §3.7. Regla de fusión: `props_finales = {**preset.as_props(), **{k: v for k, v in props_explicitas.items() if v is not None}}`.

### 2.3 Expresiones MapLibre

Se representan como `list` JSON; el wrapper no las valida (MapLibre lo hace). Helpers producen:

| Helper | Salida |
|---|---|
| `interpolate("mag", [(4, 4), (7, 24)])` | `["interpolate", ["linear"], ["get", "mag"], 4, 4, 7, 24]` |
| `step("depth", "#ef4444", [(70, "#f97316"), (300, "#3b82f6")])` | `["step", ["get", "depth"], "#ef4444", 70, "#f97316", 300, "#3b82f6"]` |
| `match("slip_type", {"Dextral": "#ef4444"}, "#64748b")` | `["match", ["get", "slip_type"], "Dextral", "#ef4444", "#64748b"]` |
| `zoom_interpolate([(0, 2), (9, 20)])` | `["interpolate", ["linear"], ["zoom"], 0, 2, 9, 20]` |

## 3. Esquema sísmico (frontera USGS → backend → cliente)

### 3.1 Entrada: USGS GeoJSON (subset relevante)

```jsonc
{ "type": "Feature", "id": "us7000abcd",
  "properties": { "mag": 5.1, "place": "35 km NNE of Cumaná, Venezuela", "time": 1690000000000, "updated": 0,
                  "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us7000abcd", "detail": "...",
                  "felt": null, "cdi": null, "mmi": null, "alert": null, "status": "reviewed", "tsunami": 0,
                  "sig": 400, "net": "us", "code": "7000abcd", "magType": "mww", "type": "earthquake", "title": "M 5.1 - ..." },
  "geometry": { "type": "Point", "coordinates": [-64.1, 10.7, 12.4] } }   // [lng, lat, depth_km]
```

### 3.2 Salida: `SeismicFeature` (recortado, lo que viaja al cliente)

```jsonc
{ "type": "Feature",
  "properties": { "id": "us7000abcd", "mag": 5.1, "magType": "mww", "depth": 12.4, "time": 1690000000000,
                  "place": "35 km NNE of Cumaná, Venezuela" },
  "geometry": { "type": "Point", "coordinates": [-64.1, 10.7] } }
```

| Campo | Tipo | Requerido | Origen | Notas |
|---|---|---|---|---|
| `id` | str | Sí | `Feature.id` del USGS | solo en properties: es lo que promociona `promote_id="id"`, y duplicarlo en la feature costaba 59 KB |
| `mag` | float | Sí | `properties.mag` | eventos con `mag` null se descartan |
| `magType` | str | No | `properties.magType` | |
| `depth` | float (km) | Sí | `geometry.coordinates[2]` | null → 0.0 y se marca `depth_unknown: true` |
| `time` | int (ms UTC) | Sí | `properties.time` | filtro temporal; NO ISO para que `["<=", ["get","time"], t]` funcione |
| `place` | str | No | `properties.place` | |
| `recent` | bool | Sí en el feed live | calculado | `now - time < 24 h`; ausente en el histórico, donde siempre sería `false` |
| `geometry.coordinates` | [lng, lat] | Sí | redondeo 4 decimales | |

La ficha del USGS no viaja: se reconstruye desde el id con
`https://earthquake.usgs.gov/earthquakes/eventpage/{id}`. Eran 236 KB de los
1 089 KB medidos antes del Delta `2026-09-catalog-payload`.

### 3.3 `SeismicCatalog` (TypedDict Python)

```python
class SeismicCatalog(TypedDict):
    features: dict            # FeatureCollection de SeismicFeature
    count: int
    fetched_at: str           # ISO-8601 UTC
    source: Literal["usgs"]
    min_magnitude: float
    start: str                # ISO date
    end: str | None
    error: str | None
```

### 3.4 Estado de la página (`SismosState`)

| Var | Tipo | Default | Descripción |
|---|---|---|---|
| `catalog` | `dict` | `{"type":"FeatureCollection","features":[]}` | histórico recortado |
| `live` | `dict` | idem | feed en vivo recortado a bbox |
| `count`, `count_visible` | `int` | 0 | total / tras filtros (computed) |
| `fetched_at`, `live_fetched_at` | `str` | "" | |
| `error` | `str` | "" | aviso |
| `year` | `int` | año actual | slider temporal |
| `month` | `int` | 12 | selector fino |
| `min_mag` | `float` | 4.0 | slider |
| `depth_band` | `Literal["all","shallow","intermediate","deep"]` | `"all"` | |
| `playing` | `bool` | False | reproducción |
| `show_live`, `show_heat`, `show_faults`, `show_terrain`, `show_notable` | `bool` | F, F, T, F, T | interruptores |
| `selected` | `dict` | `{}` | SeismicFeature seleccionado |
| `hovered_fault` | `str` | "" | |
| `layer_filter` (computed) | `list` | `["all", ["<=",["get","time"], t_ms], [">=",["get","mag"], min_mag], <depth>]` | |
| `time_cutoff_ms` (computed) | `int` | fin del mes/año elegido en UTC | |

Constantes de estilo (en `venezuela_data.py`):

```python
MAG_RADIUS = ["interpolate", ["linear"], ["get", "mag"], 4, 4, 5, 8, 6, 14, 7, 24, 8, 34]
DEPTH_COLOR = ["step", ["get", "depth"], "#ef4444", 70, "#f97316", 300, "#3b82f6"]
DEPTH_BANDS = {"shallow": (0, 70), "intermediate": (70, 300), "deep": (300, 1000)}
NOTABLE_QUAKES = [  # fecha ISO, nombre, mag aprox., lng, lat, fuente
    ("1812-03-26", "Terremoto de Caracas 1812", 7.7, -66.9, 10.5, "FUNVISIS/USGS hist."),
    ("1967-07-29", "Terremoto de Caracas 1967", 6.6, -67.1, 10.6, "USGS"),
    ("1997-07-09", "Terremoto de Cariaco", 6.9, -63.5, 10.6, "USGS"),
    ("2018-08-21", "Sismo de Boca de Uchire / Yaguaraparo", 7.3, -62.9, 10.8, "USGS"),
]
```

## 4. Esquema de fallas (GEM → asset)

```jsonc
{ "type": "Feature", "id": 1234,
  "properties": { "name": "Boconó fault", "slip_type": "Dextral", "average_dip": "(90,,)", "net_slip_rate": "(9,7,11)",
                  "activity_confidence": 1, "catalog_id": "GEM-..." },
  "geometry": { "type": "LineString" | "MultiLineString", "coordinates": [...] } }
```

- Archivo: `mapcn_demo/assets/venezuela_fallas.geojson`, ≤ 300 KB, recorte `[-76, -1, -57, 15]`, simplificación 0.005°.
- Colores por `slip_type`: `Dextral` `#ef4444`, `Sinistral` `#f97316`, `Reverse`/`Thrust` `#a855f7`, `Normal` `#3b82f6`, otros/`null` `#64748b`.
- Licencia CC BY-SA 4.0; atribución obligatoria en panel y README.

## 5. Esquemas de servicios auxiliares

### 5.1 `TravelMatrix` / `TravelRow` (OSRM)

```python
class TravelMatrix(TypedDict):
    origin: tuple[float, float]         # (lng, lat)
    durations: list[float | None]       # segundos, índice = destino
    distances: list[float | None]       # metros
    fetched_at: str
    error: str | None

class TravelRow(TypedDict):             # fila de la tabla UI
    state: str; capital: str; lng: float; lat: float
    duration_s: float | None; distance_m: float | None
    duration_label: str                 # "5h 20m" | "sin ruta"
    distance_label: str                 # "412 km" | "—"
```

Petición: `GET https://router.project-osrm.org/table/v1/driving/{lng,lat};{lng,lat};...?sources=0&annotations=duration,distance`. Respuesta relevante: `{"code": "Ok", "durations": [[...]], "distances": [[...]]}`.

### 5.2 `RainViewerFrames`

```python
class RainViewerFrame(TypedDict): time: int; path: str
class RainViewerFrames(TypedDict): host: str; generated: int; past: list[RainViewerFrame]; nowcast: list[RainViewerFrame]
```
Tiles: `f"{host}{frame['path']}/256/{{z}}/{{x}}/{{y}}/{color}/{1 if smooth else 0}_{1 if snow else 0}.png"`.

### 5.3 Rampa de color por defecto del heatmap

```python
HEATMAP_DEFAULT_COLOR = ["interpolate", ["linear"], ["heatmap-density"],
    0, "rgba(59,130,246,0)", 0.2, "rgb(59,130,246)", 0.4, "rgb(34,197,94)", 0.6, "rgb(250,204,21)", 0.8, "rgb(249,115,22)", 1, "rgb(239,68,68)"]
```

## 6. Caché en memoria (`services/cache.py`)

```python
class TTLCache:            # dict[str, tuple[expires_at: float, value: Any]]; sin límite de tamaño (≤ 50 claves esperadas)
    def get(key) -> Any | None
    def set(key, value, ttl_s: float)
```

| Clave | TTL | Tamaño aprox. |
|---|---|---|
| `usgs:catalog:{min_mag}:{start}:{end}:{bbox}` | 600 s | ≤ 400 KB (340 KB medidos con el defecto M ≥ 4,5) |
| `usgs:live:{days}:{min_mag}:{bbox}` | 60 s | ≤ 50 KB |
| `osrm:table:{profile}:{lng},{lat}` | 3600 s | ≤ 2 KB |
| `rainviewer:frames` | 300 s | ≤ 5 KB |

Proceso único por instancia de backend; no compartido entre workers (aceptable para la demo).

## 7. Relaciones

| Desde | Hacia | Tipo | Nota |
|---|---|---|---|
| `SeismicFeature.id` | `MapCircleLayer promote_id="id"` | 1:1 | hover state y selección |
| `TravelRow.state` | `STATE_INFO` (0.1.0) | N:1 | capital de origen/destino |
| `venezuela_fallas` | `MapLayer` | archivo→capa | URL estática |

## 8. Migración

No hay datos persistentes. Los assets nuevos (`venezuela_fallas.geojson`) se añaden al repo; `scripts/build_faults.py` es idempotente. Rollback = borrar el archivo.

---

## Historial de cambios

| Versión | Fecha | Autor | Cambios |
|---|---|---|---|
| 1.0 | 2026-09-11 | E. Crespo / Claude | Versión inicial (DRAFT) |
| 1.1 | 2026-09-11 | Claude | Analyze A-06: semántica de `hotKeys` |
