# reflex-mapcn 0.2.0 — Technical Design Document

## Metadata

| Campo | Valor |
|---|---|
| **Autor** | Ernesto Crespo / Claude |
| **Estado** | `APPROVED` — aprobado 2026-09-11 (checkpoint 3) |
| **Versión** | 1.0 |
| **Fecha** | 2026-09-11 |
| **PRD** | `docs/specs/prd/mapcn-layers-0.2.md` |
| **API Spec** | `docs/specs/api/mapcn-components-api-v0.2.md` |
| **Reviewers** | Ernesto Crespo |

---

## 1. Contexto

`reflex-mapcn` es un wrapper de dos capas: `mapcn.jsx` (port de mapcn con React + maplibre-gl, cargado como asset compartido) y `mapcn.py` (clases `NoSSRComponent` que declaran props y `EventHandler`s). Reflex compila cada componente Python a `const MapcnX = ClientSide(() => import('$/public/external/reflex_mapcn/mapcn/mapcn.jsx').then(m => m.X))` y pasa las props como JSON. Todos los componentes de capa comparten un patrón: esperar `isLoaded` del contexto del mapa, añadir fuente+capa, sincronizar props en caliente, y limpiar. En 0.1.0 ese patrón está duplicado a mano en `MapRoute`, `MapArc`, `MapGeoJSON` y `MapClusterLayer`.

0.2.0 añade cinco componentes de capa y una demo con backend. La decisión técnica central es **extraer el patrón común a un hook `useMapLayer`** y construir F1–F5 sobre él, en lugar de seguir copiando efectos; los componentes 0.1.0 se dejan intactos (no se refactorizan en este release para no arriesgar regresiones) y se migran en 0.3.

## 2. Objetivos técnicos

- **Correctitud:** ninguna fuente/capa huérfana tras cambio de tema, navegación entre páginas o cambio de props frías (verificado por test JSX con MapLibre simulado que inspecciona `getLayersOrder()` y `_sources`).
- **Rendimiento:** actualización de `filter`/paint sin recrear capas; 10 000 puntos en `circle` a ≥ 30 fps; payload histórico ≤ 400 KB.
- **Mantenibilidad:** un hook para el ciclo de vida; presets en Python; cada componente < 150 líneas de JSX.
- **Operabilidad:** advertencias con prefijo `mapcn:`; helpers de backend con timeouts y caché; sin claves.

## 3. Arquitectura propuesta

### 3.1 Diagrama

