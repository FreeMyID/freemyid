"""Stale claims in user-facing docs that the other wording guards do not scan (WO-305).

Scans ``docs/user/**/*.md``, ``docs/USER_GUIDE.md``, ``FAMILY_QUICK_START.md`` and
``docs/HELPER_GUIDE.md`` for:

- a first-start promise of "15 seconds" (the splash and installer now say up to a minute);
- "Coming in v0.x", "Version 0.x isn't out" and "0.x when it comes out" when that 0.x
  release is already in ``site_src/data/release.yaml``, plus a line that still names a
  different version as the one ``release.yaml`` or PyPI publishes;
- "nothing is sent" / "sends nothing".

Not duplicated here: ``tests/copilot/test_cp_wording_guard.py`` (guarantee/erase/100%/never
sent, and unreleased install channels; it does not read ``FAMILY_QUICK_START.md``),
``tests/test_web_absolute_claims.py`` and ``tests/test_web_developer_*.py`` (website only),
``tests/codex/test_cx_app_practice_wording.py`` (app strings only), and
``tests/test_wizard_desktop.py`` (splash text only).

"nothing is sent to us", "to the project", "to Free My ID", "until you click" and
"sends nothing about you" stay allowed, matching those guards. A version number by
itself stays allowed, so "in version 0.2.0 the button said Start" is not a hit.
``<!-- wording-guard: quoted -->`` on a line, or the line above it, quotes an example.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
MARKER = "wording-guard: quoted"
PUBLISHED = tuple[int, int, int]

_DOC_FILES = (
    PurePosixPath("docs/USER_GUIDE.md"),
    PurePosixPath("USER_GUIDE.md"),
    PurePosixPath("FAMILY_QUICK_START.md"),
    PurePosixPath("docs/FAMILY_QUICK_START.md"),
    PurePosixPath("docs/HELPER_GUIDE.md"),
)

_FIRST_START = re.compile(
    r"\bfirst\s+(?:start|open(?:ing|s)?|launch)\b"
    r"|\bfirst\s+time\b.{0,80}\b(?:open|opens|opening|start|starts|starting|window|app)\b"
    r"|\b(?:open|opens|opening|start|starts|starting|launch|window)\b.{0,60}\bfirst\s+time\b"
    r"|\bfree my id is starting\b|\bstarting window\b|\bafter (?:you )?install(?:ing|ed)?\b",
    re.IGNORECASE,
)
_FIFTEEN_SECONDS = re.compile(r"\b15\s+seconds\b", re.IGNORECASE)
_VER = r"(?:version\s+)?v?(0\.\d+(?:\.\d+)?)"
_COMING_IN = re.compile(rf"\bcoming\s+in\s+{_VER}\b", re.IGNORECASE)
_NOT_OUT = re.compile(
    rf"\b{_VER}\b[^.\n]{{0,50}}?(?:isn['’]t|is\s+not|\bnot)\s+out(?:\s+yet)?\b(?!\s+of\b)",
    re.IGNORECASE,
)
_NOT_FINISHED = re.compile(
    rf"\bisn['’]t\s+finished\s+until\s+{_VER}\b",
    re.IGNORECASE,
)
_COMES_OUT = re.compile(
    rf"\b{_VER}\b[^.\n]{{0,40}}?\bwhen\s+it\s+comes\s+out\b",
    re.IGNORECASE,
)
_NOTHING = re.compile(
    r"\bnothing\s+is\s+(?:actually\s+|really\s+|ever\s+)?sent\b|\bsends\s+nothing\b",
    re.IGNORECASE,
)
_ALLOWED_TAIL = re.compile(
    r"\s+(?:to\s+(?:us|the\s+project|free\s+my\s+id)\b|until\s+you\s+click\b|about\s+you\b)",
    re.IGNORECASE,
)
_PIN_ANCHOR = re.compile(
    r"release\.yaml|\bpypi\b|\blists\s+version\b|\bis\s+about\s+\d+(?:\.\d+)?\s*mb\b",
    re.IGNORECASE,
)
# "v0.2.0" inside a filename is not a token. A sentence period after "0.2.0." is.
_VERSION_TOKEN = re.compile(r"(?<![\w.])(0\.\d+(?:\.\d+)?)(?!\.\d)(?![\w])")


@dataclass(frozen=True)
class ClaimHit:
    line: int
    kind: str
    match: str


@dataclass(frozen=True)
class DocHit:
    rel: str
    line: int
    kind: str
    match: str


def _parse_version(raw: str) -> PUBLISHED:
    match = re.fullmatch(r"v?(\d+)\.(\d+)(?:\.(\d+))?", raw.strip())
    if match is None:
        raise ValueError(f"not a version: {raw}")
    patch = match.group(3)
    return (int(match.group(1)), int(match.group(2)), int(patch or 0))


def published_version(root: Path) -> PUBLISHED:
    path = root / "site_src" / "data" / "release.yaml"
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict) or "version" not in loaded:
        raise ValueError(f"{path} has no version")
    return _parse_version(str(loaded["version"]))


def _under(root: Path, rel: str) -> Path:
    return root.joinpath(*PurePosixPath(rel).parts)


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def user_doc_paths(root: Path) -> list[Path]:
    found: list[Path] = []
    user = root / "docs" / "user"
    if user.is_dir():
        found.extend(path for path in user.rglob("*.md") if path.is_file())
    for rel in _DOC_FILES:
        path = root.joinpath(*rel.parts)
        if path.is_file():
            found.append(path)
    unique = {path.resolve(): path for path in found}
    return sorted(unique.values(), key=lambda path: _rel(root, path))


def _quoted(lines: list[str], index: int) -> bool:
    if index < 0 or index >= len(lines):
        return False
    return MARKER in lines[index] or (index > 0 and MARKER in lines[index - 1])


def _window(lines: list[str], index: int) -> str:
    chunk = lines[max(0, index - 2): index + 3]
    return " ".join(chunk)


def _shipped_phrase(pattern: re.Pattern[str], line: str, published: PUBLISHED) -> list[str]:
    found: list[str] = []
    for match in pattern.finditer(line):
        version = match.group(1)
        if _parse_version(version) <= published:
            found.append(match.group(0))
    return found


def claim_hits(text: str, published: PUBLISHED) -> list[ClaimHit]:
    """Stale claims in one document. ``published`` is the release.yaml version."""
    lines = text.splitlines()
    hits: list[ClaimHit] = []
    for index, line in enumerate(lines):
        if _quoted(lines, index):
            continue
        number = index + 1
        if _FIFTEEN_SECONDS.search(line) and _FIRST_START.search(_window(lines, index)):
            hits.append(ClaimHit(number, "first_start_15s", "15 seconds"))
        for pattern in (_COMING_IN, _NOT_OUT, _NOT_FINISHED, _COMES_OUT):
            hits.extend(
                ClaimHit(number, "coming_shipped", phrase)
                for phrase in _shipped_phrase(pattern, line, published)
            )
        for match in _NOTHING.finditer(line):
            if _ALLOWED_TAIL.match(line, match.end()):
                continue
            hits.append(ClaimHit(number, "nothing_sent", match.group(0)))
        hits.extend(_pin_hits(lines, index, published))
    return hits


def _pin_hits(lines: list[str], index: int, published: PUBLISHED) -> list[ClaimHit]:
    """A line that names some other version as the published release.yaml or PyPI one."""
    if _quoted(lines, index):
        return []
    previous = lines[index - 1] if index and not _quoted(lines, index - 1) else ""
    blob = f"{previous} {lines[index]}"
    if not _PIN_ANCHOR.search(blob):
        return []
    versions = [match.group(1) for match in _VERSION_TOKEN.finditer(blob)]
    if any(_parse_version(version) == published for version in versions):
        return []
    hits: list[ClaimHit] = []
    for match in _VERSION_TOKEN.finditer(lines[index]):
        found = match.group(1)
        if _parse_version(found) != published:
            hits.append(ClaimHit(index + 1, "version_pin", found))
    return hits


def scan_user_docs(root: Path, published: PUBLISHED | None = None) -> list[DocHit]:
    version = published_version(root) if published is None else published
    hits: list[DocHit] = []
    for path in user_doc_paths(root):
        text = path.read_text(encoding="utf-8")
        rel = _rel(root, path)
        hits.extend(
            DocHit(rel, hit.line, hit.kind, hit.match) for hit in claim_hits(text, version)
        )
    return hits


def _write(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = _under(root, rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


_BAD_FILES = {
    "docs/USER_GUIDE.md": """\
