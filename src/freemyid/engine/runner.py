"""The removal loop (interfaces.py entry point `run`). PLAN_V1 D1-D4.

For each consenting profile (the consent gate is re-checked here):
  0. CA resident -> California DROP GOVERNMENT_PORTAL to-do first (D3).
  For each enabled broker, highest priority first, one at a time:
  1. load BrokerStatus; with only_due skip brokers whose next_check_at is in the future
     (an IMAP confirmation check still runs for submitted ones: it is cheap);
  2. compute the tier (tiers.tier_for) and store it on the status;
  3. scan if the broker is scannable (verified search spec), else treat it as "blind":
     never-contacted brokers count as FOUND so a request can go out;
  4. submit if state.should_submit and not scan_only. covered_by brokers go through the
     parent once; dry runs never send or submit (email -> DRAFT, automatic -> logged only);
  5. IMAP: confirmation links on confirmation_domains only, clicked in the allowlisted
     browser (never in dry runs);
  6. escalation ladder (state.next_escalation): resubmit, follow-up letter, legal demand
     (always queued for approval), COMPLAINT to-do with AG/CPPA links;
  7. next_check_at.
One broker's failure never stops the run. Events hold ids/enums/counts only.
At the end: ONE PII-free notification if anything needs the person (D4).
"""
from __future__ import annotations

import asyncio
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from .. import config as cfgmod
from ..consent import consent_ok
from ..interfaces import RunContext
from ..models import (
    Actor,
    Broker,
    Event,
    EvidenceKind,
    Listing,
    ListingState,
    MatchLevel,
    Profile,
    Registry,
    Request,
    RequestKind,
    RequestStatus,
    StateLaw,
    SubmitOutcome,
    Tier,
    Todo,
    TodoKind,
    utcnow,
)
from ..models import ListingState as S
from ..state import (
    Escalation,
    after_scan,
    can_transition,
    mark_submitted,
    next_check_at,
    next_escalation,
    should_submit,
    transition,
)
from ..submitters import assisted
from ..submitters import base as sbase
from . import handoff as hmod
from . import matcher, plugins, tiers
from .mail import DATE_SLACK, ReplyScan
from .outbox import OutboxError, dev_fixture_base

if TYPE_CHECKING:
    from ..storage import Store
    from .browser import BrowserManager

log = logging.getLogger(__name__)

#: BL-IN-10: the statutory response window (days from the first request) and the one
#: extension a broker may claim, used when no verified state-law figure is available.
LEGAL_WINDOW_DAYS = 45
LEGAL_EXTENSION_DAYS = 45
EXTENSION_EVENT = "broker_extension"
_EPOCH = datetime.min.replace(tzinfo=UTC)
_SUBMITTED_STATES = (S.SUBMITTED, S.AWAITING_VERIFICATION, S.CONFIRMED)
ID_REQUEST_REASON = "id_requested"
CPPA_COMPLAINT_URL = "https://cppa.ca.gov/webapplications/complaint"
AG_DIRECTORY_URL = "https://www.usa.gov/state-attorney-general"


@dataclass
class RunReport:
    per_profile: dict[str, dict[ListingState, int]] = field(default_factory=dict)
    needs_human: int = 0
    errors: int = 0
    tiers: dict[str, dict[Tier, int]] = field(default_factory=dict)
    skipped_not_due: int = 0
    queued_emails: int = 0
    drafted_emails: int = 0
    submitted: int = 0
    open_todos: int = 0
    skipped_profiles: int = 0
    labels: dict[str, str] = field(default_factory=dict)
    dry_run: bool = False

    def summary_lines(self) -> list[str]:
        """PII-free (profile labels like 'Mom' are user-chosen display names)."""
        out = ["Dry run: nothing was sent or submitted." if self.dry_run else "Run finished."]
        for pid, counts in self.per_profile.items():
            label = self.labels.get(pid, pid[:8])
            parts = ", ".join(f"{k.value.replace('_', ' ')}: {v}"
                              for k, v in sorted(counts.items(), key=lambda kv: kv[0].value))
            tc = self.tiers.get(pid, {})
            tparts = ", ".join(f"{t.value}: {n}" for t, n in sorted(tc.items()))
            out.append(f"{label}: {parts or 'nothing to do'}")
            if tparts:
                out.append(f"  how: {tparts}")
        if self.skipped_profiles:
            out.append(f"{self.skipped_profiles} profile(s) skipped (consent check).")
        if self.skipped_not_due:
            out.append(f"{self.skipped_not_due} site(s) not due for a check yet.")
        if self.submitted:
            out.append(f"{self.submitted} removal request(s) sent.")
        if self.queued_emails:
            out.append(f"{self.queued_emails} email(s) waiting for your approval.")
        if self.drafted_emails:
            out.append(f"{self.drafted_emails} email(s) drafted (dry run, not sent).")
        if self.open_todos:
            out.append(f"{self.open_todos} thing(s) need you. Open the dashboard to see them.")
        if self.errors:
            out.append(f"{self.errors} site(s) had errors; they will be retried next run.")
        return out


class NullNotifier:
    def notify(self, title: str, body: str, url: str | None = None) -> None:
        return None


# --------------------------------------------------------------------------- entry point


