"""Guard the built developer landing-page hero art contract."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "web/dist"
PAGE = DIST / "developers/index.html"
EXPECTED_ALT = (
    "A terminal on your own computer connected to a small home server, inside a house "
    "outline, with a clock for the schedule."
)


class _HeroPictureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_picture = False
        self.dark_sources: list[dict[str, str | None]] = []
        self.light_images: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "picture":
            self.in_picture = True
        elif self.in_picture and tag == "source":
            if values.get("media") == "(prefers-color-scheme: dark)":
                self.dark_sources.append(values)
        elif self.in_picture and tag == "img":
            src = values.get("src") or ""
            if Path(urlsplit(src).path).name == "developers-light.svg":
                self.light_images.append(values)

    def handle_endtag(self, tag: str) -> None:
        if tag == "picture":
            self.in_picture = False


@pytest.mark.web_dist
def test_developer_hero_art_builds_light_and_dark_variants() -> None:
    parser = _HeroPictureParser()
    parser.feed(PAGE.read_text(encoding="utf-8"))

    assert len(parser.dark_sources) == 1
    dark_source = parser.dark_sources[0]
    assert Path(urlsplit(dark_source.get("srcset") or "").path).name == "developers-dark.svg"

    assert len(parser.light_images) == 1
    light_image = parser.light_images[0]
    assert light_image.get("width") == "640"
    assert light_image.get("height") == "480"
    alt = (light_image.get("alt") or "").strip()
    assert alt
    assert alt == EXPECTED_ALT

    assert (DIST / "assets/art/developers-light.svg").is_file()
    assert (DIST / "assets/art/developers-dark.svg").is_file()
