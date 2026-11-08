"""WO-118: offline browser checks of the built families helper page."""

from collections.abc import Iterator
from itertools import pairwise
from mimetypes import guess_type
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
import yaml

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Browser, Route, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "web/dist"
ORIGIN = "https://freemyid.test"
CONFIG = yaml.safe_load((ROOT / "site_src/site.yaml").read_text(encoding="utf-8"))
BASE = CONFIG["base_path"].rstrip("/") + "/"


@pytest.fixture(scope="module")
def browser() -> Iterator[Browser]:
    assert (DIST / "families/index.html").is_file(), "Build web/dist before WO-118 tests"
    with sync_playwright() as driver:
        instance = driver.chromium.launch(headless=True)
        yield instance
        instance.close()


def serve(route: Route) -> None:
    """Serve build output only; external requests are aborted."""
    url = urlsplit(route.request.url)
    if f"{url.scheme}://{url.netloc}" != ORIGIN or not url.path.startswith(BASE):
        route.abort()
        return
    path = (DIST / unquote(url.path[len(BASE):])).resolve()
    if not path.is_relative_to(DIST.resolve()):
        route.abort()
        return
    if path.is_dir():
        path /= "index.html"
    if not path.is_file():
        route.fulfill(status=404, body="Not found")
        return
    route.fulfill(body=path.read_bytes(), content_type=guess_type(path.name)[0] or "text/plain")


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("width,scale", [(320, 1), (640, 2)], ids=["320", "200pct-reflow"])
def test_families_content_fits_and_actions_are_reachable(
    browser: Browser, theme: str, width: int, scale: int,
) -> None:
    context = browser.new_context(
        viewport={"width": width, "height": 1000}, device_scale_factor=scale,
        color_scheme=theme, reduced_motion="reduce", java_script_enabled=False,
    )
    context.route("**/*", serve)
    try:
        page = context.new_page()
        page.goto(ORIGIN + BASE + "families/", wait_until="load")
        main = page.locator("main")
        expect(main.locator("h1")).to_have_count(1)
        expect(main.locator("h1")).to_contain_text("Helping a parent or grandparent")
        assert page.evaluate(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
        ), "The families page should fit without horizontal scrolling"
        card_links = page.get_by_role("link", name="Print the fridge card (PDF)")
        assert card_links.count() == 2  # hero and printable-card section
        for link in card_links.all():
            expect(link).to_be_visible()
        expect(page.get_by_role("link", name="Use the free guides instead")).to_be_visible()
        expect(page.get_by_role("link", name="See the answer on our Questions page.")).to_be_visible()
        # Every interactive text link has a useful name, reaches the viewport,
        # and keeps a visible keyboard outline when focused.
        links = main.locator("a:visible")
        assert links.count() >= 5
        for link in links.all():
            name = (link.inner_text() or "").strip()
            assert name, f"Unnamed link: {link.get_attribute('href')}"
            link.focus()
            assert link.evaluate("el => el.matches(':focus-visible')"), name
            style = link.evaluate("el => getComputedStyle(el)")
            assert style["outlineStyle"] != "none" and float(style["outlineWidth"].removesuffix("px")) > 0
            box = link.bounding_box()
            assert box is not None and box["x"] >= 0 and box["x"] + box["width"] <= width + 1, name
        # Exercise the real keyboard path to the skip link, then into the page.
        page.goto(ORIGIN + BASE + "families/", wait_until="load")
        page.keyboard.press("Tab")
        skip = page.locator("a.skip-link")
        assert skip.evaluate("el => el === document.activeElement")
        page.keyboard.press("Enter")
        assert main.evaluate("el => el === document.activeElement")
        # Ensure primary actions remain available with JavaScript disabled.
        download_links = main.get_by_role("link", name="Download Free My ID")
        assert download_links.count() == 2
        for link in download_links.all():
            expect(link).to_be_visible()
    finally:
        context.close()


def test_families_headings_are_in_order_and_images_have_text_alternatives(browser: Browser) -> None:
    context = browser.new_context(java_script_enabled=False)
    context.route("**/*", serve)
    try:
        page = context.new_page()
        page.goto(ORIGIN + BASE + "families/", wait_until="load")
        levels = page.locator("main h1, main h2, main h3, main h4, main h5, main h6").evaluate_all(
            "els => els.map(el => Number(el.tagName.slice(1)))"
        )
        assert levels and levels[0] == 1
        assert levels.count(1) == 1
        assert all(current <= previous + 1 for previous, current in pairwise(levels)), levels
        missing_alt = page.locator("main img:not([alt])").count()
        assert missing_alt == 0
    finally:
        context.close()


def test_printable_helper_card_reference_survives_print_media(browser: Browser) -> None:
    context = browser.new_context(java_script_enabled=False)
    context.route("**/*", serve)
    try:
        page = context.new_page()
        page.goto(ORIGIN + BASE + "families/", wait_until="load")
        page.emulate_media(media="print")
        link = page.locator("main a[href='/assets/free-my-id-fridge-card.pdf']").nth(1)
        expect(link).to_be_visible()
        expect(link).to_have_text("Print the fridge card (PDF)")
        assert link.get_attribute("href") == "/assets/free-my-id-fridge-card.pdf"
    finally:
        context.close()
