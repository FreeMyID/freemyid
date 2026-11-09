"""Keep hand-written "never asks" promises aligned with the /safety/ source list."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "web/src/pages/safety/index.astro"

# The locations named in WO-168.  A named location may be absent while copy moves;
# that is reported as a skip rather than silently dropping it from this guard.
COPIES = (
    Path("docs/USER_GUIDE.md"),
    Path("docs/HELPER_GUIDE.md"),
    Path("docs/FRIDGE_CARD.md"),
    Path("docs/FAMILY_QUICK_START.md"),
    Path("web/src/pages/families"),
)
CORE_CONCEPTS = {
    "Social Security number": re.compile(r"\bsocial security number\b", re.IGNORECASE),
    # Bounded to one sentence: "bank" in one passage must not pair with "card details" in another.
    "bank or card details": re.compile(
        r"\bbank(?: account)?\b[^.!?]{0,80}?\b(?:credit |debit )?card\b[^.!?]{0,20}?\bdetails\b",
        re.IGNORECASE,
    ),
    "never charges you": re.compile(r"\bnever charges you\b", re.IGNORECASE),
}
BARE_PASSWORDS = re.compile(r"\bpasswords\b", re.IGNORECASE)
NEVER_ASKS = re.compile(r"\bnever ask(?:s)?\b", re.IGNORECASE)
ALLOWED_PASSWORD_CONTEXT = re.compile(
    r"\bapp passwords?\b|\b(?:your|their)\b[^.!?\n]{0,40}\bemail passwords?\b",
    re.IGNORECASE,
)


def _copy_files(location: Path) -> list[Path]:
    path = ROOT / location
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(path.rglob("*.astro"))
    return []


def _never_asks_sentences(text: str) -> list[str]:
    return [
        sentence
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if NEVER_ASKS.search(sentence)
    ]


def _bare_password_hits(sentence: str) -> list[str]:
    """Each "passwords" must sit inside its own app-password / email-password phrase."""
    allowed = [m.span() for m in ALLOWED_PASSWORD_CONTEXT.finditer(sentence)]
    return [
        m.group(0)
        for m in BARE_PASSWORDS.finditer(sentence)
        if not any(start <= m.start() and m.end() <= end for start, end in allowed)
    ]


def test_safety_master_has_the_decided_core_list() -> None:
    text = MASTER.read_text(encoding="utf-8")
    assert "Social Security number" in text
    assert "Bank account, credit or debit card details" in text
    # /safety/ states the payment equivalent of the "never charges you" promise.
    assert "A payment of any kind" in text


@pytest.mark.parametrize("location", COPIES, ids=lambda path: path.as_posix())
def test_named_copy_exists_or_is_reported_skipped(location: Path) -> None:
    if not _copy_files(location):
        pytest.skip(f"missing named copy: {location.as_posix()}")


@pytest.mark.parametrize(
    "location",
    (
        Path("docs/USER_GUIDE.md"),
        Path("docs/HELPER_GUIDE.md"),
        pytest.param(
            Path("docs/FRIDGE_CARD.md"),
            marks=pytest.mark.xfail(
                strict=True, reason="docs/FRIDGE_CARD.md:17 missing never charges you"
            ),
        ),
        Path("docs/FAMILY_QUICK_START.md"),
        Path("web/src/pages/families"),
    ),
    ids=lambda path: path.as_posix(),
)
def test_existing_copy_has_all_core_promise_concepts(location: Path) -> None:
    if not _copy_files(location):
        pytest.skip(f"missing named copy: {location.as_posix()}")
    text = "\n".join(path.read_text(encoding="utf-8") for path in _copy_files(location))
    missing = [name for name, pattern in CORE_CONCEPTS.items() if not pattern.search(text)]
    assert not missing, f"{location.as_posix()} missing: {', '.join(missing)}"


@pytest.mark.parametrize("location", COPIES, ids=lambda path: path.as_posix())
def test_never_asks_sentences_do_not_use_bare_passwords(location: Path) -> None:
    files = _copy_files(location)
    if not files:
        pytest.skip(f"missing named copy: {location.as_posix()}")
    offenders = []
    for path in files:
        for line, sentence in enumerate(_never_asks_sentences(path.read_text(encoding="utf-8")), 1):
            if _bare_password_hits(sentence):
                offenders.append(f"{path.relative_to(ROOT)}:{line}: {sentence}")
    assert not offenders, "\n".join(offenders)


def test_bare_passwords_in_a_never_asks_sentence_fails() -> None:
    sentence = "Free My ID never asks for passwords."
    assert BARE_PASSWORDS.search(sentence)
    assert NEVER_ASKS.search(sentence)
    assert not ALLOWED_PASSWORD_CONTEXT.search(sentence)


def test_allowed_password_contexts_are_not_bare() -> None:
    app = "Free My ID never asks for app passwords."
    email = "Free My ID never asks for your email password."
    assert ALLOWED_PASSWORD_CONTEXT.search(app)
    assert ALLOWED_PASSWORD_CONTEXT.search(email)


def test_bare_passwords_next_to_an_allowed_phrase_still_fails() -> None:
    sentence = "Free My ID never asks for passwords or your email password."
    assert _bare_password_hits(sentence) == ["passwords"]
    assert _bare_password_hits("Free My ID never asks for app passwords.") == []
    assert _bare_password_hits("It never asks for your Gmail email passwords.") == []


def test_bank_and_card_details_must_share_one_sentence() -> None:
    pattern = CORE_CONCEPTS["bank or card details"]
    assert pattern.search("It never asks for your bank or card details.")
    assert pattern.search("Bank account, credit or debit card details")
    assert not pattern.search("A bank may call you. Call me.\n\nNever share card details.")