Jane Q Testperson, Springfield IL.
The first opening can take up to 15 seconds.
Scheduler support is Coming in v0.2.
Version 0.2 isn't out yet.
Please update to 0.3 when it comes out.
While practice mode is on, nothing is actually sent.
If you misclick, nothing is sent until the next check.
Coming in v0.3.0: the Today screen.
Version 0.3 is not out yet.
The Linux app isn't finished until v0.2.
""",
    "FAMILY_QUICK_START.md": """\
It looks for listings but sends nothing.
The first time the window opens, wait 15 seconds.
""",
    "docs/HELPER_GUIDE.md": """\
Nothing is sent except in a request you approve.
Emails wait. Nothing is sent until they press OK.
""",
    "docs/user/INSTALL.md": """\
The release record is site_src/data/release.yaml. It lists version 0.2.0.
published: version 0.2.0 is on PyPI.
Version 0.2.0 is about 64.4 MB (site_src/data/release.yaml).
""",
    "docs/user/GLOSSARY.md": """\
Listed in site_src/data/release.yaml is available today: version
0.2.0 (site_src/data/release.yaml).
""",
}

_CLEAN_GUIDE = """\
The first time, Free My ID can take up to a minute to open.
Wait for the Free My ID is starting window.

In version 0.2.0 the box says Start Free My ID now.
From version 0.3 it says Open Free My ID now.
From version 0.3, a form gets only the age its own listing shows
(version 0.2.0 can still send an age worked out from the birth year).

