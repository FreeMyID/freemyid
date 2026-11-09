"""BL-IN-06 broker monitoring: does each broker's opt-out page still load, and do its form
selectors still match? Read only. Schema `monitor/1` (docs/MONITOR.md).

Rules (never relaxed):
* Nothing is ever filled in, clicked or submitted. Only the opt-out page and the page the
  registry's `goto` step names are loaded. Every other form step is read for its selector
  and never run.
* A challenge or CAPTCHA page, or HTTP 403/429/503, is recorded as `blocked`. Nothing
  retries around it.
* Each hop, redirects included, must be https and allowed by NetPolicy. An off-list hop is
  reported and never fetched.
* The fingerprint covers the registry selectors that matched plus the form fields' tag,
  type and name. It never includes page text. The report holds broker ids, health values,
  HTTP status, registry selectors and hashes only, with no page text and no query strings.
* Polite: one request at a time (the headless page load counts as one), a random 2-5 s gap
  (min 1 s), at most 5 redirects, a 2 MB cap per page, and a 30 s budget per broker checked
  before each request; one page body that takes longer than 30 s to read is cut off and
  reported `unreachable` (never a truncated page, which could look like a changed form).

No person's data exists here: monitoring needs no profile and touches no store.
Also used by tools/registry_health.py (qa-security) for its `--online` checks.
"""
from __future__ import annotations

import hashlib
import logging
import random
import re
import time
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urljoin, urlsplit

from . import __version__

log = logging.getLogger(__name__)
SCHEMA = "monitor/1"
USER_AGENT = f"FreeMyID/{__version__} broker-monitor (+https://freemyid.org/safety/)"
MAX_REDIRECTS = 5
MAX_BODY = 2_000_000
BLOCKED = {403, 429, 503}
BROKER_BUDGET_S = 30.0
DEMOTE_AFTER_WEEKS = 2

Health = Literal["ok", "moved", "form_changed", "blocked", "unreachable", "unknown"]
BAD: frozenset[str] = frozenset({"moved", "form_changed", "blocked", "unreachable"})

Requester = Callable[[str, str], tuple[int, str | None, bytes]]
"""(method, url) -> (status, Location header or None, body[:MAX_BODY]; empty for HEAD).
method: HEAD, GET (body not read) or GET_BODY."""

#: (broker, url) -> (status, final https url, html). One headless page load, goto only.
PageLoader = Callable[[Any, str], tuple[int, str, str]]


class ChallengeSeen(Exception):
    """The browser met a challenge page. Recorded as `blocked`; never worked around."""


# --------------------------------------------------------------------------- fetch


def httpx_requester(timeout: float = 15.0, user_agent: str = USER_AGENT, *,
                    read_budget: float = BROKER_BUDGET_S,
                    clock: Callable[[], float] = time.monotonic, transport: Any = None
                    ) -> tuple[Requester, Callable[[], None]]:
    """A plain requester: no redirects followed (fetch() does that), no cookies kept.
    `timeout` limits each network wait; `read_budget` limits the whole request, so a server
    that trickles its body can't hold the run (raises TimeoutError)."""
    import httpx
    client = httpx.Client(timeout=timeout, follow_redirects=False, transport=transport,
                          headers={"User-Agent": user_agent, "Accept": "text/html,*/*"})

    def req(method: str, url: str) -> tuple[int, str | None, bytes]:
        client.cookies.clear()
        if method == "HEAD":
            r = client.head(url)
            return r.status_code, r.headers.get("location"), b""
        stop = clock() + read_budget
        with client.stream("GET", url) as r:
            body = bytearray()
            if method == "GET_BODY":
                for chunk in r.iter_bytes():
                    if clock() > stop:
                        raise TimeoutError(f"body not read within {read_budget:.0f} s")
                    body.extend(chunk)
                    if len(body) >= MAX_BODY:
                        break
            return r.status_code, r.headers.get("location"), bytes(body[:MAX_BODY])
    return req, client.close


@dataclass
class Fetch:
    status: int | None          # None: not fetched or failed (see problem)
    problem: str = ""           # plain text, no page content
    body: bytes = b""
    final_url: str = ""


