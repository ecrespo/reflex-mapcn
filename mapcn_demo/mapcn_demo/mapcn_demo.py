"""reflex-mapcn demo application.

Every page lives in ``mapcn_demo/pages`` and registers itself with
``@rx.page``; importing the package is enough to add all routes. The Radix
theme is configured through ``RadixThemesPlugin`` in ``rxconfig.py``.
"""

import reflex as rx

from . import pages  # noqa: F401  (registers the routes)

app = rx.App(
    style={
        "font_family": "Inter, system-ui, sans-serif",
    },
)
