# Tasks — reflex-mapcn 0.2.0 (capas avanzadas + demo Sismos)

> Specs de origen: PRD `docs/specs/prd/mapcn-layers-0.2.md` · API `docs/specs/api/mapcn-components-api-v0.2.md` · Tech `docs/specs/technical/mapcn-layers-architecture.md` · Data `docs/specs/data-model/mapcn-layers-schema.md` · Plan `docs/specs/plans/mapcn-0.2-implementation-plan.md`
> Fases que cubre: 1–4 · Generado: 2026-09-11 · Estado global: `APPROVED` — en ejecución desde 2026-09-11

## Convenciones

- Orden = orden de ejecución salvo `[P]` (paralelizable: sin dependencias ni archivos en común).
- Estados: `[ ]` pendiente · `[~]` en curso · `[x] {fecha}` hecha · `[!]` bloqueada (nota).
- **Primera tanda supervisada:** T-001, T-002, T-003, T-004, T-005. Revisar salida de tests antes de continuar.
- Todo test cita su REQ en el nombre: `test_REQ_RAS_001_adds_raster_source_and_layer`.

## Tareas

### Fase 1 — Runtime y harness

### T-001 · Versionar harness JSX `[P]` — `[x] 2026-09-11`
- **Qué:** mover el harness de pruebas (stub de `maplibre-gl`, `run.mjs` con Playwright, bundler con bun) a `tests/js/harness/`; añadir script `tests/js/run.sh` que bundlea `mapcn.jsx` + entry de prueba y ejecuta en Chromium; documentar en `tests/js/README.md`.
- **REQ:** transversal (Art. 6)
- **Archivos:** `tests/js/harness/maplibre-stub.js`, `tests/js/harness/run.mjs`, `tests/js/run.sh`, `tests/js/README.md`
- **Depende de:** —
- **Done:** `bash tests/js/run.sh` ejecuta los smoke tests 0.1.0 existentes y termina con `ERRORS: none`.

### T-002 · Crear `CHANGELOG.md` `[P]` — `[x] 2026-09-11`
- **Qué:** Keep a Changelog con `## [0.1.0]` (contenido actual) y `## [Unreleased]`.
- **REQ:** Art. 7
- **Archivos:** `CHANGELOG.md`
- **Done:** archivo existe; enlace desde README.

### T-003 · Implementar `useMapLayer` — `[x] 2026-09-11`
- **Qué:** hook en `mapcn.jsx` con la firma de Data Model §2.1: add cuando `isLoaded`; diff caliente (`setData`, `setPaintProperty`, `setLayoutProperty`, `setFilter`, `setLayerZoomRange`, `moveLayer`); recreación por `coldKey`; `interactive` con cursor, `feature-state.hover`, `onClick`/`onHover` con `LayerFeatureEvent` (usa `serializeFeature`); `images` con `loadImage/addImage/removeImage`; `resolveBeforeId` con warn una vez; cleanup en orden inverso con try/catch.
- **REQ:** REQ-LAY-001, 003, 004, 005, 006, 008, 009; REQ-RAS-002, 003, 008, 009; REQ-PNT-003, 006, 009; REQ-HEA-005, 006
- **Archivos:** `custom_components/reflex_mapcn/mapcn.jsx` (sección "Layer runtime")
- **Depende de:** T-001
- **Done:** `bun build` sin errores; T-004 en verde.

### T-004 · Tests JSX de `useMapLayer` — `[x] 2026-09-11` (escritos antes que T-003, TDD)
- **Qué:** `tests/js/test_layer_runtime.mjs`: monta una capa circle de prueba y verifica add (ids), `setData`, `setPaintProperty` tras cambio de prop, `setFilter`, `beforeId` inexistente (warn + capa al final), re-add tras `style.load`, payload de `onClick`/`onHover` (serializable, `null` al salir), cleanup total al desmontar (sin capas/fuentes/listeners).
- **REQ:** los de T-003
- **Depende de:** T-003
- **Done:** `bash tests/js/run.sh` → `ERRORS: none` y todas las aserciones `PASS`.

### T-005 · Presets y helpers Python `[P]` — `[x] 2026-09-11`
- **Qué:** `presets.py` con `RasterPreset`, `TerrainPreset`, `RASTER_PRESETS` (openrailwaymap, openseamap, esri_satellite, rainviewer) y `TERRAIN_PRESETS` (aws_terrarium) según API §3.7; `helpers.py` con `interpolate`, `step`, `match`, `zoom_interpolate`; tests.
- **REQ:** REQ-RAS-005, REQ-TER-002, REQ-HEA-003 (helper)
- **Archivos:** `custom_components/reflex_mapcn/presets.py`, `helpers.py`, `tests/test_presets.py`, `tests/test_helpers.py`
- **Done:** `pytest tests/test_presets.py tests/test_helpers.py` en verde.

### Fase 2 — Componentes