def run(store: Store, registry: Registry, profiles: list[Profile], *, scan_only: bool,
        dry_run: bool, interactive: bool = True, broker_ids: list[str] | None = None,
        only_due: bool = False, scheduled: bool | None = None, mailer: Any = None,
        notifier: Any = None, browser: BrowserManager | None = None,
        state_laws: dict[str, StateLaw] | None = None, now: datetime | None = None,
        cfg: cfgmod.Config | None = None) -> RunReport:
    """Run the loop. `scheduled=True` == quiet, headless, non-blocking, only_due."""
    if scheduled:
        interactive, only_due = False, True
    r = Runner(store, registry, scan_only=scan_only, dry_run=dry_run, interactive=interactive,
               broker_ids=broker_ids, only_due=only_due, mailer=mailer, notifier=notifier,
               browser=browser, state_laws=state_laws, now=now, cfg=cfg)
    return asyncio.run(r.run(profiles))


def merge_listings(store: Store, profile: Profile, broker: Broker, found: list[Listing],
                   now: datetime) -> list[Listing]:
    """Save a clean search's listings. Keeps ids/first_seen and the user's REVIEW_MATCH
    answers across re-scans; listings no longer shown get `gone_since`. Returns the
    non-NO_MATCH listings. Shared by the runner scan and the exposure scan."""
    old = {li.url: li for li in store.list_listings(profile.id, broker.id)}
    out: list[Listing] = []
    seen = set()
    for li in found:
        prev = old.get(li.url)
        if prev is not None:
            upd: dict[str, Any] = {"id": prev.id, "first_seen": prev.first_seen,
                                   "gone_since": None}
            if "user_confirmed" in prev.match_reasons:
                upd.update(match_level=MatchLevel.CONFIRMED,
                           match_reasons=sorted({*li.match_reasons, "user_confirmed"}))
            elif "user_rejected" in prev.match_reasons:
                upd.update(match_level=MatchLevel.NO_MATCH, match_reasons=["user_rejected"])
            li = li.model_copy(update=upd)
        seen.add(li.url)
        store.save_listing(li)
        if li.match_level != MatchLevel.NO_MATCH:
            out.append(li)
    for url, prev in old.items():
        if url not in seen and prev.gone_since is None:
            store.save_listing(prev.model_copy(update={"gone_since": now}))
    return out


def keep_unchecked(store: Store, profile: Profile, broker: Broker,
                   found: list[Listing]) -> list[Listing]:
    """`found` plus the stored, still-shown listings it lacks. Use when an extra search page
    (old address / previous name) could not be read: a listing seen only on that page is
    unknown now, not gone, so merge_listings must not stamp it `gone_since`."""
    have = {li.url for li in found}
    # SEC-104: kept listings are re-scored with the current rules (never raised)
    return [*found, *(matcher.rescore(profile, li)
                      for li in store.list_listings(profile.id, broker.id)
                      if li.gone_since is None and li.url not in have)]


def answered_request(store: Store, profile_id: str, broker_id: str,
                     at: datetime | None) -> Request | None:
    """The request a broker message (or confirmation page) dated `at` answers: the latest
    real (not dry-run) SENT request sent at or before `at`; the latest one if `at` is None."""
    sent = [r for r in store.list_requests(profile_id, broker_id, status=RequestStatus.SENT)
            if r.sent_at is not None and not r.dry_run]
    if at is not None:
        ref = at if at.tzinfo else at.replace(tzinfo=UTC)
        sent = [r for r in sent if r.sent_at is not None and r.sent_at <= ref + DATE_SLACK]
    return max(sent, key=lambda r: r.sent_at or _EPOCH, default=None)


def save_replies(store: Store, profile_id: str, broker_id: str,
                 replies: list[tuple[datetime | None, bytes]], now: datetime) -> int:
    """Proof vault: each matched broker reply as encrypted EMAIL_RECEIVED evidence, tied to
    the request it answers. The same message is saved once (by content hash). Returns how
    many were new."""
    import hashlib
    have = {e.sha256 for e in store.list_evidence(profile_id, broker_id)
            if e.kind == EvidenceKind.EMAIL_RECEIVED}
    n = 0
    for when, raw in replies:
        if hashlib.sha256(raw).hexdigest() in have:
            continue
        req = answered_request(store, profile_id, broker_id, when or now)
        ev = sbase.evidence(profile_id, broker_id, EvidenceKind.EMAIL_RECEIVED, "eml",
                            request_id=req.id if req else None, caption="reply from the site")
        saved = store.save_evidence(ev, raw)
        have.add(saved.sha256)
        n += 1
    return n


def rescore_stored(store: Store, profile: Profile, broker: Broker, now: datetime) -> int:
    """SEC-104: re-score this broker's stored listings with the current matcher, so one saved
    under older, looser rules is not escalated or re-sent. Only lowers levels; the person's
    own answers are kept. If that leaves no CONFIRMED listing, the best downgraded one gets
    an 'Is this you?' to-do. Returns how many listings were lowered."""
    stored = [li for li in store.list_listings(profile.id, broker.id) if li.gone_since is None]
    lowered: list[Listing] = []
    live: list[Listing] = []
    for li in stored:
        new = matcher.rescore(profile, li, now.date())
        if new is not li:
            store.save_listing(new)
            lowered.append(new)
        live.append(new)
    if lowered:
        possible = [li for li in lowered if li.match_level == MatchLevel.POSSIBLE]
        if possible and not any(li.match_level == MatchLevel.CONFIRMED for li in live):
            review_todo(store, profile, broker, possible[0], len(possible))
    return len(lowered)


def search_variants(cfg: cfgmod.Config) -> dict[str, bool]:
    """Which extra search pages a broker search reads (config flags, off by default). The
    runner scan and the exposure scan use the same flags, so a listing found on an extra
    page is not marked gone by the other scan."""
    return {"old_addresses": bool(getattr(cfg, "exposure_old_addresses", False)),
            "previous_names": bool(getattr(cfg, "exposure_previous_names", False))}


