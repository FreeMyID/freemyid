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
import string
import time
import zlib
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin, urlsplit

from .. import __version__
from .. import config as cfgmod
from ..checklist_state import drop_first
from ..exposure_models import (
    ExposureEntry,
    ExposureListing,
    ExposureResult,
    ExposureSummary,
    ScoreDriver,
    ScoreLine,
)
from ..models import Actor, Broker, BrokerCategory, Event, Listing, MatchLevel, ProfileField, utcnow
from . import exposure_score as xs
from . import htmlsel, matcher
from .exposure_score import (  # noqa: F401  re-exported: the formula lives in exposure_score
    MAX_EXTRA_PER_SITE,
    MAX_RELATIVE_POINTS,
    W_CONFIRMED_SITE,
    W_CONTACT,
    W_EXTRA_LISTING,
    W_POSSIBLE_SITE,
    W_RELATIVE,
    score_entries,
)

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
# SEC-92: total wall-clock budget for one fetch (all hops and the whole body); httpx's
# timeout is per read, so a slow-drip server could otherwise hold a broker forever
DEADLINE_S = 30.0
CACHE_HOURS = 24
# SEC-93d: only encodings `_decoded` can stream with a running size limit
_HEADERS = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.8", "Accept-Encoding": "gzip, deflate"}
_MAX_RESULTS = 25

# score weights (docs/EXPOSURE.md; change both together)


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


MAX_ENCODINGS = 2


def _decoders(content_encoding: str) -> list[Any]:
    """zlib decompressors for a Content-Encoding header, in the order to apply them.
    Unknown codings (br, zstd, compress...) are refused: we never asked for them. More than
    MAX_ENCODINGS stacked values are refused too (SEC-101: each layer costs CPU and memory,
    and no honest server stacks more)."""
    out: list[Any] = []
    codings = [c.strip().lower() for c in content_encoding.split(",") if c.strip()]
    if len(codings) > MAX_ENCODINGS:
        raise FetchFailed("http_error")
    for c in reversed(codings):
        if c in ("identity",):
            continue
        if c in ("gzip", "x-gzip"):
            out.append(zlib.decompressobj(16 + zlib.MAX_WBITS))
        elif c == "deflate":
            out.append(_Deflate())
        else:
            raise FetchFailed("http_error")
    return out


class _Deflate:
    """HTTP "deflate" is meant to be zlib-wrapped, but some servers send raw deflate: try
    the zlib wrapper on the first bytes and fall back to raw deflate if the header is wrong."""

    def __init__(self) -> None:
        self._d: Any = zlib.decompressobj(zlib.MAX_WBITS)
        self._first = True
        self.unconsumed_tail = b""

    def decompress(self, data: bytes, max_length: int = 0) -> bytes:
        if self._first:
            self._first = False
            try:
                got = self._d.decompress(data, max_length)
            except zlib.error:
                self._d = zlib.decompressobj(-zlib.MAX_WBITS)
                got = self._d.decompress(data, max_length)
        else:
            got = self._d.decompress(data, max_length)
        self.unconsumed_tail = self._d.unconsumed_tail
        return got


def _decoded(raw: Iterable[bytes], content_encoding: str, limit: int) -> Iterator[bytes]:
    """SEC-93d: decompress `raw` piece by piece and stop as soon as more than `limit` decoded
    bytes come out, so a gzip/deflate bomb never expands in memory. Every decompress call is
    capped with `max_length`; leftover input is fed back in bounded steps."""
    decs = _decoders(content_encoding)
    total = 0

    def through(i: int, data: bytes) -> Iterator[bytes]:
        if i == len(decs):
            yield data
            return
        d = decs[i]
        while data:
            try:
                piece = d.decompress(data, limit + 1)
            except zlib.error as e:
                raise FetchFailed("http_error") from e
            data = d.unconsumed_tail
            if piece:
                yield from through(i + 1, piece)
            elif data:      # no output but input left: a stuck stream, never spin
                raise FetchFailed("http_error")

    for chunk in raw:
        for out in through(0, chunk):
            total += len(out)
            if total > limit:
                raise FetchFailed("too_large")
            yield out


