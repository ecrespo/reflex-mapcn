# docs/ — Spec-Driven Design de reflex-mapcn

Este directorio contiene las especificaciones del proyecto siguiendo Spec-Driven Design (nivel **spec-anchored**): `docs/specs/` es la verdad actual y se versiona con el código; los cambios a features ya publicadas entran como propuestas en `docs/changes/` y, al aprobarse e implementarse, se pliegan a `docs/specs/`.

## Estructura

```
docs/
├── README.md                                   ← este archivo
├── specs/
│   ├── constitution.md                         ← principios no negociables (1 vez por proyecto)
│   ├── prd/mapcn-layers-0.2.md                 ← qué construir (EARS, REQ-*)
│   ├── api/mapcn-components-api-v0.2.md        ← contrato: props, eventos, presets, helpers, servicios
│   ├── technical/mapcn-layers-architecture.md  ← cómo: useMapLayer, decisiones DD-*
│   ├── data-model/mapcn-layers-schema.md       ← esquemas JSON, estado, caché
│   ├── plans/mapcn-0.2-implementation-plan.md  ← fases y dependencias
│   ├── tasks/mapcn-0.2-tasks.md                ← tareas ejecutables T-* con matriz REQ→test
│   └── analyze/mapcn-0.2-analyze.md            ← validación cruzada y veredicto
└── changes/                                    ← propuestas (Delta Specs) — vacío por ahora
```

## Release 0.2.0 — las seis funcionalidades

| # | Feature | Componente / entregable | REQ |
|---|---|---|---|
| F1 | Capas raster de teselas (RainViewer, OpenRailwayMap, OpenSeaMap, satélite, tráfico con key) | `map_raster_layer` + presets + `rainviewer_*` | `REQ-RAS-*` |
| F2 | Capa MapLibre genérica | `map_layer` | `REQ-LAY-*` |
| F3 | Mapa de calor | `map_heatmap_layer` | `REQ-HEA-*` |
| F4 | Capas de puntos GPU (círculos por datos, iconos/texto) | `map_circle_layer`, `map_symbol_layer`, `Map.glyphs_url` | `REQ-PNT-*` |
| F5 | Terreno 3D e hillshade | `map_terrain` | `REQ-TER-*` |
| F6 | Demo Sismos de Venezuela (USGS histórico + en vivo, fallas GEM, línea de tiempo) y tiempos de viaje OSRM | `/sismos`, `services/usgs.py`, `services/osrm.py`, `assets/venezuela_fallas.geojson` | `REQ-SIS-*`, `REQ-TVJ-*` |

## Flujo de trabajo

1. **Revisar y aprobar** cada artefacto en orden (checkpoints): PRD → API → Tech → Data → Plan → Tasks. Marcar `APPROVED` en su tabla de metadata y firmar la tabla de aprobaciones del PRD.
2. **Analyze** ya ejecutado (`specs/analyze/`): los hallazgos bloqueantes se aplicaron; decidir sobre A-08…A-14.
3. **Implementar** con las Tasks por tandas de 3–5 (primera tanda: T-001…T-005), marcando progreso en el propio archivo. Prompt sugerido para Claude Code:
   > Lee `docs/specs/constitution.md` y `docs/specs/tasks/mapcn-0.2-tasks.md`. Ejecuta la primera tanda (T-001..T-005) respetando dependencias y `[P]`. Para cada tarea cita los REQ, escribe los tests con el REQ en el nombre, muestra la salida de `pytest` y de `bash tests/js/run.sh`, y marca `[x] fecha` en el archivo de tasks. Detente al terminar la tanda para revisión.
4. Si al implementar la spec resulta incorrecta: **parar**, abrir un Delta en `docs/changes/YYYY-MM-slug/` (plantilla del skill `spec-driven-design`), y seguir solo tras aprobarlo.
5. Al cerrar 0.2.0: plegar estados (`IMPLEMENTED`), registro de ejecución en Tasks, CHANGELOG.

## Trazabilidad

`REQ-XXX-NNN` (PRD) → `T-NNN` (Tasks) → `test_REQ_XXX_NNN_*` (tests). La matriz completa está al final de `tasks/mapcn-0.2-tasks.md`.
