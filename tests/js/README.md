# JSX tests

`mapcn.jsx` only runs in a browser, so these tests run the real module in
Chromium against a simulated MapLibre. Nothing here ships with the package:
`tests/js/package.json` is development tooling, and the published wheel still
depends on `maplibre-gl` alone (constitution, article 3).

## Running

```bash
bash tests/js/run.sh            # every test file
bash tests/js/run.sh layer      # only files whose name contains "layer"
MAPCN_TEST_VERBOSE=1 bash tests/js/run.sh   # also echo the page console
```

The first run installs `react`, `react-dom` and `playwright` with bun. Chromium
itself comes from `node tests/js/node_modules/playwright/cli.js install chromium`.

The script exits non-zero when an assertion fails **or** when the page logged an
error, and prints `ERRORS: none` when the console stayed clean.

## Layout

| Path | What it is |
|---|---|
| `harness/maplibre-stub.js` | Simulated `maplibre-gl`: records every call, and throws where MapLibre throws (layer over a missing source, source removed while a layer uses it). |
| `harness/mount.js` | `render()`: mounts a component inside `Map`, fires `load`/`style.load`, and returns setters for props, map props and events. |
| `harness/testing.js` | `test()`, `assert*()` and the in-page runner. |
| `harness/build.mjs` | Bundles the suite with bun, aliasing `mapcn`, `maplibre-gl` and React. |
| `harness/run.mjs` | Drives Chromium with Playwright and reports results. |
| `tests/*.test.mjs` | The tests themselves, one file per component. |

## Writing a test

```js
import { MapCircleLayer } from "mapcn";
import { assert, assertEqual, h, test } from "../harness/testing.js";
import { render } from "../harness/mount.js";

test("REQ-PNT-001: circle layer reaches the map", async () => {
  const view = await render((props) => h(MapCircleLayer, props), { id: "q", data: POINTS });
  assert(view.map.getLayer("circle-layer-q"), "layer missing");
  await view.setProps({ radius: 12 });
  assertEqual(view.map.getLayer("circle-layer-q").paint["circle-radius"], 12);
  await view.unmount();
});
```

Name each test after the requirement it covers (`REQ-XXX-NNN`), as article 6 of
the constitution requires. `view.map` exposes `calls`, `callsTo(method)`,
`getLayersOrder()`, `emit()` and `emitOn()` for assertions on lifecycle order.
