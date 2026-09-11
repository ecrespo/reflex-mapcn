# reflex-mapcn 0.2.0 — Capas avanzadas y demo sísmico de Venezuela

## Product Requirements Document (PRD)

| Campo | Valor |
|---|---|
| **Autor** | Ernesto Crespo (redacción asistida por Claude) |
| **Estado** | `APPROVED` — aprobado 2026-09-11 (checkpoint 1) |
| **Versión** | 1.1 |
| **Fecha** | 2026-09-11 |
| **Reviewers** | Ernesto Crespo |
| **Última actualización** | 2026-09-11 |
| **Constitución** | `docs/specs/constitution.md` v1.0 |

---

## 1. Resumen Ejecutivo

Vamos a extender `reflex-mapcn` (0.1.0, publicado en PyPI) con seis funcionalidades que hoy no existen en mapcn upstream y que son las que separan un "mapa bonito" de una herramienta de análisis geoespacial: **F1** capas raster de teselas (`map_raster_layer`, con presets para RainViewer, OpenRailwayMap, OpenSeaMap e imagen satelital), **F2** una capa genérica MapLibre (`map_layer`, cualquier `source` + `layer` desde Python), **F3** mapas de calor (`map_heatmap_layer`), **F4** capas de puntos renderizadas en GPU (`map_circle_layer` y `map_symbol_layer`) para miles de puntos con estilo dirigido por datos, **F5** terreno 3D con sombreado (`map_terrain`) y **F6** una página de demo "Sismos" para Venezuela que consume el catálogo del USGS (histórico desde 1900 y en vivo), muestra las fallas activas del GEM y añade una matriz de tiempos de viaje entre ciudades (OSRM).

Los destinatarios son desarrolladores Python que construyen aplicaciones Reflex con mapas (dashboards operativos, logística, salud, riesgo) y, como caso de uso guía, cualquier equipo venezolano que necesite visualizar el país con datos propios. Se mide por: los seis componentes publicados en 0.2.0 con tests trazables, la demo Sismos funcionando contra datos reales, y ningún cambio incompatible en la API 0.1.0.

## 2. Contexto y Problema

### 2.1 Situación actual
`reflex-mapcn` 0.1.0 expone los 15 componentes de mapcn más `map_camera`. Las únicas capas de datos son `map_geojson` (relleno/contorno), `map_arc`, `map_route` y `map_cluster_layer`. La demo de Venezuela (`/venezuela`) muestra estados, capitales y ciudades sobre OpenFreeMap.

### 2.2 Problema
Con 0.1.0 no se puede: superponer teselas de terceros (radar, ferrocarril, náutico, satélite); dibujar puntos con radio o color dependientes de una propiedad (magnitud, población) sin recurrir a marcadores DOM (que degradan a partir de ~300 elementos); pintar densidad; mostrar relieve; ni añadir una capa MapLibre arbitraria sin editar `mapcn.jsx`. Las peticiones concretas del usuario (tráfico, hoteles/turismo, sismos con histórico) son todas casos de estas carencias.

### 2.3 Oportunidad
MapLibre GL ya implementa raster, heatmap, circle, symbol, raster-dem/terrain e hillshade de forma nativa; el coste es exponerlos con la misma disciplina de mapcn (props declarativas, limpieza determinista, payloads serializables). El USGS, GEM y OSRM ofrecen datos abiertos sin key. El release 0.2.0 convierte el paquete en una base real de análisis geoespacial en Reflex y produce una demo con datos reales del país.

## 3. Usuarios Objetivo

### Persona 1: Desarrollador Reflex de dashboards
- **Descripción:** backend Python que construye paneles internos; no quiere escribir JavaScript.
- **Necesidad principal:** poner sus datos (miles de puntos, polígonos, series temporales) en un mapa con estilo dirigido por datos y eventos hacia el estado.
- **Frecuencia de uso:** diaria durante el desarrollo.
- **Nivel técnico:** alto en Python, bajo en MapLibre.

### Persona 2: Analista / usuario final de la demo
- **Descripción:** persona que consulta el mapa de sismos o el mapa país para tomar decisiones o informar.
- **Necesidad principal:** ver dónde, cuándo y de qué magnitud ocurrieron los sismos; filtrar por fecha y magnitud; entender el contexto (fallas, relieve).
- **Frecuencia de uso:** eventual (tras un evento) o semanal.
- **Nivel técnico:** bajo.

### Persona 3: Mantenedor del paquete
- **Descripción:** quien publica releases y responde issues.
- **Necesidad principal:** que cada componente nuevo tenga contrato claro, tests y limpieza correcta para no heredar bugs de ciclo de vida.
- **Frecuencia de uso:** por release.
- **Nivel técnico:** alto.

