"""In-house contrast fixes from docs/vendor/web-contrast-audit.md: CA-2, CA-3, CA-5, CA-6.

Ratios are recomputed from web/src/styles/tokens.css (light-dark() pairs) for both themes. The browser cases render
built CSS offline (no network) and read computed colours.
"""

import re
from collections.abc import Iterator
from mimetypes import guess_type
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "web/dist"
TOKENS = (ROOT / "web/src/styles/tokens.css").read_text(encoding="utf-8")
GLOBAL = (ROOT / "web/src/styles/global.css").read_text(encoding="utf-8")
SECTION = (ROOT / "web/src/components/Section.astro").read_text(encoding="utf-8")
SMARTSCREEN = (ROOT / "web/src/components/SmartScreen.astro").read_text(encoding="utf-8")


def token(name: str) -> tuple[str, str]:
    m = re.search(rf"--fmi-color-{name}:\s*light-dark\((#[0-9a-f]{{6}}),\s*(#[0-9a-f]{{6}})\)", TOKENS)
    assert m, name
    return m[1], m[2]


def lum(hex_: str) -> float:
    def ch(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def ratio(a: str, b: str) -> float:
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def rgb_hex(css: str) -> str:
    nums = [int(float(x)) for x in re.findall(r"[\d.]+", css)[:3]]
    return "#" + "".join(f"{n:02x}" for n in nums)


# ------------------------------------------------------------------ CA-3 focus ring (token pairs, both themes)
@pytest.mark.parametrize("theme", [0, 1])
@pytest.mark.parametrize("surface", ["bg", "bg-alt", "card", "band-brand"])
def test_ca3_focus_ring_pair_meets_3_to_1(theme: int, surface: str) -> None:
    bg = token(surface)[theme]
    gold, inner = token("focus")[theme], token("focus-inner")[theme]
    assert max(ratio(gold, bg), ratio(inner, bg)) >= 3, (surface, theme)
    if theme == 0:  # light: the dark inner ring carries the contrast, so it must also separate from the gold
        assert ratio(gold, inner) >= 3


def test_ca3_inner_ring_kept() -> None:
    assert "box-shadow: 0 0 0 3px var(--fmi-color-focus-inner) !important" in GLOBAL
    assert "do not remove the inner ring" in GLOBAL


# ------------------------------------------------------------------ CA-5 SmartScreen fixed colours
def test_ca5_smartscreen_colours() -> None:
    for c in ("#0b5394", "#fff", "#f2b705"):
        assert c in SMARTSCREEN
    assert ratio("#ffffff", "#0b5394") >= 7
    assert ratio("#f2b705", "#0b5394") >= 3


# ------------------------------------------------------------------ CA-2 brand band (source + tokens)
def test_ca2_band_rule_skips_button_links() -> None:
    assert "[&_a]:text-band-brand-ink" not in SECTION
    assert "[&_a:not(.no-underline)]:text-band-brand-ink" in SECTION
    for theme in (0, 1):
        band, ink = token("band-brand")[theme], token("band-brand-ink")[theme]
        assert ratio(ink, band) >= 7  # prose links and text in the band
        assert ratio(band, ink) >= 4.5  # onBrand button: band colour text on ink background


# ------------------------------------------------------------------ browser: CA-2 and CA-6 on built CSS
pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Browser, Route, sync_playwright

ORIGIN = "https://freemyid.test"
BASE = yaml.safe_load((ROOT / "site_src/site.yaml").read_text(encoding="utf-8"))["base_path"].rstrip("/") + "/"
BAND = re.search(r'tone === "brand" && "([^"]+)"', SECTION)[1]  # type: ignore[index]
PRIMARY = "inline-flex items-center justify-center rounded-lg font-bold no-underline bg-brand text-brand-ink min-h-tap px-m"
ON_BRAND = "inline-flex items-center justify-center rounded-lg font-bold no-underline bg-band-brand-ink text-band-brand min-h-tap px-m"


@pytest.fixture(scope="module")
def browser() -> Iterator[Browser]:
    assert (DIST / "index.html").is_file(), "Build web/dist first"
    with sync_playwright() as driver:
        instance = driver.chromium.launch(headless=True)
        yield instance
        instance.close()


def serve(route: Route) -> None:
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


INJECT = """([band, primary, onBrand]) => {
  const s = document.createElement('section');
  s.className = band;
  s.innerHTML = `<p>Text with <a id="t-prose" href="#">a plain link</a>.</p>
    <a id="t-onbrand" class="${onBrand}" href="#">On brand</a> <a id="t-primary" class="${primary}" href="#">Primary</a>`;
  document.querySelector('main').prepend(s);
}"""
COLORS = """(id) => { const cs = getComputedStyle(document.getElementById(id));
  return [cs.color, cs.backgroundColor, getComputedStyle(document.getElementById(id).closest('section')).backgroundColor]; }"""


@pytest.mark.browser
@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_ca2_buttons_keep_their_colours_in_brand_band(browser: Browser, scheme: str) -> None:
    page = browser.new_page(color_scheme=scheme)
    try:
        page.route("**/*", serve)
        page.goto(f"{ORIGIN}{BASE}")
        page.evaluate(INJECT, [BAND, PRIMARY, ON_BRAND])
        text, _, band = (rgb_hex(c) for c in page.evaluate(COLORS, "t-prose"))
        assert ratio(text, band) >= 7, ("prose link", scheme, text, band)
        for btn in ("t-onbrand", "t-primary"):
            fg, bg, _ = (rgb_hex(c) for c in page.evaluate(COLORS, btn))
            assert ratio(fg, bg) >= 4.5, (btn, scheme, fg, bg)
    finally:
        page.close()


@pytest.mark.browser
def test_ca6_forced_colors_borders_and_focus(browser: Browser) -> None:
    ctx = browser.new_context(forced_colors="active")
    page = ctx.new_page()
    try:
        page.route("**/*", serve)
        page.goto(f"{ORIGIN}{BASE}")
        cta = page.locator("main a.no-underline.inline-flex").first
        assert float(cta.evaluate("e => getComputedStyle(e).borderTopWidth").rstrip("px")) >= 2
        cta.focus()
        page.keyboard.press("Shift+Tab")
        page.keyboard.press("Tab")
        style = page.evaluate("() => { const cs = getComputedStyle(document.activeElement); "
                              "return [cs.outlineStyle, cs.outlineWidth]; }")
        assert style[0] == "solid" and float(style[1].rstrip("px")) >= 3
    finally:
        ctx.close()
