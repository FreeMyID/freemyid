"""Email pacing at registry scale (roadmap 0.7, engine/pacing.py).

With 700+ email-route brokers one run, or one "approve" click in AUTO mode, used to hand
every letter to the person's own mailbox within a second (measured: 758 emails at 1,000
brokers). Now each removal mailbox sends at most its daily cap per window, the approval
list never holds more than a day's worth, the rest goes out at later runs, and the run
still ends with ONE calm notification. Synthetic brokers and fake people only; nothing is
sent (FakeMailer).
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from freemyid import config as cfgmod
from freemyid.engine import outbox, pacing
from freemyid.engine.mail import FakeMailer
from freemyid.engine.runner import PACED_LINE, run
from freemyid.models import (
    EmailMode,
    MailboxConfig,
    Method,
    Request,
    RequestStatus,
    Tier,
    utcnow,
)
from tests.conftest import make_profile
from tests.scale import registry_gen

N = 1000


def _mailbox(provider: str = "gmail", address: str = "removals@example.com") -> MailboxConfig:
    return MailboxConfig(address=address, provider=provider, imap_host="imap.example.com",
                         smtp_host="smtp.example.com", username=address)


class Notes:
    def __init__(self) -> None:
        self.n: list[tuple[str, str]] = []

    def notify(self, title: str, body: str, url: str | None = None) -> None:
        self.n.append((title, body))


@pytest.fixture
def real_cfg():
    return cfgmod.load().model_copy(update={"real_submissions_enabled": True})


def _real(store, reg, prof, cfg, mailer, notes, now=None):
    return run(store, reg, [prof], scan_only=False, dry_run=False, interactive=False,
               notifier=notes, state_laws={}, cfg=cfg, mailer=mailer, now=now)


def _queued(store, pid):
    return [r for r in store.list_requests(pid, status=RequestStatus.QUEUED_FOR_APPROVAL)
            if not r.dry_run]


def test_auto_mode_is_paced_across_days(store, real_cfg):
    reg = registry_gen.registry(N)
    cap = pacing.PROVIDER_DAILY_CAP["gmail"]
    prof = make_profile(mailbox=_mailbox(), email_mode=EmailMode.AUTO)
    store.save_profile(prof)
    mailer, notes = FakeMailer(), Notes()
    t0 = utcnow()

    rep = _real(store, reg, prof, real_cfg, mailer, notes, now=t0)
    emails = rep.tiers[prof.id][Tier.EMAIL]     # sites reached by email
    assert emails > 5 * cap               # the scale this guards against
    assert mailer.sent == []              # first email waits for the person (SEC-27)
    assert len(_queued(store, prof.id)) == cap
    assert rep.paced_emails == emails - cap
    assert PACED_LINE.format(n=emails - cap, cap=cap) in rep.summary_lines()
    assert len(notes.n) == 1              # one calm message per run

    first = outbox.first_email_pending(store, prof)
    assert first is not None
    outbox.approve_and_send(store, first.id, mailer=mailer, registry=reg, now=t0)
    assert len(mailer.sent) == cap        # one approval releases at most a day's worth

    _real(store, reg, prof, real_cfg, mailer, notes, now=t0 + timedelta(hours=2))
    assert len(mailer.sent) == cap        # same day: nothing more goes out
    assert len(notes.n) == 2

    # paced sites are due again before the next daily run
    paced = [s for s in store.list_statuses(prof.id)
             if s.next_check_at and s.next_check_at <= t0 + timedelta(hours=2)
             + pacing.RETRY_AFTER]
    assert len(paced) >= emails - cap

    later = t0 + timedelta(hours=22)
    _real(store, reg, prof, real_cfg, mailer, notes, now=later)
    assert cap < len(mailer.sent) <= 2 * cap
    sent_window = [r for r in store.list_requests(prof.id, status=RequestStatus.SENT)
                   if r.sent_at and r.sent_at >= later - pacing.WINDOW]
    assert len(sent_window) <= cap


def test_approve_each_queue_never_exceeds_a_days_worth(store, real_cfg):
    reg = registry_gen.registry(N)
    cap = pacing.PROVIDER_DAILY_CAP["yahoo"]
    prof = make_profile(mailbox=_mailbox("yahoo"))
    store.save_profile(prof)
    mailer, notes = FakeMailer(), Notes()
    t0 = utcnow()
    _real(store, reg, prof, real_cfg, mailer, notes, now=t0)
    _real(store, reg, prof, real_cfg, mailer, notes, now=t0 + timedelta(days=1))
    assert mailer.sent == []
    assert len(_queued(store, prof.id)) == cap   # not approved yet: no new pile-up


def test_dry_run_is_not_paced(store):
    reg = registry_gen.registry(N)
    prof = make_profile(mailbox=_mailbox(), email_mode=EmailMode.AUTO)
    store.save_profile(prof)
    rep = run(store, reg, [prof], scan_only=False, dry_run=True, interactive=False,
              notifier=Notes(), state_laws={})
    assert rep.paced_emails == 0
    assert rep.drafted_emails == rep.tiers[prof.id][Tier.EMAIL] > 500


def _sent(prof, when) -> Request:
    return Request(profile_id=prof.id, broker_id="fakee00001", kind="opt_out",
                   method=Method.EMAIL, status=RequestStatus.SENT, sent_at=when,
                   created_at=when)


def test_pacer_budget_is_shared_per_mailbox_and_windowed(store):
    now = utcnow()
    a = make_profile(label="Mom", mailbox=_mailbox("other"))
    b = make_profile(label="Dad", mailbox=_mailbox("other", "Removals@Example.com "))
    c = make_profile(label="Kid", mailbox=_mailbox("other", "kid@example.com"))
    for p in (a, b, c):
        store.save_profile(p)
    cap = pacing.PROVIDER_DAILY_CAP["other"]
    for i in range(10):
        store.save_request(_sent(a, now - timedelta(hours=1, minutes=i)))
    store.save_request(_sent(b, now - pacing.WINDOW - timedelta(minutes=1)))   # too old
    store.save_request(_sent(a, now).model_copy(update={"dry_run": True}))     # practice
    store.save_request(Request(profile_id=b.id, broker_id="fakee00002", kind="opt_out",
                               method=Method.EMAIL, status=RequestStatus.QUEUED_FOR_APPROVAL))
    pacer = pacing.SendPacer(store, now)
    assert pacer.sends_left(a) == pacer.sends_left(b) == cap - 10
    assert pacer.new_left(b) == cap - 11
    assert pacer.sends_left(c) == cap
    assert all(pacer.take_new(c) for _ in range(cap))
    assert not pacer.take_new(c) and pacer.paced[c.id] == 1
    assert pacer.take_send(c)           # sending a reserved request stays in budget
    assert pacer.sends_left(make_profile()) == 0       # no mailbox: never sends
