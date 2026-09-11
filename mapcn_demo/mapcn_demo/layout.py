"""Shared page shell: sidebar navigation + content column."""

from __future__ import annotations

import reflex as rx

NAV = [
    ("Basic map", "/", "map"),
    ("Markers", "/markers", "map-pin"),
    ("Popups", "/popups", "message-square"),
    ("Controls", "/controls", "sliders-horizontal"),
    ("Routes", "/routes", "route"),
    ("Arcs", "/arcs", "globe"),
    ("GeoJSON", "/geojson", "layers"),
    ("Clusters", "/clusters", "circle-dot"),
    ("Advanced", "/advanced", "settings-2"),
    ("Venezuela", "/venezuela", "flag"),
]


def nav_link(label: str, href: str, icon: str) -> rx.Component:
    return rx.link(
        rx.hstack(
            rx.icon(icon, size=16),
            rx.text(label, size="2"),
            spacing="2",
            align="center",
        ),
        href=href,
        underline="none",
        color=rx.cond(
            rx.State.router.url.path == href,
            rx.color("accent", 11),
            rx.color("gray", 11),
        ),
        background_color=rx.cond(
            rx.State.router.url.path == href,
            rx.color("accent", 3),
            "transparent",
        ),
        border_radius="6px",
        padding="6px 10px",
        width="100%",
        _hover={"background_color": rx.color("gray", 3)},
    )


def sidebar() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.icon("map", size=20, color=rx.color("accent", 10)),
            rx.heading("reflex-mapcn", size="4"),
            rx.spacer(),
            rx.color_mode.button(size="1", variant="ghost"),
            spacing="2",
            align="center",
            width="100%",
            padding_bottom="8px",
        ),
        rx.text(
            "mapcn map components wrapped for Reflex",
            size="1",
            color=rx.color("gray", 10),
            padding_bottom="12px",
        ),
        *[nav_link(label, href, icon) for label, href, icon in NAV],
        rx.spacer(),
        rx.hstack(
            rx.link(
                rx.icon("code", size=18),
                href="https://github.com/ecrespo/reflex-mapcn",
                is_external=True,
                color=rx.color("gray", 11),
            ),
            rx.link(
                rx.text("mapcn.dev", size="1"),
                href="https://www.mapcn.dev",
                is_external=True,
                color=rx.color("gray", 11),
            ),
            spacing="3",
            align="center",
        ),
        spacing="1",
        align="start",
        width="220px",
        min_width="220px",
        height="100vh",
        position="sticky",
        top="0",
        padding="20px 14px",
        border_right=f"1px solid {rx.color('gray', 5)}",
        background_color=rx.color("gray", 1),
    )


def demo_frame(*children: rx.Component, height: str = "480px") -> rx.Component:
    """Card that hosts a map demo with a fixed height."""
    return rx.box(
        *children,
        height=height,
        width="100%",
        position="relative",
        overflow="hidden",
        border_radius="12px",
        border=f"1px solid {rx.color('gray', 5)}",
        background_color=rx.color("gray", 2),
    )


def code(snippet: str) -> rx.Component:
    return rx.code_block(
        snippet.strip("\n"),
        language="python",
        show_line_numbers=False,
        width="100%",
        font_size="12px",
    )


def section(title: str, description: str, *children: rx.Component) -> rx.Component:
    return rx.vstack(
        rx.heading(title, size="5"),
        rx.text(description, size="2", color=rx.color("gray", 11)),
        *children,
        spacing="3",
        align="start",
        width="100%",
        padding_bottom="24px",
    )


def page(title: str, subtitle: str, *children: rx.Component) -> rx.Component:
    return rx.hstack(
        sidebar(),
        rx.vstack(
            rx.heading(title, size="8"),
            rx.text(subtitle, size="3", color=rx.color("gray", 11)),
            rx.divider(margin_y="12px"),
            *children,
            spacing="3",
            align="start",
            width="100%",
            max_width="1040px",
            padding="28px 32px 64px",
        ),
        spacing="0",
        align="start",
        width="100%",
        min_height="100vh",
    )
