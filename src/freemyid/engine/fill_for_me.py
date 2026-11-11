"""'Fill it in for me' (PLAN_V1 D9): Free My ID fills the opt-out form, the person submits it.

Flow (only ever started by the person, from the dashboard; scheduled runs never do this):
  1. consent gate, broker checks (web form with an opt-out page; covered_by -> parent);
  2. a VISIBLE browser window (system Edge on Windows) opens the opt-out page through
     BrowserManager (NetPolicy allowlist, `bm.goto`, `check_escaped`);
  3. `filler.fill_page` fills the minimized fields; only registry safe_checkboxes are ticked, CAPTCHAs are not
     touched, Submit is NOT pressed;
  4. a big plain-English banner asks the person to tick the robot box and press Submit;
  5. Free My ID watches for the registry's success signal (the `expect_text` / `wait_for` steps
     after the form's submit step, same as web_form, plus `success_text` /
     `success_url_pattern`). SEC-32: success needs BOTH a submit-like event after the fill
     (a main-frame navigation, or an XHR/fetch POST to an allowed host) AND a signal that
     is new compared with the baseline taken after filling (kept up to date until the
     first submit event): a success phrase that appears more often than before, a success
     selector that was not there, a URL that changed to match `success_url_pattern`, or the
     filled form gone while a success phrase/selector is on the page. A POST that re-shows
     the same form never counts. On success: screenshots saved as evidence (the form as it
     was when the person pressed Submit, SEC-37, and the confirmation without our banner),
     a SENT web-form Request, the broker moves to SUBMITTED (or AWAITING_VERIFICATION)
     exactly like a successful web_form submission, and the Assisted to-do is closed;
  6. timeout / window closed / the page moved to an error address / no success signal /
     any error: the Assisted to-do stays (or is created) and names the next step.

Practice mode (`real_submissions_enabled: false`) still fills: the person, not Free My ID,
presses Submit. The banner then says plainly that Submit sends a real request.
"""
from __future__ import annotations

import asyncio
import logging
import re
import threading
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from .. import config as cfgmod
from ..models import (
    Actor,
    Broker,
    Event,
    EvidenceKind,
    Listing,
    ListingState,
    MatchLevel,
    Method,
    Request,
    RequestKind,
    RequestStatus,
    TodoKind,
    utcnow,
)
from . import filler

if TYPE_CHECKING:
    from playwright.async_api import Page

    from ..models import Profile, Registry, StateLaw
    from ..storage import Store
    from .browser import BrowserManager

log = logging.getLogger(__name__)

BANNER_ID = "freemyid-fill-banner"
_POLL_S = 0.5

MSG_FILLED = ("Free My ID filled this in for you. Please check it, tick the box that says "
              "you're not a robot (if there is one), then press Submit.")
MSG_MISSING = "A few boxes are still empty. Please fill those in yourself."
MSG_PRACTICE = ("Practice mode is on, but this is the real website: pressing Submit "
                "really sends your removal request.")
MSG_HINT = "Free My ID will notice when you're done. To stop, just close this window."
MSG_DONE = "Done! Free My ID saved proof that you sent it. You can close this window now."

Status = Literal["submitted", "fallback", "refused"]


@dataclass
class FillResult:
    """Outcome of one 'Fill it in for me' attempt. PII-free (keys, ids, labels)."""
    status: Status
    reason: str                     # success_text | success_selector | success_url |
    #                                 timeout | window_closed | error_page | unverified |
    #                                 nothing_filled | blocked | browser_unavailable |
    #                                 error:<Type> | consent | ...
    broker_id: str
    filled: list[str] = field(default_factory=list)
    not_found: list[str] = field(default_factory=list)
    withheld: list[str] = field(default_factory=list)
    submit_seen: bool = False       # a navigation / POST happened after filling
    practice_mode: bool = False
    todo_id: str | None = None      # Assisted card to fall back to (fallback)
    request_id: str | None = None   # SENT request (submitted)
    evidence_ids: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == "submitted"


# --------------------------------------------------------------------------- helpers


