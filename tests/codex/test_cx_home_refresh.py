"""Built-output checks for the refreshed home page."""

from __future__ import annotations

import os
from html.parser import HTMLParser
from pathlib import Path
from typing import ClassVar
from urllib.parse import unquote, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "web" / "dist"
INDEX = DIST / "index.html"


class HomeOutput(HTMLParser):
    """Collect only the home-page landmarks this work order promises to retain."""

    _VOID: ClassVar[set[str]] = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, dict[str, str]]] = []
        self.headings: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.hero_images: list[dict[str, str]] = []
        self.captions: list[list[str]] = []
        self._active_headings: list[dict[str, str]] = []
        self._active_links: list[dict[str, str]] = []
        self._active_captions: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        parent_classes = {
            name
            for _, parent_attrs in self.stack
            for name in parent_attrs.get("class", "").split()
        }

        if tag in {"h1", "h2", "h3"}:
            heading = {"tag": tag, "id": values.get("id", ""), "text": ""}
            self.headings.append(heading)
            self._active_headings.append(heading)
        elif tag == "a":
            link = {"href": values.get("href", ""), "text": ""}
            self.links.append(link)
            self._active_links.append(link)
        elif tag == "figcaption":
            caption: list[str] = []
            self.captions.append(caption)
            self._active_captions.append(caption)
        elif tag == "img" and "site-refresh__hero-media" in parent_classes:
            self.hero_images.append(values)

        if tag not in self._VOID:
            self.stack.append((tag, values))

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h1", "h2", "h3"} and self._active_headings:
            self._active_headings.pop()
        elif tag == "a" and self._active_links:
            self._active_links.pop()
        elif tag == "figcaption" and self._active_captions:
            self._active_captions.pop()

        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        for heading in self._active_headings:
            heading["text"] += data
        for link in self._active_links:
            link["text"] += data
        for caption in self._active_captions:
            caption.append(data)


def built_home() -> HomeOutput:
    if not INDEX.is_file():
        if os.environ.get("FREEMYID_REQUIRE_WEB_DIST") == "1":
            pytest.fail("Build web/dist before running the refreshed-home checks")
        pytest.skip("web/dist is not built")
    output = HomeOutput()
    output.feed(INDEX.read_text(encoding="utf-8"))
    return output


def test_built_home_keeps_approved_heading_and_d10_section_order() -> None:
    output = built_home()

    assert [heading["text"].strip() for heading in output.headings if heading["tag"] == "h1"] == [
        "Take your name off the websites that sell it."
    ]
    heading_text = [heading["text"].strip() for heading in output.headings]
    required_order = [
        "Take your name off the websites that sell it.",
        "See what was asked, and what came back.",
        "How it works, in three steps",
        "What people-search sites list about you",
        'You said "I do not consent." Here is how to make it count.',
        "Free My ID, paid removal services, or doing it by hand",
        "Built so you can check our work.",
        "It's free",
        "Helping a parent or grandparent?",
        "Common questions",
        "Your information. Off the market.",
    ]
    positions = [heading_text.index(title) for title in required_order]
    assert positions == sorted(positions)


def test_built_home_download_and_how_it_works_actions_are_visible() -> None:
    output = built_home()

    class ActionLinks(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.parents: list[tuple[str, dict[str, str]]] = []
            self.items: list[dict[str, str]] = []
            self.active: dict[str, str] | None = None

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            values = {key: value or "" for key, value in attrs}
            classes = {word for _, parent in self.parents for word in parent.get("class", "").split()}
            if tag == "a" and "hero-actions" in classes:
                self.active = {"href": values.get("href", ""), "text": ""}
                self.items.append(self.active)
            if tag not in HomeOutput._VOID:
                self.parents.append((tag, values))

        def handle_endtag(self, tag: str) -> None:
            if tag == "a":
                self.active = None
            for index in range(len(self.parents) - 1, -1, -1):
                if self.parents[index][0] == tag:
                    del self.parents[index:]
                    break

        def handle_data(self, data: str) -> None:
            if self.active is not None:
                self.active["text"] += data

    parser = ActionLinks()
    parser.feed(INDEX.read_text(encoding="utf-8"))
    actions = parser.items
    assert len(actions) == 2
    assert "Download" in actions[0]["text"] or "Coming soon" in actions[0]["text"]
    assert actions[0]["href"].startswith(("/", "https://"))
    assert actions[1]["text"].strip() == "See how it works"
    assert actions[1]["href"].endswith("how-it-works/")
    assert output.hero_images  # the real screenshot is present in the hero


def test_built_home_hero_uses_the_labelled_product_screenshot() -> None:
    output = built_home()

    assert len(output.hero_images) == 1
    image = output.hero_images[0]
    assert image.get("alt", "").startswith("The Free My ID desktop app showing its Welcome screen")
    assert image.get("width") == "768"
    assert image.get("height") == "576"
    src = image.get("src", "")
    assert "home-hero-v0.2.0" in src
    asset_path = DIST / unquote(urlsplit(src).path.lstrip("/"))
    assert asset_path.is_file(), f"Built hero image is missing: {src}"
    assert "Example with made-up data" in "".join("".join(caption) for caption in output.captions)
