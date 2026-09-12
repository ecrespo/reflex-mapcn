# Propuesta — recortar el histórico sísmico al presupuesto de red

| Campo | Valor |
|---|---|
| **Autor** | Ernesto Crespo / Claude |
| **Fecha** | 2026-09-12 |
| **Estado** | `APPROVED` — aprobado por E. Crespo el 2026-09-12 (opción 1 de tres) |
| **Afecta a** | Data Model §3.2 y §6, API Spec §5.1, Tech Design §1 y §4, Tasks T-014 y T-016 |
| **Detectado en** | T-020 (revisión E2E), hallazgo H-03 |

## Problema

El Tech Design §1 fija un presupuesto de **400 KB** para el histórico que viaja
al navegador, y el Data Model §6 lo repite en la tabla de caché. La
implementación aprobada no lo cumple: el catálogo real pesa **1 089 KB** al
cruzar el websocket.

No es una desviación de la implementación respecto a la spec, sino una
contradicción entre dos partes aprobadas: con el esquema de `SeismicFeature`
del Data Model §3.2 y el mínimo de magnitud del API Spec §5.1
(`min_magnitude=4.0`), el resultado no cabe en 400 KB. Una de las dos tiene que
ceder.

## Evidencia

Medido el 2026-09-12 sobre la respuesta real del USGS (3 555 eventos desde
1900, M ≥ 4,0, caja de Venezuela), en el fotograma del websocket y con el
reparto calculado propiedad a propiedad:

| Concepto | Peso |
|---|---|
| Total en red | 1 089 KB |
| `url` | 236 KB |
| Geometría | 162 KB |
| `place` | 151 KB |
| `id` (duplicado: en la feature y en las propiedades) | 118 KB |
| `time` | 68 KB |
| `magType` | 49 KB |
| `recent` (siempre `false` en el histórico) | 49 KB |
| `depth` | 43 KB |
| `mag` | 31 KB |

El transporte no negocia compresión (`sec-websocket-extensions: none`), así que
el dato viaja en claro; comprimido serían 131 KB, pero eso no está bajo el
control de la aplicación.

Opciones medidas:

| Opción | Peso |
|---|---|
| Como está | 1 089 KB |
| Sin `url` | 859 KB |
| Sin `url`, sin el id duplicado y sin `recent` | 744 KB |
| Lo anterior más `place` | 590 KB |
| M ≥ 4,5 con el esquema actual (1 621 eventos) | 501 KB |
| **M ≥ 4,5 más el recorte de `url`, id duplicado y `recent`** | **~340 KB** |

## Propuesta

Subir el mínimo por defecto del catálogo histórico a **M ≥ 4,5** y retirar del
histórico tres campos que no aportan información: `url` (se reconstruye desde
`id`), el `id` de nivel de feature (duplicado de `properties.id`, que es el que
usa `promote_id`) y `recent` (que solo tiene sentido en el feed en vivo).

El 4,5 no es un número arbitrario: la propia página ya advierte que el catálogo
del USGS solo es completo para Venezuela desde ~1973 a partir de esa magnitud
(hallazgo A-12 del Analyze). El valor por defecto pasa a coincidir con el rango
en el que el dato es fiable.

## Alternativas descartadas

- **Solo recortar propiedades, manteniendo M ≥ 4,0:** deja 744 KB, o 590 KB si
  además se quita `place`, que el popup muestra. Seguiría fuera de presupuesto
  y habría que subir el listón de todas formas.
- **Aceptar el tamaño y subir el presupuesto a 1,1 MB:** documentar que en
  producción conviene activar compresión en el websocket. Rechazada: el
  presupuesto existe porque la demo se abre desde conexiones cualesquiera, y
  1 MB en un solo fotograma es un segundo largo en una red lenta.