### T-006 · `map_raster_layer` — `[x] 2026-09-11`
- **Qué:** `RasterLayer` en JSX (source raster; paint `raster-*`; layout visibility; zoom range) sobre `useMapLayer`; clase `MapRasterLayer` con validación "uno de preset/tiles/url", fusión preset ⊕ props, `on_load_error` (COULD) con throttle 60 s.
- **REQ:** REQ-RAS-001, 002, 003, 004, 005, 008, 009, 010, 011
- **Archivos:** `mapcn.jsx`, `mapcn.py`, `tests/test_components.py`, `tests/js/test_raster.mjs`
- **Depende de:** T-003, T-005
- **Done:** tests Python (validación, preset merge, codegen `tiles`/`rasterOpacity`) y JSX (add, opacity caliente, tiles fría recrea, style.load) en verde.

### T-007 · Helper RainViewer `[P]` — `[x] 2026-09-11`
- **Qué:** `rainviewer_frames(timeout=10)` con httpx (sync) y `rainviewer_tiles(frame, host, size, color, smooth, snow)`; timeout/JSON inválido ⇒ frames vacíos + `logging.warning`.
- **REQ:** REQ-RAS-006, REQ-RAS-007
- **Archivos:** `helpers.py`, `tests/test_helpers.py` (mock httpx)
- **Depende de:** T-005
- **Done:** tests de éxito, timeout y JSON inválido en verde; ejemplo en README.

### T-008 · `map_layer` genérico — `[x] 2026-09-11`
- **Qué:** `Layer` en JSX (source dict o id; layer spec con `type`; inyección de `source`/`id`; id de fuente inexistente ⇒ omitir + warn + reintento tras style.load) sobre `useMapLayer`; `MapLayer` Python con `ValueError` si falta `layer.type` o `source` inválido; `interactive`, `hover_paint`, eventos.
- **REQ:** REQ-LAY-001..010
- **Archivos:** `mapcn.jsx`, `mapcn.py`, `tests/test_components.py`, `tests/js/test_layer.mjs`
- **Depende de:** T-003
- **Done:** test Python `test_REQ_LAY_007_raises_on_missing_type`; JSX: fuente por id existente añade solo capa; `fill-extrusion` sobre `source-layer` compila.

### T-009 · `map_heatmap_layer` — `[x] 2026-09-11`
- **Qué:** `HeatmapLayer` JSX (defaults de intensity/radius/color) y `MapHeatmapLayer` con `weight_property`+`weight_range` ⇒ expresión, `max_zoom_fade` ⇒ opacidad interpolada.
- **REQ:** REQ-HEA-001..006
- **Depende de:** T-008
- **Done:** test Python de las expresiones generadas; JSX add/update/cleanup.

### T-010 · `map_circle_layer` — `[x] 2026-09-11` (benchmark pendiente de T-020)
- **Qué:** `CircleLayer` JSX (paint `circle-*`, `filter`, zoom range, `cluster*` en fuente) y `MapCircleLayer`; hover_paint; eventos.
- **REQ:** REQ-PNT-001, 006, 007, 008, 009
- **Depende de:** T-008
- **Done:** tests; benchmark manual 10k puntos anotado en el registro de ejecución (fps observados).

### T-011 · `map_symbol_layer` + `Map.glyphs_url` — `[x] 2026-09-11`
- **Qué:** `SymbolLayer` JSX (layout/paint `icon-*`/`text-*`, `images` con tolerancia a fallo de carga), detección de glyphs (`map.getStyle().glyphs`) ⇒ omitir `text-field` + warn; `Map` acepta `glyphsUrl` y lo inyecta en `blankMapStyle`; `MapSymbolLayer` Python.
- **REQ:** REQ-PNT-002, 003, 004, 005, 006, 009, 010
- **Depende de:** T-010
- **Done:** JSX: con estilo sin glyphs y `textField` ⇒ warn y capa sin texto; con `glyphsUrl` ⇒ `text-field` presente; imágenes añadidas y retiradas.

### T-012 · `map_terrain` — `[x] 2026-09-11`
- **Qué:** `MapTerrain` JSX (source raster-dem, `setTerrain`, hillshade opcional, singleton vía `terrainRef` en contexto, restore tras style.load, `setTerrain(null)` en cleanup si sigue siendo el activo); `Map` añade `elevation` al viewport si hay terreno (COULD); `MapTerrain` Python con preset.
- **REQ:** REQ-TER-001..009
- **Depende de:** T-003, T-005
- **Done:** JSX: `setTerrain` llamado con `{source, exaggeration}`; cambio de `exaggeration` no recrea fuente; segundo terrain reemplaza con warn; desmontaje ⇒ `setTerrain(null)`.

### T-013 · Exportaciones, `.pyi`, README de componentes — `[x] 2026-09-11`
- **Qué:** actualizar `__init__.py`, `MapcnNamespace`, `__all__`; `uv run reflex component build`; README: tabla de componentes nuevos, presets con licencias/atribuciones, recetas (tráfico TomTom vía tiles, edificios 3D, radar).
- **REQ:** Art. 1, Art. 7
- **Depende de:** T-006..T-012
- **Done:** `.pyi` generados sin error; `pytest tests` en verde; README revisado.

### Fase 3 — Demo

