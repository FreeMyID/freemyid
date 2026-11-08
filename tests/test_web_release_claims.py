"""Site-wide checks for current app release claims in the built website."""

import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "web/dist"
VERSION = re.compile(
    r"(?<![\w.])(?:v(?:ersion)?\s*)?"
    r"(\d+\.\d+\.\d+(?:-[\da-z]+(?:[.-][\da-z]+)*)?"
    r"(?:\+[\da-z]+(?:[.-][\da-z]+)*)?)(?![\w-]|\.\d)",
    re.IGNORECASE,
)
SHORT_CURRENT_VERSION = re.compile(
    r"\b(?:v(?:ersion)?\s*)(\d{1,2}\.\d+)(?![\d.])\s+(?:is\s+)?(?:out|available)\b",
    re.IGNORECASE,
)
NONCURRENT_PREFIX = re.compile(
    r"\b(?:planned for|coming in|since|registry,|checklists,|list)\s*$", re.IGNORECASE,
)
APP_AVAILABLE = re.compile(
    r"\b(?:(?:free\s*my\s*id|(?:the\s+)?(?:windows\s+)?app)"
    r"\s+is\s+(?:now\s+)?available|(?<!not )available\s+now|also\s+available)\b",
    re.IGNORECASE,
)


class ReleaseClaims(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ignored = 0
        self.text: list[str] = []
        self.badge: list[str] | None = None
        self.badge_depth = 0
        self.badges: list[str] = []
        self.href: str | None = None
        self.link_text: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.button_text: list[str] | None = None
        self.buttons: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"head", "script", "style"}:
            self.ignored += 1
        if self.ignored:
            return
        attributes = dict(attrs)
        if attributes.get("data-slot") == "badge":
            self.badge = []
            self.badge_depth = 1
        elif tag == "span" and self.badge is not None:
            self.badge_depth += 1
        if tag == "a":
            self.href = attributes.get("href") or ""
            self.link_text = []
        if tag == "button":
            self.button_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"head", "script", "style"}:
            self.ignored -= 1
            return
        if self.ignored:
            return
        if tag == "span" and self.badge is not None:
            self.badge_depth -= 1
            if not self.badge_depth:
                self.badges.append(" ".join(" ".join(self.badge).split()))
                self.badge = None
        if tag == "a" and self.href is not None:
            self.links.append((self.href, " ".join(self.link_text)))
            self.href = None
        if tag == "button" and self.button_text is not None:
            self.buttons.append(" ".join(self.button_text))
            self.button_text = None

    def handle_data(self, data: str) -> None:
        if not self.ignored:
            self.text.append(data)
            if self.badge is not None:
                self.badge.append(data)
            if self.href is not None:
                self.link_text.append(data)
            if self.button_text is not None:
                self.button_text.append(data)


def current_versions(text: str) -> list[str]:
    versions = [
        match.group(1)
        for match in VERSION.finditer(text)
        if not NONCURRENT_PREFIX.search(text[max(0, match.start() - 20):match.start()])
    ]
    return versions + [match.group(1) for match in SHORT_CURRENT_VERSION.finditer(text)]


@pytest.fixture(scope="module")
def pages() -> list[tuple[Path, ReleaseClaims]]:
    assert (DIST / "index.html").is_file(), "Build the site with pnpm --dir web build first"
    result = []
    for path in sorted(DIST.rglob("*.html")):
        page = ReleaseClaims()
        page.feed(path.read_text(encoding="utf-8"))
        result.append((path.relative_to(DIST), page))
    return result


@pytest.fixture(scope="module")
def release_version() -> str:
    release = yaml.safe_load((ROOT / "site_src/data/release.yaml").read_text(encoding="utf-8"))
    return str(release.get("version") or "")


def test_current_release_claims_match_published_version(
    pages: list[tuple[Path, ReleaseClaims]], release_version: str,
) -> None:
    for path, page in pages:
        text = " ".join(page.text)
        versions = current_versions(text)
        available_badges = [
            badge for badge in page.badges
            if re.search(r"\bavailable now\b", badge, re.IGNORECASE)
        ]
        if release_version:
            assert all(version == release_version for version in versions), (path, versions)
            if available_badges:
                assert release_version in versions, (path, available_badges, versions)
        else:
            assert not versions, (path, versions)
            assert not available_badges, (path, available_badges)
            app_text = re.sub(
                r"\bwebsite protection guides\s+available\s+now\b", "", text, flags=re.IGNORECASE,
            )
            assert not APP_AVAILABLE.search(app_text), path


def test_no_installer_download_without_published_release(
    pages: list[tuple[Path, ReleaseClaims]], release_version: str,
) -> None:
    if release_version:
        return
    site = yaml.safe_load((ROOT / "site_src/site.yaml").read_text(encoding="utf-8"))
    for path, page in pages:
        downloads = [
            (href, label) for href, label in page.links
            if href == site["download_url"]
            or urlsplit(href).path.lower().endswith(".exe")
            or re.search(r"\bdownload\s+(?:free\s*my\s*id|freemyidsetup)", label, re.IGNORECASE)
        ]
        assert not downloads, (path, downloads)
        assert not [
            label for label in page.buttons
            if re.search(r"\bdownload\b", label, re.IGNORECASE)
            and not re.search(r"\bcoming soon\b", label, re.IGNORECASE)
        ], path


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Version 0.8.2 is out; v0.8.1 is out.", ["0.8.2", "0.8.1"]),
        ("Download version 0.8.2.", ["0.8.2"]),
        ("Version 0.9 is available.", ["0.9"]),
        ("Version 0.8.2-rc.1 is out.", ["0.8.2-rc.1"]),
        ("Planned for version 0.9.0; since version 0.7.0", []),
        ("registry, version 2026.11.06-sample; list version 2026.11.08.1; CC BY-NC 4.0", []),
    ],
)
def test_current_version_detection(text: str, expected: list[str]) -> None:
    assert current_versions(text) == expected


def test_badges_and_links_are_read_from_visible_html() -> None:
    page = ReleaseClaims()
    page.feed(
        '<head><title>Version 1.0.0</title></head>'
        '<span data-slot="badge">Available <span>now</span></span>'
        '<a href="/get/windows">Download</a>'
        '<script>Version 2.0.0</script>'
    )
    assert current_versions(" ".join(page.text)) == []
    assert page.badges == ["Available now"]
    assert page.links == [("/get/windows", "Download")]


@pytest.mark.parametrize(
    ("html", "version"),
    [
        ("Version 0.8.1 is out.", "0.8.2"),
        ('<span data-slot="badge">Available now</span>', "0.8.2"),
        ('<span data-slot="badge">Available now</span>', ""),
        ("Free My ID is available now.", ""),
        ("Available <b>now</b>", ""),
        ("Also available: Linux", ""),
        ('<a href="/FreeMyIDSetup.exe">Download</a>', ""),
        ('<a href="/download/">Download Free My ID</a>', ""),
        ("<button>Download now</button>", ""),
    ],
)
def test_inconsistent_claims_are_rejected(html: str, version: str) -> None:
    page = ReleaseClaims()
    page.feed(html)
    pages = [(Path("example.html"), page)]
    with pytest.raises(AssertionError):
        test_current_release_claims_match_published_version(pages, version)
        test_no_installer_download_without_published_release(pages, version)


def test_website_guides_are_not_an_app_release_claim() -> None:
    page = ReleaseClaims()
    page.feed("Read the free website protection guides available now")
    test_current_release_claims_match_published_version([(Path("example.html"), page)], "")
