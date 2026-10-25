"""The demo's own documentation (T-019).

The demo reads five public services and ships two derived datasets, each with
a licence that asks to be named. These tests keep the README and the example
environment file honest as pages and sources are added.
"""

from __future__ import annotations

import pathlib

from mapcn_demo.layout import NAV

README = pathlib.Path("mapcn_demo/README.md")
ROOT_README = pathlib.Path("README.md")
ENV_EXAMPLE = pathlib.Path("mapcn_demo/.env.example")

OPTIONAL_KEYS = ("TOMTOM_API_KEY", "OPENWEATHER_API_KEY")


def test_the_demo_has_its_own_readme():
    assert README.is_file()


def test_the_readme_lists_every_page_of_the_sidebar():
    text = README.read_text()

    for label, href, _ in NAV:
        assert label in text, f"{label} is not documented"
        assert href in text, f"{href} is not documented"


def test_the_readme_names_every_external_source():
    text = README.read_text()

    for source in (
        "USGS",
        "GEM",
        "OSRM",
        "OpenStreetMap",
        "OpenFreeMap",
        "CARTO",
        "Superset",
    ):
        assert source in text, f"{source} is used by the demo but not credited"


def test_the_readme_names_the_licence_of_each_dataset():
    text = README.read_text()

    for licence in ("CC BY-SA", "ODbL", "Apache-2.0"):
        assert licence in text


def test_the_readme_says_how_to_run_the_demo():
    text = README.read_text()

    assert "reflex run" in text


def test_the_readme_runs_the_demo_without_pruning_the_dev_tools():
    # `uv run` syncs the project environment first, and without the extra it
    # removes pytest and ruff from it (T-020, H-02).
    text = README.read_text()

    assert "uv run --extra dev reflex run" in text
    assert "--extra dev" in text.split("## Pages")[0], "explained where it runs"


def test_the_package_readme_points_at_the_demo_readme():
    # The package README describes the demo in a paragraph; the detail, the
    # sources and the licences live in the demo's own file.
    assert "mapcn_demo/README.md" in ROOT_README.read_text()


def test_the_environment_example_declares_the_optional_keys():
    text = ENV_EXAMPLE.read_text()

    for key in OPTIONAL_KEYS:
        assert key in text


def test_the_environment_example_says_the_keys_are_optional():
    text = ENV_EXAMPLE.read_text().lower()

    assert "opcional" in text or "optional" in text


def test_the_environment_example_carries_no_secret():
    # It is committed, so every key has to be left empty.
    for line in ENV_EXAMPLE.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        name, _, value = stripped.partition("=")
        assert value == "", f"{name} ships a value"
