# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html), as required by
article 7 of `docs/specs/constitution.md`.

## [Unreleased]

## [0.2.0] - 2026-09-12

Six new layer components, the presets and helpers they need, and a demo that
exercises every one of them against live data.

### Added

- `map_raster_layer`: any XYZ or TileJSON service on top of the basemap, with
  presets for OpenRailwayMap, OpenSeaMap, Esri World Imagery and RainViewer,
  hot updates of opacity, visibility and zoom range, and `on_load_error` for a
  service that stops answering.
- `map_layer`: the escape hatch. Any MapLibre layer spec over a source of your
  own or one the style already provides, with hover paint and feature events.
- `map_heatmap_layer`, with `weight_property`, `max_zoom_fade` and `filter`.
- `map_circle_layer` and `map_symbol_layer`, including native clustering,
  images loaded and removed with the layer, and labels that degrade to a
  console warning when the style declares no glyphs.
- `map_terrain`: raster-dem terrain with optional hillshade, one per map,
  restored after a style change and switched off on unmount.
- `Map.glyphs_url`, so labels work on the blank basemap.
- `reflex_mapcn.presets` with the tile and terrain presets, each carrying the
  attribution its licence requires, and `reflex_mapcn.helpers` with
  `interpolate`, `step`, `match`, `zoom_interpolate` and the RainViewer radar
  helpers.
- A demo page per feature, including the seismic history of Venezuela from the
  USGS catalogue and driving times between state capitals through OSRM.

### Fixed

- A height or width given to `map` itself is no longer ignored. The stylesheet
  set the size on `.mapcn-map`, which has the same weight as the class Reflex
  compiles a `height=` prop into, so the default won and the map collapsed to
  nothing whenever its parent had no height of its own. The default now sits in
  a `:where()` rule, which weighs nothing.

### Infrastructure

- Continuous integration on every push and pull request to `develop` and `main`:
  ruff, byte-compilation, the test suite on Python 3.10 through 3.13, a package
  build that rejects stale type stubs and invalid trove classifiers, and a
  clean-environment install of the built wheel.
- Security gates in the same run: gitleaks over the full history, bandit and
  semgrep for static analysis, pip-audit over the locked runtime dependencies,
  and a trivy filesystem scan. CodeQL runs alongside them and weekly.
- Release automation. Pushing a `v*` tag verifies that the tag matches the
  declared version, that its commit is on `main`, and that the version is not
  already on PyPI, then re-runs the full gate before publishing through PyPI
  trusted publishing and attaching the artifacts to the GitHub release.
- `scripts/check_metadata.py`, which validates trove classifiers and the
  tag-to-version match locally before tagging.
- Spec-driven design documents under `docs/`, including the project
  constitution and the 0.2.0 specification set.

## [0.1.0] - 2026-09-11

First public release.

### Added

- `reflex_mapcn`, a self-contained port of the mapcn map module exposed as
  Reflex components: map, markers, popups, controls, routes, arcs, GeoJSON
  layers and native clustering.
- `map_camera`, a Reflex extra for driving `flyTo`, `easeTo`, `jumpTo` and
  `fitBounds` from state.
- A CARTO basemap that follows Reflex's light and dark color mode, with support
  for custom styles, a blank basemap and globe projection.
- `mapcn_demo`, a Reflex demo application with one page per feature, including
  a Venezuela state map backed by a bundled GeoJSON.
- Type stubs and a `py.typed` marker, so editors autocomplete every prop.

[Unreleased]: https://github.com/ecrespo/reflex-mapcn/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/ecrespo/reflex-mapcn/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ecrespo/reflex-mapcn/releases/tag/v0.1.0