def http_fetcher(policy: NetPolicy, fixture_base: str | None = None,
                 client: Any = None, deadline_s: float = DEADLINE_S,
                 clock: Callable[[], float] = time.monotonic) -> Fetcher:
    """One plain GET per broker. `fixture_base` (dev only) answers https://host/path from the
    local fixture server, the same mapping BrowserManager uses."""
    import httpx

    from .browser import fixture_url

    def fetch(broker: Broker, url: str) -> Fetched:
        cl = client or httpx.Client(timeout=TIMEOUT_S, follow_redirects=False)
        end = clock() + deadline_s

        def left() -> float:
            rest = end - clock()
            if rest <= 0:
                raise FetchFailed("too_slow")
            return rest

        try:
            cur = url
            for _hop in range(MAX_REDIRECTS + 1):
                if not _on_broker(broker, cur, policy):
                    raise FetchFailed("blocked_by_policy")
                real = fixture_url(fixture_base, cur) if fixture_base else cur
                # SEC-91: "no cookies" holds per hop too; a 30x Set-Cookie is never replayed
                cl.cookies.clear()
                try:
                    with cl.stream("GET", real, headers=_HEADERS,
                                   timeout=min(TIMEOUT_S, left())) as r:
                        if r.status_code in (301, 302, 303, 307, 308):
                            loc = r.headers.get("location")
                            if not loc:
                                raise FetchFailed("http_error")
                            cur = urljoin(cur, loc)
                            continue
                        # SEC-93d: raw bytes, decoded here with a running limit (httpx would
                        # inflate a whole chunk first); a bytearray, never `body += chunk`
                        body = bytearray()
                        if r.is_stream_consumed:
                            # an in-memory test transport already read (and decoded) it
                            body.extend(r.content)
                            if len(body) > MAX_BYTES:
                                raise FetchFailed("too_large")
                        else:
                            ce = r.headers.get("content-encoding", "")
                            for piece in _decoded(r.iter_raw(), ce, MAX_BYTES):
                                body.extend(piece)
                                left()
                        enc = r.encoding or "utf-8"
                        return Fetched(cur, r.status_code,
                                       bytes(body).decode(enc, errors="replace"))
                except httpx.TimeoutException as e:
                    raise FetchFailed("too_slow") from e
                except httpx.HTTPError as e:
                    raise FetchFailed("network") from e
            raise FetchFailed("http_error")       # too many redirects
        finally:
            cl.cookies.clear()
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


def scan_brokers(registry: Registry, profile: Profile | None = None) -> list[Broker]:
    """Enabled brokers with a search URL pattern, highest priority first. For a phone/email-
    only person (BL-IN-08): the brokers with that scope's reverse-lookup pattern."""
    from .tiers import lookup_pattern

    def has(b: Broker) -> bool:
        if profile is not None and profile.value_only:
            return bool(lookup_pattern(b, profile))
        return bool(b.search_url_pattern)
    return sorted((b for b in registry.brokers if b.enabled and has(b)),
                  key=lambda b: (-b.priority, b.id))


def _lookup(profile: Profile) -> str | None:
    """The lookup kind ("phone" or "email") for a value-only person, else None."""
    return str(profile.removal_scope) if profile.value_only else None


def _main_urls(broker: Broker, profile: Profile) -> list[str]:
    """The search page(s) to read: the name search, or a value-only person's lookups."""
    from ..submitters.web_form import search_url, value_search_urls
    if profile.value_only:
        return value_search_urls(broker, profile)
    u = search_url(broker, profile)
    return [u] if u else []


def _hand_check_url(broker: Broker, profile: Profile) -> str:
    urls = _main_urls(broker, profile)
    return urls[0] if urls else str(broker.search_page_url or broker.url)


def _read(profile: Profile, broker: Broker, url: str, fetch: Fetcher,
          now: datetime) -> list[Listing]:
    """Fetch one search page and score what it shows (a value-only person's lookup page is
    scored by value, BL-IN-08). Raises FetchFailed."""
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
    kind = _lookup(profile)
    if kind:
        return matcher.score_lookup(profile, broker.id, cands, kind, now.date())
    return matcher.score_all(profile, broker.id, cands, now.date())


