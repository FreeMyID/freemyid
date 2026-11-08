"""Relative links and #anchors in the user-facing docs resolve (CP-GP-08 / WO-153).

Offline: reads Markdown only. External (http/https/mailto) links are collected and listed in
the test output, never fetched. Anchors use GitHub's heading slug rules.
"""
from __future__ import annotations

import re
from functools import cache
from pathlib import Path
from urllib.parse import unquote

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOC_FILES = sorted(
    {
        ROOT / "README.md",
        ROOT / "docs" / "USER_GUIDE.md",
        ROOT / "docs" / "CLI.md",
        *(ROOT / "docs" / "user").glob("*.md"),
    }
)

FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_LINK = re.compile(r"(?<!\!)\[(?:[^\]\n]|\\\])*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
IMAGE_LINK = re.compile(r"!\[(?:[^\]\n]*)\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
REF_DEF = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*<?(\S+?)>?(?:\s+.*)?$")
HTML_ATTR = re.compile(r"""\b(?:href|src)=["']([^"']+)["']""")
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
HTML_ID = re.compile(r"""<a\s[^>]*\b(?:name|id)=["']([^"']+)["']""")
EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.IGNORECASE)


def _lines_outside_fences(path: Path) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    fenced = False
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if FENCE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            out.append((n, line))
    return out


def _strip_code_spans(line: str) -> str:
    return re.sub(r"`[^`\n]*`", "", line)


def _slug(text: str) -> str:
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[`*]|<[^>]+>", "", text).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


@cache
def _anchors(path: Path) -> frozenset[str]:
    seen: dict[str, int] = {}
    found: set[str] = set()
    for _, line in _lines_outside_fences(path):
        m = HEADING.match(line)
        if m:
            base = _slug(m.group(2))
            count = seen.get(base, 0)
            seen[base] = count + 1
            found.add(base if count == 0 else f"{base}-{count}")
        found.update(HTML_ID.findall(line))
    return frozenset(found)


def _links(path: Path) -> list[tuple[int, str]]:
    links: list[tuple[int, str]] = []
    for n, line in _lines_outside_fences(path):
        line = _strip_code_spans(line)
        for rx in (INLINE_LINK, IMAGE_LINK, HTML_ATTR):
            links.extend((n, m) for m in rx.findall(line))
        m = REF_DEF.match(line)
        if m:
            links.append((n, m.group(1)))
    return links


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _check(path: Path, line: int, target: str) -> str | None:
    """Return a problem description, or None when the link resolves (or is external)."""
    if EXTERNAL.match(target):
        return None
    ref, _, anchor = target.partition("#")
    ref = unquote(ref.partition("?")[0])
    dest = path if not ref else (ROOT / ref.lstrip("/") if ref.startswith("/") else path.parent / ref)
    where = f"{_rel(path)}:{line}"
    resolved = dest.resolve()
    if not resolved.exists():
        return f"{where}: {target!r} does not exist"
    is_md = resolved.is_file() and resolved.suffix == ".md"
    if anchor and is_md and unquote(anchor).lower() not in _anchors(resolved):
        return f"{where}: {target!r} has no matching heading in {_rel(resolved)}"
    return None


def test_doc_set_is_present() -> None:
    names = {_rel(p) for p in DOC_FILES}
    assert {"README.md", "docs/USER_GUIDE.md", "docs/CLI.md"} <= names
    assert any(n.startswith("docs/user/") for n in names)
    for p in DOC_FILES:
        assert p.is_file(), p


@pytest.mark.parametrize("doc", [pytest.param(p, id=_rel(p)) for p in DOC_FILES])
def test_relative_links_and_anchors_resolve(doc: Path) -> None:
    problems = [p for n, t in _links(doc) if (p := _check(doc, n, t))]
    assert not problems, "\n".join(problems)


def test_external_links_are_listed_not_fetched(capsys: pytest.CaptureFixture[str]) -> None:
    external = sorted(
        {
            (_rel(doc), n, t)
            for doc in DOC_FILES
            for n, t in _links(doc)
            if re.match(r"^(?:https?:)?//", t, re.IGNORECASE) or t.lower().startswith("http")
        }
    )
    with capsys.disabled():
        print(f"\n{len(external)} external link(s), not fetched:")
        for rel, n, t in external:
            print(f"  {rel}:{n}  {t}")
    assert all(t.lower().startswith(("http://", "https://", "//")) for _, _, t in external)


@pytest.mark.parametrize(
    ("heading", "slug"),
    [
        ("Getting started", "getting-started"),
        ("What's `freemyid run`?", "whats-freemyid-run"),
        ("Step 1: Gmail & more", "step-1-gmail--more"),
    ],
)
def test_slug_matches_github_rules(heading: str, slug: str) -> None:
    assert _slug(heading) == slug
