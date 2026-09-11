# Constitución — reflex-mapcn

> Versión 1.0 · Ratificada: 2026-09-11 · Última enmienda: —
> Ámbito: repositorio `reflex-mapcn` (paquete `custom_components/reflex_mapcn`, app `mapcn_demo`, `tests/`, `docs/`)
> Nivel de rigor SDD: **spec-anchored** — las specs viven en `docs/specs/`, se versionan con el código y los cambios a features ya publicadas entran como Delta Specs en `docs/changes/`.

## Artículos

### Art. 1 — Paridad con mapcn
EL SISTEMA DEBERÁ conservar la API pública de mapcn (nombres de componentes, props y semántica de `src/registry/map.tsx` upstream) como subconjunto de la API de `reflex_mapcn`; toda extensión propia DEBERÁ estar marcada como "Reflex extra" en el docstring, el README y la spec que la introduce.
*Racional: los usuarios llegan desde la documentación de mapcn.dev; una divergencia silenciosa rompe esa transferencia de conocimiento.*

### Art. 2 — Payloads serializables
EL SISTEMA DEBERÁ entregar a todo `rx.EventHandler` únicamente valores serializables a JSON (dict, list, str, número, bool, null) construidos en `mapcn.jsx`; ningún objeto de MapLibre, evento del DOM ni referencia circular cruza al backend.
*Racional: el canal de eventos de Reflex hace `JSON.stringify`; un objeto no serializable produce un fallo en tiempo de ejecución que no se ve en compilación.*

### Art. 3 — Una sola dependencia npm
EL SISTEMA DEBERÁ depender en el frontend únicamente de `maplibre-gl` (más lo que Reflex ya provee: `react`, `react-dom`, `@emotion/react`); toda funcionalidad nueva DEBERÁ implementarse en `mapcn.jsx`/`mapcn.css` sin añadir paquetes npm, salvo que una Delta Spec aprobada lo justifique.
*Racional: cada dependencia npm es un vector de rotura de versión en el `bun install` de los usuarios y un riesgo de cadena de suministro.*

### Art. 4 — Cliente-only y limpieza determinista
EL SISTEMA DEBERÁ declarar todo componente como `NoSSRComponent` y DEBERÁ retirar en el `cleanup` de cada efecto de React todas las fuentes, capas, marcadores, popups, imágenes y listeners que ese efecto añadió al mapa, en orden inverso a su creación.
*Racional: MapLibre necesita `window`; y una capa huérfana tras un re-render produce el error `Source "x" already exists` que solo aparece al navegar entre páginas.*

### Art. 5 — Fuentes de datos externas
EL SISTEMA DEBERÁ consumir servicios externos (USGS, OSRM, RainViewer, OpenFreeMap, etc.) exclusivamente desde el backend de la app o desde el navegador del usuario final, nunca desde el paquete en tiempo de importación; DEBERÁ documentar para cada servicio su licencia, atribución obligatoria, cuota y comportamiento ante fallo (timeout ≤ 15 s, mensaje al usuario, sin excepción no capturada); y DEBERÁ leer toda clave de API desde variables de entorno, nunca desde código ni desde `assets/`.
*Racional: el paquete se instala en apps de terceros; una llamada de red al importar bloquea `reflex run`, y una clave en el repo es una fuga.*

### Art. 6 — Pruebas trazables
EL SISTEMA DEBERÁ cubrir todo requisito MUST (`REQ-*`) con al menos un test en `tests/` (Python: codegen/props/eventos) o en `tests/js/` (JSX en Chromium con MapLibre simulado) que cite el REQ en su nombre o docstring, y DEBERÁ mantener `ruff check` y `python -m compileall` en verde antes de cada merge.
*Racional: la verificación del JSX solo es posible en navegador; sin tests con REQ en el nombre la trazabilidad se pierde al segundo release.*

### Art. 7 — Compatibilidad y versionado
EL SISTEMA DEBERÁ mantener `reflex>=0.8.1` como mínimo soportado, DEBERÁ versionar el paquete con SemVer (cambio de firma pública de un componente ya publicado ⇒ major o Delta Spec con periodo de deprecación de una minor), y DEBERÁ acompañar cada release con entrada en `CHANGELOG.md` y actualización de `README.md`.
*Racional: el paquete está en PyPI; los usuarios fijan versiones y esperan que una minor no rompa.*

### Art. 8 — Proceso
EL EQUIPO DEBERÁ obtener spec aprobada (PRD con EARS + Tasks, y los 5 documentos + Analyze para trabajo ≥ feature media) antes de implementar, DEBERÁ actualizar la spec como parte del Definition of Done, y DEBERÁ ejecutar las Tasks por tandas de 3-5 con revisión intermedia cuando las implemente un agente.
*Racional: el JSX y el wrapper Python deben evolucionar juntos; la spec es el único lugar donde ambos lados se acuerdan antes de escribir código.*

### Art. 9 — Idioma
EL EQUIPO DEBERÁ escribir código, docstrings, comentarios, README, CHANGELOG y skills en inglés, y las specs de `docs/` en español con identificadores de código en inglés.
*Racional: el paquete es público e internacional; las specs son el vehículo de trabajo del equipo.*

## Restricciones del stack

| Área | Decisión |
|---|---|
| Lenguaje backend | Python ≥ 3.10 (soporte 3.10–3.13) |
| Framework | Reflex ≥ 0.8.1 (probado con 0.9.x); `NoSSRComponent`, `rx.asset(shared=True)` |
| Frontend | React 19 (provisto por Reflex), `maplibre-gl@^6.3.0`, JSX sin TypeScript, CSS plano con variables Radix |
| Empaquetado | setuptools, `custom_components/` layout, `uv` para entorno/build/publish, `reflex component build` para `.pyi` |
| Calidad | ruff (E, F, I, B, UP), `compile_check` de la demo, tests Python + smoke test JSX en Chromium (Playwright) |
| Datos geoespaciales | GeoJSON RFC 7946 (lng, lat[, elev]); coordenadas `[longitude, latitude]` siempre en ese orden; fechas ISO-8601 UTC; epochs en milisegundos (convención USGS) |
| Servicios externos permitidos sin key | USGS FDSN/feeds, OSRM demo server, OpenFreeMap, CARTO basemaps, RainViewer, OpenRailwayMap, OpenSeaMap, Esri World Imagery, AWS Terrain Tiles, GEM faults (archivo estático) |
| Servicios con key (opcionales) | TomTom/HERE tráfico, OpenWeatherMap, MapTiler — siempre detrás de variable de entorno y con degradación limpia si falta |

## Enmiendas

| Fecha | Artículo | Cambio | Razón | Aprobado por |
|---|---|---|---|---|
| — | — | — | — | — |

## Constitution check (usar en cada artefacto)

Al final de cada PRD / Tech Design / Plan, una sección de 3-5 líneas: qué artículos aplican y cómo los cumple — o qué excepción se pide y por qué. Una excepción sin justificación escrita es una violación.
