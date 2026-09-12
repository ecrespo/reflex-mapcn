"""Tests for the travel-time panel of the country page (T-018).

A Reflex state cannot be instantiated outside an app, so everything the page
decides lives in plain functions: which capitals are asked about, how a
duration reads in the table, in what order the rows land and where the camera
goes once a route is drawn.
"""

from __future__ import annotations

import reflex as rx
from mapcn_demo.pages import venezuela
from mapcn_demo.venezuela_data import (
    CAPITALS,
    CITIES,
    CONTINENTAL_CAPITALS,
    INSULAR_STATES,
    STATE_INFO,
)

# ---------------------------------------------------------------------------
# Which places are asked about (REQ-TVJ-001)
# ---------------------------------------------------------------------------


def test_REQ_TVJ_001_every_state_capital_has_coordinates():
    # Isla de Aves is the one state without a capital to drive to.
    expected = {name for name, info in STATE_INFO.items() if info["capital"] != "—"}

    assert set(CAPITALS) == expected
    for capital in CAPITALS.values():
        assert capital.name
        assert -74.0 < capital.lng < -59.0
        assert 0.5 < capital.lat < 13.0


def test_REQ_TVJ_001_capital_coordinates_come_from_the_city_markers():
    cities = {city.name: (city.lng, city.lat) for city in CITIES}

    for capital in CAPITALS.values():
        assert (capital.lng, capital.lat) == cities[capital.name]


def test_REQ_TVJ_001_the_islands_are_not_driving_destinations():
    names = {capital.state for capital in CONTINENTAL_CAPITALS}

    assert names.isdisjoint(INSULAR_STATES)
    assert len(CONTINENTAL_CAPITALS) == 23
    assert "Distrito Capital" in names


def test_REQ_TVJ_001_a_table_from_caracas_asks_about_the_other_22_capitals():
    destinations = venezuela.destinations_for("Distrito Capital")

    assert len(destinations) == 22
    assert all(capital.state != "Distrito Capital" for capital in destinations)
    assert len(destinations) <= venezuela.MAX_DESTINATIONS


def test_REQ_TVJ_001_an_island_capital_still_asks_about_the_mainland():
    # Nueva Esparta has no road to anywhere, which is a matrix full of holes
    # rather than a missing panel.
    destinations = venezuela.destinations_for("Nueva Esparta")

    assert len(destinations) == 23
    assert venezuela.capital_of("Nueva Esparta").name == "La Asunción"


def test_REQ_TVJ_001_a_state_without_a_capital_has_nothing_to_ask():
    assert venezuela.capital_of("Isla de Aves") is None
    assert venezuela.destinations_for("Isla de Aves") == []


# ---------------------------------------------------------------------------
# How a row reads (REQ-TVJ-001, REQ-TVJ-002)
# ---------------------------------------------------------------------------


def test_REQ_TVJ_001_a_duration_reads_in_hours_and_minutes():
    assert venezuela.format_duration(19800) == "5h 30m"
    assert venezuela.format_duration(7200) == "2h 0m"


def test_REQ_TVJ_001_under_an_hour_only_minutes_are_shown():
    assert venezuela.format_duration(2700) == "45 min"


def test_REQ_TVJ_002_a_missing_duration_reads_sin_ruta():
    assert venezuela.format_duration(None) == "sin ruta"


def test_REQ_TVJ_001_a_distance_reads_in_kilometres():
    assert venezuela.format_distance(412300.5) == "412 km"


def test_REQ_TVJ_002_a_missing_distance_reads_as_a_dash():
    assert venezuela.format_distance(None) == "—"


def test_REQ_TVJ_001_the_rows_are_ordered_by_how_long_the_drive_takes():
    destinations = venezuela.destinations_for("Distrito Capital")[:3]
    rows = venezuela.build_travel_rows(
        destinations, [19800.0, 3600.0, 7200.0], [412300.0, 90000.0, 154000.0]
    )

    assert [row.duration_s for row in rows] == [3600.0, 7200.0, 19800.0]
    assert [row.capital for row in rows] == [
        destinations[1].name,
        destinations[2].name,
        destinations[0].name,
    ]
    assert rows[0].duration_label == "1h 0m"
    assert rows[0].distance_label == "90 km"


def test_REQ_TVJ_002_a_row_without_a_route_sinks_to_the_bottom():
    destinations = venezuela.destinations_for("Distrito Capital")[:3]
    rows = venezuela.build_travel_rows(
        destinations, [None, 3600.0, None], [None, 90000.0, None]
    )

    assert rows[0].duration_s == 3600.0
    assert [row.duration_label for row in rows[1:]] == ["sin ruta", "sin ruta"]
    assert rows[1].distance_label == "—"


def test_REQ_TVJ_002_a_matrix_shorter_than_the_destinations_still_builds_rows():
    destinations = venezuela.destinations_for("Distrito Capital")[:3]
    rows = venezuela.build_travel_rows(destinations, [], [])

    assert len(rows) == 3
    assert all(row.duration_s is None for row in rows)


def test_REQ_TVJ_001_a_row_carries_the_coordinates_the_route_starts_from():
    destinations = venezuela.destinations_for("Distrito Capital")[:1]
    row = venezuela.build_travel_rows(destinations, [3600.0], [90000.0])[0]

    assert (row.lng, row.lat) == (destinations[0].lng, destinations[0].lat)
    assert row.state == destinations[0].state


# ---------------------------------------------------------------------------
# The drawn route (REQ-TVJ-003)
# ---------------------------------------------------------------------------


def test_REQ_TVJ_003_the_camera_is_given_the_box_around_the_route():
    bounds = venezuela.bounds_of([[-66.9, 10.5], [-67.4, 10.3], [-68.0, 10.2]])

    assert bounds == [[-68.0, 10.2], [-66.9, 10.5]]


def test_REQ_TVJ_003_an_empty_route_has_no_box():
    assert venezuela.bounds_of([]) is None


# ---------------------------------------------------------------------------
# The page itself
# ---------------------------------------------------------------------------


def test_REQ_TVJ_003_the_page_can_draw_the_selected_route():
    rendered = str(venezuela.venezuela_page().render())

    assert "MapcnMapRoute" in rendered


def test_REQ_TVJ_001_the_page_offers_the_travel_times():
    rendered = str(venezuela.venezuela_page().render())

    assert "Tiempos de viaje" in rendered


def test_REQ_TVJ_003_the_page_credits_osrm_and_openstreetmap():
    assert "OSRM" in venezuela.TRAVEL_ATTRIBUTION
    assert "OpenStreetMap" in venezuela.TRAVEL_ATTRIBUTION


def test_REQ_TVJ_003_the_credit_is_on_the_page_and_not_only_in_the_module():
    rendered = str(venezuela.venezuela_page().render())

    assert "router.project-osrm.org" in rendered


def test_the_page_is_still_a_reflex_component():
    assert isinstance(venezuela.venezuela_page(), rx.Component)
