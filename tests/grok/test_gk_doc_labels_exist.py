"""Button and link labels quoted in user docs must exist in the wizard (WO-309).

Docs call a label a button or a link when it is in bold or quotes and the line
says button/link (``**Copy** button``, ``"…" links``), gives it as an example
(``such as **I did it**``), or introduces a list (``three buttons:``).

This is not ``tests/copilot/test_cp_source_citations.py``, which checks quoted
text on a source-citation line. Website-only labels are allowlisted. A live
gap stays a strict xfail; ``src/`` and the docs are not edited to clear it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WIZARD = ROOT / "src" / "freemyid" / "wizard"
_UI_SUFFIXES = {".py", ".js", ".html", ".css", ".svg"}

# (repo-relative path, label) -> why it is not a wizard control.
# Line numbers are not part of the key. A later edit can move the sentence.
WEBSITE_ONLY: dict[tuple[str, str], str] = {}

# Live doc/app gaps, matched by file and label, not by line number.
# A strict xfail stays until that label is gone. Removing the label makes the
# xfail disappear, so the test passes. A new missing label still fails.
KNOWN_MISMATCHES: dict[tuple[str, str], str] = {
    ("docs/USER_GUIDE.md", "confirm your request"): (
        "docs/USER_GUIDE.md:36 quotes 'confirm your request' links that sites send; "
        "that phrase is not in src/freemyid/wizard/"
    ),
}

_FENCE_OPEN = re.compile(r"^ {0,3}(?P<mark>`{3,}|~{3,})(?P<info>.*)$")
_FENCE_CLOSE = re.compile(r"^ {0,3}(?P<mark>`{3,}|~{3,})[ \t]*$")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_CODE = re.compile(r"`[^`\n]*`")
_SPAN = re.compile(
    r"\*\*(?P<bold>[^*\n]{1,80})\*\*"
    r"|\"(?P<quote>[^\"\n]{1,80})\""
    r"|“(?P<curly>[^”\n]{1,80})”"
)
_AFTER = re.compile(
    r"(?:"
    r"\*\*(?P<bold>[^*\n]{1,80})\*\*"
    r"|\"(?P<quote>[^\"\n]{1,80})\""
    r"|“(?P<curly>[^”\n]{1,80})”"
    r")\s+(?:buttons?|links?)\b",
    re.IGNORECASE,
)
_SUCH_AS = re.compile(
    r"\b(?:buttons?|links?)\b[^.\n]{0,160}?"
    r"\b(?:such as|like|called|named|labeled|labelled)\b"
    r"(?P<rest>[^.\n]*)",
    re.IGNORECASE,
)
_INTRO = re.compile(r"\b(?:buttons?|links?)\s*:\s*$", re.IGNORECASE)
_LIST_ITEM = re.compile(r"\s*[-*]\s+")
_HEADING = re.compile(r"\s*#{1,6}\s")


@dataclass(frozen=True)
class QuotedLabel:
    path: str
    line: int
    label: str


def _mask_fences(text: str) -> str:
    """Blank fenced code lines using the CommonMark opening and closing rules."""
    out: list[str] = []
    mark = ""
    for raw in text.split("\n"):
        if mark:
            closer = _FENCE_CLOSE.match(raw)
            if closer and closer.group("mark")[0] == mark[0] and len(closer.group("mark")) >= len(mark):
                mark = ""
            out.append(" " * len(raw))
            continue
        opener = _FENCE_OPEN.match(raw)
        if opener and not (opener.group("mark")[0] == "`" and "`" in opener.group("info")):
            mark = opener.group("mark")
            out.append(" " * len(raw))
            continue
        out.append(raw)
    return "\n".join(out)


def _mask(text: str) -> str:
    """Blank fenced code, HTML comments, and inline code without moving line numbers."""

    def blanks(match: re.Match[str]) -> str:
        return re.sub(r"[^\n]", " ", match.group(0))

    text = _mask_fences(text)
    text = _COMMENT.sub(blanks, text)
    return _CODE.sub(lambda match: " " * len(match.group(0)), text)


def _span_text(match: re.Match[str]) -> str:
    for name in ("bold", "quote", "curly"):
        value = match.group(name)
        if value is not None:
            return value
    raise AssertionError("span matched without text")


def _clean(label: str) -> str | None:
    label = " ".join(label.split())
    if not label or len(label) > 80 or not re.search(r"[A-Za-z0-9]", label):
        return None
    if "://" in label or label.startswith(("src/", "/")):
        return None
    return label


def _list_labels(lines: list[str], start: int) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    index = start + 1
    seen = False
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            if not seen:
                index += 1
                continue
            nxt = index + 1
            while nxt < len(lines) and not lines[nxt].strip():
                nxt += 1
            if nxt < len(lines) and _LIST_ITEM.match(lines[nxt]):
                index = nxt
                continue
            break
        if _HEADING.match(line):
            break
        if _LIST_ITEM.match(line):
            seen = True
            match = _SPAN.search(line)
            if match:
                found.append((index + 1, _span_text(match)))
            index += 1
            continue
        if seen and line[:1] in (" ", "\t"):
            index += 1
            continue
        break
    return found


def extract_labels(text: str) -> list[tuple[int, str]]:
    """(line, label) for button or link text quoted in bold or quotes."""
    lines = _mask(text).splitlines()
    found: list[tuple[int, str]] = []
    seen: set[tuple[int, str]] = set()

    def add(line_no: int, raw: str) -> None:
        label = _clean(raw)
        if label is None:
            return
        key = (line_no, label)
        if key not in seen:
            seen.add(key)
            found.append(key)

    for index, line in enumerate(lines):
        for match in _AFTER.finditer(line):
            add(index + 1, _span_text(match))
        for match in _SUCH_AS.finditer(line):
            for span in _SPAN.finditer(match.group("rest")):
                add(index + 1, _span_text(span))
        if _INTRO.search(line):
            for line_no, label in _list_labels(lines, index):
                add(line_no, label)
    return found


def label_in_ui(label: str, ui_text: str) -> bool:
    """True when ``label`` is its own phrase in wizard UI source (case-sensitive)."""
    return re.search(r"(?<!\w)" + re.escape(label) + r"(?!\w)", ui_text) is not None


def labels_missing(doc_text: str, ui_text: str) -> list[tuple[int, str]]:
    return [(line, label) for line, label in extract_labels(doc_text) if not label_in_ui(label, ui_text)]


def doc_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    root_guide = root / "USER_GUIDE.md"
    if root_guide.is_file():
        paths.append(root_guide)
    for path in (root / "docs" / "USER_GUIDE.md", root / "FAMILY_QUICK_START.md"):
        if path.is_file():
            paths.append(path)
    user = root / "docs" / "user"
    if user.is_dir():
        paths.extend(sorted(path for path in user.glob("*.md") if path.is_file()))
    return paths


def _read_wizard(wizard: Path) -> str:
    parts: list[str] = []
    if not wizard.is_dir():
        return ""
    files = sorted(
        path for path in wizard.rglob("*") if path.is_file() and path.suffix.lower() in _UI_SUFFIXES
    )
    for path in files:
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def _live_labels() -> list[QuotedLabel]:
    found: list[QuotedLabel] = []
    for path in doc_paths(ROOT):
        rel = path.relative_to(ROOT).as_posix()
        for line, label in extract_labels(path.read_text(encoding="utf-8")):
            found.append(QuotedLabel(rel, line, label))
    return found


def _param_id(hit: QuotedLabel) -> str:
    safe = hit.label.replace(" ", "_").replace("/", "-")
    return f"{hit.path}:{hit.line}:{safe}"


CORPUS = _read_wizard(WIZARD)
LIVE = _live_labels()


def _live_params() -> list[object]:
    params: list[object] = []
    for hit in LIVE:
        key = (hit.path, hit.label)
        if key in WEBSITE_ONLY:
            continue
        reason = KNOWN_MISMATCHES.get(key)
        if reason:
            params.append(
                pytest.param(hit, marks=pytest.mark.xfail(strict=True, reason=reason), id=_param_id(hit))
            )
        else:
            params.append(pytest.param(hit, id=_param_id(hit)))
    return params


def test_fixture_real_hit_passes(tmp_path: Path) -> None:
    doc = tmp_path / "guide.md"
    ui = tmp_path / "wizard" / "ui.py"
    ui.parent.mkdir(parents=True)
    doc.write_text(
        "Jane Q Testperson, Springfield IL, clicks the **Continue** button.\n",
        encoding="utf-8",
    )
    ui.write_text('<button type="submit">Continue</button>\n', encoding="utf-8")
    text = doc.read_text(encoding="utf-8")
    assert extract_labels(text) == [(1, "Continue")]
    assert labels_missing(text, ui.read_text(encoding="utf-8")) == []


def test_fixture_clean_line_passes(tmp_path: Path) -> None:
    doc = tmp_path / "guide.md"
    ui = tmp_path / "screen.html"
    doc.write_text(
        "Jane Q Testperson of Springfield IL reads **Today**. Sites send links in email.\n"
        "```\nclick the **Do not count** button\n```\n"
        "<!-- click the **Also skip** button -->\n",
        encoding="utf-8",
    )
    ui.write_text("<h1>Today</h1>\n", encoding="utf-8")
    text = doc.read_text(encoding="utf-8")
    assert extract_labels(text) == []
    assert labels_missing(text, ui.read_text(encoding="utf-8")) == []


def test_fixture_missing_label_is_reported(tmp_path: Path) -> None:
    doc = tmp_path / "guide.md"
    ui = tmp_path / "screen.py"
    doc.write_text(
        'Press the "Not in the app" button for Jane Q Testperson, Springfield IL.\n',
        encoding="utf-8",
    )
    ui.write_text("<button>Continue</button>\n", encoding="utf-8")
    text = doc.read_text(encoding="utf-8")
    assert labels_missing(text, ui.read_text(encoding="utf-8")) == [(1, "Not in the app")]


def test_doc_paths_include_named_guides_when_present(tmp_path: Path) -> None:
    for rel in (
        "USER_GUIDE.md",
        "docs/USER_GUIDE.md",
        "FAMILY_QUICK_START.md",
        "docs/user/note.md",
    ):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Click the **Go** button.\n", encoding="utf-8")
    rels = [path.relative_to(tmp_path).as_posix() for path in doc_paths(tmp_path)]
    assert rels == [
        "USER_GUIDE.md",
        "docs/USER_GUIDE.md",
        "FAMILY_QUICK_START.md",
        "docs/user/note.md",
    ]


def test_guides_quote_button_or_link_labels() -> None:
    assert LIVE, "user docs quote no button or link labels"


def test_allowlist_is_website_only_and_current() -> None:
    live = {(hit.path, hit.label) for hit in LIVE}
    assert set(WEBSITE_ONLY) <= live
    assert all(reason.strip() for reason in WEBSITE_ONLY.values())
    present = [key for key in WEBSITE_ONLY if label_in_ui(key[1], CORPUS)]
    assert present == []


def test_known_mismatches_are_still_quoted() -> None:
    live = {(hit.path, hit.label) for hit in LIVE}
    assert set(KNOWN_MISMATCHES) <= live
    assert all(".md:" in reason for reason in KNOWN_MISMATCHES.values())


@pytest.mark.parametrize("hit", _live_params())
def test_quoted_button_or_link_is_in_the_wizard(hit: QuotedLabel) -> None:
    assert label_in_ui(hit.label, CORPUS), (
        f"{hit.path}:{hit.line}: {hit.label!r} is called a button or link "
        "and is not in src/freemyid/wizard/"
    )


def test_fence_masking_follows_closing_rules() -> None:
    text = (
        "````\n"
        "```\n"
        "click the **Inside** button\n"
        "````\n"
        "click the **After** button\n"
        "~~~\n"
        "click the **Tilde** button\n"
        "```\n"
        "click the **StillTilde** button\n"
        "~~~\n"
    )
    assert [label for _line, label in extract_labels(text)] == ["After"]


def test_unclosed_fence_masks_the_rest() -> None:
    assert extract_labels("click the **A** button\n```\nclick the **B** button\n") == [(1, "A")]