def success_signals(broker: Broker, vars: dict | None = None) -> tuple[list[str], list[str]]:
    """(texts, selectors) that mean "it worked": the `expect_text` values and `wait_for`
    selectors after the last click/submit step of `Broker.form` (what web_form checks),
    plus `Broker.success_text`."""
    from ..submitters.web_form import render_value
    steps = broker.form
    last = max((i for i, s in enumerate(steps) if s.action in ("click", "submit")), default=-1)
    texts: list[str] = []
    sels: list[str] = []
    for s in steps[last + 1:]:
        if s.action == "expect_text" and s.value:
            try:
                t = render_value(s.value, vars or {}).strip()
            except Exception:  # noqa: BLE001, S112 - template needs a var we don't have
                continue
            if t:
                texts.append(t.lower())
        elif s.action == "wait_for" and s.selector and last >= 0:
            sels.append(s.selector)
    for t in broker.success_text:
        t = (t or "").strip().lower()
        if t and t not in texts:
            texts.append(t)
    return texts, sels


_URL_MATCH_MAX = 2048


def url_matches(pattern: str | None, url: str) -> bool:
    """re.search of a registry regex against the URL's path+query (bounded length)."""
    if not pattern or not url:
        return False
    from urllib.parse import urlsplit
    try:
        u = urlsplit(url)
    except ValueError:
        return False
    target = (u.path or "/") + (f"?{u.query}" if u.query else "")
    try:
        return re.search(pattern, target[:_URL_MATCH_MAX]) is not None
    except re.error:
        return False


def _banner_js(lines: list[str], done: bool) -> str:
    import json
    bg, fg = ("#0b6b2e", "#ffffff") if done else ("#ffe600", "#000000")
    return f"""
(() => {{
  const id = {json.dumps(BANNER_ID)};
  let b = document.getElementById(id);
  if (b) b.remove();
  b = document.createElement('div');
  b.id = id;
  b.setAttribute('role', 'alert');
  b.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:2147483647;' +
    'background:{bg};color:{fg};font:bold 26px/1.35 "Segoe UI",Arial,sans-serif;' +
    'padding:18px 28px;border-bottom:6px solid {fg};box-shadow:0 4px 12px rgba(0,0,0,.4);' +
    'text-align:left;pointer-events:none;';
  for (const [i, t] of {json.dumps(lines)}.entries()) {{
    const p = document.createElement('div');
    p.textContent = t;
    if (i > 0) p.style.cssText = 'font-size:22px;font-weight:600;margin-top:8px;';
    b.appendChild(p);
  }}
  (document.body || document.documentElement).appendChild(b);
  if (document.body) document.body.style.marginTop = (b.offsetHeight + 8) + 'px';
  return true;
}})()
"""


_PAGE_TEXT_JS = f"""
() => {{
  const b = document.getElementById({BANNER_ID!r});
  const t = document.body ? document.body.innerText : '';
  return (b ? t.replace(b.innerText, '') : t).toLowerCase();
}}
"""


# Banner gone but a form is still there (reload after a validation error): show it again.
# A page without a form (e.g. the site's own thank-you page) gets no "press Submit" banner.
_NEEDS_BANNER_JS = f"""
() => !document.getElementById({BANNER_ID!r}) &&
  !!document.querySelector('form input:not([type=hidden]), form textarea, form select')
"""


async def _matched(page: Page, texts: list[str], sels: list[str],
                   url_pattern: str | None = None) -> str | None:
    if url_matches(url_pattern, page.url):
        return "success_url"
    if texts:
        body = await page.evaluate(_PAGE_TEXT_JS)
        if any(t in body for t in texts):
            return "success_text"
    for s in sels:
        if await page.query_selector(s) is not None:
            return "success_selector"
    return None