### T-014 · Servicios USGS + caché `[P]` — `[x] 2026-09-11`
- **Qué:** `services/cache.py` (TTLCache), `services/usgs.py` (`fetch_catalog`, `fetch_live` (FDSN con bbox, `minmagnitude=2.5`, últimos 30 días), recorte a `SeismicFeature`, `recent`, descartes por `mag` null), fixtures `tests/demo/fixtures/usgs_sample.json`; tests de parsing, caché (TTL), timeout y status ≠ 200 (mock httpx).
- **REQ:** REQ-SIS-001 (parte backend), 002, 003
- **Archivos:** `mapcn_demo/mapcn_demo/services/{__init__,cache,usgs}.py`, `tests/demo/test_usgs.py`
- **Done:** pytest en verde; tamaño de salida con fixture real ≤ 25 % del original.

### T-015 · Script de fallas GEM + asset `[P]` — `[x] 2026-09-11`
- **Qué:** `scripts/build_faults.py` (descarga, recorte a bbox ampliada, simplificación, propiedades mínimas) y ejecutar una vez en máquina con red; commitear `mapcn_demo/assets/venezuela_fallas.geojson`; atribución en `venezuela_data.py`.
- **REQ:** REQ-SIS-009, REQ-SIS-012
- **Done:** archivo ≤ 300 KB, ≥ 30 features, `python -c "import json; json.load(open(...))"` OK.

### T-016 · Página `/sismos` (núcleo) — `[x] 2026-09-11`
- **Qué:** `pages/sismos.py`: `SismosState` (vars del Data Model §3.4, `layer_filter` computed, `load_catalog` background, `select_quake`, `play/pause` con avance anual), `map_circle_layer` con `MAG_RADIUS`/`DEPTH_COLOR`/`promote_id="id"`, sliders (año, mes fino, magnitud), selector de profundidad, popup con UTC + America/Caracas, leyenda, notables (`map_marker`), contador y `fetched_at`, aviso de error, atribuciones; entrada en `layout.NAV`.
- **REQ:** REQ-SIS-001, 004, 005, 006, 011, 012
- **Depende de:** T-010, T-014
- **Done:** `compile_check` OK; en `reflex run` se ven ≥ 1 000 sismos, el slider filtra sin peticiones (verificar en Network), popup correcto.

### T-017 · `/sismos` capas opcionales — `[x] 2026-09-11`
- **Qué:** interruptores En vivo (background loop 60 s con `fetch_live` vía FDSN bbox/M≥2.5/30 días, capa recientes con anillo), Densidad (`map_heatmap_layer` con `weight_property="mag"`, `max_zoom_fade=8`), Fallas (`map_layer` line coloreada por `slip_type`, hover tooltip), Relieve (`map_terrain` preset `aws_terrarium`, hillshade).
- **REQ:** REQ-SIS-007, 008, 009, 010
- **Depende de:** T-016, T-009, T-008, T-012, T-015
- **Done:** cada interruptor añade/quita su capa sin errores en consola; cambio de tema con todas activas no deja capas huérfanas (inspeccionar `map.getLayersOrder()` desde DevTools).

### T-018 · OSRM + Tiempos de viaje en `/venezuela` `[P]` (respecto a T-016) — `[x] 2026-09-12`
- **Qué:** `services/osrm.py` (`table` máx. 25 destinos, `route`, caché 1 h, `error`), tests con fixtures; en `VenezuelaState`: `load_travel_times` (background), `travel_rows` (ordenadas), `select_travel_row` ⇒ `map_route` + `fitBounds`; UI: botón "Tiempos de viaje" (habilitado con estado seleccionado), tabla lateral, "sin ruta" para nulos.
- **REQ:** REQ-TVJ-001..004
- **Archivos:** `services/osrm.py`, `pages/venezuela.py`, `tests/demo/test_osrm.py`
- **Done:** pytest en verde; en la app, desde "Distrito Capital" aparecen 22 filas y al pulsar una se dibuja la ruta.
- **Notas de revisión (2026-09-12):**
  - `TravelRow` se implementa como dataclass y no como el `TypedDict` del Data Model §5.1: los campos son los de la spec, pero `rx.foreach` sobre una lista de dataclasses es el patrón que ya usa `/routes`. No se abre Delta porque el contrato de campos no cambia.
  - La clave de caché de la matriz añade un digest de los destinos al par `(perfil, origen)` que documenta el Data Model §6, para que un segundo cálculo desde la misma capital hacia otra lista de destinos no lea tiempos ajenos. La clave sigue siendo interna y el TTL de 1 h de REQ-TVJ-004 no cambia.
  - Un estado insular puede ser origen: la matriz vuelve llena de huecos y cada fila dice "sin ruta" (REQ-TVJ-002), en vez de ocultar el panel.
  - Verificado contra el servidor real de OSRM el 2026-09-12: 22 filas desde Caracas, sin error, y ruta de 577 puntos a La Guaira. Falta solo la comprobación visual en el navegador, que entra en T-020.

