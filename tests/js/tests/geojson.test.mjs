/**
 * Smoke test for the 0.1.0 `MapGeoJSON` component.
 *
 * It exists to prove the harness itself: a real `mapcn.jsx` runs in Chromium
 * against the simulated MapLibre, a layer reaches the map, and unmounting
 * leaves nothing behind (constitution, article 4).
 */
import { MapGeoJSON } from "mapcn";
import { assert, assertEqual, h, test } from "../harness/testing.js";
import { render } from "../harness/mount.js";

const POINTS = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      id: 1,
      properties: { name: "Caracas" },
      geometry: { type: "Point", coordinates: [-66.9036, 10.4806] },
    },
  ],
};

test("harness: MapGeoJSON adds a source and a fill layer", async () => {
  const view = await render((props) => h(MapGeoJSON, props), { id: "smoke", data: POINTS });

  assert(view.map.getSource("geojson-source-smoke"), "source was not added");
  assert(view.map.getLayer("geojson-fill-smoke"), "fill layer was not added");
  assertEqual(view.map.getSource("geojson-source-smoke").data, POINTS, "source data mismatch");

  await view.unmount();
});

test("harness: unmounting MapGeoJSON removes its layers and source", async () => {
  const view = await render((props) => h(MapGeoJSON, props), { id: "teardown", data: POINTS });
  await view.unmount();

  assertEqual(view.map.getLayersOrder(), [], "layers were left behind");
  assertEqual(Object.keys(view.map.getStyle().sources), [], "sources were left behind");
});