def _read_extra(profile: Profile, broker: Broker, url: str, fetch: Fetcher, now: datetime,
                what: str) -> list[Listing] | None:
    """One extra search page (old address / previous name). None if it failed: the main
    answer stands."""
    try:
        return _read(profile, broker, url, fetch, now)
    except FetchFailed as e:
        log.info("exposure: %s %s search skipped (%s)", broker.id, what, e.reason)
    except Exception as e:  # noqa: BLE001 - the main answer still counts
        log.warning("exposure: %s %s search failed (%s)", broker.id, what, type(e).__name__)
    return None


def _check_one(store: Store, profile: Profile, broker: Broker, url: str, fetch: Fetcher,
               now: datetime, old_url: str | None = None,
               before_old: Callable[[], None] | None = None,
               name_url: str | None = None,
               value_urls: list[str] | None = None) -> ExposureEntry:
    """Read the search page (plus, if given, one old-address page `old_url` and one
    previous-name page `name_url`), then save the listings with ONE merge so an extra page
    never marks the main page's listings gone. A failed extra page is ignored: the main
    answer stands. `before_old` runs before each extra page (the polite gap)."""
    from .runner import keep_unchecked, merge_listings, review_todo
    entry = ExposureEntry(broker_id=broker.id, broker_name=broker.name, status="check_by_hand",
                          check_url=url, checked_at=now)
    found = _read(profile, broker, url, fetch, now)
    seen = {li.url for li in found}
    unread = False
    extras = [("old-address", old_url), ("previous-name", name_url),
              *(("other-value", u) for u in value_urls or [])]
    for what, extra in extras:
        if not extra:
            continue
        if before_old is not None:
            before_old()
        more = _read_extra(profile, broker, extra, fetch, now, what)
        if more is None:
            unread = True
            continue
        if what == "old-address":
            entry.old_address_checked = True
        elif what == "previous-name":
            entry.previous_name_checked = True
        for li in more:              # the same listing on two pages counts once
            if li.url not in seen:
                seen.add(li.url)
                found.append(li)
    if unread:          # a listing seen only on the unread page is unknown, not gone
        found = keep_unchecked(store, profile, broker, found)
    saved = merge_listings(store, profile, broker, found, now)
    possible = [li for li in saved if li.match_level == MatchLevel.POSSIBLE]
    if possible and not any(li.match_level == MatchLevel.CONFIRMED for li in saved):
        review_todo(store, profile, broker, possible[0], len(possible))
    entry.status = "found" if saved else "not_found"
    return _fill(entry, saved)


_ADDRESS_FIELDS = {"city", "state", "state_name"}


def _uses_address(broker: Broker) -> bool:
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


_NAME_FIELDS = {"first", "middle", "last"}


def previous_name_url(broker: Broker, profile: Profile) -> str | None:
    """The one extra search URL for a previous name (e.g. a maiden name), at the current
    address, or None. Only for brokers whose search URL uses the name (all of them, in
    practice); picks the first previous name, in the order the person listed them, that
    gives a different URL from the main search."""
    from ..submitters.web_form import search_url
    pat = broker.search_url_pattern or ""
    if not any(f in _NAME_FIELDS for _, f, _, _ in string.Formatter().parse(pat) if f):
        return None
    main = search_url(broker, profile)
    for n in profile.previous_names:
        u = search_url(broker, profile, name=n)
        if u and u != main:
            return u
    return None


