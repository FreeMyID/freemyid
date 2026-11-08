"""WO-162: one master "never asks / never does" list (/safety/) and one exact short form everywhere else.

Short form (Morgan, 2026-11-08): "never asks for your Social Security number or bank or card details, and never charges
you". Verbs stay distinct: "asks for" (what it requests), "sends"/"gives" (what goes to a site), "does" (actions).
"""

import re
from pathlib import Path

import pytest

from tests.test_web_privacy_wording import text_of

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "web/dist"
SHORT = "never asks for your social security number or bank or card details, and never charges you"


def norm(s: str) -> str:
    return " ".join(s.replace("*", "").split()).lower()


@pytest.mark.parametrize("source", [
    "web/src/pages/index.astro", "web/src/components/Footer.astro", "web/src/pages/how-it-works/index.astro",
    "web/src/pages/families/index.astro", "site_src/data/faq.yaml", "FAMILY_QUICK_START.md", "docs/HELPER_GUIDE.md",
])
def test_short_form_in_source(source: str) -> None:
    assert SHORT in norm((ROOT / source).read_text(encoding="utf-8")), source


@pytest.mark.parametrize("page", ["index.html", "how-it-works/index.html", "families/index.html", "faq/index.html",
                                  "safety/index.html"])
def test_short_form_in_build(page: str) -> None:
    # every page has the footer short form; the listed pages also carry it in their own copy
    assert SHORT in norm(text_of((DIST / page).read_text(encoding="utf-8"))), page


def test_master_list_on_safety() -> None:
    text = norm(text_of((DIST / "safety/index.html").read_text(encoding="utf-8")))
    for item in ("your social security number", "bank account, credit or debit card details", "a payment of any kind",
                 "the password to your everyday email", "what it never does",
                 "give a site your phone number, unless you switch that on",
                 "create an account on a site for you", 'solve "are you a robot?" checks'):
        assert item in text, item
    # phone moved out of "never asks for": setup does ask for an optional phone number
    assert "your phone number, unless you choose to share it" not in text


def test_printed_copies_and_old_wording_gone() -> None:
    fridge = norm((ROOT / "docs/FRIDGE_CARD.md").read_text(encoding="utf-8"))
    # WO-184 (6deb3e8): the card now mirrors /safety/ (adds "money or a payment of any kind")
    assert "bank or card details" in fridge and "your everyday email password" in fridge
    for path in ("docs/FRIDGE_CARD.md", "docs/assets/fridge-card.html"):
        assert "bank card or passwords" not in (ROOT / path).read_text(encoding="utf-8"), path
    qs = norm((ROOT / "FAMILY_QUICK_START.md").read_text(encoding="utf-8"))
    assert "never sent to anyone" not in qs
    for page in DIST.rglob("*.html"):
        text = norm(text_of(page.read_text(encoding="utf-8")))
        assert not re.search(r"never asks for your social security number, bank or card details", text), page


def test_sec115_age_wording() -> None:
    # SEC-115 (5f01a9c): birth year is never sent; an age goes only when the listing itself shows one and a form asks
    safety = norm(text_of((DIST / "safety/index.html").read_text(encoding="utf-8")))
    assert "send your year of birth or your relatives' names to a site" in safety
    assert "it gets only the age that site's own listing already shows, never one worked out from your year of birth" in safety
    fam = norm(text_of((DIST / "families/index.html").read_text(encoding="utf-8")))
    assert "if a site's form asks for an age, it gets only the age its own listing shows" in fam
    for path in ("FAMILY_QUICK_START.md", "docs/HELPER_GUIDE.md"):
        assert "only the age" in norm((ROOT / path).read_text(encoding="utf-8")), path