## 4. Objetivos y Métricas de Éxito

### 4.1 Objetivos del producto

| Objetivo | Métrica | Target | Plazo |
|---|---|---|---|
| Publicar 0.2.0 con F1–F5 | Componentes en PyPI con `.pyi` y README | 6 componentes nuevos (`map_raster_layer`, `map_layer`, `map_heatmap_layer`, `map_circle_layer`, `map_symbol_layer`, `map_terrain`) | Release 0.2.0 |
| Sin regresiones | Tests 0.1.0 + smoke JSX | 100 % en verde | Cada PR |
| Demo Sismos con datos reales | Página `/sismos` | Histórico USGS ≥ 4.0 desde 1900 + en vivo + fallas GEM + línea de tiempo | Release 0.2.0 |
| Rendimiento de capas de puntos | Frames/seg con 10 000 puntos | ≥ 30 fps en portátil medio (Chromium) al mover el mapa | Antes de 0.2.0 |
| Trazabilidad | REQ MUST con test que lo cita | 100 % | Analyze |

### 4.2 Objetivos de usuario

| Objetivo del usuario | Indicador |
|---|---|
| Añadir radar de lluvia con una línea | `mapcn.map_raster_layer(preset="rainviewer")` funciona sin key |
| Puntos por magnitud sin JS | `map_circle_layer(radius=["interpolate", ...])` acepta expresiones MapLibre |
| Ver sismos de una fecha | Slider temporal filtra en < 100 ms sin ir al backend |
| Relieve del país | `map_terrain(exaggeration=1.5)` sobre OpenFreeMap |

## 5. Alcance

### 5.1 In scope
- [ ] F1 `map_raster_layer` con `tiles`/`url`, `tile_size`, `opacity`, `min_zoom`/`max_zoom`, `attribution`, `before_id`, `visible`, y presets `rainviewer`, `openrailwaymap`, `openseamap`, `esri_satellite`.
- [ ] F2 `map_layer` genérico: `source` (dict MapLibre o id de fuente existente) + `layer` (dict MapLibre), `before_id`, `interactive`, `on_click`, `on_hover`, y actualización en caliente de `data`, `paint`, `layout`, `filter`.
- [ ] F3 `map_heatmap_layer`: `data`, `weight`, `intensity`, `radius`, `color`, `opacity`, `max_zoom_fade`, `before_id`.
- [ ] F4 `map_circle_layer` y `map_symbol_layer`: datos GeoJSON/URL, paint/layout dirigidos por datos, `promote_id`, hover state, `on_click`/`on_hover`, imágenes de icono (`images`) para symbol.
- [ ] F5 `map_terrain`: fuente `raster-dem` (`tiles`/`url`, `encoding`), `exaggeration`, `hillshade` opcional con su paint, preset `aws_terrarium`.
- [ ] F6 Demo: página `/sismos` (USGS histórico + en vivo, fallas GEM recortadas a Venezuela, línea de tiempo, filtros, popups, heatmap de densidad) y matriz de tiempos de viaje OSRM entre capitales en `/venezuela`.
- [ ] Documentación: README, CHANGELOG, `.pyi`, recetas.

### 5.2 Out of scope (esta iteración)
- Tráfico en tiempo real (TomTom/HERE): requiere key comercial; se cubrirá vía `map_raster_layer` con `tiles` propios y una receta, sin preset oficial.
- POIs de turismo/hoteles (Overpass): backend propio; iteración 0.3.
- PMTiles / offline, dibujo (Terra Draw), medición, geocodificación, isócronas: iteración 0.3+.
- Scraping de FUNVISIS: sin API pública ni licencia clara.
- Capas vector tile (`map_vector_layer`): `map_layer` ya permite `source: {type: "vector"}`; el azúcar sintáctico se difiere.

### 5.3 Futuras consideraciones
- `map_layer_group` para agrupar/ordenar capas y un control de capas reutilizable en el demo.
- Serializadores `geopandas`/`shapely`.
- Descarga PNG del mapa.

## 6. Requisitos Funcionales (EARS)

Convenciones: `EL SISTEMA` = el paquete `reflex_mapcn` (JSX + wrapper) salvo que se indique "la demo". IDs estables por feature: `REQ-RAS` (F1), `REQ-LAY` (F2), `REQ-HEA` (F3), `REQ-PNT` (F4), `REQ-TER` (F5), `REQ-SIS`/`REQ-TVJ` (F6). Prioridad MoSCoW al final de cada criterio.

### F1 — `map_raster_layer`

