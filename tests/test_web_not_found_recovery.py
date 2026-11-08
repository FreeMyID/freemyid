"""WO-105: built v3 missing-page recovery under the configured base path."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "web/dist"


class RecoveryPage(HTMLParser):
    """Collect only headings and links inside the page's main landmark."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_main = False
        self.in_h1 = False
        self.heading_parts: list[str] = []
        self.headings: list[str] = []
        self.link_parts: list[str] | None = None
        self.link_href = ""
        self.links: list[tuple[str, str]] = []
        self.robots: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "meta" and (values.get("name") or "").lower() == "robots":
            self.robots.append(values.get("content") or "")
        if tag == "main":
            self.in_main = True
        if not self.in_main:
            return
        if tag == "h1":
            self.in_h1 = True
            self.heading_parts = []
        if tag == "a":
            self.link_parts = []
            self.link_href = values.get("href") or ""

    def handle_data(self, data: str) -> None:
        if self.in_h1:
            self.heading_parts.append(data)
        if self.link_parts is not None:
            self.link_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1" and self.in_h1:
            self.headings.append(" ".join(" ".join(self.heading_parts).split()))
            self.in_h1 = False
        if tag == "a" and self.link_parts is not None:
            self.links.append((self.link_href, " ".join(" ".join(self.link_parts).split())))
            self.link_parts = None
        if tag == "main":
            self.in_main = False


@pytest.fixture(scope="module")
def recovery() -> RecoveryPage:
    path = DIST / "404.html"
    assert path.is_file(), "Build web/dist with pnpm build before running WO-105 tests"
    parser = RecoveryPage()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def test_missing_page_has_one_clear_heading(recovery: RecoveryPage) -> None:
    assert recovery.headings == ["We couldn't find that page"]


def test_missing_page_is_not_indexable(recovery: RecoveryPage) -> None:
    assert any("noindex" in value.lower().replace(",", " ").split() for value in recovery.robots)


@pytest.mark.parametrize(
    ("label", "destination"),
    [("Go to the home page", ""), ("See the opt-out guides", "guides/")],
)
def test_recovery_links_match_configured_base_and_built_targets(
    recovery: RecoveryPage, label: str, destination: str,
) -> None:
    config = yaml.safe_load((ROOT / "site_src/site.yaml").read_text(encoding="utf-8"))
    base = config["base_path"].rstrip("/") + "/"
    matches = [href for href, text in recovery.links if text == label]
    assert len(matches) == 1, f"Expected one descriptive recovery link: {label}"
    target = urlsplit(matches[0])
    assert not target.scheme and not target.netloc, "Recovery stays on this site"
    assert target.path == base + destination
    assert not target.query and not target.fragment
    relative = unquote(target.path[len(base):])
    built = (DIST / relative / "index.html").resolve()
    assert built.is_relative_to(DIST.resolve())
    assert built.is_file(), f"Recovery link must resolve to built output: {matches[0]}"
