#!/usr/bin/env python3
"""Registry health check (qa-security). Meant to run weekly in CI.

Offline (default, no network at all):
  * the whole file validates against the JSON Schema + pydantic models (registry.validate_text),
    and each broker entry is also validated on its own so a failure names the broker;
  * ERROR: any URL value that is not https, a malformed opt_out_email, a domain listed twice
    in one broker, an unreadable/invalid file;
  * WARN: no source_urls (missing citation), last_verified missing or older than --max-age-days
    (default 180), the file's `updated` date that old, a domain claimed by two brokers.

Online (--online): one polite HEAD per enabled broker's opt-out page (falls back to a GET whose
body is never read when HEAD is refused). Every URL, and every redirect hop, must be https and
pass NetPolicy built from the registry under test; redirects are followed by hand (max 5) and an
off-list hop is an ERROR, never fetched. A generic User-Agent, one request at a time, and
--delay seconds (min 1) between requests. 403/429/503 are reported as "blocked, check by hand"
(WARN): this tool never retries around bot protection. --selectors also GETs (capped) pages with
declarative form steps and checks that simple selectors (#id, [name=x], tag[name=x]) appear.

Checks the sample registry, plus brokers/registry.yaml when present, unless paths are given.
Exit status: 0 healthy, 1 any ERROR (or any WARN with --strict), 2 a usage/IO problem.
`--report FILE` writes the findings as Markdown (or JSON if FILE ends in .json).
The registry holds no personal data; reports contain broker ids, fields and URLs only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from freemyid import monitor
from freemyid.monitor import Requester

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "brokers" / "registry.sample.yaml"
FULL = ROOT / "brokers" / "registry.yaml"

ERROR, WARN = "ERROR", "WARN"
MAX_AGE_DAYS = 180
USER_AGENT = "Mozilla/5.0 (compatible; registry-health)"
MAX_REDIRECTS = monitor.MAX_REDIRECTS
BLOCKED = monitor.BLOCKED

_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
EMAIL_RE = re.compile(
    r"^(?!\.)(?!.*\.\.)[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}(?<!\.)"
    rf"@{_LABEL}(?:\.{_LABEL})*\.[A-Za-z]{{2,63}}$")



@dataclass
class Finding:
    level: str
    registry: str
    broker: str
    check: str
    detail: str


def _load_raw(path: Path) -> Any:
    from freemyid.registry import _NoAliasLoader  # same loader as the app (aliases refused)
    return yaml.load(path.read_text(encoding="utf-8"), Loader=_NoAliasLoader)


def _strings(node: Any, where: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _strings(v, f"{where}.{k}" if where else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _strings(v, f"{where}[{i}]")
    elif isinstance(node, str):
        yield where, node


def check_offline(path: Path, *, today: date | None = None,
                  max_age_days: int = MAX_AGE_DAYS) -> list[Finding]:
    """Schema + content checks for one registry file. No network."""
    from freemyid.models import Broker
    from freemyid.registry import RegistryError, validate_text

    today = today or date.today()
    name = path.name
    out: list[Finding] = []

    def add(level: str, broker: str, check: str, detail: str) -> None:
        out.append(Finding(level, name, broker, check, detail))

    try:
        text = path.read_text(encoding="utf-8")
        raw = _load_raw(path)
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as e:
        add(ERROR, "-", "load", f"cannot read: {type(e).__name__}: {str(e)[:200]}")
        return out
    if not isinstance(raw, dict) or not isinstance(raw.get("brokers"), list):
        add(ERROR, "-", "schema", "top level must be a mapping with a 'brokers' list")
        return out
    try:
        validate_text(text)
    except RegistryError as e:
        msg = " ".join(ln.strip() for ln in str(e).splitlines()[:3] if ln.strip())
        add(ERROR, "-", "schema", msg[:300])

    updated = raw.get("updated")
    if isinstance(updated, date) and (today - updated).days > max_age_days:
        add(WARN, "-", "stale", f"registry 'updated' is {updated} (> {max_age_days} days)")

    owners: dict[str, list[str]] = {}
    for i, b in enumerate(raw["brokers"]):
        if not isinstance(b, dict):
            add(ERROR, f"#{i}", "schema", "broker entry is not a mapping")
            continue
        bid = str(b.get("id") or f"#{i}")
        try:
            Broker.model_validate(b)
        except ValueError as e:
            first = next((ln for ln in str(e).splitlines()[1:] if ln.strip()), str(e))
            add(ERROR, bid, "schema", first.strip()[:300])
        for where, s in _strings(b):
            if re.match(r"\s*http://", s, re.IGNORECASE):
                add(ERROR, bid, "https", f"{where} is not https: {s[:120]}")
        email = b.get("opt_out_email")
        if email is not None and (not isinstance(email, str) or not EMAIL_RE.match(email)):
            add(ERROR, bid, "email", f"opt_out_email is not a valid address: {str(email)[:80]}")
        if not b.get("source_urls"):
            add(WARN, bid, "citation", "no source_urls")
        lv = b.get("last_verified")
        if not isinstance(lv, date):
            add(WARN, bid, "stale", "no last_verified date")
        elif (today - lv).days > max_age_days:
            add(WARN, bid, "stale", f"last_verified {lv} is older than {max_age_days} days")
        doms = [str(d).lower().rstrip(".") for d in b.get("domains") or []]
        for d in sorted({d for d in doms if doms.count(d) > 1}):
            add(ERROR, bid, "duplicate_domain", f"{d} listed twice in domains")
        for d in set(doms):
            owners.setdefault(d, []).append(bid)
    for d, ids in sorted(owners.items()):
        if len(ids) > 1:
            add(WARN, ",".join(ids), "duplicate_domain", f"{d} is claimed by {len(ids)} brokers")
    return out


# --- online ------------------------------------------------------------------------------

# The fetch, redirect, allowlist and selector checks live in freemyid.monitor (BL-IN-06),
# shared with `freemyid monitor`; this tool keeps its own User-Agent and HEAD-first flow.

def _httpx_requester(timeout: float) -> tuple[Requester, Callable[[], None]]:
    return monitor.httpx_requester(timeout=timeout, user_agent=USER_AGENT)


def _fetch(url: str, method: str, policy: Any, req: Requester,
           pause: Callable[[], None]) -> tuple[int | None, str, bytes]:
    """(status or None, problem text, body), via freemyid.monitor.fetch."""
    r = monitor.fetch(url, method, policy, req, pause)
    return r.status, r.problem, r.body


def _selector_present(sel: str, html: str) -> bool | None:
    return monitor.selector_present(sel, html)


def check_online(path: Path, *, delay: float = 3.0, selectors: bool = False,
                 requester: Requester | None = None, policy: Any = None,
                 sleep: Callable[[float], None] = time.sleep) -> list[Finding]:
    from freemyid.netpolicy import NetPolicy
    from freemyid.registry import RegistryError, load_registry

    name = path.name
    try:
        reg = load_registry(path)
    except RegistryError as e:
        return [Finding(ERROR, name, "-", "online", f"skipped, registry invalid: {str(e)[:120]}")]
    policy = policy or NetPolicy(reg)
    delay = max(1.0, delay)
    close: Callable[[], None] = lambda: None
    if requester is None:
        requester, close = _httpx_requester(timeout=15.0)
    first = [True]

    def pause() -> None:
        if not first[0]:
            sleep(delay)
        first[0] = False

    out: list[Finding] = []
    try:
        for b in reg.brokers:
            if not b.enabled:
                continue
            target = str(b.opt_out_url or b.url)
            status, problem, _ = _fetch(target, "HEAD", policy, requester, pause)
            if problem:
                out.append(Finding(ERROR, name, b.id, "online", problem))
            elif status in BLOCKED:
                out.append(Finding(WARN, name, b.id, "online",
                                   f"HTTP {status} (likely bot protection), check by hand"))
            elif status is not None and status >= 400:
                out.append(Finding(ERROR, name, b.id, "online", f"HTTP {status} for {target}"))
            if not selectors:
                continue
            page, sels = monitor.form_plan(b)
            if not sels:
                continue
            status, problem, body = _fetch(page, "GET_BODY", policy, requester, pause)
            if problem or status is None or status >= 400:
                out.append(Finding(WARN, name, b.id, "selector",
                                   f"page not checked: {problem or f'HTTP {status}'}"))
                continue
            html = body.decode("utf-8", errors="replace")
            for sel in sels:
                if _selector_present(sel, html) is False:
                    out.append(Finding(ERROR, name, b.id, "selector", f"not found: {sel[:80]}"))
    finally:
        close()
    return out


# --- report + CLI ------------------------------------------------------------------------

def render_markdown(findings: list[Finding], files: list[Path]) -> str:
    errs = sum(f.level == ERROR for f in findings)
    warns = sum(f.level == WARN for f in findings)
    lines = ["# Registry health report", "",
             f"Files: {', '.join(p.name for p in files)}. Errors: {errs}. Warnings: {warns}.", ""]
    if findings:
        lines += ["| Level | Registry | Broker | Check | Detail |", "|---|---|---|---|---|"]
        for f in findings:
            detail = f.detail.replace("|", "\\|")
            lines.append(f"| {f.level} | {f.registry} | {f.broker} | {f.check} | {detail} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="*", type=Path,
                    help="registry files (default: sample, plus brokers/registry.yaml if present)")
    ap.add_argument("--online", action="store_true", help="HEAD each opt-out page (polite)")
    ap.add_argument("--selectors", action="store_true", help="with --online: check form selectors")
    ap.add_argument("--delay", type=float, default=3.0, help="seconds between requests (min 1)")
    ap.add_argument("--max-age-days", type=int, default=MAX_AGE_DAYS)
    ap.add_argument("--today", type=date.fromisoformat, default=None, help=argparse.SUPPRESS)
    ap.add_argument("--strict", action="store_true", help="warnings also fail the run")
    ap.add_argument("--report", type=Path, help="write findings (.md, or .json)")
    ap.add_argument("-q", "--quiet", action="store_true", help="print only the summary line")
    a = ap.parse_args(argv)
    if a.selectors and not a.online:
        ap.error("--selectors needs --online")
    files = a.paths or [SAMPLE] + ([FULL] if FULL.exists() else [])
    missing = [p for p in files if not p.exists()]
    if missing:
        print(f"registry_health: no such file: {missing[0]}", file=sys.stderr)
        return 2

    findings: list[Finding] = []
    for p in files:
        findings += check_offline(p, today=a.today, max_age_days=a.max_age_days)
        if a.online:
            findings += check_online(p, delay=a.delay, selectors=a.selectors)

    errs = sum(f.level == ERROR for f in findings)
    warns = len(findings) - errs
    if not a.quiet:
        for f in findings:
            print(f"{f.level:5} {f.registry} {f.broker}: {f.check}: {f.detail}")
    print(f"registry_health: {len(files)} file(s), {errs} error(s), {warns} warning(s)")
    if a.report:
        if a.report.suffix == ".json":
            a.report.write_text(json.dumps([asdict(f) for f in findings], indent=1) + "\n",
                                encoding="utf-8")
        else:
            a.report.write_text(render_markdown(findings, files), encoding="utf-8")
    return 1 if errs or (a.strict and warns) else 0


if __name__ == "__main__":
    sys.exit(main())