- **REQ-RAS-001** (evento): CUANDO se monte `map_raster_layer` con `tiles` (lista de plantillas `{z}/{x}/{y}`) o `url` (TileJSON) y el mapa esté cargado, EL SISTEMA DEBERÁ añadir una fuente `raster` y una capa `raster` con id determinista (`raster-source-{id}` / `raster-layer-{id}`) antes de `before_id` si esa capa existe en el estilo. MUST
- **REQ-RAS-002** (evento): CUANDO cambien `opacity`, `visible`, `min_zoom` o `max_zoom`, EL SISTEMA DEBERÁ aplicar el cambio con `setPaintProperty`/`setLayoutProperty`/`setLayerZoomRange` sin recrear la fuente. MUST
- **REQ-RAS-003** (evento): CUANDO cambien `tiles` o `url`, EL SISTEMA DEBERÁ retirar fuente y capa y volver a crearlas con los nuevos valores, conservando `before_id` y opacidad. MUST
- **REQ-RAS-004** (ubicuo): EL SISTEMA DEBERÁ aceptar `tile_size` 256 o 512 (default 256), `attribution` (string) y `scheme` (`xyz` | `tms`, default `xyz`) y pasarlos a la fuente MapLibre. MUST
- **REQ-RAS-005** (opcional): DONDE se use `preset="openrailwaymap"`, `"openseamap"` o `"esri_satellite"`, EL SISTEMA DEBERÁ rellenar `tiles`, `tile_size`, `max_zoom` y `attribution` con los valores de la tabla de presets del API Spec, permitiendo sobrescribir cualquiera de ellos con la prop explícita. MUST
- **REQ-RAS-006** (opcional): DONDE se use `preset="rainviewer"`, EL SISTEMA DEBERÁ exponer en Python los helpers `rainviewer_frames()` (consulta `weather-maps.json`, timeout 10 s, devuelve `host`, `past` y `nowcast`) y `rainviewer_tiles(frame, host)` (construye `{host}{path}/256/{z}/{x}/{y}/{color}/{options}.png`); el componente DEBERÁ recibir el resultado en `tiles` y el preset solo DEBERÁ aportar `tile_size=256`, `max_zoom=7` y atribución. MUST
- **REQ-RAS-007** (no deseado): SI `rainviewer_frames()` no obtiene respuesta en 10 s o la respuesta no es JSON válido, ENTONCES EL SISTEMA DEBERÁ devolver una lista vacía y registrar una advertencia, sin lanzar excepción al estado. MUST
- **REQ-RAS-008** (evento): CUANDO el estilo base cambie (tema claro/oscuro o `styles`), EL SISTEMA DEBERÁ volver a añadir la fuente y la capa raster tras `style.load`, en el mismo orden relativo. MUST
- **REQ-RAS-009** (evento): CUANDO el componente se desmonte, EL SISTEMA DEBERÁ retirar la capa y la fuente y no dejar listeners. MUST
- **REQ-RAS-010** (no deseado): SI una tesela falla al cargar (HTTP 4xx/5xx), ENTONCES EL SISTEMA DEBERÁ dejar la celda vacía sin error visible ni excepción, delegando en el comportamiento estándar de MapLibre. SHOULD
- **REQ-RAS-011** (opcional): DONDE se pase `on_load_error`, EL SISTEMA DEBERÁ invocarlo con `{"source_id", "message"}` la primera vez que MapLibre emita `error` para esa fuente, y como máximo una vez por minuto. COULD

### F2 — `map_layer`

