# Delta Spec — recorte del histórico sísmico

> Cambios exactos sobre los artefactos aprobados. Al implementarse se pliegan a
> `docs/specs/` y este documento queda como registro histórico.

## 1. API Spec (`docs/specs/api/mapcn-components-api-v0.2.md` §5.1)

**Cambiar** la firma de `fetch_catalog`:

```python
async def fetch_catalog(*, min_magnitude: float = 4.5, start: str = "1900-01-01", ...)
```

El parámetro sigue existiendo y una app puede pedir 4.0; solo cambia el valor
por defecto. `fetch_live` conserva `min_magnitude=2.5`.

**Añadir** bajo la firma: el histórico no incluye `url` ni `recent`. Ninguna
feature recortada, ni del histórico ni del feed en vivo, lleva `id` de nivel de
feature: `properties.id` es la clave, que es lo que `promote_id="id"` promociona.

## 2. Data Model (`docs/specs/data-model/mapcn-layers-schema.md` §3.2)

**Cambiar** la tabla de `SeismicFeature`:

| Campo | Antes | Ahora |
|---|---|---|
| `url` | str, presente | **retirado**; la ficha se reconstruye con `https://earthquake.usgs.gov/earthquakes/eventpage/{id}` |
| `recent` | bool, presente en ambos feeds | solo en el feed en vivo |
| `id` de la feature | duplicado de `properties.id` | **retirado** en ambos feeds; solo `properties.id` |

Sin cambios en `mag`, `magType`, `depth`, `time`, `place`, `depth_unknown` ni en
la geometría.

**Cambiar** §6, fila `usgs:catalog:...`: tamaño esperado `≤ 400 KB` se mantiene
como presupuesto, y ahora se cumple (~340 KB medidos con M ≥ 4,5).

## 3. Tech Design (`docs/specs/technical/mapcn-layers-architecture.md`)

§1 y §98: el presupuesto de 400 KB se mantiene sin cambios. Se añade la nota de
que el websocket de Reflex no negocia compresión, de modo que el presupuesto se
mide sobre el dato en claro.

## 4. PRD

Sin cambios. REQ-SIS-001 no fija la magnitud mínima del catálogo; la nota de
cobertura de REQ-SIS-004 ya decía que el catálogo es fiable desde M ≥ 4,5.

## 5. Trazabilidad

| REQ | Tests |
|---|---|
| REQ-SIS-001 | `test_REQ_SIS_001_the_catalog_defaults_to_the_reliable_threshold` (py) |
| REQ-SIS-001 | `test_REQ_SIS_001_the_history_drops_what_it_can_rebuild` (py) |
| REQ-SIS-007 | `test_REQ_SIS_007_the_live_feed_keeps_the_recent_flag` (py) |
| REQ-SIS-006 | `test_REQ_SIS_006_the_event_page_is_rebuilt_from_the_id` (py) |
| RNF tamaño | `test_the_history_fits_the_network_budget` (py, sobre la fixture) |