### T-019 · Docs de la demo y compile_check global — `[x] 2026-09-12`
- **Qué:** README de la demo (páginas, fuentes de datos, licencias), `.env.example` (variables opcionales: `TOMTOM_API_KEY`, `OPENWEATHER_API_KEY` para recetas), `compile_check` de todas las páginas.
- **REQ:** Art. 5, Art. 7
- **Depende de:** T-016..T-018
- **Done:** `COMPILE OK`; README actualizado.
- **Notas de revisión (2026-09-12):**
  - El `compile_check` se implementa como `scripts/compile_check.py`: lee las rutas del registro de Reflex (`RegistrationContext`, que sustituye al `DECORATED_PAGES` obsoleto desde 0.9.9) y construye cada una. Imprime `COMPILE OK: 11 pages` y devuelve 1 nombrando la página rota. `tests/demo/test_compile.py` lo ejecuta, así que la puerta corre también en CI dentro de pytest, sin necesidad de `reflex export`.
  - El README de la demo documenta las once páginas, dónde vive cada cosa y la licencia de cada fuente; el README raíz ahora apunta a él y menciona `/sismos` y los tiempos de viaje, que faltaban desde T-016.
  - Dos afirmaciones se corrigieron tras comprobarlas: `OPENWEATHER_API_KEY` no alimenta ninguna receta escrita (solo `TOMTOM_API_KEY`), y el feed de sismos de la documentación de MapLibre es dato del USGS en dominio público, no BSD.
  - Hallazgo fuera de tarea: `ruff format --check .` falla en cuatro archivos anteriores a T-018 (`presets.py`, `pages/sismos.py`, `tests/test_components.py`, `tests/test_helpers.py`), así que el trabajo de lint de CI viene en rojo desde T-005. No se toca aquí para no mezclarlo con la tarea; pendiente de decisión.

### T-023 · Página de capas raster y símbolos en la demo `[P]` — `[x] 2026-09-12`
- **Qué:** página `/raster` con un selector de fuente de datos y una capa `map_raster_layer` que se reconstruye al cambiarla: los tres presets sin clave (`openrailwaymap`, `openseamap`, `esri_satellite`), el radar de RainViewer vía `rainviewer_frames`/`rainviewer_tiles`, y el tráfico de TomTom y dos capas de OpenWeather detrás de sus variables de entorno, con aviso en lugar de capa cuando la clave falta. Controles de opacidad y visibilidad para ejercitar la actualización en caliente. Segunda sección con `map_symbol_layer` (iconos desde `images` + etiquetas de texto) y un interruptor de basemap transparente con `glyphs_url`. Lector de `.env` propio en la demo (sin dependencias nuevas) para que las claves lleguen a `os.environ`.
- **Por qué:** hallazgo de la revisión T-020: de los seis componentes de 0.2 la demo solo ejercitaba cuatro. `map_raster_layer` y `map_symbol_layer` no aparecían en ninguna página, ni el radar, ni las claves que declara `.env.example`.
- **REQ:** cobertura de demo de REQ-RAS-001..005, 008, 009 (capa raster), REQ-RAS-006, 007 (RainViewer), REQ-PNT-002, 003, 004, 005, 010 (símbolos); Art. 5
- **Archivos:** `mapcn_demo/mapcn_demo/pages/raster.py`, `services/env.py`, `mapcn_demo/assets/`, `layout.NAV`, `mapcn_demo/README.md`, `tests/demo/test_raster_page.py`
- **Depende de:** T-019
- **Done:** `COMPILE OK` con 12 páginas; pytest en verde; en `reflex run` cada fuente dibuja su capa y las que piden clave avisan cuando no está; el README de la demo vuelve a ser cierto cuando dice que ejercita todos los componentes.
- **Notas de revisión (2026-09-12):**
  - Cada fuente declara la vista en la que se ve algo y el selector mueve la cámara al elegirla. Sin eso, el tráfico a escala de país dibujaba una capa vacía y parecía roto.
  - **TomTom no cubre Venezuela.** Medido: una tesela de flujo z13 sobre Caracas pesa 1,2 KB (imagen vacía) y la misma sobre Bogotá 48 KB, con la clave del usuario y respuesta 200 en ambos casos. La capa de tráfico se muestra sobre Bogotá y la descripción lo dice. El test lo deja anotado con la medición.
  - Se usa el estilo `absolute` y no el `relative0` de la receta del README: `relative0` solo pinta lo que va más lento que el flujo libre, así que en horas tranquilas la capa parece apagada.
  - El lector de `.env` es propio (12 líneas) en vez de añadir `python-dotenv`: Reflex solo carga un dotenv si se configura `env_file` y esa dependencia no está instalada. Lo exportado en el shell gana sobre el archivo.
  - Verificado en el navegador con las claves reales del usuario: railway, radar de RainViewer, tráfico de Bogotá, nubosidad de OpenWeather e iconos con etiquetas. Sin errores en consola.

### Fase 4 — Hardening y release

