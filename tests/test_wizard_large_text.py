"""BL-IN-22: persistent large-text mode (cookie fmi_text), no sideways scroll at 320px."""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_wizard_a11y_browser import _open, _paths, browser, seeded  # noqa: F401

pytestmark = pytest.mark.browser


def test_toggle_markup_and_script_are_shipped():
    from freemyid.wizard import ui
    static = Path(ui.__file__).parent / "static"
    js = (static / "theme.js").read_text()
    assert "fmi_text=large" in js and "data-text" in js
    assert 'html[data-text="large"]' in (static / "style.css").read_text()
    assert 'id="text-toggle"' in ui.layout("t", "<p>x</p>")


def test_toggle_scales_text_and_sticks(browser, seeded):  # noqa: F811
    r, _p = seeded
    ctx, pg, origin = _open(browser, r, viewport={"width": 1000, "height": 800})
    try:
        base = pg.evaluate("parseFloat(getComputedStyle(document.body).fontSize)")
        pg.click("#text-toggle")
        assert pg.get_attribute("#text-toggle", "aria-pressed") == "true"
        big = pg.evaluate("parseFloat(getComputedStyle(document.body).fontSize)")
        assert big == pytest.approx(base * 1.25, rel=0.01)
        pg.goto(origin + "/settings")           # remembered on the next page
        assert pg.get_attribute("html", "data-text") == "large"
        pg.click("#text-toggle")                # and can be turned off again
        assert pg.get_attribute("html", "data-text") is None
    finally:
        ctx.close()


@pytest.mark.parametrize("width", [640, 320])
def test_large_text_no_sideways_scroll(browser, seeded, width):  # noqa: F811
    r, p = seeded
    ctx, pg, origin = _open(browser, r, viewport={"width": width, "height": 900})
    try:
        pg.click("#text-toggle")
        for path in _paths(p):
            pg.goto(origin + path)
            sw = pg.evaluate("document.documentElement.scrollWidth")
            assert sw <= width, f"{path} at {width}px large text scrolls sideways ({sw}px)"
    finally:
        ctx.close()


@pytest.mark.parametrize("width", [640, 320])
def test_proof_fields_fit_and_are_big_enough_with_large_text(browser, seeded, width):  # noqa: F811
    from freemyid.models import Todo, TodoKind
    from freemyid.storage import Store
    r, p = seeded
    store = Store()
    store.save_todo(Todo(profile_id=p.id, broker_id="callbroker", kind=TodoKind.PHONE_CALL,
                         title="Call them", body="Say: please delete me."))
    store.save_todo(Todo(profile_id=p.id, broker_id="mailbroker", kind=TodoKind.POSTAL_LETTER,
                         title="Mail the letter", body="Print and mail it."))
    ctx, pg, origin = _open(browser, r, viewport={"width": width, "height": 900})
    try:
        pg.click("#text-toggle")
        pg.goto(origin + "/more")
        assert pg.evaluate("document.documentElement.scrollWidth") <= width
        assert pg.locator("textarea[name=note]").count() + pg.locator("input[name=receipt]").count() >= 1
        for sel in ("textarea[name=note]", "input[name=receipt]", "form button.primary"):
            for i in range(pg.locator(sel).count()):
                el = pg.locator(sel).nth(i)
                if el.is_visible():
                    assert el.bounding_box()["height"] >= 44, sel
        labels = pg.evaluate("""() => [...document.querySelectorAll('textarea[name=note], input[name=receipt]')]
            .map(e => !!document.querySelector('label[for="' + e.id + '"]'))""")
        assert all(labels)
    finally:
        ctx.close()


@pytest.mark.parametrize("path", ["/", "/more", "/profile/{pid}/site/examplebroker"])
def test_today_more_and_broker_fit_320_with_large_text_and_keyboard(browser, seeded, path):  # noqa: F811
    from freemyid.models import Todo, TodoKind
    from freemyid.storage import Store
    r, p = seeded
    Store().save_todo(Todo(profile_id=p.id, broker_id="examplebroker", kind=TodoKind.ASSISTED_OPT_OUT,
                           title="Remove your listing", body="1. Find it\n2. Click Remove"))
    ctx, pg, origin = _open(browser, r, viewport={"width": 320, "height": 800})
    try:
        pg.click("#text-toggle")
        pg.goto(origin + path.format(pid=p.id))
        assert pg.evaluate("document.documentElement.scrollWidth") <= 320
        pg.keyboard.press("Tab")
        assert pg.evaluate("document.activeElement !== document.body")
        for el in pg.locator("a.btn, button").all():
            if el.is_visible():
                assert el.bounding_box()["height"] >= 40
    finally:
        ctx.close()
