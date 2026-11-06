"""Listing finder (PLAN_V1 D10): the person points at their own listing, Vanish records it.

Flow (only ever started by the person; scheduled runs never do this):
  1. consent gate, broker lookup;
  2. a VISIBLE browser window (system Edge on Windows) opens the site's search through
     BrowserManager (NetPolicy allowlist, `bm.goto`, `check_escaped` every poll):
       * `Broker.search_url_pattern` set -> the results URL, already filled in;
       * otherwise the site's page (`Broker.url`), whose search boxes `filler.fill_page`
         fills with name + city/state (nothing else; Search is NOT pressed);
  3. a big banner says "Find the result that is you, open it, then click the green
     'This is me' button", and a fixed green 'This is me' button (plus a smaller
     'I can't find me') is added to every page of the window;
  4. a click on 'This is me' records the URL of the page the click came from (taken from
     Playwright's frame, never from page script) if it is https, on the broker's own
     domains and matches `Broker.listing_url_pattern` (when set). Otherwise the banner says
     why and Vanish keeps waiting;
  5. accepted: a CONFIRMED Listing (match_reasons user_confirmed + listing_finder), a
     screenshot as evidence, the broker moves to FOUND (state.after_scan), an Event with
     actor USER, open REVIEW_MATCH to-dos for the broker are closed. D9 fill_for_me then
     uses the listing URL;
  6. timeout / window closed / 'I can't find me' / off-allowlist navigation / any error:
     the existing REVIEW_MATCH to-do (if there is one) or the Assisted to-do card is
     returned (created if needed), so nothing is lost.

Safety:
  * The banner and buttons are built with DOM APIs and `textContent` only (no innerHTML),
    all strings are constants or passed as `evaluate` arguments.
  * The click is reported through a binding with a random per-window name. The init script
    takes the binding into a closure and deletes it from `window` before any page script
    runs, and only forwards clicks with `event.isTrusted` (a real mouse click, not a script
    calling `.click()`). The binding argument is only an action name; the URL comes from
    the calling frame, which must be a page's main frame.
  * No CAPTCHA solving, no stealth: a real person is at a real browser.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import secrets
import threading
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlsplit, urlunsplit

from .. import config as cfgmod
from ..models import (
    Actor,
    Broker,
    Event,
    EvidenceKind,
    Listing,
    ListingState,
    MatchLevel,
    ProfileField,
    TodoKind,
    utcnow,
)
from . import filler

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Page

    from ..models import Profile, Registry
    from ..storage import Store
    from .browser import BrowserManager

log = logging.getLogger(__name__)

BANNER_ID = "vanish-find-banner"
BUTTON_ID = "vanish-this-is-me"
CANT_ID = "vanish-cant-find"
_POLL_S = 0.5
_URL_MAX = 2048

MSG_FIND = ("Find the result that is you, open it, then click the green 'This is me' "
            "button.")
MSG_SEARCH_FIRST = ("Vanish typed your name and town into the search boxes. Press the "
                    "site's Search button first.")
MSG_HINT = "Can't find yourself? Click 'I can't find me'. To stop, just close this window."
MSG_REJECT = {
    "pattern_mismatch": "This page is not a single person's listing. Open the result that "
                        "is you, then click 'This is me' again.",
    "search_page": "This is still the search page. Open the result that is you, then click "
                   "'This is me' again.",
    "off_host": "This page is not part of the site Vanish is checking. Go back to it, open "
                "your listing, then click 'This is me' again.",
}
MSG_REJECT_OTHER = "Vanish could not use this page. Open your listing, then click 'This is " \
                   "me' again."
MSG_DONE = "Thank you! Vanish saved this listing. You can close this window now."
BTN_TEXT = "This is me"
CANT_TEXT = "I can't find me"

# Fields the person searched with. The confirmed listing showed them (that is how it came
# up and how the person recognised it), so the opt-out form may repeat them (D9 minimization).
SEARCH_FIELDS = [ProfileField.LISTING_URL, ProfileField.FULL_NAME, ProfileField.FIRST_NAME,
                 ProfileField.LAST_NAME, ProfileField.CITY, ProfileField.STATE]
REASON_USER = "user_confirmed"
REASON_FINDER = "listing_finder"

Status = Literal["found", "fallback", "refused"]


@dataclass
class FindResult:
    """Outcome of one listing-finder session. `listing_url` is for the caller's UI only;
    never log it (it usually contains the person's name)."""
    status: Status
    reason: str          # this_is_me | timeout | window_closed | user_cant_find | blocked |
    #                      browser_unavailable | error:<Type> | consent | unknown_broker | ...
    broker_id: str
    listing_id: str | None = None
    listing_url: str | None = None
    rejected: int = 0                 # 'This is me' clicks on unusable pages
    last_rejection: str | None = None  # off_host | pattern_mismatch | search_page | ...
    searched_with: str | None = None   # search_url | form | none
    todo_id: str | None = None         # fallback card (REVIEW_MATCH or ASSISTED_OPT_OUT)
    evidence_ids: list[str] | None = None

    @property
    def ok(self) -> bool:
        return self.status == "found"


# --------------------------------------------------------------------------- pure helpers


def check_listing_url(broker: Broker, url: str, *,
                      search_url: str | None = None) -> tuple[str | None, str]:
    """Is `url` usable as this broker's listing URL?

    Returns (normalized_url, "") or (None, reason). Rules: https only, no credentials,
    host on `broker.domains` (or a subdomain), not the search page itself, and the path
    must `re.search`-match `broker.listing_url_pattern` when the registry has one (bounded
    input). Without a pattern the site root is refused too. Fragments are dropped.
    """
    from ..netpolicy import _host_ok, host_of
    if not url or len(url) > _URL_MAX:
        return None, "bad_url"
    try:
        u = urlsplit(url)
    except ValueError:
        return None, "bad_url"
    if u.scheme != "https":
        return None, "not_https"
    host = host_of(url)
    if not host or u.username or u.password:
        return None, "bad_url"
    if not _host_ok(host, set(broker.domains)):
        return None, "off_host"
    path = u.path or "/"
    if search_url:
        s = urlsplit(search_url)
        if (s.hostname or "").lower() == host and (s.path or "/") == path:
            return None, "search_page"
    if broker.listing_url_pattern:
        try:
            if re.search(broker.listing_url_pattern, path[:_URL_MAX]) is None:
                return None, "pattern_mismatch"
        except re.error:
            return None, "pattern_mismatch"
    elif path == "/":
        return None, "search_page"
    port = f":{u.port}" if u.port and u.port != 443 else ""
    return urlunsplit(("https", host + port, path, u.query, "")), ""


def search_values(profile: Profile) -> dict[str, str]:
    """What the search boxes get: name and current city/state. Nothing else (no phone,
    street, zip, DOB or email)."""
    cur = next((a for a in profile.addresses if a.current), profile.addresses[0])
    n = profile.name
    vals = {"first_name": n.first, "last_name": n.last,
            "full_name": f"{n.first} {n.last}".strip(), "city": cur.city or "",
            "state": (cur.state or "").upper()}
    return {k: v for k, v in vals.items() if v}


# --------------------------------------------------------------------------- page script


def _init_js(binding: str) -> str:
    """Runs before page scripts in every document of the window (main frames only).

    All text is constant (json-encoded here) and set with textContent. The binding is moved
    into this closure and deleted from window, so page script cannot call it; only trusted
    clicks are forwarded.
    """
    cfg = {"binding": binding, "banner": BANNER_ID, "btn": BUTTON_ID, "cant": CANT_ID,
           "lines": [MSG_FIND, MSG_HINT], "btnText": BTN_TEXT, "cantText": CANT_TEXT}
    return _INIT_TEMPLATE.replace("__VANISH_CFG__", json.dumps(cfg))


_INIT_TEMPLATE = """
(() => {
  if (window.top !== window) return;
  const C = __VANISH_CFG__;
  const report = window[C.binding];
  try { delete window[C.binding]; } catch (e) {}
  try { if (C.binding in window) window[C.binding] = undefined; } catch (e) {}
  if (typeof report !== 'function') return;
  const mk = (tag) => document.createElement(tag);
  const send = (action) => (ev) => {
    if (!ev || !ev.isTrusted) return;
    ev.preventDefault(); ev.stopPropagation();
    try { report(action); } catch (e) {}
  };
  const button = (id, text, css, action) => {
    const b = mk('button');
    b.id = id; b.type = 'button'; b.textContent = text;
    b.setAttribute('aria-label', text);
    b.style.cssText = css;
    b.addEventListener('click', send(action), true);
    return b;
  };
  const ensure = () => {
    const root = document.body || document.documentElement;
    if (!root) return;
    if (!document.getElementById(C.banner)) {
      const bar = mk('div');
      bar.id = C.banner;
      bar.setAttribute('role', 'alert');
      bar.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:2147483646;' +
        'background:#ffe600;color:#000;font:bold 26px/1.35 "Segoe UI",Arial,sans-serif;' +
        'padding:18px 28px;border-bottom:6px solid #000;box-shadow:0 4px 12px rgba(0,0,0,.4);' +
        'text-align:left;pointer-events:none;';
      C.lines.forEach((t, i) => {
        const p = mk('div');
        p.className = 'vanish-line';
        p.textContent = t;
        if (i > 0) p.style.cssText = 'font-size:22px;font-weight:600;margin-top:8px;';
        bar.appendChild(p);
      });
      root.appendChild(bar);
      if (document.body) document.body.style.marginTop = (bar.offsetHeight + 8) + 'px';
    }
    if (!document.getElementById(C.btn)) {
      root.appendChild(button(C.btn, C.btnText,
        'position:fixed;right:28px;bottom:96px;z-index:2147483647;background:#0b6b2e;' +
        'color:#fff;font:bold 30px/1.2 "Segoe UI",Arial,sans-serif;padding:20px 36px;' +
        'border:5px solid #fff;outline:4px solid #000;border-radius:14px;cursor:pointer;' +
        'box-shadow:0 6px 18px rgba(0,0,0,.5);', 'this_is_me'));
    }
    if (!document.getElementById(C.cant)) {
      root.appendChild(button(C.cant, C.cantText,
        'position:fixed;right:28px;bottom:28px;z-index:2147483647;background:#fff;' +
        'color:#000;font:600 20px/1.2 "Segoe UI",Arial,sans-serif;padding:10px 20px;' +
        'border:3px solid #000;border-radius:10px;cursor:pointer;', 'cant_find'));
    }
  };
  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', ensure, {once: true});
  else ensure();
  setInterval(ensure, 800);
})();
"""


# Replace the banner text (argument, never interpolated). Background green when done.
_SET_MSG_JS = """
([id, lines, done]) => {
  const bar = document.getElementById(id);
  if (!bar) return false;
  while (bar.firstChild) bar.removeChild(bar.firstChild);
  lines.forEach((t, i) => {
    const p = document.createElement('div');
    p.className = 'vanish-line';
    p.textContent = String(t);
    if (i > 0) p.style.cssText = 'font-size:22px;font-weight:600;margin-top:8px;';
    bar.appendChild(p);
  });
  if (done) { bar.style.background = '#0b6b2e'; bar.style.color = '#fff'; }
  return true;
}
"""


# --------------------------------------------------------------------------- bookkeeping


def _event(store: Store, profile_id: str, broker_id: str, action: str,
           actor: Actor = Actor.ENGINE, frm: ListingState | None = None,
           to: ListingState | None = None, **detail: Any) -> None:
    store.log(Event(profile_id=profile_id, broker_id=broker_id, actor=actor, action=action,
                    from_state=frm, to_state=to, detail=detail))


def _fallback_todo(store: Store, profile: Profile, broker: Broker) -> str:
    """The existing match-review card if there is one, else the Assisted card."""
    for t in store.list_todos(profile.id):
        if t.broker_id == broker.id and t.kind == TodoKind.REVIEW_MATCH:
            return t.id
    from .fill_for_me import _fallback_todo as assisted_card
    listings = [li for li in store.list_listings(profile.id, broker.id)
                if li.gone_since is None and li.match_level != MatchLevel.NO_MATCH]
    return assisted_card(store, profile, broker, listings, None, None)


def record_listing(store: Store, profile: Profile, broker: Broker, url: str,
                   screenshot: bytes | None = None) -> tuple[Listing, list[str]]:
    """Store `url` as a CONFIRMED listing chosen by the person (actor USER).

    Same record the matcher/runner keeps for a confirmed match (a REVIEW_MATCH 'yes' adds
    the same `user_confirmed` reason, which the runner keeps on re-scan). Moves the broker
    to FOUND via state.after_scan and clears next_check_at so the next run acts on it.
    """
    from ..state import after_scan, can_transition, transition
    from ..submitters import base
    now = utcnow()
    prev = next((li for li in store.list_listings(profile.id, broker.id) if li.url == url),
                None)
    reasons = sorted({*(prev.match_reasons if prev and prev.match_level != MatchLevel.NO_MATCH
                        else []), REASON_USER, REASON_FINDER})
    shown = sorted({*(prev.shown_fields if prev else []), *SEARCH_FIELDS},
                   key=lambda f: f.value)
    if prev is not None:
        li = prev.model_copy(update={"match_level": MatchLevel.CONFIRMED, "match_score": 100.0,
                                     "match_reasons": reasons, "shown_fields": shown,
                                     "last_seen": now, "gone_since": None})
    else:
        li = Listing(profile_id=profile.id, broker_id=broker.id, url=url, match_score=100.0,
                     match_level=MatchLevel.CONFIRMED, match_reasons=reasons,
                     shown_fields=shown, first_seen=now, last_seen=now)
    store.save_listing(li)
    ev_ids: list[str] = []
    if screenshot:
        ev = base.evidence(profile.id, broker.id, EvidenceKind.SCREENSHOT, "png",
                           listing_id=li.id, caption="listing chosen by the person")
        ev_ids.append(store.save_evidence(ev, screenshot).id)
    st = store.get_status(profile.id, broker.id)
    frm = st.state
    dst = after_scan(st, True, now)
    if dst != st.state and can_transition(st.state, dst):
        st = transition(st, dst, now)
    store.save_status(st.model_copy(update={"next_check_at": None}))
    _event(store, profile.id, broker.id, "listing_confirmed", Actor.USER, frm, st.state,
           listing_id=li.id, via=REASON_FINDER, new=prev is None)
    for t in store.list_todos(profile.id):
        if t.broker_id == broker.id and t.kind == TodoKind.REVIEW_MATCH:
            store.complete_todo(t.id)
    return li, ev_ids


# --------------------------------------------------------------------------- entry point


async def find_listing(store: Store, profile_id: str, broker_id: str, *, timeout_s: int = 600,
                       registry: Registry | None = None, browser: BrowserManager | None = None,
                       headed: bool = True, cfg: cfgmod.Config | None = None,
                       on_ready: Callable[[Page], Awaitable[Any]] | None = None,
                       close_delay_s: float = 3.0) -> FindResult:
    """Open the broker's search in a visible window and let the person pick their listing.

    `broker_id` is the people-search site itself (not its covered_by parent: the listing
    lives on this site). `browser` (an unstarted or started BrowserManager) is for tests;
    by default one is created and closed here. `on_ready(page)` runs as a task once the
    buttons are up; tests use it to play the person. Never raises for page/browser
    problems: those return status "fallback".
    """
    from ..consent import consent_ok
    cfg = cfg or cfgmod.load()
    profile = store.get_profile(profile_id)
    if profile is None:
        return FindResult("refused", "no_profile", broker_id)
    ok, _why = consent_ok(profile, store)
    if not ok:
        return FindResult("refused", "consent", broker_id)
    if registry is None:
        from ..registry import load_registry
        registry = load_registry()
    try:
        broker = registry.get(broker_id)
    except KeyError:
        return FindResult("refused", "unknown_broker", broker_id)
    res = FindResult("fallback", "", broker.id)

    def fallback(reason: str) -> FindResult:
        res.status, res.reason = "fallback", reason
        res.todo_id = _fallback_todo(store, profile, broker)
        _event(store, profile.id, broker.id, "listing_finder_fallback", reason=reason[:40],
               rejected=res.rejected)
        return res

    from ..netpolicy import NetPolicy
    from .browser import BlockedByPolicy, BrowserManager
    from .outbox import dev_fixture_base
    own = browser is None
    bm = browser or BrowserManager(NetPolicy(registry), headless=True, cfg=cfg,
                                   fixture_base=dev_fixture_base())
    bctx = None
    try:
        try:
            await bm.start()
            bctx = await bm.new_context(broker.domains, headed=headed)
        except Exception as e:  # noqa: BLE001 - no browser: the card still works
            log.warning("listing_finder: browser unavailable (%s)", type(e).__name__)
            return fallback("browser_unavailable")
        try:
            return await _drive(store, profile, broker, bm, bctx, res, timeout_s, on_ready,
                                close_delay_s, fallback)
        except BlockedByPolicy:
            return fallback("blocked")
        except Exception as e:  # noqa: BLE001 - window closed mid-call, odd page, ...
            if not [p for p in bctx.pages if not p.is_closed()]:
                return fallback("window_closed")
            log.warning("listing_finder failed: %s", type(e).__name__)
            return fallback(f"error:{type(e).__name__}")
    finally:
        if bctx is not None:
            try:
                await bctx.close()
            except Exception as e:  # noqa: BLE001
                log.debug("closing finder window failed: %s", type(e).__name__)
        if own:
            await bm.close()


async def _drive(store: Store, profile: Profile, broker: Broker, bm: BrowserManager,
                 bctx: BrowserContext, res: FindResult, timeout_s: int,
                 on_ready: Callable[[Page], Awaitable[Any]] | None, close_delay_s: float,
                 fallback: Callable[[str], FindResult]) -> FindResult:
    from ..submitters.web_form import search_url
    clicks: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
    binding = "__vanish_" + secrets.token_hex(8)

    async def _on_click(source: Any, action: Any = None) -> None:
        if action not in ("this_is_me", "cant_find"):
            return
        frame = source.get("frame") if isinstance(source, dict) else None
        pg = source.get("page") if isinstance(source, dict) else None
        if frame is None or pg is None or frame != pg.main_frame:
            return
        await clicks.put((str(action), pg))

    await bctx.expose_binding(binding, _on_click)
    await bctx.add_init_script(_init_js(binding))
    page = await bctx.new_page()

    surl = search_url(broker, profile)
    start = surl or str(broker.search_page_url or broker.url)
    await bm.goto(page, start, check_challenge=False)
    lines = [MSG_FIND]
    if surl:
        res.searched_with = "search_url"
    else:
        rep = await filler.fill_page(page, search_values(profile))
        res.searched_with = "form" if rep.filled else "none"
        if rep.filled:
            lines.append(MSG_SEARCH_FIRST)
        _event(store, profile.id, broker.id, "listing_finder_search", filled=sorted(
            set(rep.filled)), searched_with=res.searched_with)
    lines.append(MSG_HINT)
    current = lines

    async def _say(pg: Page, msg: list[str], done: bool = False) -> None:
        try:
            await pg.evaluate(_SET_MSG_JS, [BANNER_ID, msg, done])
        except Exception:  # noqa: BLE001, S110 - mid-navigation; the next poll retries
            pass

    await page.wait_for_selector(f"#{BUTTON_ID}", state="attached", timeout=10_000)
    await _say(page, current)
    task: asyncio.Task[Any] | None = (
        asyncio.ensure_future(on_ready(page)) if on_ready else None)

    loop = asyncio.get_running_loop()
    deadline = loop.time() + max(1, timeout_s)
    try:
        while loop.time() < deadline:
            open_pages = [p for p in bctx.pages if not p.is_closed()]
            if not open_pages:
                return fallback("window_closed")
            for p in open_pages:
                bm.check_escaped(p)
            try:
                action, pg = await asyncio.wait_for(clicks.get(), timeout=_POLL_S)
            except TimeoutError:
                for p in open_pages:
                    await _say(p, current)   # keep the message after a reload
                continue
            if action == "cant_find":
                _event(store, profile.id, broker.id, "listing_finder_cant_find", Actor.USER)
                return fallback("user_cant_find")
            if pg.is_closed():
                continue
            bm.check_escaped(pg)
            url, why = check_listing_url(broker, pg.url, search_url=start)
            if url is None:
                res.rejected += 1
                res.last_rejection = why
                _event(store, profile.id, broker.id, "listing_finder_rejected", Actor.USER,
                       why=why)
                current = [MSG_REJECT.get(why, MSG_REJECT_OTHER), MSG_HINT]
                await _say(pg, current)
                continue
            shot: bytes | None
            try:
                shot = await pg.screenshot(full_page=True)
            except Exception:  # noqa: BLE001 - the listing still counts without a picture
                shot = None
            li, ev_ids = record_listing(store, profile, broker, url, shot)
            res.status, res.reason = "found", "this_is_me"
            res.listing_id, res.listing_url, res.evidence_ids = li.id, li.url, ev_ids
            await _say(pg, [MSG_DONE], done=True)
            if close_delay_s > 0:
                await asyncio.sleep(close_delay_s)
            return res
        return fallback("timeout")
    finally:
        if task is not None and not task.done():
            task.cancel()


def find_listing_sync(store: Store, profile_id: str, broker_id: str, **kw: Any) -> FindResult:
    """Blocking wrapper for the wizard/CLI (safe from a thread or with a loop running)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(find_listing(store, profile_id, broker_id, **kw))
    box: dict[str, Any] = {}

    def _t() -> None:
        try:
            box["r"] = asyncio.run(find_listing(store, profile_id, broker_id, **kw))
        except BaseException as e:  # noqa: BLE001
            box["e"] = e

    th = threading.Thread(target=_t, name="vanish-find", daemon=True)
    th.start()
    th.join()
    if "e" in box:
        raise box["e"]
    return box["r"]
