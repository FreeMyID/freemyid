"""Automatic tier: data-driven search (`Broker.search`) and opt-out (`Broker.form`).

No per-broker Python. Every request goes through BrowserManager (NetPolicy allowlist,
honest UA, polite delays). A challenge page, an unexpected page or ANY error drops the
broker to the Assisted tier (an ASSISTED_OPT_OUT to-do) instead of failing the run. In an
interactive run a challenge is first handed to the person in a visible window
(HumanHandoff); Free My ID never solves it.

Page text is data: it is only matched against selectors / expected text, never obeyed.
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import quote, urljoin, urlsplit

from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

from ..engine import matcher
from ..engine.browser import BlockedByPolicy, ChallengeEncountered
from ..interfaces import RunContext, Submitter
from ..models import (
    Address,
    Broker,
    EvidenceKind,
    FormStep,
    Listing,
    ListingState,
    Method,
    PersonName,
    Profile,
    Request,
    RequestKind,
    RequestStatus,
    SubmitOutcome,
    Todo,
    TodoKind,
    utcnow,
)
from ..netpolicy import _host_ok, host_of
from . import assisted, base

if TYPE_CHECKING:
    from playwright.async_api import Page

    from ..engine.browser import BrowserManager

log = logging.getLogger(__name__)

_env = SandboxedEnvironment(undefined=StrictUndefined, autoescape=False)
MAX_RESULTS = 25


class UnexpectedPage(Exception):
    """The page did not look like the registry said it would (PII-free label)."""


class HumanStep(Exception):
    """A `human` form step: a person has to do this part."""


def _is_timeout(exc: BaseException) -> bool:
    """Playwright's TimeoutError is not asyncio's. Both classes are named TimeoutError."""
    return type(exc).__name__ == "TimeoutError"


# --------------------------------------------------------------------------- search


def _slug(s: str, case: str = "lower") -> str:
    """Whitespace -> '-', URL-encoded. `case` is Broker.slug_case: lower (default), title
    ("John-Smith", "Springfield") or as_is."""
    s = re.sub(r"\s+", "-", s.strip())
    if case == "title":
        s = "-".join(p[:1].upper() + p[1:].lower() for p in s.split("-"))
    elif case != "as_is":
        s = s.lower()
    return quote(s, safe="-")


def on_broker_url(broker: Broker, url: str) -> bool:
    """A URL taken from a broker page (or built for it) really points at the broker
    (SEC-89): `host_of` must accept it (no backslash host confusion such as
    `https://evil.example\\@broker/`, no whitespace or control characters), it has no
    user:password part, and the host is one of `broker.domains`."""
    host = host_of(url)
    if not host:
        return False
    try:
        u = urlsplit(url)
    except ValueError:
        return False
    return not u.username and not u.password and _host_ok(host, set(broker.domains))


def current_address(profile: Profile) -> Address:
    """The address searches use: the one marked current, else the first."""
    return next((a for a in profile.addresses if a.current), profile.addresses[0])


def search_url(broker: Broker, profile: Profile, address: Address | None = None,
               name: PersonName | None = None) -> str | None:
    """Fill Broker.search_url_pattern. Phone only with allow_phone_disclosure. `address`
    (default: the current one) supplies city/state/zip, e.g. for an old-address search;
    `name` (default: the current one) supplies first/middle/last, e.g. a maiden name."""
    if not broker.search_url_pattern or profile.value_only:
        return None          # BL-IN-08: a phone/email-only removal has no name search
    cur = address or current_address(profile)
    nm = name or profile.name
    vals: dict[str, str | None] = {
        "first": nm.first, "last": nm.last,
        "middle": nm.middle, "city": cur.city, "state": cur.state,
        "state_name": matcher.STATE_NAMES.get(cur.state, cur.state), "zip": cur.zip,
        "phone": matcher.digits(profile.phones[0])
        if profile.phones and profile.permissions.allow_phone_disclosure else None,
    }
    import string
    fields = {f for _, f, _, _ in string.Formatter().parse(broker.search_url_pattern) if f}
    if any(not vals.get(f) for f in fields):
        return None
    case = broker.slug_case
    # a 2-letter {state} stays upper case in title mode (".../Springfield/IL")
    url = broker.search_url_pattern.format(**{
        f: _slug(str(vals[f]), "as_is" if case == "title" and f == "state" else case)
        for f in fields})
    return url if on_broker_url(broker, url) else None


async def _text(el: Any, sel: str | None) -> str | None:
    if not sel:
        return None
    sub = await el.query_selector(sel)
    if sub is None:
        return None
    t = (await sub.inner_text()).strip()
    return t[:500] or None


def _split(t: str | None) -> list[str]:
    if not t:
        return []
    return [p.strip() for p in re.split(r"[\n;|]+|\s+-\s+", t) if p.strip()][:20]


async def parse_results(page: Page, broker: Broker) -> list[matcher.Candidate]:
    """Candidates from a results page using Broker.search selectors. Links off the broker's
    domains are dropped."""
    spec = broker.search
    if spec is None or not spec.result_selector:
        return []
    out: list[matcher.Candidate] = []
    for el in (await page.query_selector_all(spec.result_selector))[:MAX_RESULTS]:
        href = None
        if spec.link_selector:
            a = await el.query_selector(spec.link_selector)
            href = await a.get_attribute("href") if a else None
        url = urljoin(page.url, href) if href else page.url
        if not on_broker_url(broker, url):      # SEC-89
            continue
        name = await _text(el, spec.name_selector)
        locs = _split(await _text(el, spec.location_selector))
        out.append(matcher.Candidate(
            url=url, name=name, age=matcher.parse_age(await _text(el, spec.age_selector)),
            locations=locs, relatives=_split(await _text(el, spec.relatives_selector))))
    return out


def value_search_urls(broker: Broker, profile: Profile) -> list[str]:
    """BL-IN-08: reverse-lookup URLs for a phone/email-only removal (one per value, at most
    3). Each value goes out only with its explicit disclosure permission."""
    from urllib.parse import quote

    from ..engine.tiers import lookup_pattern
    pat = lookup_pattern(broker, profile)
    if not pat:
        return []
    out: list[str] = []
    if profile.removal_scope == "phone" and profile.permissions.allow_phone_disclosure:
        for ph in profile.phones[:3]:
            d = matcher.digits(ph)
            if len(d) == 10:
                out.append(pat.format(phone_digits=d,
                                      phone_dashed=f"{d[:3]}-{d[3:6]}-{d[6:]}"))
    elif profile.removal_scope == "email" and profile.permissions.allow_email_disclosure:
        for em in profile.emails[:3]:
            if "@" in em:
                out.append(pat.format(email=quote(em.strip().lower(), safe="")))
    return [u for u in dict.fromkeys(out) if on_broker_url(broker, u)]


async def _search_page(bm: BrowserManager, ctx: RunContext, url: str, *,
                       lookup: str | None = None) -> tuple[list[Listing], bytes | None]:
    """Read one search page: (scored listings, screenshot when any were found).
    `lookup` ("phone" / "email"): a BL-IN-08 reverse-lookup page, scored by value."""
    bctx = await bm.new_context(ctx.broker.domains)
    try:
        page = await bctx.new_page()
        resp = await bm.goto(page, url)
        if resp is not None and resp.status >= 400:
            # an error page is not "no results": never record NOT_FOUND from it
            raise UnexpectedPage(f"search_http_{resp.status}")
        spec = ctx.broker.search
        html = await page.content()
        if spec and spec.no_results_text and spec.no_results_text.lower() in html.lower():
            return [], None
        cands = await parse_results(page, ctx.broker)
        if not cands:
            # neither results nor the site's "no results" text: the page changed (CR-C)
            raise UnexpectedPage("search_page_unrecognized")
        today = (ctx.now or utcnow()).date()
        listings = (matcher.score_lookup(ctx.profile, ctx.broker.id, cands, lookup, today)
                    if lookup else matcher.score_all(ctx.profile, ctx.broker.id, cands, today))
        shot = await page.screenshot(full_page=True) if listings else None
        return listings, shot
    finally:
        await bctx.close()


def extra_search_urls(ctx: RunContext) -> list[str]:
    """Old-address / previous-name search URLs, per ctx.scratch["search_variants"] (the
    runner fills it from the same config flags the exposure scan uses)."""
    from ..engine.exposure import old_address_url, previous_name_url
    want = ctx.scratch.get("search_variants") or {}
    urls = []
    if want.get("old_addresses"):
        urls.append(old_address_url(ctx.broker, ctx.profile))
    if want.get("previous_names"):
        urls.append(previous_name_url(ctx.broker, ctx.profile))
    return [u for u in urls if u]


async def search_listings(ctx: RunContext) -> list[Listing]:
    """Search one broker with the browser; stores a page screenshot in ctx.scratch. Extra
    pages (old address / previous name) are merged in; if one cannot be read, the listings
    stored from earlier searches are kept as they are (unknown, never marked gone)."""
    bm: BrowserManager = ctx.scratch["browser"]
    if ctx.profile.value_only:
        return await _search_values(bm, ctx)
    url = search_url(ctx.broker, ctx.profile)
    if url is None:
        raise UnexpectedPage("search_url_unavailable")
    listings, shot = await _search_page(bm, ctx, url)
    seen = {li.url for li in listings}
    unread = False
    for extra in extra_search_urls(ctx):
        try:
            more, more_shot = await _search_page(bm, ctx, extra)
        except Exception as e:  # noqa: BLE001 - the main answer still counts
            # incl. a challenge: never bypassed, and never read as "nothing there"
            log.info("search: %s extra page skipped (%s)", ctx.broker.id, type(e).__name__)
            unread = True
            continue
        shot = shot or more_shot
        for li in more:
            if li.url not in seen:
                seen.add(li.url)
                listings.append(li)
    if unread:
        from ..engine.runner import keep_unchecked
        listings = keep_unchecked(ctx.store, ctx.profile, ctx.broker, listings)
        # SEC-104: the runner never treats these as new send targets
        ctx.scratch["unchecked_urls"] = {li.url for li in listings} - seen
    if shot is not None:
        ctx.scratch["search_screenshot"] = shot
    return listings


async def _search_values(bm: BrowserManager, ctx: RunContext) -> list[Listing]:
    """BL-IN-08: read each reverse-lookup page. Any unreadable page fails the whole search
    (never read as "nothing there"); the runner then treats the broker as not scanned."""
    urls = value_search_urls(ctx.broker, ctx.profile)
    if not urls:
        raise UnexpectedPage("search_url_unavailable")
    kind = str(ctx.profile.removal_scope)
    listings: list[Listing] = []
    seen: set[str] = set()
    shot = None
    for url in urls:
        found, more_shot = await _search_page(bm, ctx, url, lookup=kind)
        shot = shot or more_shot
        for li in found:
            if li.url not in seen:
                seen.add(li.url)
                listings.append(li)
    if shot is not None:
        ctx.scratch["search_screenshot"] = shot
    return listings


# --------------------------------------------------------------------------- form


def render_value(tpl: str | None, vars: dict) -> str:
    return _env.from_string(tpl or "").render(**vars)


async def run_steps(bm: BrowserManager, page: Page, steps: list[FormStep], vars: dict,
                    shots: list[bytes]) -> None:
    """Execute declarative steps. Raises ChallengeEncountered / UnexpectedPage / HumanStep."""
    for st in steps:
        a = st.action
        if a == "human":
            raise HumanStep(st.note or "human step")
        if a == "goto":
            await bm.goto(page, render_value(st.url, vars), timeout_ms=st.timeout_ms)
            continue
        sel = st.selector or ""
        if a in ("fill", "select", "check", "click", "wait_for", "submit") and not sel:
            raise UnexpectedPage(f"step_{a}_without_selector")
        if a == "fill":
            await page.fill(sel, render_value(st.value, vars), timeout=st.timeout_ms)
        elif a == "select":
            await page.select_option(sel, render_value(st.value, vars),
                                     timeout=st.timeout_ms)
        elif a == "check":
            await page.check(sel, timeout=st.timeout_ms)
        elif a == "wait_for":
            await page.wait_for_selector(sel, timeout=st.timeout_ms)
        elif a in ("click", "submit"):
            await page.click(sel, timeout=st.timeout_ms)
            await page.wait_for_load_state("domcontentloaded", timeout=st.timeout_ms)
            bm.check_escaped(page)          # SEC-16: a submit may redirect off-list
            await bm.raise_if_challenge(page)
        elif a == "screenshot":
            shots.append(await page.screenshot(full_page=True))
        elif a == "expect_text":
            want = render_value(st.value, vars)
            if want.lower() not in (await page.inner_text("body")).lower():
                raise UnexpectedPage("expected_text_missing")


class WebFormSubmitter(Submitter):
    method = "web_form"

    async def search(self, ctx: RunContext) -> list[Listing]:
        return await search_listings(ctx)

    async def submit(self, ctx: RunContext, listings: list[Listing]) -> SubmitOutcome:
        if ctx.dry_run:
            raise RuntimeError("submit() must never be called in a dry run")
        now = ctx.now or utcnow()
        use = base.confirmed(listings)
        uses_listing = any("listing" in (s.value or "") + (s.url or "") for s in ctx.broker.form)
        if uses_listing and not use:
            return self._fallback(ctx, listings, "no_confirmed_listing")
        targets: list[Listing | None] = list(use) if uses_listing else [use[0] if use else None]
        req = Request(profile_id=ctx.profile.id, broker_id=ctx.broker.id,
                      kind=ctx.scratch.get("kind", RequestKind.OPT_OUT), method=Method.WEB_FORM,
                      listing_ids=[li.id for li in use], created_at=now)
        evs = []
        try:
            for li in targets:
                shots = await self._fill_one(ctx, li)
                for i, png in enumerate(shots):
                    ev = base.evidence(ctx.profile.id, ctx.broker.id, EvidenceKind.SCREENSHOT,
                                       "png", listing_id=li.id if li else None,
                                       request_id=req.id,
                                       caption="confirmation page" if i == len(shots) - 1
                                       else "form step")
                    evs.append(ctx.store.save_evidence(ev, png))
        except ChallengeEncountered as e:
            return self._fallback(ctx, listings, "challenge", detail=e.kind)
        except HumanStep:
            return self._fallback(ctx, listings, "human_step")
        except UnexpectedPage as e:
            return self._fallback(ctx, listings, "unexpected_page", detail=type(e).__name__)
        except BlockedByPolicy as e:
            return self._fallback(ctx, listings, "blocked_by_policy", detail=type(e).__name__)
        except Exception as e:  # noqa: BLE001 - any error drops to Assisted (D1)
            reason = "timeout" if _is_timeout(e) else "error"
            return self._fallback(ctx, listings, reason, detail=type(e).__name__)
        req = req.model_copy(update={"status": RequestStatus.SENT, "sent_at": now})
        ctx.store.save_request(req)
        new = (ListingState.AWAITING_VERIFICATION if ctx.broker.needs_email_verification
               else ListingState.SUBMITTED)
        return SubmitOutcome(new_state=new, request=req, evidence=evs, message="form_submitted")

    async def _fill_one(self, ctx: RunContext, listing: Listing | None) -> list[bytes]:
        bm: BrowserManager = ctx.scratch["browser"]
        vars = base.form_vars(ctx.profile, ctx.broker, listing)
        bctx = await bm.new_context(ctx.broker.domains)
        shots: list[bytes] = []
        try:
            page = await bctx.new_page()
            if ctx.broker.form[0].action != "goto" and ctx.broker.opt_out_url:
                await bm.goto(page, str(ctx.broker.opt_out_url))
            try:
                await run_steps(bm, page, ctx.broker.form, vars, shots)
            except ChallengeEncountered as e:
                if not ctx.interactive:
                    raise
                todo = Todo(profile_id=ctx.profile.id, broker_id=ctx.broker.id,
                            kind=TodoKind.CAPTCHA,
                            title=f"{ctx.broker.name} wants a human check",
                            body="Finish the check in the window that opened, then come back.",
                            links=[page.url])
                if not await ctx.handoff.request(todo, page):
                    raise
                await bm.raise_if_challenge(page)
                del e
            shots.append(await page.screenshot(full_page=True))
            return shots
        finally:
            await bctx.close()

    def _fallback(self, ctx: RunContext, listings: list[Listing], reason: str,
                  detail: str | None = None) -> SubmitOutcome:
        from ..engine.outbox import record_manual_letter
        todo = assisted.todo_for(ctx.profile, ctx.broker, listings, ctx.state_law, reason=reason)
        todo = record_manual_letter(ctx.store, todo, listings,
                                    kind=ctx.scratch.get("kind", RequestKind.OPT_OUT),
                                    dry_run=ctx.dry_run, now=ctx.now)
        msg = f"fallback_assisted:{reason}" + (f":{detail}" if detail else "")
        return SubmitOutcome(new_state=ListingState.NEEDS_HUMAN, todos=[todo], message=msg)
