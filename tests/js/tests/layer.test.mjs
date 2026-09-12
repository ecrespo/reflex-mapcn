/**
 * Tests for `map_layer`, the generic escape hatch (T-008).
 *
 * Anything MapLibre can draw should be reachable from Python without touching
 * this module, so what matters here is that an arbitrary source and layer
 * specification survive the trip intact.
 */
import { Layer } from "mapcn";
import { assert, assertEqual, h, test, withWarnings } from "../harness/testing.js";
import { render } from "../harness/mount.js";

const FAULTS = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      id: 3,
      properties: { name: "Boconó", slip_type: "Dextral" },
      geometry: { type: "LineString", coordinates: [[-70, 8], [-69, 9]] },
    },
  ],
};

const layer = (props) => h(Layer, props);

test("REQ-LAY-001: a source specification becomes a source and a layer", async () => {
  const view = await render(layer, {
    id: "faults",
    source: { type: "geojson", data: FAULTS },
    layer: { type: "line", paint: { "line-color": "#ef4444", "line-width": 2 } },
  });

  const source = view.map.getSource("layer-source-faults");
  assert(source, "source missing");
  assertEqual(source.data, FAULTS, "source data");

  const added = view.map.getLayer("layer-faults");
  assert(added, "layer missing");
  assertEqual(added.type, "line", "layer type");
  assertEqual(added.source, "layer-source-faults", "the source was not injected");
  assertEqual(added.paint["line-color"], "#ef4444", "paint");

  await view.unmount();
});

test("REQ-LAY-002: an existing source id adds the layer only", async () => {
  const view = await render(
    layer,
    {
      id: "buildings",
      source: "openmaptiles",
      layer: {
        type: "fill-extrusion",
        "source-layer": "building",
        minzoom: 14,
        paint: { "fill-extrusion-height": ["get", "render_height"] },
      },
    },
    { autoLoad: false },
  );

  view.map.addSource("openmaptiles", { type: "vector", url: "https://example.test/v.json" });
  await view.emit("load");
  await view.emit("style.load");

  assertEqual(view.map.callsTo("addSource").length, 1, "a second source was created");
  const added = view.map.getLayer("layer-buildings");
  assert(added, "layer missing");
  assertEqual(added.source, "openmaptiles", "the layer is not bound to the style source");
  assertEqual(added["source-layer"], "building", "source-layer was dropped");
  assertEqual(added.minzoom, 14, "minzoom was dropped");

  await view.unmount();
  assert(view.map.getSource("openmaptiles"), "a source owned by the style was removed");
});

test("REQ-LAY-006: hover paint is merged and the events carry the feature", async () => {
  const seen = { click: [], hover: [] };
  const view = await render(layer, {
    id: "faults",
    source: { type: "geojson", data: FAULTS, promoteId: "name" },
    layer: { type: "line", paint: { "line-width": 1 } },
    interactive: true,
    hoverPaint: { "line-width": 4 },
    onClick: (payload) => seen.click.push(payload),
    onHover: (payload) => seen.hover.push(payload),
  });

  assertEqual(
    view.map.getLayer("layer-faults").paint["line-width"],
    ["case", ["boolean", ["feature-state", "hover"], false], 4, 1],
    "hover paint was not merged",
  );

  const feature = { ...FAULTS.features[0], source: "layer-source-faults", sourceLayer: null };
  await view.emitOn("click", "layer-faults", {
    features: [feature],
    lngLat: { lng: -70, lat: 8 },
  });

  assertEqual(seen.click.length, 1, "onClick");
  assertEqual(seen.click[0].feature.properties.slip_type, "Dextral", "feature properties");

  await view.unmount();
});

test("REQ-LAY-001: visible false hides the layer without removing it", async () => {
  const view = await render(layer, {
    id: "faults",
    source: { type: "geojson", data: FAULTS },
    layer: { type: "line" },
    visible: false,
  });

  assertEqual(view.map.getLayer("layer-faults").layout.visibility, "none", "visibility");

  await view.setProps({ visible: true });
  assertEqual(view.map.getLayer("layer-faults").layout.visibility, "visible", "visibility");
  assertEqual(view.map.callsTo("addLayer").length, 1, "the layer was recreated");

  await view.unmount();
});

test("REQ-LAY-010: a source id the style does not provide is skipped with a warning", async () => {
  let view;
  const warnings = await withWarnings(async () => {
    view = await render(layer, {
      id: "buildings",
      source: "not-in-this-style",
      layer: { type: "fill-extrusion", "source-layer": "building" },
    });
  });

  assertEqual(view.map.getLayersOrder(), [], "the layer should have been skipped");
  assert(warnings[0].includes('source "not-in-this-style" not found'), warnings[0]);

  await view.unmount();
});