def scan_exposure(store: Store, profile_id: str, *, registry: Registry | None = None,
                  offline: bool = False, refresh: bool = False,
                  cfg: cfgmod.Config | None = None, fetch: Fetcher | None = None,
                  browser_fetch: Fetcher | None = None, use_browser: bool = True,
                  broker_ids: list[str] | None = None, now: datetime | None = None,
                  sleep: Callable[[float], None] = time.sleep,
                  old_addresses: bool | None = None,
                  previous_names: bool | None = None) -> ExposureResult:
    """Run the exposure scan for one person and store it. Never raises for a broker's
    failure (that broker becomes "check by hand"). Raises ExposureRefused without consent.

    `fetch` / `browser_fetch` are injectable for tests. Fresh results from the last
    `CACHE_HOURS` are reused unless `refresh`. `old_addresses` (default: the config flag
    `exposure_old_addresses`, off) adds at most one previous-address search per broker;
    `previous_names` (default: config `exposure_previous_names`, off) adds at most one
    previous-name (maiden name) search per broker.
    """
    from ..consent import consent_ok
    from ..netpolicy import NetPolicy
    from .outbox import dev_fixture_base
    cfg = cfg or cfgmod.load()
    if old_addresses is None:
        old_addresses = bool(getattr(cfg, "exposure_old_addresses", False))
    if previous_names is None:
        previous_names = bool(getattr(cfg, "exposure_previous_names", False))
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
        for broker in scan_brokers(registry, profile):
            if broker_ids and broker.id not in broker_ids:
                continue
            entry = _scan_broker(store, profile, broker, now, offline, prev.get(broker.id),
                                 fetch, browser_fetch, cfg, fast, sleep, pace, old_addresses,
                                 previous_names)
            entry.category = broker.category
            entries.append(entry)
    finally:
        if own_browser is not None:
            own_browser.close()
    score, lines = score_entries(entries)
    res = ExposureResult(profile_id=profile.id, created_at=now, offline=offline,
                         practice_mode=not cfg.real_submissions_enabled, score=score,
                         explanation=lines, entries=entries, drop_first=drop_first(profile),
                         drivers=xs.drivers(entries))
    _save(store, res)
    return res


