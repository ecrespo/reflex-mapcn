/**
 * Tests for `map_circle_layer` (T-010).
 *
 * This is the component the seismic demo stands on: thousands of points drawn
 * by the GPU, with radius and colour driven by the data instead of by DOM
 * markers that fall apart past a few hundred.
 */
import { CircleLayer } from "mapcn";
import { assert, assertEqual, h, test } from "../harness/testing.js";
import { render } from "../harness/mount.js";

const QUAKES = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      id: "us1",
      properties: { id: "us1", mag: 5.1, depth: 30, time: 1689999000000 },
      geometry: { type: "Point", coordinates: [-66.9, 10.5] },
    },
  ],
};

const MAG_RADIUS = ["interpolate", ["linear"], ["get", "mag"], 4, 4, 7, 24];
const DEPTH_COLOR = ["step", ["get", "depth"], "#ef4444", 70, "#f97316"];

const circles = (props) => h(CircleLayer, props);

test("REQ-PNT-001: a geojson source and a circle layer reach the map", async () => {
  const view = await render(circles, { id: "quakes", data: QUAKES, promoteId: "id" });

  const source = view.map.getSource("circle-source-quakes");
  assert(source, "source missing");
  assertEqual(source.promoteId, "id", "promoteId");

  const layer = view.map.getLayer("circle-layer-quakes");
  assert(layer, "layer missing");
  assertEqual(layer.type, "circle", "layer type");

  await view.unmount();
});

test("REQ-PNT-001: the defaults draw a visible point without configuration", async () => {
  const view = await render(circles, { id: "quakes", data: QUAKES });
  const paint = view.map.getLayer("circle-layer-quakes").paint;

  assertEqual(paint["circle-radius"], 5, "radius");
  assertEqual(paint["circle-color"], "#3b82f6", "colour");
  assertEqual(paint["circle-opacity"], 0.85, "opacity");
  assertEqual(paint["circle-stroke-color"], "#ffffff", "stroke colour");
  assertEqual(paint["circle-stroke-width"], 1, "stroke width");

  await view.unmount();
});

test("REQ-PNT-001: every paint prop reaches its MapLibre property", async () => {
  const view = await render(circles, {
    id: "quakes",
    data: QUAKES,
    radius: MAG_RADIUS,
    color: DEPTH_COLOR,
    opacity: 0.7,
    strokeColor: "#111827",
    strokeWidth: 2,
    strokeOpacity: 0.5,
    blur: 0.3,
    pitchScale: "viewport",
    sortKey: ["get", "mag"],
  });
  const layer = view.map.getLayer("circle-layer-quakes");

  assertEqual(layer.paint["circle-radius"], MAG_RADIUS, "radius expression");
  assertEqual(layer.paint["circle-color"], DEPTH_COLOR, "colour expression");
  assertEqual(layer.paint["circle-opacity"], 0.7, "opacity");
  assertEqual(layer.paint["circle-stroke-color"], "#111827", "stroke colour");
  assertEqual(layer.paint["circle-stroke-width"], 2, "stroke width");
  assertEqual(layer.paint["circle-stroke-opacity"], 0.5, "stroke opacity");
  assertEqual(layer.paint["circle-blur"], 0.3, "blur");
  assertEqual(layer.paint["circle-pitch-scale"], "viewport", "pitch scale");
  // circle-sort-key is a layout property, not a paint one.
  assertEqual(layer.layout["circle-sort-key"], ["get", "mag"], "sort key");

  await view.unmount();
});

test("REQ-SIS-004: a new filter is applied without recreating the layer", async () => {
  const view = await render(circles, { id: "quakes", data: QUAKES });

  await view.setProps({ filter: ["<=", ["get", "time"], 1690000000000] });

  assertEqual(view.map.callsTo("setFilter").length, 1, "setFilter");
  assertEqual(view.map.callsTo("addLayer").length, 1, "the layer was recreated");

  await view.unmount();
});

test("REQ-PNT-006: circles are interactive by default and hover paint is merged", async () => {
  const clicks = [];
  const view = await render(circles, {
    id: "quakes",
    data: QUAKES,
    promoteId: "id",
    hoverPaint: { "circle-stroke-width": 3 },
    onClick: (payload) => clicks.push(payload),
  });

  assertEqual(
    view.map.getLayer("circle-layer-quakes").paint["circle-stroke-width"],
    ["case", ["boolean", ["feature-state", "hover"], false], 3, 1],
    "hover paint was not merged over the default stroke width",
  );

  const feature = { ...QUAKES.features[0], source: "circle-source-quakes", sourceLayer: null };
  await view.emitOn("click", "circle-layer-quakes", {
    features: [feature],
    lngLat: { lng: -66.9, lat: 10.5 },
  });

  assertEqual(clicks.length, 1, "onClick did not fire without asking for interactive");
  assertEqual(clicks[0].feature.properties.mag, 5.1, "feature properties");

  await view.unmount();
});

test("REQ-PNT-006: interactive false registers no listeners", async () => {
  const clicks = [];
  const view = await render(circles, {
    id: "quakes",
    data: QUAKES,
    interactive: false,
    onClick: (payload) => clicks.push(payload),
  });

  await view.emitOn("click", "circle-layer-quakes", {
    features: [QUAKES.features[0]],
    lngLat: { lng: -66.9, lat: 10.5 },
  });

  assertEqual(clicks.length, 0, "a non-interactive layer still fired onClick");

  await view.unmount();
});

test("REQ-PNT-008: clustering is configured on the source", async () => {
  const view = await render(circles, {
    id: "quakes",
    data: QUAKES,
    cluster: true,
    clusterRadius: 80,
    clusterMaxZoom: 12,
  });

  const source = view.map.getSource("circle-source-quakes");
  assertEqual(source.cluster, true, "cluster");
  assertEqual(source.clusterRadius, 80, "clusterRadius");
  assertEqual(source.clusterMaxZoom, 12, "clusterMaxZoom");

  // Turning clustering off changes the source itself, so it must be rebuilt.
  await view.setProps({ cluster: false });
  assertEqual(view.map.callsTo("addSource").length, 2, "the source was not rebuilt");
  assert(!view.map.getSource("circle-source-quakes").cluster, "cluster is still on");

  await view.unmount();
});
