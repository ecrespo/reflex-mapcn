#!/usr/bin/env python3
"""Validate the packaging metadata that PyPI rejects only at upload time.

`twine check` does not look at classifiers, so an unknown one is a 400 from
PyPI after the build has already been made. Run this before tagging::

    python scripts/check_metadata.py
    python scripts/check_metadata.py --expect-version v0.1.0

Exits non-zero and prints every problem it found.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import tomllib


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parent.parent,
        help="directory holding pyproject.toml (default: the repository root)",
    )
    parser.add_argument(
        "--expect-version",
        help="fail unless project.version matches this (a leading 'v' is fine)",
    )
    args = parser.parse_args()

    pyproject = args.project_root / "pyproject.toml"
    if not pyproject.is_file():
        print(f"error: {pyproject} not found", file=sys.stderr)
        return 1

    project = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]
    problems: list[str] = []

    try:
        from trove_classifiers import classifiers as known
    except ImportError:
        print("error: trove-classifiers is not installed", file=sys.stderr)
        return 1

    for classifier in project.get("classifiers", []):
        if classifier in known:
            print(f"  ok      {classifier}")
        else:
            print(f"  INVALID {classifier}")
            problems.append(f"{classifier!r} is not an official trove classifier")

    version = project["version"]
    print(f"\nversion: {version}")
    if args.expect_version:
        expected = args.expect_version.removeprefix("v")
        if version != expected:
            problems.append(
                f"project.version is {version!r} but {expected!r} was expected; "
                "bump the version or retag"
            )
        else:
            print(f"matches expected version {expected}")

    if problems:
        print("\nmetadata check failed:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print("\nmetadata check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
