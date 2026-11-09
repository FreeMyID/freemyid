"""Absolute claims on the live site (web/) must be literally true for the shipped app.

Fixed 2026-11-08 (web lead): the listing check sends name + town to people-search search pages
(engine/exposure.py, submitters/web_form.search_url), practice mode still looks people up, the
wizard asks for an optional phone number, AUTO email mode is opt-in, and desktop notices carry
no name (engine/runner.py notify()).
"""

import re
from pathlib import Path

import pytest

from tests.test_web_privacy_wording import text_of

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "web/dist"
SRC = ROOT / "web/src/pages"
# Source comments ({/* source: ... */} and // lines) may quote banned words to explain a rule.
# <style> blocks are CSS, not copy ("max-width: 100%" is not a claim). A // comment is stripped
# to the end of its own line only, so it can't hide the rest of the page.
COMMENTS = re.compile(
    r"\{/\*.*?\*/\}|^\s*//[^\n]*$|<style\b.*?</style>", re.DOTALL | re.MULTILINE
)

# (built page, astro source, phrase that must be there)
FIXED = [
    ("index.html", "index.astro",
     "It gives a site your phone number only if you switch that on."),
    ("index.html", "index.astro",
     "Practice mode comes first, so no removal requests go out until you say so."),
    ("how-it-works/index.html", "how-it-works/index.astro",
     'so no removal requests go out until you say "start sending real requests."'),
    ("families/index.html", "families/index.astro",
     "Unless they switch on automatic sending, no email goes out until they press OK."),
    ("families/index.html", "families/index.astro",
     ('like "Free My ID needs 5 minutes of your help." '
     "They don't show names, addresses or other personal details.")),
    ("safety/index.html", "safety/index.astro",
     ("The app may only contact the removal sites themselves, your removal mailbox "
     "and our public list of sites (see below).")),
]

# Phrases that were not true for the shipped app. Checked on every built page.
BANNED = (
    "never a phone number",
    "nothing is sent until you say",
    "nothing is sent until they press ok",
    "they never include personal details",
    "mom: 2 sites need you",
    "never sent to anyone",
    "go out only in removal requests you approve",
    "go only to the sites you ask to remove you",
    "go out only in a removal request you approve",
    "guaranteed",
    "100%",
    "erase you from the internet",
)

# Practice mode still searches people-search sites, so "nothing is sent / sends nothing /
# nothing goes out" is false in any wording (2026-11-08, families said "nothing is sent to any
# site until you turn on real requests"). The approved wording talks about removal requests:
# "no removal requests go out until you say so" must stay allowed.
NOTHING_SENT = re.compile(
    r"\bnothing\s+(?:is|gets|will\s+be|has\s+been|was)?\s*(?:sent|submitted)\b(?!\s+to\s+(?:us|the\s+project)\b)(?!\s+until\s+you\s+click\b)"
    r"|\bnothing\s+(?:goes|go|is\s+going|gets\s+sent)\s+out\b"
    r"|\b(?:sends|sent|submits|submitted)\s+nothing\b(?!\s+about\s+you\b)"
    r"|\bdoes(?:n't|\s+not)\s+send\s+anything\b"
)
SHOULD_BE_BANNED = (
    "Nothing is sent until you say so.",
    "Nothing is sent to any site until you turn on real requests.",
    "Nothing gets sent while you practice.",
    "In practice mode Free My ID sends nothing.",
    "Practice mode sent nothing to any site.",
    "Nothing goes out until you turn it on.",
    "Practice mode does not send anything.",
    "Nothing will be submitted in practice mode.",
)
SHOULD_BE_ALLOWED = (
    "Nothing is sent to us.",
    "That download sends nothing about you or the people you protect.",
    "Share this page on Facebook (opens Facebook; nothing is sent until you click)",
    "Practice mode comes first, so no removal requests go out until you say so.",
    'so no removal requests go out until you say "start sending real requests."',
    "Unless they switch on automatic sending, no email goes out until they press OK.",
)


@pytest.mark.parametrize("sentence", SHOULD_BE_BANNED)
def test_nothing_sent_pattern_catches(sentence: str) -> None:
    assert NOTHING_SENT.search(sentence.lower()), sentence


@pytest.mark.parametrize("sentence", SHOULD_BE_ALLOWED)
def test_nothing_sent_pattern_allows_approved(sentence: str) -> None:
    assert not NOTHING_SENT.search(sentence.lower()), sentence


def test_no_nothing_sent_claim_in_sources() -> None:
    for f in sorted(SRC.rglob("*.astro")):
        text = text_of(COMMENTS.sub("", f.read_text(encoding="utf-8"))).lower()
        m = NOTHING_SENT.search(text)
        assert not m, (f.relative_to(ROOT), text[max(0, m.start() - 60):m.end() + 60])


def test_no_nothing_sent_claim_in_build() -> None:
    pages = sorted(DIST.rglob("*.html"))
    assert pages, "Build web/dist with pnpm build first"
    for page in pages:
        text = text_of(page.read_text(encoding="utf-8")).lower()
        m = NOTHING_SENT.search(text)
        assert not m, (page.relative_to(DIST), text[max(0, m.start() - 60):m.end() + 60])


@pytest.mark.parametrize(("page", "source", "phrase"), FIXED)
def test_fixed_phrase_in_source(page: str, source: str, phrase: str) -> None:
    assert phrase in text_of((SRC / source).read_text(encoding="utf-8"))


@pytest.mark.parametrize(("page", "source", "phrase"), FIXED)
def test_fixed_phrase_in_build(page: str, source: str, phrase: str) -> None:
    path = DIST / page
    assert path.is_file(), "Build web/dist with pnpm build first"
    assert phrase in text_of(path.read_text(encoding="utf-8"))


def test_no_banned_absolute_in_sources() -> None:
    for f in sorted(SRC.rglob("*.astro")):
        text = text_of(COMMENTS.sub("", f.read_text(encoding="utf-8"))).lower()
        for claim in BANNED:
            assert claim not in text, (f.relative_to(ROOT), claim)


def test_no_banned_absolute_in_build() -> None:
    pages = sorted(DIST.rglob("*.html"))
    assert pages, "Build web/dist with pnpm build first"
    for page in pages:
        text = text_of(page.read_text(encoding="utf-8")).lower()
        for claim in BANNED:
            assert claim not in text, (page.relative_to(DIST), claim)
