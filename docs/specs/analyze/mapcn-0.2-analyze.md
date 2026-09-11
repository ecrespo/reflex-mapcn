# Analyze — reflex-mapcn 0.2.0 · 2026-09-11

> Validación cruzada de solo lectura sobre: constitución v1.0, PRD v1.0, API Spec 0.2.0-draft, Tech Design v1.0, Data Model v1.0, Plan v1.0, Tasks (borrador). Los hallazgos con "Aplicado" se corrigieron en una segunda pasada (PRD v1.1, API draft.2, Data Model v1.1, Plan v1.1, Tasks); el resto queda para decisión humana.

## Hallazgos

| # | Severidad | Categoría | Hallazgo | Artefactos | Sugerencia | Estado |
|---|---|---|---|---|---|---|
| A-01 | ALTO | Terminología / Cobertura | REQ-RAS-006 decía que el componente recibe el `path` del frame RainViewer, mientras el API Spec exige `tiles` calculado con `rainviewer_tiles()`. Un agente implementaría dos contratos. | PRD, API | Unificar: el componente solo recibe `tiles`; el preset aporta `tile_size`/`max_zoom`/atribución | **Aplicado** (PRD v1.1) |
| A-02 | ALTO | No felices / Rendimiento | REQ-SIS-007 usaba el feed global `all_month.geojson` (≈ 8–10 k eventos mundiales, varios MB) cada 60 s y recortaba en backend: coste innecesario y riesgo de throttling. | PRD, API §5.1, Data Model §6 | Usar FDSN `query` con bbox de Venezuela, `minmagnitude=2.5`, `starttime=now−30d` | **Aplicado** (PRD v1.1, API, Data Model, Tasks T-014/T-017) |
| A-03 | ALTO | No felices | `map_layer` con `source` como id de fuente inexistente no tenía criterio SI…ENTONCES; MapLibre lanza error en `addLayer` y la capa se pierde en silencio. | PRD F2, Tech §3.4 | Nuevo REQ-LAY-010 (omitir + warn + reintento tras `style.load`) | **Aplicado** |
| A-04 | ALTO | No felices | Fallo de `loadImage` en `map_symbol_layer` estaba en Tech Design §3.4 pero sin REQ, por lo que no tenía tarea ni test. | PRD F4, Tech | Nuevo REQ-PNT-010 | **Aplicado** (+ T-011, matriz) |
| A-05 | MEDIO | No felices | Sin criterio para fallo de teselas DEM en `map_terrain`. | PRD F5 | Nuevo REQ-TER-009 (SHOULD) reutilizando el contrato de `on_load_error` | **Aplicado** |
| A-06 | MEDIO | Ambigüedad | `LayerSpec.hotKeys` aparecía en el Data Model sin definición de semántica. | Data Model §2.1 | Definir: grupos de props que sincroniza el efecto caliente | **Aplicado** |
| A-07 | MEDIO | Ejecutabilidad | El plan asume `bun`, Node y Playwright/Chromium en la máquina del dev para `tests/js`, pero no estaba en pre-requisitos. | Plan §2 | Añadir pre-requisito de tooling | **Aplicado** |
| A-08 | MEDIO | Cobertura | REQ-SIS-004 "< 100 ms" y REQ-PNT-007 "≥ 30 fps" solo se verifican manualmente (T-020). Aceptable para una demo, pero el Analyze debe dejar constancia de que no hay test automatizado. | PRD, Tasks | Registrar la medición (DevTools Performance) en el registro de ejecución de T-020; considerar test Playwright con `performance.now()` en 0.3 | Pendiente (decisión humana) |
| A-09 | MEDIO | Consistencia | `LayerFeatureEvent` (0.2) y `MapGeoJSONEvent` (0.1.0) tienen la misma forma con nombres distintos. | API §2.3, `mapcn.py` | En T-013 exportar `LayerFeatureEvent` como alias de `MapGeoJSONEvent` (mismo TypedDict) y documentar | **Aplicado** (T-008, 2026-09-11) |
| A-10 | MEDIO | Datos | Caché TTL en memoria de proceso: con varios workers de backend cada uno consulta USGS por separado. Documentado en Data Model §6 como aceptable para la demo. | Data Model §6 | Mantener; si la demo se despliega con >1 worker, mover a Redis (Reflex ya lo soporta) — abrir Delta entonces | Pendiente (aceptado) |
| A-11 | BAJO | Terminología | "capa de puntos" (PRD) vs "point layers" (Tech) vs `map_circle_layer`/`map_symbol_layer` (API): consistente en identificadores; el término genérico varía por idioma (Art. 9). | PRD, Tech | Sin acción | Cerrado |
| A-12 | BAJO | Datos | El histórico USGS anterior a 1973 es incompleto para Venezuela (solo grandes eventos); el slider desde 1900 puede sugerir ausencia de actividad. | PRD REQ-SIS-004 | Mostrar nota en el panel: "Catálogo USGS: completo aprox. desde 1973 para M ≥ 4.5" | Pendiente (recomendado, sin REQ nuevo; texto de UI) |
| A-13 | BAJO | Constitución | Art. 3 (una sola dependencia npm) vs. tooling de tests (bun/playwright): son dependencias de desarrollo, no del paquete. | Constitución, Plan | Aclarar en Art. 3 "en el paquete publicado" en la próxima enmienda | Pendiente (enmienda menor) |
| A-14 | BAJO | Ejecutabilidad | T-015 (script GEM) requiere red y el repo GEM usa Git LFS; desde el sandbox de Cowork no fue posible descargarlo. | Tasks T-015 | Ejecutar T-015 en la máquina del dev; si LFS falla, usar la release ZIP del repo GEM | **Resuelto** (2026-09-11): el GeoJSON se sirve por raw.githubusercontent sin LFS (10,6 MB) |

## Verificaciones de cobertura

- **MUST → tarea → test:** 100 % tras A-03/A-04 (ver matriz en Tasks). 0 REQ fantasma; 0 tareas huérfanas (T-001/T-002 citan artículos de la constitución, permitido para infraestructura).
- **API ↔ Tech ↔ Data:** todos los componentes del API Spec aparecen en Tech §3.2 y §5.1; `LayerSpec`, presets, `SeismicFeature`, `TravelMatrix`, `RainViewerFrames` definidos en Data Model; caché con claves alineadas a las firmas (tras A-02).
- **Plan ↔ Tasks:** las 24 tareas del plan (F1-01…F4-05) están cubiertas por T-001…T-022 (F1-04 = T-002; F2-09 = T-013; F3-06 = T-019).
- **Constitución:** sin contradicciones; A-13 es una aclaración de redacción.
- **Ambigüedad:** todos los criterios nombran un resultado observable; límites con unidad (10 s, 15 s, 60 s, 400 KB, 300 KB, 100 ms, 30 fps, 25 destinos, zoom 7/15).
- **No felices:** cada integración externa tiene SI…ENTONCES (RAS-007/010/011, LAY-008/010, PNT-004/010, TER-007/009, SIS-003, TVJ-002).
- **Tasks:** sin ciclos; `[P]` solo en tareas sin archivos comunes; primera tanda T-001…T-005 identificada.

## Veredicto

**LISTO PARA IMPLEMENTAR** tras la aprobación humana de los artefactos (los hallazgos ALTO/MEDIO bloqueantes se aplicaron; A-08, A-09, A-10, A-12, A-13, A-14 son decisiones o notas operativas que no bloquean la primera tanda).

Regla final: el Analyze no aprueba nada — presenta hallazgos. La aprobación es humana (tabla de aprobaciones del PRD).
