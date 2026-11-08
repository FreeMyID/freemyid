""""Find me first" exposure scan (ROADMAP 3.2, docs/EXPOSURE.md).

For one person, look at every enabled broker that has a `search_url_pattern`, once:

* build the search URL from name + current city/state (`web_form.search_url`, which honours
  `Broker.slug_case`);
* `search_access`:
    open         one plain HTTPS GET (honest User-Agent, no cookies, at most 2 redirects that
                 stay on the broker's domains, every hop checked by NetPolicy);
    js_required  one page load in the headless browser (BrowserManager: NetPolicy routing,
                 challenge detection), only when a browser fetcher is available;
    bot_blocked / unknown, or anything that fails  -> "check by hand" with the URL to open.
  Bot protection is never worked around: a challenge page is "check by hand", full stop;
* read the results with the registry's `Broker.search` selectors (engine.htmlsel, no
  scripts run) and score them with the existing matcher (confirmed / possible / no match);
* save matched listings exactly as a `scan` does (runner.merge_listings) and record the scan
  as one PII-free Event (`action="exposure_scan"`: ids, levels, signal names, counts,
  timestamps, score lines). No HTML is kept. URLs live only in the encrypted listings table
  and are re-derived from the profile for "check by hand" rows.

The exposure score (0-100) and its plain-English lines come from `score_entries`.
Dashboard hook: `latest_exposure(store, profile)`.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin, urlsplit

from .. import __version__
from .. import config as cfgmod
from ..checklist_state import drop_first
from ..exposure_models import (
    ExposureEntry,
    ExposureListing,
    ExposureResult,
    ScoreLine,
)
from ..models import Actor, Broker, Event, Listing, MatchLevel, ProfileField, utcnow
from . import htmlsel, matcher

if TYPE_CHECKING:
    from ..models import Profile, Registry
    from ..netpolicy import NetPolicy
    from ..storage import Store

log = logging.getLogger(__name__)

USER_AGENT = f"FreeMyID/{__version__} (+https://freemyid.org/safety/)"
EVENT_ACTION = "exposure_scan"
CHECK_ACTION = "exposure_check"
MAX_BYTES = 2_000_000
MAX_REDIRECTS = 2
TIMEOUT_S = 20.0
CACHE_HOURS = 24
_HEADERS = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.8"}
_MAX_RESULTS = 25

# score weights (docs/EXPOSURE.md; change both together)
W_CONFIRMED_SITE = 15
W_EXTRA_LISTING = 5
MAX_EXTRA_PER_SITE = 2
W_CONTACT = 5
W_POSSIBLE_SITE = 5
W_RELATIVE = 2
MAX_RELATIVE_POINTS = 10


class ExposureRefused(Exception):
    """No scan: unknown profile or no valid consent. `reason` is safe to show."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class FetchFailed(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason     # an HAND_REASONS key


@dataclass
class Fetched:
    url: str         # logical (https, broker) URL of the final page
    status: int
    html: str


Fetcher = Callable[[Broker, str], Fetched]


# --------------------------------------------------------------------------- fetching


def _on_broker(broker: Broker, url: str, policy: NetPolicy) -> bool:
    from ..netpolicy import _host_ok, host_of
    try:
        u = urlsplit(url)
    except ValueError:
        return False
    host = host_of(url) or ""
    return (u.scheme == "https" and not u.username and not u.password and bool(host)
            and _host_ok(host, set(broker.domains)) and policy.is_allowed(url))


def http_fetcher(policy: NetPolicy, fixture_base: str | None = None,
                 client: Any = None) -> Fetcher:
    """One plain GET per broker. `fixture_base` (dev only) answers https://host/path from the
    local fixture server, the same mapping BrowserManager uses."""
    import httpx

    from .browser import fixture_url

    def fetch(broker: Broker, url: str) -> Fetched:
        cl = client or httpx.Client(timeout=TIMEOUT_S, follow_redirects=False)
        try:
            cur = url
            for _hop in range(MAX_REDIRECTS + 1):
                if not _on_broker(broker, cur, policy):
                    raise FetchFailed("blocked_by_policy")
                real = fixture_url(fixture_base, cur) if fixture_base else cur
                try:
                    with cl.stream("GET", real, headers=_HEADERS) as r:
                        if r.status_code in (301, 302, 303, 307, 308):
                            loc = r.headers.get("location")
                            if not loc:
                                raise FetchFailed("http_error")
                            cur = urljoin(cur, loc)
                            continue
                        body = b""
                        for chunk in r.iter_bytes():
                            body += chunk
                            if len(body) > MAX_BYTES:
                                raise FetchFailed("too_large")
                        enc = r.encoding or "utf-8"
                        return Fetched(cur, r.status_code, body.decode(enc, errors="replace"))
                except httpx.HTTPError as e:
                    raise FetchFailed("network") from e
            raise FetchFailed("http_error")       # too many redirects
        finally:
            if client is None:
                cl.close()

    return fetch


