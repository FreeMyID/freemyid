"""WO-103: offline browser checks for the built home hero's action layout.

The 200% case models a 1280px desktop as a 640 CSS-pixel viewport rendered
at device scale 2. It checks zoom-equivalent reflow, not browser chrome controls.
"""

from collections.abc import Iterator
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
RELEASE = yaml.safe_load((ROOT / "site_src/data/release.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def browser() -> Iterator[Browser]:
    assert (DIST / "index.html").is_file(), "Build web/dist before running WO-103 tests"
    with sync_playwright() as driver:
        instance = driver.chromium.launch(headless=True)
        yield instance
        instance.close()


def serve(route: Route) -> None:
    """Serve built files only; all requests are fulfilled offline or aborted."""
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


GEOMETRY = """(actions) => {
    const links = [...actions.querySelectorAll('a')];
    const box = el => {
        const r = el.getBoundingClientRect();
        return {left:r.left, right:r.right, top:r.top, bottom:r.bottom,
                width:r.width, height:r.height};
    };
    const textBox = (el, needle) => {
        const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
        let node;
        while ((node = walker.nextNode())) {
            const start = node.textContent.indexOf(needle);
            if (start >= 0) {
                const range = document.createRange();
                range.setStart(node, start);
                range.setEnd(node, start + needle.length);
                return [...range.getClientRects()].map(box => ({
                    left:box.left, right:box.right, top:box.top, bottom:box.bottom
                }));
            }
        }
        return [];
    };
    return {
        viewport: innerWidth, scroll: document.documentElement.scrollWidth,
        actions: box(actions), column: box(actions.parentElement),
        links: links.map(box), gap: parseFloat(getComputedStyle(actions).rowGap),
        brand: textBox(links[0], 'Free My ID'),
        secondary: textBox(links[1], 'See how it works')
    };
}"""


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize(
    ("width", "scale"),
    [(320, 1), (360, 1), (390, 1), (1280, 1), (640, 2)],
    ids=["320", "360", "390", "1280", "desktop-200pct-reflow"],
)
def test_home_hero_actions_fit_and_keep_the_brand_together(
    browser: Browser, theme: str, width: int, scale: int,
) -> None:
    context = browser.new_context(
        viewport={"width": width, "height": 1000}, device_scale_factor=scale,
        color_scheme=theme, reduced_motion="reduce", java_script_enabled=False,
    )
    context.route("**/*", serve)
    try:
        page = context.new_page()
        page.goto(ORIGIN + BASE, wait_until="load")
        actions = page.locator(".hero-actions")
        links = actions.locator("a")
        expect(links).to_have_count(2)
        expected_label = "Download Free My ID" if RELEASE["version"] else "Windows download: coming soon"
        expected_url = CONFIG["download_url"] if RELEASE["version"] else BASE + "download/"
        expect(links.nth(0)).to_have_text(expected_label)
        expect(links.nth(0)).to_have_attribute("href", expected_url)
        expect(links.nth(1)).to_have_text("See how it works")
        expect(links.nth(1)).to_have_attribute("href", BASE + "how-it-works/")
        geometry = actions.evaluate(GEOMETRY)
        assert geometry["scroll"] <= width + 1
        outer = geometry["actions"]
        primary, secondary = geometry["links"]
        for link in (primary, secondary):
            assert link["left"] >= 0 and link["right"] <= width + 1
            assert link["width"] >= 44 and link["height"] >= 44
            assert abs(link["left"] - outer["left"]) <= 1
            assert abs(link["width"] - outer["width"]) <= 1
        assert abs(secondary["top"] - primary["bottom"] - geometry["gap"]) <= 1
        if RELEASE["version"]:
            assert len(geometry["brand"]) == 1, "Free My ID must stay on one line"
            brand = geometry["brand"][0]
            assert brand["left"] >= primary["left"] and brand["right"] <= primary["right"]
        assert len(geometry["secondary"]) == 1
        if width < 900:
            assert abs(outer["width"] - geometry["column"]["width"]) <= 1
        else:
            assert abs(geometry["secondary"][0]["left"] - outer["left"]) <= 1
        artifacts = ROOT / "web/.astro/wo103-qa"
        artifacts.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(artifacts / f"after-{width}-{scale}x-{theme}.png"))
        page.keyboard.press("Tab")
        for index in (0, 1):
            link = links.nth(index)
            link.focus()
            assert link.evaluate("el => el.matches(':focus-visible')")
            assert link.evaluate("el => parseFloat(getComputedStyle(el).outlineWidth)") >= 2
            assert link.evaluate("el => getComputedStyle(el).outlineStyle") != "none"
    finally:
        context.close()
