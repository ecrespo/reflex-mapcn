"""The version has to be the same everywhere it is written down.

`pyproject.toml` is what PyPI and the release tag check, `__version__` is what
an application reads at runtime, and nothing kept them together: the release
script only rewrites the first one. A wheel that says two different things
about itself is a bug nobody notices until someone reports it.
"""

from __future__ import annotations

import pathlib
import tomllib

import reflex_mapcn

PYPROJECT = pathlib.Path("pyproject.toml")


def declared_version() -> str:
    return tomllib.loads(PYPROJECT.read_text())["project"]["version"]


def test_the_package_reports_the_version_it_was_built_with():
    assert reflex_mapcn.__version__ == declared_version()


def test_the_version_is_a_release_number():
    parts = declared_version().split(".")

    assert len(parts) == 3, "SemVer, as article 7 of the constitution requires"
    assert all(part.isdigit() for part in parts)
