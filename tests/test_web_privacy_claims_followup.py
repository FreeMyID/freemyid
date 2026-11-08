"""WO-107: storage and approved-request privacy wording on remaining pages."""

from pathlib import Path

import pytest

from tests.test_web_privacy_wording import text_of

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "web/dist"
OLD_CLAIMS = ("never sent to anyone", "stay on the box", "stay with you")
FAMILIES_DETAILS = (
    "Optional: year of birth, phone number, relatives' names. "
    "These help Free My ID recognize the right listing. "
    "They are stored on your computer and sent only when a site's removal form asks for them, "
    "in a request you approve."
)


@pytest.mark.parametrize(
    ("page", "expected"),
    [
        ("families/index.html", FAMILIES_DETAILS),
        (
            "developers/index.html",
            ("Your profile and records are stored on the box you control. "
             "Nothing is sent to us: your details go only to the people-search sites "
             "(a name-and-town lookup, then the removal requests you approve) "
             "and through your own mail server."),
        ),
        (
            "whats-coming/index.html",
            ("Your details are stored with you. They are kept on your computer "
             "and go only to the people-search sites it checks and asks to remove you. "
             "Nothing is sent to us."),
        ),
    ],
)
def test_remaining_pages_explain_local_storage_without_absolute_claims(
    page: str, expected: str,
) -> None:
    path = DIST / page
    assert path.is_file(), "Build web/dist with pnpm build before running WO-107 tests"
    html = path.read_text(encoding="utf-8")
    text = text_of(html)
    assert expected in text
    for claim in OLD_CLAIMS:
        assert claim not in html.lower()
        assert claim not in text.lower()


def test_legacy_families_matches_the_corrected_optional_details_copy() -> None:
    source = (ROOT / "site_src/templates/pages/families.html").read_text(encoding="utf-8")
    assert FAMILIES_DETAILS in text_of(source)
    assert "never sent to anyone" not in source.lower()
    live_source = (ROOT / "web/src/pages/families/index.astro").read_text(encoding="utf-8")
    assert FAMILIES_DETAILS in text_of(live_source)
    assert "never sent to anyone" not in live_source.lower()
