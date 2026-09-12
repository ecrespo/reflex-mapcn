# Tasks — Delta `filter` en `map_heatmap_layer`

### D-001 · Prop `filter` en `map_heatmap_layer` — `[x] 2026-09-11`
- **Qué:** añadir `filter` a `HeatmapLayer` (JSX) y a `MapHeatmapLayer` (Python);
  incluir `filter` en los `hotKeys` de la capa; documentar en el README.
- **REQ:** REQ-HEA-007
- **Tests:** `test_REQ_HEA_007_filter_prop_reaches_the_layer` (py),
  `REQ-HEA-007: a new filter is applied without a rebuild` (js).
- **Done:** pytest y `bash tests/js/run.sh` en verde.

### D-002 · Plegar el Delta a las specs — `[x] 2026-09-11`
- **Qué:** REQ-HEA-007 en el PRD, props en el API Spec §3.3, fila en la matriz
  de trazabilidad de Tasks.
- **Done:** `git diff docs/specs` refleja los tres cambios.
