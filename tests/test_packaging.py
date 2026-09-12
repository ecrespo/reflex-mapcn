"""The version has to be the same everywhere it is written down.

`pyproject.toml` is what PyPI and the release tag check, `__version__` is what
an application reads at runtime, and nothing kept them together: the release
script only rewrites the first one. A wheel that says two different things
about itself is a bug nobody notices until someone reports it.

The version is read with a regular expression rather than with `tomllib`,
which only exists from Python 3.11 and this package supports 3.10.
"""

from __future__ import annotations

import pathlib
import re

import reflex_mapcn

PYPROJECT = pathlib.Path("pyproject.toml")

VERSION_LINE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)


def declared_version() -> str:
    """The version of the `[project]` table, the one PyPI publishes."""
    text = PYPROJECT.read_text()
    project = text.split("[project]", 1)[1].split("\n[", 1)[0]
    match = VERSION_LINE.search(project)
    assert match, "no version in the [project] table of pyproject.toml"
    return match.group(1)


def test_the_package_reports_the_version_it_was_built_with():
    assert reflex_mapcn.__version__ == declared_version()


def test_the_version_is_a_release_number():
    parts = declared_version().split(".")

    assert len(parts) == 3, "SemVer, as article 7 of the constitution requires"
    assert all(part.isdigit() for part in parts)
