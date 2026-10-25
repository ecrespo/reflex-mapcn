# Tasks — Delta Migración a Reflex 0.10

### D-001 · Subir dependencias y CI — `[x] 2026-10-24`
- **Qué:** `reflex>=0.10.0` y `requires-python = ">=3.11"` en `pyproject.toml`,
  `setuptools>=78.1.1` en `build-system`, `uv.lock` regenerado, quitar 3.10 de
  los clasificadores y de la matriz de `ci.yml`, sustituir
  `reflex component build` por `reflex_base.utils.pyi_generator` + `uv build`,
  ruff `target-version = "py311"`.
- **REQ:** REQ-CMP-001, REQ-CMP-002, REQ-CMP-003
- **Tests:** `test_REQ_CMP_001_*`, `test_REQ_CMP_002_*` (py).
- **Done:** pytest, `bash tests/js/run.sh`, `scripts/compile_check.py`,
  `reflex run` de la demo y `twine check` en verde; stubs sin diff.

### D-002 · Plegar el Delta y documentar — `[x] 2026-10-24`
- **Qué:** constitución 1.1 (Art. 7, stack, enmiendas), README (requisitos de
  instalación, flujo de desarrollo, matriz), `CLAUDE.md`, comentarios que
  citaban `reflex component build`, CHANGELOG 0.3.0.
- **Done:** `git grep "component build"` solo aparece en registros históricos.

### D-003 · Release 0.3.0 — `[x] 2026-10-24`
- **Qué:** versión 0.3.0 en `pyproject.toml` y `__version__`; PR `develop` →
  `main` con CI en verde; etiqueta `v0.3.0` sobre el merge; `release.yml`
  publica en PyPI con trusted publishing.
- **Done:** `https://pypi.org/project/reflex-mapcn/0.3.0/` responde 200 y la
  release de GitHub tiene los artefactos.
- **Registro:** PR #9 a `main` con todas las comprobaciones en verde tras
  retirar una variable sin uso en `tests/js/preview.mjs` que CodeQL señaló.
  Etiqueta `v0.3.0` sobre el commit de merge `0e2084d`; `release.yml` verificó
  la etiqueta, repitió el CI completo, publicó en PyPI por trusted publishing y
  adjuntó wheel y sdist a la release de GitHub. Un entorno limpio instala
  `reflex-mapcn==0.3.0` desde PyPI junto con `reflex` 0.10.0.
