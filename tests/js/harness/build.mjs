/**
 * Bundles the JSX test suite for the browser with bun.
 *
 * `maplibre-gl` resolves to the stub and every stylesheet import is emptied,
 * so the bundle is the real `mapcn.jsx` running against a map it cannot break.
 * Run with `bun harness/build.mjs` from `tests/js`.
 */
import { readdir, mkdir, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const testsDir = resolve(here, "..", "tests");
const buildDir = resolve(here, "..", ".build");
const mapcnPath = resolve(here, "..", "..", "..", "custom_components", "reflex_mapcn", "mapcn.jsx");
const stubPath = join(here, "maplibre-stub.js");

const files = (await readdir(testsDir)).filter((name) => name.endsWith(".test.mjs")).sort();
if (files.length === 0) throw new Error("no test files found in tests/js/tests");

const only = process.argv[2];
const selected = only ? files.filter((name) => name.includes(only)) : files;
if (selected.length === 0) throw new Error(`no test file matches "${only}"`);

await mkdir(buildDir, { recursive: true });
const entryPath = join(buildDir, "entry.mjs");
await writeFile(
  entryPath,
  [
    `import { runAll } from ${JSON.stringify(join(here, "testing.js"))};`,
    ...selected.map((name) => `import ${JSON.stringify(join(testsDir, name))};`),
    "runAll().then((results) => { window.__MAPCN_RESULTS__ = results; });",
    "",
  ].join("\n"),
);

// `mapcn.jsx` lives outside this folder, so bun would resolve its `react`
// import from a different node_modules and React would see two copies of
// itself ("invalid hook call"). Pin every React specifier to ours.
const reactDir = resolve(here, "..", "node_modules", "react");
const reactDomDir = resolve(here, "..", "node_modules", "react-dom");
const REACT_ALIASES = {
  react: join(reactDir, "index.js"),
  "react/jsx-runtime": join(reactDir, "jsx-runtime.js"),
  "react/jsx-dev-runtime": join(reactDir, "jsx-dev-runtime.js"),
  "react-dom": join(reactDomDir, "index.js"),
  "react-dom/client": join(reactDomDir, "client.js"),
};

const aliasPlugin = {
  name: "mapcn-test-alias",
  setup(build) {
    build.onResolve({ filter: /^mapcn$/ }, () => ({ path: mapcnPath }));
    build.onResolve({ filter: /^react(-dom)?(\/.*)?$/ }, (args) => {
      const target = REACT_ALIASES[args.path];
      return target ? { path: target } : undefined;
    });
    build.onResolve({ filter: /^maplibre-gl$/ }, () => ({ path: stubPath }));
    build.onResolve({ filter: /\.css$/ }, (args) => ({
      path: `stylesheet:${args.path}`,
      namespace: "empty-css",
    }));
    build.onLoad({ filter: /.*/, namespace: "empty-css" }, () => ({
      contents: "export default {};",
      loader: "js",
    }));
  },
};

const result = await Bun.build({
  entrypoints: [entryPath],
  outdir: buildDir,
  target: "browser",
  format: "esm",
  sourcemap: "inline",
  plugins: [aliasPlugin],
});

if (!result.success) {
  for (const log of result.logs) console.error(log);
  process.exit(1);
}

console.log(`built ${selected.length} test file(s) -> ${join(buildDir, "entry.js")}`);