# One look at the page for SEC-32: how often each success phrase occurs (our banner's words
# subtracted), which success selectors exist, how many of the boxes we filled are still
# there and visible, and the URL. All inputs are passed as arguments, never interpolated.
_SNAPSHOT_JS = """
([banner, texts, sels, controls]) => {
  const b = document.getElementById(banner);
  let t = document.body ? document.body.innerText : '';
  if (b) t = t.replace(b.innerText, '');
  t = t.toLowerCase();
  const counts = texts.map((x) => {
    let n = 0, i = 0;
    while (x && (i = t.indexOf(x, i)) !== -1) { n++; i += x.length; }
    return n;
  });
  const present = sels.map((s) => { try { return !!document.querySelector(s); }
                                    catch (e) { return false; } });
  const vis = (el) => {
    const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none';
  };
  let formLeft = 0;
  for (const [name, id] of controls) {
    let el = null;
    try {
      if (id) el = document.getElementById(id);
      if (!el && name) el = document.querySelector('[name="' + CSS.escape(name) + '"]');
    } catch (e) { el = null; }
    if (el && vis(el)) formLeft++;
  }
  return {counts, present, formLeft, url: location.href};
}
"""

_REMOVE_BANNER_JS = f"""
() => {{
  const b = document.getElementById({BANNER_ID!r});
  if (b) {{ b.remove(); if (document.body) document.body.style.marginTop = ''; }}
  return true;
}}
"""


@dataclass
class _Snap:
    counts: list[int]
    present: list[bool]
    form_left: int
    url: str


async def _snapshot(page: Page, texts: list[str], sels: list[str],
                    controls: list[tuple[str, str]]) -> _Snap:
    d = await page.evaluate(_SNAPSHOT_JS, [BANNER_ID, texts, sels,
                                           [list(c) for c in controls]])
    counts = [int(x) for x in (d.get("counts") or [])][:len(texts)]
    present = [bool(x) for x in (d.get("present") or [])][:len(sels)]
    counts += [0] * (len(texts) - len(counts))
    present += [False] * (len(sels) - len(present))
    return _Snap(counts, present, int(d.get("formLeft") or 0), page.url)


# SEC-39: no single page call may outlive the fill_for_me deadline (an evaluate can hang
# forever while a navigation is paused in a route handler).
_CALL_TIMEOUT_S = 5.0


async def _eval_t(page: Page, js: str, arg: Any = None) -> Any:
    return await asyncio.wait_for(page.evaluate(js, arg), _CALL_TIMEOUT_S)


async def _snap_t(page: Page, texts: list[str], sels: list[str],
                  controls: list[tuple[str, str]]) -> _Snap:
    return await asyncio.wait_for(_snapshot(page, texts, sels, controls), _CALL_TIMEOUT_S)


def _merge_baseline(base: _Snap, now: _Snap) -> _Snap:
    """Before the first submit event, anything that shows up (late-rendered FAQ text, ...)
    becomes part of the baseline: it cannot be the result of submitting."""
    return _Snap([max(a, b) for a, b in zip(base.counts, now.counts, strict=True)],
                 [a or b for a, b in zip(base.present, now.present, strict=True)],
                 max(base.form_left, now.form_left), base.url)


def _path_of(url: str) -> str:
    from urllib.parse import urlsplit
    try:
        u = urlsplit(url)
    except ValueError:
        return url
    return (u.path or "/") + (f"?{u.query}" if u.query else "")


# Path segment (before a dot) or query key that means the site showed an error page.
# A confirmation such as /done is not in this set. HTTP status is not on the snapshot,
# and engine/browser.py is not ours to change, so the address is the signal we have.
_ERROR_SEGMENTS = frozenset({
    "error", "errors", "404", "403", "410", "500", "502", "503", "oops", "failure", "failed",
})
_ERROR_QUERY_KEYS = frozenset({"error", "errors", "error_code", "errcode"})
REASON_ERROR_PAGE = "error_page"

# Plain next step on the Assisted card. Codes stay in the result, the event and the log.
_NEXT_STEP: dict[str, str] = {
    "timeout": (
        "Next step: the site did not confirm it in time. "
        "Open the opt-out page and press Submit yourself."
    ),
    "window_closed": (
        "Next step: the window closed before the site confirmed it. "
        "Open the opt-out page and finish the form."
    ),
    REASON_ERROR_PAGE: (
        "Next step: the site showed an error page, not a success page. "
        "Open the opt-out page and try the form again."
    ),
}


def _error_segment(segment: str) -> bool:
    stem = segment.split(".", 1)[0]
    if stem in _ERROR_SEGMENTS:
        return True
    return stem.startswith("error-") or stem.endswith("-error")


