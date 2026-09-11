"""Tests for the raster and terrain presets (T-005).

The presets are the package's answer to "add a radar layer with one line", so
what matters is that every entry carries the tiles, the zoom limits and the
attribution the data source requires, and that it stays JSON-serialisable.
"""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest
from reflex_mapcn.presets import (
    RASTER_PRESETS,
    TERRAIN_PRESETS,
    RasterPreset,
    TerrainPreset,
)


def test_REQ_RAS_005_raster_presets_cover_the_documented_names():
    assert set(RASTER_PRESETS) == {
        "openrailwaymap",
        "openseamap",
        "esri_satellite",
        "rainviewer",
    }


def test_REQ_RAS_005_openseamap_preset_matches_the_api_spec():
    preset = RASTER_PRESETS["openseamap"]
    assert preset.tiles == ("https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png",)
    assert preset.tile_size == 256
    assert preset.max_zoom == 18
    assert preset.attribution == "© OpenSeaMap contributors"


def test_REQ_RAS_005_openrailwaymap_preset_uses_the_three_subdomains():
    tiles = RASTER_PRESETS["openrailwaymap"].tiles
    assert tiles == (
        "https://a.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png",
        "https://b.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png",
        "https://c.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png",
    )
    assert RASTER_PRESETS["openrailwaymap"].max_zoom == 19


def test_REQ_RAS_005_esri_satellite_preset_uses_the_zyx_scheme():
    preset = RASTER_PRESETS["esri_satellite"]
    assert preset.tiles == (
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery"
        "/MapServer/tile/{z}/{y}/{x}",
    )
    assert "Esri" in preset.attribution


def test_REQ_RAS_006_rainviewer_preset_brings_no_tiles_of_its_own():
    # Frame paths expire, so the tiles come from rainviewer_tiles() at runtime.
    preset = RASTER_PRESETS["rainviewer"]
    assert preset.tiles == ()
    assert preset.tile_size == 256
    assert preset.max_zoom == 7
    assert "RainViewer" in preset.attribution


def test_REQ_RAS_005_every_raster_preset_documents_attribution_and_licence():
    for name, preset in RASTER_PRESETS.items():
        assert preset.name == name
        assert preset.attribution, f"{name} has no attribution"
        assert preset.license, f"{name} has no licence"


def test_REQ_TER_002_aws_terrarium_preset_matches_the_api_spec():
    preset = TERRAIN_PRESETS["aws_terrarium"]
    assert preset.tiles == (
        "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png",
    )
    assert preset.encoding == "terrarium"
    assert preset.tile_size == 256
    assert preset.max_zoom == 15
    assert "Terrain" in preset.attribution


def test_REQ_RAS_005_as_props_returns_component_props_without_metadata():
    props = RASTER_PRESETS["openseamap"].as_props()
    assert props == {
        "tiles": ["https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png"],
        "tile_size": 256,
        "min_zoom": 0,
        "max_zoom": 18,
        "attribution": "© OpenSeaMap contributors",
    }
    assert json.dumps(props)


def test_REQ_TER_002_terrain_as_props_carries_the_encoding():
    props = TERRAIN_PRESETS["aws_terrarium"].as_props()
    assert props["encoding"] == "terrarium"
    assert props["tiles"] == [
        "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
    ]
    assert json.dumps(props)


def test_REQ_RAS_005_presets_are_immutable():
    preset = RASTER_PRESETS["openseamap"]
    with pytest.raises(FrozenInstanceError):
        preset.tile_size = 512  # type: ignore[misc]


def test_REQ_RAS_005_preset_types_are_the_documented_dataclasses():
    assert all(isinstance(p, RasterPreset) for p in RASTER_PRESETS.values())
    assert all(isinstance(p, TerrainPreset) for p in TERRAIN_PRESETS.values())