### T-020 · Revisión E2E manual
- **Qué:** ejecutar checklist: claro/oscuro con todas las capas; cambiar estilo base con capas activas; navegar entre las 11 páginas y volver (sin errores `already exists`); `blank=True` + symbol con/sin `glyphs_url`; 10k puntos (fps); tamaño del histórico en Network.
- **REQ:** REQ-*-008/009, REQ-PNT-004/007, RNF rendimiento
- **Depende de:** T-019
- **Done:** checklist rellenado en el registro de ejecución con resultados y capturas.
- **Hallazgos de la revisión (en curso):**
  - **H-01 (2026-09-12, corregido):** `/sismos` no mostraba el mapa. El contenedor medía 0 px de alto, sin errores en consola. Causa: `mapcn.css` fijaba `height: 100%` en `.mapcn-map`, misma especificidad que la clase en la que Reflex compila un `height=`, y ganaba la hoja del paquete; la página es la única que da el alto al mapa en vez de a un contenedor padre. El defecto venía de 0.1.0 y solo se ve cuando el padre no tiene alto propio. Arreglado moviendo el tamaño por defecto a una regla `:where(.mapcn-map)`, que no pesa nada, con dos tests nuevos en Chromium (`tests/js/tests/map_size.test.mjs`) que miden el alto computado con la regla del autor insertada antes que la del paquete. Verificado en la app: 3555 sismos dibujados.
  - **H-02 (2026-09-12, pendiente de decisión):** `uv run reflex run` sincroniza el entorno sin el extra `dev` y deja el `.venv` sin pytest ni ruff. Conviene documentar `uv run --extra dev reflex run`, o arrancar la demo desde su propio entorno.

### T-021 · Plegar specs y CHANGELOG 0.2.0
- **Qué:** marcar PRD/API/Tech/Data/Plan como `APPROVED` + nota `IMPLEMENTED 0.2.0`; anotar desviaciones como Delta si las hubo; CHANGELOG `## [0.2.0]`.
- **REQ:** Art. 8
- **Depende de:** T-020
- **Done:** `git diff docs/` muestra estados actualizados; sin TODOs abiertos en Tasks.

### T-022 · Release 0.2.0
- **Qué:** `python scripts/bump_version.py . minor` (skill), `uv run reflex component build`, verificar wheel (jsx/css/pyi/presets/helpers), `uv publish` (con confirmación humana), tag `v0.2.0`, `reflex component share` con captura de `/sismos`.
- **REQ:** Art. 7
- **Depende de:** T-021
- **Done:** `pip install reflex-mapcn==0.2.0` en venv limpio importa `reflex_mapcn.map_terrain`.

## Matriz de trazabilidad

