"""WO-201: protect the rendered how-it-works sequence and its navigation."""

from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "web/dist/how-it-works/index.html"


class HowItWorksPage(HTMLParser):
    """Collect the visible step headings, text, images, and links from built output."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_main = False
        self.in_step = False
        self.heading_tag: str | None = None
        self.heading_parts: list[str] = []
        self.h1s: list[str] = []
        self.step_title_parts: list[str] = []
        self.step_titles: list[str] = []
        self.step_text: list[str] = []
        self.all_text: list[str] = []
        self.image_alts: list[str] = []
        self.links: list[str] = []
        self.has_refresh_root = False
        self.step_list_label = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = (values.get("class") or "").split()
        if tag == "main":
            self.in_main = True
        if not self.in_main:
            return
        if "site-refresh" in classes:
            self.has_refresh_root = True
        if tag == "ol" and "site-refresh__steps" in classes:
            self.step_list_label = values.get("aria-label") or ""
        if tag == "li" and "site-refresh__step" in classes:
            self.in_step = True
            self.step_title_parts = []
            self.step_text.append("")
        if tag == "h1" or (tag == "h3" and self.in_step):
            self.heading_tag = tag
            self.heading_parts = []
        if tag == "a":
            self.links.append(values.get("href") or "")
        if tag == "img":
            self.image_alts.append(values.get("alt") or "")
        if tag == "svg" and values.get("role") == "img":
            self.image_alts.append(values.get("aria-label") or "")

    def handle_data(self, data: str) -> None:
        if not self.in_main:
            return
        normalized = " ".join(data.split())
        if not normalized:
            return
        self.all_text.append(normalized)
        if self.in_step:
            self.step_text[-1] += f" {normalized}"
        if self.heading_tag:
            self.heading_parts.append(normalized)

    def handle_endtag(self, tag: str) -> None:
        if self.heading_tag == tag:
            heading = " ".join(self.heading_parts)
            if tag == "h1":
                self.h1s.append(heading)
            elif tag == "h3" and self.in_step:
                self.step_titles.append(heading)
                self.step_title_parts.append(heading)
            self.heading_tag = None
        if tag == "li" and self.in_step:
            self.in_step = False
        if tag == "main":
            self.in_main = False


@pytest.fixture(scope="module")
def page() -> HowItWorksPage:
    assert PAGE.is_file(), "Build web/dist with pnpm build before WO-201 tests"
    parsed = HowItWorksPage()
    parsed.feed(PAGE.read_text(encoding="utf-8"))
    return parsed


def test_built_page_has_the_refresh_root_and_one_clear_title(page: HowItWorksPage) -> None:
    assert page.has_refresh_root
    assert page.h1s == ["How Free My ID works"]
    assert page.step_list_label == "The four steps in the Free My ID process"


def test_built_steps_keep_the_approved_order_and_key_process_details(page: HowItWorksPage) -> None:
    assert page.step_titles == [
        "Tell it who to protect",
        "It sends the requests",
        "It keeps checking",
        "You see the proof",
    ]
    text = " ".join(page.step_text)
    assert "Once a day, when your PC is on and you're signed in" in text
    assert "You can print it." in text


def test_built_step_art_has_meaningful_alternatives_and_guides_link(page: HowItWorksPage) -> None:
    # WO-178: steps 1-3 carry the approved light/dark step pictures, step 4 the report picture.
    assert len(page.image_alts) == 4
    assert all(alt.strip() for alt in page.image_alts)
    assert any(href.endswith("/guides/") for href in page.links)


def test_built_page_keeps_request_methods_and_practice_guidance(page: HowItWorksPage) -> None:
    text = " ".join(page.all_text)
    assert '"Do it with me"' in text
    assert '"Fill it in for me"' in text
    assert "Practice mode first" in text
    assert "It never tries to get around those checks." in text
