"""Link, anchor, and image checks for the Markdown the copilot link guard skips.

The guard checked is ``tests/copilot/test_cp_doc_links.py``. It covers only
``README.md``, ``docs/USER_GUIDE.md``, ``docs/CLI.md``, and top-level
``docs/user/*.md``. This module does not re-check those files. The gap is
``FAMILY_QUICK_START.md``, ``distro/**/*.md``, and any ``docs/user/**/*.md``
that sits in a subfolder.

Relative links must resolve to a file inside the repo. ``#anchors`` use the
same GitHub heading-slug rules as that copilot guard. Image references
(``![...](...)``) must point at an existing file and have non-empty alt text.
Web links (http, https, mailto) are printed and never fetched.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal, NamedTuple
from urllib.parse import unquote

import pytest

ROOT = Path(__file__).resolve().parents[2]

_FENCE_OPEN = re.compile(r"^ {0,3}(?P<mark>`{3,}|~{3,})(?P<info>.*)$")
_FENCE_CLOSE = re.compile(r"^ {0,3}(?P<mark>`{3,}|~{3,})[ \t]*$")
_DEST = r"(?:<(?P<angle>[^>\n]*)>|(?P<bare>[^)\s>]+))"
_CODE_SPAN = re.compile(r"`[^`\n]*`")
_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_HTML_ID = re.compile(r"""<a\s[^>]*\b(?:name|id)=["']([^"']+)["']""")
_TITLE = r"(?:\s+(?:\"[^\"]*\"|'[^']*'))?"
_IMAGE = re.compile(r"!\[(?P<alt>[^\]]*)\]\(\s*" + _DEST + _TITLE + r"\s*\)")
_LINK = re.compile(r"(?<!!)\[(?P<text>[^\]]*)\]\(\s*" + _DEST + _TITLE + r"\s*\)")
_REF_DEF = re.compile(
    r"^[ ]{0,3}\[[^\]]+\]:[ \t]*(?:<(?P<angle>[^>\n]*)>|(?P<bare>[^>\s]+))"
    r"(?:[ \t]+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?[ \t]*$"
)
_AUTOLINK = re.compile(r"<((?:https?://|mailto:)[^>\s]+)>", re.IGNORECASE)
_HTML_URL = re.compile(r"""\b(?:href|src)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_SCHEME = re.compile(r"^(?:[A-Za-z][A-Za-z0-9+.-]*:|//)")
_WEB = re.compile(r"^(?:https?://|mailto:)", re.IGNORECASE)


class _Hit(NamedTuple):
    """One markdown destination: line, target, kind, and alt text for images."""

    line: int
    target: str
    kind: Literal["link", "image"]
    alt: str


def _lane_markdown() -> list[Path]:
    """Grok-lane pages the copilot guard does not open."""
    user = ROOT / "docs" / "user"
    paths = [ROOT / "FAMILY_QUICK_START.md"]
    paths.extend(path for path in (ROOT / "distro").rglob("*.md") if path.is_file())
    if user.is_dir():
        paths.extend(
            path
            for path in user.rglob("*.md")
            if path.is_file() and path.parent != user
        )
    return sorted(paths, key=lambda path: path.relative_to(ROOT).as_posix())


LANE = _lane_markdown()