def fetch(url: str, method: str, policy: Any, req: Requester, pause: Callable[[], None],
          deadline: float | None = None, clock: Callable[[], float] = time.monotonic
          ) -> Fetch:
    """Follow redirects by hand. Each hop must be https and allowed by `policy`.
    A HEAD refused with 405/501 is retried once as a GET."""
    for _ in range(MAX_REDIRECTS + 1):
        if urlsplit(url).scheme != "https":
            return Fetch(None, f"not https: {_safe(url)}")
        if not policy.is_allowed(url):
            return Fetch(None, f"host not on the NetPolicy allowlist: {urlsplit(url).hostname}")
        if deadline is not None and clock() > deadline:
            return Fetch(None, f"took longer than {BROKER_BUDGET_S:.0f} s")
        pause()
        try:
            status, loc, body = req(method, url)
            if method == "HEAD" and status in (405, 501):
                pause()
                status, loc, body = req("GET", url)
        except Exception as e:  # noqa: BLE001 - a network failure is a finding, not a crash
            return Fetch(None, f"request failed: {type(e).__name__}")
        if status in (301, 302, 303, 307, 308) and loc:
            url = urljoin(url, loc)
            continue
        return Fetch(status, "", body, url)
    return Fetch(None, f"more than {MAX_REDIRECTS} redirects")


def _safe(url: str) -> str:
    """A URL for a report: scheme, host and path only (no query, no fragment)."""
    u = urlsplit(url)
    return f"{u.scheme}://{u.hostname or ''}{u.path}"[:120]


# --------------------------------------------------------------------------- page checks

_SIMPLE_SEL = re.compile(
    r"""^(?:#(?P<id>[A-Za-z][\w-]*)|(?:[a-z]+)?\[name=["']?(?P<name>[\w\[\]-]+)["']?\])$""")
_FIELD = re.compile(r"<(input|select|textarea|button)\b([^>]*)>", re.IGNORECASE)
# (?<![\w-]) not \b: "data-name" or "data-id" must not count as name or id.
_ATTR = re.compile(r"""(?<![\w-])(type|name)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>/]+))""", re.IGNORECASE)


def selector_present(sel: str, html: str) -> bool | None:
    """True/False for simple selectors (#id, [name=x], tag[name=x]); None: can't tell
    without a browser."""
    m = _SIMPLE_SEL.match(sel.strip())
    if not m:
        return None
    attr, val = ("id", m["id"]) if m["id"] else ("name", m["name"])
    return re.search(rf"""(?<![\w-]){attr}\s*=\s*["']?{re.escape(val)}["'\s>/]""", html) is not None


def form_fields(html: str) -> list[tuple[str, str, str]]:
    """(tag, type, name) of each form control, sorted. Structure only, never values,
    labels or any other page text."""
    out = set()
    for tag, attrs in _FIELD.findall(html):
        got = {k.lower(): (a or b or c) for k, a, b, c in _ATTR.findall(attrs)}
        typ = got.get("type", "").lower()
        if typ == "hidden":
            continue                      # tokens rotate on every load
        out.add((tag.lower(), typ, got.get("name", "")))
    return sorted(out)


def fingerprint(matched: Iterable[str], fields: list[tuple[str, str, str]]) -> str:
    h = hashlib.sha256()
    for s in sorted(matched):
        h.update(b"S\0" + s.encode() + b"\0")
    for f in fields:
        h.update(b"F\0" + "\0".join(f).encode() + b"\0")
    return h.hexdigest()[:16]


def form_plan(broker: Any) -> tuple[str, list[str]]:
    """The page the form lives on and the selectors its steps use. Steps are READ here,
    never run: fill/click/check/select/submit/human only give their selector."""
    page = str(broker.opt_out_url or broker.url)
    sels: list[str] = []
    for st in broker.form:
        if st.action == "goto" and st.url:
            page = st.url
        elif st.selector and st.selector not in sels:
            sels.append(st.selector)
    return page, sels


# --------------------------------------------------------------------------- one broker


