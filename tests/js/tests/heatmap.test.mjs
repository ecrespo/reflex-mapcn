/**
 * Tests for `map_heatmap_layer` (T-009).
 *
 * A heatmap has to look right with no configuration at all, so the defaults
 * are part of the contract and are asserted here.
 */
import { HeatmapLayer } from "mapcn";
import { assert, assertEqual, h, test } from "../harness/testing.js";
import { render } from "../harness/mount.js";

const QUAKES = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      id: "us1",
      properties: { mag: 5.1 },
      geometry: { type: "Point", coordinates: [-66.9, 10.5] },
    },
  ],
};

const MORE_QUAKES = { type: "FeatureCollection", features: [] };

const heatmap = (props) => h(HeatmapLayer, props);

test("REQ-HEA-001: a geojson source and a heatmap layer reach the map", async () => {
  const view = await render(heatmap, { id: "density", data: QUAKES });

  const source = view.map.getSource("heatmap-source-density");
  assert(source, "source missing");
  assertEqual(source.data, QUAKES, "source data");

  const layer = view.map.getLayer("heatmap-layer-density");
  assert(layer, "layer missing");
  assertEqual(layer.type, "heatmap", "layer type");

  await view.unmount();
});

test("REQ-HEA-002: the defaults make a readable heatmap without configuration", async () => {
  const view = await render(heatmap, { id: "density", data: QUAKES });
  const paint = view.map.getLayer("heatmap-layer-density").paint;

  assertEqual(paint["heatmap-weight"], 1, "weight");
  assertEqual(paint["heatmap-opacity"], 0.8, "opacity");
  assertEqual(
    paint["heatmap-intensity"],
    ["interpolate", ["linear"], ["zoom"], 0, 1, 9, 3],
    "intensity grows with zoom",
  );
  assertEqual(
    paint["heatmap-radius"],
    ["interpolate", ["linear"], ["zoom"], 0, 2, 9, 20],
    "radius grows with zoom",
  );
  assert(Array.isArray(paint["heatmap-color"]), "colour ramp missing");
  assertEqual(paint["heatmap-color"][2], ["heatmap-density"], "ramp reads the density");

  await view.unmount();
});

test("REQ-HEA-002: every paint prop reaches its MapLibre property", async () => {
  const view = await render(heatmap, {
    id: "density",
    data: QUAKES,
    weight: ["interpolate", ["linear"], ["get", "mag"], 4, 0, 8, 1],
    intensity: 2,
    radius: 30,
    opacity: 0.5,
    color: ["interpolate", ["linear"], ["heatmap-density"], 0, "rgba(0,0,0,0)", 1, "red"],
  });
  const paint = view.map.getLayer("heatmap-layer-density").paint;

  assertEqual(paint["heatmap-weight"][2], ["get", "mag"], "weight");
  assertEqual(paint["heatmap-intensity"], 2, "intensity");
  assertEqual(paint["heatmap-radius"], 30, "radius");
  assertEqual(paint["heatmap-opacity"], 0.5, "opacity");
  assertEqual(paint["heatmap-color"][6], "red", "colour");

  await view.unmount();
});

test("REQ-HEA-005: new data and new paint are applied without a rebuild", async () => {
  const view = await render(heatmap, { id: "density", data: QUAKES });

  await view.setProps({ data: MORE_QUAKES, radius: 40, visible: false });

  assertEqual(view.map.callsTo("setData").length, 1, "setData");
  assertEqual(view.map.getLayer("heatmap-layer-density").paint["heatmap-radius"], 40, "radius");
  assertEqual(
    view.map.getLayer("heatmap-layer-density").layout.visibility,
    "none",
    "visibility",
  );
  assertEqual(view.map.callsTo("addSource").length, 1, "the source was recreated");

  await view.unmount();
});

test("REQ-HEA-006: the heatmap survives a style change and leaves nothing behind", async () => {
  const view = await render(heatmap, { id: "density", data: QUAKES });

  await view.setMapProps({ theme: "dark" });
  await view.emit("style.load");
  assertEqual(view.map.getLayersOrder(), ["heatmap-layer-density"], "not re-added");

  await view.unmount();
  assertEqual(view.map.getLayersOrder(), [], "layers left behind");
  assertEqual(Object.keys(view.map.getStyle().sources), [], "sources left behind");
});

test("REQ-HEA-007: a new filter is applied without a rebuild", async () => {
  const view = await render(heatmap, { id: "density", data: QUAKES });

  await view.setProps({ filter: ["<=", ["get", "time"], 1690000000000] });

  assertEqual(view.map.callsTo("setFilter").length, 1, "setFilter");
  assertEqual(
    view.map.getLayer("heatmap-layer-density").filter,
    ["<=", ["get", "time"], 1690000000000],
    "filter",
  );
  assertEqual(view.map.callsTo("addLayer").length, 1, "the layer was recreated");

  await view.unmount();
});
