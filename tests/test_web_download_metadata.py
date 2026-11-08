"""WO-109: built download metadata follows checked-in published-release data."""

from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class DownloadMetadata(HTMLParser):
    """Read visible main metadata, primary links and the checksum disclosure."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_main = False
        self.in_checksum = False
        self.in_fingerprint = False
        self.field = ""
        self.parts: list[str] = []
        self.term = ""
        self.current_metadata: dict[str, str] | None = None
        self.metadata: list[dict[str, str]] = []
        self.link_href: str | None = None
        self.link_parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.ids: list[str] = []
        self.fingerprints: list[str] = []
        self.fingerprint_parts: list[str] = []
        self.copy_values: list[str] = []
        self.checksum_parts: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "main":
            self.in_main = True
        if not self.in_main:
            return
        if values.get("id"):
            self.ids.append(values["id"] or "")
        if tag == "dl":
            self.current_metadata = {}
            self.metadata.append(self.current_metadata)
        if tag in {"dt", "dd"} and self.current_metadata is not None:
            self.field = tag
            self.parts = []
        if tag == "a":
            self.link_href = values.get("href") or ""
            self.link_parts = []
        if tag == "details" and values.get("id") == "checksum":
            self.in_checksum = True
        if self.in_checksum:
            if tag == "code" and "block" in (values.get("class") or "").split():
                self.in_fingerprint = True
                self.fingerprint_parts = []
            if "data-copy-hash" in values:
                self.copy_values.append(values["data-copy-hash"] or "")

    def handle_data(self, data: str) -> None:
        if not self.in_main:
            return
        self.text_parts.append(data)
        if self.field:
            self.parts.append(data)
        if self.link_href is not None:
            self.link_parts.append(data)
        if self.in_checksum:
            self.checksum_parts.append(data)
        if self.in_fingerprint:
            self.fingerprint_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == self.field:
            value = " ".join(" ".join(self.parts).split())
            if tag == "dt":
                self.term = value
            elif self.current_metadata is not None:
                self.current_metadata[self.term] = value
            self.field = ""
        if tag == "dl":
            self.current_metadata = None
        if tag == "a" and self.link_href is not None:
            self.links.append((self.link_href, " ".join(" ".join(self.link_parts).split())))
            self.link_href = None
        if tag == "code" and self.in_fingerprint:
            self.fingerprints.append("".join(self.fingerprint_parts).strip())
            self.in_fingerprint = False
        if tag == "details":
            self.in_checksum = False
        if tag == "main":
            self.in_main = False


@pytest.fixture(scope="module")
def page() -> DownloadMetadata:
    path = ROOT / "web/dist/download/index.html"
    assert path.is_file(), "Build web/dist with pnpm build before WO-109 tests"
    parser = DownloadMetadata()
    parser.feed(path.read_text(encoding="utf-8"))
    assert parser.metadata, "Expected the download's visible metadata list"
    return parser


@pytest.fixture(scope="module")
def release() -> dict[str, Any]:
    # Use published site metadata only; never infer availability from a git tag.
    return yaml.safe_load((ROOT / "site_src/data/release.yaml").read_text(encoding="utf-8")) or {}


def test_version_and_publication_date_match_release_data(
    page: DownloadMetadata, release: dict[str, Any],
) -> None:
    version = release.get("version")
    if not version:
        assert all("Version" not in block for block in page.metadata)
        assert "Download opens soon" in " ".join(page.text_parts)
        return
    date = str(release.get("date") or "")
    assert page.metadata[0]["Version"] == str(version) + (f" ({date})" if date else "")
    assert page.metadata[1]["Version"] == str(version) + (
        " (an early release)" if str(version).startswith("0.") else ""
    )
    if date:
        assert page.metadata[1]["Published"] == date
    assert "release-notes" in page.ids


def test_visible_sizes_match_published_installer_metadata(
    page: DownloadMetadata, release: dict[str, Any],
) -> None:
    size = release.get("size_mb")
    sizes = [block["Size"] for block in page.metadata if "Size" in block]
    if not size:
        assert sizes == []
        return
    expected = f"{float(size):g} MB"
    assert sizes == [expected] * (2 if release.get("version") else 1)


def test_fingerprint_display_copy_value_and_fragment_agree(
    page: DownloadMetadata, release: dict[str, Any],
) -> None:
    assert page.ids.count("checksum") == 1
    fingerprint = release.get("sha256")
    if not fingerprint:
        assert page.fingerprints == []
        assert page.copy_values == []
        assert all("Fingerprint" not in block for block in page.metadata)
        return
    assert page.fingerprints == [fingerprint]
    assert page.copy_values == [fingerprint]
    assert f"For version {release.get('version')}, the code is:" in " ".join(page.checksum_parts)
    if release.get("version"):
        assert ("#checksum", 'SHA256 code, under "For helpers" above') in page.links
        assert page.metadata[1]["Fingerprint"] == 'SHA256 code, under "For helpers" above'


def test_primary_download_link_is_gated_by_release_metadata(
    page: DownloadMetadata, release: dict[str, Any],
) -> None:
    site = yaml.safe_load((ROOT / "site_src/site.yaml").read_text(encoding="utf-8"))
    primary = [href for href, text in page.links if text == "Download FreeMyIDSetup.exe"]
    assert primary == ([site["download_url"]] if release.get("version") else [])
