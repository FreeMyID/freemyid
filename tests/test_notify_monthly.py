"""BL-IN-25: monthly progress toast: counts only, at most every 30 days."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from freemyid import notify
from freemyid.models import (
    Address,
    BrokerStatus,
    Consent,
    ConsentBasis,
    ListingState,
    Method,
    PersonName,
    Profile,
    Request,
    RequestKind,
    RequestStatus,
)
from freemyid.storage import Store

T0 = datetime(2026, 11, 1, tzinfo=UTC)


class Rec:
    def __init__(self):
        self.calls = []

    def notify(self, title, body, url=None):
        self.calls.append((title, body))


def _store():
    s = Store()
    p = Profile(label="Pat", name=PersonName(first="Pat", last="Testperson"),
                addresses=[Address(city="Springfield", state="IL", current=True)],
                consent=Consent(basis=ConsentBasis.SELF, attested_by="Pat Testperson",
                                text_version="t"))
    s.save_profile(p)
    return s, p


def _req(p, when, dry=False):
    return Request(profile_id=p.id, broker_id="examplebroker", kind=RequestKind.OPT_OUT,
                   method=Method.EMAIL, status=RequestStatus.SENT, sent_at=when, dry_run=dry)


def test_first_call_only_starts_the_clock(freemyid_env):
    s, _ = _store()
    rec = Rec()
    assert notify.maybe_monthly_progress(s, rec, T0) is False
    assert not rec.calls and (freemyid_env / notify.PROGRESS_MARKER).exists()


def test_sends_once_after_30_days_with_counts_only(freemyid_env):
    s, p = _store()
    rec = Rec()
    notify.maybe_monthly_progress(s, rec, T0)
    s.save_request(_req(p, T0 + timedelta(days=3)))
    s.save_request(_req(p, T0 + timedelta(days=4), dry=True))     # practice: not counted
    s.save_status(BrokerStatus(profile_id=p.id, broker_id="examplebroker",
                               state=ListingState.CONFIRMED))
    assert notify.maybe_monthly_progress(s, rec, T0 + timedelta(days=10)) is False
    assert notify.maybe_monthly_progress(s, rec, T0 + timedelta(days=31)) is True
    (title, body), = rec.calls
    assert "1 request sent" in body and "1 site confirmed" in body and "0 need you" in body
    for word in ("Pat", "Testperson", "Springfield", "examplebroker"):
        assert word not in title + body
    assert notify.maybe_monthly_progress(s, rec, T0 + timedelta(days=40)) is False


def test_quiet_when_nothing_happened(freemyid_env):
    s, _ = _store()
    rec = Rec()
    notify.maybe_monthly_progress(s, rec, T0)
    assert notify.maybe_monthly_progress(s, rec, T0 + timedelta(days=45)) is False
    assert not rec.calls