@dataclass
class BrokerHealth:
    broker_id: str
    health: Health
    detail: str = ""                         # plain text, no page content
    http_status: int | None = None
    page: str = ""                           # scheme://host/path, no query
    selectors_missing: list[str] = field(default_factory=list)
    selectors_unchecked: int = 0             # not simple, and no browser load
    fingerprint: str | None = None
    used_browser: bool = False
    # filled in by compare()
    previous_health: str | None = None
    changed: bool = False
    first_seen_bad: str | None = None
    weeks_bad: int = 0
    demote_suggested: bool = False


def _path(url: str) -> tuple[str, str]:
    u = urlsplit(url)
    return (u.hostname or "").lower().removeprefix("www."), (u.path.rstrip("/") or "/")


def check_broker(broker: Any, policy: Any, req: Requester, pause: Callable[[], None], *,
                 page_loader: PageLoader | None = None,
                 clock: Callable[[], float] = time.monotonic) -> BrokerHealth:
    from .engine.browser import detect_challenge
    deadline = clock() + BROKER_BUDGET_S
    target, sels = form_plan(broker)
    res = fetch(target, "GET_BODY", policy, req, pause, deadline, clock)
    h = BrokerHealth(broker_id=broker.id, health="ok", http_status=res.status,
                     page=_safe(target))
    if res.problem:
        h.health, h.detail = "unreachable", res.problem
        return h
    html = res.body.decode("utf-8", errors="replace")
    label = detect_challenge(html, status=res.status)
    if label:
        h.health, h.detail = "blocked", f"challenge page ({label}); check by hand"
        return h
    if res.status is None or res.status >= 400:
        h.health, h.detail = "unreachable", f"HTTP {res.status}"
        return h
    if _path(res.final_url) != _path(target):
        h.health, h.detail = "moved", f"now at {_safe(res.final_url)}"
    if not sels:
        h.fingerprint = fingerprint([], form_fields(html))
        return h
    results = {s: selector_present(s, html) for s in sels}
    js_only = not form_fields(html)
    # only a form with no fields in the HTML goes to the browser (docs/MONITOR.md): a
    # selector we can't parse (None) stays unresolvable on rendered HTML too (CR #64)
    if js_only and page_loader is not None:
        if clock() > deadline:
            h.health, h.detail = "unknown", f"took longer than {BROKER_BUDGET_S:.0f} s"
            return h
        pause()                           # the browser load is a request too: same gap
        try:
            status, final, html = page_loader(broker, res.final_url or target)
        except ChallengeSeen:
            h.health, h.detail = "blocked", "challenge page in the browser; check by hand"
            return h
        except Exception as e:  # reported, never retried
            log.debug("browser load failed for %s", broker.id, exc_info=True)
            h.health, h.detail = "unknown", f"browser load failed: {type(e).__name__}"
            return h
        h.used_browser = True
        if not final.startswith("https://") or not policy.is_allowed(final):
            h.health, h.detail = "moved", "browser ended off the allowlist"
            return h
        label = detect_challenge(html, status=status)
        if label:
            h.health, h.detail = "blocked", f"challenge page ({label}); check by hand"
            return h
        if status is None or status >= 400:     # an error page is no evidence of a form
            h.http_status = status
            h.health, h.detail = "unreachable", f"HTTP {status} in the browser"
            return h
        js_only = not form_fields(html)
        results = {s: selector_present(s, html) for s in sels}
    if js_only and not h.used_browser:
        h.health = "unknown" if h.health == "ok" else h.health
        h.detail = h.detail or "form is built by JavaScript; needs a browser check"
        return h
    h.selectors_missing = [s for s, ok in results.items() if ok is False]
    h.selectors_unchecked = sum(1 for ok in results.values() if ok is None)
    h.fingerprint = fingerprint([s for s, ok in results.items() if ok], form_fields(html))
    if h.selectors_missing and h.health == "ok":
        h.health = "form_changed"
        h.detail = f"{len(h.selectors_missing)} form selector(s) not found"
    return h


# --------------------------------------------------------------------------- run + compare


