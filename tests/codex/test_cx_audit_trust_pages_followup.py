"""Keep the safety and families heroes inside the shared phone gutter."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from typing import ClassVar

ROOT = Path(__file__).resolve().parents[2]
PAGES = {
    "safety": ROOT / "web" / "dist" / "safety" / "index.html",
    "families": ROOT / "web" / "dist" / "families" / "index.html",
}


class HeroGutterParser(HTMLParser):
    """Collect whether each hero has its own wrap ancestor."""

    _VOID: ClassVar[set[str]] = {
        "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta"
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, dict[str, str]]] = []
        self.heroes: list[dict[str, bool]] = []
        self.current_hero: dict[str, bool] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        classes = set(values.get("class", "").split())
        ancestors = [parent_attrs for _, parent_attrs in self.stack]
        if tag == "section" and "site-refresh__hero" in classes:
            wrapped = any("site-refresh__wrap" in parent.get("class", "").split() for parent in ancestors)
            self.current_hero = {"wrapped": wrapped, "heading": False, "media": False}
            self.heroes.append(self.current_hero)
        elif self.current_hero is not None and tag == "h1":
            self.current_hero["heading"] = True
        elif self.current_hero is not None and "site-refresh__hero-media" in classes:
            self.current_hero["media"] = True

        if tag not in self._VOID:
            self.stack.append((tag, values))

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break
        if tag == "section" and self.current_hero is not None:
            self.current_hero = None


def test_safety_and_families_hero_heading_and_art_have_phone_gutters() -> None:
    for route, page in PAGES.items():
        assert page.is_file(), f"Build web/dist before checking /{route}/ hero gutters"
        parser = HeroGutterParser()
        parser.feed(page.read_text(encoding="utf-8"))

        assert len(parser.heroes) == 1, route
        hero = parser.heroes[0]
        assert hero["wrapped"], f"/{route}/ hero needs the shared site-refresh__wrap gutter"
        assert hero["heading"], route
        assert hero["media"], route