- **REQ-LAY-001** (evento): CUANDO se monte `map_layer` con `source` (dict MapLibre de tipo `geojson`, `vector`, `raster`, `raster-dem`, `image` o `video`) y `layer` (dict con `type`, `paint`, `layout`, `filter`, `minzoom`, `maxzoom`, `source-layer`), EL SISTEMA DEBERÁ registrar la fuente con id `layer-source-{id}` y la capa con id `layer-{id}`, inyectando `source` en la capa automáticamente. MUST
- **REQ-LAY-002** (opcional): DONDE `source` sea un string, EL SISTEMA DEBERÁ interpretarlo como id de una fuente ya existente en el mapa (p. ej. la del estilo base o de otro componente) y solo añadir la capa. MUST
- **REQ-LAY-003** (evento): CUANDO cambie `source.data` de una fuente `geojson`, EL SISTEMA DEBERÁ llamar a `setData` sin recrear la capa. MUST
- **REQ-LAY-004** (evento): CUANDO cambien `layer.paint`, `layer.layout` o `layer.filter`, EL SISTEMA DEBERÁ aplicar cada propiedad modificada con `setPaintProperty`, `setLayoutProperty` o `setFilter` respectivamente. MUST
- **REQ-LAY-005** (evento): CUANDO cambie `layer.type`, `source.type` o cualquier propiedad de la fuente distinta de `data`, EL SISTEMA DEBERÁ recrear fuente y capa. MUST
- **REQ-LAY-006** (opcional): DONDE `interactive=True`, CUANDO el usuario haga clic sobre una feature de la capa, EL SISTEMA DEBERÁ invocar `on_click` con `{"feature": {id, properties, geometry, source, sourceLayer}, "longitude", "latitude"}`; y CUANDO el cursor entre/salga de una feature DEBERÁ invocar `on_hover` con el mismo payload o `None`, y marcar `feature-state.hover` si la fuente tiene ids. MUST
- **REQ-LAY-007** (no deseado): SI `layer` carece de `type` o `source` no es dict ni string, ENTONCES EL SISTEMA DEBERÁ lanzar `ValueError` en Python en `create()` con el nombre de la prop inválida, antes de compilar. MUST
- **REQ-LAY-008** (no deseado): SI `before_id` no existe en el estilo, ENTONCES EL SISTEMA DEBERÁ añadir la capa al final del orden sin error (misma política que `map_route`). MUST
- **REQ-LAY-009** (evento): CUANDO el estilo base cambie o el componente se desmonte, EL SISTEMA DEBERÁ comportarse como REQ-RAS-008 y REQ-RAS-009. MUST
- **REQ-LAY-010** (no deseado): SI `source` es un id de fuente que no existe en el estilo activo, ENTONCES EL SISTEMA DEBERÁ omitir la capa, registrar la advertencia `mapcn: source "<id>" not found` una vez, y reintentar automáticamente tras el siguiente `style.load`. MUST

### F3 — `map_heatmap_layer`

- **REQ-HEA-001** (evento): CUANDO se monte `map_heatmap_layer` con `data` (FeatureCollection de puntos o URL), EL SISTEMA DEBERÁ añadir una fuente `geojson` y una capa `heatmap` con ids `heatmap-source-{id}` / `heatmap-layer-{id}`. MUST
- **REQ-HEA-002** (ubicuo): EL SISTEMA DEBERÁ mapear las props `weight` → `heatmap-weight`, `intensity` → `heatmap-intensity`, `radius` → `heatmap-radius`, `color` → `heatmap-color`, `opacity` → `heatmap-opacity`, aceptando números o expresiones MapLibre, con defaults documentados en el API Spec. MUST
- **REQ-HEA-003** (opcional): DONDE se pase `weight_property="mag"` y `weight_range=[min, max]`, EL SISTEMA DEBERÁ generar la expresión `["interpolate", ["linear"], ["get", "mag"], min, 0, max, 1]` como `heatmap-weight`. SHOULD
- **REQ-HEA-004** (opcional): DONDE se pase `max_zoom_fade=Z`, EL SISTEMA DEBERÁ generar `heatmap-opacity` que interpola de 1 a 0 entre `Z-1` y `Z`, para combinar con una capa de puntos que aparece a partir de `Z`. SHOULD
- **REQ-HEA-005** (evento): CUANDO cambien `data` o cualquier prop de paint, EL SISTEMA DEBERÁ actualizar en caliente según REQ-LAY-003/004. MUST
- **REQ-HEA-006** (evento): CUANDO el estilo cambie o el componente se desmonte, EL SISTEMA DEBERÁ comportarse como REQ-RAS-008/009. MUST

### F4 — `map_circle_layer` y `map_symbol_layer`

