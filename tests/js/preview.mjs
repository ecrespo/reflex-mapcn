import { chromium } from "playwright";
const out = "/tmp/claude-1000/-home-ernesto-PycharmProjects-reflex-mapcn/cb0fc342-8463-433b-9b57-374d0dadc85d/scratchpad";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
await page.goto("http://127.0.0.1:3000/sismos", { waitUntil: "load", timeout: 90000 });
await page.waitForTimeout(20000);   // the catalogue lands, defaults: circles + faults

// The map on its own, which is what a thumbnail crops to.
await page.locator(".mapcn-map").first().screenshot({ path: `${out}/preview-map.png` });

// The panel, the map and the legend together: the component being driven.
const section = page.locator("div").filter({ has: page.locator(".mapcn-map") }).last();
const box = await page.locator(".mapcn-map").first().boundingBox();
await page.screenshot({
  path: `${out}/preview-panel.png`,
  clip: { x: 240, y: box.y - 12, width: 1200, height: box.height + 24 },
});
console.log("ok");
await browser.close();
