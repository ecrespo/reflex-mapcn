# reflex-mapcn demo

The application that exercises every component of `reflex_mapcn` against real
data. It is not published to PyPI: it lives in this repository so that each
feature has a page someone can open, and so that the compile check has
something to build.

## Running it

From this directory, with the package installed in editable mode:

```bash
uv run reflex run
```

The app then serves on <http://localhost:3000>. Every page works without
credentials. The two keys in `.env.example` unlock three optional tile
services on the raster page: copy that file to `.env`, fill in what you have,
and restart. Anything already exported in the shell wins over the file.

To build every page without a browser, from the repository root:

```bash
uv run python scripts/compile_check.py
```

It prints one line per route and ends in `COMPILE OK`.

## Pages

| Page | Route | What it shows |
|---|---|---|
| Basic map | `/` | `map` with MapLibre GL set up, light and dark basemaps following the Reflex colour mode, a viewport bound to state, the blank canvas and custom styles. |
| Markers | `/markers` | `map_marker` composed with `marker_content`, `marker_tooltip`, `marker_popup` and `marker_label`. |
| Popups | `/popups` | `map_popup` at a coordinate without a marker, opened and closed from state. |
| Controls | `/controls` | `map_controls` with zoom, compass, geolocate and fullscreen, in any corner. |
| Routes | `/routes` | `map_route` with `route_progress` and `route_marker`, plus alternatives read from the OSRM demo server. |
| Arcs | `/arcs` | `map_arc` drawing curved connections on the globe projection. |
| GeoJSON | `/geojson` | `map_geojson` rendering a FeatureCollection as fill and outline, with hover highlighting through `promote_id`. |
| Clusters | `/clusters` | `map_cluster_layer` over MapLibre's native clustering, on a few thousand earthquakes. |
| Raster | `/raster` | `map_raster_layer` over one tile service at a time: three presets that need no key, the RainViewer radar, and TomTom traffic or OpenWeather behind their own. A second map draws `map_symbol_layer` icons and labels. |
| Advanced | `/advanced` | The Reflex extras: `map_camera` driven from state, lifecycle events and the globe projection. |
| Venezuela | `/venezuela` | The country at street level: state polygons, city markers, and driving times from one capital to the others with the chosen route drawn. |
| Sismos | `/sismos` | The USGS seismic history of Venezuela with a time slider, a live feed, a density heatmap, the active faults and terrain relief. |

The last two pages are written in Spanish, which is the language of the
audience they were built for. Everything else, code and documentation
included, is in English.

## Where the code lives

| Path | What it holds |
|---|---|
| `mapcn_demo/pages/` | One module per page; importing the package registers every route. |
| `mapcn_demo/services/` | Clients for the public services: `usgs.py`, `osrm.py` and the shared `cache.py`. |
| `mapcn_demo/venezuela_data.py` | Reference data for both Venezuelan pages: states, capitals, regions and the seismic styling. |
| `assets/` | Static files served by Reflex, including the two derived datasets below. |
| `../scripts/build_faults.py` | Builds the fault asset from the GEM catalogue. Run by hand; its output is committed. |

Every service call has an explicit timeout, caches what it gets in the memory
of the backend process, and returns a value the page can render even when the
service is down. Nothing here reaches the browser directly: the pages read
their data through the backend, as the project constitution requires.

## Data sources and licences

| Source | Used by | Licence |
|---|---|---|
| [OpenFreeMap](https://openfreemap.org/) vector tiles, from OpenStreetMap data | Basemaps on the Venezuela and Sismos pages | ODbL 1.0 (data) |
| CARTO basemaps | The default light and dark basemap of the package | CARTO terms, OpenStreetMap data under ODbL 1.0 |
| [USGS Earthquake Hazards Program](https://earthquake.usgs.gov/fdsnws/event/1/) | The catalogue and the live feed of `/sismos` | Public domain (US government work) |
| [GEM Global Active Faults](https://github.com/GEMScienceTools/gem-global-active-faults) | `assets/venezuela_fallas.geojson`, the fault layer of `/sismos` | CC BY-SA 4.0 |
| [OSRM](https://router.project-osrm.org/) demo server | Route alternatives on `/routes`, travel times on `/venezuela` | Service under its own terms, road network from OpenStreetMap under ODbL 1.0 |
| Apache Superset country-map plugin | `assets/venezuela_estados.geojson`, the state polygons | Apache-2.0 |
| [Natural Earth](https://www.naturalearthdata.com/) via jsDelivr | The world map of `/geojson` | Public domain |
| The sample earthquake feed of the MapLibre documentation, which is USGS data | The clustering demo of `/clusters` | Public domain (US government work) |
| [OpenRailwayMap](https://www.openrailwaymap.org/) and [OpenSeaMap](https://www.openseamap.org/) | Two of the presets on `/raster` | ODbL 1.0, data from OpenStreetMap |
| Esri World Imagery | The satellite preset on `/raster` | Esri's own terms |
| [RainViewer](https://www.rainviewer.com/) | The radar on `/raster` | Free for non-commercial use |
| TomTom traffic and OpenWeather map tiles | `/raster`, only with a key of your own | Each provider's own terms; both have a free tier |
| AWS Terrain Tiles, terrarium encoding | The relief switch of `/sismos` | Open data; the preset carries the attribution "Terrain: Mapzen/AWS Terrain Tiles" |

The attribution that a licence requires is shown on the page that uses the
data, not only here.

## Tests

The demo is covered by `tests/demo/` at the repository root: the services
against saved responses, the pure functions each page decides with, and the
compile check above. Run them with `uv run pytest tests` from there.
