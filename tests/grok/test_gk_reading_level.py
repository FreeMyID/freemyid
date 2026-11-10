"""Flesch-Kincaid reading-level ratchet for pages a regular user reads (WO-321).

Checked ``tests/copilot/test_cp_wording_guard.py``. That guard flags banned words
and unreleased install channels. It does not score reading grade, and it does
not read ``FAMILY_QUICK_START.md``. ``tests/codex/test_cx_app_practice_wording.py``
covers app strings only. ``tests/grok/`` has no other guard in this worktree.
The gap is the grade of the pages a regular user reads.

The grade written here is::

    0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59

Syllables are a simple count, not a dictionary: groups of aeiouy, a trailing
silent e dropped, and a trailing "le" after a consonant kept as a syllable.
A word of three letters or fewer, a word with no vowel, and a number each
count as one syllable.

Scored pages are ``docs/user/*.md`` (glob, not a fixed name list),
``FAMILY_QUICK_START.md``, and ``docs/USER_GUIDE.md``. Readable text skips
fenced code, tables, HTML comments, link targets, and headings. A section
whose heading says it is for helpers (for example "For helpers: the command
line") is skipped until the next heading of the same or higher level.
"""
from __future__ import annotations

import math
import re
from pathlib import Path, PurePosixPath

import pytest

ROOT = Path(__file__).resolve().parents[2]
CEILING = 8.0
SLACK = 0.5
_ASL = 0.39
_ASW = 11.8
_OFFSET = 15.59

# Path -> (today's grade rounded up, why the page is over the ceiling).
# Empty while every scored page is at or under 8. Drop a page from this dict
# once it scores under 8; the live test says so.
BASELINE: dict[str, tuple[float, str]] = {}

_EXTRA_PAGES = (
    PurePosixPath("FAMILY_QUICK_START.md"),
    PurePosixPath("docs/USER_GUIDE.md"),
)

_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_FENCE = re.compile(r"^[ \t]*(?P<mark>`{3,}|~{3,})(?P<rest>.*)$")
_ATX = re.compile(r"^ {0,3}(?P<hashes>#{1,6})[ \t]+(?P<title>.*)$")
_HR = re.compile(r"^ {0,3}(?:\*{3,}|_{3,})[ \t]*$")
_SETEXT = re.compile(r"^ {0,3}(?:=+|-{3,})[ \t]*$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
_REF_DEF = re.compile(r"^ {0,3}\[[^\]]+\]:[ \t]+\S")
_HELPER = re.compile(r"\bfor\s+(?:a\s+|the\s+)?helpers?\b", re.IGNORECASE)
_LIST = re.compile(r"^[ \t]*(?:[-*+]|\d+[.)])[ \t]+")
_BQ = re.compile(r"^[ \t]*>[ \t]?")
_IMG = re.compile(r"!\[([^\]]*)\]\((?:[^()]|\([^()]*\))*\)")
_LINK = re.compile(r"\[([^\]]*)\]\((?:[^()]|\([^()]*\))*\)")
_REF_LINK = re.compile(r"\[([^\]]*)\]\[[^\]]*\]")
_AUTOLINK = re.compile(r"<(?:https?|mailto):[^>\s]+>", re.IGNORECASE)
_URL = re.compile(r"https?://[^\s<>)\]]+", re.IGNORECASE)
_CODE_SPAN = re.compile(r"`+([^`]*)`+")
_CODE_MARK = re.compile("\ue000(\\d+)\ue001")
_WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?|[0-9]+(?:\.[0-9]+)*")
_ABBREV = re.compile(r"\b(?:e\.g|i\.e|mr|mrs|ms|dr|vs|etc|u\.s|u\.k)\.", re.IGNORECASE)
_VOWELS = frozenset("aeiouy")

PLAIN = "The cat sat on the mat. The dog ran in the park."
JARGON = (
    "The organizational telecommunications infrastructure utilizes "
    "extraordinarily sophisticated cryptographic authentication mechanisms "
    "to facilitate comprehensive interoperability standardization across "
    "international administrative jurisdictions simultaneously and "
    "continuously."
)


def rounded_up_grade(grade: float) -> float:
    """Whole number stored in ``BASELINE``: today's score rounded up."""
    return float(math.ceil(grade))


def syllable_count(token: str) -> int:
    """Simple syllable count for one word or number."""
    if not re.search(r"[A-Za-z]", token):
        return 1
    word = re.sub(r"[^a-z]", "", token.lower())
    if not word or len(word) <= 3:
        return 1
    count = 0
    previous_vowel = False
    for char in word:
        is_vowel = char in _VOWELS
        if is_vowel and not previous_vowel:
            count += 1
        previous_vowel = is_vowel
    if word.endswith("e"):
        count -= 1
    if word.endswith("le") and len(word) > 2 and word[-3] not in _VOWELS:
        count += 1
    return max(count, 1)


def _drop_url(match: re.Match[str]) -> str:
    url = match.group(0)
    trailing = ""
    while url and url[-1] in ".,;:!?":
        trailing = url[-1] + trailing
        url = url[:-1]
    return f" {trailing} "


def _clean_inline(text: str) -> str:
    """Drop link targets and markdown marks. Keep the words a reader speaks."""
    held: list[str] = []

    def hold(match: re.Match[str]) -> str:
        held.append(match.group(1))
        return f"\ue000{len(held) - 1}\ue001"

    def restore(match: re.Match[str]) -> str:
        return f" {held[int(match.group(1))]} "

    text = _CODE_SPAN.sub(hold, text)
    text = _IMG.sub(r" \1 ", text)
    text = _LINK.sub(r" \1 ", text)
    text = _REF_LINK.sub(r" \1 ", text)
    text = _AUTOLINK.sub(" ", text)
    text = _URL.sub(_drop_url, text)
    text = text.replace("**", "").replace("__", "")
    text = text.replace("*", "")
    text = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"\1", text)
    text = re.sub(r"<[^>\n]+>", " ", text)
    text = text.replace("\\", "")
    text = _CODE_MARK.sub(restore, text)
    return re.sub(r"\s+", " ", text).strip()


