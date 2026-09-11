/**
 * Runs the bundled test suite in Chromium and reports the result.
 *
 * Exits non-zero when an assertion fails or when the page logged an error, so
 * the suite is usable from CI as well as from `tests/js/run.sh`.
 */
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const bundlePath = resolve(here, "..", ".build", "entry.js");
const bundle = await readFile(bundlePath, "utf8");

const browser = await chromium.launch();
const page = await browser.newPage();

const consoleErrors = [];
page.on("console", (message) => {
  const type = message.type();
  if (type === "error") consoleErrors.push(message.text());
  if (process.env.MAPCN_TEST_VERBOSE) console.log(`  [page:${type}] ${message.text()}`);
});
page.on("pageerror", (error) => consoleErrors.push(String(error)));

await page.setContent("<!doctype html><html><body></body></html>");
await page.addScriptTag({ content: bundle, type: "module" });

let results;
try {
  results = await page.waitForFunction(() => window.__MAPCN_RESULTS__, null, { timeout: 30000 })
    .then((handle) => handle.jsonValue());
} catch (error) {
  console.error("the suite never finished:", error.message);
  for (const line of consoleErrors) console.error(`  [page error] ${line}`);
  await browser.close();
  process.exit(1);
}

await browser.close();

let failed = 0;
for (const result of results) {
  if (result.ok) {
    console.log(`PASS  ${result.name} (${result.ms.toFixed(0)} ms)`);
  } else {
    failed += 1;
    console.log(`FAIL  ${result.name}`);
    console.log(`      ${result.error.split("\n").join("\n      ")}`);
  }
}

console.log(`\n${results.length - failed}/${results.length} passing`);
console.log(consoleErrors.length ? `ERRORS: ${consoleErrors.length}` : "ERRORS: none");
for (const line of consoleErrors) console.log(`  ${line}`);

process.exit(failed || consoleErrors.length ? 1 : 0);
