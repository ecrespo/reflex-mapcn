# Tasks — Delta recorte del histórico sísmico

### D-003 · Recortar el histórico y subir el mínimo por defecto — `[x] 2026-09-12`
- **Qué:** en `services/usgs.py`, `fetch_catalog(min_magnitude=4.5)` y `_trim`
  sin `url`, sin `id` de feature y sin `recent` cuando no se marca lo reciente;
  en `pages/sismos.py`, reconstruir el enlace de la ficha desde el id.
- **REQ:** REQ-SIS-001, REQ-SIS-006, REQ-SIS-007, RNF de tamaño
- **Tests:** los cinco de la matriz del Delta.
- **Done:** pytest en verde y el histórico por debajo de 400 KB medido en el
  websocket.

### D-004 · Plegar el Delta a las specs — `[x] 2026-09-12`
- **Qué:** API Spec §5.1, Data Model §3.2 y §6, nota de compresión en el Tech
  Design, fila en `docs/changes/README.md`, cierre de H-03 en T-020.
- **Done:** `git diff docs/specs` refleja los cambios y H-03 queda cerrado.


## Resultado

1 621 eventos y 335,4 KB en el fotograma del websocket, medidos en la app el 2026-09-12, frente a 3 555 eventos y 1 089 KB antes del cambio. La ficha del USGS se abre desde el popup con la url reconstruida.
