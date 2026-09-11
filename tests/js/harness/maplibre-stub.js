/**
 * A simulated `maplibre-gl` module.
 *
 * It implements the surface `mapcn.jsx` touches and records every call, so the
 * tests can assert on what the components asked MapLibre to do without a real
 * WebGL context. Where MapLibre throws, this stub throws too: adding a layer
 * whose source is gone, or removing a source that a layer still uses, are the
 * lifecycle bugs the layer runtime must avoid.
 */

const instances = [];

export function getInstances() {
  return instances;
}

export function lastInstance() {
  return instances[instances.length - 1];
}

export function resetInstances() {
  instances.length = 0;
}

class StubGeoJSONSource {
  constructor(map, id, spec) {
    this._map = map;
    this._id = id;
    Object.assign(this, spec);
  }

  setData(data) {
    this.data = data;
    this._map.record("setData", this._id, data);
  }

  setTiles(tiles) {
    this.tiles = tiles;
    this._map.record("setTiles", this._id, tiles);
  }
}

class StubCanvas {
  constructor() {
    this.style = { cursor: "" };
  }
}

class StubMap {
  constructor(options = {}) {
    this.options = options;
    this.container = options.container ?? null;
    this.style = options.style ?? null;
    this.calls = [];
    this.warnings = [];
    this._sources = new Map();
    this._layers = [];
    this._images = new Map();
    this._listeners = [];
    this._featureStates = new Map();
    this._canvas = new StubCanvas();
    this._terrain = null;
    this._moving = false;
    this._elevation = null;
    this.removed = false;

    const center = options.center ?? [0, 0];
    this._center = { lng: center[0], lat: center[1] };
    this._zoom = options.zoom ?? 0;
    this._bearing = options.bearing ?? 0;
    this._pitch = options.pitch ?? 0;

    instances.push(this);
  }

  // ---- test helpers ----------------------------------------------------

  record(method, ...args) {
    this.calls.push({ method, args });
  }

  callsTo(method) {
    return this.calls.filter((call) => call.method === method);
  }

  /** Fire a map-wide event, e.g. `load` or `style.load`. */
  emit(type, event = {}) {
    for (const entry of [...this._listeners]) {
      if (entry.type === type && entry.layerId == null) entry.handler(event);
    }
  }

  /** Fire a layer-scoped event, e.g. a click on `circle-layer-x`. */
  emitOn(type, layerId, event = {}) {
    for (const entry of [...this._listeners]) {
      if (entry.type === type && entry.layerId === layerId) entry.handler(event);
    }
  }

  listenerCount() {
    return this._listeners.length;
  }

  setElevation(value) {
    this._elevation = value;
  }

  // ---- events ----------------------------------------------------------

  on(type, layerOrHandler, maybeHandler) {
    const layerId = typeof layerOrHandler === "function" ? null : layerOrHandler;
    const handler = typeof layerOrHandler === "function" ? layerOrHandler : maybeHandler;
    this._listeners.push({ type, layerId, handler });
    this.record("on", type, layerId);
    return this;
  }

  off(type, layerOrHandler, maybeHandler) {
    const layerId = typeof layerOrHandler === "function" ? null : layerOrHandler;
    const handler = typeof layerOrHandler === "function" ? layerOrHandler : maybeHandler;
    const index = this._listeners.findIndex(
      (entry) => entry.type === type && entry.layerId === layerId && entry.handler === handler,
    );
    if (index >= 0) this._listeners.splice(index, 1);
    this.record("off", type, layerId);
    return this;
  }

  once(type, handler) {
    const wrapper = (event) => {
      this.off(type, wrapper);
      handler(event);
    };
    return this.on(type, wrapper);
  }

  // ---- sources and layers ---------------------------------------------

  addSource(id, spec) {
    if (this._sources.has(id)) throw new Error(`Source "${id}" already exists.`);
    this._sources.set(id, new StubGeoJSONSource(this, id, spec));
    this.record("addSource", id, spec);
  }

  getSource(id) {
    return this._sources.get(id);
  }