def _strip_blockquote(raw: str) -> str:
    line = raw
    while True:
        updated = _BQ.sub("", line, count=1)
        if updated == line:
            return line
        line = updated


def _is_table_row(raw: str) -> bool:
    stripped = raw.strip()
    if not stripped or stripped.startswith(("```", "~~~")):
        return False
    if _TABLE_SEP.match(stripped):
        return True
    return stripped.startswith("|") and stripped.count("|") >= 2


def _blocks(text: str) -> list[str]:
    """Prose blocks. Code, tables, headings, comments, and helper sections are out."""
    text = _HTML_COMMENT.sub(" ", text)
    blocks: list[str] = []
    current: list[str] = []
    in_fence = False
    fence_char = ""
    fence_len = 0
    helper_level: int | None = None
    in_list = False

    def flush(*, keep: bool = True) -> None:
        nonlocal in_list
        if keep and current:
            piece = " ".join(current).strip()
            core = piece.rstrip("\"')]}”’")
            if in_list and core and core[-1] not in ".!?":
                piece += "."
            if piece:
                blocks.append(piece)
        current.clear()
        in_list = False

    for raw in text.splitlines():
        if in_fence:
            closed = _FENCE.match(raw)
            if (
                closed
                and not closed.group("rest").strip()
                and closed.group("mark")[0] == fence_char
                and len(closed.group("mark")) >= fence_len
            ):
                in_fence = False
            continue
        opened = _FENCE.match(raw)
        if opened:
            in_fence = True
            fence_char = opened.group("mark")[0]
            fence_len = len(opened.group("mark"))
            flush()
            continue
        heading = _ATX.match(raw)
        if heading:
            flush()
            level = len(heading.group("hashes"))
            title = re.sub(r"\s+#+\s*$", "", heading.group("title")).strip()
            if helper_level is not None and level <= helper_level:
                helper_level = None
            if helper_level is None and _HELPER.search(title):
                helper_level = level
            continue
        if helper_level is not None:
            continue
        if not raw.strip():
            flush()
            continue
        if _HR.match(raw) or _REF_DEF.match(raw) or _is_table_row(raw):
            flush()
            continue
        if _SETEXT.match(raw):
            # A dashed or equals line glued to text is a setext heading.
            if current:
                flush(keep=False)
            continue
        line = _strip_blockquote(raw)
        if _LIST.match(line):
            flush()
            cleaned = _clean_inline(_LIST.sub("", line, count=1))
            if cleaned:
                current.append(cleaned)
                in_list = True
            continue
        cleaned = _clean_inline(line)
        if not cleaned:
            continue
        if in_list and raw[:1].isspace():
            current.append(cleaned)
            continue
        if in_list:
            flush()
        current.append(cleaned)
    flush()
    return blocks


