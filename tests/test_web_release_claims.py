"""WO-123: site-wide release claims in the built site follow site_src/data/release.yaml.

Needs a fresh build: ``cd web && pnpm build``. Offline. The unreleased branch is exercised on small
synthetic pages so no checked-in data is edited.
"""

import re
from html import unescape
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "web/dist"

VERSION_MENTION = re.compile(r"(?:\b[Vv]ersion\s+|\bv)(\d+\.\d+\.\d+)\b")
TAG_HREF = re.compile(r"""href=["'][^"']*/releases/tag/v?(\d+\.\d+\.\d+)[^"']*["']""")
EXE_HREF = re.compile(r"""href=["'][^"']*\.exe(?:[?#][^"']*)?["']""", re.IGNORECASE)
# History pages legitimately name older versions.
HISTORY_PAGES = ("release-notes", "changelog")


def visible_text(html: str) -> str:
    body = re.sub(r"<(script|style|title)\b.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", body)).split())


def release_problems(pages: dict[str, str], version: str | None) -> list[str]:
    problems: list[str] = []
    for name, html in sorted(pages.items()):
        text = visible_text(html)
        history = any(part in name for part in HISTORY_PAGES)
        if version:
            if history:
                continue
            for found in VERSION_MENTION.findall(text) + TAG_HREF.findall(html):
                # Date-shaped versions (2026.11.06) are broker data versions, not app versions.
                if int(found.split(".")[0]) >= 2000:
                    continue
                if found != version:
                    problems.append(f"{name}: shows version {found}, release.yaml says {version}")
        else:
            if "Available now" in text:
                problems.append(f"{name}: shows 'Available now' with no published version")
            if "Download FreeMyIDSetup" in text or EXE_HREF.search(html):  # one finding per page
                problems.append(f"{name}: offers a download with no published version")
    return problems


def built_pages() -> dict[str, str]:
    assert DIST.is_dir(), "Build web/dist with pnpm --dir web build before WO-123 tests"
    pages = {
        path.relative_to(DIST).as_posix(): path.read_text(encoding="utf-8")
        for path in DIST.rglob("*.html")
    }
    assert pages, "web/dist has no HTML pages"
    return pages


@pytest.fixture(scope="module")
def release() -> dict[str, Any]:
    return yaml.safe_load((ROOT / "site_src/data/release.yaml").read_text(encoding="utf-8")) or {}


def test_built_pages_state_only_the_published_version(release: dict[str, Any]) -> None:
    version = str(release["version"]) if release.get("version") else None
    assert release_problems(built_pages(), version) == []


def test_built_pages_with_available_now_badge_exist_only_with_published_version(
    release: dict[str, Any],
) -> None:
    badged = [
        name for name, html in built_pages().items() if "Available now" in visible_text(html)
    ]
    if not release.get("version"):
        assert badged == []
    else:
        # Guards the scan itself: it must see the badge somewhere if a release is published.
        assert badged, "Expected at least one page with an 'Available now' badge"


def test_download_page_has_no_older_or_newer_version(release: dict[str, Any]) -> None:
    if not release.get("version"):
        pytest.skip("No published version in release.yaml")
    html = built_pages()["download/index.html"]
    text = visible_text(html)
    assert str(release["version"]) in text
    others = {v for v in VERSION_MENTION.findall(text) if v != str(release["version"])}
    assert others == set()


def test_checker_flags_mismatched_versions() -> None:
    pages = {
        "a/index.html": "<p>Version 0.1.0 is out. Available now.</p>",
        "b/index.html": '<a href="https://example.test/releases/tag/v0.3.0">notes</a>',
        "release-notes/index.html": "<p>Version 0.1.0 was the first.</p>",
        "c/index.html": "<p>Version 0.2.0 is out.</p><script>var v = 'v9.9.9'</script>",
    }
    problems = release_problems(pages, "0.2.0")
    assert len(problems) == 2
    assert problems[0].startswith("a/index.html") and "0.1.0" in problems[0]
    assert problems[1].startswith("b/index.html") and "0.3.0" in problems[1]


def test_checker_flags_download_and_badge_without_published_version() -> None:
    pages = {
        "download/index.html": '<a href="/files/FreeMyIDSetup.exe">Download FreeMyIDSetup.exe</a>',
        "home/index.html": "<span>Available now</span>",
        "soon/index.html": "<p>The download is not available yet. Download opens soon.</p>",
    }
    problems = release_problems(pages, None)
    # One finding per page and problem: the download text and the .exe link are one problem.
    assert [p.split(":")[0] for p in problems] == ["download/index.html", "home/index.html"]


def test_checker_ignores_date_shaped_data_versions() -> None:
    pages = {"guides/index.html": "<p>Checklist version 2026.11.06</p>"}
    assert release_problems(pages, "0.2.0") == []
