# Delta Spec — `filter` en `map_heatmap_layer`

> Cambios exactos sobre los artefactos aprobados. Al implementarse se pliegan a
> `docs/specs/` y este documento queda como registro histórico.

## 1. PRD (`docs/specs/prd/mapcn-layers-0.2.md`)

**Añadir** en F3:

- **REQ-HEA-007** (opcional): DONDE se pase `filter` (expresión MapLibre), EL
  SISTEMA DEBERÁ aplicarlo a la capa de calor con `setFilter` sin recrear la
  fuente, con la misma semántica que `REQ-LAY-004`. MUST

Sin cambios en REQ-HEA-001..006 ni en REQ-SIS-008.

## 2. API Spec (`docs/specs/api/mapcn-components-api-v0.2.md` §3.3)

**Añadir** a la tabla de props de `map_heatmap_layer`:

| Prop Python | Tipo | Default | MapLibre |
|---|---|---|---|
| `filter` | `list` | — | `filter` (caliente) |
| `min_zoom` / `max_zoom` | `float` | — | `minzoom`/`maxzoom` (calientes) |

`min_zoom`/`max_zoom` se documentan porque ya estaban implementados y son
comunes a todas las capas; la omisión en el borrador era un descuido de
redacción, no una decisión.

## 3. Data Model (`docs/specs/data-model/mapcn-layers-schema.md` §2.1)

Sin cambios: `filter` y `zoomRange` ya figuran como campos calientes de
`LayerSpec`, y el mapa de calor pasa a incluirlos en sus `hotKeys`.

## 4. Tech Design

Sin cambios. `DD-006` se refuerza: el filtrado en cliente pasa a aplicarse
también a la capa de densidad.

## 5. Trazabilidad

| REQ | Tarea | Test |
|---|---|---|
| REQ-HEA-007 | T-009 (ampliada), T-017 | `test_REQ_HEA_007_filter_prop_reaches_the_layer` (py), `REQ-HEA-007: a new filter is applied without a rebuild` (js) |

## 6. Impacto

- **Compatibilidad:** aditivo. Ningún usuario de 0.1.0 o del borrador de 0.2.0
  ve un cambio de firma. SemVer: sigue siendo 0.2.0.
- **Riesgo:** bajo. El runtime ya aplica `filter` en caliente y está probado.
