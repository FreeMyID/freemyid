"""WO-206: the refreshed download page preserves release and help routes."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


class DownloadPage(HTMLParser):
    """Collect the download page's visible copy, links, IDs, and classes."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_main = False
        self.main_text: list[str] = []
        self.ids: set[str] = set()
        self.classes: set[str] = set()
        self.link_href: str | None = None
        self.link_text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "main" and values.get("id") == "main":
            self.in_main = True
        if not self.in_main:
            return
        if values.get("id"):
            self.ids.add(values["id"] or "")
        self.classes.update((values.get("class") or "").split())
        if tag == "a":
            self.link_href = values.get("href") or ""
            self.link_text = []

    def handle_data(self, data: str) -> None:
        if not self.in_main:
            return
        self.main_text.append(data)
        if self.link_href is not None:
            self.link_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.in_main and self.link_href is not None:
            label = " ".join(" ".join(self.link_text).split())
            self.links.append((self.link_href, label))
            self.link_href = None
        if tag == "main":
            self.in_main = False

    @property
    def text(self) -> str:
        return " ".join(" ".join(self.main_text).split())


@pytest.fixture(scope="module")
def page() -> DownloadPage:
    path = ROOT / "web/dist/download/index.html"
    assert path.is_file(), "Build web/dist with pnpm build before the WO-206 test"
    parser = DownloadPage()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


@pytest.fixture(scope="module")
def release() -> dict[str, Any]:
    return yaml.safe_load((ROOT / "site_src/data/release.yaml").read_text(encoding="utf-8")) or {}


@pytest.fixture(scope="module")
def site() -> dict[str, Any]:
    return yaml.safe_load((ROOT / "site_src/site.yaml").read_text(encoding="utf-8")) or {}


@pytest.mark.web_dist
def test_primary_download_action_preserves_d5_release_state(
    page: DownloadPage, release: dict[str, Any], site: dict[str, Any],
) -> None:
    primary = [(href, label) for href, label in page.links if label == "Download FreeMyIDSetup.exe"]

    if release.get("version"):
        assert primary == [(site["download_url"], "Download FreeMyIDSetup.exe")]
        assert "Download opens soon" not in page.text
    else:
        assert primary == []
        assert "Download opens soon" in page.text
        assert site["download_url"] not in {href for href, _ in page.links}

    assert "site-refresh__button" in page.classes


@pytest.mark.web_dist
def test_download_help_sections_and_internal_destinations_remain_available(
    page: DownloadPage, release: dict[str, Any],
) -> None:
    assert {"smartscreen", "checksum", "remove"} <= page.ids
    assert ("release-notes" in page.ids) is bool(release.get("version"))
    assert "For helpers: check the download is genuine" in page.text
    assert "Unknown publisher" in page.text
    assert "Open the file you downloaded" in page.text
    assert "Click the small words “More info”" in page.text
    assert "Check the name, then click “Run anyway”" in page.text
    assert "Click Install" in page.text

    destinations = {href for href, _ in page.links}
    assert any(href.rstrip("/").endswith("/families") for href in destinations)
    assert any(href.rstrip("/").endswith("/developers") for href in destinations)