| REQ | Tareas | Tests que lo citan (planificados) |
|---|---|---|
| REQ-RAS-001 | T-003, T-006 | `test_REQ_RAS_001_adds_raster_source_and_layer` (js) |
| REQ-RAS-002 | T-003, T-006 | `test_REQ_RAS_002_opacity_visible_zoom_hot_update` (js) |
| REQ-RAS-003 | T-003, T-006 | `test_REQ_RAS_003_tiles_change_recreates_source` (js) |
| REQ-RAS-004 | T-006 | `test_REQ_RAS_004_tile_size_scheme_attribution_props` (py) |
| REQ-RAS-005 | T-005, T-006 | `test_REQ_RAS_005_preset_merge_and_override` (py) |
| REQ-RAS-006 | T-007 | `test_REQ_RAS_006_rainviewer_frames_and_tiles` (py) |
| REQ-RAS-007 | T-007 | `test_REQ_RAS_007_rainviewer_timeout_returns_empty` (py) |
| REQ-RAS-008 | T-003, T-006 | `test_REQ_RAS_008_readd_after_style_load` (js) |
| REQ-RAS-009 | T-003, T-006 | `test_REQ_RAS_009_unmount_cleans_up` (js) |
| REQ-RAS-010 (SHOULD) | T-006 | manual (T-020) |
| REQ-RAS-011 (COULD) | T-006 | `test_REQ_RAS_011_on_load_error_throttled` (js) |
| REQ-LAY-001 | T-003, T-008 | `test_REQ_LAY_001_injects_source_and_id` (js) |
| REQ-LAY-002 | T-008 | `test_REQ_LAY_002_existing_source_id_adds_layer_only` (js) |
| REQ-LAY-003 | T-003 | `test_REQ_LAY_003_setdata_on_data_change` (js) |
| REQ-LAY-004 | T-003 | `test_REQ_LAY_004_paint_layout_filter_hot` (js) |
| REQ-LAY-005 | T-003 | `test_REQ_LAY_005_cold_change_recreates` (js) |
| REQ-LAY-006 | T-003, T-008 | `test_REQ_LAY_006_click_hover_payload` (js) |
| REQ-LAY-007 | T-008 | `test_REQ_LAY_007_raises_on_missing_type` (py) |
| REQ-LAY-008 | T-003 | `test_REQ_LAY_008_missing_before_id_appends` (js) |
| REQ-LAY-009 | T-003 | cubierto por RAS-008/009 (js) |
| REQ-LAY-010 | T-008 | `test_REQ_LAY_010_missing_source_id_warns_and_retries` (js) |
| REQ-HEA-001, REQ-HEA-005, REQ-HEA-006 | T-009 | `test_REQ_HEA_001_heatmap_layer` (js) |
| REQ-HEA-002 | T-009 | `test_REQ_HEA_002_prop_mapping` (py) |
| REQ-HEA-003 (SHOULD) | T-009 | `test_REQ_HEA_003_weight_property_expression` (py) |
| REQ-HEA-004 (SHOULD) | T-009 | `test_REQ_HEA_004_max_zoom_fade` (py) |
| REQ-HEA-007 (Delta 2026-09) | T-009, T-017 | `test_REQ_HEA_007_filter_prop_reaches_the_layer` (py), `REQ-HEA-007: a new filter is applied without a rebuild` (js) |
| REQ-PNT-001 | T-010 | `test_REQ_PNT_001_circle_layer_props` (py+js) |
| REQ-PNT-002 | T-011 | `test_REQ_PNT_002_symbol_layer_props` (py+js) |
| REQ-PNT-003 | T-003, T-011 | `test_REQ_PNT_003_images_loaded_and_removed` (js) |
| REQ-PNT-004 | T-011 | `test_REQ_PNT_004_symbol_text_without_glyphs_warns` (js) |
| REQ-PNT-005 (SHOULD) | T-011 | `test_REQ_PNT_005_glyphs_url_injected_in_blank_style` (js) |
| REQ-PNT-006 | T-003, T-010 | `test_REQ_PNT_006_hover_paint_and_events` (js) |
| REQ-PNT-007 (SHOULD) | T-010, T-020 | manual (fps registrado) |
| REQ-PNT-008 (COULD) | T-010 | `test_REQ_PNT_008_cluster_source_options` (js) |
| REQ-PNT-009 | T-003 | cubierto por LAY-003/004, RAS-008/009 |
| REQ-PNT-010 | T-003, T-011 | `test_REQ_PNT_010_image_load_failure_is_tolerated` (js) |
| REQ-TER-001 | T-012 | `test_REQ_TER_001_sets_terrain` (js) |
| REQ-TER-002 | T-005, T-012 | `test_REQ_TER_002_aws_preset` (py) |
| REQ-TER-003 | T-012 | `test_REQ_TER_003_hillshade_layer` (js) |
| REQ-TER-004 | T-012 | `test_REQ_TER_004_exaggeration_hot` (js) |
| REQ-TER-005 | T-012 | `test_REQ_TER_005_unmount_clears_terrain` (js) |
| REQ-TER-006 | T-012 | `test_REQ_TER_006_restore_after_style_load` (js) |
| REQ-TER-007 | T-012 | `test_REQ_TER_007_singleton_warns` (js) |
| REQ-TER-008 (COULD) | T-012 | `test_REQ_TER_008_elevation_in_viewport` (js) |
| REQ-TER-009 (SHOULD) | T-012 | manual (T-020) + `test_REQ_TER_009_on_load_error` (js) |
| REQ-SIS-001 | T-014, T-016 | `test_REQ_SIS_001_catalog_query_and_trim` (py) + manual |
| REQ-SIS-002 | T-014 | `test_REQ_SIS_002_cache_ttl` (py) |
| REQ-SIS-003 | T-014, T-016 | `test_REQ_SIS_003_timeout_keeps_cache` (py) |
| REQ-SIS-004, REQ-SIS-005 | T-016 | `test_REQ_SIS_004_layer_filter_expression`, `test_REQ_SIS_005_combined_filters` (py: computed var) + manual |
| REQ-SIS-006 | T-016 | `test_REQ_SIS_006_popup_time_formats` (py) |
| REQ-SIS-007 | T-014, T-017 | `test_REQ_SIS_007_live_bbox_and_recent` (py) + manual |
| REQ-SIS-008, REQ-SIS-010 (SHOULD) | T-017 | manual (T-020) |
| REQ-SIS-009 | T-015, T-017 | `test_REQ_SIS_009_faults_asset_valid` (py) + manual |
| REQ-SIS-011 (SHOULD) | T-016 | `test_REQ_SIS_011_notable_quakes_list` (py) |
| REQ-SIS-012 | T-015, T-016 | manual |
| REQ-TVJ-001 | T-018 | `test_REQ_TVJ_001_table_request_and_rows` (py) |
| REQ-TVJ-002 | T-018 | `test_REQ_TVJ_002_null_cells_and_errors` (py) |
| REQ-TVJ-003 (SHOULD) | T-018 | manual |
| REQ-TVJ-004 | T-018 | `test_REQ_TVJ_004_cache_1h` (py) |

SHOULD/COULD sin tarea propia: ninguno (todos asignados; los COULD pueden diferirse en el Analyze/implementación sin abrir Delta).

## Registro de ejecución

