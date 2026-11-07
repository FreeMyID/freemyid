"""FAQ guards against built Astro HTML; run after the website build."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Element:
    tag: str
    attrs: dict[str, str | None]
    children: list[Element | str] = field(default_factory=list)

    def elements(self, tag: str) -> list[Element]:
        found: list[Element] = []
        for child in self.children:
            if isinstance(child, Element):
                if child.tag == tag:
                    found.append(child)
                found.extend(child.elements(tag))
        return found

    def text(self) -> str:
        return "".join(c if isinstance(c, str) else c.text() for c in self.children)


class Document(HTMLParser):
    def __init__(self, html: str) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("document", {})
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Element(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input",
                       "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


@pytest.mark.parametrize(("page", "home", "open_first"), [
    ("index.html", True, 2),
    ("faq/index.html", False, 0),
])
def test_built_faq_native_controls(page: str, home: bool, open_first: int) -> None:
    path = ROOT / "web" / "dist" / page
    assert path.is_file(), "Build web/dist first; see web/package.json and VENDOR_STATUS.md"
    document = Document(path.read_text(encoding="utf-8")).root
    items = yaml.safe_load((ROOT / "site_src/data/faq.yaml").read_text(encoding="utf-8"))
    expected = [item for item in items if not home or item.get("home")]
    disclosures = [node for node in document.elements("details")
                   if "faq-item" in (node.attrs.get("class") or "").split()]
    assert len(disclosures) == len(expected) > 0
    assert len({node.attrs.get("id") for node in disclosures}) == len(disclosures)
    for index, (node, item) in enumerate(zip(disclosures, expected, strict=True)):
        assert node.attrs["id"] == f"q-{item['id']}"
        assert ("open" in node.attrs) == (index < open_first)
        children = [child for child in node.children if isinstance(child, Element)]
        assert children[0].tag == "summary"
        assert len(node.elements("summary")) == 1
        summary = children[0]
        assert " ".join(summary.text().split()) == " ".join(item["q"].split())
        for control in (node, summary):
            for attr in ("role", "tabindex", "aria-expanded", "aria-label", "aria-hidden"):
                assert attr not in control.attrs
        for tag in ("a", "button", "input", "select", "textarea"):
            assert not summary.elements(tag)
        icons = summary.elements("svg")
        assert len(icons) == 1
        assert icons[0].attrs.get("aria-hidden") == "true"
        assert icons[0].attrs.get("focusable") == "false"
        assert len(children) == 2 and children[1].tag == "div"
        assert children[1].text().strip(), "Answer must remain readable HTML"
        if "<a " in item["a"]:
            links = children[1].elements("a")
            assert links and all(link.text().strip() and link.attrs.get("href") for link in links)


def luminance(color: str) -> float:
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
              for c in channels]
    return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))


@pytest.mark.parametrize("theme", [0, 1], ids=["light", "dark"])
@pytest.mark.parametrize(("foreground", "background", "minimum"), [
    ("heading", "card", 4.5),
    ("heading", "brand-soft", 4.5),
    ("text", "card", 4.5),
    ("link", "card", 4.5),
])
def test_faq_token_contrast(theme: int, foreground: str, background: str, minimum: float) -> None:
    """Question, answer and link ink against card and hover fills."""
    css = (ROOT / "web/src/styles/tokens.css").read_text(encoding="utf-8")
    pairs = {name: (light, dark) for name, light, dark in re.findall(
        r"--fmi-color-([\w-]+): light-dark\((#[\da-f]{6}), (#[\da-f]{6})\)", css,
    )}
    values = sorted((luminance(pairs[foreground][theme]), luminance(pairs[background][theme])))
    assert (values[1] + 0.05) / (values[0] + 0.05) >= minimum
