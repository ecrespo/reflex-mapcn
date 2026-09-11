# reflex-mapcn 0.2.0 — Implementation Plan

## Metadata

| Campo | Valor |
|---|---|
| **Autor** | Ernesto Crespo / Claude |
| **Estado** | `APPROVED` — aprobado 2026-09-11 (checkpoint 5) |
| **Versión** | 1.0 |
| **Fecha** | 2026-09-11 |
| **PRD** | `docs/specs/prd/mapcn-layers-0.2.md` |
| **Tech Design** | `docs/specs/technical/mapcn-layers-architecture.md` |
| **Data Model** | `docs/specs/data-model/mapcn-layers-schema.md` |
| **API Spec** | `docs/specs/api/mapcn-components-api-v0.2.md` |
| **Tasks** | `docs/specs/tasks/mapcn-0.2-tasks.md` |

---

## 1. Resumen de implementación

Cuatro fases incrementales, cada una deployable (el paquete sigue instalable y la demo sigue compilando al final de cada fase). Primero la infraestructura JSX común y su harness de pruebas (Fase 1), luego los cinco componentes en orden de dependencia y riesgo (Fase 2: raster y layer genérico desbloquean el resto; circle antes que symbol; terrain al final por ser singleton), después la demo con sus servicios (Fase 3) y por último hardening, docs y release (Fase 4).

**Duración total estimada:** 12 días de trabajo (≈ 3 semanas a tiempo parcial), con factor 1.5 ya aplicado sobre la estimación optimista.
**Equipo:** 1 dev (E. Crespo) + agente (Claude Code) ejecutando Tasks por tandas.
**Fecha objetivo 0.2.0 en PyPI:** 2026-10-03.

## 2. Pre-requisitos

| Pre-requisito | Owner | Estado | Fecha límite |
|---|---|---|---|
| Specs aprobadas (PRD, API, Tech, Data, Plan) + Analyze sin CRÍTICOS | E. Crespo | ✔ 2026-09-11 | 2026-09-14 |
| 0.1.0 publicado y tag `v0.1.0` en git | E. Crespo | ☐ (en curso) | 2026-09-12 |
| Harness JSX (stub maplibre + Playwright) versionado en `tests/js/` (hoy solo existe en scratch) | Agente | ✔ 2026-09-11 | Fase 1 |
| Acceso a red desde la máquina de desarrollo para USGS/OSRM/GEM (no desde el sandbox de Cowork) | E. Crespo | ✔ | — |
| `CHANGELOG.md` creado con sección 0.1.0 | Agente | ✔ 2026-09-11 | Fase 1 |
| Tooling JS en la máquina de desarrollo: `bun` ≥ 1.2, Node ≥ 20 y `playwright` con Chromium (`npx playwright install chromium`) para `tests/js` | E. Crespo | ✔ 2026-09-11 (bun 1.3.13, node 24, Chromium presente) | Fase 1 |

## 3. Fases

---

### Fase 1 — Runtime de capas y harness de pruebas

**Duración:** 2 días
**Objetivo:** `useMapLayer` funcionando con tests en Chromium; base para todo lo demás.

| ID | Tarea | Estimación | Dependencia | Estado |
|---|---|---|---|---|
| F1-01 | Versionar harness JSX: `tests/js/harness/maplibre-stub.js`, `run.mjs`, entry builder con bun | 0.5d | — | ✔ 2026-09-11 |
| F1-02 | Implementar `useMapLayer` en `mapcn.jsx` (add/hot diff/cold recreate/eventos/hover/cleanup/images) | 1d | F1-01 | ✔ 2026-09-11 |
| F1-03 | Tests JSX de `useMapLayer` con una capa `circle` de prueba: add, setData, setPaint, setFilter, style.load re-add, unmount, beforeId inexistente | 0.5d | F1-02 | ✔ 2026-09-11 |
| F1-04 | `CHANGELOG.md` + sección "Unreleased" | 0.1d | — | ✔ 2026-09-11 |

**Done:** `node tests/js/run.mjs` en verde; `python -m compileall` y ruff en verde; ninguna página 0.1.0 cambia de salida (diff de `.web/app/routes` antes/después vacío).

---