- **REQ-PNT-001** (evento): CUANDO se monte `map_circle_layer` con `data`, EL SISTEMA DEBERÁ añadir fuente `geojson` (con `promote_id` si se indica) y capa `circle` con ids `circle-source-{id}` / `circle-layer-{id}`, mapeando `radius`, `color`, `opacity`, `stroke_color`, `stroke_width`, `stroke_opacity`, `blur`, `pitch_scale` a las propiedades `circle-*` y aceptando expresiones MapLibre. MUST
- **REQ-PNT-002** (evento): CUANDO se monte `map_symbol_layer` con `data`, EL SISTEMA DEBERÁ añadir fuente `geojson` y capa `symbol` con ids `symbol-source-{id}` / `symbol-layer-{id}`, mapeando `icon_image`, `icon_size`, `icon_anchor`, `icon_allow_overlap`, `text_field`, `text_font`, `text_size`, `text_offset`, `text_anchor`, `text_color`, `text_halo_color`, `text_halo_width` y `allow_overlap`. MUST
- **REQ-PNT-003** (opcional): DONDE `map_symbol_layer` reciba `images={"nombre": url_png_o_data_uri}`, EL SISTEMA DEBERÁ cargar cada imagen con `map.loadImage` + `map.addImage` antes de añadir la capa, y DEBERÁ retirar las imágenes en el desmontaje. MUST
- **REQ-PNT-004** (no deseado): SI el estilo activo no declara `glyphs` (caso `blank=True`) y `text_field` está definido, ENTONCES EL SISTEMA DEBERÁ registrar una advertencia en consola con la instrucción de pasar `glyphs_url` al `Map`, y DEBERÁ omitir la capa de texto en lugar de romper el mapa. MUST
- **REQ-PNT-005** (opcional): DONDE `Map` reciba `glyphs_url`, EL SISTEMA DEBERÁ inyectarlo en el estilo `blank` (`glyphs: "<url>/{fontstack}/{range}.pbf"`). SHOULD
- **REQ-PNT-006** (opcional): DONDE `interactive=True` (default para ambas capas), EL SISTEMA DEBERÁ emitir `on_click` y `on_hover` con el payload de REQ-LAY-006, cambiar el cursor a `pointer` sobre features, y mantener `feature-state.hover` para que `hover_paint` funcione (`hover_paint` se fusiona con `case` sobre `feature-state.hover`, igual que `map_arc`). MUST
- **REQ-PNT-007** (ubicuo): EL SISTEMA DEBERÁ renderizar 10 000 puntos en `map_circle_layer` manteniendo ≥ 30 fps al arrastrar el mapa en Chromium sobre un portátil medio (Intel i5 integrado). SHOULD
- **REQ-PNT-008** (opcional): DONDE se pase `cluster=True` a `map_circle_layer`, EL SISTEMA DEBERÁ activar clustering en la fuente (`cluster_radius`, `cluster_max_zoom`) y exponer `point_count` a las expresiones; el comportamiento de clic sobre cluster (zoom) es responsabilidad de `map_cluster_layer`, no de este componente. COULD
- **REQ-PNT-009** (evento): CUANDO cambien `data`, paint o layout, o el estilo, o se desmonte, EL SISTEMA DEBERÁ comportarse como REQ-LAY-003/004 y REQ-RAS-008/009. MUST
- **REQ-PNT-010** (no deseado): SI una imagen de `images` no puede cargarse (error de red o formato), ENTONCES EL SISTEMA DEBERÁ registrar `mapcn: image "<name>" failed to load`, añadir la capa sin ese icono y no bloquear las demás imágenes. MUST

### F5 — `map_terrain`

- **REQ-TER-001** (evento): CUANDO se monte `map_terrain` con `tiles` o `url` y `encoding` (`terrarium` | `mapbox`), EL SISTEMA DEBERÁ añadir una fuente `raster-dem` con id `terrain-source-{id}` y llamar a `map.setTerrain({source, exaggeration})`. MUST
- **REQ-TER-002** (opcional): DONDE `preset="aws_terrarium"`, EL SISTEMA DEBERÁ usar `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png`, `encoding="terrarium"`, `tile_size=256`, `max_zoom=15` y la atribución de la tabla de presets. MUST
- **REQ-TER-003** (opcional): DONDE `hillshade=True`, EL SISTEMA DEBERÁ añadir una capa `hillshade` (`hillshade-layer-{id}`) sobre la misma fuente, antes de `before_id` si existe, con `hillshade_paint` fusionado sobre los defaults `{"hillshade-exaggeration": 0.5}`. MUST
- **REQ-TER-004** (evento): CUANDO cambie `exaggeration`, EL SISTEMA DEBERÁ llamar de nuevo a `setTerrain` con el nuevo valor sin recrear la fuente. MUST
- **REQ-TER-005** (evento): CUANDO el componente se desmonte, EL SISTEMA DEBERÁ llamar a `map.setTerrain(null)`, retirar la capa hillshade y la fuente. MUST
- **REQ-TER-006** (evento): CUANDO el estilo base cambie, EL SISTEMA DEBERÁ restaurar terreno e hillshade tras `style.load`. MUST
- **REQ-TER-007** (no deseado): SI se montan dos `map_terrain` en el mismo `Map`, ENTONCES EL SISTEMA DEBERÁ mantener solo el último montado activo y registrar una advertencia en consola (MapLibre admite un único terreno). MUST
- **REQ-TER-008** (opcional): DONDE `Map` reciba `on_move_end` y haya terreno activo, EL SISTEMA DEBERÁ incluir en el payload de viewport el campo `elevation` (m) del centro obtenido con `queryTerrainElevation`, o `null` si no está disponible. COULD
- **REQ-TER-009** (no deseado): SI las teselas DEM fallan (HTTP 4xx/5xx o sin red), ENTONCES EL SISTEMA DEBERÁ mantener el mapa plano en las celdas afectadas sin excepción y, DONDE se pase `on_load_error`, invocarlo con el mismo contrato de REQ-RAS-011. SHOULD

