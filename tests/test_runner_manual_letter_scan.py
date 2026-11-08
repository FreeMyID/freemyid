"""CodeRabbit (runner._manual_to_email / _apply_scan): a scan-only, dry-run or practice run
keeps the "send it yourself" letter (SEC-118), but a scannable site's scan result must not
then move the status off NEEDS_HUMAN while that letter's to-do is still open. Otherwise a
later real run queues a second (real) email next to the open letter, or "I sent it" on the
kept letter can't record the submission. Fake people and brokers (*.example) only."""
from __future__ import annotations

import asyncio
from datetime import timedelta

from freemyid import config as cfgmod
from freemyid.engine import handoff
from freemyid.engine.mail import FakeMailer
from freemyid.engine.runner import Runner
from freemyid.models import (
    Listing,
    ListingState,
    MatchLevel,
    Registry,
    RequestKind,
    RequestStatus,
    Todo,
    TodoKind,
)
from tests.test_proof_vault import MB, T0, B, _no_mailbox_person, _run_once

S = ListingState


class _ScanRunner(Runner):
    """A Runner whose site is scannable: the scan returns `found` listings (or none)."""

    found: bool = False
    unchecked: bool = False         # SEC-104: the listing sat on an unreadable extra page

    async def _scan(self, ctx, st, tier):
        if not self.found:
            return [], True
        if self.unchecked:
            ctx.scratch["unchecked_urls"] = {"https://fakeb.example/p/1"}
        li = Listing(profile_id=ctx.profile.id, broker_id=ctx.broker.id,
                     url="https://fakeb.example/p/1", match_score=95,
                     match_level=MatchLevel.CONFIRMED)
        return [li], True


def _run(store, p, now, *, found: bool, scan_only=False, dry_run=False, unchecked=False):
    reg = Registry(version="t", updated=T0.date(), brokers=[B])
    cfg = cfgmod.Config(real_submissions_enabled=True, min_delay_s=0, max_delay_s=0)
    r = _ScanRunner(store, reg, scan_only=scan_only, dry_run=dry_run, interactive=False,
                    broker_ids=None, only_due=False, mailer=FakeMailer(), cfg=cfg,
                    state_laws={}, now=now)
    r.found = found
    r.unchecked = unchecked
    return asyncio.run(r.process(p, B))


def _manual(store, p, open_only=True):
    return [t for t in store.list_todos(p.id, open_only=open_only)
            if t.kind == TodoKind.SEND_EMAIL_MANUALLY and t.resume_token == f"manual_email:{B.id}"]


def _opt_outs(store, p, status):
    return [r for r in store.list_requests(p.id, B.id)
            if r.kind == RequestKind.OPT_OUT and r.status == status and not r.dry_run]


def _letter_made(store):
    p = _no_mailbox_person(store)
    _run_once(store, p)                            # blind first run: send-it-yourself letter
    (todo,) = _manual(store, p)
    assert store.get_request(todo.request_id).status == RequestStatus.DRAFT
    assert store.get_status(p.id, B.id).state == S.NEEDS_HUMAN
    return p, todo


def test_scan_only_found_then_real_run_queues_once_and_retires_the_letter(store):
    p, todo = _letter_made(store)
    p = p.model_copy(update={"mailbox": MB})
    store.save_profile(p)

    st = _run(store, p, T0 + timedelta(days=8), found=True, scan_only=True, dry_run=True)
    assert st.state == S.NEEDS_HUMAN, "the open letter keeps the site waiting on the person"
    assert [t.id for t in _manual(store, p)] == [todo.id]
    assert store.get_request(todo.request_id).status == RequestStatus.DRAFT
    assert not _opt_outs(store, p, RequestStatus.QUEUED_FOR_APPROVAL)

    st = _run(store, p, T0 + timedelta(days=16), found=True)
    # SEC-117: the real run retires the letter and queues the email in its place, once
    assert not _manual(store, p), "no actionable letter next to a queued email"
    assert len(_opt_outs(store, p, RequestStatus.QUEUED_FOR_APPROVAL)) == 1
    assert store.get_request(todo.request_id).status == RequestStatus.CANCELLED
    assert st.state == S.FOUND


def test_dry_run_found_keeps_the_letter_consistent(store):
    p, todo = _letter_made(store)
    p = p.model_copy(update={"mailbox": MB})
    store.save_profile(p)
    st = _run(store, p, T0 + timedelta(days=8), found=True, dry_run=True)
    assert st.state == S.NEEDS_HUMAN
    assert [t.id for t in _manual(store, p)] == [todo.id]
    assert store.get_request(todo.request_id).status == RequestStatus.DRAFT
    assert not _opt_outs(store, p, RequestStatus.QUEUED_FOR_APPROVAL)


