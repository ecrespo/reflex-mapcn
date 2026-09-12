"""Tests for the raster and symbol page of the demo (T-023).

The page is a switchboard over tile services: three that need no key, the
RainViewer radar, and three that only work when an API key is in the
environment. Everything it decides is a plain function, tested here without
network and without a Reflex app.
"""

from __future__ import annotations

import reflex as rx
from mapcn_demo.pages import raster
from mapcn_demo.services import env as env_service

# ---------------------------------------------------------------------------
# Reading the keys (.env)
# ---------------------------------------------------------------------------


def test_the_env_file_is_read_as_key_value_pairs(tmp_path):
    path = tmp_path / ".env"
    path.write_text("# a comment\n\nTOMTOM_API_KEY=abc123\nOPENWEATHER_API_KEY=def\n")

    assert env_service.read_env_file(path) == {
        "TOMTOM_API_KEY": "abc123",
        "OPENWEATHER_API_KEY": "def",
    }


def test_quotes_and_spacing_around_a_value_are_dropped(tmp_path):
    path = tmp_path / ".env"
    path.write_text("TOMTOM_API_KEY = \"abc123\"  \nOPENWEATHER_API_KEY='def'\n")

    values = env_service.read_env_file(path)

    assert values["TOMTOM_API_KEY"] == "abc123"
    assert values["OPENWEATHER_API_KEY"] == "def"


def test_a_line_without_an_equals_sign_is_ignored(tmp_path):
    path = tmp_path / ".env"
    path.write_text("TOMTOM_API_KEY=abc\nthis is not a setting\n")

    assert env_service.read_env_file(path) == {"TOMTOM_API_KEY": "abc"}


def test_a_missing_env_file_is_not_an_error(tmp_path):
    assert env_service.read_env_file(tmp_path / "nothing-here") == {}


def test_a_variable_already_in_the_environment_wins_over_the_file(tmp_path):
    path = tmp_path / ".env"
    path.write_text("TOMTOM_API_KEY=from-the-file\n")
    environ = {"TOMTOM_API_KEY": "from-the-shell"}

    env_service.load_env_file(path, environ)

    assert environ["TOMTOM_API_KEY"] == "from-the-shell"


def test_a_variable_only_in_the_file_reaches_the_environment(tmp_path):
    path = tmp_path / ".env"
    path.write_text("OPENWEATHER_API_KEY=from-the-file\n")
    environ: dict[str, str] = {}

    env_service.load_env_file(path, environ)

    assert environ["OPENWEATHER_API_KEY"] == "from-the-file"


# ---------------------------------------------------------------------------
# The sources (REQ-RAS-005, REQ-RAS-004)
# ---------------------------------------------------------------------------


def test_REQ_RAS_005_the_keyless_sources_are_always_ready():
    keyless = [source for source in raster.SOURCES if source.env_var is None]

    assert {source.key for source in keyless} >= {
        "openrailwaymap",
        "openseamap",
        "esri_satellite",
        "rainviewer",
    }
    for source in keyless:
        assert raster.is_ready(source, {})


def test_REQ_RAS_004_every_source_carries_an_attribution():
    # Each service asks to be credited, and a preset only fills in what the
    # page leaves out.
    for source in raster.SOURCES:
        assert source.preset or source.attribution, source.key


def test_a_source_that_needs_a_key_is_not_ready_without_it():
    tomtom = raster.source_by_key("tomtom_traffic")

    assert tomtom.env_var == "TOMTOM_API_KEY"
    assert not raster.is_ready(tomtom, {})
    assert raster.is_ready(tomtom, {"TOMTOM_API_KEY": "abc"})


def test_both_weather_layers_read_the_same_key():
    weather = [s for s in raster.SOURCES if s.env_var == "OPENWEATHER_API_KEY"]

    assert len(weather) >= 2
    assert {s.key for s in weather} >= {"openweather_clouds", "openweather_rain"}


def test_the_traffic_tiles_carry_the_key_and_the_xyz_placeholders():
    tiles = raster.tiles_for(raster.source_by_key("tomtom_traffic"), "abc123")

    assert len(tiles) == 1
    assert "key=abc123" in tiles[0]
    assert "{z}/{x}/{y}" in tiles[0]
    assert tiles[0].startswith("https://api.tomtom.com/")


def test_the_weather_tiles_name_their_layer_and_carry_the_key():
    clouds = raster.tiles_for(raster.source_by_key("openweather_clouds"), "abc")
    rain = raster.tiles_for(raster.source_by_key("openweather_rain"), "abc")

    assert "clouds_new" in clouds[0]
    assert "precipitation_new" in rain[0]
    for tiles in (clouds, rain):
        assert "appid=abc" in tiles[0]
        assert "{z}/{x}/{y}" in tiles[0]


def test_a_preset_source_brings_no_tiles_of_its_own():
    # The preset carries them, so the page must not pass an empty list that
    # would override it.
    assert raster.tiles_for(raster.source_by_key("openseamap"), "") == []


