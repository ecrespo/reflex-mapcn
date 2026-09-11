/**
 * mapcn for Reflex.
 *
 * This is a port of the mapcn map component (https://www.mapcn.dev,
 * https://github.com/AnmolSaini16/mapcn, MIT license) adapted for Reflex:
 *
 *  - Tailwind utility classes are replaced by semantic `mapcn-*` classes that
 *    live in `mapcn.css` and are themed with Radix/Reflex CSS variables.
 *  - `lucide-react` icons are inlined as SVG so the module has a single npm
 *    dependency: `maplibre-gl`.
 *  - Every callback receives JSON-serialisable payloads only, so they can be
 *    wired straight into Reflex event handlers.
 *  - A few Reflex-friendly extras are added on `Map`: `onClick`, `onMoveEnd`,
 *    `onLoad`, `workerUrl` and a `style` prop that is applied to the container.
 */

import * as MapLibreGL from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import "./mapcn.css";
import React, {
  createContext,
  forwardRef,
  useCallback,
  useContext,
  useEffect,
  useId,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Tiny replacement for shadcn's `cn` helper (no tailwind-merge needed). */
function cn(...inputs) {
  return inputs.filter(Boolean).join(" ");
}

/** Configure the MapLibre worker URL once. */
function setWorkerUrl(url) {
  if (typeof window === "undefined") return;
  if (url) {
    MapLibreGL.setWorkerUrl(url);
  } else if (!MapLibreGL.getWorkerUrl()) {
    MapLibreGL.setWorkerUrl(
      `https://unpkg.com/maplibre-gl@${MapLibreGL.getVersion()}/dist/maplibre-gl-worker.mjs`,
    );
  }
}

setWorkerUrl();

const defaultStyles = {
  dark: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
  light: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
};

// A tile-less, dependency-free style with a transparent background.
const blankMapStyle = {
  version: 8,
  sources: {},
  layers: [
    {
      id: "background",
      type: "background",
      paint: { "background-color": "rgba(0, 0, 0, 0)" },
    },
  ],
};

// Prevent equivalent inline objects from triggering effects / style reloads.
function useStableValue(value) {
  const key = useMemo(() => JSON.stringify(value) ?? "", [value]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  return useMemo(() => value, [key]);
}

function mergeHoverPaint(paint, hoverPaint) {
  if (!hoverPaint) return paint;
  const merged = { ...paint };
  for (const [key, hoverValue] of Object.entries(hoverPaint)) {
    if (hoverValue === undefined) continue;
    const baseValue = merged[key];
    merged[key] =
      baseValue === undefined
        ? hoverValue
        : [
            "case",
            ["boolean", ["feature-state", "hover"], false],
            hoverValue,
            baseValue,
          ];
  }
  return merged;
}

/** Plain, JSON-serialisable copy of a MapLibre rendered feature. */
function serializeFeature(feature) {
  if (!feature) return null;
  return {
    type: "Feature",
    id: feature.id ?? null,
    properties: feature.properties ?? {},
    geometry: feature.geometry ?? null,
    source: feature.source ?? null,
    sourceLayer: feature.sourceLayer ?? null,
  };
}

function toLngLat(lngLat) {
  return { lng: lngLat.lng, lat: lngLat.lat };
}

// ---------------------------------------------------------------------------
// Theme detection
// ---------------------------------------------------------------------------

// Check the document for an explicit theme (works with next-themes / Reflex).
// Covers both the `class` attribute (the default) and `data-theme`.
function getDocumentTheme() {
  if (typeof document === "undefined") return null;
  const root = document.documentElement;
  if (root.classList.contains("dark")) return "dark";
  if (root.classList.contains("light")) return "light";
  const dataTheme = root.dataset.theme;
  if (dataTheme === "dark" || dataTheme === "light") return dataTheme;
  return null;
}

function getSystemTheme() {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function useResolvedTheme(themeProp) {
  const [detectedTheme, setDetectedTheme] = useState(
    () => getDocumentTheme() ?? getSystemTheme(),
  );

  useEffect(() => {
    if (themeProp) return;

    const observer = new MutationObserver(() => {
      const docTheme = getDocumentTheme();
      if (docTheme) setDetectedTheme(docTheme);
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class", "data-theme"],
    });

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleSystemChange = (e) => {
      if (!getDocumentTheme()) setDetectedTheme(e.matches ? "dark" : "light");
    };
    mediaQuery.addEventListener("change", handleSystemChange);

    return () => {
      observer.disconnect();
      mediaQuery.removeEventListener("change", handleSystemChange);
    };
  }, [themeProp]);

  return themeProp ?? detectedTheme;
}

// ---------------------------------------------------------------------------
// Map context
// ---------------------------------------------------------------------------

const MapContext = createContext(null);

function useMap() {
  const context = useContext(MapContext);
  if (!context) {
    throw new Error("useMap must be used within a Map component");
  }
  return context;
}

function DefaultLoader() {
  return (
    <div className="mapcn-loader">
      <div className="mapcn-loader-dots">
        <span className="mapcn-loader-dot" />
        <span className="mapcn-loader-dot" />
        <span className="mapcn-loader-dot" />
      </div>
    </div>
  );
}

function getViewport(map) {
  const center = map.getCenter();
  return {
    center: [center.lng, center.lat],
    zoom: map.getZoom(),
    bearing: map.getBearing(),
    pitch: map.getPitch(),
  };
}

/** Keys that are Reflex/React concerns and must never reach MapLibre. */
const NON_MAPLIBRE_PROPS = new Set(["id", "style", "key", "ref"]);

// ---------------------------------------------------------------------------
// Map
// ---------------------------------------------------------------------------

const Map = forwardRef(function Map(
  {
    children,
    className,
    style: containerStyle,
    theme: themeProp,
    styles,
    blank = false,
    projection,
    viewport,
    onViewportChange,
    onMoveEnd,
    onClick,
    onLoad,
    loading = false,
    workerUrl,
    ...props
  },
  ref,
) {
  const containerRef = useRef(null);
  const [mapInstance, setMapInstance] = useState(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [isStyleLoaded, setIsStyleLoaded] = useState(false);
  const [pendingStyle, setPendingStyle] = useState(null);
  const currentStyleRef = useRef(null);
  const styleSwapInFlightRef = useRef(false);
  const internalUpdateRef = useRef(false);
  const resolvedTheme = useResolvedTheme(themeProp);

  const isControlled = viewport !== undefined && onViewportChange !== undefined;

  const callbacksRef = useRef({ onViewportChange, onMoveEnd, onClick, onLoad });
  callbacksRef.current = { onViewportChange, onMoveEnd, onClick, onLoad };

  const stableStyles = useStableValue(styles);
  const stableProjection = useStableValue(projection);

  const mapStyles = useMemo(() => {
    // An empty `styles` object (easy to produce from Reflex state) counts as
    // "no custom styles" so `blank` / the defaults still apply.
    if (stableStyles && (stableStyles.light || stableStyles.dark)) {
      return {
        dark: stableStyles.dark ?? defaultStyles.dark,
        light: stableStyles.light ?? defaultStyles.light,
      };
    }
    if (blank) return { dark: blankMapStyle, light: blankMapStyle };
    return defaultStyles;
  }, [stableStyles, blank]);

  useImperativeHandle(ref, () => mapInstance, [mapInstance]);

  // Initialize the map
  useEffect(() => {
    if (!containerRef.current) return;

    if (workerUrl) setWorkerUrl(workerUrl);

    const initialStyle =
      resolvedTheme === "dark" ? mapStyles.dark : mapStyles.light;
    currentStyleRef.current = initialStyle;

    const mapOptions = {};
    for (const [key, value] of Object.entries(props)) {
      if (NON_MAPLIBRE_PROPS.has(key) || value === undefined) continue;
      mapOptions[key] = value;
    }

    const map = new MapLibreGL.Map({
      container: containerRef.current,
      style: initialStyle,
      renderWorldCopies: false,
      attributionControl: { compact: true },
      ...(stableProjection ? { projection: stableProjection } : {}),
      ...mapOptions,
      ...viewport,
    });

    const styleLoadHandler = () => {
      styleSwapInFlightRef.current = false;
      setIsStyleLoaded(true);
    };
    const loadHandler = () => {
      setIsLoaded(true);
      callbacksRef.current.onLoad?.(getViewport(map));
    };
    const handleMove = () => {
      if (internalUpdateRef.current) return;
      callbacksRef.current.onViewportChange?.(getViewport(map));
    };
    const handleMoveEnd = () => {
      if (internalUpdateRef.current) return;
      callbacksRef.current.onMoveEnd?.(getViewport(map));
    };
    const handleClick = (e) => {
      callbacksRef.current.onClick?.({
        lng: e.lngLat.lng,
        lat: e.lngLat.lat,
        point: { x: e.point.x, y: e.point.y },
      });
    };

    map.on("load", loadHandler);
    map.on("style.load", styleLoadHandler);
    map.on("move", handleMove);
    map.on("moveend", handleMoveEnd);
    map.on("click", handleClick);
    setMapInstance(map);

    return () => {
      map.off("load", loadHandler);
      map.off("style.load", styleLoadHandler);
      map.off("move", handleMove);
      map.off("moveend", handleMoveEnd);
      map.off("click", handleClick);
      map.remove();
      setIsLoaded(false);
      setIsStyleLoaded(false);
      setMapInstance(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync controlled viewport to map
  const stableViewport = useStableValue(viewport);
  useEffect(() => {
    if (!mapInstance || !isControlled || !stableViewport) return;
    if (mapInstance.isMoving()) return;

    const current = getViewport(mapInstance);
    const next = {
      center: stableViewport.center ?? current.center,
      zoom: stableViewport.zoom ?? current.zoom,
      bearing: stableViewport.bearing ?? current.bearing,
      pitch: stableViewport.pitch ?? current.pitch,
    };

    if (
      next.center[0] === current.center[0] &&
      next.center[1] === current.center[1] &&
      next.zoom === current.zoom &&
      next.bearing === current.bearing &&
      next.pitch === current.pitch
    ) {
      return;
    }

    internalUpdateRef.current = true;
    mapInstance.jumpTo(next);
    internalUpdateRef.current = false;
  }, [mapInstance, isControlled, stableViewport]);

  // Handle style change (theme toggle or `styles` prop update).
  useEffect(() => {
    if (!mapInstance || !resolvedTheme) return;
    const newStyle =
      resolvedTheme === "dark" ? mapStyles.dark : mapStyles.light;
    if (currentStyleRef.current === newStyle) return;
    currentStyleRef.current = newStyle;
    setIsStyleLoaded(false);
    setPendingStyle(newStyle);
  }, [mapInstance, resolvedTheme, mapStyles]);

  useEffect(() => {
    if (!mapInstance || !pendingStyle) return;
    setPendingStyle(null);
    styleSwapInFlightRef.current = true;
    // Full reload (no diff) so `style.load` fires deterministically.
    mapInstance.setStyle(pendingStyle, { diff: false });
  }, [mapInstance, pendingStyle]);

  // Sync projection when the prop changes after mount.
  useEffect(() => {
    if (!mapInstance || !isStyleLoaded || !stableProjection) return;
    if (styleSwapInFlightRef.current) return;
    mapInstance.setProjection(stableProjection);
  }, [mapInstance, isStyleLoaded, stableProjection]);

  const contextValue = useMemo(
    () => ({
      map: mapInstance,
      isLoaded: isLoaded && isStyleLoaded,
      resolvedTheme,
    }),
    [mapInstance, isLoaded, isStyleLoaded, resolvedTheme],
  );

  return (
    <MapContext.Provider value={contextValue}>
      <div
        ref={containerRef}
        id={props.id}
        style={containerStyle}
        className={cn("mapcn-map", className)}
        data-mapcn-theme={resolvedTheme}
      >
        {(!isLoaded || loading) && <DefaultLoader />}
        {mapInstance && children}
      </div>
    </MapContext.Provider>
  );
});

// ---------------------------------------------------------------------------
// Markers
// ---------------------------------------------------------------------------

const MarkerContext = createContext(null);

function useMarkerContext() {
  const context = useContext(MarkerContext);
  if (!context) {
    throw new Error("Marker components must be used within MapMarker");
  }
  return context;
}

function MapMarker({
  longitude,
  latitude,
  children,
  onClick,
  onMouseEnter,
  onMouseLeave,
  onDragStart,
  onDrag,
  onDragEnd,
  draggable = false,
  ...markerOptions
}) {
  const { map } = useMap();

  const callbacksRef = useRef({});
  callbacksRef.current = {
    onClick,
    onMouseEnter,
    onMouseLeave,
    onDragStart,
    onDrag,
    onDragEnd,
  };

  const marker = useMemo(() => {
    const markerInstance = new MapLibreGL.Marker({
      ...markerOptions,
      element: document.createElement("div"),
      draggable,
    }).setLngLat([longitude, latitude]);

    const handleClick = (e) => {
      // Do not let the click bubble to the map (`Map.onClick`).
      e.stopPropagation();
      callbacksRef.current.onClick?.(toLngLat(markerInstance.getLngLat()));
    };
    const handleMouseEnter = () =>
      callbacksRef.current.onMouseEnter?.(toLngLat(markerInstance.getLngLat()));
    const handleMouseLeave = () =>
      callbacksRef.current.onMouseLeave?.(toLngLat(markerInstance.getLngLat()));

    const element = markerInstance.getElement();
    element?.addEventListener("click", handleClick);
    element?.addEventListener("mouseenter", handleMouseEnter);
    element?.addEventListener("mouseleave", handleMouseLeave);

    markerInstance.on("dragstart", () =>
      callbacksRef.current.onDragStart?.(toLngLat(markerInstance.getLngLat())),
    );
    markerInstance.on("drag", () =>
      callbacksRef.current.onDrag?.(toLngLat(markerInstance.getLngLat())),
    );
    markerInstance.on("dragend", () =>
      callbacksRef.current.onDragEnd?.(toLngLat(markerInstance.getLngLat())),
    );

    return markerInstance;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!map) return;
    marker.addTo(map);
    return () => {
      marker.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map]);

  const { offset, rotation, rotationAlignment, pitchAlignment } = markerOptions;
  const stableOffset = useStableValue(offset);

  useEffect(() => {
    const current = marker.getLngLat();
    if (current.lng !== longitude || current.lat !== latitude) {
      marker.setLngLat([longitude, latitude]);
    }
    if (marker.isDraggable() !== draggable) marker.setDraggable(draggable);

    const currentOffset = marker.getOffset();
    const newOffset = stableOffset ?? [0, 0];
    const [newOffsetX, newOffsetY] = Array.isArray(newOffset)
      ? newOffset
      : [newOffset.x, newOffset.y];
    if (currentOffset.x !== newOffsetX || currentOffset.y !== newOffsetY) {
      marker.setOffset(newOffset);
    }

    if (marker.getRotation() !== (rotation ?? 0)) {
      marker.setRotation(rotation ?? 0);
    }
    if (marker.getRotationAlignment() !== (rotationAlignment ?? "auto")) {
      marker.setRotationAlignment(rotationAlignment ?? "auto");
    }
    if (marker.getPitchAlignment() !== (pitchAlignment ?? "auto")) {
      marker.setPitchAlignment(pitchAlignment ?? "auto");
    }
  }, [
    marker,
    longitude,
    latitude,
    draggable,
    stableOffset,
    rotation,
    rotationAlignment,
    pitchAlignment,
  ]);

  const markerContext = useMemo(() => ({ marker, map }), [marker, map]);

  return (
    <MarkerContext.Provider value={markerContext}>
      {children}
    </MarkerContext.Provider>
  );
}

function DefaultMarkerIcon() {
  return <div className="mapcn-marker-default" />;
}

function MarkerContent({ children, className, style }) {
  const { marker } = useMarkerContext();

  return createPortal(
    <div className={cn("mapcn-marker-content", className)} style={style}>
      {children || <DefaultMarkerIcon />}
    </div>,
    marker.getElement(),
  );
}

function IconX() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="14"
      height="14"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M18 6 6 18" />
      <path d="m6 6 12 12" />
    </svg>
  );
}

function PopupCloseButton({ onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Close popup"
      className="mapcn-popup-close"
    >
      <IconX />
    </button>
  );
}

function MarkerPopup({
  children,
  className,
  style,
  closeButton = false,
  ...popupOptions
}) {
  const { marker, map } = useMarkerContext();
  const container = useMemo(() => document.createElement("div"), []);
  const { offset, maxWidth } = popupOptions;
  const stableOffset = useStableValue(offset);

  const popup = useMemo(() => {
    return new MapLibreGL.Popup({
      offset: 16,
      ...popupOptions,
      closeButton: false,
    })
      .setMaxWidth("none")
      .setDOMContent(container);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!map) return;
    popup.setDOMContent(container);
    marker.setPopup(popup);
    return () => {
      marker.setPopup(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map]);

  useEffect(() => {
    popup.setOffset(stableOffset ?? 16);
    if (maxWidth) popup.setMaxWidth(maxWidth);
  }, [popup, stableOffset, maxWidth]);

  const handleClose = () => popup.remove();

  return createPortal(
    <div className={cn("mapcn-popup", className)} style={style}>
      {closeButton && <PopupCloseButton onClick={handleClose} />}
      {children}
    </div>,
    container,
  );
}

function MarkerTooltip({ children, className, style, ...popupOptions }) {
  const { marker, map } = useMarkerContext();
  const container = useMemo(() => document.createElement("div"), []);
  const { offset, maxWidth } = popupOptions;
  const stableOffset = useStableValue(offset);

  const tooltip = useMemo(() => {
    return new MapLibreGL.Popup({
      offset: 16,
      ...popupOptions,
      closeOnClick: true,
      closeButton: false,
    }).setMaxWidth("none");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!map) return;
    tooltip.setDOMContent(container);

    const handleMouseEnter = () => {
      tooltip.setLngLat(marker.getLngLat()).addTo(map);
    };
    const handleMouseLeave = () => tooltip.remove();

    const element = marker.getElement();
    element?.addEventListener("mouseenter", handleMouseEnter);
    element?.addEventListener("mouseleave", handleMouseLeave);

    return () => {
      element?.removeEventListener("mouseenter", handleMouseEnter);
      element?.removeEventListener("mouseleave", handleMouseLeave);
      tooltip.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map]);

  useEffect(() => {
    tooltip.setOffset(stableOffset ?? 16);
    if (maxWidth) tooltip.setMaxWidth(maxWidth);
  }, [tooltip, stableOffset, maxWidth]);

  return createPortal(
    <div className={cn("mapcn-tooltip", className)} style={style}>
      {children}
    </div>,
    container,
  );
}

function MarkerLabel({ children, className, style, position = "top" }) {
  return (
    <div
      className={cn(
        "mapcn-marker-label",
        position === "bottom"
          ? "mapcn-marker-label-bottom"
          : "mapcn-marker-label-top",
        className,
      )}
      style={style}
    >
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Controls
// ---------------------------------------------------------------------------

const positionClasses = {
  "top-left": "mapcn-controls-top-left",
  "top-right": "mapcn-controls-top-right",
  "bottom-left": "mapcn-controls-bottom-left",
  "bottom-right": "mapcn-controls-bottom-right",
};

function ControlGroup({ children }) {
  return <div className="mapcn-control-group">{children}</div>;
}

function ControlButton({ onClick, label, children, disabled = false }) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      type="button"
      className="mapcn-control-button"
      disabled={disabled}
    >
      {children}
    </button>
  );
}

const iconProps = {
  viewBox: "0 0 24 24",
  width: "16",
  height: "16",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: "2",
  strokeLinecap: "round",
  strokeLinejoin: "round",
};

function IconPlus() {
  return (
    <svg {...iconProps}>
      <path d="M5 12h14" />
      <path d="M12 5v14" />
    </svg>
  );
}

function IconMinus() {
  return (
    <svg {...iconProps}>
      <path d="M5 12h14" />
    </svg>
  );
}

function IconLocate() {
  return (
    <svg {...iconProps}>
      <line x1="2" x2="5" y1="12" y2="12" />
      <line x1="19" x2="22" y1="12" y2="12" />
      <line x1="12" x2="12" y1="2" y2="5" />
      <line x1="12" x2="12" y1="19" y2="22" />
      <circle cx="12" cy="12" r="7" />
    </svg>
  );
}

function IconMaximize() {
  return (
    <svg {...iconProps}>
      <path d="M8 3H5a2 2 0 0 0-2 2v3" />
      <path d="M21 8V5a2 2 0 0 0-2-2h-3" />
      <path d="M3 16v3a2 2 0 0 0 2 2h3" />
      <path d="M16 21h3a2 2 0 0 0 2-2v-3" />
    </svg>
  );
}

function IconLoader() {
  return (
    <svg {...iconProps} className="mapcn-spin">
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}

function CompassButton({ onClick }) {
  const { map } = useMap();
  const compassRef = useRef(null);

  useEffect(() => {
    if (!map || !compassRef.current) return;
    const compass = compassRef.current;

    const updateRotation = () => {
      const bearing = map.getBearing();
      const pitch = map.getPitch();
      compass.style.transform = `rotateX(${pitch}deg) rotateZ(${-bearing}deg)`;
    };

    map.on("rotate", updateRotation);
    map.on("pitch", updateRotation);
    updateRotation();

    return () => {
      map.off("rotate", updateRotation);
      map.off("pitch", updateRotation);
    };
  }, [map]);

  return (
    <ControlButton onClick={onClick} label="Reset bearing to north">
      <svg
        ref={compassRef}
        viewBox="0 0 24 24"
        width="20"
        height="20"
        style={{ transformStyle: "preserve-3d" }}
      >
        <path d="M12 2L16 12H12V2Z" fill="#ef4444" />
        <path d="M12 2L8 12H12V2Z" fill="#fca5a5" />
        <path d="M12 22L16 12H12V22Z" className="mapcn-compass-south" />
        <path d="M12 22L8 12H12V22Z" className="mapcn-compass-south-light" />
      </svg>
    </ControlButton>
  );
}

function MapControls({
  position = "bottom-right",
  showZoom = true,
  showCompass = false,
  showLocate = false,
  showFullscreen = false,
  className,
  style,
  onLocate,
}) {
  const { map } = useMap();
  const [waitingForLocation, setWaitingForLocation] = useState(false);

  const handleZoomIn = useCallback(() => {
    map?.zoomTo(map.getZoom() + 1, { duration: 300 });
  }, [map]);

  const handleZoomOut = useCallback(() => {
    map?.zoomTo(map.getZoom() - 1, { duration: 300 });
  }, [map]);

  const handleResetBearing = useCallback(() => {
    map?.resetNorthPitch({ duration: 300 });
  }, [map]);

  const handleLocate = useCallback(() => {
    if (!("geolocation" in navigator)) return;
    setWaitingForLocation(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const coords = {
          longitude: pos.coords.longitude,
          latitude: pos.coords.latitude,
        };
        map?.flyTo({
          center: [coords.longitude, coords.latitude],
          zoom: 14,
          duration: 1500,
        });
        onLocate?.(coords);
        setWaitingForLocation(false);
      },
      (error) => {
        console.error("Error getting location:", error);
        setWaitingForLocation(false);
      },
      { timeout: 10000 },
    );
  }, [map, onLocate]);

  const handleFullscreen = useCallback(() => {
    const container = map?.getContainer();
    if (!container) return;
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      container.requestFullscreen();
    }
  }, [map]);

  return (
    <div
      className={cn("mapcn-controls", positionClasses[position], className)}
      style={style}
    >
      {showZoom && (
        <ControlGroup>
          <ControlButton onClick={handleZoomIn} label="Zoom in">
            <IconPlus />
          </ControlButton>
          <ControlButton onClick={handleZoomOut} label="Zoom out">
            <IconMinus />
          </ControlButton>
        </ControlGroup>
      )}
      {showCompass && (
        <ControlGroup>
          <CompassButton onClick={handleResetBearing} />
        </ControlGroup>
      )}
      {showLocate && (
        <ControlGroup>
          <ControlButton
            onClick={handleLocate}
            label="Find my location"
            disabled={waitingForLocation}
          >
            {waitingForLocation ? <IconLoader /> : <IconLocate />}
          </ControlButton>
        </ControlGroup>
      )}
      {showFullscreen && (
        <ControlGroup>
          <ControlButton onClick={handleFullscreen} label="Toggle fullscreen">
            <IconMaximize />
          </ControlButton>
        </ControlGroup>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Standalone popup
// ---------------------------------------------------------------------------

function MapPopup({
  longitude,
  latitude,
  onClose,
  children,
  className,
  style,
  closeButton = false,
  ...popupOptions
}) {
  const { map } = useMap();
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  const container = useMemo(() => document.createElement("div"), []);
  const { offset, maxWidth } = popupOptions;
  const stableOffset = useStableValue(offset);

  const popup = useMemo(() => {
    return new MapLibreGL.Popup({
      offset: 16,
      ...popupOptions,
      closeButton: false,
    })
      .setMaxWidth("none")
      .setLngLat([longitude, latitude]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!map) return;
    const onCloseProp = () => onCloseRef.current?.();
    popup.on("close", onCloseProp);
    popup.setDOMContent(container);
    popup.addTo(map);
    return () => {
      popup.off("close", onCloseProp);
      if (popup.isOpen()) popup.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map]);

  useEffect(() => {
    const current = popup.getLngLat();
    if (!current || current.lng !== longitude || current.lat !== latitude) {
      popup.setLngLat([longitude, latitude]);
    }
    popup.setOffset(stableOffset ?? 16);
    if (maxWidth) popup.setMaxWidth(maxWidth);
  }, [popup, longitude, latitude, stableOffset, maxWidth]);

  const handleClose = () => popup.remove();

  return createPortal(
    <div className={cn("mapcn-popup", className)} style={style}>
      {closeButton && <PopupCloseButton onClick={handleClose} />}
      {children}
    </div>,
    container,
  );
}

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------

const EMPTY_ROUTE_MEASURE = { cumulative: [], total: 0 };
const EMPTY_COORDINATES = [];

/** `beforeId`, but only when that layer is actually in the style. */
function resolveBeforeId(map, beforeId) {
  return beforeId && map.getLayer(beforeId) ? beforeId : undefined;
}

function clampFraction(value) {
  if (!Number.isFinite(value)) return 0;
  return Math.min(1, Math.max(0, value));
}

function measureRoute(coordinates) {
  if (coordinates.length < 2) return EMPTY_ROUTE_MEASURE;
  const cumulative = [0];
  let total = 0;
  for (let i = 1; i < coordinates.length; i += 1) {
    const [lng1, lat1] = coordinates[i - 1];
    const [lng2, lat2] = coordinates[i];
    const midLat = ((lat1 + lat2) / 2) * (Math.PI / 180);
    total += Math.hypot((lng2 - lng1) * Math.cos(midLat), lat2 - lat1);
    cumulative.push(total);
  }
  return { cumulative, total };
}

function findSegmentIndex(cumulative, distance) {
  let low = 0;
  let high = cumulative.length - 1;
  while (low < high) {
    const mid = Math.floor((low + high) / 2);
    if (cumulative[mid] < distance) low = mid + 1;
    else high = mid;
  }
  return Math.min(low === 0 ? 0 : low - 1, cumulative.length - 2);
}

function pointAtFraction(coordinates, measure, fraction) {
  if (coordinates.length === 0) return null;
  if (coordinates.length === 1 || measure.total === 0) return coordinates[0];
  const target = measure.total * clampFraction(fraction);
  const index = findSegmentIndex(measure.cumulative, target);
  const [lng1, lat1] = coordinates[index];
  const [lng2, lat2] = coordinates[index + 1];
  const segment = measure.cumulative[index + 1] - measure.cumulative[index];
  const ratio =
    segment === 0 ? 0 : (target - measure.cumulative[index]) / segment;
  return [lng1 + (lng2 - lng1) * ratio, lat1 + (lat2 - lat1) * ratio];
}

function sliceAtFraction(coordinates, measure, fraction) {
  if (coordinates.length < 2) return [];
  const t = clampFraction(fraction);
  if (t <= 0 || measure.total === 0) return [];
  if (t >= 1) return coordinates;
  const target = measure.total * t;
  const index = findSegmentIndex(measure.cumulative, target);
  const point = pointAtFraction(coordinates, measure, t);
  const traveled = coordinates.slice(0, index + 1);
  if (point) traveled.push(point);
  return traveled;
}

const RouteContext = createContext(null);

function useMapRoute() {
  const context = useContext(RouteContext);
  if (!context) {
    throw new Error("Route components must be used within MapRoute");
  }
  return context;
}

function MapRoute({
  id: propId,
  coordinates: coordinatesProp,
  color = "#4285F4",
  width = 3,
  opacity = 0.8,
  dashArray,
  progress,
  active = false,
  activeColor,
  activeWidth,
  activeOpacity,
  activeDashArray,
  beforeId,
  onClick,
  onMouseEnter,
  onMouseLeave,
  interactive = true,
  children,
}) {
  const { map, isLoaded } = useMap();
  const autoId = useId();
  const id = propId ?? autoId;
  const sourceId = `route-source-${id}`;
  const layerId = `route-layer-${id}`;
  const [ready, setReady] = useState(false);

  const stableCoordinates = useStableValue(coordinatesProp ?? EMPTY_COORDINATES);
  const coordinates =
    stableCoordinates.length > 0 ? stableCoordinates : EMPTY_COORDINATES;

  const stableDashArray = useStableValue(dashArray);
  const stableActiveDashArray = useStableValue(activeDashArray);

  const resolvedColor = active ? (activeColor ?? color) : color;
  const resolvedWidth = active ? (activeWidth ?? width) : width;
  const resolvedOpacity = active ? (activeOpacity ?? opacity) : opacity;
  const resolvedDashArray = active
    ? (stableActiveDashArray ?? stableDashArray)
    : stableDashArray;

  const measure = useMemo(() => measureRoute(coordinates), [coordinates]);
  const traveled = useMemo(
    () =>
      progress === undefined || progress === null
        ? []
        : sliceAtFraction(coordinates, measure, progress),
    [coordinates, measure, progress],
  );

  const pointAt = useCallback(
    (at) => {
      if (coordinates.length === 0) return null;
      if (at === "start") return coordinates[0];
      if (at === "end") return coordinates[coordinates.length - 1];
      if (at === "progress") {
        if (progress === undefined || progress === null) return null;
        return pointAtFraction(coordinates, measure, progress);
      }
      return pointAtFraction(coordinates, measure, Number(at));
    },
    [coordinates, measure, progress],
  );

  const childLayersRef = useRef([]);
  const registerLayer = useCallback((childLayerId) => {
    childLayersRef.current = [...childLayersRef.current, childLayerId];
    return () => {
      childLayersRef.current = childLayersRef.current.filter(
        (entry) => entry !== childLayerId,
      );
    };
  }, []);

  const callbacksRef = useRef({});
  callbacksRef.current = { onClick, onMouseEnter, onMouseLeave };

  // Add source and layer on mount
  useEffect(() => {
    if (!isLoaded || !map) return;

    map.addSource(sourceId, {
      type: "geojson",
      data: {
        type: "Feature",
        properties: {},
        geometry: { type: "LineString", coordinates: [] },
      },
    });

    map.addLayer(
      {
        id: layerId,
        type: "line",
        source: sourceId,
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": resolvedColor,
          "line-width": resolvedWidth,
          "line-opacity": resolvedOpacity,
          ...(resolvedDashArray && { "line-dasharray": resolvedDashArray }),
        },
      },
      resolveBeforeId(map, beforeId),
    );

    setReady(true);

    return () => {
      setReady(false);
      try {
        if (map.getLayer(layerId)) map.removeLayer(layerId);
        if (map.getSource(sourceId)) map.removeSource(sourceId);
      } catch {
        // ignore
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, map]);

  // When coordinates change, update the source data
  useEffect(() => {
    if (!isLoaded || !map) return;
    const source = map.getSource(sourceId);
    if (source) {
      source.setData({
        type: "Feature",
        properties: {},
        geometry: {
          type: "LineString",
          coordinates: coordinates.length < 2 ? [] : coordinates,
        },
      });
    }
  }, [isLoaded, map, coordinates, sourceId]);

  useEffect(() => {
    if (!isLoaded || !map || !map.getLayer(layerId)) return;
    map.setPaintProperty(layerId, "line-color", resolvedColor);
    map.setPaintProperty(layerId, "line-width", resolvedWidth);
    map.setPaintProperty(layerId, "line-opacity", resolvedOpacity);
    map.setPaintProperty(layerId, "line-dasharray", resolvedDashArray);
  }, [
    isLoaded,
    map,
    layerId,
    resolvedColor,
    resolvedWidth,
    resolvedOpacity,
    resolvedDashArray,
  ]);

  // Raise the active route (and anything it owns) above its siblings.
  useEffect(() => {
    if (!ready || !map || !active) return;

    let lastLayerSet = "";

    const raise = () => {
      const order = map.getLayersOrder();
      const layerSet = [...order].sort().join("|");
      if (layerSet === lastLayerSet) return;
      lastLayerSet = layerSet;

      const owned = [layerId, ...childLayersRef.current].filter((entry) =>
        map.getLayer(entry),
      );
      if (owned.length === 0) return;

      const before = resolveBeforeId(map, beforeId);
      const limit = before ? order.indexOf(before) : order.length;
      const top = order.slice(Math.max(0, limit - owned.length), limit);
      if (owned.every((entry, index) => top[index] === entry)) return;

      for (const entry of owned) map.moveLayer(entry, before);
    };

    raise();
    map.on("styledata", raise);
    return () => {
      map.off("styledata", raise);
    };
  }, [ready, map, active, layerId, beforeId]);

  // Handle click and hover events
  useEffect(() => {
    if (!isLoaded || !map || !interactive) return;

    const handleClick = (e) => {
      callbacksRef.current.onClick?.({ lng: e.lngLat.lng, lat: e.lngLat.lat });
    };
    const handleMouseEnter = (e) => {
      map.getCanvas().style.cursor = "pointer";
      callbacksRef.current.onMouseEnter?.({
        lng: e.lngLat.lng,
        lat: e.lngLat.lat,
      });
    };
    const handleMouseLeave = () => {
      map.getCanvas().style.cursor = "";
      callbacksRef.current.onMouseLeave?.();
    };

    map.on("click", layerId, handleClick);
    map.on("mouseenter", layerId, handleMouseEnter);
    map.on("mouseleave", layerId, handleMouseLeave);

    return () => {
      map.off("click", layerId, handleClick);
      map.off("mouseenter", layerId, handleMouseEnter);
      map.off("mouseleave", layerId, handleMouseLeave);
    };
  }, [isLoaded, map, layerId, interactive]);

  const contextValue = useMemo(
    () => ({
      id,
      ready,
      coordinates,
      traveled,
      progress,
      color: resolvedColor,
      width: resolvedWidth,
      opacity: resolvedOpacity,
      dashArray: resolvedDashArray,
      beforeId,
      pointAt,
      registerLayer,
    }),
    [
      id,
      ready,
      coordinates,
      traveled,
      progress,
      resolvedColor,
      resolvedWidth,
      resolvedOpacity,
      resolvedDashArray,
      beforeId,
      pointAt,
      registerLayer,
    ],
  );

  return (
    <RouteContext.Provider value={contextValue}>
      {children}
    </RouteContext.Provider>
  );
}

function RouteProgress({ color, width, opacity, dashArray }) {
  const { map, isLoaded } = useMap();
  const route = useMapRoute();
  const { ready, traveled, registerLayer, beforeId } = route;

  const sourceId = `route-progress-source-${route.id}`;
  const layerId = `route-progress-layer-${route.id}`;

  const resolvedColor = color ?? route.color;
  const resolvedWidth = width ?? route.width;
  const resolvedOpacity = opacity ?? route.opacity;
  const stableDashArray = useStableValue(dashArray);

  useEffect(() => {
    if (!ready || !map) return;

    map.addSource(sourceId, {
      type: "geojson",
      data: {
        type: "Feature",
        properties: {},
        geometry: { type: "LineString", coordinates: [] },
      },
    });

    map.addLayer(
      {
        id: layerId,
        type: "line",
        source: sourceId,
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": resolvedColor,
          "line-width": resolvedWidth,
          "line-opacity": resolvedOpacity,
          ...(stableDashArray && { "line-dasharray": stableDashArray }),
        },
      },
      resolveBeforeId(map, beforeId),
    );

    const unregister = registerLayer(layerId);

    return () => {
      unregister();
      try {
        if (map.getLayer(layerId)) map.removeLayer(layerId);
        if (map.getSource(sourceId)) map.removeSource(sourceId);
      } catch {
        // ignore
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, map]);

  useEffect(() => {
    if (!ready || !map) return;
    const source = map.getSource(sourceId);
    if (source) {
      source.setData({
        type: "Feature",
        properties: {},
        geometry: {
          type: "LineString",
          coordinates: traveled.length < 2 ? [] : traveled,
        },
      });
    }
  }, [ready, map, traveled, sourceId]);

  useEffect(() => {
    if (!isLoaded || !map || !map.getLayer(layerId)) return;
    map.setPaintProperty(layerId, "line-color", resolvedColor);
    map.setPaintProperty(layerId, "line-width", resolvedWidth);
    map.setPaintProperty(layerId, "line-opacity", resolvedOpacity);
    map.setPaintProperty(layerId, "line-dasharray", stableDashArray);
  }, [
    isLoaded,
    map,
    layerId,
    resolvedColor,
    resolvedWidth,
    resolvedOpacity,
    stableDashArray,
  ]);

  return null;
}

function RouteMarker({ at, children, ...markerProps }) {
  const { pointAt } = useMapRoute();
  const position = pointAt(at);
  if (!position) return null;
  return (
    <MapMarker longitude={position[0]} latitude={position[1]} {...markerProps}>
      {children}
    </MapMarker>
  );
}

// ---------------------------------------------------------------------------
// GeoJSON
// ---------------------------------------------------------------------------

const GEOJSON_DEFAULT_COLORS = {
  light: { fill: "#d4d4d4", line: "#ffffff" },
  dark: { fill: "#404040", line: "#171717" },
};

function MapGeoJSON({
  data,
  id: propId,
  promoteId,
  fillPaint,
  linePaint,
  fillHoverPaint,
  onClick,
  onHover,
  interactive = false,
  beforeId,
}) {
  const { map, isLoaded, resolvedTheme } = useMap();
  const autoId = useId();
  const id = propId ?? autoId;
  const sourceId = `geojson-source-${id}`;
  const fillLayerId = `geojson-fill-${id}`;
  const lineLayerId = `geojson-line-${id}`;

  const defaults = GEOJSON_DEFAULT_COLORS[resolvedTheme] ?? GEOJSON_DEFAULT_COLORS.light;

  const showFill = fillPaint !== false;
  const showLine = linePaint !== false;

  const stableData = useStableValue(data);
  const stableFillPaint = useStableValue(fillPaint);
  const stableLinePaint = useStableValue(linePaint);
  const stableFillHoverPaint = useStableValue(fillHoverPaint);

  const mergedFillPaint = useMemo(
    () =>
      mergeHoverPaint(
        { "fill-color": defaults.fill, ...(stableFillPaint || {}) },
        stableFillHoverPaint,
      ),
    [defaults.fill, stableFillPaint, stableFillHoverPaint],
  );
  const mergedLinePaint = useMemo(
    () => ({
      "line-color": defaults.line,
      "line-width": 0.5,
      ...(stableLinePaint || {}),
    }),
    [defaults.line, stableLinePaint],
  );
  const latestRef = useRef({ onClick, onHover });
  latestRef.current = { onClick, onHover };

  // Add source on mount.
  useEffect(() => {
    if (!isLoaded || !map) return;

    map.addSource(sourceId, {
      type: "geojson",
      data: stableData,
      ...(promoteId ? { promoteId } : {}),
    });

    return () => {
      try {
        if (map.getLayer(lineLayerId)) map.removeLayer(lineLayerId);
        if (map.getLayer(fillLayerId)) map.removeLayer(fillLayerId);
        if (map.getSource(sourceId)) map.removeSource(sourceId);
      } catch {
        // style may be mid-reload
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, map]);

  // Sync data when it changes.
  useEffect(() => {
    if (!isLoaded || !map) return;
    const source = map.getSource(sourceId);
    source?.setData(stableData);
  }, [isLoaded, map, stableData, sourceId]);

  // Sync layers and paint when visibility or styling changes.
  useEffect(() => {
    if (!isLoaded || !map) return;
    const source = map.getSource(sourceId);
    if (!source) return;

    if (showFill && !map.getLayer(fillLayerId)) {
      map.addLayer(
        { id: fillLayerId, type: "fill", source: sourceId, paint: mergedFillPaint },
        resolveBeforeId(map, beforeId),
      );
    } else if (!showFill && map.getLayer(fillLayerId)) {
      map.removeLayer(fillLayerId);
    }

    if (showLine && !map.getLayer(lineLayerId)) {
      map.addLayer(
        { id: lineLayerId, type: "line", source: sourceId, paint: mergedLinePaint },
        resolveBeforeId(map, beforeId),
      );
    } else if (!showLine && map.getLayer(lineLayerId)) {
      map.removeLayer(lineLayerId);
    }

    if (showFill && map.getLayer(fillLayerId)) {
      for (const [key, value] of Object.entries(mergedFillPaint)) {
        map.setPaintProperty(fillLayerId, key, value);
      }
    }
    if (showLine && map.getLayer(lineLayerId)) {
      for (const [key, value] of Object.entries(mergedLinePaint)) {
        map.setPaintProperty(lineLayerId, key, value);
      }
    }
  }, [
    isLoaded,
    map,
    sourceId,
    fillLayerId,
    lineLayerId,
    showFill,
    showLine,
    mergedFillPaint,
    mergedLinePaint,
    beforeId,
  ]);

  // Interaction handlers (bound to the fill layer).
  useEffect(() => {
    if (!isLoaded || !map || !interactive || !showFill) return;

    let hoveredId = null;

    const setHover = (next) => {
      if (next === hoveredId) return;
      const sourceExists = !!map.getSource(sourceId);
      if (hoveredId != null && sourceExists) {
        map.setFeatureState({ source: sourceId, id: hoveredId }, { hover: false });
      }
      hoveredId = next;
      if (next != null && sourceExists) {
        map.setFeatureState({ source: sourceId, id: next }, { hover: true });
      }
    };

    const payload = (feature, e) => ({
      feature: serializeFeature(feature),
      longitude: e.lngLat.lng,
      latitude: e.lngLat.lat,
    });

    const handleMouseMove = (e) => {
      const feature = e.features?.[0];
      if (!feature) return;
      map.getCanvas().style.cursor = "pointer";
      const featureId = feature.id;
      if (featureId === hoveredId) return;
      setHover(featureId ?? null);
      latestRef.current.onHover?.(payload(feature, e));
    };

    const handleMouseLeave = () => {
      setHover(null);
      map.getCanvas().style.cursor = "";
      latestRef.current.onHover?.(null);
    };

    const handleClick = (e) => {
      const feature = e.features?.[0];
      if (!feature) return;
      latestRef.current.onClick?.(payload(feature, e));
    };

    map.on("mousemove", fillLayerId, handleMouseMove);
    map.on("mouseleave", fillLayerId, handleMouseLeave);
    map.on("click", fillLayerId, handleClick);

    return () => {
      map.off("mousemove", fillLayerId, handleMouseMove);
      map.off("mouseleave", fillLayerId, handleMouseLeave);
      map.off("click", fillLayerId, handleClick);
      setHover(null);
      map.getCanvas().style.cursor = "";
    };
  }, [isLoaded, map, fillLayerId, sourceId, interactive, showFill]);

  return null;
}

// ---------------------------------------------------------------------------
// Arcs
// ---------------------------------------------------------------------------

const DEFAULT_ARC_CURVATURE = 0.2;
const DEFAULT_ARC_SAMPLES = 64;
const ARC_HIT_MIN_WIDTH = 12;
const ARC_HIT_PADDING = 6;

const DEFAULT_ARC_PAINT = {
  "line-color": "#4285F4",
  "line-width": 2,
  "line-opacity": 0.85,
};

const DEFAULT_ARC_LAYOUT = {
  "line-join": "round",
  "line-cap": "round",
};

function buildArcCoordinates(from, to, curvature, samples) {
  const [x0, y0] = from;
  const [xTo, y2] = to;
  const rawDx = xTo - x0;
  const x2 = rawDx > 180 ? xTo - 360 : rawDx < -180 ? xTo + 360 : xTo;
  const dx = x2 - x0;
  const dy = y2 - y0;
  const distance = Math.hypot(dx, dy);

  if (distance === 0 || curvature === 0) return [from, [x2, y2]];

  const mx = (x0 + x2) / 2;
  const my = (y0 + y2) / 2;
  const nx = -dy / distance;
  const ny = dx / distance;
  const offset = distance * curvature;
  const cx = mx + nx * offset;
  const cy = my + ny * offset;

  const points = [];
  const segments = Math.max(2, Math.floor(samples));
  for (let i = 0; i <= segments; i += 1) {
    const t = i / segments;
    const inv = 1 - t;
    const x = inv * inv * x0 + 2 * inv * t * cx + t * t * x2;
    const y = inv * inv * y0 + 2 * inv * t * cy + t * t * y2;
    points.push([x, y]);
  }
  return points;
}

function MapArc({
  data,
  id: propId,
  curvature = DEFAULT_ARC_CURVATURE,
  samples = DEFAULT_ARC_SAMPLES,
  paint,
  layout,
  hoverPaint,
  onClick,
  onHover,
  interactive = true,
  beforeId,
}) {
  const { map, isLoaded } = useMap();
  const autoId = useId();
  const id = propId ?? autoId;
  const sourceId = `arc-source-${id}`;
  const layerId = `arc-layer-${id}`;
  const hitLayerId = `arc-hit-layer-${id}`;

  const stableData = useStableValue(data ?? []);
  const stablePaint = useStableValue(paint);
  const stableLayout = useStableValue(layout);
  const stableHoverPaint = useStableValue(hoverPaint);

  const mergedPaint = useMemo(
    () => mergeHoverPaint({ ...DEFAULT_ARC_PAINT, ...stablePaint }, stableHoverPaint),
    [stablePaint, stableHoverPaint],
  );
  const mergedLayout = useMemo(
    () => ({ ...DEFAULT_ARC_LAYOUT, ...stableLayout }),
    [stableLayout],
  );

  const hitWidth = useMemo(() => {
    const w = stablePaint?.["line-width"] ?? DEFAULT_ARC_PAINT["line-width"];
    const base = typeof w === "number" ? w : ARC_HIT_MIN_WIDTH;
    return Math.max(base + ARC_HIT_PADDING, ARC_HIT_MIN_WIDTH);
  }, [stablePaint]);

  const geoJSON = useMemo(
    () => ({
      type: "FeatureCollection",
      features: stableData.map((arc) => {
        const { from, to, ...properties } = arc;
        return {
          type: "Feature",
          properties,
          geometry: {
            type: "LineString",
            coordinates: buildArcCoordinates(from, to, curvature, samples),
          },
        };
      }),
    }),
    [stableData, curvature, samples],
  );

  const latestRef = useRef({ data: stableData, onClick, onHover });
  latestRef.current = { data: stableData, onClick, onHover };

  useEffect(() => {
    if (!isLoaded || !map) return;

    map.addSource(sourceId, { type: "geojson", data: geoJSON, promoteId: "id" });

    map.addLayer(
      {
        id: hitLayerId,
        type: "line",
        source: sourceId,
        layout: DEFAULT_ARC_LAYOUT,
        paint: {
          "line-color": "rgba(0, 0, 0, 0)",
          "line-width": hitWidth,
          "line-opacity": 1,
        },
      },
      resolveBeforeId(map, beforeId),
    );

    map.addLayer(
      { id: layerId, type: "line", source: sourceId, layout: mergedLayout, paint: mergedPaint },
      resolveBeforeId(map, beforeId),
    );

    return () => {
      try {
        if (map.getLayer(layerId)) map.removeLayer(layerId);
        if (map.getLayer(hitLayerId)) map.removeLayer(hitLayerId);
        if (map.getSource(sourceId)) map.removeSource(sourceId);
      } catch {
        // ignore
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, map]);

  useEffect(() => {
    if (!isLoaded || !map) return;
    const source = map.getSource(sourceId);
    source?.setData(geoJSON);
  }, [isLoaded, map, geoJSON, sourceId]);

  useEffect(() => {
    if (!isLoaded || !map || !map.getLayer(layerId)) return;
    for (const [key, value] of Object.entries(mergedPaint)) {
      map.setPaintProperty(layerId, key, value);
    }
    for (const [key, value] of Object.entries(mergedLayout)) {
      map.setLayoutProperty(layerId, key, value);
    }
    if (map.getLayer(hitLayerId)) {
      map.setPaintProperty(hitLayerId, "line-width", hitWidth);
    }
  }, [isLoaded, map, layerId, hitLayerId, mergedPaint, mergedLayout, hitWidth]);

  useEffect(() => {
    if (!isLoaded || !map || !interactive) return;

    let hoveredId = null;

    const setHover = (next) => {
      if (next === hoveredId) return;
      const sourceExists = !!map.getSource(sourceId);
      if (hoveredId != null && sourceExists) {
        map.setFeatureState({ source: sourceId, id: hoveredId }, { hover: false });
      }
      hoveredId = next;
      if (next != null && sourceExists) {
        map.setFeatureState({ source: sourceId, id: next }, { hover: true });
      }
    };

    const findArc = (featureId) =>
      featureId == null
        ? undefined
        : latestRef.current.data.find(
            (arc) => String(arc.id) === String(featureId),
          );

    const handleMouseMove = (e) => {
      const featureId = e.features?.[0]?.id;
      if (featureId == null || featureId === hoveredId) return;
      setHover(featureId);
      map.getCanvas().style.cursor = "pointer";
      const arc = findArc(featureId);
      if (arc) {
        latestRef.current.onHover?.({
          arc,
          longitude: e.lngLat.lng,
          latitude: e.lngLat.lat,
        });
      }
    };

    const handleMouseLeave = () => {
      setHover(null);
      map.getCanvas().style.cursor = "";
      latestRef.current.onHover?.(null);
    };

    const handleClick = (e) => {
      const arc = findArc(e.features?.[0]?.id);
      if (!arc) return;
      latestRef.current.onClick?.({
        arc,
        longitude: e.lngLat.lng,
        latitude: e.lngLat.lat,
      });
    };

    map.on("mousemove", hitLayerId, handleMouseMove);
    map.on("mouseleave", hitLayerId, handleMouseLeave);
    map.on("click", hitLayerId, handleClick);

    return () => {
      map.off("mousemove", hitLayerId, handleMouseMove);
      map.off("mouseleave", hitLayerId, handleMouseLeave);
      map.off("click", hitLayerId, handleClick);
      setHover(null);
      map.getCanvas().style.cursor = "";
    };
  }, [isLoaded, map, hitLayerId, sourceId, interactive]);

  return null;
}

// ---------------------------------------------------------------------------
// Clusters
// ---------------------------------------------------------------------------

const DEFAULT_CLUSTER_COLORS = ["#3b82f6", "#1d4ed8", "#1e3a8a"];
const DEFAULT_CLUSTER_THRESHOLDS = [100, 750];

function MapClusterLayer({
  data,
  clusterMaxZoom = 14,
  clusterRadius = 50,
  clusterColors = DEFAULT_CLUSTER_COLORS,
  clusterThresholds = DEFAULT_CLUSTER_THRESHOLDS,
  pointColor = "#3b82f6",
  onPointClick,
  onClusterClick,
}) {
  const { map, isLoaded } = useMap();
  const id = useId();
  const sourceId = `cluster-source-${id}`;
  const clusterLayerId = `clusters-${id}`;
  const clusterCountLayerId = `cluster-count-${id}`;
  const unclusteredLayerId = `unclustered-point-${id}`;

  const stableData = useStableValue(data);
  const stableClusterColors = useStableValue(clusterColors);
  const stableClusterThresholds = useStableValue(clusterThresholds);

  const callbacksRef = useRef({});
  callbacksRef.current = { onPointClick, onClusterClick };

  const stylePropsRef = useRef({
    clusterColors: stableClusterColors,
    clusterThresholds: stableClusterThresholds,
    pointColor,
  });

  useEffect(() => {
    if (!isLoaded || !map) return;

    map.addSource(sourceId, {
      type: "geojson",
      data: stableData,
      cluster: true,
      clusterMaxZoom,
      clusterRadius,
    });

    map.addLayer({
      id: clusterLayerId,
      type: "circle",
      source: sourceId,
      filter: ["has", "point_count"],
      paint: {
        "circle-color": [
          "step",
          ["get", "point_count"],
          stableClusterColors[0],
          stableClusterThresholds[0],
          stableClusterColors[1],
          stableClusterThresholds[1],
          stableClusterColors[2],
        ],
        "circle-radius": [
          "step",
          ["get", "point_count"],
          20,
          stableClusterThresholds[0],
          30,
          stableClusterThresholds[1],
          40,
        ],
        "circle-stroke-width": 0.75,
        "circle-stroke-color": "#fff",
        "circle-opacity": 0.85,
      },
    });

    map.addLayer({
      id: clusterCountLayerId,
      type: "symbol",
      source: sourceId,
      filter: ["has", "point_count"],
      layout: {
        "text-field": "{point_count_abbreviated}",
        "text-font": ["Open Sans Semibold"],
        "text-size": 12,
      },
      paint: { "text-color": "#fff" },
    });

    map.addLayer({
      id: unclusteredLayerId,
      type: "circle",
      source: sourceId,
      filter: ["!", ["has", "point_count"]],
      paint: {
        "circle-color": pointColor,
        "circle-radius": 5,
        "circle-stroke-width": 2,
        "circle-stroke-color": "#fff",
      },
    });

    return () => {
      try {
        if (map.getLayer(clusterCountLayerId)) map.removeLayer(clusterCountLayerId);
        if (map.getLayer(unclusteredLayerId)) map.removeLayer(unclusteredLayerId);
        if (map.getLayer(clusterLayerId)) map.removeLayer(clusterLayerId);
        if (map.getSource(sourceId)) map.removeSource(sourceId);
      } catch {
        // ignore
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, map, sourceId]);

  // Update source data when data prop changes (only for non-URL data)
  useEffect(() => {
    if (!isLoaded || !map || typeof stableData === "string") return;
    const source = map.getSource(sourceId);
    if (source) source.setData(stableData);
  }, [isLoaded, map, stableData, sourceId]);

  // Update layer styles when props change
  useEffect(() => {
    if (!isLoaded || !map) return;

    const prev = stylePropsRef.current;
    const colorsChanged =
      prev.clusterColors !== stableClusterColors ||
      prev.clusterThresholds !== stableClusterThresholds;

    if (map.getLayer(clusterLayerId) && colorsChanged) {
      map.setPaintProperty(clusterLayerId, "circle-color", [
        "step",
        ["get", "point_count"],
        stableClusterColors[0],
        stableClusterThresholds[0],
        stableClusterColors[1],
        stableClusterThresholds[1],
        stableClusterColors[2],
      ]);
      map.setPaintProperty(clusterLayerId, "circle-radius", [
        "step",
        ["get", "point_count"],
        20,
        stableClusterThresholds[0],
        30,
        stableClusterThresholds[1],
        40,
      ]);
    }

    if (map.getLayer(unclusteredLayerId) && prev.pointColor !== pointColor) {
      map.setPaintProperty(unclusteredLayerId, "circle-color", pointColor);
    }

    stylePropsRef.current = {
      clusterColors: stableClusterColors,
      clusterThresholds: stableClusterThresholds,
      pointColor,
    };
  }, [
    isLoaded,
    map,
    clusterLayerId,
    unclusteredLayerId,
    stableClusterColors,
    stableClusterThresholds,
    pointColor,
  ]);

  // Handle click events
  useEffect(() => {
    if (!isLoaded || !map) return;

    const handleClusterClick = async (e) => {
      const features = map.queryRenderedFeatures(e.point, {
        layers: [clusterLayerId],
      });
      if (!features.length) return;

      const feature = features[0];
      const clusterId = feature.properties?.cluster_id;
      const pointCount = feature.properties?.point_count;
      const coordinates = feature.geometry.coordinates;

      if (callbacksRef.current.onClusterClick) {
        callbacksRef.current.onClusterClick(clusterId, coordinates, pointCount);
      } else {
        const source = map.getSource(sourceId);
        const zoom = await source.getClusterExpansionZoom(clusterId);
        map.easeTo({ center: coordinates, zoom });
      }
    };

    const handlePointClick = (e) => {
      if (!callbacksRef.current.onPointClick || !e.features?.length) return;
      const feature = e.features[0];
      const coordinates = feature.geometry.coordinates.slice();
      while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
        coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
      }
      callbacksRef.current.onPointClick(serializeFeature(feature), coordinates);
    };

    const handleMouseEnterCluster = () => {
      map.getCanvas().style.cursor = "pointer";
    };
    const handleMouseLeaveCluster = () => {
      map.getCanvas().style.cursor = "";
    };
    const handleMouseEnterPoint = () => {
      if (callbacksRef.current.onPointClick) map.getCanvas().style.cursor = "pointer";
    };
    const handleMouseLeavePoint = () => {
      map.getCanvas().style.cursor = "";
    };

    map.on("click", clusterLayerId, handleClusterClick);
    map.on("click", unclusteredLayerId, handlePointClick);
    map.on("mouseenter", clusterLayerId, handleMouseEnterCluster);
    map.on("mouseleave", clusterLayerId, handleMouseLeaveCluster);
    map.on("mouseenter", unclusteredLayerId, handleMouseEnterPoint);
    map.on("mouseleave", unclusteredLayerId, handleMouseLeavePoint);

    return () => {
      map.off("click", clusterLayerId, handleClusterClick);
      map.off("click", unclusteredLayerId, handlePointClick);
      map.off("mouseenter", clusterLayerId, handleMouseEnterCluster);
      map.off("mouseleave", clusterLayerId, handleMouseLeaveCluster);
      map.off("mouseenter", unclusteredLayerId, handleMouseEnterPoint);
      map.off("mouseleave", unclusteredLayerId, handleMouseLeavePoint);
    };
  }, [isLoaded, map, clusterLayerId, unclusteredLayerId, sourceId]);

  return null;
}

// ---------------------------------------------------------------------------
// Layer runtime (Reflex extra)
// ---------------------------------------------------------------------------

/**
 * Shared lifecycle for every 0.2.0 layer component.
 *
 * One place decides when a source and its layers are added, which prop changes
 * can be applied in place and which ones need a rebuild, how interaction is
 * wired, and in what order everything is torn down. The 0.1.0 components keep
 * their hand-written effects; they move over in a later release.
 *
 * ```js
 * useMapLayer({
 *   id: "quakes",                                  // only used in warnings
 *   sourceId: "circle-source-quakes",              // created, or reused when `source` is null
 *   source: { type: "geojson", data },             // null to attach to an existing source
 *   layers: [{ id: "circle-layer-quakes", type: "circle", paint, layout, filter }],
 *   beforeId, interactive, hoverPaint, images,
 *   hotKeys: ["data", "paint", "layout", "filter", "zoomRange", "beforeId", "images"],
 *   callbacks: { onClick, onHover },
 * });
 * ```
 */

const HOT_GROUPS = ["data", "paint", "layout", "filter", "zoomRange", "beforeId", "images"];

/**
 * The part of a source that cannot change without recreating it.
 *
 * `data` is pushed with `setData`, and the zoom range is applied to the layer
 * with `setLayerZoomRange`, so neither belongs in the rebuild key.
 */
function sourceIdentity(source) {
  if (!source) return null;
  const { data, minzoom, maxzoom, ...rest } = source;
  return rest;
}

/** The part of a layer that cannot change without recreating it. */
function layerIdentity(layers) {
  return layers.map((layer) => ({
    id: layer.id,
    type: layer.type,
    sourceLayer: layer["source-layer"] ?? null,
  }));
}

function isSame(a, b) {
  return JSON.stringify(a ?? null) === JSON.stringify(b ?? null);
}

function useMapLayer({
  id,
  sourceId,
  source,
  layers = [],
  beforeId,
  interactive = false,
  hoverPaint,
  images,
  hotKeys,
  callbacks,
}) {
  const { map, isLoaded } = useMap();

  const stableSource = useStableValue(source);
  const stableLayers = useStableValue(layers);
  const stableImages = useStableValue(images);
  const stableHoverPaint = useStableValue(hoverPaint);
  const stableHotKeys = useStableValue(hotKeys ?? HOT_GROUPS);

  const callbacksRef = useRef(callbacks);
  callbacksRef.current = callbacks ?? {};

  // Warn at most once per message for the life of the component: a missing
  // `before_id` must not fill the console on every state update.
  const warnedRef = useRef(null);
  if (warnedRef.current === null) warnedRef.current = new Set();
  const warnOnce = useCallback((message) => {
    if (warnedRef.current.has(message)) return;
    warnedRef.current.add(message);
    console.warn(message);
  }, []);

  const hot = useMemo(() => new Set(stableHotKeys), [stableHotKeys]);

  const resolvedLayers = useMemo(() => {
    if (!stableHoverPaint) return stableLayers;
    return stableLayers.map((layer, index) =>
      index === 0
        ? { ...layer, paint: mergeHoverPaint(layer.paint ?? {}, stableHoverPaint) }
        : layer,
    );
  }, [stableLayers, stableHoverPaint]);

  // Everything the map cannot be told about after the fact.
  const coldKey = useMemo(
    () =>
      JSON.stringify({
        sourceId,
        source: sourceIdentity(stableSource),
        layers: layerIdentity(resolvedLayers),
      }),
    [sourceId, stableSource, resolvedLayers],
  );

  // Everything it can.
  const snapshot = useCallback(
    () => ({
      data: stableSource?.data,
      beforeId: beforeId ?? null,
      layers: resolvedLayers.map((layer) => ({
        paint: layer.paint ?? {},
        layout: layer.layout ?? {},
        filter: layer.filter ?? null,
        minzoom: layer.minzoom ?? null,
        maxzoom: layer.maxzoom ?? null,
      })),
    }),
    [stableSource, resolvedLayers, beforeId],
  );

  const appliedRef = useRef(null);
  const addedLayersRef = useRef([]);
  const addedImagesRef = useRef([]);
  const [retryToken, setRetryToken] = useState(0);

  const loadImageInto = useCallback(
    async (name, url) => {
      try {
        const image = await map.loadImage(url);
        if (!map.hasImage(name)) map.addImage(name, image?.data ?? image);
        if (!addedImagesRef.current.includes(name)) addedImagesRef.current.push(name);
        return true;
      } catch {
        warnOnce(`mapcn: image "${name}" failed to load`);
        return false;
      }
    },
    [map, warnOnce],
  );

  // Add / rebuild.
  useEffect(() => {
    if (!map || !isLoaded) return undefined;

    let cancelled = false;
    let retryHandler = null;
    const ownsSource = !!stableSource;

    const addLayers = () => {
      const target = resolveBeforeId(map, beforeId);
      if (beforeId && !target) {
        warnOnce(`mapcn: before_id "${beforeId}" not found; layer appended`);
      }
      for (const layer of resolvedLayers) {
        if (map.getLayer(layer.id)) map.removeLayer(layer.id);
        map.addLayer({ ...layer, ...(sourceId ? { source: sourceId } : {}) }, target);
        addedLayersRef.current.push(layer.id);
      }
      appliedRef.current = snapshot();
    };

    const add = async () => {
      if (ownsSource) {
        // A leftover source means an aborted teardown or a double mount.
        if (map.getSource(sourceId)) {
          for (const layer of resolvedLayers) {
            if (map.getLayer(layer.id)) map.removeLayer(layer.id);
          }
          map.removeSource(sourceId);
        }
        map.addSource(sourceId, stableSource);
      } else if (sourceId && !map.getSource(sourceId)) {
        // The style does not provide it (yet): skip the layer and try again
        // when the next style finishes loading.
        warnOnce(`mapcn: source "${sourceId}" not found`);
        retryHandler = () => setRetryToken((token) => token + 1);
        map.on("style.load", retryHandler);
        return;
      }

      if (stableImages) {
        await Promise.all(
          Object.entries(stableImages).map(([name, url]) => loadImageInto(name, url)),
        );
        if (cancelled) return;
      }

      addLayers();
    };

    add();

    return () => {
      cancelled = true;
      try {
        if (retryHandler) map.off("style.load", retryHandler);
        for (const layerId of [...addedLayersRef.current].reverse()) {
          if (map.getLayer(layerId)) map.removeLayer(layerId);
        }
        if (ownsSource && map.getSource(sourceId)) map.removeSource(sourceId);
        for (const name of addedImagesRef.current) {
          if (map.hasImage(name)) map.removeImage(name);
        }
      } catch {
        // The style may be mid-reload; MapLibre has already dropped these.
      }
      addedLayersRef.current = [];
      addedImagesRef.current = [];
      appliedRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, isLoaded, coldKey, retryToken]);

  // Apply in place.
  useEffect(() => {
    if (!map || !isLoaded) return;
    const applied = appliedRef.current;
    if (!applied) return;

    const next = snapshot();

    if (hot.has("data") && !isSame(next.data, applied.data)) {
      map.getSource(sourceId)?.setData?.(next.data);
    }

    resolvedLayers.forEach((layer, index) => {
      if (!map.getLayer(layer.id)) return;
      const before = applied.layers[index] ?? {};
      const after = next.layers[index];

      if (hot.has("paint")) {
        for (const [key, value] of Object.entries(after.paint)) {
          if (!isSame(value, before.paint?.[key])) map.setPaintProperty(layer.id, key, value);
        }
      }
      if (hot.has("layout")) {
        for (const [key, value] of Object.entries(after.layout)) {
          if (!isSame(value, before.layout?.[key])) map.setLayoutProperty(layer.id, key, value);
        }
      }
      if (hot.has("filter") && !isSame(after.filter, before.filter)) {
        map.setFilter(layer.id, after.filter ?? undefined);
      }
      if (
        hot.has("zoomRange") &&
        (after.minzoom !== before.minzoom || after.maxzoom !== before.maxzoom)
      ) {
        map.setLayerZoomRange(layer.id, after.minzoom ?? undefined, after.maxzoom ?? undefined);
      }
    });

    if (hot.has("beforeId") && next.beforeId !== applied.beforeId) {
      const target = resolveBeforeId(map, next.beforeId);
      for (const layer of resolvedLayers) {
        if (map.getLayer(layer.id)) map.moveLayer(layer.id, target);
      }
    }

    if (hot.has("images")) {
      const wanted = stableImages ?? {};
      for (const name of [...addedImagesRef.current]) {
        if (name in wanted) continue;
        if (map.hasImage(name)) map.removeImage(name);
        addedImagesRef.current = addedImagesRef.current.filter((entry) => entry !== name);
      }
      for (const [name, url] of Object.entries(wanted)) {
        if (!addedImagesRef.current.includes(name)) loadImageInto(name, url);
      }
    }

    appliedRef.current = next;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, isLoaded, snapshot, stableImages, hot, sourceId]);

  // Interaction, bound to the first layer (the one hover paint applies to).
  const hitLayerId = resolvedLayers[0]?.id;
  useEffect(() => {
    if (!map || !isLoaded || !interactive || !hitLayerId) return undefined;

    let hoveredId = null;

    const setHover = (next) => {
      if (next === hoveredId) return;
      const sourceExists = !!map.getSource(sourceId);
      if (hoveredId != null && sourceExists) {
        map.setFeatureState({ source: sourceId, id: hoveredId }, { hover: false });
      }
      hoveredId = next;
      if (next != null && sourceExists) {
        map.setFeatureState({ source: sourceId, id: next }, { hover: true });
      }
    };

    const payload = (feature, event) => ({
      feature: serializeFeature(feature),
      longitude: event.lngLat.lng,
      latitude: event.lngLat.lat,
    });

    const handleMouseMove = (event) => {
      const feature = event.features?.[0];
      if (!feature) return;
      map.getCanvas().style.cursor = "pointer";
      if (feature.id === hoveredId) return;
      setHover(feature.id ?? null);
      callbacksRef.current.onHover?.(payload(feature, event));
    };

    const handleMouseLeave = () => {
      setHover(null);
      map.getCanvas().style.cursor = "";
      callbacksRef.current.onHover?.(null);
    };

    const handleClick = (event) => {
      const feature = event.features?.[0];
      if (!feature) return;
      callbacksRef.current.onClick?.(payload(feature, event));
    };

    map.on("mousemove", hitLayerId, handleMouseMove);
    map.on("mouseleave", hitLayerId, handleMouseLeave);
    map.on("click", hitLayerId, handleClick);

    return () => {
      map.off("mousemove", hitLayerId, handleMouseMove);
      map.off("mouseleave", hitLayerId, handleMouseLeave);
      map.off("click", hitLayerId, handleClick);
      setHover(null);
      try {
        map.getCanvas().style.cursor = "";
      } catch {
        // The map may already be gone.
      }
    };
  }, [map, isLoaded, interactive, hitLayerId, sourceId]);

  return { sourceId, layerIds: resolvedLayers.map((layer) => layer.id) };
}

// ---------------------------------------------------------------------------
// Raster layer (Reflex extra)
// ---------------------------------------------------------------------------

/** Component prop -> MapLibre paint property. */
const RASTER_PAINT_PROPS = {
  opacity: "raster-opacity",
  resampling: "raster-resampling",
  saturation: "raster-saturation",
  contrast: "raster-contrast",
  brightnessMin: "raster-brightness-min",
  brightnessMax: "raster-brightness-max",
  hueRotate: "raster-hue-rotate",
  fadeDuration: "raster-fade-duration",
};

// A raster source has no `data` to push and no filter to set.
const RASTER_HOT_KEYS = ["paint", "layout", "zoomRange", "beforeId"];

// MapLibre reports every failed tile; one report a minute is enough to tell an
// application that a service is down.
const TILE_ERROR_THROTTLE_MS = 60000;

/**
 * Third-party raster tiles on top of the basemap: radar, railways, nautical
 * charts, satellite imagery, traffic. Point it at a set of `{z}/{x}/{y}`
 * templates or at a TileJSON url; the Python side resolves presets.
 */
function RasterLayer({
  id: propId,
  tiles,
  url,
  tileSize = 256,
  scheme = "xyz",
  bounds,
  attribution,
  minZoom,
  maxZoom,
  opacity,
  resampling,
  saturation,
  contrast,
  brightnessMin,
  brightnessMax,
  hueRotate,
  fadeDuration,
  visible = true,
  beforeId,
  onLoadError,
}) {
  const { map, isLoaded } = useMap();
  const autoId = useId();
  const id = propId ?? autoId;
  const sourceId = `raster-source-${id}`;
  const layerId = `raster-layer-${id}`;

  const stableTiles = useStableValue(tiles);
  const stableBounds = useStableValue(bounds);

  const source = useMemo(
    () => ({
      type: "raster",
      ...(stableTiles ? { tiles: stableTiles } : {}),
      ...(url ? { url } : {}),
      tileSize,
      scheme,
      ...(stableBounds ? { bounds: stableBounds } : {}),
      ...(attribution ? { attribution } : {}),
      ...(minZoom !== undefined ? { minzoom: minZoom } : {}),
      ...(maxZoom !== undefined ? { maxzoom: maxZoom } : {}),
    }),
    [stableTiles, url, tileSize, scheme, stableBounds, attribution, minZoom, maxZoom],
  );

  const paint = useMemo(() => {
    const values = {
      opacity,
      resampling,
      saturation,
      contrast,
      brightnessMin,
      brightnessMax,
      hueRotate,
      fadeDuration,
    };
    const result = {};
    for (const [prop, name] of Object.entries(RASTER_PAINT_PROPS)) {
      if (values[prop] !== undefined) result[name] = values[prop];
    }
    return result;
  }, [
    opacity,
    resampling,
    saturation,
    contrast,
    brightnessMin,
    brightnessMax,
    hueRotate,
    fadeDuration,
  ]);

  const layers = useMemo(
    () => [
      {
        id: layerId,
        type: "raster",
        paint,
        layout: { visibility: visible ? "visible" : "none" },
        ...(minZoom !== undefined ? { minzoom: minZoom } : {}),
        ...(maxZoom !== undefined ? { maxzoom: maxZoom } : {}),
      },
    ],
    [layerId, paint, visible, minZoom, maxZoom],
  );

  useMapLayer({ id, sourceId, source, layers, beforeId, hotKeys: RASTER_HOT_KEYS });

  const onLoadErrorRef = useRef(onLoadError);
  onLoadErrorRef.current = onLoadError;
  const reportsErrors = !!onLoadError;

  useEffect(() => {
    if (!map || !isLoaded || !reportsErrors) return undefined;

    let lastReport = 0;
    const handleError = (event) => {
      if (event?.sourceId !== sourceId) return;
      const now = Date.now();
      if (lastReport && now - lastReport < TILE_ERROR_THROTTLE_MS) return;
      lastReport = now;
      onLoadErrorRef.current?.({
        source_id: sourceId,
        message: event?.error?.message ?? "tile request failed",
      });
    };

    map.on("error", handleError);
    return () => {
      map.off("error", handleError);
    };
  }, [map, isLoaded, sourceId, reportsErrors]);

  return null;
}

// ---------------------------------------------------------------------------
// Generic layer (Reflex extra)
// ---------------------------------------------------------------------------

/**
 * Any MapLibre source and layer, straight from Python.
 *
 * This is the escape hatch: whatever this package does not wrap yet, from
 * extruded buildings over the basemap's own vector tiles to a video overlay,
 * is one `map_layer` away. `source` is either a source specification or the id
 * of a source the style already provides; the layer receives its id and its
 * source automatically.
 */
function Layer({
  id: propId,
  source,
  layer,
  beforeId,
  interactive = false,
  hoverPaint,
  visible = true,
  onClick,
  onHover,
}) {
  const autoId = useId();
  const id = propId ?? autoId;

  const stableSource = useStableValue(source);
  const stableLayer = useStableValue(layer);

  const usesStyleSource = typeof stableSource === "string";
  const sourceId = usesStyleSource ? stableSource : `layer-source-${id}`;

  const layers = useMemo(() => {
    const { id: ignoredId, source: ignoredSource, layout, ...rest } = stableLayer ?? {};
    return [
      {
        ...rest,
        id: `layer-${id}`,
        layout: {
          ...(layout ?? {}),
          visibility: visible ? (layout?.visibility ?? "visible") : "none",
        },
      },
    ];
  }, [stableLayer, id, visible]);

  useMapLayer({
    id,
    sourceId,
    source: usesStyleSource ? null : stableSource,
    layers,
    beforeId,
    interactive,
    hoverPaint,
    callbacks: { onClick, onHover },
  });

  return null;
}

// ---------------------------------------------------------------------------
// Heatmap layer (Reflex extra)
// ---------------------------------------------------------------------------

// Defaults chosen so a heatmap is readable with nothing but `data`: both the
// spread and the strength of a point grow as the map is zoomed in.
const HEATMAP_DEFAULT_INTENSITY = ["interpolate", ["linear"], ["zoom"], 0, 1, 9, 3];
const HEATMAP_DEFAULT_RADIUS = ["interpolate", ["linear"], ["zoom"], 0, 2, 9, 20];
const HEATMAP_DEFAULT_COLOR = [
  "interpolate",
  ["linear"],
  ["heatmap-density"],
  0,
  "rgba(59,130,246,0)",
  0.2,
  "rgb(59,130,246)",
  0.4,
  "rgb(34,197,94)",
  0.6,
  "rgb(250,204,21)",
  0.8,
  "rgb(249,115,22)",
  1,
  "rgb(239,68,68)",
];

// A heatmap is not interactive in MapLibre: it renders density, not features.
const HEATMAP_HOT_KEYS = ["data", "paint", "layout", "zoomRange", "beforeId"];

/** Point density as a heatmap. Feed it a point FeatureCollection or a url. */
function HeatmapLayer({
  id: propId,
  data,
  weight = 1,
  intensity = HEATMAP_DEFAULT_INTENSITY,
  radius = HEATMAP_DEFAULT_RADIUS,
  color = HEATMAP_DEFAULT_COLOR,
  opacity = 0.8,
  visible = true,
  beforeId,
  minZoom,
  maxZoom,
}) {
  const autoId = useId();
  const id = propId ?? autoId;

  const stableData = useStableValue(data);
  const stableWeight = useStableValue(weight);
  const stableIntensity = useStableValue(intensity);
  const stableRadius = useStableValue(radius);
  const stableColor = useStableValue(color);
  const stableOpacity = useStableValue(opacity);

  const source = useMemo(
    () => ({ type: "geojson", data: stableData }),
    [stableData],
  );

  const layers = useMemo(
    () => [
      {
        id: `heatmap-layer-${id}`,
        type: "heatmap",
        paint: {
          "heatmap-weight": stableWeight,
          "heatmap-intensity": stableIntensity,
          "heatmap-radius": stableRadius,
          "heatmap-color": stableColor,
          "heatmap-opacity": stableOpacity,
        },
        layout: { visibility: visible ? "visible" : "none" },
        ...(minZoom !== undefined ? { minzoom: minZoom } : {}),
        ...(maxZoom !== undefined ? { maxzoom: maxZoom } : {}),
      },
    ],
    [
      id,
      stableWeight,
      stableIntensity,
      stableRadius,
      stableColor,
      stableOpacity,
      visible,
      minZoom,
      maxZoom,
    ],
  );

  useMapLayer({
    id,
    sourceId: `heatmap-source-${id}`,
    source,
    layers,
    beforeId,
    hotKeys: HEATMAP_HOT_KEYS,
  });

  return null;
}

// ---------------------------------------------------------------------------
// Reflex helpers
// ---------------------------------------------------------------------------

/**
 * Imperative camera helper for Reflex. Rendered inside `<Map>`; whenever the
 * `command` prop changes it runs `map.flyTo / easeTo / jumpTo / fitBounds`.
 * Reflex apps drive it from state, e.g. `MapcnState.fly_to([...], zoom=12)`.
 */
function MapCamera({ command }) {
  const { map, isLoaded } = useMap();
  const stableCommand = useStableValue(command);
  const lastSeq = useRef(null);

  useEffect(() => {
    if (!map || !isLoaded || !stableCommand) return;
    const { type = "flyTo", seq, ...options } = stableCommand;
    if (seq !== undefined && seq === lastSeq.current) return;
    lastSeq.current = seq;
    try {
      if (type === "fitBounds") {
        const { bounds, ...rest } = options;
        map.fitBounds(bounds, rest);
      } else if (typeof map[type] === "function") {
        map[type](options);
      }
    } catch (error) {
      console.error("mapcn: camera command failed", error);
    }
  }, [map, isLoaded, stableCommand]);

  return null;
}

export {
  Map,
  useMap,
  useMapLayer,
  RasterLayer,
  Layer,
  HeatmapLayer,
  MapMarker,
  MarkerContent,
  MarkerPopup,
  MarkerTooltip,
  MarkerLabel,
  MapPopup,
  MapControls,
  MapRoute,
  RouteProgress,
  RouteMarker,
  MapArc,
  MapGeoJSON,
  MapClusterLayer,
  MapCamera,
  setWorkerUrl,
};
