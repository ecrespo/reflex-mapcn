# Propuesta — Migración a Reflex 0.10

| Campo | Valor |
|---|---|
| **Autor** | Ernesto Crespo / Claude |
| **Fecha** | 2026-10-24 |
| **Estado** | `APPROVED` — solicitado y aprobado por E. Crespo el 2026-10-24 |
| **Afecta a** | Constitución (Art. 7, Restricciones del stack), `pyproject.toml`, `ci.yml`, README, CHANGELOG |
| **Detectado en** | Actualización de dependencias (`uv lock --upgrade`) a Reflex 0.10.0 |

## Problema

Reflex 0.10.0 es la versión estable actual y la que el proyecto debe usar.
Con la especificación aprobada no se puede adoptar sin divergir de ella:

1. El Art. 7 de la constitución fija `reflex>=0.8.1` como mínimo y la tabla
   del stack declara Python ≥ 3.10 (soporte 3.10–3.13). Reflex 0.10 publica
   `requires-python = ">=3.11"`: con 3.10 en la matriz, `uv lock` no resuelve.
2. La tabla del stack fija `reflex component build` para generar los `.pyi`.
   Reflex 0.10 eliminó el subcomando `reflex component` completo
   (`init`, `build`, `publish`, `share`).

## Evidencia

- `https://pypi.org/pypi/reflex/json`: versión `0.10.0`, `requires_python`
  `<4.0,>=3.11`.
- `uv run reflex component --help` con 0.10.0: "`reflex component` was removed
  in Reflex 0.10".
- El generador de stubs sigue disponible como módulo:
  `python -m reflex_base.utils.pyi_generator custom_components/reflex_mapcn`
  produce un `mapcn.pyi` idéntico al publicado en 0.2.0.
- Con 0.10.0: 206 tests Python, 59 tests JSX y las 12 páginas de la demo en
  verde; `reflex run` arranca la demo sin avisos.

## Opciones consideradas

| Opción | Pros | Contras |
|---|---|---|
| **A. Subir el mínimo a `reflex>=0.10.0` y Python ≥ 3.11 (elegida)** | Usa la versión actual; un único camino de generación de stubs; CI reproducible | Las apps en Python 3.10 o Reflex < 0.10 se quedan en 0.2.x |
| B. Mantener `reflex>=0.8.1` y probar ambas ramas | Compatibilidad amplia | Dos generadores de stubs distintos; matriz doble; 0.8/0.9 ya no reciben correcciones |
| C. No actualizar | Cero cambios | Contradice el requisito de usar la última versión de Reflex |

## Recomendación

Opción A. La API pública no cambia (ningún componente, prop ni evento), así que
según el Art. 7 basta una minor: **0.3.0**. La subida del mínimo de Python y de
Reflex se anuncia en el CHANGELOG bajo *Changed* / *Removed*.

## Aprobación

| Rol | Nombre | Fecha | Estado |
|---|---|---|---|
| Product owner / Tech lead | Ernesto Crespo | 2026-10-24 | ☑ Aprobado (opción A) |
