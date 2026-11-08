"""WR-61: the "Help a parent" guide is built, linked, in the sitemap, and keeps the cleared wording."""

from pathlib import Path

from tests.test_web_privacy_wording import text_of

DIST = Path(__file__).resolve().parents[1] / "web/dist"
OUT = "guides/help-a-parent-remove-their-information/"


def test_page_built_with_cleared_wording() -> None:
    text = text_of((DIST / OUT / "index.html").read_text(encoding="utf-8"))
    assert "Some sites can list people again under a new record" in text
    assert "The opt-out pages in our guides don't ask for a Social Security number" in text
    assert "Their details are stored on their computer, and nothing is sent to us." in text
    for draft_only in ("takes an afternoon", "No genuine opt-out page", "details stay on their computer",
                       "go only to the sites they ask"):
        assert draft_only not in text


def test_page_linked_and_in_sitemap() -> None:
    for page in ("families/index.html", "guides/index.html"):
        assert f'/{OUT}"' in (DIST / page).read_text(encoding="utf-8"), page
    assert OUT in (DIST / "sitemap.xml").read_text(encoding="utf-8")