class BrowserFetcher:
    """js_required brokers: one headless page load each through BrowserManager (NetPolicy
    routing, challenge detection, no retries). Started lazily, closed by `close()`."""

    def __init__(self, policy: NetPolicy, cfg: cfgmod.Config,
                 fixture_base: str | None = None) -> None:
        self.policy, self.cfg, self.fixture_base = policy, cfg, fixture_base
        self._loop: asyncio.AbstractEventLoop | None = None
        self._bm: Any = None

    def __call__(self, broker: Broker, url: str) -> Fetched:
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
        return self._loop.run_until_complete(self._fetch(broker, url))

    async def _fetch(self, broker: Broker, url: str) -> Fetched:
        from .browser import BlockedByPolicy, BrowserManager, ChallengeEncountered
        if not _on_broker(broker, url, self.policy):
            raise FetchFailed("blocked_by_policy")
        if self._bm is None:
            cfg = self.cfg.model_copy(update={"max_retries": 1})
            self._bm = BrowserManager(self.policy, headless=True, cfg=cfg,
                                      fixture_base=self.fixture_base)
            try:
                await self._bm.start()
            except Exception as e:
                self._bm = None
                raise FetchFailed("needs_browser") from e
        bctx = await self._bm.new_context(broker.domains)
        try:
            page = await bctx.new_page()
            try:
                resp = await self._bm.goto(page, url)
            except ChallengeEncountered as e:
                raise FetchFailed("challenge") from e
            except BlockedByPolicy as e:
                raise FetchFailed("blocked_by_policy") from e
            except Exception as e:
                raise FetchFailed("network") from e
            return Fetched(page.url if page.url.startswith("https://") else url,
                           resp.status if resp else 200, await page.content())
        finally:
            await bctx.close()

    def close(self) -> None:
        if self._loop is None:
            return
        if self._bm is not None:
            self._loop.run_until_complete(self._bm.close())
        self._loop.close()
        self._loop = None


# --------------------------------------------------------------------------- parsing


def _split(t: str | None) -> list[str]:
    import re
    if not t:
        return []
    return [p.strip() for p in re.split(r"[\n;|]+", t) if p.strip()][:20]


def parse_candidates(broker: Broker, page_url: str, html: str) -> list[matcher.Candidate]:
    """Same reading as web_form.parse_results, on static HTML. Raises
    htmlsel.UnsupportedSelector for selectors the subset cannot run."""
    from ..submitters.web_form import on_broker_url
    spec = broker.search
    if spec is None or not spec.result_selector:
        return []
    root = htmlsel.parse(html)

    def txt(el: htmlsel.Node, sel: str | None) -> str | None:
        if not sel:
            return None
        sub = el.select_one(sel)
        t = sub.text().strip() if sub is not None else ""
        return t[:500] or None

    out: list[matcher.Candidate] = []
    for el in root.select(spec.result_selector)[:_MAX_RESULTS]:
        href = None
        if spec.link_selector:
            a = el.select_one(spec.link_selector)
            href = a.get("href") if a is not None else None
        url = urljoin(page_url, href) if href else page_url
        if urlsplit(url).scheme != "https" or not on_broker_url(broker, url):   # SEC-89
            continue
        out.append(matcher.Candidate(
            url=url, name=txt(el, spec.name_selector),
            age=matcher.parse_age(txt(el, spec.age_selector)),
            locations=_split(txt(el, spec.location_selector)),
            relatives=_split(txt(el, spec.relatives_selector))))
    return out


# --------------------------------------------------------------------------- scoring


