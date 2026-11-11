"""Guard the quick start and the help pages the copilot parity test misses.

tests/copilot/test_cp_never_asks_parity.py looks for docs/FAMILY_QUICK_START.md,
but the file is at the repo root, and it does not read docs/user/.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
USER_DOCS = ROOT / "docs" / "user"
QUICK_START = ROOT / "FAMILY_QUICK_START.md"

# "bank or card details" (src/freemyid/wizard/ui.py:266-267) names both items.
_SSN = re.compile(r"\b(?:social security numbers?|ssn)\b", re.IGNORECASE)
_BANK_DETAILS = re.compile(
    r"\bbank(?:\s+account)?(?:\s*,\s*|\s+or\s+)?\s*(?:credit\s+or\s+debit\s+)?card\s+details\b"
    r"|\bbank(?:\s+account)?\s+details\b",
    re.IGNORECASE,
)
_CARD_DETAILS = re.compile(
    r"\b(?:credit\s+or\s+debit\s+|debit\s+|credit\s+)?card\s+details\b",
    re.IGNORECASE,
)
# Either verb covers never paying or charging ("never charges you" on the quick start).
_NEVER_PAYS_OR_CHARGES = re.compile(
    r"\bnever\s+(?:pays?|paying|charges?|charging)\b"
    r"|\b(?:no|without\s+a)\s+payment\b"
    r"|\bpayment\s+of\s+any\s+kind\b",
    re.IGNORECASE,
)
_CORE_ITEMS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Social Security number", _SSN),
    ("bank details", _BANK_DETAILS),
    ("card details", _CARD_DETAILS),
)

_NEVER_ASKS = re.compile(r"\bnever\s+asks?\b", re.IGNORECASE)
# Other ways to promise it ("does not ask", "won't ever ask"). These count as the
# promise only when the same text also names a core item, so "does not ask you to
# restart" is not read as a weak promise.
_NEVER_ASKS_OTHER = re.compile(
    r"\b(?:will\s+not|would\s+not|does\s+not|do\s+not|won'?t|doesn'?t|don'?t)"
    r"\s+(?:ever\s+)?asks?\b",
    re.IGNORECASE,
)
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*\S)\s*$")
_FENCE_OR_COMMENT = re.compile(r"```.*?```|<!--.*?-->", re.DOTALL)
_PY_CITE = re.compile(r"(\b[A-Za-z0-9_]+)\.py\b")

_NEGATED_ASK = re.compile(
    r"\b(?:never|not|won'?t|will not|would not|does not|do not|doesn'?t|don'?t)\s+asks?\b",
    re.IGNORECASE,
)
_WILL_ASK = re.compile(
    r"\b(?:free my id|the app|the program|the wizard|we)\b[^.!?]{0,120}?"
    r"\b(?:will ask|would ask|asks?|needs?|will need|requires?|wants?|will want"
    r"|prompts?|will prompt|collects?|will collect|must have)\b"
    r"|\b(?:it|this|the next screen)\s+(?:will ask|would ask|asks|needs|will need|requires"
    r"|prompts|will prompt|collects)\b",
    re.IGNORECASE,
)
_BANK_NUMBER = re.compile(
    r"\bbank\b[^.!?]{0,40}\b(?:numbers?|accounts?|details)\b|\baccount\s+numbers?\b",
    re.IGNORECASE,
)
_CARD_NUMBER = re.compile(
    r"\b(?:credit\s+|debit\s+|bank\s+)?cards?\b[^.!?]{0,20}\b(?:numbers?|details)\b",
    re.IGNORECASE,
)
_PASSWORD = re.compile(r"\bpasswords?\b", re.IGNORECASE)
# The removals mailbox is the only password Free My ID may ask the person to enter.
_MAILBOX_PASSWORD = re.compile(
    r"\b(?:app(?:[-\s]specific)?|application|program|mailbox|bridge"
    r"|removals(?:\s+mailbox)?)\s+passwords?\b"
    r"|\bpasswords?\s+for\s+(?:your\s+|the\s+)?(?:own\s+)?(?:removals\s+)?mailbox\b",
    re.IGNORECASE,
)


def _user_pages() -> list[Path]:
    return sorted(path for path in USER_DOCS.glob("*.md") if path.is_file())


def _mask_fences_and_comments(text: str) -> str:
    """Blank out fenced code and HTML comments without moving line numbers."""

    def blanks(match: re.Match[str]) -> str:
        return re.sub(r"[^\n]", " ", match.group(0))

    return _FENCE_OR_COMMENT.sub(blanks, text)


def _split_sentences(flat: str) -> list[str]:
    protected = _PY_CITE.sub(r"\1_py", flat)
    parts = re.split(r"(?<=[.!?])\s+", protected)
    return [part.replace("_py", ".py").strip() for part in parts if part.strip()]


def _intro_before(lines: list[str], start: int) -> tuple[int, str]:
    """Paragraph immediately above a list, even with one blank line between them."""
    cursor = start - 1
    while cursor >= 0 and lines[cursor].strip() == "":
        cursor -= 1
    if cursor < 0:
        return start + 1, ""
    collected: list[str] = []
    while cursor >= 0 and lines[cursor].strip() != "":
        collected.append(lines[cursor].strip())
        cursor -= 1
    collected.reverse()
    return cursor + 2, " ".join(collected)


def _is_promise(text: str) -> bool:
    if _NEVER_ASKS.search(text):
        return True
    return bool(
        _NEVER_ASKS_OTHER.search(text)
        and any(pattern.search(text) for _name, pattern in _CORE_ITEMS)
    )


def _never_asks_units(text: str) -> list[tuple[int, str]]:
    """Each "never asks" sentence, or a list whose intro says "never asks"."""
    lines = _mask_fences_and_comments(text).splitlines()
    consumed: set[int] = set()
    units: list[tuple[int, str]] = []
    index = 0
    total = len(lines)
    while index < total:
        if _LIST_ITEM.match(lines[index]) is None:
            index += 1
            continue
        start = index
        items: list[str] = []
        while index < total:
            item = _LIST_ITEM.match(lines[index])
            if item is not None:
                items.append(item.group(1).strip())
                index += 1
                continue
            next_line = index + 1
            blank_between_items = lines[index].strip() == "" and next_line < total
            if blank_between_items and _LIST_ITEM.match(lines[next_line]):
                index += 1
                continue
            break
        intro_line, intro = _intro_before(lines, start)
        block = " ".join(part for part in (intro, *items) if part)
        if _is_promise(block):
            units.append((intro_line, " ".join(block.split())))
            if intro:
                consumed.update(range(intro_line - 1, start))
            consumed.update(range(start, index))
    paragraph: list[tuple[int, str]] = []

    def flush() -> None:
        if not paragraph:
            return
        start_line = paragraph[0][0]
        flat = " ".join(piece for _, piece in paragraph)
        for sentence in _split_sentences(flat):
            if _is_promise(sentence):
                units.append((start_line, sentence))
        paragraph.clear()

    for line_number, line in enumerate(lines, 1):
        if line_number - 1 in consumed or line.strip() == "":
            flush()
            continue
        paragraph.append((line_number, line.strip()))
    flush()
    return units


def _promise_report(text: str) -> list[str]:
    """Missing core items for each never-asks sentence or list. Empty means the promise holds."""
    weak: list[str] = []
    for line, unit in _never_asks_units(text):
        missing = [name for name, pattern in _CORE_ITEMS if pattern.search(unit) is None]
        if missing:
            weak.append(f"line {line}: missing {', '.join(missing)}")
    return weak


def _password_is_only_mailbox(sentence: str) -> bool:
    allowed = [match.span() for match in _MAILBOX_PASSWORD.finditer(sentence)]
    passwords = list(_PASSWORD.finditer(sentence))
    if not passwords:
        return True
    return all(
        any(start <= match.start() and match.end() <= end for start, end in allowed)
        for match in passwords
    )


def _forbidden_asks(text: str) -> list[str]:
    """Lines that say Free My ID will ask for a secret it promises not to ask for."""
    hits: list[str] = []
    lines = _mask_fences_and_comments(text).splitlines()
    paragraph: list[tuple[int, str]] = []

    def flush() -> None:
        if not paragraph:
            return
        start_line = paragraph[0][0]
        flat = " ".join(piece for _, piece in paragraph)
        for sentence in _split_sentences(flat):
            cleaned = _NEGATED_ASK.sub("not that", sentence)
            if _WILL_ASK.search(cleaned) is None:
                continue
            reasons: list[str] = []
            if _SSN.search(sentence):
                reasons.append("Social Security number")
            if _BANK_NUMBER.search(sentence):
                reasons.append("bank number")
            if _CARD_NUMBER.search(sentence):
                reasons.append("card number")
            if _PASSWORD.search(sentence) and not _password_is_only_mailbox(sentence):
                reasons.append("password")
            if reasons:
                hits.append(f"line {start_line}: {', '.join(reasons)}")
        paragraph.clear()

    for line_number, line in enumerate(lines, 1):
        if line.strip() == "":
            flush()
            continue
        paragraph.append((line_number, line.strip()))
    flush()
    return hits


def test_user_docs_directory_has_pages() -> None:
    pages = _user_pages()
    assert pages, "docs/user has no markdown pages"
    assert all(page.parent == USER_DOCS for page in pages)


def test_root_quick_start_names_core_items_and_never_paying_or_charging() -> None:
    text = QUICK_START.read_text(encoding="utf-8")
    report = _promise_report(text)
    assert not report, "FAMILY_QUICK_START.md " + "; ".join(report)
    flat = " ".join(text.split())
    assert _never_asks_units(text), "FAMILY_QUICK_START.md has no never-asks promise"
    pays = _NEVER_PAYS_OR_CHARGES.search(flat)
    assert pays, "FAMILY_QUICK_START.md missing never paying or charging"


@pytest.mark.parametrize("page", _user_pages(), ids=lambda page: page.name)
def test_user_page_never_asks_names_all_three_in_one_place(page: Path) -> None:
    report = _promise_report(page.read_text(encoding="utf-8"))
    assert not report, f"{page.relative_to(ROOT).as_posix()}: " + "; ".join(report)


@pytest.mark.parametrize("page", _user_pages(), ids=lambda page: page.name)
def test_user_page_does_not_say_it_will_ask_for_secrets(page: Path) -> None:
    hits = _forbidden_asks(page.read_text(encoding="utf-8"))
    assert not hits, f"{page.relative_to(ROOT).as_posix()}: " + "; ".join(hits)


def test_at_least_one_user_page_makes_the_promise() -> None:
    assert any(
        _never_asks_units(page.read_text(encoding="utf-8")) for page in _user_pages()
    ), "no docs/user page says Free My ID never asks for these items"


def test_deleting_the_promise_is_not_a_pass() -> None:
    assert _never_asks_units("Free My ID is friendly. Nothing else to say.") == []


def test_other_ways_to_promise_are_recognised() -> None:
    for sample in (
        "Free My ID will never ask for your Social Security number.",
        "Free My ID does not ask for your Social Security number.",
        "Free My ID doesn't ever ask for your Social Security number.",
        "We won't ask for your Social Security number.",
    ):
        units = _never_asks_units(sample)
        assert units, sample
        assert _promise_report(sample), sample


def test_other_ways_to_say_it_will_ask_fail() -> None:
    for sample in (
        "Free My ID wants your Social Security number.",
        "We will collect your bank number.",
        "The wizard prompts for your card number.",
        "The app will need a password.",
        "It requires your Social Security number.",
    ):
        assert _forbidden_asks(sample), sample


def test_full_promise_passes() -> None:
    text = "Free My ID never asks for your Social Security number, bank details, or card details."
    assert _promise_report(text) == []


def test_app_wording_in_one_sentence_passes() -> None:
    text = "Free My ID never asks for your Social Security number, bank or card details."
    assert _promise_report(text) == []


def test_full_promise_in_one_list_passes() -> None:
    text = (
        "Free My ID never asks for:\n"
        "\n"
        "- your Social Security number\n"
        "- bank details\n"
        "- card details\n"
    )
    assert _promise_report(text) == []


def test_promise_naming_only_the_social_security_number_fails() -> None:
    text = "Free My ID never asks for your Social Security number."
    report = _promise_report(text)
    assert len(report) == 1
    assert "bank details" in report[0]
    assert "card details" in report[0]


def test_never_asks_split_across_two_paragraphs_fails() -> None:
    text = (
        "Free My ID never asks for your Social Security number.\n"
        "\n"
        "It never asks for bank details or card details.\n"
    )
    report = _promise_report(text)
    assert len(report) == 2
    assert "bank details" in report[0] and "card details" in report[0]
    assert "Social Security number" in report[1]


def test_will_ask_for_a_secret_fails() -> None:
    samples = (
        "Free My ID will ask for your Social Security number.",
        "Free My ID will ask for your bank number.",
        "Free My ID will ask for your card number.",
        "Free My ID will ask for a password.",
    )
    for sample in samples:
        assert _forbidden_asks(sample), sample


def test_removals_mailbox_password_is_allowed() -> None:
    text = "Free My ID asks for an app password for your own removals mailbox."
    assert _forbidden_asks(text) == []


def test_never_asks_promise_is_not_treated_as_a_will_ask() -> None:
    text = "Free My ID never asks for your Social Security number, bank details, or card details."
    assert _forbidden_asks(text) == []
