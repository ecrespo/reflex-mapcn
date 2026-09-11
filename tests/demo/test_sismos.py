"""Tests for the seismic page's own logic (T-016).

Reflex states cannot be instantiated outside an app, so everything the page
decides lives in plain functions and is tested here: the time cutoff, the
combined MapLibre filter and the two clocks a popup shows.
"""

from __future__ import annotations

import reflex as rx
from mapcn_demo.pages import sismos
from mapcn_demo.venezuela_data import (
    DEPTH_COLOR,
    MAG_RADIUS,
    NOTABLE_QUAKES,
)


def test_REQ_SIS_004_the_cutoff_is_the_last_instant_of_the_selected_month():
    assert sismos.time_cutoff_ms(1990, 3) == 638927999999
    assert sismos.time_cutoff_ms(1900, 12) == -2177452800001


def test_REQ_SIS_004_the_cutoff_knows_about_leap_years():
    assert sismos.time_cutoff_ms(2024, 2) == 1709251199999


def test_REQ_SIS_004_the_filter_cuts_by_time():
    layer_filter = sismos.build_layer_filter(638927999999, 4.0, "all")

    assert layer_filter[0] == "all"
    assert ["<=", ["get", "time"], 638927999999] in layer_filter


def test_REQ_SIS_005_the_filter_combines_magnitude_and_depth():
    shallow = sismos.build_layer_filter(0, 5.5, "shallow")

    assert [">=", ["get", "mag"], 5.5] in shallow
    assert ["<", ["get", "depth"], 70] in shallow

    intermediate = sismos.build_layer_filter(0, 4.0, "intermediate")
    assert [">=", ["get", "depth"], 70] in intermediate
    assert ["<", ["get", "depth"], 300] in intermediate

    deep = sismos.build_layer_filter(0, 4.0, "deep")
    assert [">=", ["get", "depth"], 300] in deep


def test_REQ_SIS_005_the_default_band_adds_no_depth_clause():
    every_depth = sismos.build_layer_filter(0, 4.0, "all")

    assert not any("depth" in str(clause) for clause in every_depth)


def test_REQ_SIS_006_an_event_is_dated_in_utc_and_in_caracas():
    times = sismos.format_event_times(1689999000000)

    assert times["utc"] == "2023-07-22 04:10 UTC"
    assert times["caracas"] == "2023-07-22 00:10 Caracas"


def test_REQ_SIS_006_an_event_without_a_time_says_so():
    times = sismos.format_event_times(0)

    assert times["utc"] == "—"
    assert times["caracas"] == "—"


def test_REQ_SIS_001_radius_follows_magnitude_and_colour_follows_depth():
    assert MAG_RADIUS[0] == "interpolate"
    assert MAG_RADIUS[2] == ["get", "mag"]

    assert DEPTH_COLOR[0] == "step"
    assert DEPTH_COLOR[1] == ["get", "depth"]
    # The three bands seismology uses: shallow, intermediate and deep.
    assert 70 in DEPTH_COLOR and 300 in DEPTH_COLOR


def test_REQ_SIS_011_the_notable_earthquakes_are_listed_with_their_source():
    names = [quake.name for quake in NOTABLE_QUAKES]

    assert len(NOTABLE_QUAKES) == 4
    assert any("Cariaco" in name for name in names)
    assert any("1812" in quake.date for quake in NOTABLE_QUAKES)
    for quake in NOTABLE_QUAKES:
        assert quake.magnitude > 0
        assert -74 < quake.longitude < -59
        assert 0 < quake.latitude < 13
        assert quake.source


def test_REQ_SIS_012_the_page_credits_usgs_and_gem():
    assert "USGS" in sismos.ATTRIBUTION
    assert "GEM" in sismos.ATTRIBUTION
    assert "CC BY-SA" in sismos.ATTRIBUTION


def test_REQ_SIS_001_the_page_draws_the_catalogue_as_a_circle_layer():
    rendered = str(sismos.sismos_page().render())

    assert "MapcnCircleLayer" in rendered
    assert "MapcnMapPopup" in rendered
    assert "promoteId" in rendered


def test_the_page_is_registered_in_the_navigation():
    from mapcn_demo.layout import NAV

    assert any(href == "/sismos" for _, href, _ in NAV)


def test_the_page_component_is_a_reflex_component():
    assert isinstance(sismos.sismos_page(), rx.Component)


def test_REQ_SIS_005_the_depth_selector_maps_labels_back_to_bands():
    # The select shows Spanish labels; the filter needs the band key, or the
    # depth clause silently never matches.
    for band, label in sismos.DEPTH_BAND_LABELS.items():
        assert sismos.depth_band_from_label(label) == band

    assert sismos.depth_band_from_label("no such label") == "all"


# ---------------------------------------------------------------------------
# Optional layers (T-017)
# ---------------------------------------------------------------------------


def test_REQ_SIS_007_the_live_feed_is_polled_once_a_minute():
    assert sismos.LIVE_POLL_S == 60


def test_REQ_SIS_007_recent_events_get_their_own_ring():
    # The backend flags anything under 24 hours old; the ring layer draws only
    # those, since MapLibre cannot animate a pulse from state.
    assert sismos.RECENT_FILTER == ["==", ["get", "recent"], True]


def test_REQ_SIS_009_faults_are_coloured_by_slip_type():
    from mapcn_demo.venezuela_data import SLIP_TYPE_COLORS, SLIP_TYPE_DEFAULT_COLOR

    expression = sismos.FAULT_COLOR

    assert expression[0] == "match"
    assert expression[1] == ["get", "slip_type"]
    assert expression[-1] == SLIP_TYPE_DEFAULT_COLOR
    for slip_type, color in SLIP_TYPE_COLORS.items():
        assert slip_type in expression
        assert color in expression


def test_REQ_SIS_010_relief_uses_the_open_elevation_preset():
    assert sismos.TERRAIN_PRESET == "aws_terrarium"
    assert 1.0 < sismos.TERRAIN_EXAGGERATION < 3.0


def test_REQ_SIS_008_the_density_layer_weighs_by_magnitude_and_fades_out():
    assert sismos.HEATMAP_WEIGHT_PROPERTY == "mag"
    assert sismos.HEATMAP_MAX_ZOOM_FADE == 8


def test_REQ_SIS_007_the_page_carries_every_optional_layer():
    rendered = str(sismos.sismos_page().render())

    assert rendered.count("MapcnCircleLayer") >= 3, "history, live and recent ring"
    assert "MapcnHeatmapLayer" in rendered
    assert "MapcnLayer" in rendered, "the fault layer"
    assert "MapcnMapTerrain" in rendered