def _contact(li: Listing) -> bool:
    return bool({ProfileField.PHONE, ProfileField.STREET_ADDRESS} & set(li.shown_fields))


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def score_entries(entries: list[ExposureEntry]) -> tuple[int, list[ScoreLine]]:
    """Exposure score 0-100 plus the lines that explain it (docs/EXPOSURE.md)."""
    confirmed = [e for e in entries if e.match_level == MatchLevel.CONFIRMED]
    possible = [e for e in entries if e.match_level == MatchLevel.POSSIBLE]
    lines: list[ScoreLine] = []
    if confirmed:
        lines.append(ScoreLine(points=W_CONFIRMED_SITE * len(confirmed), text=(
            f"{_plural(len(confirmed), 'site shows', 'sites show')} a listing that is you "
            f"({W_CONFIRMED_SITE} points each)")))
        extra = sum(min(MAX_EXTRA_PER_SITE, sum(
            1 for li in e.listings if li.match_level == MatchLevel.CONFIRMED) - 1)
            for e in confirmed)
        if extra > 0:
            lines.append(ScoreLine(points=W_EXTRA_LISTING * extra, text=(
                f"{_plural(extra, 'extra listing', 'extra listings')} of you on the same "
                f"sites ({W_EXTRA_LISTING} points each, up to {MAX_EXTRA_PER_SITE} per site)")))
        contact = sum(1 for e in confirmed if any(
            li.contact_shown for li in e.listings if li.match_level == MatchLevel.CONFIRMED))
        if contact:
            lines.append(ScoreLine(points=W_CONTACT * contact, text=(
                f"{_plural(contact, 'of them shows', 'of them show')} your phone number or "
                f"street address ({W_CONTACT} points each)")))
        rel = sum(li.relatives_shown for e in confirmed for li in e.listings
                  if li.match_level == MatchLevel.CONFIRMED)
        if rel:
            lines.append(ScoreLine(points=min(MAX_RELATIVE_POINTS, W_RELATIVE * rel), text=(
                f"{_plural(rel, 'relative or associate is', 'relatives or associates are')} "
                f"named next to you ({W_RELATIVE} points each, up to {MAX_RELATIVE_POINTS})")))
    if possible:
        lines.append(ScoreLine(points=W_POSSIBLE_SITE * len(possible), text=(
            f"{_plural(len(possible), 'site may show', 'sites may show')} you; please look "
            f"and tell us ({W_POSSIBLE_SITE} points each)")))
    raw = sum(ln.points for ln in lines)
    if raw > 100:
        lines.append(ScoreLine(points=100 - raw, text="The score stops at 100"))
    hand = sum(1 for e in entries if e.status == "check_by_hand" and e.match_level is None)
    if hand:
        lines.append(ScoreLine(points=0, text=(
            f"{_plural(hand, 'site', 'sites')} could not be checked automatically; open "
            f"{'it' if hand == 1 else 'them'} yourself (not counted)")))
    if not lines:
        lines.append(ScoreLine(points=0, text="No listings of you were found on the sites "
                                              "we checked"))
    return max(0, min(100, raw)), lines


# --------------------------------------------------------------------------- scan


def _exp_listing(li: Listing) -> ExposureListing:
    return ExposureListing(url=li.url, match_level=li.match_level,
                           signals=sorted(r for r in li.match_reasons
                                          if r in {"city", "age", "relative", "phone", "email",
                                                   "user_confirmed"}),
                           contact_shown=_contact(li), relatives_shown=len(li.relatives_shown))


def _fill(entry: ExposureEntry, listings: list[Listing]) -> ExposureEntry:
    live = sorted((li for li in listings
                   if li.gone_since is None and li.match_level != MatchLevel.NO_MATCH),
                  key=lambda x: (x.match_level != MatchLevel.CONFIRMED, -x.match_score))
    entry.listings = [_exp_listing(li) for li in live]
    if entry.listings:
        entry.match_level = (MatchLevel.CONFIRMED if any(
            x.match_level == MatchLevel.CONFIRMED for x in entry.listings)
            else MatchLevel.POSSIBLE)
        entry.signals = sorted({s for x in entry.listings for s in x.signals})
    return entry


def scan_brokers(registry: Registry) -> list[Broker]:
    """Enabled brokers with a search URL pattern, highest priority first."""
    return sorted((b for b in registry.brokers if b.enabled and b.search_url_pattern),
                  key=lambda b: (-b.priority, b.id))


def _hand_check_url(broker: Broker, profile: Profile) -> str:
    from ..submitters.web_form import search_url
    return search_url(broker, profile) or str(broker.search_page_url or broker.url)


