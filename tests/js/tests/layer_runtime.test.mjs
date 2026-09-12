/**
 * Tests for `useMapLayer`, the shared layer lifecycle (T-003 / T-004).
 *
 * The hook is exercised through a probe component defined here, so the test
 * owns the ids and the prop shape and nothing test-only lives in the package.
 */
import { useMapLayer } from "mapcn";
import { assert, assertEqual, h, test, withWarnings } from "../harness/testing.js";
import { render } from "../harness/mount.js";

const POINTS = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      id: 7,
      properties: { name: "Caracas", mag: 5.2 },
      geometry: { type: "Point", coordinates: [-66.9036, 10.4806] },
    },
  ],
};

const MORE_POINTS = {
  type: "FeatureCollection",
  features: [
    ...POINTS.features,
    {
      type: "Feature",
      id: 8,
      properties: { name: "Cumaná", mag: 4.1 },
      geometry: { type: "Point", coordinates: [-64.1833, 10.4539] },
    },
  ],
};

/** A minimal circle layer built on the hook under test. */
function Probe({
  id = "probe",
  data = POINTS,
  sourceId,
  source,
  radius = 5,
  visible = true,
  filter,
  minZoom,
  maxZoom,
  beforeId,
  interactive = false,
  hoverPaint,
  promoteId,
  images,
  onClick,
  onHover,
  layerType = "circle",
}) {
  useMapLayer({
    id,
    sourceId: sourceId ?? `probe-source-${id}`,
    source:
      source === undefined
        ? { type: "geojson", data, ...(promoteId ? { promoteId } : {}) }
        : source,
    layers: [
      {
        id: `probe-layer-${id}`,
        type: layerType,
        paint: { "circle-radius": radius },
        layout: { visibility: visible ? "visible" : "none" },
        ...(filter ? { filter } : {}),
        ...(minZoom !== undefined ? { minzoom: minZoom } : {}),
        ...(maxZoom !== undefined ? { maxzoom: maxZoom } : {}),
      },
    ],
    beforeId,
    interactive,
    hoverPaint,
    images,
    callbacks: { onClick, onHover },
  });
  return null;
}

const probe = (props) => h(Probe, props);

function lngLatEvent(feature, lng = -66.9, lat = 10.5) {
  return { features: feature ? [feature] : [], lngLat: { lng, lat } };
}

const RENDERED_FEATURE = {
  type: "Feature",
  id: 7,
  properties: { name: "Caracas", mag: 5.2 },
  geometry: { type: "Point", coordinates: [-66.9036, 10.4806] },
  source: "probe-source-probe",
  sourceLayer: null,
};

test("REQ-LAY-001: the source and the layer reach the map", async () => {
  const view = await render(probe, {});

  const source = view.map.getSource("probe-source-probe");
  assert(source, "source missing");
  assertEqual(source.type, "geojson", "source type");
  assertEqual(source.data, POINTS, "source data");

  const layer = view.map.getLayer("probe-layer-probe");
  assert(layer, "layer missing");
  assertEqual(layer.source, "probe-source-probe", "layer is not bound to the source");
  assertEqual(layer.paint["circle-radius"], 5, "paint was not applied");

  await view.unmount();
});

test("REQ-LAY-003: new data calls setData and keeps the layer", async () => {
  const view = await render(probe, {});
  const addCallsBefore = view.map.callsTo("addLayer").length;

  await view.setProps({ data: MORE_POINTS });

  assertEqual(view.map.callsTo("setData").length, 1, "setData was not called once");
  assertEqual(view.map.getSource("probe-source-probe").data, MORE_POINTS, "data not updated");
  assertEqual(view.map.callsTo("addLayer").length, addCallsBefore, "the layer was recreated");

  await view.unmount();
});

test("REQ-LAY-004: paint, layout and filter are updated in place", async () => {
  const view = await render(probe, {});

  await view.setProps({ radius: 12, visible: false, filter: [">=", ["get", "mag"], 5] });

  const layer = view.map.getLayer("probe-layer-probe");
  assertEqual(layer.paint["circle-radius"], 12, "paint not updated");
  assertEqual(layer.layout.visibility, "none", "layout not updated");
  assertEqual(layer.filter, [">=", ["get", "mag"], 5], "filter not updated");
  assertEqual(view.map.callsTo("setPaintProperty").length, 1, "setPaintProperty calls");
  assertEqual(view.map.callsTo("setLayoutProperty").length, 1, "setLayoutProperty calls");
  assertEqual(view.map.callsTo("setFilter").length, 1, "setFilter calls");

  await view.unmount();
});