  removeSource(id) {
    if (!this._sources.has(id)) throw new Error(`There is no source with this ID "${id}"`);
    const user = this._layers.find((layer) => layer.source === id);
    if (user) {
      throw new Error(`Source "${id}" cannot be removed while layer "${user.id}" is using it.`);
    }
    this._sources.delete(id);
    this.record("removeSource", id);
  }

  addLayer(layer, beforeId) {
    if (this.getLayer(layer.id)) throw new Error(`Layer "${layer.id}" already exists.`);
    if (layer.source && !this._sources.has(layer.source)) {
      throw new Error(`Source "${layer.source}" not found.`);
    }
    const copy = { ...layer, paint: { ...(layer.paint ?? {}) }, layout: { ...(layer.layout ?? {}) } };
    const index = beforeId ? this._layers.findIndex((entry) => entry.id === beforeId) : -1;
    if (index >= 0) this._layers.splice(index, 0, copy);
    else this._layers.push(copy);
    this.record("addLayer", layer, beforeId);
  }

  getLayer(id) {
    return this._layers.find((layer) => layer.id === id);
  }

  removeLayer(id) {
    const index = this._layers.findIndex((layer) => layer.id === id);
    if (index < 0) throw new Error(`The layer '${id}' does not exist in the map's style.`);
    this._layers.splice(index, 1);
    this.record("removeLayer", id);
  }

  moveLayer(id, beforeId) {
    const index = this._layers.findIndex((layer) => layer.id === id);
    if (index < 0) return;
    const [layer] = this._layers.splice(index, 1);
    const target = beforeId ? this._layers.findIndex((entry) => entry.id === beforeId) : -1;
    if (target >= 0) this._layers.splice(target, 0, layer);
    else this._layers.push(layer);
    this.record("moveLayer", id, beforeId);
  }

  getLayersOrder() {
    return this._layers.map((layer) => layer.id);
  }

  setPaintProperty(layerId, name, value) {
    const layer = this.getLayer(layerId);
    if (!layer) throw new Error(`The layer '${layerId}' does not exist in the map's style.`);
    layer.paint[name] = value;
    this.record("setPaintProperty", layerId, name, value);
  }

  setLayoutProperty(layerId, name, value) {
    const layer = this.getLayer(layerId);
    if (!layer) throw new Error(`The layer '${layerId}' does not exist in the map's style.`);
    layer.layout[name] = value;
    this.record("setLayoutProperty", layerId, name, value);
  }

  setFilter(layerId, filter) {
    const layer = this.getLayer(layerId);
    if (!layer) throw new Error(`The layer '${layerId}' does not exist in the map's style.`);
    layer.filter = filter;
    this.record("setFilter", layerId, filter);
  }

  setLayerZoomRange(layerId, minzoom, maxzoom) {
    const layer = this.getLayer(layerId);
    if (!layer) throw new Error(`The layer '${layerId}' does not exist in the map's style.`);
    layer.minzoom = minzoom;
    layer.maxzoom = maxzoom;
    this.record("setLayerZoomRange", layerId, minzoom, maxzoom);
  }

  setFeatureState(target, state) {
    const key = `${target.source}:${target.id}`;
    this._featureStates.set(key, { ...(this._featureStates.get(key) ?? {}), ...state });
    this.record("setFeatureState", target, state);
  }

  getFeatureState(target) {
    return this._featureStates.get(`${target.source}:${target.id}`) ?? {};
  }

  removeFeatureState(target, key) {
    this._featureStates.delete(`${target.source}:${target.id}`);
    this.record("removeFeatureState", target, key);
  }

  // ---- style -----------------------------------------------------------

  getStyle() {
    const sources = {};
    for (const [id, source] of this._sources) sources[id] = source;
    return {
      ...(typeof this.style === "object" && this.style ? this.style : {}),
      layers: this._layers,
      sources,
    };
  }

  setStyle(style) {
    // A real style swap drops every source, layer and image the app added.
    this._sources.clear();
    this._layers.length = 0;
    this._images.clear();
    this._terrain = null;
    this.style = style;
    this.record("setStyle", style);
  }

  setProjection(projection) {
    this.record("setProjection", projection);
  }

  // ---- images ----------------------------------------------------------