def _url_is_error_page(url: str) -> bool:
    """True when the path or query names an error page. The query value is ignored."""
    from urllib.parse import parse_qsl, urlsplit
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    for segment in (parts.path or "").lower().split("/"):
        if segment and _error_segment(segment):
            return True
    for key, _value in parse_qsl(parts.query, keep_blank_values=True):
        if key.lower() in _ERROR_QUERY_KEYS:
            return True
    return False


def _missed_on_error_page(base_url: str, now_url: str) -> bool:
    """Success was not seen, and the address changed to an error page."""
    if _path_of(base_url) == _path_of(now_url):
        return False
    return _url_is_error_page(now_url)


def _todo_reason(reason: str) -> str | None:
    """What `_fallback_todo` should hear. `error:*` stays the generic assisted reason."""
    if reason in _NEXT_STEP:
        return reason
    if reason.startswith("error"):
        return "error"
    return None


def new_signal(base: _Snap, now: _Snap, url_pattern: str | None) -> str | None:
    """A success signal that was NOT there at baseline (SEC-32), or None."""
    if url_pattern and url_matches(url_pattern, now.url) and \
            not url_matches(url_pattern, base.url) and _path_of(now.url) != _path_of(base.url):
        return "success_url"
    if any(n > b for n, b in zip(now.counts, base.counts, strict=True)):
        return "success_text"
    if any(n and not b for n, b in zip(now.present, base.present, strict=True)):
        return "success_selector"
    # The filled form is gone (e.g. replaced by a thank-you page that repeats a phrase the
    # form page already had in its instructions) and a success phrase / selector is shown.
    if base.form_left > 0 and now.form_left == 0:
        if any(now.counts):
            return "success_text"
        if any(now.present):
            return "success_selector"
    return None


def _confirmed_listing(store: Store, profile_id: str, broker_id: str) -> tuple[
        Listing | None, list[Listing]]:
    lis = [li for li in store.list_listings(profile_id, broker_id) if li.gone_since is None]
    conf = [li for li in lis if li.match_level == MatchLevel.CONFIRMED]
    return (conf[0] if conf else None), lis


def _event(store: Store, profile_id: str, broker_id: str, action: str, actor: Actor = Actor.ENGINE,
           frm: ListingState | None = None, to: ListingState | None = None, **detail: Any) -> None:
    store.log(Event(profile_id=profile_id, broker_id=broker_id, actor=actor, action=action,
                    from_state=frm, to_state=to, detail=detail))


def _fallback_todo(store: Store, profile: Profile, broker: Broker, listings: list[Listing],
                   law: StateLaw | None, reason: str | None) -> str:
    """Make sure the Assisted card exists (deduplicated) and return its id.

    `timeout`, `window_closed` and `error_page` put a plain next step on a new card.
    An existing card is reused as-is (same id). `error` / `challenge` stay the words
    `assisted_todo` already knows.
    """
    from ..submitters import assisted
    from .handoff import persist_todo
    for t in store.list_todos(profile.id):
        if t.broker_id == broker.id and t.kind == TodoKind.ASSISTED_OPT_OUT:
            return t.id
    known = reason if reason in ("error", "challenge") else None
    todo = assisted.assisted_todo(profile, broker, listings, reason=known)
    step = _NEXT_STEP.get(reason or "")
    if step:
        todo = todo.model_copy(update={"body": step + "\n" + todo.body})
    return persist_todo(store, todo).id


