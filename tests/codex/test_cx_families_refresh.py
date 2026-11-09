"""Protect the refreshed families page's structure, guidance, and key links."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "web" / "dist" / "families" / "index.html"


class FamiliesPageParser(HTMLParser):
    """Collect built page text, headings, links, image alternatives, and step text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self.headings: list[str] = []
        self.links: list[str] = []
        self.classes: set[str] = set()
        self.images: list[dict[str, str | None]] = []
        self.steps: list[str] = []
        self._heading: list[str] | None = None
        self._step: list[str] | None = None
        self._step_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        self.classes.update((attributes.get("class") or "").split())

        if tag in {"h1", "h2", "h3", "h4"}:
            self._heading = []
        elif tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"] or "")
        elif tag == "img":
            self.images.append(
                {
                    "alt": attributes.get("alt"),
                    "width": attributes.get("width"),
                    "height": attributes.get("height"),
                }
            )

        if tag == "li" and "site-refresh__step" in (attributes.get("class") or "").split():
            self._step = []
            self._step_depth = 1
        elif tag == "li" and self._step is not None:
            self._step_depth += 1

    def handle_data(self, data: str) -> None:
        clean = " ".join(data.split())
        if not clean:
            return
        self.text.append(clean)
        if self._heading is not None:
            self._heading.append(clean)
        if self._step is not None:
            self._step.append(clean)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h1", "h2", "h3", "h4"} and self._heading is not None:
            self.headings.append(" ".join(self._heading))
            self._heading = None
        if tag == "li" and self._step is not None:
            self._step_depth -= 1
            if self._step_depth == 0:
                self.steps.append(" ".join(self._step))
                self._step = None


def _page() -> tuple[str, FamiliesPageParser]:
    assert PAGE.is_file(), "Build web/dist with pnpm build before running this suite"
    html = PAGE.read_text(encoding="utf-8")
    parser = FamiliesPageParser()
    parser.feed(html)
    return html, parser


def test_built_families_page_has_scoped_refresh_and_readable_heading_order() -> None:
    html, parsed = _page()
    assert "site-refresh" in parsed.classes
    assert parsed.headings[0] == "Helping a parent or grandparent use Free My ID"

    ordered = [
        "What you're setting up, in one sentence",
        "What it doesn't do",
        "Before you sit down",
        "A separate email address for replies (optional)",
        "Setting it up",
        "What they'll see afterward",
        "Tell them this",
        "Printable card for the fridge",
        "Pausing, stopping, uninstalling",
        "Questions helpers ask",
    ]
    positions = [parsed.headings.index(heading) for heading in ordered]
    assert positions == sorted(positions)

    assert '<ol class="site-refresh__steps"' in html
    expected_steps = [
        "Download",
        "Open FreeMyIDSetup.exe",
        "Click Install",
        "Go through the six setup screens",
        "Start in practice mode",
    ]
    assert len(parsed.steps) == len(expected_steps)
    assert all(
        step.startswith(f"{number} {title}")
        for number, (step, title) in enumerate(zip(parsed.steps, expected_steps, strict=True), start=1)
    )


def test_built_families_page_keeps_key_copy_and_routes() -> None:
    _, parsed = _page()
    text = " ".join(parsed.text)
    assert "Each adult gives their own permission." in text
    assert "Go through the six setup screens" in text
    assert "When you're ready, go to Settings and turn on real requests." in text
    assert "See the full list" in text
    assert "Doing it by hand together?" in text

    for href in (
        "/download/#smartscreen",
        "/safety/#never-asks",
        "/faq/",
        "/guides/",
        "/guides/help-a-parent-remove-their-information/",
    ):
        assert href in parsed.links

    assert parsed.images == [
        {
            "alt": "Two people work together through a simple checklist",
            "width": "320",
            "height": "240",
        }
    ]