def test_a_source_without_its_key_yields_no_tiles():
    assert raster.tiles_for(raster.source_by_key("tomtom_traffic"), "") == []


def test_the_selector_maps_labels_back_to_keys():
    for source in raster.SOURCES:
        assert raster.key_from_label(source.label) == source.key

    assert raster.key_from_label("no such label") == raster.SOURCES[0].key


# ---------------------------------------------------------------------------
# The radar (REQ-RAS-006, REQ-RAS-007)
# ---------------------------------------------------------------------------


FRAMES = {
    "host": "https://tilecache.rainviewer.com",
    "generated": 1689999000,
    "past": [
        {"time": 1689998400, "path": "/v2/radar/1689998400"},
        {"time": 1689999000, "path": "/v2/radar/1689999000"},
    ],
    "nowcast": [],
}


def test_REQ_RAS_006_the_radar_uses_the_newest_frame():
    tiles, label = raster.radar_tiles(FRAMES)

    assert len(tiles) == 1
    assert "/v2/radar/1689999000/" in tiles[0]
    assert tiles[0].startswith("https://tilecache.rainviewer.com")
    assert "{z}/{x}/{y}" in tiles[0]
    assert label


def test_REQ_RAS_007_no_frames_means_no_tiles_and_a_note():
    tiles, label = raster.radar_tiles({"host": "", "past": [], "nowcast": []})

    assert tiles == []
    assert "radar" in label.lower()


# ---------------------------------------------------------------------------
# The symbol layer (REQ-PNT-002, REQ-PNT-003, REQ-PNT-005)
# ---------------------------------------------------------------------------


def test_REQ_PNT_002_the_symbol_data_is_a_collection_of_named_points():
    data = raster.symbol_features()

    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) >= 5
    for feature in data["features"]:
        assert feature["geometry"]["type"] == "Point"
        assert feature["properties"]["name"]
        longitude, latitude = feature["geometry"]["coordinates"]
        assert -74.0 < longitude < -59.0
        assert 0.5 < latitude < 13.0


def test_REQ_PNT_003_the_icon_is_shipped_as_an_asset():
    import pathlib

    assert raster.ICON_NAME
    assert raster.ICON_URL.startswith("/")
    assert pathlib.Path("mapcn_demo/assets" + raster.ICON_URL).is_file()


def test_REQ_PNT_005_the_blank_basemap_is_offered_with_glyphs():
    # Labels need the style to declare its fonts; the blank basemap does not.
    assert raster.GLYPHS_URL.startswith("https://")
    assert "{fontstack}" in raster.GLYPHS_URL
    assert "{range}" in raster.GLYPHS_URL


# ---------------------------------------------------------------------------
# The page
# ---------------------------------------------------------------------------


def test_the_page_draws_a_raster_layer_and_a_symbol_layer():
    rendered = str(raster.raster_page().render())

    assert "MapcnRasterLayer" in rendered
    assert "MapcnSymbolLayer" in rendered


def test_the_page_is_registered_in_the_navigation():
    from mapcn_demo.layout import NAV

    assert any(href == "/raster" for _, href, _ in NAV)


def test_the_page_is_a_reflex_component():
    assert isinstance(raster.raster_page(), rx.Component)


# ---------------------------------------------------------------------------
# Each source at a scale where it can be seen
# ---------------------------------------------------------------------------


def test_every_source_declares_the_view_it_is_visible_at():
    for source in raster.SOURCES:
        view = raster.view_for(source)
        longitude, latitude = view["center"]
        assert -180.0 <= longitude <= 180.0
        assert -85.0 <= latitude <= 85.0
        assert 3.0 <= view["zoom"] <= 16.0


def test_traffic_is_shown_over_a_city_and_the_weather_over_the_country():
    # Traffic tiles carry nothing at country scale, and a cloud layer says
    # nothing from inside a city.
    assert raster.view_for(raster.source_by_key("tomtom_traffic"))["zoom"] >= 10
    assert raster.view_for(raster.source_by_key("openseamap"))["zoom"] >= 7
    assert raster.view_for(raster.source_by_key("openweather_clouds"))["zoom"] <= 6


def test_traffic_is_shown_where_the_service_has_coverage():
    # Measured 2026-09-12: a z13 TomTom flow tile over Caracas comes back at
    # 1.2 KB, an empty image, while Bogota returns 48 KB. Venezuela is not
    # covered, so the traffic view leaves the country on purpose.
    longitude, latitude = raster.view_for(raster.source_by_key("tomtom_traffic"))[
        "center"
    ]

    assert not (-74.0 < longitude < -59.0 and 0.5 < latitude < 13.0)
    assert abs(longitude - (-74.07)) < 0.5
    assert abs(latitude - 4.71) < 0.5


def test_selecting_a_source_hands_the_camera_a_command():
    command = raster.camera_for(raster.source_by_key("tomtom_traffic"), seq=3)

    assert command["type"] == "flyTo"
    assert command["seq"] == 3
    assert command["zoom"] >= 10
