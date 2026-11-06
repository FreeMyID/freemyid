"""Automatic tier: data-driven search (`Broker.search`) and opt-out (`Broker.form`).

No per-broker Python. Every request goes through BrowserManager (NetPolicy allowlist,
honest UA, polite delays). A challenge page, an unexpected page or ANY error drops the
broker to the Assisted tier (an ASSISTED_OPT_OUT to-do) instead of failing the run. In an
interactive run a challenge is first handed to the person in a visible window
(HumanHandoff); Vanish never solves it.

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
    Broker,
    EvidenceKind,
    FormStep,
    Listing,
    ListingState,
    Method,
    Profile,
    Request,
    RequestKind,
    RequestStatus,
    SubmitOutcome,
    Todo,
    TodoKind,
    utcnow,
)
from ..netpolicy import _host_ok
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


# --------------------------------------------------------------------------- search


def _slug(s: str) -> str:
    return quote(re.sub(r"\s+", "-", s.strip().lower()), safe="-")


def search_url(broker: Broker, profile: Profile) -> str | None:
    """Fill Broker.search_url_pattern. Phone only with allow_phone_disclosure."""
    if not broker.search_url_pattern:
        return None
    cur = next((a for a in profile.addresses if a.current), profile.addresses[0])
    vals: dict[str, str | None] = {
        "first": profile.name.first, "last": profile.name.last,
        "middle": profile.name.middle, "city": cur.city, "state": cur.state,
        "state_name": matcher.STATE_NAMES.get(cur.state, cur.state), "zip": cur.zip,
        "phone": matcher.digits(profile.phones[0])
        if profile.phones and profile.permissions.allow_phone_disclosure else None,
    }
    import string
    fields = {f for _, f, _, _ in string.Formatter().parse(broker.search_url_pattern) if f}
    if any(not vals.get(f) for f in fields):
        return None
    url = broker.search_url_pattern.format(**{f: _slug(str(vals[f])) for f in fields})
    return url if _host_ok(urlsplit(url).hostname or "", set(broker.domains)) else None


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
    return [p.strip() for p in re.split(r"[\n;|]+", t) if p.strip()][:20]


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
        if not _host_ok(urlsplit(url).hostname or "", set(broker.domains)):
            continue
        name = await _text(el, spec.name_selector)
        locs = _split(await _text(el, spec.location_selector))
        out.append(matcher.Candidate(
            url=url, name=name, age=matcher.parse_age(await _text(el, spec.age_selector)),
            locations=locs, relatives=_split(await _text(el, spec.relatives_selector))))
    return out


async def search_listings(ctx: RunContext) -> list[Listing]:
    """Search one broker with the browser; stores a page screenshot in ctx.scratch."""
    bm: BrowserManager = ctx.scratch["browser"]
    url = search_url(ctx.broker, ctx.profile)
    if url is None:
        raise UnexpectedPage("search_url_unavailable")
    bctx = await bm.new_context(ctx.broker.domains)
    try:
        page = await bctx.new_page()
        await bm.goto(page, url)
        spec = ctx.broker.search
        html = await page.content()
        if spec and spec.no_results_text and spec.no_results_text.lower() in html.lower():
            return []
        cands = await parse_results(page, ctx.broker)
        listings = matcher.score_all(ctx.profile, ctx.broker.id, cands,
                                     (ctx.now or utcnow()).date())
        if listings:
            ctx.scratch["search_screenshot"] = await page.screenshot(full_page=True)
        return listings
    finally:
        await bctx.close()


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
        except (UnexpectedPage, BlockedByPolicy) as e:
            return self._fallback(ctx, listings, "error", detail=type(e).__name__)
        except Exception as e:  # noqa: BLE001 - any error drops to Assisted (D1)
            return self._fallback(ctx, listings, "error", detail=type(e).__name__)
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
        todo = assisted.todo_for(ctx.profile, ctx.broker, listings, ctx.state_law,
                                 reason="challenge" if reason == "challenge" else "error")
        msg = f"fallback_assisted:{reason}" + (f":{detail}" if detail else "")
        return SubmitOutcome(new_state=ListingState.NEEDS_HUMAN, todos=[todo], message=msg)
