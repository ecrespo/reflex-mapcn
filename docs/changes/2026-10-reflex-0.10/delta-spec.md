# Delta Spec — Migración a Reflex 0.10

> Cambios exactos sobre los artefactos aprobados. Al implementarse se pliegan a
> `docs/specs/` y este documento queda como registro histórico.

## 1. Constitución (`docs/specs/constitution.md`)

**Modificar** Art. 7:

- Antes: "EL SISTEMA DEBERÁ mantener `reflex>=0.8.1` como mínimo soportado, …"
- Después: "EL SISTEMA DEBERÁ mantener `reflex>=0.10.0` como mínimo soportado, …"

**Modificar** Restricciones del stack:

| Área | Antes | Después |
|---|---|---|
| Lenguaje backend | Python ≥ 3.10 (soporte 3.10–3.13) | Python ≥ 3.11 (soporte 3.11–3.13) |
| Framework | Reflex ≥ 0.8.1 (probado con 0.9.x) | Reflex ≥ 0.10.0 (probado con 0.10.0) |
| Empaquetado | `reflex component build` para `.pyi` | `python -m reflex_base.utils.pyi_generator` para `.pyi`; `uv build` para las distribuciones |

**Añadir** fila en Enmiendas (versión 1.1).

## 2. Requisitos de compatibilidad (nuevos)

- **REQ-CMP-001**: EL SISTEMA DEBERÁ declarar `reflex>=0.10.0` en
  `[project].dependencies` y en `mapcn_demo/requirements.txt`. MUST
- **REQ-CMP-002**: EL SISTEMA DEBERÁ declarar `requires-python = ">=3.11"` y
  los clasificadores `Programming Language :: Python :: 3.11` a `3.13`, y la
  matriz de CI DEBERÁ ejecutar exactamente esas versiones. MUST
- **REQ-CMP-003**: CUANDO cambie `mapcn.py`, EL SISTEMA DEBERÁ fallar en CI si
  el `mapcn.pyi` generado con `reflex_base.utils.pyi_generator` difiere del
  versionado. MUST

## 3. PRD, API Spec, Data Model, Tech Design

Sin cambios. Ningún componente, prop, evento ni payload cambia. La línea
"Reflex ≥ 0.8.1" del PRD 0.2 (§ dependencias) queda como registro histórico de
esa release.

## 4. Trazabilidad

| REQ | Test / verificación |
|---|---|
| REQ-CMP-001 | `tests/test_packaging.py::test_REQ_CMP_001_reflex_floor_is_0_10` |
| REQ-CMP-002 | `tests/test_packaging.py::test_REQ_CMP_002_python_floor_matches_the_classifiers`; matriz de `ci.yml` |
| REQ-CMP-003 | Paso "Fail if the committed type stubs are stale" de `ci.yml` |