def _sentences(blocks: list[str]) -> list[str]:
    text = "\n".join(blocks)
    text = _ABBREV.sub(lambda match: match.group(0).replace(".", ""), text)
    parts = re.split(r"[.!?]+(?:[\"')\]]+)?(?=\s|$)", text)
    found: list[str] = []
    for part in parts:
        cleaned = part.strip().strip("\"'()[]")
        if _WORD.search(cleaned):
            found.append(cleaned)
    return found


def _measure(text: str) -> tuple[list[str], int]:
    sentences = _sentences(_blocks(text))
    words = [word for sentence in sentences for word in _WORD.findall(sentence)]
    return words, len(sentences)


def prose_words(text: str) -> list[str]:
    """Words that count toward the grade, in order."""
    words, _sentences_n = _measure(text)
    return words


def grade_of(text: str) -> float:
    """Flesch-Kincaid grade of the readable words in ``text``.

    ``0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59``.
    Returns 0.0 when nothing scorable is left.
    """
    words, sentence_count = _measure(text)
    if not words or sentence_count == 0:
        return 0.0
    syllables = sum(syllable_count(word) for word in words)
    return _ASL * (len(words) / sentence_count) + _ASW * (syllables / len(words)) - _OFFSET


def _page_paths(root: Path) -> list[Path]:
    found: list[Path] = []
    user_dir = root / "docs" / "user"
    if user_dir.is_dir():
        found.extend(path for path in user_dir.glob("*.md") if path.is_file())
    for rel in _EXTRA_PAGES:
        path = root.joinpath(*rel.parts)
        if path.is_file():
            found.append(path)
    unique: dict[Path, Path] = {}
    for path in found:
        unique[path.resolve()] = path
    return list(unique.values())


def page_scores(root: Path) -> list[tuple[str, float]]:
    """``(relative posix path, grade)`` for every page this guard scores."""
    rows: list[tuple[str, float]] = []
    for path in _page_paths(root):
        rel = path.relative_to(root).as_posix()
        rows.append((rel, grade_of(path.read_text(encoding="utf-8"))))
    rows.sort(key=lambda row: row[0])
    return rows


def reading_problem(
    rel: str,
    grade: float,
    baseline: dict[str, tuple[float, str]] | None = None,
) -> str | None:
    """Why ``rel`` fails the ratchet, or None when it is allowed.

    A page not listed in the baseline fails above grade 8. A baseline page
    fails when it gets worse by more than 0.5, or when it drops under 8
    (that page has to leave ``BASELINE``).
    """
    table = BASELINE if baseline is None else baseline
    shown = f"{grade:.2f}"
    if rel in table:
        allowed, _reason = table[rel]
        if grade < CEILING:
            return f"{rel} scores {shown}, under {CEILING:.0f}; remove it from BASELINE"
        if grade > allowed + SLACK:
            return (
                f"{rel} scores {shown}, worse than its baseline of "
                f"{allowed:.0f} by more than {SLACK:g}"
            )
        return None
    if grade > CEILING:
        return f"{rel} scores {shown}, over the grade {CEILING:.0f} ceiling"
    return None


def problems_for(
    rows: list[tuple[str, float]],
    baseline: dict[str, tuple[float, str]] | None = None,
) -> list[str]:
    found: list[str] = []
    for rel, grade in rows:
        problem = reading_problem(rel, grade, baseline)
        if problem is not None:
            found.append(problem)
    return found


def format_report(rows: list[tuple[str, float]], problems: list[str]) -> str:
    """Failure text. The first lines are every page's score."""
    lines = [f"{rel}: {grade:.2f}" for rel, grade in rows]
    lines.append("")
    lines.extend(problems)
    return "\n".join(lines)


def test_short_plain_paragraph_passes() -> None:
    one = "The cat sat on the mat."
    assert grade_of(one) == pytest.approx(-1.45)
    assert grade_of(PLAIN) == pytest.approx(-1.45)
    assert grade_of(PLAIN) <= CEILING
    assert reading_problem("docs/user/plain.md", grade_of(PLAIN)) is None


def test_long_jargon_paragraph_fails() -> None:
    grade = grade_of(JARGON)
    assert grade > CEILING
    problem = reading_problem("docs/user/jargon.md", grade)
    assert problem is not None
    assert "docs/user/jargon.md" in problem
    assert f"{grade:.2f}" in problem