def _scan_broker(store: Store, profile: Profile, broker: Broker, now: datetime, offline: bool,
                 prev: ExposureEntry | None, fetch: Fetcher | None,
                 browser_fetch: Fetcher | None, cfg: cfgmod.Config, fast: bool,
                 sleep: Callable[[float], None], pace: dict[str, bool],
                 old_addresses: bool = False,
                 previous_names: bool = False) -> ExposureEntry:
    urls = _main_urls(broker, profile)
    url = urls[0] if urls else None

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
    name_url = previous_name_url(broker, profile) if previous_names else None
    try:
        entry = _check_one(store, profile, broker, url, fetcher, now, old_url, gap, name_url,
                           value_urls=urls[1:])
    except FetchFailed as e:
        entry = hand(e.reason)
    except RecursionError:
        # SEC-92: a hostile page, not the network
        log.warning("exposure: %s page too complex", broker.id)
        entry = hand("page_unrecognized")
    except Exception as e:  # noqa: BLE001 - one broker never stops the scan
        log.warning("exposure: %s failed (%s)", broker.id, type(e).__name__)
        entry = hand("network")
    store.log(Event(profile_id=profile.id, broker_id=broker.id, actor=Actor.ENGINE,
                    action=CHECK_ACTION, detail={
                        "status": entry.status, "reason": entry.reason,
                        "level": entry.match_level.value if entry.match_level else None,
                        "listings": len(entry.listings),
                        "old_address": entry.old_address_checked,
                        "previous_name": entry.previous_name_checked}))
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
        "version": res.version, "score": res.score, "score_version": res.score_version,
        "offline": res.offline, "practice_mode": res.practice_mode,
        "explanation": [[ln.points, ln.text] for ln in res.explanation],
        "drivers": [[d.points, d.text, d.broker_id] for d in res.drivers],
        "entries": [{
            "broker_id": e.broker_id, "status": e.status, "reason": e.reason,
            "category": e.category.value if e.category else None,
            "match_level": e.match_level.value if e.match_level else None,
            "signals": e.signals, "from_store": e.from_store,
            "old_address_checked": e.old_address_checked,
            "previous_name_checked": e.previous_name_checked,
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
            category=BrokerCategory(raw["category"]) if raw.get("category") else None,
            match_level=MatchLevel(raw["match_level"]) if raw.get("match_level") else None,
            signals=raw.get("signals", []), listings=lis,
            check_url=_hand_check_url(b, profile) if b else None,
            from_store=bool(raw.get("from_store")),
            old_address_checked=bool(raw.get("old_address_checked")),
            previous_name_checked=bool(raw.get("previous_name_checked")),
            checked_at=datetime.fromisoformat(raw["checked_at"])))
    version = int(d.get("score_version", 1))
    if "drivers" in d:
        drv = [ScoreDriver(points=int(p), text=str(t), broker_id=b)
               for p, t, b in d["drivers"]]
    else:   # older scan: work the drivers out the way its score was worked out
        drv = xs.drivers(entries, weighted=version >= 2)
    return ExposureResult(
        profile_id=profile.id, created_at=ev.ts, offline=bool(d.get("offline")),
        score_version=version, drivers=drv,
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


# ------------------------------------------------------------------ trend (BL-IN-02)


@dataclass(frozen=True)
class TrendPoint:
    """One day's exposure: the last fresh scan of that day. Counts only, no PII."""
    day: date
    score: int
    sites_total: int
    sites_checked: int
    found: int
    score_version: int = 1            # how the score was worked out (exposure_score)


@dataclass(frozen=True)
class Trend:
    points: list[TrendPoint]          # oldest first
    change: int | None                # latest score minus the previous day's; None if < 2
    since: date | None                # the day `change` is measured from
    note: str                         # one plain-English line; never says "safe"


def _point(ev: Event) -> TrendPoint:
    entries = ev.detail.get("entries") or []
    return TrendPoint(
        day=ev.ts.date(), score=int(ev.detail.get("score", 0)), sites_total=len(entries),
        sites_checked=sum(1 for e in entries if e.get("status") in ("found", "not_found")
                          and not e.get("from_store")),
        found=sum(1 for e in entries if e.get("status") == "found" and
                  e.get("match_level") == MatchLevel.CONFIRMED.value),
        score_version=int(ev.detail.get("score_version", 1)))


def trend_note(points: list[TrendPoint]) -> str:
    if not points:
        return "No scans yet."
    if len(points) == 1:
        return "This is the first scan. Later scans will show whether your score goes down."
    prev, last = points[-2], points[-1]
    d = last.score - prev.score
    when = prev.day.isoformat()
    if d < 0:
        out = f"Your score went down {-d} {'point' if d == -1 else 'points'} since {when}."
    elif d > 0:
        out = f"Your score went up {d} {'point' if d == 1 else 'points'} since {when}."
    else:
        out = f"Your score is the same as on {when}."
    if last.sites_checked < prev.sites_checked:
        out += " Fewer sites could be checked this time, so the change may not be real."
    if last.score_version != prev.score_version:
        out += (" The way the score is worked out changed between these scans, so part of "
                "the change comes from that.")
    return out


def exposure_trend(store: Store, profile_id: str, limit: int = 52) -> Trend:
    """BL-IN-02: the score over time, one point per day (the day's last scan). Offline scans
    are skipped: they only re-read stored results, so they say nothing new."""
    by_day: dict[date, TrendPoint] = {}
    for ev in reversed(_scan_events(store, profile_id)):         # oldest first
        if ev.detail.get("offline"):
            continue
        p = _point(ev)
        by_day[p.day] = p
    points = [by_day[d] for d in sorted(by_day)][-limit:]
    change = points[-1].score - points[-2].score if len(points) >= 2 else None
    since = points[-2].day if len(points) >= 2 else None
    return Trend(points=points, change=change, since=since, note=trend_note(points))


# ------------------------------------------------------------- summary (ROADMAP 3.2)


def summarize(res: ExposureResult) -> ExposureSummary:
    """The score with its coverage, band, headline and top 3 drivers. Pure."""
    cov = res.coverage
    return ExposureSummary(
        profile_id=res.profile_id, created_at=res.created_at, practice_mode=res.practice_mode,
        score=res.score, score_version=res.score_version, band=xs.band(res.score, cov),
        headline=xs.headline(res.score, cov), coverage=cov, coverage_note=res.coverage_note,
        drivers=list(res.drivers))


def exposure_summary(store: Store, profile: Profile | str,
                     registry: Registry | None = None) -> ExposureSummary | None:
    """Wizard / dashboard hook: the newest stored scan as an ExposureSummary, or None if
    this person has never been scanned. Reads only; no network. Show `headline` and
    `coverage_note` next to `score` every time; never show the number alone."""
    res = latest_exposure(store, profile, registry)
    return summarize(res) if res is not None else None
