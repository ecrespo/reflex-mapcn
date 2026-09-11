# reflex-mapcn — agent instructions

Read `docs/specs/constitution.md` first: it holds the non-negotiable project rules (mapcn API parity, JSON-serialisable event payloads, single npm dependency, client-only components with deterministic cleanup, external data only from the app backend, REQ-traceable tests, SemVer, spec-before-code, English for code/docs and Spanish for `docs/specs`).

Current work is specified under `docs/specs/` (SDD, spec-anchored). Before implementing anything ≥ a medium feature, make sure the relevant PRD/API/Tech/Data/Plan are `APPROVED` and execute `docs/specs/tasks/*.md` in batches of 3–5 tasks, citing `REQ-*` ids in tests. If the spec turns out to be wrong, stop and open a Delta Spec in `docs/changes/` instead of diverging silently.

Layout: package in `custom_components/reflex_mapcn/` (`mapcn.py`, `mapcn.jsx`, `mapcn.css`), demo app in `mapcn_demo/`, tests in `tests/`. Use `uv` for the environment and `uv run reflex component build` to regenerate `.pyi` stubs before a release.
