"""WO-110: native FAQ keyboard interactions against offline built pages.

The 640 CSS-pixel viewport at scale 2 models reflow at 200% on a 1280px
screen. It does not operate browser chrome zoom or test a screen reader.
"""

from collections.abc import Iterator

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Browser, Locator, Page, expect

from tests.test_web_home_hero_layout import BASE, ORIGIN, serve
from tests.test_web_home_hero_layout import browser as browser  # noqa: PLC0414


@pytest.fixture
def faq_page(browser: Browser, request: pytest.FixtureRequest) -> Iterator[Page]:
    path, width, scale, theme = request.param
    context = browser.new_context(
        viewport={"width": width, "height": 900}, device_scale_factor=scale,
        color_scheme=theme, reduced_motion="reduce", java_script_enabled=False,
    )
    context.route("**/*", serve)
    try:
        page = context.new_page()
        response = page.goto(ORIGIN + BASE + path, wait_until="load")
        assert response is not None and response.status == 200, "Build the FAQ pages first"
        yield page
    finally:
        context.close()


def tab_to(page: Page, target: Locator) -> None:
    """Reach a control using real Tab presses, rather than programmatic focus."""
    for _ in range(200):
        page.keyboard.press("Tab")
        if target.evaluate("el => el === document.activeElement"):
            return
    pytest.fail("FAQ summary or answer link could not be reached with Tab")


def assert_keyboard_focus(target: Locator) -> None:
    expect(target).to_be_focused()
    style = target.evaluate("""el => {
        const css = getComputedStyle(el);
        return {visible: el.matches(':focus-visible'), width: parseFloat(css.outlineWidth),
                style: css.outlineStyle, color: css.outlineColor};
    }""")
    assert style["visible"], "Keyboard focus must match :focus-visible"
    assert style["width"] >= 2 and style["style"] not in {"none", "hidden"}
    assert style["color"] not in {"transparent", "rgba(0, 0, 0, 0)"}


def assert_fits_width(page: Page, target: Locator) -> None:
    bounds = target.bounding_box()
    assert bounds is not None
    assert page.viewport_size is not None
    width = page.viewport_size["width"]
    assert bounds["x"] >= -1 and bounds["x"] + bounds["width"] <= width + 1
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")


@pytest.mark.parametrize(
    "faq_page",
    [(path, width, scale, theme)
     for path in ("", "faq/")
     for width, scale in ((320, 1), (640, 2))
     for theme in ("light", "dark")],
    ids=[f"{path or 'home'}-{width}-{scale}x-{theme}"
         for path in ("", "faq/")
         for width, scale in ((320, 1), (640, 2))
         for theme in ("light", "dark")],
    indirect=True,
)
def test_faq_disclosures_and_answer_links_work_with_keyboard_without_javascript(
    faq_page: Page,
) -> None:
    page = faq_page
    disclosures = page.locator("main details.faq-item")
    assert disclosures.count() > 1
    answers_with_links = 0
    for disclosure in disclosures.all():
        summary = disclosure.locator(":scope > summary")
        answer = disclosure.locator(":scope > div")
        tab_to(page, summary)
        assert_keyboard_focus(summary)
        assert_fits_width(page, summary)
        box = summary.bounding_box()
        assert box is not None and box["height"] >= 44 and box["width"] >= 44
        if disclosure.get_attribute("open") is not None:
            page.keyboard.press("Enter")
        expect(answer).to_be_hidden()
        for link in answer.locator("a").all():
            expect(link).to_be_hidden()

        page.keyboard.press("Enter")
        expect(disclosure).to_have_attribute("open", "")
        expect(answer).to_be_visible()
        assert_fits_width(page, answer)
        page.keyboard.press("Space")
        expect(disclosure).not_to_have_attribute("open", "")
        expect(answer).to_be_hidden()
        page.keyboard.press("Space")
        expect(answer).to_be_visible()

        links = answer.locator("a")
        if links.count():
            answers_with_links += 1
        for link in links.all():
            expect(link).to_be_visible()
            assert link.inner_text().strip() and link.get_attribute("href")
            tab_to(page, link)
            assert_keyboard_focus(link)
            assert_fits_width(page, link)
        # Advance naturally from the last answer link to the next summary.
        # Leaving this disclosure open lets Tab ordering verify reachable answers.
    assert answers_with_links > 0, "Exercise answer links as well as text-only answers"
