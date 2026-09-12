/**
 * How the map container gets its size (found during the T-020 review).
 *
 * `Map` documents two ways to be sized: through its parent, or with a height
 * of its own. The second one goes through a class, because that is what
 * Reflex compiles a `height=` prop into, and the package stylesheet sets a
 * height on `.mapcn-map` as well. The rules below pin which one wins, with
 * the author rule inserted first so that only specificity can decide.
 */
import { assert, assertEqual, test } from "../harness/testing.js";
import { render } from "../harness/mount.js";

/**
 * Insert an author rule and then the package stylesheet, and return a handle
 * that removes both again.
 */
function withStylesheets(authorCss) {
  const author = document.createElement("style");
  author.textContent = authorCss;
  document.head.appendChild(author);

  const packaged = document.createElement("style");
  packaged.textContent = window.__MAPCN_CSS__ || "";
  document.head.appendChild(packaged);

  assert(packaged.textContent.includes(".mapcn-map"), "the package stylesheet is missing");

  return () => {
    author.remove();
    packaged.remove();
  };
}

test("a height given to the map itself survives the package stylesheet", async () => {
  const cleanup = withStylesheets(".author-size { height: 680px; width: 100%; }");

  const view = await render(() => null, {}, { mapProps: { className: "author-size" } });
  const element = view.container.querySelector(".mapcn-map");

  assertEqual(
    getComputedStyle(element).height,
    "680px",
    "the map collapsed: the stylesheet default won over the height it was given",
  );

  await view.unmount();
  cleanup();
});

test("without a height of its own the map fills its parent", async () => {
  const cleanup = withStylesheets(".author-size { height: 680px; }");

  const view = await render(() => null, {});
  view.container.style.height = "400px";
  const element = view.container.querySelector(".mapcn-map");

  assertEqual(
    getComputedStyle(element).height,
    "400px",
    "the map no longer fills a sized parent",
  );

  await view.unmount();
  cleanup();
});