### F6 — Demo "Sismos de Venezuela" y tiempos de viaje

- **REQ-SIS-001** (evento): CUANDO se cargue `/sismos`, la demo DEBERÁ solicitar al backend el catálogo histórico USGS (FDSN `query`, `format=geojson`, caja `[-74, 0.5, -59, 13]`, `minmagnitude=4.0`, `starttime=1900-01-01`, `orderby=time`) y mostrarlo como `map_circle_layer` con radio interpolado por `mag` (M4 → 4 px, M7 → 24 px) y color por profundidad (`< 70 km` rojo, `70–300` naranja, `> 300` azul). MUST
- **REQ-SIS-002** (ubicuo): La demo DEBERÁ cachear en memoria de proceso la respuesta del histórico durante 10 minutos y la del feed en vivo durante 60 s, con clave por parámetros, para no repetir peticiones al USGS por cada sesión. MUST
- **REQ-SIS-003** (no deseado): SI el USGS no responde en 15 s o devuelve un código distinto de 200, ENTONCES la demo DEBERÁ mostrar un aviso en el panel ("No se pudo obtener el catálogo del USGS") y mantener la última respuesta cacheada si existe. MUST
- **REQ-SIS-004** (evento): CUANDO el usuario mueva el slider temporal (rango [1900, hoy], paso 1 año, más un selector fino de mes en los últimos 5 años), la demo DEBERÁ filtrar los sismos visibles mediante `filter=["<=", ["get", "time"], t_ms]` en el cliente, sin nueva petición al backend, en < 100 ms. MUST
- **REQ-SIS-005** (evento): CUANDO el usuario cambie la magnitud mínima (slider 4.0–8.0) o el rango de profundidad, la demo DEBERÁ combinar los filtros con `["all", ...]` en la misma capa. MUST
- **REQ-SIS-006** (evento): CUANDO el usuario haga clic sobre un sismo, la demo DEBERÁ abrir `map_popup` con magnitud (`mag`, `magType`), profundidad (km), fecha/hora en UTC y en `America/Caracas`, `place`, y enlace a `url` del USGS. MUST
- **REQ-SIS-007** (opcional): DONDE el interruptor "En vivo" esté activo, la demo DEBERÁ consultar cada 60 s (tarea en segundo plano de Reflex) el servicio FDSN del USGS con la caja de Venezuela, `minmagnitude=2.5` y `starttime = ahora − 30 días` (no los feeds globales `all_*`, que pesan varios MB), y mostrar los eventos como una segunda capa con anillo estático más ancho para los de las últimas 24 h. MUST
- **REQ-SIS-008** (opcional): DONDE el interruptor "Densidad" esté activo, la demo DEBERÁ mostrar `map_heatmap_layer` alimentado por el mismo histórico filtrado, con `weight_property="mag"`, `max_zoom_fade=8`. MUST
- **REQ-SIS-009** (opcional): DONDE el interruptor "Fallas" esté activo, la demo DEBERÁ mostrar las fallas activas del GEM recortadas a la caja ampliada `[-76, -1, -57, 15]` desde `assets/venezuela_fallas.geojson` (generado en build por script) como `map_layer` tipo `line`, coloreadas por `slip_type`, con tooltip de `name` y `slip_type`. MUST
- **REQ-SIS-010** (opcional): DONDE el interruptor "Relieve" esté activo, la demo DEBERÁ activar `map_terrain(preset="aws_terrarium", hillshade=True, exaggeration=1.3)`. SHOULD
- **REQ-SIS-011** (ubicuo): La demo DEBERÁ marcar los sismos históricos notables (Caracas 1812-03-26, Caracas 1967-07-29, Cariaco 1997-07-09, Boca de Uchire 2018-08-21) con `map_marker` y etiqueta, a partir de una lista estática en `venezuela_data.py` con fecha, magnitud y fuente. SHOULD
- **REQ-SIS-012** (ubicuo): La demo DEBERÁ mostrar la atribución "USGS Earthquake Hazards Program · GEM Global Active Faults (CC BY-SA 4.0)" en el panel. MUST
- **REQ-TVJ-001** (evento): CUANDO el usuario pulse "Tiempos de viaje" en `/venezuela` con un estado seleccionado, la demo DEBERÁ consultar la OSRM Table API (`/table/v1/driving/`, `annotations=duration,distance`) desde la capital de ese estado hacia las demás capitales continentales (máx. 25 destinos por petición) y mostrar una tabla ordenada por duración con `h m` y `km`. MUST
- **REQ-TVJ-002** (no deseado): SI OSRM devuelve `code != "Ok"`, no responde en 15 s, o una celda es `null` (sin ruta, p. ej. islas), ENTONCES la demo DEBERÁ mostrar "sin ruta" en esa celda y un aviso general si toda la matriz falla, sin excepción. MUST
- **REQ-TVJ-003** (evento): CUANDO el usuario pulse una fila de la tabla, la demo DEBERÁ dibujar la ruta con `map_route` (OSRM `route` con `overview=full`) y ajustar la cámara a sus bounds. SHOULD
- **REQ-TVJ-004** (ubicuo): La demo DEBERÁ cachear las matrices OSRM 1 hora por capital de origen. MUST