test("REQ-RAS-002: a new zoom range uses setLayerZoomRange", async () => {
  const view = await render(probe, { minZoom: 0, maxZoom: 22 });

  await view.setProps({ minZoom: 4, maxZoom: 12 });

  assertEqual(view.map.callsTo("setLayerZoomRange").length, 1, "setLayerZoomRange calls");
  assertEqual(view.map.getLayer("probe-layer-probe").minzoom, 4, "minzoom");
  assertEqual(view.map.getLayer("probe-layer-probe").maxzoom, 12, "maxzoom");

  await view.unmount();
});

test("REQ-LAY-005: a cold change recreates the source and the layer", async () => {
  const view = await render(probe, {});

  await view.setProps({ promoteId: "name" });

  assertEqual(view.map.callsTo("addSource").length, 2, "the source was not recreated");
  assertEqual(view.map.callsTo("removeSource").length, 1, "the old source was not removed");
  assertEqual(view.map.getSource("probe-source-probe").promoteId, "name", "promoteId");
  assertEqual(view.map.getLayersOrder(), ["probe-layer-probe"], "layer order after recreate");

  await view.unmount();
});

test("REQ-LAY-006: click and hover carry a serialisable payload", async () => {
  const seen = { click: [], hover: [] };
  const view = await render(probe, {
    interactive: true,
    onClick: (payload) => seen.click.push(payload),
    onHover: (payload) => seen.hover.push(payload),
  });

  await view.emitOn("click", "probe-layer-probe", lngLatEvent(RENDERED_FEATURE));
  await view.emitOn("mousemove", "probe-layer-probe", lngLatEvent(RENDERED_FEATURE));
  await view.emitOn("mouseleave", "probe-layer-probe", lngLatEvent(null));

  assertEqual(seen.click.length, 1, "onClick was not called once");
  assertEqual(seen.click[0].feature.properties.name, "Caracas", "feature properties");
  assertEqual(seen.click[0].longitude, -66.9, "longitude");
  assertEqual(seen.click[0].latitude, 10.5, "latitude");
  assertEqual(
    JSON.parse(JSON.stringify(seen.click[0])),
    seen.click[0],
    "payload is not JSON-serialisable",
  );
  assertEqual(seen.hover.length, 2, "onHover was not called on enter and leave");
  assertEqual(seen.hover[1], null, "onHover did not receive null on leave");

  await view.unmount();
});

test("REQ-PNT-006: hover writes feature state on the source", async () => {
  const view = await render(probe, { interactive: true, promoteId: "name" });

  await view.emitOn("mousemove", "probe-layer-probe", lngLatEvent(RENDERED_FEATURE));
  assertEqual(
    view.map.getFeatureState({ source: "probe-source-probe", id: 7 }),
    { hover: true },
    "hover state was not set",
  );
  assertEqual(view.map.getCanvas().style.cursor, "pointer", "cursor was not changed");

  await view.emitOn("mouseleave", "probe-layer-probe", lngLatEvent(null));
  assertEqual(
    view.map.getFeatureState({ source: "probe-source-probe", id: 7 }),
    { hover: false },
    "hover state was not cleared",
  );
  assertEqual(view.map.getCanvas().style.cursor, "", "cursor was not restored");

  await view.unmount();
});

test("REQ-LAY-008: an unknown before_id appends the layer and warns once", async () => {
  let view;
  const warnings = await withWarnings(async () => {
    view = await render(probe, { beforeId: "does-not-exist" });
    // A cold rebuild runs the add path again; the warning must not repeat.
    await view.setProps({ promoteId: "name" });
  });

  assertEqual(view.map.getLayersOrder(), ["probe-layer-probe"], "layer was not added");
  assertEqual(warnings.length, 1, `expected one warning, got: ${warnings.join(" | ")}`);
  assert(
    warnings[0].includes('before_id "does-not-exist" not found'),
    `unexpected warning: ${warnings[0]}`,
  );

  await view.unmount();
});

