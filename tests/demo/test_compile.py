"""The compile check of the demo (T-019).

Every page registers itself with ``@rx.page`` on import, so a page that only
breaks when it is rendered would otherwise be found by opening it in a
browser. This builds all eleven of them and fails on the first one that
cannot be built.
"""

from __future__ import annotations

from mapcn_demo.layout import NAV

from scripts import compile_check


def test_every_navigation_entry_has_a_page_behind_it():
    routes = compile_check.registered_routes()

    for _, href, _ in NAV:
        assert href in routes, f"{href} is in the sidebar but registers no page"


def test_the_demo_registers_no_page_the_sidebar_hides():
    assert sorted(compile_check.registered_routes()) == sorted(
        href for _, href, _ in NAV
    )


def test_every_page_of_the_demo_builds():
    failures = compile_check.failures()

    assert failures == []


def test_the_check_reports_compile_ok(capsys):
    code = compile_check.main()

    assert code == 0
    assert "COMPILE OK" in capsys.readouterr().out


def test_the_check_names_the_page_that_breaks(capsys, monkeypatch):
    # The report is only worth running if a broken page is named in it.
    def broken():
        raise ValueError("no such colour")

    monkeypatch.setattr(
        compile_check, "registered_pages", lambda: [("/broken", broken)]
    )

    code = compile_check.main()

    out = capsys.readouterr().out
    assert code == 1
    assert "/broken" in out
    assert "no such colour" in out
    assert "COMPILE OK" not in out