## 7. Requisitos No Funcionales

### Rendimiento
- Actualización de `filter`/paint desde estado: percibida < 100 ms tras recibir el delta de estado.
- Histórico USGS Venezuela ≥ M4 desde 1900 ≈ 3 000–4 500 eventos (~1.5 MB GeoJSON): el backend DEBERÁ recortar las propiedades a `mag, magType, depth, time, place, url, id` antes de enviarlas al cliente (≤ 400 KB).
- Sin degradación en la demo actual: las páginas 0.1.0 no cargan código nuevo hasta que se use un componente nuevo (lazy `ClientSide`).

### Seguridad
- Sin claves en el repositorio; `.env.example` documenta variables opcionales.
- URLs de teselas y GeoJSON externas se pasan tal cual a MapLibre (lado cliente); el backend solo llama a USGS/OSRM/RainViewer con `httpx` y timeouts explícitos.
- Las expresiones MapLibre se serializan como JSON; no hay `eval` en JSX.

### Disponibilidad
- La demo DEBERÁ funcionar (mapa, estados, ciudades) aunque USGS, OSRM o RainViewer estén caídos; las capas afectadas muestran aviso.

### Compatibilidad
- Reflex ≥ 0.8.1; navegadores con WebGL2 (requisito de maplibre-gl 6).

### Observabilidad
- Advertencias de consola con prefijo `mapcn:` en el JSX; `logging.getLogger("reflex_mapcn")` en Python.

## 8. Restricciones y Dependencias

### Restricciones técnicas
- Un único terreno por mapa (MapLibre).
- Las capas `symbol` con texto requieren `glyphs` en el estilo; el estilo `blank` no lo trae.
- `heatmap` solo acepta fuentes de puntos.
- RainViewer: zoom máximo 7 en teselas; los frames expiran (~2 h); se requiere consultar el JSON.

### Dependencias externas

| Dependencia | Tipo | Owner | Estado | Riesgo |
|---|---|---|---|---|
| USGS FDSN Event + feeds | API pública, sin key | USGS | Estable | Bajo (cuota implícita; cachear) |
| OSRM demo server | API pública, sin key, "uso razonable" | Project OSRM | Estable | Medio (puede limitar; cachear 1 h) |
| RainViewer weather-maps.json | API pública | RainViewer | Estable | Medio (términos: uso no comercial gratuito) |
| OpenRailwayMap / OpenSeaMap tiles | Teselas, CC BY-SA | comunidad OSM | Estable | Bajo |
| Esri World Imagery | Teselas con atribución | Esri | Estable | Bajo |
| AWS Terrain Tiles (Terrarium) | Teselas públicas S3 | AWS Open Data | Estable | Bajo |
| GEM Global Active Faults | GeoJSON, CC BY-SA 4.0 | GEM | Archivo estático | Bajo (descarga en build) |

## 9. User Stories

### Épica: Capas de datos avanzadas (F1–F5)
- **US-001:** Como desarrollador Reflex, quiero superponer teselas de terceros con `map_raster_layer(preset=...)`, para añadir radar, ferrocarril o satélite sin escribir JS. — Criterios: REQ-RAS-001, 005, 006.
- **US-002:** Como desarrollador, quiero `map_layer(source=..., layer=...)` para usar cualquier capacidad de MapLibre que el paquete aún no envuelve. — REQ-LAY-001..006.
- **US-003:** Como desarrollador, quiero `map_circle_layer` con radio/color por propiedad para mostrar miles de puntos fluidos. — REQ-PNT-001, 006, 007.
- **US-004:** Como desarrollador, quiero `map_heatmap_layer` para mostrar densidad. — REQ-HEA-001..004.
- **US-005:** Como desarrollador, quiero `map_terrain(preset="aws_terrarium")` para relieve 3D. — REQ-TER-001..003.

