# changes/

Propuestas activas (Delta Specs). Estructura por cambio: `YYYY-MM-slug/proposal.md`, `delta-spec.md`, `tasks.md`. Vacío mientras no haya cambios sobre features ya especificadas.

| Cambio | Estado | Resumen |
|---|---|---|
| `2026-09-catalog-payload/` | Aprobado e implementado (2026-09-12) | Histórico sísmico a M ≥ 4,5 y sin `url`, id duplicado ni `recent`: con el esquema aprobado pesaba 1 089 KB contra un presupuesto de 400 KB. Detectado en T-020 (H-03). |
| `2026-09-heatmap-filter/` | Aprobado e implementado (2026-09-11) | `filter` en `map_heatmap_layer`: sin él, REQ-SIS-008 (densidad filtrada) contradecía DD-006 (no reenviar la colección). Plegado a PRD (REQ-HEA-007) y API Spec §3.3. |
