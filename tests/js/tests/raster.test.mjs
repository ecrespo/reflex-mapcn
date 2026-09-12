/**
 * Tests for `map_raster_layer` (T-006).
 *
 * The lifecycle itself is covered by the layer runtime tests; what matters
 * here is the translation from component props to a MapLibre raster source and
 * raster layer, and the tile-error callback.
 */
import { RasterLayer } from "mapcn";
import { assert, assertEqual, h, test } from "../harness/testing.js";
import { render } from "../harness/mount.js";

const TILES = ["https://tiles.example.test/a/{z}/{x}/{y}.png"];
const OTHER_TILES = ["https://tiles.example.test/b/{z}/{x}/{y}.png"];

const raster = (props) => h(RasterLayer, props);

test("REQ-RAS-001: a raster source and a raster layer reach the map", async () => {
  const view = await render(raster, { id: "radar", tiles: TILES });

  const source = view.map.getSource("raster-source-radar");
  assert(source, "source missing");
  assertEqual(source.type, "raster", "source type");
  assertEqual(source.tiles, TILES, "tiles");

  const layer = view.map.getLayer("raster-layer-radar");
  assert(layer, "layer missing");
  assertEqual(layer.type, "raster", "layer type");
  assertEqual(layer.source, "raster-source-radar", "layer source");

  await view.unmount();
});

test("REQ-RAS-004: tile size, scheme and attribution reach the source", async () => {
  const view = await render(raster, {
    id: "sea",
    tiles: TILES,
    tileSize: 512,
    scheme: "tms",
    attribution: "© Example",
    maxZoom: 18,
  });

  const source = view.map.getSource("raster-source-sea");
  assertEqual(source.tileSize, 512, "tileSize");
  assertEqual(source.scheme, "tms", "scheme");
  assertEqual(source.attribution, "© Example", "attribution");
  assertEqual(source.maxzoom, 18, "source maxzoom keeps overzooming working");

  await view.unmount();
});

test("REQ-RAS-004: the default tile size is 256 and the default scheme is xyz", async () => {
  const view = await render(raster, { id: "d", tiles: TILES });
  const source = view.map.getSource("raster-source-d");
  assertEqual(source.tileSize, 256, "tileSize default");
  assertEqual(source.scheme, "xyz", "scheme default");
  await view.unmount();
});

test("REQ-RAS-002: opacity, visibility and zoom range change without a rebuild", async () => {
  const view = await render(raster, { id: "radar", tiles: TILES, opacity: 1 });

  await view.setProps({ opacity: 0.4, visible: false, minZoom: 3, maxZoom: 9 });

  const layer = view.map.getLayer("raster-layer-radar");
  assertEqual(layer.paint["raster-opacity"], 0.4, "opacity");
  assertEqual(layer.layout.visibility, "none", "visibility");
  assertEqual(view.map.callsTo("setLayerZoomRange").length, 1, "setLayerZoomRange");
  assertEqual(view.map.callsTo("addSource").length, 1, "the source was recreated");

  await view.unmount();
});

test("REQ-RAS-003: new tiles recreate the source and keep the opacity", async () => {
  const view = await render(raster, { id: "radar", tiles: TILES, opacity: 0.6 });

  await view.setProps({ tiles: OTHER_TILES });

  assertEqual(view.map.callsTo("addSource").length, 2, "the source was not recreated");
  assertEqual(view.map.getSource("raster-source-radar").tiles, OTHER_TILES, "tiles");
  assertEqual(
    view.map.getLayer("raster-layer-radar").paint["raster-opacity"],
    0.6,
    "opacity was lost in the rebuild",
  );

  await view.unmount();
});

test("REQ-RAS-008: the raster layer survives a style change", async () => {
  const view = await render(raster, { id: "radar", tiles: TILES });

  await view.setMapProps({ theme: "dark" });
  await view.emit("style.load");

  assert(view.map.getSource("raster-source-radar"), "source was not re-added");
  assertEqual(view.map.getLayersOrder(), ["raster-layer-radar"], "layer was not re-added");

  await view.unmount();
});

test("REQ-RAS-009: unmounting leaves no raster source or layer behind", async () => {
  const view = await render(raster, { id: "radar", tiles: TILES });
  await view.unmount();

  assertEqual(view.map.getLayersOrder(), [], "layers left behind");
  assertEqual(Object.keys(view.map.getStyle().sources), [], "sources left behind");
});

test("REQ-RAS-011: a tile error calls on_load_error once per minute", async () => {
  const seen = [];
  const view = await render(raster, {
    id: "radar",
    tiles: TILES,
    onLoadError: (payload) => seen.push(payload),
  });

  await view.emit("error", {
    sourceId: "raster-source-radar",
    error: { message: "Failed to fetch tile" },
  });
  await view.emit("error", {
    sourceId: "raster-source-radar",
    error: { message: "Failed to fetch tile" },
  });
  // An error from another source must not reach this layer.
  await view.emit("error", { sourceId: "other-source", error: { message: "nope" } });

  assertEqual(seen.length, 1, "on_load_error was not throttled");
  assertEqual(seen[0].source_id, "raster-source-radar", "source_id");
  assertEqual(seen[0].message, "Failed to fetch tile", "message");

  await view.unmount();
});
