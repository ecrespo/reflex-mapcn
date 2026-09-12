"""Build every page of the demo and report the ones that break.

A Reflex page is only executed when it is rendered, so a bad prop or a Var
used where a value is needed stays invisible until someone opens that route.
This imports the demo, asks the registry for every route it declares and
builds them all.

Run it from the repository root::

    python scripts/compile_check.py
"""

from __future__ import annotations

import pathlib
import sys
import traceback
from collections.abc import Callable

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEMO_ROOT = REPO_ROOT / "mapcn_demo"


def _load_pages() -> list[tuple[str, Callable]]:
    """Import the demo and read the routes it registered on the way in."""
    if str(DEMO_ROOT) not in sys.path:
        sys.path.insert(0, str(DEMO_ROOT))

    import mapcn_demo.pages  # noqa: F401  (registers the routes)
    from reflex_base.registry import RegistrationContext

    context = RegistrationContext.ensure_context()
    return [
        (kwargs.get("route", "/"), render) for render, kwargs in context.decorated_pages
    ]


def registered_pages() -> list[tuple[str, Callable]]:
    """Every route of the demo with the function that builds it."""
    return _load_pages()


def registered_routes() -> list[str]:
    return [route for route, _ in registered_pages()]


def failures() -> list[tuple[str, str]]:
    """The routes that cannot be built, each with its traceback."""
    broken: list[tuple[str, str]] = []
    for route, render in registered_pages():
        try:
            render()
        except Exception:  # noqa: BLE001 - every failure is worth reporting
            broken.append((route, traceback.format_exc()))
    return broken


def main() -> int:
    """Print one line per route and a verdict. Returns a shell exit code."""
    broken = failures()
    routes = registered_routes()

    for route in sorted(routes):
        mark = "FAIL" if any(route == name for name, _ in broken) else "ok"
        print(f"  {mark:>4}  {route}")

    if broken:
        for route, error in broken:
            print(f"\n{route} does not build:\n{error}")
        print(f"COMPILE FAILED: {len(broken)} of {len(routes)} pages")
        return 1

    print(f"COMPILE OK: {len(routes)} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