def _pauser(delay: tuple[float, float], sleep: Callable[[float], None]) -> Callable[[], None]:
    lo = max(1.0, delay[0])
    hi = max(lo, delay[1])
    first = [True]

    def pause() -> None:
        if not first[0]:
            sleep(random.uniform(lo, hi) if hi > lo else lo)
        first[0] = False
    return pause


def compare(current: list[BrokerHealth], previous: dict[str, Any] | None,
            today: str) -> None:
    """Fill the week-over-week fields in place from last week's monitor/1 doc."""
    prev = {b["broker_id"]: b for b in (previous or {}).get("brokers", [])
            if isinstance(b, dict) and "broker_id" in b}
    for h in current:
        p = prev.get(h.broker_id)
        if p is not None and h.health == "ok" and p.get("fingerprint") and h.fingerprint \
                and p["fingerprint"] != h.fingerprint:
            h.health, h.detail = "form_changed", "the form's fields changed since last week"
        h.previous_health = p.get("health") if p else None
        h.changed = p is not None and p.get("health") != h.health
        if h.health in BAD:
            same = p is not None and p.get("health") == h.health
            h.weeks_bad = int(p.get("weeks_bad", 1)) + 1 if same and p else 1
            h.first_seen_bad = (p.get("first_seen_bad") if same and p else None) or today
            h.demote_suggested = h.weeks_bad >= DEMOTE_AFTER_WEEKS


def run_monitor(registry: Any, *, requester: Requester | None = None,
                page_loader: PageLoader | None = None, policy: Any = None,
                previous: dict[str, Any] | None = None, delay: tuple[float, float] = (2.0, 5.0),
                sleep: Callable[[float], None] | None = None, now: datetime | None = None,
                broker_ids: list[str] | None = None) -> dict[str, Any]:
    """Check every enabled broker with a web page and return the monitor/1 doc.
    One broker's failure never stops the run."""
    from .netpolicy import NetPolicy
    now = now or datetime.now(UTC)
    policy = policy or NetPolicy(registry)
    close: Callable[[], None] = lambda: None
    if requester is None:
        requester, close = httpx_requester()
    pause = _pauser(delay, sleep or time.sleep)   # looked up per call, not at import
    out: list[BrokerHealth] = []
    try:
        for b in registry.brokers:
            if not b.enabled or (broker_ids and b.id not in broker_ids):
                continue
            if not (b.opt_out_url or b.form):
                continue                       # email/postal only: nothing to load
            try:
                out.append(check_broker(b, policy, requester, pause, page_loader=page_loader))
            except Exception as e:  # one broker never stops the run
                log.debug("monitor check failed for %s", b.id, exc_info=True)
                out.append(BrokerHealth(broker_id=b.id, health="unknown",
                                        detail=f"check failed: {type(e).__name__}"))
    finally:
        close()
    compare(out, previous if valid_doc(previous) else None, now.date().isoformat())
    counts = {k: sum(1 for h in out if h.health == k)
              for k in ("ok", "moved", "form_changed", "blocked", "unreachable", "unknown")}
    return {
        "schema": SCHEMA,
        "generated_at": now.isoformat(timespec="seconds"),
        "previous_generated_at": (previous or {}).get("generated_at")
        if valid_doc(previous) else None,
        "counts": counts,
        "changed": [h.broker_id for h in out if h.changed],
        "demote_suggested": [h.broker_id for h in out if h.demote_suggested],
        "brokers": [asdict(h) for h in out],
    }


def valid_doc(doc: Any) -> bool:
    return isinstance(doc, dict) and doc.get("schema") == SCHEMA and \
        isinstance(doc.get("brokers"), list)


def browser_page_loader(policy: Any, cfg: Any) -> tuple[PageLoader, Callable[[], None]]:
    """A headless page loader: one goto per page through BrowserManager (NetPolicy
    routing, challenge detection). It never fills, clicks or submits."""
    from .engine.exposure import BrowserFetcher, FetchFailed
    bf = BrowserFetcher(policy, cfg)

    def load(broker: Any, url: str) -> tuple[int, str, str]:
        try:
            got = bf(broker, url)
        except FetchFailed as e:
            if e.reason == "challenge":
                raise ChallengeSeen() from e
            raise
        return got.status, got.url, got.html
    return load, bf.close