def _read(profile: Profile, broker: Broker, url: str, fetch: Fetcher,
          now: datetime) -> list[Listing]:
    """Fetch one search page and score what it shows. Raises FetchFailed."""
    from .browser import detect_challenge
    page = fetch(broker, url)
    if detect_challenge(page.html, status=page.status):
        raise FetchFailed("challenge")
    if page.status >= 400:
        raise FetchFailed("http_error")
    spec = broker.search
    if spec is None or not spec.result_selector:
        raise FetchFailed("no_parser")
    if spec.no_results_text and spec.no_results_text.lower() in page.html.lower():
        return []
    try:
        cands = parse_candidates(broker, page.url, page.html)
    except htmlsel.UnsupportedSelector as e:
        raise FetchFailed("no_parser") from e
    if not cands and spec.no_results_text:
        raise FetchFailed("page_unrecognized")
    return matcher.score_all(profile, broker.id, cands, now.date())


def _check_one(store: Store, profile: Profile, broker: Broker, url: str, fetch: Fetcher,
               now: datetime, old_url: str | None = None,
               before_old: Callable[[], None] | None = None) -> ExposureEntry:
    """Read the search page (and, if `old_url`, one old-address search page too), then
    save the listings with ONE merge so the second page never marks the first page's
    listings gone. A failed old-address page is ignored: the main answer stands."""
    from .runner import merge_listings, review_todo
    entry = ExposureEntry(broker_id=broker.id, broker_name=broker.name, status="check_by_hand",
                          check_url=url, checked_at=now)
    found = _read(profile, broker, url, fetch, now)
    if old_url:
        if before_old is not None:
            before_old()
        try:
            more = _read(profile, broker, old_url, fetch, now)
            entry.old_address_checked = True
        except FetchFailed as e:
            log.info("exposure: %s old-address search skipped (%s)", broker.id, e.reason)
            more = []
        except Exception as e:  # noqa: BLE001 - the main answer still counts
            log.warning("exposure: %s old-address search failed (%s)", broker.id,
                        type(e).__name__)
            more = []
        seen = {li.url for li in found}
        for li in more:              # the same listing on both pages counts once
            if li.url not in seen:
                seen.add(li.url)
                found.append(li)
    saved = merge_listings(store, profile, broker, found, now)
    possible = [li for li in saved if li.match_level == MatchLevel.POSSIBLE]
    if possible and not any(li.match_level == MatchLevel.CONFIRMED for li in saved):
        review_todo(store, profile, broker, possible[0], len(possible))
    entry.status = "found" if saved else "not_found"
    return _fill(entry, saved)


_ADDRESS_FIELDS = {"city", "state", "state_name"}


def _uses_address(broker: Broker) -> bool:
    import string
    pat = broker.search_url_pattern or ""
    return any(f in _ADDRESS_FIELDS for _, f, _, _ in string.Formatter().parse(pat) if f)


def old_address_url(broker: Broker, profile: Profile) -> str | None:
    """The one extra search URL for a previous address (Address.current False), or None.
    Only for brokers whose search URL uses city/state; picks the most recent previous
    address (highest to_year, then from_year, then list order) that gives a different URL
    from the current-address search."""
    from ..submitters.web_form import current_address, search_url
    if not _uses_address(broker):
        return None
    cur = current_address(profile)
    main = search_url(broker, profile)
    prev = [a for a in profile.addresses if a is not cur and not a.current]
    prev.sort(key=lambda a: (-(a.to_year or 0), -(a.from_year or 0)))   # stable
    for a in prev:
        u = search_url(broker, profile, a)
        if u and u != main:
            return u
    return None