def test_scan_only_not_found_then_i_sent_it_records_the_submission(store):
    p, todo = _letter_made(store)
    st = _run(store, p, T0 + timedelta(days=8), found=False, scan_only=True, dry_run=True)
    assert st.state == S.NEEDS_HUMAN
    assert [t.id for t in _manual(store, p)] == [todo.id]

    handoff.mark_resolved(store, todo)
    st = store.get_status(p.id, B.id)
    assert st.state == S.SUBMITTED and st.last_submitted_at is not None
    assert store.get_request(todo.request_id).status == RequestStatus.SENT
    assert not _opt_outs(store, p, RequestStatus.QUEUED_FOR_APPROVAL)


def test_real_run_retires_letter_and_listing_gone_cancels_the_draft(store):
    """Mailbox added, then a real run: _manual_to_email retires the letter (SEC-117) but the
    scan no longer finds the listing, so nothing is queued. The retired letter's DRAFT must
    not linger as an open "send it yourself" request with no to-do behind it."""
    p, todo = _letter_made(store)
    p = p.model_copy(update={"mailbox": MB})
    store.save_profile(p)
    st = _run(store, p, T0 + timedelta(days=8), found=False)
    assert st.state == S.NOT_FOUND
    assert not _manual(store, p)
    assert not _opt_outs(store, p, RequestStatus.QUEUED_FOR_APPROVAL)
    assert not _opt_outs(store, p, RequestStatus.DRAFT), "no orphan send-it-yourself DRAFT"
    assert store.get_request(todo.request_id).status == RequestStatus.CANCELLED
    ev = [e for e in store.events(p.id, B.id) if e.action == "manual_letter_retired"]
    assert ev and ev[0].detail == {"request_id": todo.request_id, "why": "nothing_to_send"}


def _retired_events(store, p):
    return [e.detail for e in store.events(p.id, B.id) if e.action == "manual_letter_retired"]


def test_retired_letter_with_deferred_submit_cancels_draft_then_queues_once(store):
    """SEC-104: the run that retires the letter defers the send (the listing was only seen on
    an unreadable page). The DRAFT is cancelled; the next clean real run queues one email."""
    p, todo = _letter_made(store)
    p = p.model_copy(update={"mailbox": MB})
    store.save_profile(p)
    st = _run(store, p, T0 + timedelta(days=8), found=True, unchecked=True)
    assert any(e.action == "submit_deferred" for e in store.events(p.id, B.id))
    assert st.state == S.FOUND
    assert not _manual(store, p)
    assert store.get_request(todo.request_id).status == RequestStatus.CANCELLED
    assert not _opt_outs(store, p, RequestStatus.QUEUED_FOR_APPROVAL)
    assert _retired_events(store, p) == [{"request_id": todo.request_id,
                                          "why": "nothing_to_send"}]

    _run(store, p, T0 + timedelta(days=16), found=True)
    (q,) = _opt_outs(store, p, RequestStatus.QUEUED_FOR_APPROVAL)
    assert q.id != todo.request_id
    assert not _opt_outs(store, p, RequestStatus.DRAFT)
    assert len(_retired_events(store, p)) == 1, "the old DRAFT is cancelled only once"


def test_open_id_request_keeps_the_letter_so_the_hold_never_follows_a_retire(store):
    """An open ID-request to-do for the site is another human to-do, so _manual_to_email does
    not retire the letter (it only retires when the letter is the site's sole to-do). The ID
    hold therefore can't follow a retire on the same site: the letter, its DRAFT and the
    status are kept, nothing is queued and nothing is cancelled."""
    p, todo = _letter_made(store)
    p = p.model_copy(update={"mailbox": MB})
    store.save_profile(p)
    store.save_todo(Todo(profile_id=p.id, broker_id=B.id, kind=TodoKind.ID_UPLOAD,
                         title="Fake B asked for ID", resume_token=f"id_requested:{B.id}"))
    st = _run(store, p, T0 + timedelta(days=8), found=True)
    assert st.state == S.NEEDS_HUMAN
    assert [t.id for t in _manual(store, p)] == [todo.id]
    assert store.get_request(todo.request_id).status == RequestStatus.DRAFT
    assert not _opt_outs(store, p, RequestStatus.QUEUED_FOR_APPROVAL)
    assert not _retired_events(store, p)
