#!/usr/bin/env python3
"""Turn CodeRabbit's PR review comments into a triage checklist for the in-house team.

    tools/coderabbit_findings.py 61            # one PR
    tools/coderabbit_findings.py 55 57 60 61   # several PRs
    tools/coderabbit_findings.py --open        # every open PR
    tools/coderabbit_findings.py --open --out docs/reviews/coderabbit-2026-11-08.md

Every comment becomes one checklist row: severity, file:line, title and PR link. Rows with the
same file, line and title are merged, because CodeRabbit repeats findings across incremental
reviews. The in-house reviewer then marks each row VALID (fix with a test), ALREADY FIXED or
INVALID (why) (docs/SDLC.md, "Review findings"). CodeRabbit is advice only: qa-security
and the full test run remain the merge gate.

Stdlib only. gh is called with argument lists (never shell=True). Read-only: it never posts.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field

REPO = "FreeMyID/freemyid"
# Exact app login only: any GitHub user can name themselves "coderabbit-something", but the
# "[bot]" suffix is reserved for GitHub Apps, so this is the one identity we trust.
BOT_LOGIN = "coderabbitai[bot]"
SEVERITIES = ("Critical", "Major", "Minor", "Nitpick")
_SEV = re.compile(r"\*\*(?:<picture>.*?</picture>\s*)?(Critical|Major|Minor|Nitpick)\*\*", re.DOTALL)
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_TITLE = re.compile(r"^\*\*([^*\n<][^*\n]{2,200})\*\*\s*$", re.MULTILINE)


@dataclass
class Finding:
    path: str
    line: int | None
    severity: str
    title: str
    prs: list[int] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)

    @property
    def key(self) -> tuple[str, int | None, str]:
        return (self.path, self.line, self.title.lower())


_DETAILS = re.compile(r"<details>(?:(?!<details>).)*?</details>", re.DOTALL)


def _strip_details(body: str) -> str:
    """Drop every collapsed <details> block (innermost first), wherever it sits."""
    prev = None
    while prev != body:
        prev, body = body, _DETAILS.sub("", body)
    return body.split("<details>")[0]  # an unclosed block hides the rest


def parse_comment(c: dict, pr: int) -> Finding | None:
    """One CodeRabbit inline comment -> Finding (None for non-bot or empty comments)."""
    if (c.get("user") or {}).get("login") != BOT_LOGIN:
        return None
    body = _strip_details(_COMMENT.sub("", c.get("body") or ""))
    m = _SEV.search(body)
    sev = m.group(1) if m else "Unrated"
    titles = [t.strip() for t in _TITLE.findall(body) if not _SEV.fullmatch(f"**{t.strip()}**")]
    plain = [ln.strip() for ln in body.splitlines()
             if ln.strip() and not ln.lstrip().startswith(("<", "**", ">", "_"))]
    title = titles[0] if titles else (plain[0][:120] if plain else "(no title)")
    line = c.get("line") or c.get("original_line")
    return Finding(c.get("path", "?"), line, sev, title, [pr], [c.get("html_url", "")])


_RANK = {s: i for i, s in enumerate(SEVERITIES)}


def merge(findings: list[Finding]) -> list[Finding]:
    out: dict[tuple, Finding] = {}
    for f in findings:
        if f.key in out:
            g = out[f.key]
            g.prs += [p for p in f.prs if p not in g.prs]
            g.urls += [u for u in f.urls if u not in g.urls]
            if _RANK.get(f.severity, 9) < _RANK.get(g.severity, 9):
                g.severity = f.severity  # an incremental review escalated it: keep the highest
        else:
            out[f.key] = f
    return sorted(out.values(), key=lambda f: (_RANK.get(f.severity, 9), f.path, f.line or 0))


def render(findings: list[Finding], prs: list[int]) -> str:
    counts = {s: sum(f.severity == s for f in findings) for s in (*SEVERITIES, "Unrated")}
    head = ", ".join(f"{n} {s}" for s, n in counts.items() if n)
    lines = [
        f"# CodeRabbit findings: PR {', '.join('#' + str(p) for p in prs) or '(none)'}",
        "",
        (f"{len(findings)} unique ({head or 'none'}). Disposition per row: VALID (fix + test, "
         "commit) / ALREADY FIXED (commit) / INVALID (why)."),
        "",
        "| # | Severity | Where | Finding | PRs | Disposition |",
        "|---|---|---|---|---|---|",
    ]
    for i, f in enumerate(findings, 1):
        where = f"`{f.path}:{f.line}`" if f.line else f"`{f.path}`"
        link = f.urls[0] if f.urls and f.urls[0] else ""
        title = f.title.replace("|", "\\|")
        title = f"[{title}]({link})" if link else title
        lines.append(f"| {i} | {f.severity} | {where} | {title} | "
                     f"{' '.join('#' + str(p) for p in f.prs)} | |")
    return "\n".join(lines) + "\n"


def _gh(args: list[str]) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def _pages(endpoint: str) -> list[dict]:
    """Every item of a paginated list endpoint. --slurp wraps the pages in one JSON array
    ([[page1...], [page2...]]), so the text is parsed as-is and never edited."""
    raw = _gh(["api", "--paginate", "--slurp", endpoint])
    return [item for page in (json.loads(raw) if raw.strip() else []) for item in page]


def fetch(pr: int, repo: str = REPO) -> list[dict]:
    return _pages(f"repos/{repo}/pulls/{pr}/comments?per_page=100")


def open_prs(repo: str = REPO) -> list[int]:
    """All open PRs, every page (gh pr list --limit is a cap, not a page size)."""
    return [p["number"] for p in _pages(f"repos/{repo}/pulls?state=open&per_page=100")]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("prs", nargs="*", type=int)
    ap.add_argument("--open", action="store_true", help="all open PRs")
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--out", help="write the checklist here instead of stdout")
    a = ap.parse_args(argv)
    prs = sorted(set(a.prs) | (set(open_prs(a.repo)) if a.open else set()))
    if not prs:
        ap.error("give PR numbers or --open")
    found = [f for pr in prs for c in fetch(pr, a.repo) if (f := parse_comment(c, pr))]
    text = render(merge(found), prs)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {a.out}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