def scan_exposure(store: Store, profile_id: str, *, registry: Registry | None = None,
                  offline: bool = False, refresh: bool = False,
                  cfg: cfgmod.Config | None = None, fetch: Fetcher | None = None,
                  browser_fetch: Fetcher | None = None, use_browser: bool = True,
                  broker_ids: list[str] | None = None, now: datetime | None = None,
                  sleep: Callable[[float], None] = time.sleep,
                  old_addresses: bool | None = None) -> ExposureResult:
    """Run the exposure scan for one person and store it. Never raises for a broker's
    failure (that broker becomes "check by hand"). Raises ExposureRefused without consent.

    `fetch` / `browser_fetch` are injectable for tests. Fresh results from the last
    `CACHE_HOURS` are reused unless `refresh`. `old_addresses` (default: the config flag
    `exposure_old_addresses`, off) adds at most one previous-address search per broker.
    """
    from ..consent import consent_ok
    from ..netpolicy import NetPolicy
    from .outbox import dev_fixture_base
    cfg = cfg or cfgmod.load()
    if old_addresses is None:
        old_addresses = bool(getattr(cfg, "exposure_old_addresses", False))
    now = now or utcnow()
    profile = store.get_profile(profile_id)
    if profile is None:
        raise ExposureRefused("no such person")
    ok, why = consent_ok(profile, store)
    if not ok:
        raise ExposureRefused(why)
    if registry is None:
        from ..registry import load_registry
        registry = load_registry()
    fixture = dev_fixture_base()
    policy = NetPolicy(registry)
    own_browser: BrowserFetcher | None = None
    if not offline:
        fetch = fetch or http_fetcher(policy, fixture)
        if browser_fetch is None and use_browser:
            browser_fetch = own_browser = BrowserFetcher(policy, cfg, fixture)
    prev = {e.broker_id: e for e in (latest_exposure(store, profile, registry) or
                                     _EMPTY).entries} if not refresh else {}
    fast = bool(fixture) or cfg.max_delay_s <= 0
    entries: list[ExposureEntry] = []
    pace = {"fetched": False}
    try:
        for broker in scan_brokers(registry):
            if broker_ids and broker.id not in broker_ids:
                continue
            entries.append(_scan_broker(store, profile, broker, now, offline,
                                        prev.get(broker.id), fetch, browser_fetch, cfg, fast,
                                        sleep, pace, old_addresses))
    finally:
        if own_browser is not None:
            own_browser.close()
    score, lines = score_entries(entries)
    res = ExposureResult(profile_id=profile.id, created_at=now, offline=offline,
                         practice_mode=not cfg.real_submissions_enabled, score=score,
                         explanation=lines, entries=entries, drop_first=drop_first(profile))
    _save(store, res)
    return res


def _scan_broker(store: Store, profile: Profile, broker: Broker, now: datetime, offline: bool,
                 prev: ExposureEntry | None, fetch: Fetcher | None,
                 browser_fetch: Fetcher | None, cfg: cfgmod.Config, fast: bool,
                 sleep: Callable[[float], None], pace: dict[str, bool],
                 old_addresses: bool = False) -> ExposureEntry:
    from ..submitters.web_form import search_url
    url = search_url(broker, profile)

    def hand(reason: str) -> ExposureEntry:
        e = ExposureEntry(broker_id=broker.id, broker_name=broker.name,
                          status="check_by_hand", reason=reason,
                          check_url=url or _hand_check_url(broker, profile), checked_at=now)
        # what earlier runs already know about this site still counts
        _fill(e, store.list_listings(profile.id, broker.id))
        if e.listings:
            e.status, e.from_store = "found", True
        return e

    if url is None:
        return hand("missing_details")
    if offline:
        return hand("offline")
    if prev is not None and prev.status in ("found", "not_found") and not prev.from_store \
            and now - prev.checked_at < timedelta(hours=CACHE_HOURS):
        # one request per broker per day: reuse the recent answer (listings re-read)
        e = prev.model_copy(update={"listings": [], "match_level": None, "signals": [],
                                    "check_url": url})
        return _fill(e, store.list_listings(profile.id, broker.id))
    access = broker.search_access
    if access == "bot_blocked":
        return hand("bot_blocked")
    if access == "unknown":
        return hand("unknown_access")
    fetcher = fetch if access == "open" else browser_fetch
    if fetcher is None:
        return hand("needs_browser")

    def gap() -> None:                    # polite gap between requests
        if not fast:
            sleep(random.uniform(max(0.0, cfg.min_delay_s),
                                 max(cfg.min_delay_s, cfg.max_delay_s)))

    if pace["fetched"]:
        gap()
    pace["fetched"] = True
    old_url = old_address_url(broker, profile) if old_addresses else None
    try:
        entry = _check_one(store, profile, broker, url, fetcher, now, old_url, gap)
    except FetchFailed as e:
        entry = hand(e.reason)
    except Exception as e:  # noqa: BLE001 - one broker never stops the scan
        log.warning("exposure: %s failed (%s)", broker.id, type(e).__name__)
        entry = hand("network")
    store.log(Event(profile_id=profile.id, broker_id=broker.id, actor=Actor.ENGINE,
                    action=CHECK_ACTION, detail={
                        "status": entry.status, "reason": entry.reason,
                        "level": entry.match_level.value if entry.match_level else None,
                        "listings": len(entry.listings),
                        "old_address": entry.old_address_checked}))
    return entry


# --------------------------------------------------------------------------- storage


_EMPTY = ExposureResult(profile_id="0" * 32, score=0)


