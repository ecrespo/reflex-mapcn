# reflex-mapcn

[mapcn](https://www.mapcn.dev) map components for [Reflex](https://reflex.dev).

mapcn is a set of beautifully designed, MapLibre GL powered map components
(map, markers, popups, controls, routes, arcs, GeoJSON layers and clusters)
originally distributed as a shadcn/ui registry item. `reflex-mapcn` ships a
self-contained port of that component and exposes every piece as a Reflex
component, so you can build interactive maps in pure Python.

- Free CARTO basemap that follows Reflex's light/dark color mode automatically
- Markers with content, tooltips, popups, labels and dragging
- Standalone popups, zoom / compass / locate / fullscreen controls
- Routes with progress tracking and route-anchored markers
- Curved arcs, GeoJSON fill/outline layers with hover state, native clustering
- Controlled viewport, globe projection, custom styles and a blank basemap
- Every callback delivers JSON-serialisable payloads for Reflex event handlers
- Extras for Reflex: `map_camera` (flyTo / easeTo / fitBounds from state),
  `on_click`, `on_move_end` and `on_load` on the map

## Installation

```bash
pip install reflex-mapcn
```

The only npm dependency (`maplibre-gl`) is installed automatically by Reflex
the first time the app compiles.

## Quick start

```python
import reflex as rx
import reflex_mapcn as mapcn


def index() -> rx.Component:
    return rx.box(
        mapcn.map(
            mapcn.map_controls(position="top-right", show_compass=True),
            mapcn.map_marker(
                mapcn.marker_content(),          # default blue dot
                mapcn.marker_tooltip("Caracas"),
                mapcn.marker_popup(rx.text("Hello from Caracas"), close_button=True),
                longitude=-66.9036,
                latitude=10.4806,
            ),
            center=[-66.9036, 10.4806],
            zoom=11,
        ),
        height="480px",
    )


app = rx.App()
app.add_page(index)
```

The map fills its parent, so give the parent (or the map itself via `height`
and `width`) a size.

## Components

| Reflex factory | mapcn component | Notes |
| --- | --- | --- |
| `mapcn.map` | `Map` | Root container. Accepts MapLibre `MapOptions` as props. |
| `mapcn.map_marker` | `MapMarker` | `longitude`, `latitude`, `draggable`, drag/click/hover events |
| `mapcn.marker_content` | `MarkerContent` | Visual of the marker (defaults to a dot) |
| `mapcn.marker_popup` | `MarkerPopup` | Click popup attached to the marker |
| `mapcn.marker_tooltip` | `MarkerTooltip` | Hover tooltip |
| `mapcn.marker_label` | `MarkerLabel` | Text above/below the marker (`position`) |
| `mapcn.map_popup` | `MapPopup` | Standalone popup at a coordinate, `on_close` |
| `mapcn.map_controls` | `MapControls` | `position`, `show_zoom`, `show_compass`, `show_locate`, `show_fullscreen`, `on_locate` |
| `mapcn.map_route` | `MapRoute` | `coordinates`, `color`, `width`, `progress`, `active*`, `dash_array` |
| `mapcn.route_progress` | `RouteProgress` | Traveled part of the parent route |
| `mapcn.route_marker` | `RouteMarker` | Marker at `"start"`, `"end"`, `"progress"` or a 0-1 fraction |
| `mapcn.map_arc` | `MapArc` | Curved arcs, `paint`, `hover_paint`, `on_hover`, `on_click` |
| `mapcn.map_geojson` | `MapGeoJSON` | Fill + outline layers, `promote_id`, `fill_hover_paint`, events |
| `mapcn.map_cluster_layer` | `MapClusterLayer` | Native clustering, `on_point_click`, `on_cluster_click` |
| `mapcn.map_camera` | *(Reflex extra)* | Runs a camera command dict from state |

A `mapcn.mapcn` namespace mirrors the same factories with shorter names
(`mapcn.mapcn.marker`, `mapcn.mapcn.geojson`, ...).

Props use `snake_case` and are converted to the camelCase props of the
React component (`show_zoom` → `showZoom`, `fill_paint` → `fillPaint`).

## Events

All callbacks receive plain dictionaries / lists:

| Event | Payload |
| --- | --- |
| `map.on_viewport_change`, `on_move_end`, `on_load` | `{"center": [lng, lat], "zoom", "bearing", "pitch"}` |
| `map.on_click` | `{"lng", "lat", "point": {"x", "y"}}` |
| `map_marker.on_click / on_mouse_enter / on_mouse_leave / on_drag*` | `{"lng", "lat"}` |
| `map_controls.on_locate` | `{"longitude", "latitude"}` |
| `map_route.on_click / on_mouse_enter` | `{"lng", "lat"}` |
| `map_arc.on_click / on_hover` | `{"arc": {...datum}, "longitude", "latitude"}` (`None` on hover leave) |
| `map_geojson.on_click / on_hover` | `{"feature": {"id", "properties", "geometry"}, "longitude", "latitude"}` (`None` on hover leave) |
| `map_cluster_layer.on_point_click` | `(feature, [lng, lat])` |
| `map_cluster_layer.on_cluster_click` | `(cluster_id, [lng, lat], point_count)` |
| `map_popup.on_close` | no arguments |

`on_viewport_change` fires continuously while the map moves; throttle it
(`State.handler.throttle(100)`) or prefer `on_move_end`.

```python
class MapState(rx.State):
    viewport: dict = {"center": [-66.9, 10.48], "zoom": 11, "bearing": 0, "pitch": 0}

    @rx.event
    def set_viewport(self, viewport: dict):
        self.viewport = viewport


mapcn.map(
    viewport=MapState.viewport,                              # controlled mode
    on_viewport_change=MapState.set_viewport.throttle(100),
)
```

## Recipes

### Route with progress

```python
mapcn.map_route(
    mapcn.route_progress(color="#3b82f6", width=5, opacity=1),
    mapcn.route_marker(mapcn.marker_content(), at="start"),
    mapcn.route_marker(mapcn.marker_content(rx.icon("car")), at="progress"),
    coordinates=[[lng, lat], ...],
    progress=State.progress,     # 0-1
    color="#94a3b8",
    dash_array=[0.5, 1.5],
)
```

### Choropleth on a blank basemap

```python
mapcn.map(
    mapcn.map_geojson(
        data="https://.../countries.geojson",
        promote_id="NAME_LONG",
        fill_paint={"fill-color": ["match", ["get", "NAME_LONG"], "Venezuela", "#1d4ed8", "#9ca3af"]},
        fill_hover_paint={"fill-color": "#f59e0b"},
        interactive=True,
        on_hover=State.on_country_hover,
    ),
    blank=True,
    center=[-30, 20],
    zoom=1.4,
)
```

### Driving the camera from state

```python
class State(rx.State):
    command: dict = {}
    _seq: int = 0

    @rx.event
    def fly_to(self, lng: float, lat: float):
        self._seq += 1
        self.command = mapcn.camera_command("flyTo", center=[lng, lat], zoom=12, seq=self._seq)


mapcn.map(mapcn.map_camera(command=State.command), ...)
```

Supported command types: `flyTo` (default), `easeTo`, `jumpTo`, `fitBounds`
(`bounds=[[west, south], [east, north]]`). `seq` lets you re-issue an identical
command.

### Custom styles, globe and blank basemap

```python
mapcn.map(styles={"light": "https://tiles.openfreemap.org/styles/bright",
                  "dark": "https://tiles.openfreemap.org/styles/dark"})
mapcn.map(projection={"type": "globe"}, zoom=1)
mapcn.map(blank=True)   # transparent, tile-less canvas for data viz
```

## Theming

The component ships its own stylesheet (no Tailwind required). Colors default
to the Radix Themes variables Reflex uses, so popups, tooltips and controls
match your app in both light and dark mode. Override the `--mapcn-*` custom
properties on `.mapcn-map` to re-theme:

```css
.mapcn-map {
  --mapcn-bg: #fff;
  --mapcn-fg: #111;
  --mapcn-border: #e5e5e5;
  --mapcn-accent: #3b82f6;
  --mapcn-radius: 8px;
}
```

Marker content, popup bodies and labels are regular Reflex components, so
style them as usual (`rx.box(background_color=..., border_radius="9999px")`).

## Web worker and CSP

MapLibre loads its web worker from unpkg by default. To self-host it, copy
`node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs` into your app's
`assets/` folder and pass `worker_url="/maplibre-gl-worker.mjs"` to
`mapcn.map`. With a strict CSP allow `worker-src 'self' blob:` and, unless
self-hosting, `script-src https://unpkg.com`.

## Demo app

The repository contains a demo app that exercises every feature:

```bash
git clone https://github.com/ecrespo/reflex-mapcn
cd reflex-mapcn
uv venv && uv pip install -e . && uv pip install -r mapcn_demo/requirements.txt
cd mapcn_demo && uv run reflex run
```

Pages: basic map (controlled viewport, blank basemap, custom styles), markers,
popups, controls, routes (progress, OSRM alternatives), arcs, GeoJSON,
clusters, advanced (camera commands, event log, globe) and a full-country
Venezuela map (OpenFreeMap street-level basemap, state polygons served from
`assets/`, capitals and main cities, state picker and camera fitting).

## Development

```bash
uv venv && uv pip install -e ".[dev]"
uv run reflex component build    # generates .pyi stubs + builds dist/
```

## Credits

- [mapcn](https://github.com/AnmolSaini16/mapcn) by Anmol Saini (MIT)
- [MapLibre GL JS](https://maplibre.org)
- Basemap tiles by [CARTO](https://carto.com/basemaps)

## License

MIT