def _lane_id(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _dest(match: re.Match[str]) -> str:
    """The link destination, from angle brackets (spaces allowed) or bare."""
    angle = match.group("angle")
    return angle if angle is not None else match.group("bare")


def _outside_fences(path: Path) -> list[tuple[int, str]]:
    """Lines outside fenced code, using the CommonMark opening and closing rules."""
    return _outside_fences_text(path.read_text(encoding="utf-8"))


def _outside_fences_text(text: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    mark = ""
    for number, raw in enumerate(text.splitlines(), start=1):
        if mark:
            closer = _FENCE_CLOSE.match(raw)
            if closer and closer.group("mark")[0] == mark[0] and len(closer.group("mark")) >= len(mark):
                mark = ""
            continue
        opener = _FENCE_OPEN.match(raw)
        if opener and not (opener.group("mark")[0] == "`" and "`" in opener.group("info")):
            mark = opener.group("mark")
            continue
        lines.append((number, raw))
    return lines


def _heading_slug(text: str) -> str:
    """GitHub heading slug, same steps as tests/copilot/test_cp_doc_links.py."""
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[`*]|<[^>]+>", "", text).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def _heading_ids(path: Path) -> set[str]:
    seen: dict[str, int] = {}
    found: set[str] = set()
    for _number, raw in _outside_fences(path):
        match = _HEADING.match(raw)
        if match:
            base = _heading_slug(match.group(2))
            count = seen.get(base, 0)
            seen[base] = count + 1
            found.add(base if count == 0 else f"{base}-{count}")
        found.update(_HTML_ID.findall(raw))
    return found


def _note_web(target: str, line: int, webs: list[tuple[int, str]]) -> None:
    if _WEB.match(target):
        webs.append((line, target))


def _scan(path: Path) -> tuple[list[_Hit], list[tuple[int, str]]]:
    hits: list[_Hit] = []
    webs: list[tuple[int, str]] = []
    for number, raw in _outside_fences(path):
        visible = _CODE_SPAN.sub("", raw)
        for match in _IMAGE.finditer(visible):
            target = _dest(match)
            hits.append(_Hit(number, target, "image", match.group("alt")))
            _note_web(target, number, webs)
        for match in _LINK.finditer(visible):
            target = _dest(match)
            hits.append(_Hit(number, target, "link", ""))
            _note_web(target, number, webs)
        for match in _AUTOLINK.finditer(visible):
            _note_web(match.group(1), number, webs)
        for match in _HTML_URL.finditer(visible):
            target = match.group(1).strip()
            hits.append(_Hit(number, target, "link", ""))
            _note_web(target, number, webs)
        ref = _REF_DEF.match(visible)
        if ref is not None:
            target = _dest(ref)
            hits.append(_Hit(number, target, "link", ""))
            _note_web(target, number, webs)
    return hits, webs


def _web_links(path: Path) -> list[tuple[int, str]]:
    _hits, webs = _scan(path)
    return webs


def _label(path: Path, line: int, root_resolved: Path) -> str:
    resolved = path.resolve()
    try:
        shown = resolved.relative_to(root_resolved).as_posix()
    except ValueError:
        shown = path.name
    return f"{shown}:{line}"


def _anchors(path: Path, cache: dict[Path, frozenset[str]]) -> frozenset[str]:
    resolved = path.resolve()
    cached = cache.get(resolved)
    if cached is None:
        cached = frozenset(_heading_ids(resolved))
        cache[resolved] = cached
    return cached


def _issues(
    path: Path,
    root_resolved: Path,
    hit: _Hit,
    cache: dict[Path, frozenset[str]],
) -> list[str]:
    label = _label(path, hit.line, root_resolved)
    found: list[str] = []
    if hit.kind == "image" and not hit.alt.strip():
        found.append(f"{label}: image {hit.target!r} has empty alt text")
    if _SCHEME.match(hit.target):
        return found
    ref, _, anchor = hit.target.partition("#")
    ref = unquote(ref.partition("?")[0])
    if ref == "":
        dest = path
    elif ref.startswith("/"):
        dest = root_resolved.joinpath(ref.lstrip("/"))
    else:
        dest = path.parent.joinpath(ref)
    resolved = dest.resolve()
    if not resolved.is_relative_to(root_resolved):
        found.append(f"{label}: {hit.target!r} resolves outside the repo")
        return found
    if not resolved.exists():
        found.append(f"{label}: {hit.target!r} does not exist")
        return found
    if not resolved.is_file():
        found.append(f"{label}: {hit.target!r} is not a file")
        return found
    if anchor and resolved.suffix.lower() == ".md":
        known = _anchors(resolved, cache)
        if unquote(anchor).lower() not in known:
            shown = resolved.relative_to(root_resolved).as_posix()
            found.append(f"{label}: {hit.target!r} has no matching heading in {shown}")
    return found


def _problems(path: Path, root: Path) -> list[str]:
    root_resolved = root.resolve()
    cache: dict[Path, frozenset[str]] = {}
    hits, _webs = _scan(path)
    found: list[str] = []
    for hit in hits:
        found.extend(_issues(path, root_resolved, hit, cache))
    return found


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_lane_is_the_copilot_gap() -> None:
    user = ROOT / "docs" / "user"
    copilot = {
        ROOT / "README.md",
        ROOT / "docs" / "USER_GUIDE.md",
        ROOT / "docs" / "CLI.md",
        *user.glob("*.md"),
    }
    nested = {path for path in user.rglob("*.md") if path.is_file() and path.parent != user}
    distro = {path for path in (ROOT / "distro").rglob("*.md") if path.is_file()}
    quick = ROOT / "FAMILY_QUICK_START.md"
    expected = {quick, *distro, *nested}
    lane = set(LANE)
    assert quick.is_file()
    assert lane == expected
    assert lane.isdisjoint(copilot)
    assert all(path.is_file() for path in lane)
    assert all(path.parent != user for path in lane if user in path.parents)


@pytest.mark.parametrize(
    ("heading", "slug"),
    [
        ("Getting started", "getting-started"),
        ("What's `freemyid run`?", "whats-freemyid-run"),
        ("Step 1: Gmail & more", "step-1-gmail--more"),
        ("See [the guide](guide.md)", "see-the-guide"),
    ],
)
def test_heading_slug_matches_copilot_github_rules(heading: str, slug: str) -> None:
    assert _heading_slug(heading) == slug


@pytest.mark.parametrize("doc", LANE, ids=_lane_id)
def test_lane_links_anchors_and_images(doc: Path) -> None:
    assert _problems(doc, ROOT) == []


def test_web_links_are_listed_not_fetched(capsys: pytest.CaptureFixture[str]) -> None:
    listed = sorted(
        (_lane_id(doc), line, target) for doc in LANE for line, target in _web_links(doc)
    )
    with capsys.disabled():
        print(f"\n{len(listed)} web link(s) in the Grok lane, not fetched:")
        for rel, line, target in listed:
            print(f"  {rel}:{line}  {target}")
    schemes = ("http://", "https://", "mailto:")
    assert all(target.lower().startswith(schemes) for _rel, _line, target in listed)


def test_broken_link_fails(tmp_path: Path) -> None:
    page = _write(tmp_path / "page.md", "# Page\n\n[gone](missing.md)\n")
    found = _problems(page, tmp_path)
    assert len(found) == 1
    assert "missing.md" in found[0]
    assert "does not exist" in found[0]


def test_broken_anchor_fails(tmp_path: Path) -> None:
    _write(tmp_path / "guide.md", "# Real title\n")
    page = _write(tmp_path / "page.md", "# Page\n\n[bad](guide.md#no-such-heading)\n")
    found = _problems(page, tmp_path)
    assert len(found) == 1
    assert "no matching heading" in found[0]
    assert "guide.md#no-such-heading" in found[0]


def test_missing_image_fails(tmp_path: Path) -> None:
    page = _write(tmp_path / "page.md", "# Page\n\n![Install steps](missing-steps.png)\n")
    found = _problems(page, tmp_path)
    assert len(found) == 1
    assert "missing-steps.png" in found[0]
    assert "does not exist" in found[0]
    assert "empty alt" not in found[0]


def test_empty_alt_text_fails(tmp_path: Path) -> None:
    _write(tmp_path / "pic.png", "img")
    page = _write(tmp_path / "page.md", "# Page\n\n![](pic.png)\n![   ](pic.png)\n")
    found = _problems(page, tmp_path)
    assert len(found) == 2
    assert all("empty alt text" in item for item in found)
    assert all("does not exist" not in item for item in found)


def test_link_outside_the_repo_fails(tmp_path: Path) -> None:
    page = _write(tmp_path / "page.md", "# Page\n\n[out](%2e%2e/no-such-outside.md)\n")
    found = _problems(page, tmp_path)
    assert len(found) == 1
    assert "resolves outside the repo" in found[0]


def test_directory_target_fails(tmp_path: Path) -> None:
    (tmp_path / "folder").mkdir()
    page = _write(tmp_path / "page.md", "# Page\n\n[dir](folder)\n")
    found = _problems(page, tmp_path)
    assert len(found) == 1
    assert "is not a file" in found[0]


def test_good_links_anchors_images_and_web_links_pass(tmp_path: Path) -> None:
    _write(
        tmp_path / "guide.md",
        "# Notes\n\nIntro for Jane Q Testperson, Springfield IL.\n\n## Notes\n",
    )
    _write(tmp_path / "notes.txt", "not markdown\n")
    _write(tmp_path / "assets" / "steps.png", "png")
    page = _write(
        tmp_path / "sub" / "page.md",
        """# Start here

See the [guide](../guide.md#notes) and the [second notes](../guide.md#notes-1).
Back to [the top](#start-here).
Root link [guide](/guide.md?plain=1#notes).
Plain file [notes](../notes.txt) and [mark](../notes.txt#skipped).
See [more][local-guide].

![Install steps](../assets/steps.png "steps")

[site](https://example.invalid/help)
<mailto:jane.q.testperson@example.com>

```
[broken](missing.md)
![](missing.png)
```

A span `[broken](missing.md)` is not a link.

[local-guide]: ../guide.md
""",
    )
    assert _problems(page, tmp_path) == []
    targets = [target for _line, target in _web_links(page)]
    assert "https://example.invalid/help" in targets
    assert "mailto:jane.q.testperson@example.com" in targets


def test_http_https_and_mailto_are_listed_not_fetched(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    page = _write(
        tmp_path / "page.md",
        "# Page\n\n"
        "[http](http://example.invalid/a)\n"
        "[https](https://example.invalid/b)\n"
        "<mailto:jane.q.testperson@example.com>\n",
    )
    assert _problems(page, tmp_path) == []
    listed = _web_links(page)
    with capsys.disabled():
        print(f"\n{len(listed)} sample web link(s), not fetched:")
        for line, target in listed:
            print(f"  page.md:{line}  {target}")
    assert [target for _line, target in listed] == [
        "http://example.invalid/a",
        "https://example.invalid/b",
        "mailto:jane.q.testperson@example.com",
    ]


def test_fence_closes_only_on_a_matching_fence() -> None:
    text = (
        "````\n"
        "```\n"
        "[inside](missing.md)\n"
        "````\n"
        "[after](after.md)\n"
        "~~~\n"
        "```\n"
        "[tilde](missing.md)\n"
        "~~~\n"
        "[end](end.md)\n"
    )
    assert [raw for _n, raw in _outside_fences_text(text)] == ["[after](after.md)", "[end](end.md)"]


def test_unclosed_fence_hides_the_rest() -> None:
    assert _outside_fences_text("a\n```\nb\nc\n") == [(1, "a")]


def test_destinations_with_spaces_in_angle_brackets_are_checked(tmp_path: Path) -> None:
    _write(tmp_path / "my guide.md", "# Guide\n")
    _write(tmp_path / "pic one.png", "png")
    page = _write(
        tmp_path / "page.md",
        "# Page\n\n"
        "[ok](<my guide.md>)\n"
        "[bad](<no such.md>)\n"
        "![Steps](<pic one.png>)\n"
        "![Gone](<gone pic.png> \"title\")\n"
        "[ref]\n\n"
        "[ref]: <no ref.md>\n",
    )
    found = _problems(page, tmp_path)
    assert len(found) == 3, found
    joined = "\n".join(found)
    assert "no such.md" in joined and "gone pic.png" in joined and "no ref.md" in joined