A site has up to 45 days, then Free My ID waits another 15 days.
Some pages mention 15 seconds with no first-start promise.
Version 0.4 isn't out yet. Coming in v0.4: a Mac app.
Coming in v0.3.1 still waits on a published release.
Version 0.3.0 is out. site_src/data/release.yaml lists version 0.3.0.
The package on PyPI is version 0.3.0.

Practice mode looks for listings. No removal requests go out until you say so.
Nothing is sent to us. That download sends nothing about you.
Share this page (nothing is sent until you click).
If you press No, nothing will be sent for this listing.
It sends no removal requests.
<!-- wording-guard: quoted -->
Never write that the first opening takes 15 seconds, or Coming in v0.2, or that nothing is sent.
"""


def test_bad_fixture_flags_each_stale_claim(tmp_path: Path) -> None:
    _write(tmp_path, _BAD_FILES)
    found = {(hit.rel, hit.line, hit.kind) for hit in scan_user_docs(tmp_path, (0, 3, 0))}
    assert found == {
        ("docs/USER_GUIDE.md", 2, "first_start_15s"),
        ("docs/USER_GUIDE.md", 3, "coming_shipped"),
        ("docs/USER_GUIDE.md", 4, "coming_shipped"),
        ("docs/USER_GUIDE.md", 5, "coming_shipped"),
        ("docs/USER_GUIDE.md", 6, "nothing_sent"),
        ("docs/USER_GUIDE.md", 7, "nothing_sent"),
        ("docs/USER_GUIDE.md", 8, "coming_shipped"),
        ("docs/USER_GUIDE.md", 9, "coming_shipped"),
        ("docs/USER_GUIDE.md", 10, "coming_shipped"),
        ("FAMILY_QUICK_START.md", 1, "nothing_sent"),
        ("FAMILY_QUICK_START.md", 2, "first_start_15s"),
        ("docs/HELPER_GUIDE.md", 1, "nothing_sent"),
        ("docs/HELPER_GUIDE.md", 2, "nothing_sent"),
        ("docs/user/INSTALL.md", 1, "version_pin"),
        ("docs/user/INSTALL.md", 2, "version_pin"),
        ("docs/user/INSTALL.md", 3, "version_pin"),
        ("docs/user/GLOSSARY.md", 2, "version_pin"),
    }


def test_clean_fixture_passes(tmp_path: Path) -> None:
    _write(tmp_path, {
        "docs/USER_GUIDE.md": _CLEAN_GUIDE,
        "FAMILY_QUICK_START.md": "It runs on your computer, and nothing is sent to us.\n",
        "docs/HELPER_GUIDE.md": "No removal requests go out until you say so.\n",
        "docs/user/INSTALL.md": "site_src/data/release.yaml lists version 0.3.0.\n",
        "README.md": "The first opening takes 15 seconds. Coming in v0.2. Nothing is sent.\n",
    })
    assert scan_user_docs(tmp_path, (0, 3, 0)) == []


def test_future_version_and_allowed_privacy_lines_pass() -> None:
    text = """\
