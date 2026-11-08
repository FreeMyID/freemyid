"""WO-115: native header menu geometry and keyboard regression checks.

Assets are fulfilled from built files offline with JavaScript disabled. These
checks cover Chromium's native popover, not an emulation of older browsers.
The accepted tab-out closure limitation is deliberately outside this contract.
"""

from collections.abc import Iterator

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Browser, Locator, Page, expect

from tests.test_web_faq_keyboard import assert_keyboard_focus, tab_to
from tests.test_web_home_hero_layout import BASE, ORIGIN, browser, serve

__all__ = ["browser"]  # Re-export the existing module-scoped pytest fixture.


@pytest.fixture
def navigation_page(browser: Browser, request: pytest.FixtureRequest) -> Iterator[Page]:
    width, theme = request.param
    context = browser.new_context(
        viewport={"width": width, "height": 900}, color_scheme=theme,
        reduced_motion="reduce", java_script_enabled=False,
    )
    context.route("**/*", serve)
    try:
        page = context.new_page()
        response = page.goto(ORIGIN + BASE, wait_until="load")
        assert response is not None and response.status == 200, "Build web/dist first"
        yield page
    finally:
        context.close()


def assert_inside_viewport(page: Page, links: Locator) -> None:
    """Use site_shots.py's visible-link rectangle check without modifying it."""
    assert links.count() > 0
    for link in links.all():
        expect(link).to_be_visible()
        bounds = link.bounding_box()
        assert bounds is not None and bounds["width"] > 0 and bounds["height"] > 0
        assert page.viewport_size is not None
        assert bounds["x"] >= 0, (link.inner_text(), bounds)
        assert bounds["x"] + bounds["width"] <= page.viewport_size["width"], (
            link.inner_text(), bounds,
        )
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


@pytest.mark.parametrize(
    "navigation_page",
    [(width, theme) for width in (320, 360, 390, 414) for theme in ("light", "dark")],
    ids=[f"{width}-{theme}" for width in (320, 360, 390, 414) for theme in ("light", "dark")],
    indirect=True,
)
def test_phone_menu_opens_with_keyboard_fits_and_returns_focus(navigation_page: Page) -> None:
    page = navigation_page
    assert page.evaluate("'popover' in HTMLElement.prototype"), "Requires native popover support"
    toggle = page.locator('header button[popovertarget="site-menu"]')
    panel = page.locator("header #site-menu")
    expect(toggle).to_be_visible()
    expect(page.locator("header .menu-fallback > summary")).to_be_hidden()
    expect(panel).to_be_hidden()
    inline_links = page.locator('header nav[aria-label="Main"] > ul > li > a')
    panel_links = panel.locator("a")
    expected = [(link.inner_text(), link.get_attribute("href")) for link in inline_links.all()]
    assert expected
    assert [(link.inner_text(), link.get_attribute("href")) for link in panel_links.all()] == expected

    tab_to(page, toggle)
    assert_keyboard_focus(toggle)
    for opening_key in ("Enter", "Space"):
        page.keyboard.press(opening_key)
        expect(panel).to_be_visible()
        assert panel.evaluate("el => el.matches(':popover-open')")
        assert_inside_viewport(page, panel_links)
        for link in panel_links.all():
            page.keyboard.press("Tab")
            expect(link).to_be_focused()
            assert_keyboard_focus(link)
        page.keyboard.press("Escape")
        expect(panel).to_be_hidden()
        assert not panel.evaluate("el => el.matches(':popover-open')")
        expect(toggle).to_be_focused()


@pytest.mark.parametrize(
    "navigation_page", [(1280, "light"), (1280, "dark")],
    ids=["1280-light", "1280-dark"], indirect=True,
)
def test_desktop_navigation_is_visible_without_the_phone_toggle(navigation_page: Page) -> None:
    page = navigation_page
    links = page.locator('header nav[aria-label="Main"] > ul > li > a')
    assert_inside_viewport(page, links)
    expect(page.locator('header button[popovertarget="site-menu"]')).to_be_hidden()
    expect(page.locator("header .menu-fallback > summary")).to_be_hidden()
    expect(page.locator("header #site-menu")).to_be_hidden()
    for link in links.all():
        assert link.inner_text().strip() and link.get_attribute("href")
        tab_to(page, link)
        assert_keyboard_focus(link)