### Fase 2 — Componentes F1–F5

**Duración:** 5 días
**Objetivo:** seis componentes nuevos con contrato del API Spec, `.pyi` y tests.

| ID | Tarea | Estimación | Dependencia | Estado |
|---|---|---|---|---|
| F2-01 | `presets.py` (RasterPreset/TerrainPreset + tablas) y `helpers.py` (expresiones) + tests | 0.5d | — | ✔ 2026-09-11 |
| F2-02 | `RasterLayer` JSX + `MapRasterLayer` Python (validación, preset ⊕ props) + tests | 0.75d | F1-02, F2-01 | ✔ 2026-09-11 |
| F2-03 | `rainviewer_frames/tiles` (httpx, timeout, warning) + tests con mock | 0.5d | F2-01 | ✔ 2026-09-11 |
| F2-04 | `Layer` JSX + `MapLayer` Python (source dict/str, validación) + tests | 0.75d | F1-02 | ✔ 2026-09-11 |
| F2-05 | `HeatmapLayer` JSX + `MapHeatmapLayer` (+ `weight_property`, `max_zoom_fade`) + tests | 0.5d | F2-04 | ✔ 2026-09-11 |
| F2-06 | `CircleLayer` JSX + `MapCircleLayer` (+ cluster COULD) + tests; benchmark 10k puntos manual | 0.75d | F2-04 | ✔ 2026-09-11 (benchmark en T-020) |
| F2-07 | `SymbolLayer` JSX + `MapSymbolLayer` (+ `images`, glyphs warn) + `Map.glyphs_url` + tests | 1d | F2-06 | ✔ 2026-09-11 |
| F2-08 | `MapTerrain` JSX + `MapTerrain` Python (+ hillshade, singleton, `elevation` COULD) + tests | 0.75d | F1-02, F2-01 | ✔ 2026-09-11 |
| F2-09 | `__init__.py`/namespace/`__all__`, `reflex component build` (.pyi), README sección "Layers" | 0.5d | F2-02..08 | ✔ 2026-09-11 |

**Done:** todos los REQ MUST de F1–F5 con test que los cita; `uv run reflex component build` genera `.pyi` sin error; demo 0.1.0 compila sin cambios.

---

### Fase 3 — Demo: Sismos y tiempos de viaje

**Duración:** 3 días
**Objetivo:** `/sismos` con datos reales y "Tiempos de viaje" en `/venezuela`.

| ID | Tarea | Estimación | Dependencia | Estado |
|---|---|---|---|---|
| F3-01 | `services/cache.py` (TTL) + `services/usgs.py` (catálogo, live, recorte) + tests con fixtures | 0.75d | — | ✔ 2026-09-11 |
| F3-02 | `scripts/build_faults.py` + generar `assets/venezuela_fallas.geojson` + atribución | 0.5d | — | ✔ 2026-09-11 |
| F3-03 | Página `/sismos`: estado, capa circle, filtros, slider temporal y ▶, popup, leyenda, notables | 1d | F2-06, F3-01 | ☐ |
| F3-04 | En vivo (bg loop 60 s + capa recientes), Densidad (heatmap), Fallas (map_layer), Relieve (terrain) | 0.5d | F3-03, F2-05, F2-04, F2-08, F3-02 | ☐ |
| F3-05 | `services/osrm.py` (table + route, caché) + tests; UI "Tiempos de viaje" en `/venezuela` con tabla y ruta | 0.75d | — | ☐ |
| F3-06 | Nav y README de la demo; `compile_check` de todas las páginas | 0.25d | F3-03..05 | ☐ |

**Done:** `reflex run` muestra `/sismos` con ≥ 1 000 sismos históricos y el feed en vivo; tabla de tiempos desde Caracas con 22 filas; compile_check OK.

---

### Fase 4 — Hardening y release 0.2.0

**Duración:** 2 días
**Objetivo:** publicar.