Coming in v0.9. Nothing is sent to the project.
Coming in version 0.4. Sends nothing to us.
Version 0.3.1 isn't out yet.
"""
    assert claim_hits(text, (0, 3, 0)) == []


def test_scan_reads_the_user_docs_and_skips_the_readme() -> None:
    rels = {_rel(ROOT, path) for path in user_doc_paths(ROOT)}
    assert {
        "docs/USER_GUIDE.md",
        "docs/HELPER_GUIDE.md",
        "FAMILY_QUICK_START.md",
        "docs/user/INSTALL.md",
    } <= rels
    assert "README.md" not in rels
    assert not any(rel.startswith(("web/", "src/", "distro/")) for rel in rels)


def test_family_quick_start_has_no_stale_claims() -> None:
    text = _under(ROOT, "FAMILY_QUICK_START.md").read_text(encoding="utf-8")
    assert claim_hits(text, published_version(ROOT)) == []


def test_version_comparisons_are_not_coming_or_pin_hits() -> None:
    published = published_version(ROOT)
    kept = {"coming_shipped", "version_pin", "first_start_15s"}
    for rel in ("FAMILY_QUICK_START.md", "docs/HELPER_GUIDE.md"):
        hits = claim_hits(_under(ROOT, rel).read_text(encoding="utf-8"), published)
        assert [hit for hit in hits if hit.kind in kept] == []


def test_live_docs_have_no_unlisted_stale_claims() -> None:
    found = {(hit.rel, hit.line, hit.kind) for hit in scan_user_docs(ROOT)}
    assert sorted(found - set(_KNOWN_REASONS)) == []


_KNOWN_REASONS: dict[tuple[str, int, str], str] = {
    ("docs/USER_GUIDE.md", 113, "coming_shipped"): (
        "docs/USER_GUIDE.md:113 says update to 0.3 when it comes out; "
        "site_src/data/release.yaml version is newer. "
        "The same guide at line 250 already describes 0.3 as current."
    ),
    ("docs/USER_GUIDE.md", 177, "nothing_sent"): (
        "docs/USER_GUIDE.md:177 says nothing is actually sent in practice mode. "
        "Practice mode still searches people-search sites (docs/USER_GUIDE.md:99). "
        "The app says no removal requests go out (src/freemyid/wizard/dashboard.py:131)."
    ),
    ("docs/USER_GUIDE.md", 180, "nothing_sent"): (
        "docs/USER_GUIDE.md:180 says nothing is sent until the next check. "
        "That is the unqualified phrase; the lookup has already gone out "
        "(docs/USER_GUIDE.md:99). Allowed form is about removal requests, or to us."
    ),
    ("docs/HELPER_GUIDE.md", 53, "nothing_sent"): (
        "docs/HELPER_GUIDE.md:53 says nothing is sent except in a request you approve. "
        "Name and city searches go out before any removal request (docs/USER_GUIDE.md:99)."
    ),
    ("docs/HELPER_GUIDE.md", 62, "nothing_sent"): (
        "docs/HELPER_GUIDE.md:62 says practice mode sends nothing. "
        "Searches still go out. Approved wording is no removal requests go out "
        "(src/freemyid/wizard/dashboard.py:131)."
    ),
    ("docs/HELPER_GUIDE.md", 72, "nothing_sent"): (
        "docs/HELPER_GUIDE.md:72 says nothing is sent until they press OK. "
        "Automatic sending can send without that OK; the website no longer uses this line."
    ),
    ("docs/user/GLOSSARY.md", 10, "version_pin"): (
        "docs/user/GLOSSARY.md:10 says release.yaml lists version 0.2.0. "
        "site_src/data/release.yaml version is newer."
    ),
    ("docs/user/INSTALL.md", 12, "version_pin"): (
        "docs/user/INSTALL.md:12 says release.yaml lists version 0.2.0. "
        "site_src/data/release.yaml version is newer."
    ),
    ("docs/user/INSTALL.md", 16, "version_pin"): (
        "docs/user/INSTALL.md:16 says version 0.2.0 is on PyPI. "
        "The published release record is newer, not 0.2.0."
    ),
    ("docs/user/INSTALL.md", 48, "version_pin"): (
        "docs/user/INSTALL.md:48 says Version 0.2.0 is about 64.4 MB. "
        "site_src/data/release.yaml has a newer version and size_mb."
    ),
    ("docs/user/INSTALL.md", 72, "version_pin"): (
        "docs/user/INSTALL.md:72 says version 0.2.0 is in release.yaml. "
        "That file's version is newer."
    ),
    ("docs/user/INSTALL.md", 78, "version_pin"): (
        "docs/user/INSTALL.md:78 says the command-line tool is version 0.2.0 from PyPI. "
        "The published release record is newer."
    ),
}


def _known_params() -> list[pytest.ParameterSet]:
    params: list[pytest.ParameterSet] = []
    for (rel, line, kind), reason in _KNOWN_REASONS.items():
        params.append(pytest.param(
            rel, line, kind,
            marks=pytest.mark.xfail(
                strict=True, reason=f"WO-305 (freemyid-pm#222) stale claim, fix the doc: {reason}"
            ),
            id=f"{rel}:{line}:{kind}",
        ))
    return params


@pytest.mark.parametrize(("rel", "line", "kind"), _known_params())
def test_known_stale_user_doc_claim(rel: str, line: int, kind: str) -> None:
    """Clean-state assertion. Strict xfail while this file:line is still stale."""
    text = _under(ROOT, rel).read_text(encoding="utf-8")
    hits = claim_hits(text, published_version(ROOT))
    assert not any(hit.line == line and hit.kind == kind for hit in hits)
