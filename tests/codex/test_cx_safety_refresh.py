"""Protect the rebuilt safety page's sections, anchors, and navigation."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "web" / "dist" / "safety" / "index.html"


class SafetyPageParser(HTMLParser):
    """Collect text, heading IDs, section IDs, and links from built HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self.ids: list[str] = []
        self.links: list[str] = []
        self.headings: list[str] = []
        self._heading: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        element_id = attributes.get("id")
        if element_id:
            self.ids.append(element_id)
        href = attributes.get("href")
        if href:
            self.links.append(href)
        if tag in {"h1", "h2", "h3"}:
            self._heading = []

    def handle_data(self, data: str) -> None:
        clean = " ".join(data.split())
        if clean:
            self.text.append(clean)
            if self._heading is not None:
                self._heading.append(clean)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h1", "h2", "h3"} and self._heading is not None:
            self.headings.append(" ".join(self._heading))
            self._heading = None


def _page() -> tuple[str, SafetyPageParser]:
    assert PAGE.is_file(), "Build web/dist with pnpm build before running this suite"
    html = PAGE.read_text(encoding="utf-8")
    parser = SafetyPageParser()
    parser.feed(html)
    return html, parser


def test_built_safety_page_keeps_scoped_refresh_and_anchor_order() -> None:
    html, parsed = _page()
    assert 'class="site-refresh"' in html
    assert parsed.headings[0] == "Is Free My ID safe?"
    anchors = [
        "local",
        "never-asks",
        "never-does",
        "open-source",
        "verify",
        "uninstall",
        "limits",
        "this-website",
    ]
    positions = [parsed.ids.index(anchor) for anchor in anchors]
    assert positions == sorted(positions)
    assert "You can check the work" in parsed.headings
    assert "Stop or uninstall any time" in parsed.headings


def test_built_safety_page_keeps_approved_explanations_and_links() -> None:
    _, parsed = _page()
    text = " ".join(parsed.text)
    assert "Your details are stored on your computer. Nothing is sent to us." in text
    assert "Your details are stored encrypted on your computer" in text
    assert "the key is kept in Windows' own secure password store" in text
    assert "What it never asks for" in parsed.headings
    assert "What it never does" in parsed.headings
    assert "Check that your download is genuine" in parsed.headings
    assert "our download page" in text
    assert "/developers/" in parsed.links
    assert "/download/" in parsed.links
    assert "/download/#checksum" in parsed.links
    assert "/download/#smartscreen" in parsed.links
