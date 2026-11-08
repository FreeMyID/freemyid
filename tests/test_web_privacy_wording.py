"""WO-101: privacy promises in built v3 pages and rollback templates."""

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "dist"
PROMISE = (
    "Your details are stored only on your computer. "
    "They go out only to the people-search sites themselves: your name and town to look you up, "
    "and removal requests you approve."
)
ABSOLUTE = re.compile(
    r"your details stay on your (?:computer|pc)"
    r"|(?:never|nothing) leaves? (?:your|the) computer"
    r"|(?:your )?(?:details|information|data) never leave(?:s)? (?:your|the) computer",
    re.IGNORECASE,
)


class PageText(HTMLParser):
    """Collect rendered text without depending on HTML whitespace."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def text_of(html: str) -> str:
    parser = PageText()
    parser.feed(html)
    return " ".join(" ".join(parser.parts).split())


def test_no_built_page_promises_details_never_leave() -> None:
    pages = sorted(DIST.rglob("*.html"))
    assert pages, "Build web/dist with pnpm build before running this suite"
    for page in pages:
        html = page.read_text(encoding="utf-8")
        assert not ABSOLUTE.search(html), page.relative_to(DIST)
        assert not ABSOLUTE.search(text_of(html)), page.relative_to(DIST)


@pytest.mark.parametrize("page", ["index.html", "safety/index.html", "faq/index.html"])
def test_built_privacy_promise_explains_approved_request(page: str) -> None:
    path = DIST / page
    assert path.is_file(), "Build web/dist with pnpm build before running this suite"
    html = path.read_text(encoding="utf-8")
    assert PROMISE in text_of(html)
    if page in {"index.html", "faq/index.html"}:
        answer = re.search(
            r'<details\b[^>]*\bid="q-where-data"[^>]*>(.*?)</details>',
            html,
            re.DOTALL,
        )
        assert answer, "Expected the existing where-data FAQ disclosure"
        assert "Where does my information go?" in text_of(answer[1])
        assert PROMISE in text_of(answer[1])


@pytest.mark.parametrize(
    "source",
    [
        "site_src/templates/pages/home.html",
        "site_src/templates/pages/safety.html",
        "site_src/data/faq.yaml",
    ],
)
def test_rollback_sources_use_same_privacy_promise(source: str) -> None:
    content = (ROOT / source).read_text(encoding="utf-8")
    assert PROMISE in content
    assert not ABSOLUTE.search(content)
