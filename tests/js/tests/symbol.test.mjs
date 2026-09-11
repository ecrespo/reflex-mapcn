/**
 * Tests for `map_symbol_layer` and `Map.glyphs_url` (T-011).
 *
 * Symbols are the one layer that can take the whole map down: a style without
 * glyphs cannot render text, so asking for a label on the blank basemap has to
 * degrade instead of failing.
 */
import { SymbolLayer } from "mapcn";
import { assert, assertEqual, h, test, withWarnings } from "../harness/testing.js";
import { render } from "../harness/mount.js";

const CITIES = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      id: 1,
      properties: { name: "Caracas" },
      geometry: { type: "Point", coordinates: [-66.9, 10.5] },
    },
  ],
};

const GLYPHS = "https://tiles.openfreemap.org/fonts";
const symbols = (props) => h(SymbolLayer, props);

test("REQ-PNT-002: icon and text props reach layout and paint", async () => {
  const view = await render(
    symbols,
    {
      id: "cities",
      data: CITIES,
      iconImage: "pin",
      iconSize: 1.2,
      iconAnchor: "bottom",
      iconOffset: [0, -4],
      iconRotate: 15,
      iconAllowOverlap: true,
      textField: ["get", "name"],
      textSize: 14,
      textOffset: [0, 1.5],
      textAnchor: "top",
      textColor: "#111827",
      textHaloColor: "#ffffff",
      textHaloWidth: 1.5,
    },
    { mapProps: { blank: true, glyphsUrl: GLYPHS } },
  );

  const layer = view.map.getLayer("symbol-layer-cities");
  assert(layer, "layer missing");
  assertEqual(layer.type, "symbol", "layer type");

  assertEqual(layer.layout["icon-image"], "pin", "icon-image");
  assertEqual(layer.layout["icon-size"], 1.2, "icon-size");
  assertEqual(layer.layout["icon-anchor"], "bottom", "icon-anchor");
  assertEqual(layer.layout["icon-offset"], [0, -4], "icon-offset");
  assertEqual(layer.layout["icon-rotate"], 15, "icon-rotate");
  assertEqual(layer.layout["icon-allow-overlap"], true, "icon-allow-overlap");
  assertEqual(layer.layout["text-field"], ["get", "name"], "text-field");
  assertEqual(layer.layout["text-font"], ["Noto Sans Regular"], "text-font default");
  assertEqual(layer.layout["text-size"], 14, "text-size");
  assertEqual(layer.layout["text-offset"], [0, 1.5], "text-offset");
  assertEqual(layer.layout["text-anchor"], "top", "text-anchor");

  assertEqual(layer.paint["text-color"], "#111827", "text-color");
  assertEqual(layer.paint["text-halo-color"], "#ffffff", "text-halo-color");
  assertEqual(layer.paint["text-halo-width"], 1.5, "text-halo-width");

  await view.unmount();
});

test("REQ-PNT-005: glyphs_url is injected into the blank basemap", async () => {
  const view = await render(
    symbols,
    { id: "cities", data: CITIES, textField: ["get", "name"] },
    { mapProps: { blank: true, glyphsUrl: GLYPHS } },
  );

  assertEqual(
    view.map.getStyle().glyphs,
    "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf",
    "the glyphs url was not injected",
  );
  assert(view.map.getLayer("symbol-layer-cities").layout["text-field"], "text was dropped");

  await view.unmount();
});

test("REQ-PNT-005: a glyphs_url that already has the placeholders is used as is", async () => {
  const template = "https://example.test/fonts/{fontstack}/{range}.pbf";
  const view = await render(
    symbols,
    { id: "cities", data: CITIES, textField: ["get", "name"] },
    { mapProps: { blank: true, glyphsUrl: template } },
  );

  assertEqual(view.map.getStyle().glyphs, template, "the template was rewritten");

  await view.unmount();
});

test("REQ-PNT-004: text without glyphs warns and drops the label, not the layer", async () => {
  let view;
  const warnings = await withWarnings(async () => {
    view = await render(
      symbols,
      { id: "cities", data: CITIES, iconImage: "pin", textField: ["get", "name"] },
      { mapProps: { blank: true } },
    );
  });

  const layer = view.map.getLayer("symbol-layer-cities");
  assert(layer, "the layer should still be there");
  assertEqual(layer.layout["text-field"], undefined, "the label should have been dropped");
  assertEqual(layer.layout["icon-image"], "pin", "the icon should still be drawn");
  assertEqual(warnings.length, 1, `expected one warning, got: ${warnings.join(" | ")}`);
  assert(warnings[0].includes("glyphs"), `unexpected warning: ${warnings[0]}`);

  await view.unmount();
});

test("REQ-PNT-003: icon images are added before the layer and removed on unmount", async () => {
  const view = await render(symbols, {
    id: "cities",
    data: CITIES,
    images: { pin: "https://example.test/pin.png" },
    iconImage: "pin",
  });
  await view.settle();

  assertEqual(view.map.listImages(), ["pin"], "the image was not added");
  const addImageAt = view.map.calls.findIndex((call) => call.method === "addImage");
  const addLayerAt = view.map.calls.findIndex((call) => call.method === "addLayer");
  assert(addImageAt < addLayerAt, "the image was added after the layer");

  await view.unmount();
  assertEqual(view.map.listImages(), [], "the image was left behind");
});

test("REQ-PNT-006: symbols are interactive by default", async () => {
  const clicks = [];
  const view = await render(symbols, {
    id: "cities",
    data: CITIES,
    promoteId: "name",
    iconImage: "pin",
    onClick: (payload) => clicks.push(payload),
  });

  const feature = { ...CITIES.features[0], source: "symbol-source-cities", sourceLayer: null };
  await view.emitOn("click", "symbol-layer-cities", {
    features: [feature],
    lngLat: { lng: -66.9, lat: 10.5 },
  });

  assertEqual(clicks.length, 1, "onClick did not fire");
  assertEqual(clicks[0].feature.properties.name, "Caracas", "feature properties");

  await view.unmount();
});