def _record_success(store: Store, profile: Profile, broker: Broker, listing: Listing | None,
                    shots: list[tuple[bytes, str]], how: str) -> tuple[str, list[str]]:
    """Same bookkeeping as a successful web_form submission (runner._apply_outcome)."""
    from ..state import can_transition, mark_submitted, next_check_at, transition
    from ..submitters import base
    now = utcnow()
    conf = [listing] if listing else []
    req = Request(profile_id=profile.id, broker_id=broker.id, kind=RequestKind.OPT_OUT,
                  method=Method.WEB_FORM, listing_ids=[li.id for li in conf],
                  status=RequestStatus.SENT, created_at=now, sent_at=now)
    store.save_request(req)
    ev_ids: list[str] = []
    for png, caption in shots:
        ev = base.evidence(profile.id, broker.id, EvidenceKind.SCREENSHOT, "png",
                           listing_id=listing.id if listing else None, request_id=req.id,
                           caption=caption)
        ev_ids.append(store.save_evidence(ev, png).id)
    st = store.get_status(profile.id, broker.id)
    frm = st.state
    if st.state in (ListingState.UNKNOWN, ListingState.NOT_FOUND):
        st = transition(st, ListingState.FOUND, now)   # the person found it worth removing
    if can_transition(st.state, ListingState.SUBMITTED):
        st = mark_submitted(st, now)
        if broker.needs_email_verification:
            st = transition(st, ListingState.AWAITING_VERIFICATION, now)
        st = st.model_copy(update={"next_check_at": next_check_at(broker, st.state, now)})
        store.save_status(st)
    _event(store, profile.id, broker.id, "submitted", Actor.USER, frm, st.state,
           request_id=req.id, method=Method.WEB_FORM.value, via="fill_for_me", signal=how)
    for t in store.list_todos(profile.id):
        if t.broker_id == broker.id and t.kind in (TodoKind.ASSISTED_OPT_OUT,
                                                   TodoKind.CAPTCHA):
            store.complete_todo(t.id)
    return req.id, ev_ids


# --------------------------------------------------------------------------- entry point


async def fill_for_me(store: Store, profile_id: str, broker_id: str, *, timeout_s: int = 600,
                      registry: Registry | None = None, browser: BrowserManager | None = None,
                      headed: bool = True, cfg: cfgmod.Config | None = None,
                      state_laws: dict[str, StateLaw] | None = None,
                      on_ready: Callable[[Page], Awaitable[Any]] | None = None,
                      close_delay_s: float = 4.0) -> FillResult:
    """Open the broker's opt-out page in a visible window, fill it, let the person submit.

    `broker_id` may be a covered_by child; the parent's form is used. `browser` (an
    unstarted or started BrowserManager) is for tests; by default one is created and closed
    here. `on_ready(page)` runs (as a task) once the banner is up; tests use it to play the
    person. Never raises for page/browser problems: those return status "fallback".
    """
    from ..consent import consent_ok
    from . import tiers
    cfg = cfg or cfgmod.load()
    profile = store.get_profile(profile_id)
    if profile is None:
        return FillResult("refused", "no_profile", broker_id)
    ok, _why = consent_ok(profile, store)
    if not ok:
        return FillResult("refused", "consent", broker_id)
    if registry is None:
        from ..registry import load_registry
        registry = load_registry()
    try:
        broker = tiers.submit_target(registry.get(broker_id), registry)
    except KeyError:
        return FillResult("refused", "unknown_broker", broker_id)
    if state_laws is None:
        try:
            from ..registry import load_state_laws
            state_laws = load_state_laws()
        except Exception:  # noqa: BLE001
            state_laws = {}
    law = state_laws.get(profile.state_of_residence)
    practice = not cfg.real_submissions_enabled
    listing, listings = _confirmed_listing(store, profile.id, broker.id)
    if broker.id != broker_id:
        # covered_by child: the listing finder (D10) records the listing on the child site
        c_listing, c_listings = _confirmed_listing(store, profile.id, broker_id)
        listing = listing or c_listing
        listings = listings + [li for li in c_listings if li not in listings]
    res = FillResult("fallback", "", broker.id, practice_mode=practice)

    def fallback(reason: str) -> FillResult:
        res.status, res.reason = "fallback", reason
        res.todo_id = _fallback_todo(store, profile, broker, listings, law, _todo_reason(reason))
        # Codes and counts only: never the page address, the next-step sentence, or a value.
        log.info("fill_for_me fallback code=%s filled=%s submit_seen=%s",
                 reason[:40], len(res.filled), int(res.submit_seen))
        _event(store, profile.id, broker.id, "fill_for_me_fallback", reason=reason[:40],
               submit_seen=res.submit_seen)
        return res

    if broker.method != Method.WEB_FORM or not broker.opt_out_url:
        res.status, res.reason = "refused", "not_a_web_form"
        return res
    if broker.needs_id_upload and not profile.permissions.allow_id_upload:
        return fallback("id_upload")

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
            # SEC-36: the person may need the site's robot box; headed windows only.
            bctx = await bm.new_context(broker.domains, headed=headed,
                                        allow_captcha_frames=headed)
            page = await bctx.new_page()
        except Exception as e:  # noqa: BLE001 - no browser: the card still works
            log.warning("fill_for_me: browser unavailable (%s)", type(e).__name__)
            return fallback("browser_unavailable")
        try:
            return await _drive(store, profile, broker, listing, bm, page, res, timeout_s,
                                practice, on_ready, close_delay_s, fallback)
        except BlockedByPolicy:
            return fallback("blocked")
        except Exception as e:  # noqa: BLE001 - window closed mid-call, odd page, ...
            if page.is_closed():
                return fallback("window_closed")
            log.warning("fill_for_me failed: %s", type(e).__name__)
            return fallback(f"error:{type(e).__name__}")
    finally:
        if bctx is not None:
            try:
                await bctx.close()
            except Exception as e:  # noqa: BLE001
                log.debug("closing fill window failed: %s", type(e).__name__)
        if own:
            await bm.close()


