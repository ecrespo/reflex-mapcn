/**
 * Tests for `map_terrain` (T-012).
 *
 * MapLibre allows one terrain per map, so besides the usual lifecycle this
 * component has to behave when two of them exist and when one of them leaves.
 */
import { MapTerrain } from "mapcn";
import { assert, assertEqual, h, test, withWarnings } from "../harness/testing.js";
import { render } from "../harness/mount.js";

const DEM = ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"];

const terrain = (props) => h(MapTerrain, props);

test("REQ-TER-001: a raster-dem source is added and terrain is switched on", async () => {
  const view = await render(terrain, { id: "relief", tiles: DEM, exaggeration: 1.3 });

  const source = view.map.getSource("terrain-source-relief");
  assert(source, "source missing");
  assertEqual(source.type, "raster-dem", "source type");
  assertEqual(source.encoding, "terrarium", "encoding default");
  assertEqual(source.tiles, DEM, "tiles");

  assertEqual(
    view.map.getTerrain(),
    { source: "terrain-source-relief", exaggeration: 1.3 },
    "setTerrain was not called with the source and the exaggeration",
  );

  await view.unmount();
});

test("REQ-TER-003: hillshade adds a layer over the same source", async () => {
  const view = await render(terrain, {
    id: "relief",
    tiles: DEM,
    hillshade: true,
    hillshadePaint: { "hillshade-shadow-color": "#334155" },
  });

  const layer = view.map.getLayer("hillshade-layer-relief");
  assert(layer, "hillshade layer missing");
  assertEqual(layer.type, "hillshade", "layer type");
  assertEqual(layer.source, "terrain-source-relief", "the layer shares the dem source");
  assertEqual(layer.paint["hillshade-shadow-color"], "#334155", "custom paint");
  assertEqual(layer.paint["hillshade-exaggeration"], 0.5, "default paint was lost");

  await view.unmount();
});

test("REQ-TER-004: a new exaggeration does not recreate the source", async () => {
  const view = await render(terrain, { id: "relief", tiles: DEM, exaggeration: 1 });

  await view.setProps({ exaggeration: 2.5 });

  assertEqual(view.map.getTerrain().exaggeration, 2.5, "exaggeration");
  assertEqual(view.map.callsTo("addSource").length, 1, "the source was recreated");

  await view.unmount();
});

test("REQ-TER-005: unmounting switches terrain off and removes the source", async () => {
  const view = await render(terrain, { id: "relief", tiles: DEM, hillshade: true });

  await view.unmount();

  assertEqual(view.map.getTerrain(), null, "terrain was left on");
  assertEqual(view.map.getLayersOrder(), [], "the hillshade layer was left behind");
  assertEqual(Object.keys(view.map.getStyle().sources), [], "the source was left behind");
});

test("REQ-TER-006: terrain is restored after a style change", async () => {
  const view = await render(terrain, { id: "relief", tiles: DEM, exaggeration: 1.3 });

  await view.setMapProps({ theme: "dark" });
  assertEqual(view.map.getTerrain(), null, "the style swap should have dropped the terrain");

  await view.emit("style.load");

  assert(view.map.getSource("terrain-source-relief"), "the source was not re-added");
  assertEqual(view.map.getTerrain().exaggeration, 1.3, "terrain was not restored");

  await view.unmount();
});

test("REQ-TER-007: a second terrain replaces the first one with a warning", async () => {
  let view;
  const warnings = await withWarnings(async () => {
    view = await render(
      () => [
        h(MapTerrain, { id: "first", key: "first", tiles: DEM, exaggeration: 1 }),
        h(MapTerrain, { id: "second", key: "second", tiles: DEM, exaggeration: 2 }),
      ],
      {},
    );
  });

  assertEqual(
    view.map.getTerrain().source,
    "terrain-source-second",
    "the last terrain should win",
  );
  assert(
    warnings.some((line) => line.includes("only one map_terrain")),
    `expected a warning, got: ${warnings.join(" | ")}`,
  );

  await view.unmount();
  assertEqual(view.map.getTerrain(), null, "terrain was left on");
});

test("REQ-TER-008: the viewport payload carries the centre elevation", async () => {
  const moves = [];
  const view = await render(
    terrain,
    { id: "relief", tiles: DEM },
    { mapProps: { onMoveEnd: (viewport) => moves.push(viewport) } },
  );

  view.map.setElevation(942);
  await view.emit("moveend");

  assertEqual(moves.length, 1, "onMoveEnd did not fire");
  assertEqual(moves[0].elevation, 942, "elevation missing from the viewport");

  await view.unmount();
});

test("REQ-TER-009: failing dem tiles report through on_load_error", async () => {
  const seen = [];
  const view = await render(terrain, {
    id: "relief",
    tiles: DEM,
    onLoadError: (payload) => seen.push(payload),
  });

  await view.emit("error", {
    sourceId: "terrain-source-relief",
    error: { message: "Failed to fetch dem tile" },
  });

  assertEqual(seen.length, 1, "on_load_error did not fire");
  assertEqual(seen[0].source_id, "terrain-source-relief", "source_id");

  await view.unmount();
});
