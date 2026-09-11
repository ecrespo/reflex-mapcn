# Propuesta — `filter` en `map_heatmap_layer`

| Campo | Valor |
|---|---|
| **Autor** | Ernesto Crespo / Claude |
| **Fecha** | 2026-09-11 |
| **Estado** | `APPROVED` — aprobado por E. Crespo el 2026-09-11 |
| **Afecta a** | PRD `mapcn-layers-0.2.md` (F3, F6), API Spec §3.3, Tasks T-009 y T-017 |
| **Detectado en** | T-009 (implementación del mapa de calor), confirmado al planificar T-017 |

## Problema

`REQ-SIS-008` exige que el interruptor "Densidad" muestre `map_heatmap_layer`
**alimentado por el mismo histórico filtrado**. Con la especificación aprobada
eso no se puede implementar:

1. El API Spec §3.3 no da prop `filter` a `map_heatmap_layer`; sus props son
   `data`, `weight`, `intensity`, `radius`, `color`, `opacity`, `max_zoom_fade`,
   `before_id` y `visible`.
2. `DD-006` (Tech Design) decide que el histórico completo viaja **una vez** al
   cliente y que los filtros se aplican allí con `setFilter`, y descarta
   explícitamente "filtrar en Python y reenviar la colección (400 KB por tick,
   inaceptable)".

La única forma de cumplir `REQ-SIS-008` sin romper `DD-006` es filtrar la capa
de calor en el cliente, y para eso necesita la prop.

## Evidencia

- `REQ-SIS-004` exige que el filtro temporal se aplique en < 100 ms sin ir al
  backend. La capa de puntos ya lo hace con `filter`.
- Sin filtro, la mancha de densidad ignoraría los tres deslizadores mientras
  los puntos responden a ellos: la página se contradice a sí misma.
- El runtime de capas (`useMapLayer`, T-003) ya aplica `filter` en caliente con
  `setFilter` para cualquier capa; el mapa de calor simplemente no lo expone.
  El coste de implementación es una prop y su test.

## Opciones consideradas

| Opción | Pros | Contras |
|---|---|---|
| **A. Añadir `filter` al mapa de calor (elegida)** | Coherente con las capas de puntos; el runtime ya lo soporta; cumple REQ-SIS-008 y DD-006 | Amplía la superficie pública del componente |
| B. Dejar el mapa de calor sin filtrar | Cero cambios de spec | Incumple REQ-SIS-008; la página queda incoherente |
| C. Filtrar en el backend y reenviar la colección | Cero cambios de API | Viola DD-006 explícitamente; 400 KB por movimiento del deslizador |

## Recomendación

Opción A. Es aditiva (SemVer minor, sin cambio de firma para nadie), alinea el
mapa de calor con `map_circle_layer` y `map_symbol_layer`, y desbloquea T-017.

## Aprobación

| Rol | Nombre | Fecha | Estado |
|---|---|---|---|
| Product owner / Tech lead | Ernesto Crespo | 2026-09-11 | ☑ Aprobado (opción A) |
