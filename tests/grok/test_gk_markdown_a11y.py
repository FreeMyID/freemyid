"""Offline accessibility guard for Markdown a user or helper reads.

``tests/codex/test_cx_app_a11y_sweep.py`` checks app screens, not docs. This file
does not repeat that sweep. It also does not repeat the copilot guards
``tests/copilot/test_cp_doc_links.py`` (link targets resolve),
``tests/copilot/test_cp_user_docs_reachable.py`` (a page is linked), or
``tests/copilot/test_cp_wording_guard.py`` (banned wording). The gap is the
accessibility of the Markdown itself: exactly one ``# `` title, heading levels
that never skip, link text other than "here", "click here", "this", or "link",
a header row and separator on every pipe table, no all-caps line longer than
three words, and no emoji used as the only signal of meaning.

Fenced code blocks and HTML comments are ignored. Inline code is code, so it is
not read as a heading, link, table, shout, or emoji signal. A problem in a
current doc is a strict xfail; this work order does not edit those docs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pytest

# tests/grok/this_file.py -> parents[2] is the worktree root.
ROOT = Path(__file__).resolve().parents[2]

RULE_TITLE = "single_title"
RULE_SKIP = "heading_skip"
RULE_LINK = "link_text"
RULE_TABLE = "table_shape"
RULE_CAPS = "all_caps"
RULE_EMOJI = "emoji_only"
RULES = (RULE_TITLE, RULE_SKIP, RULE_LINK, RULE_TABLE, RULE_CAPS, RULE_EMOJI)

_BAD_LINK = frozenset({"here", "click here", "this", "link"})
_ATX = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*))?$")
_FENCE_OPEN = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
_FENCE_CLOSE = {
    "`": re.compile(r"^ {0,3}(`{3,})\s*$"),
    "~": re.compile(r"^ {0,3}(~{3,})\s*$"),
}
_SEP_CELL = r":?-{3,}:?"
_SEPARATOR = re.compile(rf"^\s*\|?\s*{_SEP_CELL}\s*(?:\|\s*{_SEP_CELL}\s*)*\|?\s*$")
_INLINE = re.compile(r"(?<!!)\[([^\]\n]+)\]\(([^)\n]*)\)")
_REF = re.compile(r"(?<!!)\[([^\]\n]+)\]\[([^\]\n]*)\]")
_SHORT = re.compile(r"(?<!!)\[([^\]\n]+)\](?![(\[])")
_HTML_A = re.compile(r"(?i)<a\b[^>]*>(.*?)</a>")
_DEF = re.compile(r"^ {0,3}\[([^\]\n]+)\]:")
_EMOJI_BASE = re.compile(
    "["
    "\U0001f1e6-\U0001f1ff"
    "\U0001f300-\U0001faff"
    "\u2600-\u26ff"
    "\u2700-\u27bf"
    "\u2b05-\u2b07"
    "\u2b1b\u2b1c\u2b50\u2b55"
    "]"
)
_EMOJI_CHARS = re.compile(
    "["
    "\U0001f1e6-\U0001f1ff"
    "\U0001f300-\U0001faff"
    "\u2600-\u26ff"
    "\u2700-\u27bf"
    "\u2b05-\u2b07"
    "\u2b1b\u2b1c\u2b50\u2b55"
    "\ufe0f\u200d\u20e3"
    "]+"
)

# file, rule -> reason. Strict xfail: a later doc fix must drop the marker.
KNOWN: dict[tuple[str, str], str] = {
    ("docs/user/GLOSSARY.md", RULE_SKIP): (
        "docs/user/GLOSSARY.md:12 jumps from a level-1 title to a level-3 heading "
        "with no level-2 heading between them. This work order does not edit docs."
    ),
}

_EXPECTED_DOCS = frozenset(
    {
        "docs/user/GLOSSARY.md",
        "docs/user/HELPING.md",
        "docs/user/INSTALL.md",
        "docs/user/mail-gmail.md",
        "docs/user/mail-other.md",
        "docs/user/mail-proton.md",
        "docs/user/troubleshooting.md",
        "FAMILY_QUICK_START.md",
        "docs/USER_GUIDE.md",
        "docs/CLI.md",
        "distro/aur/README.md",
        "distro/flatpak/README.md",
        "distro/homebrew/README.md",
        "distro/nix/README.md",
        "distro/scoop/README.md",
        "distro/winget/README.md",
    }
)


@dataclass(frozen=True)
class Finding:
    rule: str
    line: int
    detail: str


def _strip_comments(line: str) -> tuple[str, bool]:
    """Drop HTML comments. The bool is true when a comment runs past this line."""
    parts: list[str] = []
    index = 0
    spans = _code_ranges(line)
    while True:
        start = line.find("<!--", index)
        while start != -1 and _inside(start, spans):
            start = line.find("<!--", start + 4)
        if start == -1:
            parts.append(line[index:])
            return "".join(parts), False
        parts.append(line[index:start])
        end = line.find("-->", start + 4)
        if end == -1:
            return "".join(parts), True
        index = end + 3


def _fence_opens(line: str) -> tuple[str, int] | None:
    match = _FENCE_OPEN.match(line)
    if match is None:
        return None
    marker = match.group(2)
    if marker.startswith("`") and "`" in match.group(3):
        return None
    return marker[0], len(marker)


def _fence_closes(line: str, fence: tuple[str, int]) -> bool:
    char, length = fence
    match = _FENCE_CLOSE[char].match(line)
    return match is not None and len(match.group(1)) >= length


def _visible_lines(text: str) -> list[tuple[int, str]]:
    """Lines a reader sees: fenced code and HTML comments removed."""
    visible: list[tuple[int, str]] = []
    fence: tuple[str, int] | None = None
    in_comment = False
    for lineno, raw in enumerate(text.splitlines(), 1):
        if fence is not None:
            if _fence_closes(raw, fence):
                fence = None
            continue
        line = raw
        if in_comment:
            end = line.find("-->")
            if end == -1:
                continue
            line = line[end + 3 :]
            in_comment = False
        line, in_comment = _strip_comments(line)
        opener = _fence_opens(line)
        if opener is not None:
            fence = opener
            continue
        visible.append((lineno, line))
    return visible


def _code_ranges(line: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    index = 0
    size = len(line)
    while index < size:
        if line[index] == "\\" and index + 1 < size:
            index += 2
            continue
        if line[index] != "`":
            index += 1
            continue
        end_tick = index
        while end_tick < size and line[end_tick] == "`":
            end_tick += 1
        ticks = end_tick - index
        close = line.find("`" * ticks, end_tick)
        if close == -1:
            break
        ranges.append((index, close + ticks))
        index = close + ticks
    return ranges


def _strip_code(line: str) -> str:
    kept: list[str] = []
    index = 0
    for start, stop in _code_ranges(line):
        kept.append(line[index:start])
        kept.append(" ")
        index = stop
    kept.append(line[index:])
    return "".join(kept)


def _inside(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= pos < stop for start, stop in spans)


def _ref_key(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _link_name(text: str) -> str:
    text = re.sub(r"<[^>]*>", "", text)
    text = text.replace("\\", "")
    text = re.sub(r"[*_~`]", "", text)
    text = re.sub(r"\s+", " ", text).strip().casefold()
    return text.strip("\"'`.,;:!?()[]{}")


def _without_definition(line: str) -> str:
    match = _DEF.match(line)
    if match is None:
        return line
    return (" " * match.end()) + line[match.end() :]


def _definitions(lines: list[tuple[int, str]]) -> set[str]:
    found: set[str] = set()
    for _, text in lines:
        match = _DEF.match(_strip_code(text))
        if match is not None:
            found.add(_ref_key(match.group(1)))
    return found


def _link_texts(line: str, definitions: set[str]) -> list[str]:
    spans = _code_ranges(line)
    texts: list[str] = []
    taken: list[tuple[int, int]] = []

    def accept(match: re.Match[str]) -> None:
        if _inside(match.start(), spans) or _inside(match.start(), taken):
            return
        texts.append(match.group(1))
        taken.append((match.start(), match.end()))

    for match in _INLINE.finditer(line):
        accept(match)
    for match in _REF.finditer(line):
        accept(match)
    for match in _HTML_A.finditer(line):
        accept(match)
    for match in _SHORT.finditer(_without_definition(line)):
        if _inside(match.start(), spans) or _inside(match.start(), taken):
            continue
        if _ref_key(match.group(1)) not in definitions:
            continue
        texts.append(match.group(1))
    return texts


def _headings(lines: list[tuple[int, str]]) -> list[tuple[int, int]]:
    found: list[tuple[int, int]] = []
    for lineno, text in lines:
        match = _ATX.match(text)
        if match is not None:
            found.append((lineno, len(match.group(1))))
    return found


def _title_findings(lines: list[tuple[int, str]]) -> list[Finding]:
    titles = [lineno for lineno, level in _headings(lines) if level == 1]
    if not titles:
        return [Finding(RULE_TITLE, 1, "no `# ` title")]
    if len(titles) == 1:
        return []
    detail = f"expected exactly one `# ` title, found {len(titles)}"
    return [Finding(RULE_TITLE, lineno, detail) for lineno in titles]


def _skip_findings(lines: list[tuple[int, str]]) -> list[Finding]:
    found: list[Finding] = []
    previous: int | None = None
    for lineno, level in _headings(lines):
        if previous is not None and level > previous + 1:
            found.append(
                Finding(
                    RULE_SKIP,
                    lineno,
                    f"level {level} follows level {previous} and skips level {previous + 1}",
                )
            )
        previous = level
    return found


def _link_findings(lines: list[tuple[int, str]], definitions: set[str]) -> list[Finding]:
    found: list[Finding] = []
    for lineno, text in lines:
        for label in _link_texts(text, definitions):
            name = _link_name(label)
            if name in _BAD_LINK:
                found.append(Finding(RULE_LINK, lineno, f"link text is {name!r}"))
    return found


def _table_text(line: str) -> str:
    return _strip_code(line).strip()


def _is_separator(text: str) -> bool:
    return "|" in text and _SEPARATOR.match(text) is not None


def _is_table_line(line: str) -> bool:
    return _table_text(line).startswith("|")


def _one_table(rows: list[tuple[int, str]]) -> list[Finding]:
    separators = [index for index, (_, text) in enumerate(rows) if _is_separator(text)]
    if not separators:
        return [Finding(RULE_TABLE, rows[0][0], "table has no separator row")]
    if separators[0] == 0:
        return [
            Finding(RULE_TABLE, rows[0][0], "table has no header row before the separator")
        ]
    if separators[0] != 1:
        return [
            Finding(
                RULE_TABLE,
                rows[separators[0]][0],
                "separator is not the row immediately after the header",
            )
        ]
    return []


def _table_findings(lines: list[tuple[int, str]]) -> list[Finding]:
    found: list[Finding] = []
    block: list[tuple[int, str]] = []
    for lineno, text in lines:
        if _is_table_line(text):
            block.append((lineno, _table_text(text)))
            continue
        if block:
            found.extend(_one_table(block))
            block = []
    if block:
        found.extend(_one_table(block))
    return found


def _caps_findings(lines: list[tuple[int, str]]) -> list[Finding]:
    found: list[Finding] = []
    for lineno, text in lines:
        visible = _strip_code(text)
        letters = [char for char in visible if char.isalpha()]
        if not letters or any(char.islower() for char in letters):
            continue
        words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", visible)
        if len(words) > 3:
            found.append(Finding(RULE_CAPS, lineno, f"all-caps line has {len(words)} words"))
    return found


def _prose(text: str) -> str:
    """Link and anchor labels only, so a URL is not treated as words."""
    text = _HTML_A.sub(r"\1", text)
    text = _INLINE.sub(r"\1", text)
    return _REF.sub(r"\1", text)


def _emoji_only(text: str) -> bool:
    if _EMOJI_BASE.search(text) is None:
        return False
    kept = _EMOJI_CHARS.sub("", text)
    return re.search(r"[A-Za-z]", kept) is None


def _cells(text: str) -> list[str]:
    parts = text.split("|")
    if text.startswith("|"):
        parts = parts[1:]
    if text.endswith("|") and parts:
        parts = parts[:-1]
    return [part.strip() for part in parts]


def _emoji_findings(lines: list[tuple[int, str]], definitions: set[str]) -> list[Finding]:
    found: list[Finding] = []
    for lineno, text in lines:
        if _is_table_line(text):
            cells = _cells(_table_text(text))
            if any(_emoji_only(_prose(cell)) for cell in cells):
                found.append(
                    Finding(RULE_EMOJI, lineno, "emoji is the only signal in a table cell")
                )
            continue
        if _emoji_only(_prose(_strip_code(text))):
            found.append(Finding(RULE_EMOJI, lineno, "emoji is the only signal of meaning"))
            continue
        labels = _link_texts(text, definitions)
        if any(_emoji_only(_prose(label)) for label in labels):
            found.append(Finding(RULE_EMOJI, lineno, "emoji is the only signal in link text"))
    return found


def audit(path: Path) -> list[Finding]:
    """Accessibility findings for one Markdown file. Empty means the file passed."""
    lines = _visible_lines(path.read_text(encoding="utf-8"))
    definitions = _definitions(lines)
    found = [
        *_title_findings(lines),
        *_skip_findings(lines),
        *_link_findings(lines, definitions),
        *_table_findings(lines),
        *_caps_findings(lines),
        *_emoji_findings(lines, definitions),
    ]
    return sorted(found, key=lambda item: (item.line, item.rule, item.detail))


def _hits(path: Path, rule: str) -> list[Finding]:
    return [item for item in audit(path) if item.rule == rule]


def _doc_paths() -> list[Path]:
    found = [path for path in (ROOT / "docs" / "user").rglob("*.md") if path.is_file()]
    found.extend(
        ROOT / rel
        for rel in ("FAMILY_QUICK_START.md", "docs/USER_GUIDE.md", "docs/CLI.md")
    )
    found.extend(path for path in (ROOT / "distro").rglob("README.md") if path.is_file())
    unique = {path.resolve(): path for path in found}
    return sorted(unique.values(), key=lambda path: path.relative_to(ROOT).as_posix())


def _cases() -> list[pytest.ParameterSet]:
    params: list[pytest.ParameterSet] = []
    for path in _doc_paths():
        rel = path.relative_to(ROOT).as_posix()
        for rule in RULES:
            reason = KNOWN.get((rel, rule))
            if reason is None:
                params.append(pytest.param(rel, rule, id=f"{rel}:{rule}"))
                continue
            params.append(
                pytest.param(
                    rel,
                    rule,
                    id=f"{rel}:{rule}",
                    marks=pytest.mark.xfail(
                        strict=True, reason=f"WO-325 (freemyid-pm#245) doc not fixed yet: {reason}"
                    ),
                )
            )
    return params


def _write(folder: Path, name: str, lines: list[str]) -> Path:
    path = folder / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_scan_covers_the_user_facing_set() -> None:
    rels = {path.relative_to(ROOT).as_posix() for path in _doc_paths()}
    missing = _EXPECTED_DOCS - rels
    assert not missing, f"scan missed {sorted(missing)}"
    for rel in _EXPECTED_DOCS:
        assert (ROOT / rel).is_file(), rel


@pytest.mark.parametrize(("rel_path", "rule"), _cases())
def test_user_markdown_follows_one_a11y_rule(rel_path: str, rule: str) -> None:
    found = _hits(ROOT / rel_path, rule)
    message = [f"{rel_path}:{item.line}: {item.detail}" for item in found]
    assert found == [], message


def test_single_title_flags_and_passes(tmp_path: Path) -> None:
    missing = _write(tmp_path, "missing.md", ["## Section only", "", "No title."])
    extra = _write(tmp_path, "extra.md", ["# First", "", "# Second"])
    good = _write(
        tmp_path,
        "good.md",
        [
            "<!--",
            "# Hidden",
            "-->",
            "```",
            "# Hidden",
            "```",
            "# Only title #",
            "",
            "## Section",
        ],
    )
    assert _hits(missing, RULE_TITLE) == [Finding(RULE_TITLE, 1, "no `# ` title")]
    assert _hits(extra, RULE_TITLE) == [
        Finding(RULE_TITLE, 1, "expected exactly one `# ` title, found 2"),
        Finding(RULE_TITLE, 3, "expected exactly one `# ` title, found 2"),
    ]
    assert _hits(good, RULE_TITLE) == []


def test_heading_skip_flags_and_passes(tmp_path: Path) -> None:
    bad = _write(
        tmp_path,
        "bad.md",
        [
            "# Title",
            "",
            "### Too deep",
            "",
            "## Section",
            "",
            "#### Also too deep",
        ],
    )
    good = _write(
        tmp_path,
        "good.md",
        [
            "# Title",
            "",
            "## Section",
            "",
            "### Detail",
            "",
            "## Again",
            "<!--",
            "#### Hidden",
            "-->",
            "```",
            "#### Hidden",
            "```",
        ],
    )
    assert _hits(bad, RULE_SKIP) == [
        Finding(RULE_SKIP, 3, "level 3 follows level 1 and skips level 2"),
        Finding(RULE_SKIP, 7, "level 4 follows level 2 and skips level 3"),
    ]
    assert _hits(good, RULE_SKIP) == []


def test_link_text_flags_and_passes(tmp_path: Path) -> None:
    bad = _write(
        tmp_path,
        "bad.md",
        [
            "# Title",
            "",
            "Read [here](https://example.invalid/a).",
            "Read [Click Here](https://example.invalid/b).",
            "Read [this](https://example.invalid/c).",
            "Read [link](https://example.invalid/d).",
            "See [here][] now.",
            "See [this] for notes.",
            "",
            "[this]: https://example.invalid/notes",
            'Read <a href="https://example.invalid/e">LINK</a>.',
        ],
    )
    good = _write(
        tmp_path,
        "good.md",
        [
            "# Title",
            "",
            "Read [the install steps](https://example.invalid/install).",
            "Read [this page](https://example.invalid/page).",
            "See [the notes][notes].",
            "",
            '[notes]: https://example.invalid/notes "here"',
            "",
            "Code: `[here](https://example.invalid/a)`.",
            "<!-- [click here](https://example.invalid/a) -->",
            "```",
            "[link](https://example.invalid/a)",
            "```",
        ],
    )
    assert _hits(bad, RULE_LINK) == [
        Finding(RULE_LINK, 3, "link text is 'here'"),
        Finding(RULE_LINK, 4, "link text is 'click here'"),
        Finding(RULE_LINK, 5, "link text is 'this'"),
        Finding(RULE_LINK, 6, "link text is 'link'"),
        Finding(RULE_LINK, 7, "link text is 'here'"),
        Finding(RULE_LINK, 8, "link text is 'this'"),
        Finding(RULE_LINK, 11, "link text is 'link'"),
    ]
    assert _hits(good, RULE_LINK) == []


def test_table_shape_flags_and_passes(tmp_path: Path) -> None:
    bad = _write(
        tmp_path,
        "bad.md",
        [
            "# Title",
            "",
            "| Name | State |",
            "| Jane | confirmed |",
            "",
            "| --- | --- |",
            "| Jane | confirmed |",
            "",
            "| Name | State |",
            "| Jane | confirmed |",
            "| --- | --- |",
        ],
    )
    good = _write(
        tmp_path,
        "good.md",
        [
            "# Title",
            "",
            "| Name | State |",
            "| --- | --- |",
            "| Jane Q Testperson | confirmed |",
            "",
            "| Step |",
            "| :--- |",
            "| Install |",
            "",
            "| Code | Meaning |",
            "|---|---|",
            "| 0 | OK | |",
            "",
            "Use a | b in prose.",
            "   ```",
            "   | No | Header |",
            "   | still | bad |",
            "   ```",
            "<!-- | No | Header | -->",
        ],
    )
    assert _hits(bad, RULE_TABLE) == [
        Finding(RULE_TABLE, 3, "table has no separator row"),
        Finding(RULE_TABLE, 6, "table has no header row before the separator"),
        Finding(RULE_TABLE, 11, "separator is not the row immediately after the header"),
    ]
    assert _hits(good, RULE_TABLE) == []


def test_all_caps_flags_and_passes(tmp_path: Path) -> None:
    bad = _write(
        tmp_path,
        "bad.md",
        [
            "# Title",
            "",
            "DO NOT SEND THIS",
            "WARNING: DO NOT SEND THIS",
        ],
    )
    good = _write(
        tmp_path,
        "good.md",
        [
            "# Title",
            "",
            "DO NOT SEND",
            "Please DO NOT SEND THIS today.",
            "| Code | Meaning |",
            "| --- | --- |",
            "| 0 | OK | |",
            "`WARNING DO NOT SEND THIS FILE`",
            "```",
            "WARNING DO NOT SEND THIS FILE",
            "```",
            "<!-- WARNING DO NOT SEND THIS FILE -->",
        ],
    )
    assert _hits(bad, RULE_CAPS) == [
        Finding(RULE_CAPS, 3, "all-caps line has 4 words"),
        Finding(RULE_CAPS, 4, "all-caps line has 5 words"),
    ]
    assert _hits(good, RULE_CAPS) == []


def test_emoji_only_flags_and_passes(tmp_path: Path) -> None:
    bad = _write(
        tmp_path,
        "bad.md",
        [
            "# Title",
            "",
            "✅",
            "⚠️",
            "",
            "| Step | State |",
            "| --- | --- |",
            "| Mail | ✅ |",
            "",
            "Read [✅](https://example.invalid/status) now.",
        ],
    )
    good = _write(
        tmp_path,
        "good.md",
        [
            "# Title",
            "",
            "✅ Done",
            "",
            "| Step | State |",
            "| --- | --- |",
            "| Mail | ✅ done |",
            "",
            "Status is [confirmed ✅](https://example.invalid/status).",
            "`✅`",
            "```",
            "✅",
            "```",
            "<!-- ✅ -->",
        ],
    )
    assert _hits(bad, RULE_EMOJI) == [
        Finding(RULE_EMOJI, 3, "emoji is the only signal of meaning"),
        Finding(RULE_EMOJI, 4, "emoji is the only signal of meaning"),
        Finding(RULE_EMOJI, 8, "emoji is the only signal in a table cell"),
        Finding(RULE_EMOJI, 10, "emoji is the only signal in link text"),
    ]
    assert _hits(good, RULE_EMOJI) == []


def test_comment_opener_inside_inline_code_does_not_hide_later_lines(tmp_path: Path) -> None:
    page = tmp_path / "page.md"
    page.write_text(
        "# Title\n\nUse `<!--` to open a comment.\n\n[here](https://example.invalid/a)\n",
        encoding="utf-8",
    )
    assert _hits(page, RULE_LINK) == [Finding(RULE_LINK, 5, "link text is 'here'")]
