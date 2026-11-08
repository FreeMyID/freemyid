"""Every docs/user/*.md page is reachable (WO-159 / GP-13). Offline; reads files only.

A page counts as reachable when INSTALL.md or GLOSSARY.md links to it directly, or links to a page
that links to it (one hop).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
USER_DOCS = ROOT / "docs" / "user"
ENTRY_POINTS = {"INSTALL.md", "GLOSSARY.md"}

_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def _links(page: Path) -> set[str]:
    """Names of docs/user pages that `page` links to (anchors and queries dropped)."""
    found: set[str] = set()
    for target in _LINK.findall(page.read_text(encoding="utf-8")):
        if re.match(r"[a-z][a-z0-9+.-]*:", target, re.IGNORECASE):
            continue
        path = target.split("#", 1)[0].split("?", 1)[0]
        if not path:
            continue
        resolved = (page.parent / path).resolve()
        if resolved.parent == USER_DOCS.resolve():
            found.add(resolved.name)
    return found


def _reachable() -> set[str]:
    direct: set[str] = set()
    for name in ENTRY_POINTS:
        direct |= _links(USER_DOCS / name)
    hop = set(direct)
    for name in direct:
        page = USER_DOCS / name
        if page.is_file():
            hop |= _links(page)
    return hop | ENTRY_POINTS


def _pages() -> list[str]:
    return sorted(p.name for p in USER_DOCS.glob("*.md"))


def test_entry_points_exist() -> None:
    for name in ENTRY_POINTS:
        assert (USER_DOCS / name).is_file(), name


def test_links_resolve_to_real_pages() -> None:
    for name in ENTRY_POINTS:
        for target in _links(USER_DOCS / name):
            assert (USER_DOCS / target).is_file(), f"{name} links to missing {target}"


@pytest.mark.parametrize("page", _pages())
def test_user_page_is_reachable(page: str) -> None:
    assert page in _reachable(), f"docs/user/{page} is not linked from INSTALL.md or GLOSSARY.md (one hop)"