def _save(store: Store, res: ExposureResult) -> None:
    """One PII-free audit Event per scan. Listing URLs stay in the (encrypted) listings
    table and are referenced by id; check URLs are re-derived from the profile on read."""
    ids_by_url: dict[str, str] = {}
    for e in res.entries:
        if e.listings:
            for li in store.list_listings(res.profile_id, e.broker_id):
                ids_by_url[li.url] = li.id
    detail = {
        "version": res.version, "score": res.score, "offline": res.offline,
        "practice_mode": res.practice_mode,
        "explanation": [[ln.points, ln.text] for ln in res.explanation],
        "entries": [{
            "broker_id": e.broker_id, "status": e.status, "reason": e.reason,
            "match_level": e.match_level.value if e.match_level else None,
            "signals": e.signals, "from_store": e.from_store,
            "old_address_checked": e.old_address_checked,
            "checked_at": e.checked_at.isoformat(),
            "listings": [{"listing_id": ids_by_url.get(li.url), "match_level":
                          li.match_level.value, "signals": li.signals,
                          "contact_shown": li.contact_shown,
                          "relatives_shown": li.relatives_shown} for li in e.listings],
        } for e in res.entries],
    }
    store.log(Event(ts=res.created_at, profile_id=res.profile_id, actor=Actor.ENGINE,
                    action=EVENT_ACTION, detail=detail))


def _scan_events(store: Store, profile_id: str, limit: int = 5000) -> list[Event]:
    return [ev for ev in store.events(profile_id, limit=limit) if ev.action == EVENT_ACTION]


def _from_event(store: Store, profile: Profile, ev: Event,
                registry: Registry | None) -> ExposureResult | None:
    d = ev.detail
    if d.get("version") != 1:
        return None
    names: dict[str, Broker] = {b.id: b for b in registry.brokers} if registry else {}
    by_id: dict[str, Listing] = {li.id: li for li in store.list_listings(profile.id)}
    entries: list[ExposureEntry] = []
    for raw in d.get("entries", []):
        b = names.get(raw["broker_id"])
        lis = []
        for x in raw.get("listings", []):
            li = by_id.get(x.get("listing_id") or "")
            if li is None:
                continue           # deleted since; nothing to show
            lis.append(ExposureListing(url=li.url, match_level=MatchLevel(x["match_level"]),
                                       signals=x.get("signals", []),
                                       contact_shown=bool(x.get("contact_shown")),
                                       relatives_shown=int(x.get("relatives_shown", 0))))
        entries.append(ExposureEntry(
            broker_id=raw["broker_id"], broker_name=b.name if b else raw["broker_id"],
            status=raw["status"], reason=raw.get("reason"),
            match_level=MatchLevel(raw["match_level"]) if raw.get("match_level") else None,
            signals=raw.get("signals", []), listings=lis,
            check_url=_hand_check_url(b, profile) if b else None,
            from_store=bool(raw.get("from_store")),
            old_address_checked=bool(raw.get("old_address_checked")),
            checked_at=datetime.fromisoformat(raw["checked_at"])))
    return ExposureResult(
        profile_id=profile.id, created_at=ev.ts, offline=bool(d.get("offline")),
        practice_mode=bool(d.get("practice_mode", True)), score=int(d.get("score", 0)),
        drop_first=drop_first(profile),     # from the profile now, not stored
        explanation=[ScoreLine(points=int(p), text=str(t)) for p, t in d.get("explanation",
                                                                            [])],
        entries=entries)


def latest_exposure(store: Store, profile: Profile | str,
                    registry: Registry | None = None) -> ExposureResult | None:
    """Dashboard hook: the newest stored exposure result for `profile` (a Profile or its
    id), or None if there has never been a scan. Reads only; no network."""
    if isinstance(profile, str):
        p = store.get_profile(profile)
        if p is None:
            return None
        profile = p
    if registry is None:
        try:
            from ..registry import load_registry
            registry = load_registry()
        except Exception:  # noqa: BLE001 - still show the score without broker names
            registry = None
    for ev in _scan_events(store, profile.id):
        res = _from_event(store, profile, ev, registry)
        if res is not None:
            return res
    return None


def exposure_history(store: Store, profile_id: str,
                     limit: int = 52) -> list[tuple[datetime, int]]:
    """(when, score) for past scans, oldest first, for a trend line."""
    out = [(ev.ts, int(ev.detail.get("score", 0))) for ev in _scan_events(store, profile_id)]
    return list(reversed(out[:limit]))