| ID | Tarea | Estimación | Dependencia | Estado |
|---|---|---|---|---|
| F4-01 | Revisión manual E2E (checklist §7) en claro/oscuro, cambio de estilo con capas activas, navegación entre páginas | 0.5d | Fase 3 | ☐ |
| F4-02 | Rendimiento: 10k puntos (REQ-PNT-007), tamaño del histórico ≤ 400 KB, tiempo de filtro < 100 ms | 0.25d | F3-03 | ☐ |
| F4-03 | Docs finales: README (componentes, presets, atribuciones, recetas tráfico/POIs), CHANGELOG 0.2.0, `.env.example` | 0.5d | F4-01 | ☐ |
| F4-04 | Plegar specs: marcar PRD/API/Tech/Data como `APPROVED`+`IMPLEMENTED`, actualizar Tasks (registro de ejecución) | 0.25d | F4-03 | ☐ |
| F4-05 | `bump_version 0.2.0`, `reflex component build`, `uv publish`, tag `v0.2.0`, `reflex component share` (preview `/sismos`) | 0.5d | F4-04 | ☐ |

**Done:** `pip install reflex-mapcn==0.2.0` funciona en venv limpio; PyPI muestra README nuevo; tag creado.

## 4. Mapa de dependencias

```
Fase 1 (useMapLayer + harness)
  ├──▶ F2-02 Raster ──┐
  ├──▶ F2-04 Layer ───┼──▶ F2-05 Heatmap ─┐
  │                   │                    ├──▶ F3-03/F3-04 Demo Sismos ──▶ Fase 4
  │                   └──▶ F2-06 Circle ──▶ F2-07 Symbol
  └──▶ F2-08 Terrain ─────────────────────┘
F2-01 Presets/helpers (paralelo) ──▶ F2-02, F2-08, F2-03
F3-01 USGS, F3-02 Fallas, F3-05 OSRM (paralelos, sin dependencia del JSX)
```

Paralelizable desde el día 1: F2-01, F3-01, F3-02, F3-05 (solo Python/datos).

## 5. Riesgos de implementación

| Riesgo | Prob. | Impacto | Mitigación | Owner |
|---|---|---|---|---|
| `useMapLayer` no cubre bien raster + geojson y se bifurca | Media | Medio | Diseñar la spec del hook con `source` genérico y `hotKeys`; test con ambas fuentes en F1-03 | Agente |
| Sandbox sin red al implementar (como en este proyecto) | Alta | Medio | Servicios con fixtures JSON; pruebas de red solo en máquina del dev | E. Crespo |
| MapLibre 6 cambia API de `setTerrain`/`raster-dem` | Baja | Alto | Fijar `maplibre-gl@^6.3.0`; test JSX con stub que replica firmas | Agente |
| OSRM demo rechaza `table` con 25 destinos | Media | Bajo | Trocear en 2 peticiones si `code != Ok` | Agente |
| Glyphs incompatibles entre CARTO y OpenFreeMap | Media | Bajo | Default `Noto Sans Regular` + documentación + warn | Agente |

## 6. Comunicación y seguimiento

Trabajo por tandas de 3–5 Tasks (Art. 8): el agente ejecuta, reporta salida de tests (Python y JSX) y el dev revisa antes de la siguiente tanda. El progreso se marca en `docs/specs/tasks/mapcn-0.2-tasks.md`. Desviaciones de la spec ⇒ Delta Spec en `docs/changes/`.

## 7. Definición de Done (global)

- [ ] Código mergeado en `main` con ruff y compileall en verde
- [ ] Tests Python + JSX en verde; cada REQ MUST citado por ≥ 1 test
- [ ] `.pyi` regenerados y commiteados
- [ ] README, CHANGELOG, docstrings actualizados (inglés)
- [ ] Demo compila y las páginas nuevas funcionan con datos reales
- [ ] Specs actualizadas (estado `IMPLEMENTED`) y registro de ejecución en Tasks
- [ ] Atribuciones de datos externos visibles en la demo

## Constitution check

Art. 6 y 8: tandas de 3–5 tareas, tests por REQ, spec plegada al cerrar. Art. 7: 0.2.0 aditivo con CHANGELOG. Sin excepciones.

---

## Historial de cambios

| Versión | Fecha | Autor | Cambios |
|---|---|---|---|
| 1.0 | 2026-09-11 | E. Crespo / Claude | Versión inicial (DRAFT) |
| 1.1 | 2026-09-11 | Claude | Analyze A-07: prerequisito de tooling JS |