class Runner:
    def __init__(self, store: Store, registry: Registry, *, scan_only: bool, dry_run: bool,
                 interactive: bool, broker_ids: list[str] | None, only_due: bool,
                 mailer: Any = None, notifier: Any = None,
                 browser: BrowserManager | None = None,
                 state_laws: dict[str, StateLaw] | None = None, now: datetime | None = None,
                 cfg: cfgmod.Config | None = None) -> None:
        self.store, self.registry = store, registry
        self.cfg = cfg or cfgmod.load()
        self.fixture_base = dev_fixture_base()
        # defence in depth: the CLI also refuses, but never submit for real unless enabled
        self.dry_run = dry_run or scan_only or (
            not self.cfg.real_submissions_enabled and not self.fixture_base)
        self.scan_only = scan_only
        self.interactive = interactive
        self.broker_ids = set(broker_ids) if broker_ids else None
        self.only_due = only_due
        self._mailer = mailer
        self.notifier = notifier
        self._browser = browser
        self._browser_failed = False
        self._own_browser = browser is None
        self.state_laws = state_laws if state_laws is not None else self._load_laws()
        self.now = now or utcnow()
        self.report = RunReport(dry_run=self.dry_run)
        # (profile_id, target_id) -> outcome this run: sent | queued | draft | human
        self._target_outcome: dict[tuple[str, str], str] = {}

    # ------------------------------------------------------------------ services
    @staticmethod
    def _load_laws() -> dict[str, StateLaw]:
        try:
            from ..registry import load_state_laws
            return load_state_laws()
        except Exception as e:  # noqa: BLE001 - missing/invalid file: generic letters
            log.info("state laws unavailable: %s", type(e).__name__)
            return {}

    def mailer_for(self, profile: Profile) -> Any:
        if self._mailer is not None:
            return self._mailer
        from .mail import FakeMailer, SmtpImapMailer
        if self.dry_run or self.fixture_base or profile.mailbox is None:
            self._mailer = FakeMailer(inbox=self._fixture_inbox())
            return self._mailer
        from ..netpolicy import NetPolicy
        return SmtpImapMailer(NetPolicy(self.registry, [profile]))

    def _fixture_inbox(self) -> dict[str, list[bytes]]:
        if not self.fixture_base:
            return {}
        try:
            from . import _dev
            return _dev.fixture_inbox()
        except Exception:  # noqa: BLE001
            return {}

    async def browser(self) -> BrowserManager | None:
        if self._browser is not None:
            return self._browser
        if self._browser_failed or not tiers.browser_automation_allowed(self.cfg):
            return None
        bm = None
        try:
            from ..netpolicy import NetPolicy
            from .browser import BrowserManager
            pol = NetPolicy(self.registry)
            bm = BrowserManager(pol, headless=True if not self.interactive else None,
                                cfg=self.cfg, fixture_base=self.fixture_base)
            await bm.start()
            self._browser = bm
            return bm
        except Exception as e:  # noqa: BLE001 - no browser: Automatic drops to Assisted
            if bm is not None:        # SEC-26: never leak the Playwright driver
                try:
                    await bm.close()
                except Exception as ce:  # noqa: BLE001
                    log.debug("browser cleanup failed: %s", type(ce).__name__)
            log.warning("browser unavailable (%s); automatic sites become assisted",
                        type(e).__name__)
            self._browser_failed = True
            return None

    def _notifier(self) -> Any:
        if self.notifier is None:
            self.notifier = hmod.get_notifier()
        return self.notifier

    def _handoff(self, profile: Profile) -> Any:
        if self.interactive:
            return hmod.make_handoff(self.store, self._notifier(), True, self._browser,
                                     profile.label)
        return hmod.QueuedHandoff(self.store, NullNotifier(), profile.label)

    def _law(self, profile: Profile) -> StateLaw | None:
        return self.state_laws.get(profile.state_of_residence)

    def _event(self, profile: Profile, broker_id: str | None, action: str,
               frm: S | None = None, to: S | None = None, **detail: Any) -> None:
        self.store.log(Event(profile_id=profile.id, broker_id=broker_id, actor=Actor.ENGINE,
                             action=action, from_state=frm, to_state=to, detail=detail))

    # ------------------------------------------------------------------ main loop
    async def run(self, profiles: list[Profile]) -> RunReport:
        try:
            for p in profiles:
                ok, _why = consent_ok(p, self.store)
                if not ok:
                    self.report.skipped_profiles += 1
                    self.store.log(Event(profile_id=p.id, actor=Actor.ENGINE,
                                         action="profile_skipped_consent"))
                    continue
                self.report.labels[p.id] = p.label
                await self.run_profile(p)
        finally:
            if self._browser is not None and self._own_browser:
                try:
                    await self._browser.close()
                except Exception as e:  # noqa: BLE001
                    log.debug("browser close failed: %s", type(e).__name__)
        self._finish(profiles)
        return self.report

    def brokers(self) -> list[Broker]:
        bs = [b for b in self.registry.brokers if b.enabled and
              (self.broker_ids is None or b.id in self.broker_ids)]
        return sorted(bs, key=lambda b: (-b.priority, b.id))

    async def run_profile(self, profile: Profile) -> None:
        counts: Counter[ListingState] = Counter()
        tcounts: Counter[Tier] = Counter()
        if not self.scan_only:
            self._drop_first(profile)
        for broker in self.brokers():
            if broker.id == assisted.DROP_BROKER_ID:
                # handled by the GOVERNMENT_PORTAL to-do (CA only); record the tier only
                dst = self.store.get_status(profile.id, broker.id)
                if dst.tier != Tier.ASSISTED:
                    self.store.save_status(dst.model_copy(update={"tier": Tier.ASSISTED}))
                continue
            try:
                st = await self.process(profile, broker)
            except Exception as e:
                self.report.errors += 1
                log.warning("broker %s failed: %s", broker.id, type(e).__name__)
                log.debug("broker failure detail", exc_info=True)
                st = self._mark_error(profile, broker, type(e).__name__)
            if st is None:
                continue
            counts[st.state] += 1
            if st.tier:
                tcounts[st.tier] += 1
            if st.state == S.NEEDS_HUMAN:
                self.report.needs_human += 1
        self.report.per_profile[profile.id] = dict(counts)
        self.report.tiers[profile.id] = dict(tcounts)

    def _mark_error(self, profile: Profile, broker: Broker, err: str) -> Any:
        try:
            st = self.store.get_status(profile.id, broker.id)
            new = transition(st, S.ERROR, self.now)
            new.next_check_at = next_check_at(broker, S.ERROR, self.now)
            self.store.save_status(new)
            self._event(profile, broker.id, "error", st.state, S.ERROR, error=err)
            return new
        except Exception:  # noqa: BLE001
            return None

    def _drop_first(self, profile: Profile) -> None:
        """D3: California DROP first for CA residents (current address)."""
        if profile.state_of_residence != "CA":
            return
        broker = None
        try:
            broker = self.registry.get(assisted.DROP_BROKER_ID)
        except KeyError:
            pass
        for t in self.store.list_todos(profile.id, open_only=False):
            if t.kind == TodoKind.GOVERNMENT_PORTAL and t.resume_token == "gov:ca_drop":
                return      # open or already done: never nag twice
        todo = assisted.drop_todo(profile, broker)
        self.store.save_todo(todo)
        self._event(profile, todo.broker_id, "todo_created", todo_kind=todo.kind.value)

    # ------------------------------------------------------------------ one broker
    async def process(self, profile: Profile, broker: Broker) -> Any:
        if profile.value_only and not tiers.value_applicable(broker, profile, self.registry):
            return self.store.get_status(profile.id, broker.id)    # BL-IN-08: not for this
        n = rescore_stored(self.store, profile, broker, self.now)
        if n:
            self._event(profile, broker.id, "rescored", downgraded=n)
        st = self.store.get_status(profile.id, broker.id)
        tier = tiers.tier_for(broker, profile, self.cfg, registry=self.registry)
        target = tiers.submit_target(broker, self.registry)
        if self.only_due and st.next_check_at and st.next_check_at > self.now:
            self.report.skipped_not_due += 1
            st = st.model_copy(update={"tier": tier})
            if st.state in (S.SUBMITTED, S.AWAITING_VERIFICATION):
                st = await self._verify(profile, broker, target, st, tier)
                self.store.save_status(st)
            return st
        st = st.model_copy(update={"tier": tier})
        ctx = self._ctx(profile, broker)

        # 3. scan (or blind)
        listings, scanned = await self._scan(ctx, st, tier)
        st = self._apply_scan(profile, broker, st, listings, scanned)

        # 4. submit (paused while the site's request for ID waits on a person)
        if should_submit(st.state) and not self.scan_only and self._id_hold(profile, target):
            st = self._set(profile, st, S.NEEDS_HUMAN, "id_request_open")
            st = st.model_copy(update={"needs_human_reason": ID_REQUEST_REASON})
        if should_submit(st.state) and not self.scan_only:
            # SEC-104: a listing only kept because an extra page was unreadable is never a
            # new send target; wait for a clean scan instead
            unchecked = ctx.scratch.get("unchecked_urls") or set()
            conf = sbase.confirmed(listings)
            fresh = [li for li in conf if li.url not in unchecked]
            if scanned and conf and not fresh:
                self._event(profile, broker.id, "submit_deferred", why="unchecked_page")
            else:
                st = await self._submit(profile, broker, target, st, tier,
                                        fresh or ([] if scanned else listings))

        # 5. verification mail
        if st.state in (S.SUBMITTED, S.AWAITING_VERIFICATION):
            st = await self._verify(profile, broker, target, st, tier)

        # 6. escalation
        if not self.scan_only:
            st = await self._escalate(profile, broker, target, st, tier, scanned)

        # 7. next check
        st = st.model_copy(update={"next_check_at": next_check_at(
            broker, st.state, self.now, weekly=profile.schedule.weekly_recheck)})
        self.store.save_status(st)
        return st

    def _ctx(self, profile: Profile, broker: Broker, **scratch: Any) -> RunContext:
        from ..netpolicy import NetPolicy
        return RunContext(profile=profile, broker=broker, store=self.store,
                          netpolicy=NetPolicy(self.registry), handoff=self._handoff(profile),
                          notifier=NullNotifier(), mailer=self.mailer_for(profile),
                          dry_run=self.dry_run, interactive=self.interactive,
                          state_law=self._law(profile), now=self.now,
                          scratch={"search_variants": search_variants(self.cfg), **scratch})

    def _set(self, profile: Profile, st: Any, dst: S, action: str, **detail: Any) -> Any:
        if st.state == dst:
            return st
        if not can_transition(st.state, dst):
            self._event(profile, st.broker_id, "transition_skipped", st.state, dst, **detail)
            return st
        new = transition(st, dst, self.now)
        self._event(profile, st.broker_id, action, st.state, dst, **detail)
        return new

    # ------------------------------------------------------------------ scan
    async def _scan(self, ctx: RunContext, st: Any, tier: Tier) -> tuple[list[Listing], bool]:
        scannable = (tiers.can_scan_value(ctx.broker, ctx.profile, self.cfg)
                     if ctx.profile.value_only else tiers.can_scan(ctx.broker, self.cfg))
        if not scannable:
            return [], False
        bm = await self.browser()
        if bm is None:
            return [], False
        from ..submitters.web_form import search_listings
        ctx.scratch["browser"] = bm
        try:
            found = await search_listings(ctx)
        except Exception as e:  # noqa: BLE001 - challenge/unexpected page: treat as blind
            self._event(ctx.profile, ctx.broker.id, "scan_failed", error=type(e).__name__)
            return [], False
        listings = self._merge_listings(ctx.profile, ctx.broker, found)
        shot = ctx.scratch.pop("search_screenshot", None)
        if shot and listings:
            ev = sbase.evidence(ctx.profile.id, ctx.broker.id, EvidenceKind.SCREENSHOT, "png",
                                listing_id=listings[0].id, caption="search results")
            self.store.save_evidence(ev, shot)
        return listings, True

    def _merge_listings(self, profile: Profile, broker: Broker,
                        found: list[Listing]) -> list[Listing]:
        return merge_listings(self.store, profile, broker, found, self.now)

    def _apply_scan(self, profile: Profile, broker: Broker, st: Any, listings: list[Listing],
                    scanned: bool) -> Any:
        if scanned:
            conf = sbase.confirmed(listings)
            possible = [li for li in listings if li.match_level == MatchLevel.POSSIBLE]
            new_state = after_scan(st, bool(conf), self.now)
            st = self._set(profile, st, new_state, "scanned", confirmed=len(conf),
                           possible=len(possible))
            st = st.model_copy(update={"last_scan_at": self.now})
            if possible and not conf:
                self._review_todo(profile, broker, possible[0], len(possible))
            return st
        # blind broker: no search. A broker we never contacted is presumed to hold data.
        if st.last_submitted_at is None and st.state in (S.UNKNOWN, S.ERROR, S.NOT_FOUND):
            return self._set(profile, st, S.FOUND, "presumed_listed", blind=True)
        if st.state == S.NEEDS_HUMAN and st.last_submitted_at is None and \
                not self._open_human_todo(profile, broker):
            return self._set(profile, st, S.FOUND, "presumed_listed", blind=True)
        return st

    def _open_human_todo(self, profile: Profile, broker: Broker) -> bool:
        target = tiers.submit_target(broker, self.registry)
        ids = {broker.id, target.id}
        return any(t.broker_id in ids and t.kind != TodoKind.REVIEW_MATCH
                   for t in self.store.list_todos(profile.id))

    def _review_todo(self, profile: Profile, broker: Broker, li: Listing, n: int) -> None:
        review_todo(self.store, profile, broker, li, n)

    # ------------------------------------------------------------------ submit
    async def _dispatch(self, profile: Profile, target: Broker, tier: Tier,
                        listings: list[Listing], **scratch: Any) -> SubmitOutcome:
        """Run the tier's submitter against `target`. AUTOMATIC falls back to ASSISTED when
        the browser is unavailable. In dry runs AUTOMATIC submits nothing."""
        ctx = self._ctx(profile, target, **scratch)
        if tier == Tier.AUTOMATIC:
            if self.dry_run:
                return SubmitOutcome(new_state=S.FOUND, message="dry_run_would_submit")
            bm = await self.browser()
            if bm is None:
                tier = Tier.ASSISTED
                ctx.scratch["reason"] = "error"
            else:
                ctx.scratch["browser"] = bm
        sub = plugins.get_submitter(target, tier)
        return await sub.submit(ctx, listings)

    async def _submit(self, profile: Profile, broker: Broker, target: Broker, st: Any,
                      tier: Tier, listings: list[Listing]) -> Any:
        key = (profile.id, target.id)
        if target.id != broker.id:
            # covered_by: one submission to the parent covers this site (PLAN_V1)
            pst = self.store.get_status(profile.id, target.id)
            done = self._target_outcome.get(key)
            if done is None and pst.state in _SUBMITTED_STATES:
                done = "sent"
            if done is None and self._open_human_todo(profile, target):
                done = "human"
            if done == "sent" and not self.dry_run:
                new = mark_submitted(st, self.now)
                self._event(profile, broker.id, "covered_by_parent", st.state, new.state,
                            parent=target.id)
                return new
            if done == "human":
                new = self._set(profile, st, S.NEEDS_HUMAN, "covered_by_parent",
                                parent=target.id)
                return new.model_copy(update={"needs_human_reason": f"via:{target.id}"})
            if done is not None:
                return st
        elif key in self._target_outcome:
            return st
        out = await self._dispatch(profile, target, tier, listings)
        return self._apply_outcome(profile, broker, st, out, key)

    def _apply_outcome(self, profile: Profile, broker: Broker, st: Any, out: SubmitOutcome,
                       key: tuple[str, str]) -> Any:
        for t in out.todos:
            hmod.persist_todo(self.store, t)
            self._event(profile, t.broker_id, "todo_created", todo_kind=t.kind.value)
        req = out.request
        if req is not None and req.status == RequestStatus.SENT:
            self._target_outcome[key] = "sent"
            self.report.submitted += 1
            new = mark_submitted(st, self.now)
            if out.new_state == S.AWAITING_VERIFICATION:
                new = transition(new, S.AWAITING_VERIFICATION, self.now)
            self._event(profile, broker.id, "submitted", st.state, new.state,
                        request_id=req.id, method=req.method.value)
            self._mirror_parent(profile, broker, key, new)
            return new
        if req is not None:
            if req.status == RequestStatus.QUEUED_FOR_APPROVAL:
                self.report.queued_emails += 1
            elif req.dry_run:
                self.report.drafted_emails += 1
            self._target_outcome[key] = "draft" if req.dry_run else "queued"
            return st
        if out.new_state == S.NEEDS_HUMAN:
            self._target_outcome[key] = "human"
            new = self._set(profile, st, S.NEEDS_HUMAN, "needs_human", why=out.message[:60])
            return new.model_copy(update={"needs_human_reason": out.message[:60]})
        if out.message:
            self._event(profile, broker.id, out.message[:60])
        return st

    def _mirror_parent(self, profile: Profile, broker: Broker, key: tuple[str, str],
                       child_new: Any) -> None:
        """A child's submission went to the parent: record it on the parent too."""
        if key[1] == broker.id:
            return
        pst = self.store.get_status(profile.id, key[1])
        if pst.state in _SUBMITTED_STATES:
            return
        if pst.state in (S.UNKNOWN, S.NOT_FOUND, S.ERROR):
            pst = transition(pst, S.FOUND, self.now)
        if can_transition(pst.state, S.SUBMITTED):
            self.store.save_status(mark_submitted(pst, self.now))

    # ------------------------------------------------------------------ verify (IMAP)
    async def _verify(self, profile: Profile, broker: Broker, target: Broker, st: Any,
                      tier: Tier) -> Any:
        if profile.mailbox is None or st.last_submitted_at is None:
            return st
        if not (target.needs_email_verification or tier == Tier.EMAIL):
            return st
        if target.id != broker.id:
            return st         # the parent's own status handles its confirmation mail
        mailer = self.mailer_for(profile)
        try:
            if hasattr(mailer, "scan_replies"):
                scan = await mailer.scan_replies(profile, target, st.last_submitted_at,
                                                 timeout_s=0)
            else:   # a Mailer that only implements the interfaces.py protocol
                scan = ReplyScan(links=await mailer.wait_for_confirmation(
                    profile, target, st.last_submitted_at, timeout_s=0))
        except Exception as e:  # noqa: BLE001
            self._event(profile, broker.id, "mail_check_failed", error=type(e).__name__)
            return st
        n = save_replies(self.store, profile.id, target.id, scan.replies, self.now)
        if n:
            self._event(profile, broker.id, "replies_saved", count=n)
        if scan.duplicates or scan.stale:
            self._event(profile, broker.id, "mail_replies_skipped",
                        duplicates=scan.duplicates, stale=scan.stale)
        if scan.extension_claimed and not self._extension_claimed(profile, broker):
            self._event(profile, broker.id, EXTENSION_EVENT)
        if scan.id_requested:
            return self._id_requested(profile, broker, st)
        links = scan.links
        if not links:
            return st
        if self.dry_run:
            self._event(profile, broker.id, "confirmation_link_found", links=len(links),
                        clicked=False)
            return st
        clicked = 0
        for u in links[:1]:       # SEC-18: only the best-ranked confirm link
            if await self._click(profile, target, u):
                clicked += 1
        if clicked:
            return self._set(profile, st, S.CONFIRMED, "confirmed", links=len(links),
                             clicked=clicked)
        return self._set(profile, st, S.AWAITING_VERIFICATION, "confirmation_pending")

    def _id_requested(self, profile: Profile, broker: Broker, st: Any) -> Any:
        """The broker's reply asks for an ID document. Free My ID never sends ID and never
        clicks anything in that mail: a person decides (ID_UPLOAD to-do)."""
        if self.dry_run:
            self._event(profile, broker.id, ID_REQUEST_REASON, todo=False)
            return st
        hmod.persist_todo(self.store, Todo(
            profile_id=profile.id, broker_id=broker.id, kind=TodoKind.ID_UPLOAD,
            title=f"{broker.name} asked for a copy of {profile.label}'s ID",
            body=("The site wrote back asking for an ID document before it will remove the "
                  "listing. Free My ID never sends ID for you. Read their email in your "
                  "removal mailbox and decide yourself. Many sites remove listings without "
                  "ID if you reply that you only want your data deleted. When you have "
                  "dealt with it, press \"I did it\"."),
            resume_token=f"{ID_REQUEST_REASON}:{broker.id}"))
        new = self._set(profile, st, S.NEEDS_HUMAN, ID_REQUEST_REASON, todo=True)
        return new.model_copy(update={"needs_human_reason": ID_REQUEST_REASON})

    def _id_hold(self, profile: Profile, target: Broker) -> bool:
        """An open ID-request to-do pauses every new letter/form to that site."""
        return any(t.kind == TodoKind.ID_UPLOAD and t.broker_id == target.id
                   and (t.resume_token or "").startswith(ID_REQUEST_REASON)
                   for t in self.store.list_todos(profile.id))

    async def _click(self, profile: Profile, broker: Broker, url: str) -> bool:
        from ..netpolicy import host_of
        from .mail import _host_in, confirmation_hosts
        hosts = confirmation_hosts(broker)
        if not url.lower().startswith("https://") or not _host_in(host_of(url), hosts):
            return False
        bm = await self.browser()
        if bm is None:
            return False
        bctx = await bm.new_context(broker.domains, extra=hosts)
        try:
            page = await bctx.new_page()
            await bm.goto(page, url)
            png = await page.screenshot(full_page=True)
            req = answered_request(self.store, profile.id, broker.id, self.now)
            ev = sbase.evidence(profile.id, broker.id, EvidenceKind.SCREENSHOT, "png",
                                request_id=req.id if req else None,
                                caption="confirmation link page")
            self.store.save_evidence(ev, png)
            return True
        except Exception as e:  # noqa: BLE001
            self._event(profile, broker.id, "confirmation_click_failed", error=type(e).__name__)
            hmod.persist_todo(self.store, Todo(
                profile_id=profile.id, broker_id=broker.id, kind=TodoKind.UNEXPECTED_PAGE,
                title=f"Confirm {profile.label}'s removal at {broker.name}",
                body="Open the link and finish the confirmation yourself.", links=[url]))
            return False
        finally:
            await bctx.close()

    # ------------------------------------------------------------------ escalation
    def _last_sent(self, profile: Profile, target: Broker) -> Request | None:
        sent = [r for r in self.store.list_requests(profile.id, target.id)
                if r.status == RequestStatus.SENT and
                r.kind in (RequestKind.OPT_OUT, RequestKind.RESUBMIT)]
        return sent[-1] if sent else None

    async def _escalate(self, profile: Profile, broker: Broker, target: Broker, st: Any,
                        tier: Tier, scanned: bool) -> Any:
        if target.id != broker.id:
            return st                 # the parent's own ladder covers this site
        if not scanned and st.state == S.CONFIRMED:
            return st                 # blind + confirmed: no sign it is still listed
        dec = next_escalation(self._ladder_view(profile, broker, st), broker, self.now)
        if dec.action == Escalation.NONE:
            return st
        waiting = self._escalation_waiting(profile, broker)
        if waiting:
            # the previous rung has not actually gone out yet: never climb past it
            self._event(profile, broker.id, "escalation_waiting", rung=dec.action.value,
                        why=waiting)
            return st
        law = self._law(profile)
        window_end = self.legal_window_end(profile, broker, st, law)
        early = window_end is not None and self.now < window_end
        if window_end is not None and early and \
                dec.action in (Escalation.LEGAL_DEMAND, Escalation.COMPLAINT):
            # BL-IN-10: no legal demand (or complaint) before the statutory window has passed
            self._event(profile, broker.id, "escalation_waiting", rung=dec.action.value,
                        why="legal_window", until=window_end.date().isoformat())
            return st
        if early and dec.action == Escalation.FOLLOW_UP:
            law = None        # a polite reminder: no statute, no legal deadline
        if self.dry_run:
            self._event(profile, broker.id, "escalation_due", rung=dec.action.value,
                        level=dec.new_level, reminder=early)
            return st
        listings = [li for li in self.store.list_listings(profile.id, broker.id)
                    if li.gone_since is None and li.match_level == MatchLevel.CONFIRMED]
        original = self._last_sent(profile, broker)
        done = "ok"
        try:
            if dec.action == Escalation.RESUBMIT:
                out = await self._dispatch(profile, broker, tier, listings,
                                           kind=RequestKind.RESUBMIT, again=True)
                for t in out.todos:
                    hmod.persist_todo(self.store, t)
                if out.request is not None and out.request.status == RequestStatus.SENT:
                    st = mark_submitted(st, self.now)
                    self.report.submitted += 1
                elif out.request is not None:
                    self.report.queued_emails += 1
            elif dec.action in (Escalation.FOLLOW_UP, Escalation.LEGAL_DEMAND):
                kind = (RequestKind.FOLLOW_UP if dec.action == Escalation.FOLLOW_UP
                        else RequestKind.LEGAL_DEMAND)
                done = self._letter(profile, broker, listings, law, kind, original)
            elif dec.action == Escalation.COMPLAINT:
                hmod.persist_todo(self.store, self._complaint_todo(profile, broker, law))
        except OutboxError as e:
            done = f"failed:{str(e)[:40]}"
        if done.startswith("failed:"):
            # retry this same rung one window from now; never skip to the next one
            self._event(profile, broker.id, "escalation_failed", rung=dec.action.value,
                        level=st.escalation_level, result=done)
            return st.model_copy(update={"last_escalated_at": self.now})
        self._event(profile, broker.id, "escalated", rung=dec.action.value,
                    level=dec.new_level, result=done, reminder=early)
        return st.model_copy(update={"escalation_level": dec.new_level,
                                     "last_escalated_at": self.now})

    def _extension_claimed(self, profile: Profile, broker: Broker) -> bool:
        return any(e.action == EXTENSION_EVENT
                   for e in self.store.events(profile.id, broker.id, limit=2000))

    def legal_window_end(self, profile: Profile, broker: Broker, st: Any,
                         law: StateLaw | None) -> datetime | None:
        """BL-IN-10: when the statutory response window for the FIRST request ends:
        45 days (or the verified `response_days`), plus the extension (verified
        `extension_days`, else 45) once the broker has said it is taking more time. Before
        this, a follow-up is a polite reminder and no legal demand goes out. None = nothing
        was ever sent."""
        sent = [r.sent_at for r in self.store.list_requests(profile.id, broker.id,
                                                            status=RequestStatus.SENT)
                if r.sent_at is not None and not r.dry_run and
                r.kind in (RequestKind.OPT_OUT, RequestKind.RESUBMIT)]
        first = min(sent, default=None) or st.last_submitted_at
        if first is None:
            return None
        from .outbox import effective_law
        eff = effective_law(profile, law, self.now.date())
        days = (eff.response_days if eff and eff.response_days else LEGAL_WINDOW_DAYS)
        if self._extension_claimed(profile, broker):
            days += (eff.extension_days if eff and eff.extension_days
                     else LEGAL_EXTENSION_DAYS)
        return first + timedelta(days=days)

    def _ladder_view(self, profile: Profile, broker: Broker, st: Any) -> Any:
        """Status as the ladder should see it: a letter approved (and sent) long after it
        was queued restarts the wait from its real send time, so the next rung never comes
        days after the previous one went out."""
        sent = [r.sent_at for r in self.store.list_requests(profile.id, broker.id,
                                                            status=RequestStatus.SENT)
                if r.sent_at is not None and not r.dry_run]
        latest = max(sent, default=None)
        if latest is None or (st.last_escalated_at and st.last_escalated_at >= latest):
            return st
        if st.last_submitted_at and st.last_submitted_at >= latest:
            return st
        return st.model_copy(update={"last_escalated_at": latest})

    def _escalation_waiting(self, profile: Profile, broker: Broker) -> str | None:
        if any(not r.dry_run for r in self.store.list_requests(
                profile.id, broker.id, status=RequestStatus.QUEUED_FOR_APPROVAL)):
            return "awaiting_approval"
        tok = f"manual_email:{broker.id}:"
        if any((t.resume_token or "").startswith(tok) for t in self.store.list_todos(profile.id)):
            return "awaiting_manual_letter"
        return None

    def _letter(self, profile: Profile, broker: Broker, listings: list[Listing],
                law: StateLaw | None, kind: RequestKind, original: Request | None) -> str:
        if not tiers.has_email_route(broker):
            return "no_email_route"
        from .outbox import compose, queue_email, record_manual_letter
        if profile.mailbox is None:
            subject, body = compose(profile, broker, listings, law, kind, original=original)
            word = "follow-up" if kind == RequestKind.FOLLOW_UP else "formal demand"
            todo = assisted.manual_email_todo(
                profile, broker, subject, body,
                title=f"Send a {word} to {broker.name} for {profile.label}").model_copy(
                    update={"resume_token": f"manual_email:{broker.id}:{kind.value}"})
            hmod.persist_todo(self.store, record_manual_letter(
                self.store, todo, listings, kind=kind, original=original, now=self.now))
            return "manual_todo"
        req = queue_email(self.store, profile, broker, listings, kind=kind, state_law=law,
                          dry_run=False, mailer=self.mailer_for(profile), original=original,
                          now=self.now)
        if req.status == RequestStatus.QUEUED_FOR_APPROVAL:
            self.report.queued_emails += 1
        return req.status.value

    def _complaint_todo(self, profile: Profile, broker: Broker, law: StateLaw | None) -> Todo:
        links = [str(u) for u in ([law.ag_complaint_url, *law.other_complaint_urls]
                                  if law else []) if u]
        if profile.state_of_residence == "CA" and CPPA_COMPLAINT_URL not in links:
            links.append(CPPA_COMPLAINT_URL)
        if not links:
            links = [AG_DIRECTORY_URL]
        return Todo(profile_id=profile.id, broker_id=broker.id, kind=TodoKind.COMPLAINT,
                    title=f"{broker.name} ignored {profile.label}'s requests: file a complaint",
                    body=("Free My ID asked several times and the site did not act. You can report "
                          "it to your state's consumer protection office. The links below "
                          "open the complaint forms. Your sent letters are saved as proof."),
                    links=links, resume_token=f"complaint:{broker.id}")

    # ------------------------------------------------------------------ finish
    def _finish(self, profiles: list[Profile]) -> None:
        ids = {p.id for p in profiles}
        todos = [t for t in self.store.list_todos() if t.profile_id in ids]
        queued = [r for r in self.store.list_requests(status=RequestStatus.QUEUED_FOR_APPROVAL)
                  if r.profile_id in ids]
        self.report.open_todos = len(todos)
        n = len(todos) + len(queued)
        if n == 0:
            return
        try:
            # SEC-28: no URL (a bare dashboard URL has no session token and lands on 403);
            # the notifier's click handler opens the app itself.
            body = f"{n} thing{'s' if n != 1 else ''} need you. Open Free My ID to see them."
            self._notifier().notify("Free My ID needs 5 minutes of your help", body, None)
        except Exception as e:  # noqa: BLE001
            log.info("notification failed: %s", type(e).__name__)


def review_todo(store: Store, profile: Profile, broker: Broker, li: Listing, n: int) -> None:
    """The 'Is this you?' to-do for possible matches (deduplicated by handoff.persist_todo).
    Shared by the runner and the exposure scan."""
    what = {"phone_lookup": "phone number", "email_lookup": "email address"}
    kind = next((what[r] for r in li.match_reasons if r in what), None)
    if kind:    # BL-IN-08 reverse-lookup hit: always the person's call (rule 7)
        title = f"Is this {profile.label}'s {kind}? ({broker.name})"
        body = (f"{broker.name} has {n} page(s) for a {kind} {profile.label} asked to "
                f"remove. Open the link and tell us if it is about them.")
    else:
        title = f"Is this {profile.label}? ({broker.name})"
        body = (f"Free My ID found {n} listing(s) on {broker.name} that might be "
                f"{profile.label}. Open the link and tell us if it is them.")
    todo = Todo(profile_id=profile.id, broker_id=broker.id, kind=TodoKind.REVIEW_MATCH,
                title=title, body=body, links=[li.url], resume_token=f"review:{li.id}")
    hmod.persist_todo(store, todo)
