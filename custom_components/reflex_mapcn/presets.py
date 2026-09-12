"""Tile presets for ``map_raster_layer`` and ``map_terrain`` (Reflex extra).

Every entry carries the tile templates, the zoom limits and, above all, the
attribution the data source requires. They live in Python rather than in the
JavaScript module so an application can read them, copy them and override any
single value with an explicit prop.

Usage::

    import reflex_mapcn as mapcn

    mapcn.map_raster_layer(preset="openseamap", opacity=0.9)
    mapcn.map_terrain(preset="aws_terrarium", hillshade=True)

None of these services needs an API key. Check each licence before using a
preset in a commercial product: RainViewer, in particular, is free for
non-commercial use only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

__all__ = [
    "RASTER_PRESETS",
    "TERRAIN_PRESETS",
    "RasterPreset",
    "TerrainPreset",
]


@dataclass(frozen=True)
class RasterPreset:
    """A third-party raster tile service."""

    name: str
    tiles: tuple[str, ...]
    tile_size: int
    max_zoom: int
    attribution: str
    license: str
    min_zoom: int = 0

    def as_props(self) -> dict[str, Any]:
        """Return the props a ``map_raster_layer`` would receive.

        Explicit props always win over these, so the preset is a default and
        never a constraint.
        """
        return {
            "tiles": list(self.tiles),
            "tile_size": self.tile_size,
            "min_zoom": self.min_zoom,
            "max_zoom": self.max_zoom,
            "attribution": self.attribution,
        }


@dataclass(frozen=True)
class TerrainPreset:
    """A digital elevation model served as raster-dem tiles."""

    name: str
    tiles: tuple[str, ...]
    encoding: Literal["terrarium", "mapbox"]
    tile_size: int
    max_zoom: int
    attribution: str
    license: str

    def as_props(self) -> dict[str, Any]:
        """Return the props a ``map_terrain`` would receive."""
        return {
            "tiles": list(self.tiles),
            "encoding": self.encoding,
            "tile_size": self.tile_size,
            "max_zoom": self.max_zoom,
            "attribution": self.attribution,
        }


#: Raster tile services usable without an API key.
RASTER_PRESETS: dict[str, RasterPreset] = {
    "openrailwaymap": RasterPreset(
        name="openrailwaymap",
        tiles=(
            "https://a.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png",
            "https://b.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png",
            "https://c.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png",
        ),
        tile_size=256,
        max_zoom=19,
        attribution=("© OpenRailwayMap contributors, CC BY-SA 2.0 · © OpenStreetMap"),
        license="CC BY-SA 2.0",
    ),
    "openseamap": RasterPreset(
        name="openseamap",
        tiles=("https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png",),
        tile_size=256,
        max_zoom=18,
        attribution="© OpenSeaMap contributors",
        license="CC BY-SA 2.0",
    ),
    "esri_satellite": RasterPreset(
        name="esri_satellite",
        tiles=(
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery"
            "/MapServer/tile/{z}/{y}/{x}",
        ),
        tile_size=256,
        max_zoom=19,
        attribution=(
            "Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, "
            "and the GIS User Community"
        ),
        license="Esri Terms of Use",
    ),
    # RainViewer frame paths expire after roughly two hours, so this preset
    # carries no tiles: build them with ``rainviewer_tiles()`` and pass the
    # result as ``tiles``.
    "rainviewer": RasterPreset(
        name="rainviewer",
        tiles=(),
        tile_size=256,
        max_zoom=7,
        attribution="© RainViewer",
        license="RainViewer Terms of Use (free for non-commercial use)",
    ),
}

#: Elevation tile services usable without an API key.
TERRAIN_PRESETS: dict[str, TerrainPreset] = {
    "aws_terrarium": TerrainPreset(
        name="aws_terrarium",
        tiles=(
            "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png",
        ),
        encoding="terrarium",
        tile_size=256,
        max_zoom=15,
        attribution="Terrain: Mapzen/AWS Terrain Tiles",
        license="Open (see the Mapzen attribution notice)",
    ),
}
