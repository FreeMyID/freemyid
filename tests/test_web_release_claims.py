"""Site-wide checks for visible app release claims in the built website."""

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "dist"
PAGES = sorted(DIST.rglob("*.html"))
VERSION = re.compile(
    r"(?<![\w.])(?:(?:version\s+|v)"
    r"(?P<labelled>\d{1,3}\.\d+(?:\.\d+)?(?:[-+][\w.-]+)?)|"
    r"(?P<bare>\d{1,3}\.\d+\.\d+(?:[-+][\w.-]+)?))"
    r"(?!\w|\.\d)",
    re.IGNORECASE,
)


class VisiblePage(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.text: list[str] = []
        self.controls: list[tuple[str, str]] = []
        self.control: tuple[str, str, list[str]] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"head", "script", "style", "template"}:
            self.hidden += 1
        if self.hidden:
            return
        if tag in {"p", "li", "h1", "h2", "h3", "h4", "dt", "dd", "section"}:
            self.text.append(" ")
        if tag in {"a", "button"}:
            self.control = (tag, dict(attrs).get("href") or "", [])

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.text.append(data)
            if self.control is not None:
                self.control[2].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"head", "script", "style", "template"}:
            self.hidden -= 1
            return
        if self.hidden:
            return
        if self.control is not None and tag == self.control[0]:
            _, href, parts = self.control
            self.controls.append((href, " ".join("".join(parts).split())))
            self.control = None
        if tag in {"p", "li", "h1", "h2", "h3", "h4", "dt", "dd", "section"}:
            self.text.append(" ")

    @property
    def visible_text(self) -> str:
        return " ".join("".join(self.text).split())


def app_versions(text: str) -> list[str]:
    versions = []
    for match in VERSION.finditer(text):
        before = text[max(0, match.start() - 50):match.start()].lower()
        after = text[match.end():match.end() + 40].lower()
        if re.search(
            r"(?:planned for|since|sample broker registry,|checklists,|list)\s*$",
            before,
        ) or re.match(r"\s*,?\s*(?:we're|we are)\s+planning\b", after):
            continue
        versions.append(match.group("labelled") or match.group("bare"))
    return versions


def matches_release(claim: str, release: str) -> bool:
    return claim == release or (
        claim.count(".") == 1 and release.startswith(claim + ".")
    )


def app_availability(text: str, *, only_now: bool = True) -> list[str]:
    pattern = r"\b(?:available now|now available)\b" if only_now else r"\bavailable\b"
    claims = []
    for match in re.finditer(pattern, text, re.IGNORECASE):
        before = text[max(0, match.start() - 80):match.start()]
        if re.search(r"\b(?:not|isn't|aren't)\s+(?:yet\s+)?$", before, re.IGNORECASE):
            continue
        if re.search(
            r"\b(?:website|web site)\s+(?:\w+\s+){0,3}guides?\s+$",
            before, re.IGNORECASE,
        ):
            continue
        claims.append(match.group())
    return claims


@pytest.fixture(scope="module")
def release_version() -> str:
    data = yaml.safe_load((ROOT / "site_src/data/release.yaml").read_text(encoding="utf-8")) or {}
    return str(data.get("version") or "").removeprefix("v")


def assert_release_claims(page: VisiblePage, release_version: str, name: str) -> None:
    text = page.visible_text
    versions = app_versions(text)

    if release_version:
        assert all(matches_release(version, release_version) for version in versions), (
            f"{name}: app versions {versions} do not match {release_version}"
        )
        if app_availability(text):
            assert versions, f"{name}: availability claim without app version"
    else:
        downloads = [
            (href, label) for href, label in page.controls
            if re.search(r"\bdownload\b", label, re.IGNORECASE)
            or re.search(r"freemyidsetup.*\.exe", href, re.IGNORECASE)
        ]
        assert not versions, f"{name}: app versions without a release: {versions}"
        assert not app_availability(text, only_now=False), f"{name}: availability without a release"
        assert not downloads, f"{name}: download controls without a release"


@pytest.mark.parametrize("path", PAGES or [DIST / "index.html"], ids=lambda p: str(p.relative_to(DIST)))
def test_visible_release_claims_follow_published_version(path: Path, release_version: str) -> None:
    assert path.is_file(), "Build the Astro site with pnpm --dir web build first"
    page = VisiblePage()
    page.feed(path.read_text(encoding="utf-8"))
    assert_release_claims(page, release_version, str(path.relative_to(DIST)))


def test_claim_detection_distinguishes_current_planned_and_non_app_versions() -> None:
    text = (
        "Version 8.2.4 is out. New in v8.2. Planned for version 8.3. "
        "For version 8.4, we're planning more. In the app since version 7.1. "
        "Steps from the Free My ID checklists, version 2026.11.08.1. "
        "Guide data: the Free My ID sample broker registry, version 2026.11.06-sample."
    )
    assert app_versions(text) == ["8.2.4", "8.2"]
    assert matches_release("8.2", "8.2.4")
    assert not matches_release("8.2.5", "8.2.4")
    assert not matches_release("8.3", "8.2.4")
    assert app_availability("Read the website protection guides available now.") == []
    assert app_availability("The app is available now.")
    assert app_availability("The website has guides. The app is available now.")
    assert app_availability("The app is not available yet.", only_now=False) == []


@pytest.mark.parametrize(
    ("html", "release", "reason"),
    [
        ("<p>Version 8.2.3 is out.</p>", "8.2.4", "do not match"),
        ("<p>Version 8.2.5 is out.</p>", "8.2.4", "do not match"),
        ("<span>Available now</span>", "8.2.4", "without app version"),
        ("<p>The app is available.</p>", "", "availability without a release"),
        ('<a href="/download/">Download</a>', "", "download controls without a release"),
    ],
)
def test_inconsistent_claims_are_rejected(html: str, release: str, reason: str) -> None:
    page = VisiblePage()
    page.feed(html)
    with pytest.raises(AssertionError, match=reason):
        assert_release_claims(page, release, "example")
