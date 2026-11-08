"""Credit freeze checklist: built from page-level research facts only, linked from /protect/, art and checklist present."""

from pathlib import Path

from tests.test_web_privacy_wording import text_of

DIST = Path(__file__).resolve().parents[1] / "web/dist"
OUT = "protect/credit-freeze/"


def test_checklist_page() -> None:
    html = (DIST / OUT / "index.html").read_text(encoding="utf-8")
    text = text_of(html)
    for bureau in ("freeze_equifax", "freeze_experian", "freeze_transunion"):
        assert f'id="cf-{bureau}"' in html and f'/protect/{bureau}/"' in html
    assert "within one business day (three business days by mail)" in text
    assert "proof of who you are and proof of your authority" in text
    assert 'alt="A credit card with a snowflake showing a frozen file."' in html
    # snippet-only or unresolved facts stay off the page (research doc sections 2 and 6)
    for unverified in ("800-887-7652", "800-428-9623", "guaranteed", "100%"):
        assert unverified not in text


def test_linked_from_protect_and_in_sitemap() -> None:
    assert f'/{OUT}"' in (DIST / "protect/index.html").read_text(encoding="utf-8")
    assert OUT in (DIST / "sitemap.xml").read_text(encoding="utf-8")