test("REQ-LAY-004: a new before_id moves the layer", async () => {
  const view = await render(
    (props) => [h(Probe, { id: "a", key: "a" }), h(Probe, { ...props, id: "b", key: "b" })],
    {},
  );
  assertEqual(view.map.getLayersOrder(), ["probe-layer-a", "probe-layer-b"], "initial order");

  await view.setProps({ beforeId: "probe-layer-a" });

  assertEqual(view.map.callsTo("moveLayer").length > 0, true, "moveLayer was not called");
  assertEqual(view.map.getLayersOrder(), ["probe-layer-b", "probe-layer-a"], "order after move");

  await view.unmount();
});

test("REQ-LAY-010: an unknown source id is skipped, warned once and retried", async () => {
  let view;
  const warnings = await withWarnings(async () => {
    view = await render(probe, { source: null, sourceId: "style-source" });
  });

  assertEqual(view.map.getLayersOrder(), [], "the layer should have been skipped");
  assertEqual(warnings.length, 1, `expected one warning, got: ${warnings.join(" | ")}`);
  assert(warnings[0].includes('source "style-source" not found'), `unexpected: ${warnings[0]}`);

  // The style now provides the source; a style reload must retry the layer.
  view.map.addSource("style-source", { type: "geojson", data: POINTS });
  await view.emit("style.load");

  assertEqual(view.map.getLayersOrder(), ["probe-layer-probe"], "the layer was not retried");

  await view.unmount();
});

test("REQ-RAS-008: the layer is re-added after a style change", async () => {
  const view = await render(probe, {});
  assertEqual(view.map.getLayersOrder(), ["probe-layer-probe"], "layer missing before the swap");

  await view.setMapProps({ theme: "dark" });
  assertEqual(view.map.getLayersOrder(), [], "the style swap should have dropped the layer");

  await view.emit("style.load");

  assertEqual(view.map.getLayersOrder(), ["probe-layer-probe"], "layer was not re-added");
  assert(view.map.getSource("probe-source-probe"), "source was not re-added");

  await view.unmount();
});

test("REQ-RAS-009: unmounting removes layers, source and listeners", async () => {
  const view = await render(probe, { interactive: true });
  const listenersBefore = view.map.listenerCount();
  assert(listenersBefore > 0, "no listeners were registered");

  await view.unmount();

  assertEqual(view.map.getLayersOrder(), [], "layers were left behind");
  assertEqual(Object.keys(view.map.getStyle().sources), [], "the source was left behind");
  assertEqual(
    view.map.callsTo("removeSource").length,
    1,
    "the source was not removed exactly once",
  );
});

test("REQ-PNT-003: images are added before the layer and removed on unmount", async () => {
  const view = await render(probe, {
    layerType: "symbol",
    images: { pin: "https://example.test/pin.png" },
  });
  await view.settle();

  assertEqual(view.map.listImages(), ["pin"], "the image was not added");
  const addImageAt = view.map.calls.findIndex((call) => call.method === "addImage");
  const addLayerAt = view.map.calls.findIndex((call) => call.method === "addLayer");
  assert(addImageAt >= 0 && addImageAt < addLayerAt, "the image was added after the layer");

  await view.unmount();
  assertEqual(view.map.listImages(), [], "the image was left behind");
});

test("REQ-PNT-010: a failing image is tolerated and the layer is still added", async () => {
  let view;
  const warnings = await withWarnings(async () => {
    view = await render(probe, {
      layerType: "symbol",
      images: { broken: "https://example.test/fail.png", ok: "https://example.test/pin.png" },
    });
    await view.settle();
  });

  assertEqual(view.map.listImages(), ["ok"], "the working image was not added");
  assertEqual(view.map.getLayersOrder(), ["probe-layer-probe"], "the layer was not added");
  assertEqual(warnings.length, 1, `expected one warning, got: ${warnings.join(" | ")}`);
  assert(warnings[0].includes('image "broken" failed to load'), `unexpected: ${warnings[0]}`);

  await view.unmount();
});

test("REQ-PNT-003: replacing the images adds the new one and drops the old", async () => {
  const view = await render(probe, {
    layerType: "symbol",
    images: { pin: "https://example.test/pin.png" },
  });
  await view.settle();

  await view.setProps({ images: { flag: "https://example.test/flag.png" } });
  await view.settle();

  assertEqual(view.map.listImages(), ["flag"], "images were not swapped");

  await view.unmount();
});