### Épica: Demo Sismos y tiempos de viaje (F6)
- **US-006:** Como analista, quiero ver los sismos de Venezuela por fecha y magnitud, con detalles al hacer clic. — REQ-SIS-001, 004, 005, 006.
- **US-007:** Como analista, quiero ver los sismos recientes en vivo. — REQ-SIS-007.
- **US-008:** Como analista, quiero ver fallas activas y relieve para entender el contexto. — REQ-SIS-009, 010.
- **US-009:** Como usuario de la demo país, quiero saber cuánto se tarda en coche desde una capital a las demás. — REQ-TVJ-001..003.

## 10. Wireframes (descripción)

- `/sismos`: mapa a altura 680 px con OpenFreeMap; panel superior izquierdo con: título, contador "N sismos (M ≥ x) hasta {fecha}", slider temporal con botón ▶ (reproduce 1 año/200 ms), slider magnitud, selector de profundidad, interruptores En vivo / Densidad / Fallas / Relieve / Notables; leyenda inferior izquierda (color por profundidad, radio por magnitud, tipos de falla); popup de sismo; badge "USGS · GEM" con última actualización.
- `/venezuela`: al panel existente se añade el botón "Tiempos de viaje" (activo con estado seleccionado) que despliega una tabla lateral derecha (capital destino, duración, distancia) y dibuja la ruta seleccionada.

## 11. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Cambio de estilo (tema) borra capas nuevas | Alta | Alto | Patrón `isLoaded` + re-add tras `style.load` ya usado por `map_route`; test JSX que dispara `style.load` (REQ-*-008) |
| Estilo `blank` sin glyphs rompe `symbol` con texto | Media | Medio | REQ-PNT-004/005 |
| OSRM demo limita peticiones | Media | Medio | Caché 1 h, máx. 25 destinos, botón bajo demanda |
| RainViewer cambia esquema de teselas | Baja | Medio | Helper en Python aislado; preset actualizable en minor |
| GEM faults ~ decenas de MB | Alta | Medio | Script de build recorta a Venezuela y simplifica; se versiona el resultado (~200 KB) en `assets/` |
| Volumen del histórico USGS | Media | Medio | Recorte de propiedades en backend; `minmagnitude=4.0` |
| Dos terrenos en un mapa | Baja | Bajo | REQ-TER-007 |

## 12. Timeline estimado

| Fase | Duración estimada | Entregable |
|---|---|---|
| Spec & Design (este paquete de docs) | 2 días | Specs aprobadas + Analyze |
| Fase 1 — infraestructura JSX común (registro de capas, re-add tras style.load, hooks) | 2 días | `useMapLayer` hook + tests |
| Fase 2 — F1, F2, F3, F4, F5 | 5 días | Componentes + `.pyi` + tests |
| Fase 3 — F6 demo (backend USGS/OSRM, página, assets) | 3 días | `/sismos`, tiempos de viaje |
| Fase 4 — Hardening, docs, release 0.2.0 | 2 días | PyPI 0.2.0, CHANGELOG |

## Constitution check

- Art. 1: F1–F5 son "Reflex extra"; se marcan así en docstrings/README. Cumple.
- Art. 2: todos los payloads definidos en §6 son dicts/listas planas; REQ-LAY-006 fija el shape. Cumple.
- Art. 3: sin npm nuevo (raster, heatmap, circle, symbol, terrain son nativos de maplibre-gl). Cumple.
- Art. 4: REQ-*-008/009 exigen re-add tras `style.load` y limpieza. Cumple.
- Art. 5: USGS/OSRM/RainViewer se llaman desde backend de la demo o helpers opcionales con timeout; sin keys. Cumple.
- Art. 6/8: cada MUST tiene ID; Tasks y Analyze pendientes en los artefactos siguientes.

---

## Historial de cambios

| Versión | Fecha | Autor | Cambios |
|---|---|---|---|
| 1.0 | 2026-09-11 | E. Crespo / Claude | Versión inicial (DRAFT) |
| 1.1 | 2026-09-11 | Claude | Correcciones del Analyze A-01..A-05: REQ-RAS-006 unificado con API, REQ-SIS-007 usa FDSN con bbox, nuevos REQ-LAY-010, REQ-PNT-010, REQ-TER-009 |

## Aprobaciones

| Rol | Nombre | Fecha | Estado |
|---|---|---|---|
| Product owner | Ernesto Crespo | 2026-09-11 | ☑ Aprobado |
| Tech lead | Ernesto Crespo | 2026-09-11 | ☑ Aprobado |
