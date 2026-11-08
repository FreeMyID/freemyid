"""WR-62/63: the phone-number guide is built with the cleared wording, linked from /guides/, in the sitemap."""

from pathlib import Path

from tests.test_web_privacy_wording import text_of

DIST = Path(__file__).resolve().parents[1] / "web/dist"
OUT = "guides/get-your-phone-number-off-people-search-sites/"


def test_page_uses_cleared_wording() -> None:
    text = text_of((DIST / OUT / "index.html").read_text(encoding="utf-8"))
    assert "Each listing is a separate request, and a site can have more than one listing for you." in text
    assert "can bring up a name and address" in text
    assert "It won't stop scammers" in text
    for not_cleared in ("remove the whole profile", "often brings up", "in a few months"):
        assert not_cleared not in text


def test_page_links_guides_and_is_linked() -> None:
    html = (DIST / OUT / "index.html").read_text(encoding="utf-8")
    for slug in ("spokeo", "whitepages", "truepeoplesearch"):
        assert f'/guides/{slug}/"' in html
    assert f'/{OUT}"' in (DIST / "guides/index.html").read_text(encoding="utf-8")
    assert OUT in (DIST / "sitemap.xml").read_text(encoding="utf-8")
