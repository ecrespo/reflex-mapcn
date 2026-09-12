/**
 * Renders mapcn components into a real DOM with a simulated MapLibre map.
 *
 * `render` returns the stub map plus setters for the component props and the
 * map props, so a test can drive the same lifecycle a Reflex state update
 * drives: new props on an already mounted layer, a theme swap, an unmount.
 */
import React from "react";
import { createRoot } from "react-dom/client";
import { Map as MapcnMap } from "mapcn";
import { lastInstance, resetInstances } from "./maplibre-stub.js";

const act = React.act;

window.IS_REACT_ACT_ENVIRONMENT = true;

/**
 * @param renderChildren function(props) -> React element(s) placed inside the map
 * @param initialProps   props handed to `renderChildren`
 * @param options.mapProps props for the surrounding `Map`
 * @param options.autoLoad fire `load` and `style.load` right after mounting
 */
export async function render(renderChildren, initialProps = {}, options = {}) {
  const { mapProps = {}, autoLoad = true } = options;

  resetInstances();

  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);

  const control = {};

  function Harness() {
    const [props, setProps] = React.useState(initialProps);
    const [currentMapProps, setMapProps] = React.useState(mapProps);
    control.setPropsState = setProps;
    control.setMapPropsState = setMapProps;
    return React.createElement(MapcnMap, currentMapProps, renderChildren(props));
  }

  await act(async () => {
    root.render(React.createElement(Harness));
  });

  const map = lastInstance();

  if (autoLoad) {
    await act(async () => {
      map.emit("load");
      map.emit("style.load");
    });
  }

  return {
    map,
    container,
    /** Replace the props of the component under test. */
    async setProps(next) {
      await act(async () => {
        control.setPropsState((current) => ({ ...current, ...next }));
      });
    },
    /** Replace the props of the surrounding `Map` (theme, styles, blank...). */
    async setMapProps(next) {
      await act(async () => {
        control.setMapPropsState((current) => ({ ...current, ...next }));
      });
    },
    /** Fire an event on the stub map inside `act`. */
    async emit(type, event) {
      await act(async () => {
        map.emit(type, event);
      });
    },
    /** Fire a layer-scoped event on the stub map inside `act`. */
    async emitOn(type, layerId, event) {
      await act(async () => {
        map.emitOn(type, layerId, event);
      });
    },
    /** Let pending promises (image loading, effects) settle. */
    async settle() {
      await act(async () => {
        await Promise.resolve();
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    },
    async unmount() {
      await act(async () => {
        root.unmount();
      });
      container.remove();
    },
  };
}
