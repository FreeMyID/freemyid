"""Checks for the Astro roadmap. Build web/ before running these tests."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import pytest

DIST = Path(__file__).resolve().parents[1] / "web" / "dist"


class RoadmapParser(HTMLParser):
    """Collect visible text and links from the v0.3 section only."""

    def __init__(self) -> None:
        super().__init__()
        self.active = False
        self.text: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.href: str | None = None
        self.label: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "section" and attributes.get("id") == "then":
            self.active = True
        if self.active and tag == "a":
            self.href = attributes.get("href")
            self.label = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "section":
            self.active = False
        if tag == "a" and self.href is not None:
            self.links.append((self.href, " ".join(self.label)))
            self.href = None

    def handle_data(self, data: str) -> None:
        if self.active:
            self.text.append(data)
            if self.href is not None:
                self.label.append(data)


@pytest.fixture
def roadmap() -> RoadmapParser:
    page = DIST / "whats-coming" / "index.html"
    assert page.is_file(), "Build the Astro site with pnpm --dir web build first"
    parser = RoadmapParser()
    parser.feed(page.read_text(encoding="utf-8"))
    return parser


def test_v03_is_planned_with_ordered_journey(roadmap: RoadmapParser) -> None:
    text = " ".join(" ".join(roadmap.text).split())
    assert "Planned for version 0.3" in text
    steps = [
        "1. Find possible listings",
        "2. Review uncertain matches",
        "3. Choose what to request",
        "4. Check the results",
    ]
    positions = [text.index(step) for step in steps]
    assert positions == sorted(positions)
    assert "possible match may belong to someone else" in text
    assert "possible matches separate from confirmed matches" in text
    assert "not that it has been removed" in text
    assert "Sending a request will not mean removal is confirmed" in text
    assert "requests and confirmed results separately" in text
    assert "which need checking by hand" in text
    assert "which results are uncertain" in text
    assert "low score will not mean your details are gone everywhere" in text
    assert "planned printable summary" in text
    assert "PDF" not in text
    assert "proof vault" not in text.lower()


def test_available_website_guides_link_to_built_page(roadmap: RoadmapParser) -> None:
    text = " ".join(" ".join(roadmap.text).split())
    assert "checklists are planned inside the app" in text
    assert "website already has step-by-step protection guides" in text
    links = [(href, label) for href, label in roadmap.links if "protection guides" in label]
    assert len(links) == 1
    href, label = links[0]
    assert "website" in label and "available now" in label
    target = urlsplit(href)
    assert not target.scheme and not target.netloc
    assert target.path.endswith("/protect/")
    assert (DIST / target.path.lstrip("/") / "index.html").is_file()