```
┌────────────────────────── Reflex app (Python) ──────────────────────────┐
│ mapcn_demo/pages/sismos.py    SismosState (rx.State)                     │
│   ├─ on_load ──▶ services/usgs.fetch_catalog()  ──▶ USGS FDSN (httpx)    │
│   ├─ bg loop ──▶ services/usgs.fetch_live()     ──▶ USGS feeds           │
│   └─ tiempos ──▶ services/osrm.table()/route()  ──▶ OSRM demo server      │
│ reflex_mapcn/                                                            │
│   mapcn.py  (MapRasterLayer, MapLayer, MapHeatmapLayer, MapCircleLayer,  │
│              MapSymbolLayer, MapTerrain + 0.1.0)                         │
│   presets.py (tablas), helpers.py (rainviewer_*, expresiones)            │
└──────────────┬───────────────────────────────────────────────────────────┘
               │ props JSON / eventos JSON (websocket Reflex)
┌──────────────▼──────────────── navegador ────────────────────────────────┐
│ mapcn.jsx                                                                │
│   MapContext {map, isLoaded, resolvedTheme, glyphsUrl}                   │
│   useMapLayer(spec)  ◀── RasterLayer / Layer / HeatmapLayer /            │
│      │                    CircleLayer / SymbolLayer                      │
│      │  addSource/addLayer · setData · setPaint/Layout · setFilter       │
│      │  hover state · click/hover events · teardown                      │
│   MapTerrain ─ setTerrain / hillshade                                    │
│   maplibre-gl ─▶ teselas (OpenFreeMap, RainViewer, OSM overlays, AWS DEM)│
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Componentes

| Componente | Tecnología | Responsabilidad |
|---|---|---|
| `useMapLayer` (JSX) | React hook | Ciclo de vida fuente+capa(s): add cuando `isLoaded`, diff de props calientes/frías, eventos, hover state, cleanup |
| `RasterLayer`, `Layer`, `HeatmapLayer`, `CircleLayer`, `SymbolLayer` (JSX) | React | Traducen props camelCase a `source`/`layer` MapLibre y delegan en `useMapLayer` |
| `MapTerrain` (JSX) | React | Fuente `raster-dem`, `setTerrain`, hillshade opcional, singleton por mapa vía `MapContext.terrainRef` |
| `Map` (JSX, modificado) | React | Añade `glyphsUrl` (inyecta `glyphs` en `blankMapStyle`), `terrainRef`, `elevation` en viewport si hay terreno |
| `mapcn.py` (Python) | Reflex `NoSSRComponent` | Clases + validación en `create()` + aplicación de presets |
| `presets.py`, `helpers.py` (Python) | Python puro | Tablas de presets, `rainviewer_*`, constructores de expresiones |
| `mapcn_demo/services/usgs.py`, `osrm.py` | httpx async + caché TTL en memoria | Clientes de datos externos con timeouts y recorte |
| `scripts/build_faults.py` | Python (json puro; sin GDAL) | Genera `assets/venezuela_fallas.geojson` |
| `mapcn_demo/pages/sismos.py` | Reflex | Página, estado, filtros, línea de tiempo, popups |

### 3.3 Flujo principal: montaje de una capa

```
1. Reflex renderiza <MapcnCircleLayer data=... radius=[...] onClick=fn/> dentro de <MapcnMap>.
2. CircleLayer construye spec = {id, source: {type:"geojson", data, promoteId}, layers: [{id, type:"circle", paint, layout, filter}], interactive, callbacks}.
3. useMapLayer: si !isLoaded → no-op. Si isLoaded → addSource + addLayer(s) con resolveBeforeId; registra click/mousemove/mouseleave si interactive; setReady(true).
4. Cambio de props: efecto de "calientes" compara con ref anterior (JSON.stringify por propiedad) y aplica setData / setPaintProperty / setLayoutProperty / setFilter / setLayerZoomRange.
5. Cambio de "frías" (key derivada de source sin data, tipos, promoteId, cluster*): el efecto principal se re-ejecuta (dependencia = coldKey) → cleanup + re-add.
6. Cambio de tema: Map pone isLoaded=false (style swap) → cleanup del efecto principal; style.load → isLoaded=true → re-add. Idéntico a MapRoute hoy.
7. Desmontaje: cleanup (off listeners → removeLayer(s) → removeSource → removeImage(s)).
```

### 3.4 Flujo de error / degradación

```
- addLayer con beforeId inexistente → resolveBeforeId devuelve undefined → capa al final + warn una vez.
- addSource sobre id existente (StrictMode doble montaje) → guard `if (map.getSource(id)) removeSource` en add; nunca lanzar.
- style mid-reload en cleanup → try/catch alrededor de remove* (patrón 0.1.0).
- loadImage falla → warn `mapcn: image "<k>" failed`, capa se añade sin ese icono.
- symbol text sin glyphs → omitir text-field + warn (REQ-PNT-004).
- Backend USGS/OSRM: timeout 15 s → objeto con `error`; el estado muestra aviso y conserva datos previos.
```

### 3.5 Flujo de la demo Sismos

```
1. on_load(/sismos) → SismosState.load_catalog (background): usgs.fetch_catalog() → recorta propiedades → self.catalog (FeatureCollection ≤ 400 KB), self.count, self.fetched_at.
2. UI: map_circle_layer(data=SismosState.catalog, filter=SismosState.layer_filter, radius=MAG_RADIUS, color=DEPTH_COLOR, promote_id="id", on_click=select_quake).
3. Slider tiempo/magnitud/profundidad → set_* → layer_filter (computed var) = ["all", ["<=",["get","time"],t], [">=",["get","mag"],m], [...depth]] → setFilter en cliente.
4. ▶ reproducir: background event que avanza year cada 200 ms hasta hoy o hasta pausa.
5. "En vivo": background loop cada 60 s → usgs.fetch_live() → self.live (FeatureCollection) → segunda circle layer + capa "pulse" (circle con stroke animado vía circle-radius interpolado por ["-", now, ["get","time"]]? no: MapLibre no anima; se usa 2 capas y toggling de opacidad cada 700 ms desde estado → decidido: anillo estático más grande, sin animación por estado para no saturar websocket).
6. Popup: select_quake recibe LayerFeatureEvent → SismosState.selected → map_popup con formato de fecha en UTC y America/Caracas (zoneinfo).
7. Fallas: map_layer(source={"type":"geojson","data":"/venezuela_fallas.geojson"}, layer={"type":"line", paint: color por slip_type}, interactive=True, on_hover).
8. Relieve: rx.cond(show_terrain, map_terrain(preset="aws_terrarium", hillshade=True, exaggeration=1.3)).
```

## 4. Decisiones de diseño

### DD-001: Hook `useMapLayer` compartido vs. efectos por componente
- **Decisión:** implementar `useMapLayer({ id, source, layers, interactive, hoverPaint, callbacks, beforeId, images })` y construir F1–F5 sobre él.
- **Contexto:** 0.1.0 repite ~80 líneas por capa; cada copia ha tenido bugs sutiles (orden de cleanup, style.load).
- **Alternativas:**

| Opción | Pros | Contras |
|---|---|---|
| **Hook compartido (elegida)** | Un solo lugar para ciclo de vida; tests una vez; componentes finos | Riesgo de abstracción prematura; hay que cubrir raster y geojson |
| Copiar el patrón de `MapGeoJSON` | Cero riesgo para 0.1.0; rápido | Quinta copia del mismo código; deuda |
| Refactorizar también 0.1.0 al hook | Consistencia total | Regresiones en componentes publicados; fuera del alcance 0.2 |

- **Justificación:** cinco componentes nuevos amortizan el hook; 0.1.0 se migra en 0.3 con tests ya existentes.
- **Consecuencias:** `mapcn.jsx` crece con una sección "layer runtime"; los componentes 0.1.0 quedan como están (documentado en el código).

### DD-002: Diff de props calientes vs. frías
- **Decisión:** dos efectos: uno con dependencia `coldKey = JSON.stringify({sourceSansData, layerTypes, promoteId, cluster*})` que hace add/teardown, y otro con dependencias por propiedad que aplica `set*`. Las fuentes `geojson` actualizan `data` con `setData`; las raster con nuevos `tiles` se recrean (MapLibre no permite cambiar `tiles` en caliente de forma fiable en todas las versiones).
- **Alternativas:** siempre recrear (simple, parpadea y pierde estado de hover) vs. diff fino por propiedad (elegida) vs. `setStyle` completo (inaceptable).

### DD-003: Presets en Python, no en JSX
- **Decisión:** `presets.py` con dataclasses; `create()` fusiona preset ⊕ props explícitas.
- **Justificación:** inspeccionables, testeables con pytest, sin lógica de negocio en JS; el JSX recibe siempre `tiles`/`url` finales (Art. 1: el JSX sigue siendo "mapcn + runtime de capas", no un catálogo).

### DD-004: RainViewer requiere backend
- **Decisión:** el preset `rainviewer` no funciona solo: el usuario obtiene frames con `rainviewer_frames()` (Python, httpx) y pasa `tiles=rainviewer_tiles(frame, host)`.
- **Contexto:** los paths de frames caducan; hacer la petición desde el JSX rompería Art. 5 y el modelo "sin fetch en el paquete". Alternativa descartada: fetch en JSX con refresco automático (dependencia de red dentro del componente, imposible de testear sin mocks).

### DD-005: Terreno como singleton por mapa
- **Decisión:** `MapContext` expone `terrainRef`; `MapTerrain` escribe su id al montar, y si otro está activo lo reemplaza con warn. `setTerrain(null)` solo si `terrainRef.current === myId` al desmontar.
- **Justificación:** evita que un desmontaje tardío (StrictMode) borre el terreno del otro.

### DD-006: Filtro temporal en cliente con `setFilter`
- **Decisión:** el histórico completo viaja una vez al cliente; slider y filtros generan `filter` en un computed var; `useMapLayer` aplica `setFilter`.
- **Alternativas:** re-consultar backend por rango (latencia y carga en USGS) vs. filtrar en Python y reenviar la colección (400 KB por tick, inaceptable). Consecuencia: `time` debe viajar como número (ms) en las propiedades.

### DD-007: Recorte de propiedades USGS en backend
- **Decisión:** `usgs.py` conserva `id, mag, magType, depth (=coordinates[2]), time, place, url`; el resto se descarta. Coordenadas a 4 decimales.
- **Justificación:** el GeoJSON crudo del USGS pesa ~4× por metadatos que la demo no usa.

### DD-008: Fallas GEM como asset estático generado por script
- **Decisión:** `scripts/build_faults.py` (json puro + simplificación Douglas-Peucker propia) produce `assets/venezuela_fallas.geojson` versionado.
- **Justificación:** el GeoJSON global pesa decenas de MB y su repo usa LFS; la app no debe descargarlo en runtime. Se cita CC BY-SA 4.0 en panel y README.

### DD-009: Sin animación "pulso" dirigida por estado
- **Decisión:** los sismos < 24 h se muestran con anillo estático (segunda capa `circle` con `stroke` ancho, `opacity` 0.5); la animación CSS no aplica a capas GPU y animar desde estado saturaría el websocket. Alternativa futura: `map_marker` con CSS para los ≤ 10 más recientes.

### DD-010: Glyphs para `symbol` en estilo blank
- **Decisión:** `Map.glyphs_url` (Reflex extra) inyecta `glyphs` en `blankMapStyle`; documentar fuentes OpenFreeMap (`Noto Sans Regular`) y CARTO (`Open Sans Regular`).

## 5. Patrones y convenciones

### 5.1 Estructura del código (0.2.0)

```
custom_components/reflex_mapcn/
├── __init__.py          # re-exporta mapcn + presets + helpers
├── mapcn.py             # componentes 0.1.0 + F1..F5 (clases + create() con validación)
├── presets.py           # RASTER_PRESETS, TERRAIN_PRESETS (dataclasses congeladas)
├── helpers.py           # rainviewer_frames/tiles, interpolate/step/match/zoom_interpolate
├── mapcn.jsx            # + sección "layer runtime": useMapLayer, RasterLayer, Layer, HeatmapLayer, CircleLayer, SymbolLayer, MapTerrain
└── mapcn.css
mapcn_demo/
├── mapcn_demo/services/usgs.py, osrm.py, cache.py
├── mapcn_demo/pages/sismos.py
├── mapcn_demo/venezuela_data.py   (+ NOTABLE_QUAKES, DEPTH_COLORS)
└── assets/venezuela_fallas.geojson
scripts/build_faults.py
tests/
├── test_components.py           (+ tests F1..F5 codegen/validación)
├── test_presets.py, test_helpers.py
├── js/harness/ (stub maplibre, run.mjs)  y js/test_layers.spec.mjs
└── demo/test_usgs_parsing.py, test_osrm_parsing.py (fixtures JSON, sin red)
```

### 5.2 Patrones aplicados

| Patrón | Dónde | Por qué |
|---|---|---|
| Hook de ciclo de vida | `useMapLayer` | Un solo lugar para add/diff/cleanup |
| Ref de callbacks | todos los componentes | Evitar re-suscribir listeners cuando cambia el handler |
| `useStableValue` (JSON key) | props objeto/array | Reflex re-crea objetos en cada render |
| Preset ⊕ override | `create()` Python | Presets inspeccionables y sobrescribibles |
| Caché TTL en memoria | `services/cache.py` | Proteger APIs públicas sin infraestructura extra |
| Resultado con `error` en vez de excepción | servicios demo | El estado siempre puede renderizar |

### 5.3 Manejo de errores

- Python `create()`: `ValueError` con prefijo del componente.
- JSX: `console.warn("mapcn: ...")`; nunca `throw` fuera de `useMap`/`useMarkerContext` (contratos de composición).
- Servicios: `dict` con `error: str | None`; log con `logging.getLogger("mapcn_demo.services")`.

## 6. Seguridad

| Vector | Mitigación |
|---|---|
| URLs de teselas arbitrarias inyectadas desde estado | Solo se pasan a MapLibre (peticiones de imagen); no se interpolan en HTML. Atribución se renderiza por MapLibre (HTML permitido) ⇒ el usuario del paquete controla su origen |
| Expresiones MapLibre desde estado | Son JSON; MapLibre las valida; no hay eval |
| Claves de terceros | Solo por env; `.env.example`; nunca en `assets/` |
| Abuso de APIs públicas por la demo | Caché TTL, límites de destinos, botón bajo demanda, User-Agent identificando la demo |
| Datos sensibles | Ninguno; geolocalización del usuario solo si pulsa "locate" (ya en 0.1.0) |

## 7. Observabilidad

- JSX: advertencias `mapcn:` (tabla en API Spec §6). Modo `debug` (prop `debug=True` en `Map`, COULD) que loguea add/remove de capas.
- Python: `logging` en servicios con duración de la petición y tamaño de respuesta.
- Demo: badge con `fetched_at` y contador de eventos.

## 8. Estrategia de pruebas

| Nivel | Cobertura objetivo | Herramientas | Qué cubre |
|---|---|---|---|
| Unit Python | 100 % de `create()` y presets/helpers | pytest | Validaciones (REQ-LAY-007), presets (REQ-RAS-005, TER-002), expresiones (HEA-003/004), codegen de props/eventos |
| Unit JSX (Chromium) | `useMapLayer` + 5 componentes + terrain | Playwright + stub maplibre (`tests/js/harness`) | Add/diff/cleanup, style.load re-add (REQ-*-008/009), eventos y payloads (LAY-006), glyphs warn (PNT-004), terrain singleton (TER-007) |
| Servicios demo | Parsing y errores | pytest + fixtures JSON + `respx`/mock de httpx | REQ-SIS-002/003, TVJ-002 |
| Integración demo | Compila | `compile_check` (reflex desde fuente) o `reflex export --frontend-only` | Todas las páginas compilan |
| Rendimiento | Manual con perfilador | Chromium DevTools | REQ-PNT-007 (10 000 puntos) |
| E2E | Manual antes de release | `reflex run` + checklist | Páginas /sismos y /venezuela |

## 9. Plan de migración / rollout

- Aditivo: 0.1.0 → 0.2.0 sin cambios de firma. `Map` gana `glyphs_url` (opcional).
- Feature flag no necesario; los componentes nuevos solo cargan si se usan.
- Rollback: fijar `reflex-mapcn==0.1.0`.

## 10. Preguntas abiertas

- [ ] ¿Migrar `MapGeoJSON`/`MapArc`/`MapRoute` a `useMapLayer` en 0.3? — Owner: E. Crespo — tras 0.2.0.
- [ ] ¿Usar `text-font` por defecto según estilo detectado (Carto vs OpenFreeMap)? — decidir en Fase 2 (hoy default `Noto Sans Regular`).
- [ ] ¿Incluir `map_vector_layer` como azúcar sobre `map_layer` en 0.2.0 si sobra tiempo? — COULD.

---

## Constitution check

Art. 1 (extras marcados), Art. 2 (payload LayerFeatureEvent), Art. 3 (sin npm nuevo), Art. 4 (`useMapLayer` con cleanup determinista y re-add tras style.load), Art. 5 (fetch solo en backend/helpers con timeout; presets sin red), Art. 6 (matriz de tests por REQ en §8). Sin excepciones solicitadas.

## Historial de cambios

| Versión | Fecha | Autor | Cambios |
|---|---|---|---|
| 1.0 | 2026-09-11 | E. Crespo / Claude | Versión inicial (DRAFT) |
