"""WO-102: source and built Safety illustration regression checks."""

from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
SVG = "{http://www.w3.org/2000/svg}"
TITLE = "Your details are stored on your computer, not in the cloud"
OLD_TITLE = "Your details stay on your computer"
SOURCES = (
    "web/src/art/sections/safety-local.svg",
    "brand/v3/sections/safety-local.svg",
)


class SafetyIllustration(HTMLParser):
    """Identify the hero art independently of its accessible wording."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_main = False
        self.art: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "main":
            self.in_main = True
        if tag == "svg" and self.in_main and "fmi-art" in (values.get("class") or "").split():
            self.art.append(values)

    def handle_endtag(self, tag: str) -> None:
        if tag == "main":
            self.in_main = False


@pytest.mark.parametrize("source", SOURCES)
def test_safety_art_is_self_contained_and_has_no_tiny_text(source: str) -> None:
    content = (ROOT / source).read_text(encoding="utf-8")
    root = ET.fromstring(content)
    assert root.tag == SVG + "svg"
    assert root.attrib["viewBox"] == "0 0 320 240"
    assert root.attrib["aria-labelledby"] == "t"
    title = root.find(SVG + "title")
    assert title is not None
    assert title.attrib["id"] == "t"
    assert title.text == TITLE
    assert OLD_TITLE not in content
    assert not list(root.iter(SVG + "text"))
    assert not list(root.iter(SVG + "script"))
    assert "@media(prefers-color-scheme:dark)" in content
    assert "var(--fmi-" in content
    for node in root.iter():
        for name, value in node.attrib.items():
            if name.rsplit("}", 1)[-1] in {"href", "src"}:
                assert value.startswith("#"), "No external resources in the SVG"
    assert "url(" not in content
    assert len(content.encode("utf-8")) < 3400


def test_source_master_and_web_copy_match() -> None:
    assert (ROOT / SOURCES[0]).read_bytes() == (ROOT / SOURCES[1]).read_bytes()


def test_built_safety_page_uses_storage_specific_label() -> None:
    path = ROOT / "web/dist/safety/index.html"
    assert path.is_file(), "Build web/dist before running this test"
    html = path.read_text(encoding="utf-8")
    assert OLD_TITLE not in html
    parser = SafetyIllustration()
    parser.feed(html)
    assert len(parser.art) == 1, "Expected the Safety hero illustration in main"
    hero = parser.art[0]
    assert hero.get("role") == "img"
    assert (hero.get("aria-label") or "").strip().removesuffix(".") == TITLE