async def _drive(store: Store, profile: Profile, broker: Broker, listing: Listing | None,
                 bm: BrowserManager, page: Page, res: FillResult, timeout_s: int,
                 practice: bool, on_ready: Callable[[Page], Awaitable[Any]] | None,
                 close_delay_s: float, fallback: Callable[[str], FillResult]) -> FillResult:
    from ..submitters.base import form_vars
    closed = {"v": False}
    page.on("close", lambda _p: closed.__setitem__("v", True))

    await bm.goto(page, str(broker.opt_out_url), check_challenge=False)
    values = filler.plan_values(profile, broker, listing)
    rep = await filler.fill_page(page, values)
    if broker.safe_checkboxes:
        rep.ticked = await filler.tick_safe_checkboxes(page, broker.safe_checkboxes)
    res.filled, res.not_found, res.withheld = (sorted(set(rep.filled)), rep.not_found,
                                               sorted(set(rep.withheld)))
    _event(store, profile.id, broker.id, "fill_for_me_filled", **rep.summary())
    if not rep.filled:
        return fallback("nothing_filled")
    # Kept only as a fallback: the evidence shot is taken when the person submits (SEC-37).
    filled_png = await page.screenshot(full_page=True)

    texts, sels = success_signals(broker, form_vars(profile, broker, listing))
    url_re = broker.success_url_pattern
    lines = [MSG_FILLED]
    if rep.not_found or rep.withheld or rep.unknown:
        lines.append(MSG_MISSING)
    if practice:
        lines.append(MSG_PRACTICE)
    lines.append(MSG_HINT)
    banner = _banner_js(lines, done=False)
    await page.evaluate(banner)
    controls = rep.controls
    hosts: set[str] = getattr(page.context, "freemyid_hosts", set())
    # "base" = the page as it was before the person submitted: taken now, merged with every
    # poll until the first submit event, and with a last look taken at that event itself.
    submit: dict[str, Any] = {"n": 0, "shot": None,
                              "base": await _snapshot(page, texts, sels, controls)}

    async def _watch(route: Any) -> None:
        """Submit-like events after the fill (SEC-32): a main-frame navigation, or an
        XHR/fetch POST to an allowed host. The page is captured while the request waits,
        i.e. exactly as the person sent it (SEC-37). Then the context route decides.

        SEC-39: while a main-frame navigation is paused in this handler, Playwright never
        answers a page.evaluate, so for navigations the baseline is the one from the last
        poll (no snapshot here), and the request is always released (finally)."""
        try:
            req = route.request
            try:
                nav = req.is_navigation_request() and req.frame == page.main_frame
                post = (req.resource_type in ("xhr", "fetch") and
                        req.method not in ("GET", "HEAD", "OPTIONS") and
                        bm.url_allowed(req.url, hosts))
            except Exception:  # noqa: BLE001 - no frame (worker): not a submit
                nav = post = False
            if nav or post:
                first = submit["n"] == 0
                submit["n"] += 1
                if first and post and not nav:   # the page before submitting
                    try:
                        submit["base"] = _merge_baseline(
                            submit["base"], await _snap_t(page, texts, sels, controls))
                    except Exception as e:  # noqa: BLE001 - keep the last poll's baseline
                        log.debug("submit-time baseline failed: %s", type(e).__name__)
                try:
                    submit["shot"] = await asyncio.wait_for(
                        page.screenshot(full_page=True), _CALL_TIMEOUT_S)
                except Exception as e:  # noqa: BLE001 - the fill-time shot is the fallback
                    log.debug("submit-time screenshot failed: %s", type(e).__name__)
        finally:
            try:
                await route.fallback()
            except Exception as e:  # noqa: BLE001 - route already handled / page closed
                log.debug("route fallback failed: %s", type(e).__name__)

    await page.route("**/*", _watch)
    task: asyncio.Task[Any] | None = (
        asyncio.ensure_future(on_ready(page)) if on_ready else None)

    loop = asyncio.get_running_loop()
    deadline = loop.time() + max(1, timeout_s)
    how: str | None = None
    seen_url = submit["base"].url
    try:
        while loop.time() < deadline:
            if closed["v"] or page.is_closed():
                return fallback("window_closed")
            bm.check_escaped(page)
            submitted_before = submit["n"] > 0
            res.submit_seen = res.submit_seen or submitted_before
            try:
                now = await _snap_t(page, texts, sels, controls)
                seen_url = now.url
                if not submitted_before:
                    if submit["n"] == 0:      # nothing was submitted while we looked
                        submit["base"] = _merge_baseline(submit["base"], now)
                else:
                    how = new_signal(submit["base"], now, url_re)
                    if how:
                        break
                # An error address mid-run is often a validation message the person can
                # fix and resubmit, so it never ends the fill early (the window would
                # close). error_page is decided from seen_url when the time runs out.
                if await _eval_t(page, _NEEDS_BANNER_JS):
                    await _eval_t(page, banner)   # page reloaded (e.g. a validation error)
            except Exception:  # noqa: BLE001 - mid-navigation; try again next tick
                if closed["v"] or page.is_closed():
                    return fallback("window_closed")
            await asyncio.sleep(_POLL_S)
        if how is None:
            if _missed_on_error_page(submit["base"].url, seen_url):
                return fallback(REASON_ERROR_PAGE)
            if not (texts or sels or url_re) and res.submit_seen:
                return fallback("unverified")
            return fallback("timeout")
        bm.check_escaped(page)
        try:
            await _eval_t(page, _REMOVE_BANNER_JS)       # SEC-37: no banner in the proof
        except Exception:  # noqa: BLE001, S110 - mid-navigation: shoot what is there
            pass
        done_png = await page.screenshot(full_page=True)
        sent_png = submit["shot"]
        shots = [(sent_png, "form as sent") if sent_png else
                 (filled_png, "form filled by Free My ID"), (done_png, "confirmation page")]
        res.request_id, res.evidence_ids = _record_success(store, profile, broker, listing,
                                                           shots, how)
        res.status, res.reason = "submitted", how
        try:
            await _eval_t(page, _banner_js([MSG_DONE], done=True))
            if close_delay_s > 0:
                await asyncio.sleep(close_delay_s)
        except Exception:  # noqa: BLE001, S110 - person closed the window already
            pass
        return res
    finally:
        if task is not None and not task.done():
            task.cancel()


def fill_for_me_sync(store: Store, profile_id: str, broker_id: str, **kw: Any) -> FillResult:
    """Blocking wrapper for the wizard (safe to call from a thread or with a loop running)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(fill_for_me(store, profile_id, broker_id, **kw))
    box: dict[str, Any] = {}

    def _t() -> None:
        try:
            box["r"] = asyncio.run(fill_for_me(store, profile_id, broker_id, **kw))
        except BaseException as e:  # noqa: BLE001
            box["e"] = e

    th = threading.Thread(target=_t, name="freemyid-fill", daemon=True)
    th.start()
    th.join()
    if "e" in box:
        raise box["e"]
    return box["r"]
