"""Built-output regressions for the scoped page refresh; no network requests."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "web/dist"


class Document(HTMLParser):
    """Build a small queryable tree without a third-party HTML dependency."""

    def __init__(self, html: str) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("document")
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = SubElement(self.stack[-1], tag, {k: v or "" for k, v in attrs})
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input",
                       "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data: str) -> None:
        node = SubElement(self.stack[-1], "text")
        node.text = data


def text(node: Element) -> str:
    return " ".join("".join(node.itertext()).split())


def page(route: str) -> Element:
    path = DIST / route / "index.html"
    assert path.is_file(), "Run pnpm build before these required built-output checks"
    root = Document(path.read_text()).root
    assert any("site-refresh" in n.get("class", "").split() for n in root.iter())
    assert len(list(root.iter("h1"))) == 1
    assert all("style" not in n.attrib for n in root.iter())
    assert all(n.get("type") == "application/ld+json" for n in root.iter("script"))
    return root


def by_id(root: Element, value: str) -> Element:
    return next(n for n in root.iter() if n.get("id") == value)


def links(root: Element) -> set[str]:
    return {n.get("href", "") for n in root.iter("a")}


def test_configuration_table_keeps_column_and_row_associations() -> None:
    root = page("developers/config")
    table = next(root.iter("table"))
    thead = table.find("thead")
    assert thead is not None
    columns = list(thead.iter("th"))
    assert [text(n) for n in columns] == ["Field", "What it means"]
    assert all(n.get("scope") == "col" for n in columns)
    body = table.find("tbody")
    assert body is not None
    rows = list(body.iter("tr"))
    expected = ["version", "consent", "person.name", "person.addresses",
                "person (optional fields)", "permissions", "email_mode", "schedule"]
    assert len(rows) == len(expected)
    for row, field in zip(rows, expected, strict=True):
        headings = list(row.iter("th"))
        cells = list(row.iter("td"))
        assert len(headings) == len(cells) == 1
        assert headings[0].get("scope") == "row" and text(headings[0]) == field
        assert text(cells[0])
    for anchor in ("overview", "person", "mailbox", "example"):
        assert by_id(root, anchor) is not None
    assert any(h.endswith("/schema/setup-config.schema.json") for h in links(root))
    examples = list(root.iter("pre"))
    assert len(examples) == 2
    assert all(n.get("tabindex") == "0" and n.get("aria-label") for n in examples)
    assert "Fake example only" in text(examples[1])


import pytest
from playwright.sync_api import Browser, expect

from tests.test_web_home_hero_layout import BASE, ORIGIN, serve
from tests.test_web_home_hero_layout import browser as browser  # noqa: PLC0414


@pytest.mark.parametrize("route", ['developers/config/'])
@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize(("width", "scale"), [(320, 1), (360, 1), (768, 1), (1280, 1),
                                              (1024, 1.25), (1280, 1.5), (640, 2)])
def test_offline_refresh_reflows_and_has_keyboard_targets(
    browser: Browser, route: str, theme: str, width: int, scale: float,
) -> None:
    """Emulate scaling/reflow; this does not operate Windows or browser zoom UI."""
    context = browser.new_context(viewport={"width": width, "height": 900},
                                  device_scale_factor=scale, color_scheme=theme,
                                  java_script_enabled=False, reduced_motion="reduce")
    context.route("**/*", serve)
    try:
        tab = context.new_page()
        response = tab.goto(ORIGIN + BASE + route, wait_until="load")
        assert response is not None and response.status == 200
        assert tab.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        scope = tab.locator(".site-refresh")
        assert scope.count() == 1
        summaries = scope.locator("summary")
        if summaries.count():
            summary = summaries.first
            for _ in range(100):
                tab.keyboard.press("Tab")
                if summary.evaluate("el => el === document.activeElement"):
                    break
            expect(summary).to_be_focused()
            tab.keyboard.press("Enter")
            expect(scope.locator("details").first).to_have_attribute("open", "")
            tab.keyboard.press("Space")
            expect(scope.locator("details").first).not_to_have_attribute("open", "")
        for summary in summaries.all():
            summary.focus()
            tab.keyboard.press("Enter")
        for target in scope.locator("a, summary").all():
            if target.is_visible():
                box = target.bounding_box()
                assert box is not None and box["height"] >= 43.9 and box["width"] >= 43.9
        body_sizes = scope.locator("p, li, td, summary").evaluate_all(
            "els => els.filter(e => e.getClientRects().length).map(e => parseFloat(getComputedStyle(e).fontSize))"
        )
        assert body_sizes and min(body_sizes) >= 20
        contrast_failures = scope.evaluate(r"""root => {
            const rgb = s => (s.match(/[\d.]+/g) || []).map(Number);
            const lum = c => c.slice(0, 3).map(v => {
                v /= 255; return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4;
            }).reduce((v, n, i) => v + n * [.2126, .7152, .0722][i], 0);
            const failures = [];
            for (const el of root.querySelectorAll('*')) {
                if (!el.getClientRects().length || ![...el.childNodes].some(
                    n => n.nodeType === 3 && n.textContent.trim())) continue;
                const fg = rgb(getComputedStyle(el).color);
                let parent = el, bg;
                while (parent) {
                    const c = rgb(getComputedStyle(parent).backgroundColor);
                    if (c.length === 3 || c[3] === 1) { bg = c; break; }
                    parent = parent.parentElement;
                }
                if (!bg || fg.length < 3) continue;
                const ratio = (Math.max(lum(fg), lum(bg)) + .05) / (Math.min(lum(fg), lum(bg)) + .05);
                const limit = el.closest('h1,h2,h3,h4,a,summary') ? 4.5 : 7;
                if (ratio + .01 < limit) failures.push([el.textContent.slice(0, 60), ratio, limit]);
            }
            return failures;
        }""")
        assert not contrast_failures, contrast_failures
        first = scope.locator("a").first
        first.focus()
        expect(first).to_be_focused()
        tab.keyboard.press("Tab")
        assert tab.evaluate("document.activeElement !== document.body")
    finally:
        context.close()
