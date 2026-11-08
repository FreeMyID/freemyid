"""Real-browser a11y checks on the app: 200% zoom (no sideways scroll), 44px targets, focus ring,
dark mode. Uses the real server and Playwright Chromium; fake person only; skips without a browser."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Error as PWError
from playwright.sync_api import sync_playwright

from freemyid.models import (
    Address,
    Consent,
    ConsentBasis,
    PersonName,
    Profile,
)
from tests.conftest import BROWSER_LAUNCH_TIMEOUT_MS, no_browser
from tests.test_wizard_v03 import _todo

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")
SHOTS = os.environ.get("FREEMYID_A11Y_SHOTS", "")


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        try:
            b = p.chromium.launch(headless=True, timeout=BROWSER_LAUNCH_TIMEOUT_MS)
        except PWError as e:
            no_browser(type(e).__name__)
        yield b
        b.close()


@pytest.fixture
def seeded(freemyid_env, monkeypatch):
    monkeypatch.setenv("FREEMYID_NO_BACKGROUND", "1")
    from freemyid.storage import Store
    from freemyid.wizard.server import start_background
    store = Store()
    p = Profile(label="Jane", name=PersonName(first="Jane", last="Testperson"),
                addresses=[Address(city="Springfield", state="IL", current=True)],
                consent=Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
                                text_version="t"))
    store.save_profile(p)
    store.save_todo(_todo(p))
    r = start_background()
    yield r, p
    r.stop()


def _open(browser, r, **ctx_args):
    origin = f"http://127.0.0.1:{r.port}"
    ctx = browser.new_context(**ctx_args)
    ctx.route("**/*", lambda route: route.continue_()
              if route.request.url.startswith(origin) else route.abort())
    pg = ctx.new_page()
    pg.goto(r.url)
    return ctx, pg, origin


def _paths(p):
    return ["/", f"/profile/{p.id}", f"/profile/{p.id}/site/examplebroker",
            f"/protect?p={p.id}", "/settings", "/outbox"]


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("width", [640, 320])   # 1280px at 200% zoom, and a narrow window
def test_no_sideways_scroll_and_big_targets(browser, seeded, scheme, width):
    r, p = seeded
    ctx, pg, origin = _open(browser, r, viewport={"width": width, "height": 900},
                            color_scheme=scheme)
    try:
        for path in _paths(p):
            pg.goto(origin + path)
            sw = pg.evaluate("document.documentElement.scrollWidth")
            assert sw <= width, f"{path} at {width}px {scheme}: scrolls sideways ({sw}px)"
            small = pg.evaluate("""() => [...document.querySelectorAll(
              'main a, main button, main summary, header a, header button, main input:not([type=hidden]), main select')]
              .map(e => (e.type === 'checkbox' || e.type === 'radio') && e.closest('label') ? e.closest('label') : e)
              .filter(e => e.offsetParent !== null && !e.closest('.skip'))
              .map(e => {const b = e.getBoundingClientRect();
                         const inline = getComputedStyle(e).display === 'inline' && e.tagName === 'A'
                                        && !e.classList.contains('btn');
                         return [e.tagName, (e.textContent||e.name||'').trim().slice(0,30),
                                 Math.round(b.width), Math.round(b.height), inline]})
              .filter(x => !x[4] && x[3] < 44)""")
            assert not small, f"{path}: targets under 44px tall: {small}"
            if SHOTS:
                tag = path.strip("/").replace("/", "-").replace("?p=", "-")[:20] or "today"
                pg.screenshot(path=str(Path(SHOTS) / f"after-{tag}-{width}-{scheme}.png"),
                              full_page=True)
    finally:
        ctx.close()


def test_keyboard_focus_is_visible_and_skip_link_works(browser, seeded):
    r, _ = seeded
    ctx, pg, origin = _open(browser, r, viewport={"width": 1024, "height": 768})
    try:
        pg.goto(origin + "/")
        pg.keyboard.press("Tab")
        first = pg.evaluate("document.activeElement.className")
        assert first == "skip"                                 # skip link is first in the order
        ring = pg.evaluate("""() => {const s = getComputedStyle(document.activeElement);
                               return [s.outlineStyle, parseFloat(s.outlineWidth)]}""")
        assert ring[0] != "none" and ring[1] >= 3
        pg.keyboard.press("Enter")
        assert pg.evaluate("document.activeElement.id") == "main"
        seen = set()
        for _ in range(12):                                    # every stop shows a ring
            pg.keyboard.press("Tab")
            if pg.evaluate("document.activeElement === document.body"):
                break                                          # wrapped past the last control
            ring = pg.evaluate("""() => {const s = getComputedStyle(document.activeElement);
                                 return [document.activeElement.tagName, s.outlineStyle,
                                         parseFloat(s.outlineWidth)]}""")
            seen.add(ring[0])
            assert ring[1] != "none" and ring[2] >= 3, ring
        assert seen
    finally:
        ctx.close()


def test_manual_dark_toggle_changes_colours_and_sticks(browser, seeded):
    r, _ = seeded
    ctx, pg, origin = _open(browser, r, color_scheme="light")
    try:
        pg.goto(origin + "/")
        before = pg.evaluate("getComputedStyle(document.body).backgroundColor")
        pg.locator("#theme-toggle").click()
        after = pg.evaluate("getComputedStyle(document.body).backgroundColor")
        assert before != after
        pg.goto(origin + "/settings")
        assert pg.evaluate("getComputedStyle(document.body).backgroundColor") == after
    finally:
        ctx.close()
