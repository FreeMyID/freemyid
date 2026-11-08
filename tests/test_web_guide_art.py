"""Spot illustrations on the two topic guides: light/dark <picture>, README alt text, self-hosted, no script."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "web/dist"

CASES = [
    ("guides/help-a-parent-remove-their-information/index.html", "help-a-parent",
     "A grown child and a parent checking a laptop together."),
    ("guides/get-your-phone-number-off-people-search-sites/index.html", "phone-number",
     "A phone with its number hidden and a green check."),
]


@pytest.mark.parametrize(("page", "name", "alt"), CASES)
def test_guide_art(page: str, name: str, alt: str) -> None:
    html = (DIST / page).read_text(encoding="utf-8")
    assert f'/assets/art/{name}-dark.svg" media="(prefers-color-scheme: dark)"' in html
    assert f'/assets/art/{name}-light.svg"' in html
    assert f'alt="{alt}"' in html
    assert 'width="320" height="250"' in html
    for theme in ("light", "dark"):
        built = DIST / f"assets/art/{name}-{theme}.svg"
        assert built.read_bytes() == (ROOT / f"brand/illustrations/{name}-{theme}.svg").read_bytes()
        assert b"<script" not in built.read_bytes()
