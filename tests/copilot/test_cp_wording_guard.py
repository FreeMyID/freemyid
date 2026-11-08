"""Wording and released-versus-coming guard for user-facing docs (GP-09 / WO-154).

Scans README.md, docs/USER_GUIDE.md, docs/HELPER_GUIDE.md, docs/user/**/*.md and distro/**/README.md for:
- words docs/POSITIONING.md bans ("guarantee", "erase", "100%", "never sent");
- a package channel (Homebrew, AUR, Nix, Flatpak, winget, Scoop) described as "available" while
  site_src/data/release.yaml does not list it.

A quoted example (a line that must show a banned word, for instance "never write 'guaranteed'")
is allowed when the line, or the line right above it, carries `<!-- wording-guard: quoted -->`.
Offline, read-only, no new dependencies.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
MARKER = "wording-guard: quoted"

BANNED = re.compile(
    r"\bguarantee[sd]?\b|\bguaranteeing\b|\berase[sd]?\b|\berasing\b|100\s?%|\bnever\s+sent\b",
    re.IGNORECASE,
)

CHANNELS: dict[str, re.Pattern[str]] = {
    "homebrew": re.compile(r"\bhomebrew\b|\bbrew\b", re.IGNORECASE),
    "aur": re.compile(r"\baur\b|\barch\b", re.IGNORECASE),
    "nix": re.compile(r"\bnix(?:os)?\b", re.IGNORECASE),
    "flatpak": re.compile(r"\bflatpak\b|\bflathub\b", re.IGNORECASE),
    "winget": re.compile(r"\bwinget\b", re.IGNORECASE),
    "scoop": re.compile(r"\bscoop\b", re.IGNORECASE),
}
AVAILABLE = re.compile(r"\bavailable\b", re.IGNORECASE)
# Lines that say "available" only to deny it or to define the word are fine.
NEGATED = re.compile(
    r"\bnot\b|\bnothing\b|\bno\b|\buntil\b|\bonly if\b|\bonly what\b|\bunavailable\b|\bcoming\b"
    r"|\bdraft\b|n't\b",
    re.IGNORECASE,
)


# Owner-reviewed sentences the banned-word check skips: (file, exact fragment, reason).
REVIEWED: list[tuple[str, str, str]] = [
    (
        "README.md",
        "DOB, relatives and personal emails are used only for matching and are never sent",
        "Code-backed claim (Listing.shown_fields), reviewed by the owner; not an absolute privacy promise.",
    ),
    (
        "docs/USER_GUIDE.md",
        "Birth year and relatives are never sent to a site",
        "Code-backed (submitters/base.py has no birth date or relatives field); matches /safety/ never-does list.",
    ),
]


def _doc_files() -> list[Path]:
    files = [ROOT / "README.md", ROOT / "docs/USER_GUIDE.md", ROOT / "docs/HELPER_GUIDE.md"]
    files += sorted((ROOT / "docs/user").glob("**/*.md"))
    files += sorted((ROOT / "distro").glob("**/README.md"))
    return [f for f in files if f.is_file()]


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _released_channels() -> set[str]:
    """Channels `release.yaml` lists as published (key `distro`, `channels` or `packages`)."""
    data = yaml.safe_load((ROOT / "site_src/data/release.yaml").read_text(encoding="utf-8")) or {}
    found: set[str] = set()
    for key in ("distro", "channels", "packages"):
        value = data.get(key)
        if isinstance(value, dict):
            items = [k for k, v in value.items() if v]
        elif isinstance(value, list):
            items = [str(v) for v in value]
        else:
            items = []
        found.update(i.lower() for i in items)
    return found


def _is_quoted(lines: list[str], idx: int) -> bool:
    return MARKER in lines[idx] or (idx > 0 and MARKER in lines[idx - 1])


def banned_hits(text: str, rel: str = "") -> list[tuple[int, str]]:
    lines = text.splitlines()
    skip = [frag for f, frag, _ in REVIEWED if f == rel]
    hits = []
    for i, line in enumerate(lines):
        if _is_quoted(lines, i):
            continue
        for frag in skip:
            line = line.replace(frag, "")
        for m in BANNED.finditer(line):
            hits.append((i + 1, m.group(0)))
    return hits


def channel_hits(text: str, implied: str | None, released: set[str]) -> list[tuple[int, str]]:
    lines = text.splitlines()
    hits = []
    for i, line in enumerate(lines):
        if _is_quoted(lines, i) or not AVAILABLE.search(line) or NEGATED.search(line):
            continue
        named = [n for n, p in CHANNELS.items() if p.search(line)]
        # In distro/<channel>/README.md a bare "available" is about that channel.
        for name in named or ([implied] if implied else []):
            if name not in released:
                hits.append((i + 1, name))
    return hits


def _implied_channel(path: Path) -> str | None:
    rel = _rel(path)
    if rel.startswith("distro/"):
        name = rel.split("/")[1]
        return name if name in CHANNELS else None
    return None


# --- the checkers themselves -------------------------------------------------------------------


def test_banned_words_are_caught() -> None:
    text = "We guarantee it.\nIt can erase you.\nNow 100% done.\nData is never sent."
    assert [h[0] for h in banned_hits(text)] == [1, 2, 3, 4]


def test_banned_words_ignore_lookalikes() -> None:
    assert banned_hits("A traverse of the guaranteeless eraser; 1100 items; sent never.") == []


def test_quoted_marker_allows_a_banned_word() -> None:
    same_line = f"Never write \"guaranteed\". <!-- {MARKER} -->"
    line_above = f"<!-- {MARKER} -->\nNever write \"100% removed\"."
    assert banned_hits(same_line) == []
    assert banned_hits(line_above) == []
    assert banned_hits(f"<!-- {MARKER} -->\n\nNever write \"erase\".") == [(3, "erase")]


def test_channel_available_is_caught_unless_released() -> None:
    text = "Homebrew is available now.\n| Flatpak | Available |\nWindows installer: available."
    assert channel_hits(text, None, set()) == [(1, "homebrew"), (2, "flatpak")]
    assert channel_hits(text, "flatpak", set()) == [(1, "homebrew"), (2, "flatpak"), (3, "flatpak")]
    assert channel_hits(text, None, {"homebrew"}) == [(2, "flatpak")]


def test_channel_negations_and_marker_are_allowed() -> None:
    text = (
        'Nothing here is "available" until a release is published.\n'
        "Homebrew is not available yet.\n"
        f"Winget is available. <!-- {MARKER} -->\n"
        "| Mac | Homebrew | Coming |"
    )
    assert channel_hits(text, "homebrew", set()) == []


# --- the real docs -----------------------------------------------------------------------------


def test_scanned_files_exist() -> None:
    names = {_rel(f) for f in _doc_files()}
    assert {
        "README.md",
        "docs/USER_GUIDE.md",
        "docs/HELPER_GUIDE.md",
        "docs/user/INSTALL.md",
    } <= names
    assert any(n.startswith("distro/") for n in names)


@pytest.mark.parametrize("path", _doc_files(), ids=_rel)
def test_no_banned_words(path: Path) -> None:
    hits = banned_hits(path.read_text(encoding="utf-8"), _rel(path))
    assert not hits, "\n".join(
        f"{_rel(path)}:{n}: banned word {w!r} (docs/POSITIONING.md); "
        f"if it is a quoted example add `<!-- {MARKER} -->`"
        for n, w in hits
    )


@pytest.mark.parametrize("path", _doc_files(), ids=_rel)
def test_no_unreleased_channel_called_available(path: Path) -> None:
    released = _released_channels()
    hits = channel_hits(path.read_text(encoding="utf-8"), _implied_channel(path), released)
    assert not hits, "\n".join(
        f"{_rel(path)}:{n}: {c} called available but not listed in site_src/data/release.yaml"
        for n, c in hits
    )
