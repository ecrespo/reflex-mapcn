"""The version has to be the same everywhere it is written down.

`pyproject.toml` is what PyPI and the release tag check, `__version__` is what
an application reads at runtime, and nothing kept them together: the release
script only rewrites the first one. A wheel that says two different things
about itself is a bug nobody notices until someone reports it.

The supported floor is written down in three places too: the Reflex
dependency, `requires-python` and the trove classifiers. They are checked
against each other for the same reason.
"""

from __future__ import annotations

import pathlib
import tomllib

import reflex_mapcn

PYPROJECT = pathlib.Path("pyproject.toml")


def project() -> dict:
    """The `[project]` table, the one PyPI publishes."""
    return tomllib.loads(PYPROJECT.read_text())["project"]


def declared_version() -> str:
    return project()["version"]


def test_the_package_reports_the_version_it_was_built_with():
    assert reflex_mapcn.__version__ == declared_version()


def test_the_version_is_a_release_number():
    parts = declared_version().split(".")

    assert len(parts) == 3, "SemVer, as article 7 of the constitution requires"
    assert all(part.isdigit() for part in parts)


def test_REQ_CMP_001_reflex_floor_is_0_10():
    assert "reflex>=0.10.0" in project()["dependencies"]


def test_REQ_CMP_002_python_floor_matches_the_classifiers():
    table = project()
    versions = sorted(
        classifier.rsplit(" :: ", 1)[1]
        for classifier in table["classifiers"]
        if classifier.startswith("Programming Language :: Python :: 3.")
    )

    assert table["requires-python"] == ">=3.11"
    assert versions[0] == "3.11"
