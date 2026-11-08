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