  loadImage(url) {
    this.record("loadImage", url);
    if (String(url).includes("fail")) {
      return Promise.reject(new Error(`Could not load image ${url}`));
    }
    return Promise.resolve({ data: { width: 1, height: 1, data: new Uint8Array(4) } });
  }

  addImage(name, image) {
    this._images.set(name, image);
    this.record("addImage", name);
  }

  hasImage(name) {
    return this._images.has(name);
  }

  removeImage(name) {
    this._images.delete(name);
    this.record("removeImage", name);
  }

  listImages() {
    return [...this._images.keys()];
  }

  // ---- terrain ---------------------------------------------------------

  setTerrain(spec) {
    this._terrain = spec;
    this.record("setTerrain", spec);
  }

  getTerrain() {
    return this._terrain;
  }

  queryTerrainElevation() {
    return this._elevation;
  }

  // ---- camera and misc -------------------------------------------------

  getCenter() {
    return { ...this._center };
  }

  getZoom() {
    return this._zoom;
  }

  getBearing() {
    return this._bearing;
  }

  getPitch() {
    return this._pitch;
  }

  isMoving() {
    return this._moving;
  }

  jumpTo(options = {}) {
    if (options.center) this._center = { lng: options.center[0], lat: options.center[1] };
    if (options.zoom !== undefined) this._zoom = options.zoom;
    this.record("jumpTo", options);
  }

  flyTo(options) {
    this.record("flyTo", options);
  }

  easeTo(options) {
    this.record("easeTo", options);
  }

  fitBounds(bounds, options) {
    this.record("fitBounds", bounds, options);
  }

  getCanvas() {
    return this._canvas;
  }

  getContainer() {
    return this.container;
  }

  queryRenderedFeatures() {
    return [];
  }

  project(lngLat) {
    return { x: lngLat[0] ?? 0, y: lngLat[1] ?? 0 };
  }

  unproject(point) {
    return { lng: point.x ?? 0, lat: point.y ?? 0 };
  }

  addControl() {
    return this;
  }

  removeControl() {
    return this;
  }

  resize() {
    return this;
  }

  remove() {
    this.removed = true;
    this._listeners.length = 0;
    this.record("remove");
  }
}

export class Marker {
  constructor(options = {}) {
    this.options = options;
    this.element = options.element ?? null;
    this.lngLat = null;
    this.popup = null;
    this._listeners = [];
  }

  setLngLat(lngLat) {
    this.lngLat = lngLat;
    return this;
  }

  getLngLat() {
    return this.lngLat;
  }

  addTo(map) {
    this.map = map;
    return this;
  }

  remove() {
    this.map = null;
    return this;
  }

  getElement() {
    return this.element;
  }

  setOffset() {
    return this;
  }

  setDraggable() {
    return this;
  }

  setPopup(popup) {
    this.popup = popup;
    return this;
  }

  togglePopup() {
    return this;
  }

  on(type, handler) {
    this._listeners.push({ type, handler });
    return this;
  }

  off(type, handler) {
    const index = this._listeners.findIndex((e) => e.type === type && e.handler === handler);
    if (index >= 0) this._listeners.splice(index, 1);
    return this;
  }
}

export class Popup {
  constructor(options = {}) {
    this.options = options;
    this.lngLat = null;
    this.content = null;
    this.open = false;
    this._listeners = [];
  }

  setLngLat(lngLat) {
    this.lngLat = lngLat;
    return this;
  }

  setDOMContent(node) {
    this.content = node;
    return this;
  }

  setHTML(html) {
    this.content = html;
    return this;
  }

  setMaxWidth() {
    return this;
  }

  addTo(map) {
    this.map = map;
    this.open = true;
    return this;
  }

  remove() {
    this.open = false;
    this.map = null;
    return this;
  }

  isOpen() {
    return this.open;
  }

  on(type, handler) {
    this._listeners.push({ type, handler });
    return this;
  }

  off() {
    return this;
  }
}

let workerUrl = "";

export function setWorkerUrl(url) {
  workerUrl = url;
}

export function getWorkerUrl() {
  return workerUrl;
}

export function getVersion() {
  return "6.3.0-stub";
}

export { StubMap as Map };

export default { Map: StubMap, Marker, Popup, setWorkerUrl, getWorkerUrl, getVersion };