def test_code_blocks_and_tables_do_not_count() -> None:
    noisy = (
        f"{PLAIN}\n"
        "```\n"
        f"{JARGON}\n"
        "```\n"
        "   ```\n"
        f"{JARGON}\n"
        "   ```\n"
        "\n"
        "| Organizational | Telecommunications |\n"
        "| --- | --- |\n"
        "| cryptographic | interoperability |"
    )
    assert prose_words(noisy) == prose_words(PLAIN)
    assert grade_of(noisy) == pytest.approx(grade_of(PLAIN))
    assert grade_of("```\n" + JARGON + "\n```\n") == 0.0
    assert "organizational" not in {word.lower() for word in prose_words(noisy)}


def test_helper_sections_comments_headings_and_link_targets_do_not_count() -> None:
    text = "\n".join(
        [
            "The cat sat on the mat.",
            "<!--",
            JARGON,
            "-->",
            "# " + JARGON,
            "## For helpers: the command line",
            JARGON,
            "## Next",
            "The dog ran in the park.",
            "Read the [notes](https://example.com/organizational/telecommunications) now.",
            "See <https://example.com/cryptographic> too.",
        ]
    )
    words = [word.lower() for word in prose_words(text)]
    assert "organizational" not in words
    assert "cryptographic" not in words
    assert "example" not in words
    assert words.count("cat") == 1
    assert words.count("dog") == 1
    assert "notes" in words
    kept = "The cat sat on the mat. The dog ran in the park. Read the notes now. See too."
    assert grade_of(text) == pytest.approx(grade_of(kept))


def test_baseline_ratchet() -> None:
    today = 9.2
    allowed = rounded_up_grade(today)
    assert allowed == 10.0
    baseline = {"docs/user/example.md": (allowed, "Long setup sentences.")}
    rel = "docs/user/example.md"
    assert reading_problem(rel, today, baseline) is None
    assert reading_problem(rel, allowed + SLACK, baseline) is None
    worse = reading_problem(rel, allowed + SLACK + 0.1, baseline)
    assert worse is not None
    assert "worse than its baseline" in worse
    under = reading_problem(rel, 7.9, baseline)
    assert under is not None
    assert "remove it from BASELINE" in under
    assert reading_problem("docs/user/new.md", 8.0, baseline) is None
    over = reading_problem("docs/user/new.md", 8.01, baseline)
    assert over is not None
    assert "over the grade 8 ceiling" in over
    for path, (limit, reason) in BASELINE.items():
        assert limit >= CEILING
        assert "\n" not in reason and reason.strip()
        assert path


def test_failure_report_prints_every_score() -> None:
    rows = [("FAMILY_QUICK_START.md", 3.25), ("docs/user/hard.md", 9.5)]
    text = format_report(rows, problems_for(rows))
    assert text.splitlines()[0] == "FAMILY_QUICK_START.md: 3.25"
    assert "docs/user/hard.md: 9.50" in text
    assert "docs/user/hard.md scores 9.50, over the grade 8 ceiling" in text


def test_new_user_page_is_picked_up(tmp_path: Path) -> None:
    user = tmp_path / "docs" / "user"
    user.mkdir(parents=True)
    (user / "fresh-page.md").write_text(JARGON + "\n", encoding="utf-8")
    (user / "easy-page.md").write_text(PLAIN + "\n", encoding="utf-8")
    (tmp_path / "FAMILY_QUICK_START.md").write_text(PLAIN + "\n", encoding="utf-8")
    (tmp_path / "docs" / "USER_GUIDE.md").write_text(PLAIN + "\n", encoding="utf-8")
    rows = page_scores(tmp_path)
    scores = dict(rows)
    assert "docs/user/fresh-page.md" in scores
    assert "docs/user/easy-page.md" in scores
    assert scores["docs/user/fresh-page.md"] > CEILING
    assert scores["docs/user/easy-page.md"] <= CEILING
    report = format_report(rows, problems_for(rows))
    for rel, _grade in rows:
        assert f"{rel}:" in report
    assert "fresh-page.md scores" in report
    assert "easy-page.md scores" not in report


def test_live_user_pages_stay_readable() -> None:
    rows = page_scores(ROOT)
    rels = {rel for rel, _grade in rows}
    assert "FAMILY_QUICK_START.md" in rels
    assert "docs/USER_GUIDE.md" in rels
    for path in (ROOT / "docs" / "user").glob("*.md"):
        assert f"docs/user/{path.name}" in rels
    problems = problems_for(rows)
    if problems:
        pytest.fail(format_report(rows, problems))