| Fecha | Tareas | Resultado | Notas |
|---|---|---|---|
| 2026-09-12 | T-023 | OK | TDD: 26 tests escritos antes del código (lector de `.env`, registro de fuentes, plantillas con clave, radar, datos de símbolos, vistas por fuente). El test de documentación de T-019 hizo su trabajo solo: falló en cuanto la página entró en el menú y el README no la nombraba. Dos hallazgos medidos durante la verificación en el navegador, no supuestos: TomTom no tiene datos sobre Venezuela y el estilo `relative0` no pinta casi nada fuera de hora punta. La demo ya ejercita los seis componentes de 0.2. 196 tests Python, 59 JSX, `COMPILE OK: 12 pages`. |
| 2026-09-12 | T-019 | OK | TDD también para las docs: 13 tests escritos antes (cinco del compile_check, ocho del README y del `.env.example`), que fallaron por script y archivos inexistentes. El compile_check construye las once páginas y nombra la que rompe; un test lo comprueba con una página rota de mentira, para que el informe valga algo. Tres afirmaciones del README se corrigieron al verificarlas contra el código en vez de darlas por buenas. 169 tests Python en verde y `COMPILE OK: 11 pages`. Queda anotado que `ruff format --check` viene fallando en cuatro archivos previos. |
| 2026-09-12 | T-018 | OK | TDD: 17 tests del cliente OSRM y 22 de la página, escritos antes del código, con dos respuestas reales guardadas como fixtures y sin red. Dos decisiones de implementación: `TravelRow` es un dataclass y no un `TypedDict`, porque `rx.foreach` sobre una lista de dataclasses es el patrón que ya usa `/routes` y el Data Model solo fija los campos; y la clave de caché de la matriz añade un digest de los destinos al `(perfil, origen)` de la spec, para que un segundo cálculo desde la misma capital hacia otra lista no lea tiempos ajenos. Un estado insular sí puede ser origen: la matriz vuelve llena de huecos y cada fila dice "sin ruta", que es justo lo que pide REQ-TVJ-002. Mutación de tres puntos (columna del origen, tamaño del lote, orden de las filas) para comprobar que los tests discriminan: los tres fallaron. 155 tests Python en verde; ruff y compileall también. Falta el benchmark de red real, que se verá en T-020. |
| 2026-09-11 | Delta 2026-09-heatmap-filter, T-017 | OK | El Delta del filtro en el mapa de calor se aprobó (opción A), se implementó y se plegó a PRD (REQ-HEA-007) y API Spec §3.3. Después T-017: los cuatro interruptores. En vivo con bucle de 60 s y capa de anillo estático para las últimas 24 h (sin animación por estado, DD-009). Densidad con peso por magnitud y desvanecido en zoom 8, ya filtrada. Fallas desde el asset con color por tipo de desplazamiento y tooltip en hover. Relieve con el preset de AWS y sombreado. 6 tests nuevos; 116 tests Python y 57 JSX en verde; las 11 páginas renderizan. |
| 2026-09-11 | T-016 | OK | TDD: 14 tests sobre funciones puras, porque un estado de Reflex no se puede instanciar fuera de la app; la lógica vive en funciones de módulo y el estado solo delega. Dos fallos reales encontrados por los tests: faltaba el manejador del interruptor de notables (Reflex ya no genera `set_*` implícitos) y el selector de profundidad devolvía la etiqueta en español en vez de la clave, con lo que la cláusula de profundidad nunca habría casado. Se añadió la nota de cobertura del catálogo (hallazgo A-12 del Analyze). Las 11 páginas de la demo renderizan sin error. 109 tests Python en verde. |
| 2026-09-11 | T-015 | OK | TDD: 13 tests, primero las funciones puras con geometría sintética. La primera versión filtraba fallas pero no recortaba geometrías, y el test del asset lo detectó: una falla llegaba a 19,7° N. Se añadió `clip_line`, que parte la línea en tramos dentro de la caja y conserva el vértice de cruce para que la línea llegue al borde. Descargado el catálogo GEM (10,6 MB) y generado `mapcn_demo/assets/venezuela_fallas.geojson`: 255 fallas, 86 KB, muy por debajo del presupuesto de 300 KB. Atribución CC BY-SA 4.0 y colores por tipo de desplazamiento en `venezuela_data.py`. 95 tests Python y 56 JSX en verde. |
| 2026-09-11 | T-014 | OK | TDD: 13 tests con una respuesta real del USGS guardada como fixture y sin red. Recorte a 8 propiedades: 33 % del tamaño original con la fixture (medido, no estimado). Caché con reloj inyectable para probar la expiración sin dormir. El camino degradado guarda el último valor bueno con un TTL cien veces mayor, así que un timeout conserva lo que la página ya mostraba; verificado con una mutación que lo elimina. `pythonpath` de pytest incluye `mapcn_demo` para poder probar sus servicios sin instalarla. 82 tests Python en verde. |
| 2026-09-11 | T-013 | OK | TDD: 4 tests que exigen factorías en `__all__`, alias `Mapcn*`, espacio de nombres, presets y helpers accesibles desde el paquete, y stubs que declaran los seis componentes. `__init__.py` reexporta `presets` y `helpers` (Tech §5.1). `reflex component build` regenera `mapcn.pyi` (+358 líneas). README: tabla de capas, tabla de presets con licencia y atribución, y cinco recetas (puntos masivos, radar, tráfico con clave propia, edificios 3D, relieve). La comprobación de la rueda en CI ahora exige `presets.py` y `helpers.py`; verificado que ambos viajan. Fase 2 completa. 69 tests Python y 56 JSX en verde. |
| 2026-09-11 | T-012 | OK | TDD: 5 tests de pytest (preset, precedencia, validación) y 8 en Chromium (fuente raster-dem y activación, hillshade con pintura fusionada, exageración en caliente sin recrear la fuente, apagado al desmontar, restauración tras cambio de estilo, segundo terreno que reemplaza avisando, elevación en el viewport, fallo de teselas DEM). El mapa guarda el terreno activo en un ref del contexto, así que un desmontaje tardío no apaga el relieve de otro componente. Refactor: el informe de error de teselas se comparte entre raster y terreno. 65 tests Python y 56 JSX en verde. Con esto los seis componentes de F1-F5 están completos. |
| 2026-09-11 | T-011 | OK | TDD: 2 tests de pytest y 6 en Chromium (mapeo de icono y texto a layout y paint, inyección de `glyphs` en el estilo transparente en sus dos formas de URL, texto sin tipografías que avisa y omite solo la etiqueta, imágenes antes de la capa y retiradas al desmontar, interactividad por defecto). `Map` gana `glyphs_url`, que es aditivo y no cambia ninguna firma de 0.1.0. 60 tests Python y 48 JSX en verde. |
| 2026-09-11 | T-010 | OK | TDD: 3 tests de pytest y 7 en Chromium (ids y `promote_id`, defaults, mapeo completo de pintura con `circle-sort-key` en layout y no en paint, filtro en caliente, interactividad por defecto y su desactivación, opciones de agrupación que reconstruyen la fuente). El benchmark de 10 000 puntos (REQ-PNT-007) no se puede medir contra el MapLibre simulado: queda para T-020 con `reflex run`. 58 tests Python y 42 JSX en verde. |
| 2026-09-11 | T-009 | OK | TDD: 7 tests de pytest (las dos expresiones generadas, precedencia de la prop explícita, validación) y 5 en Chromium (defaults, mapeo de pintura, caliente, estilo y limpieza). Un test JSX falló por un índice mal contado en la rampa de color y se corrigió el test, no el componente. Anotado un conflicto de spec para T-017: REQ-SIS-008 pide un mapa de calor filtrado, pero el API Spec no da prop `filter` al heatmap y DD-006 prohíbe reenviar los datos; se resolverá con un Delta. 55 tests Python y 35 JSX en verde. |
| 2026-09-11 | T-008 | OK | TDD: 6 tests de pytest (validación temprana y props) y 5 en Chromium (fuente por diccionario, fuente del estilo por id que solo añade la capa y no se borra al desmontar, fusión de pintura de hover, visibilidad, id de fuente inexistente). Se aplica de paso el hallazgo A-09: `LayerFeatureEvent` se exporta como alias de `MapGeoJSONEvent`. 48 tests Python y 30 JSX en verde. |
| 2026-09-11 | T-007 | OK | TDD: 8 tests con el cliente HTTP simulado antes del código (éxito, timeout, JSON inválido, estado 503, payload sin radar, plantilla de teselas y sus opciones). `helpers.py` importa `httpx` directamente, así que se declara como dependencia explícita en `pyproject.toml`; ya venía con reflex. 42 tests Python y 25 JSX en verde. |
| 2026-09-11 | T-006 | OK | TDD en dos frentes: 9 tests de pytest y 8 en Chromium, escritos antes del componente. Decisión de implementación: el rango de zoom sale de la clave de reconstrucción del hook (`sourceIdentity`), porque REQ-RAS-002 exige aplicarlo con `setLayerZoomRange` sin recrear la fuente; la fuente conserva su `maxzoom` nativo para que el sobre-zoom siga funcionando. 34 tests Python y 25 JSX en verde. |
| 2026-09-11 | T-005 | OK | TDD: `tests/test_presets.py` y `tests/test_helpers.py` primero (rojo: módulos inexistentes), luego `presets.py` y `helpers.py`. 19 tests nuevos, 25 de pytest en total. Los helpers rechazan listas de stops vacías o no ascendentes, que MapLibre rechazaría en tiempo de estilo. |
| 2026-09-11 | T-003, T-004 | OK | TDD: `tests/js/tests/layer_runtime.test.mjs` primero (rojo: no existía `useMapLayer`), luego el hook. 17/17 passing, ERRORS: none. Mutación de tres puntos del hook (setFilter, dedupe de advertencias, orden de limpieza) para comprobar que los tests discriminan; la primera versión del test de `before_id` no detectaba la mutación y se reforzó con una reconstrucción en frío. |
| 2026-09-11 | T-001, T-002 | OK | Harness JSX versionado en `tests/js/` (stub MapLibre que registra llamadas y lanza donde lanza MapLibre, `render()` con act, runner Playwright). `bash tests/js/run.sh` → 2/2 passing, ERRORS: none. `ruff`, `compileall` y `pytest` (6) en verde. CHANGELOG ya existía desde 0.1.0. |

Si al implementar se descubre que la spec estaba mal: parar, abrir Delta en `docs/changes/`, y solo entonces seguir.
