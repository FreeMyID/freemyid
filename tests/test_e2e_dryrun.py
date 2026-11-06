"""End-to-end dry run (docs/PLAN_V1.md D1/D2) against the dev fixture registry + local server.

Runs against `vanish.engine.runner.run` and `vanish.engine._dev` (fixture_registry +
fixture_server). The assertions below are the acceptance criteria; do not loosen them.

Network: conftest blocks every socket connect that isn't loopback, so the fixture server on
127.0.0.1 is the only thing reachable. SMTP is additionally patched to fail loudly.
"""
from __future__ import annotations

import importlib
import smtplib

import pytest

from tests.conftest import make_profile
from vanish.models import (
    ListingState,
    MailboxConfig,
    ProfileField,
    RequestStatus,
    Tier,
    TodoKind,
)

# Candidate homes for the dev fixture registry/server (automation-engineer, PLAN_V1 wave 1).
# Expected API: fixture_registry() -> models.Registry whose URLs point at the server, and
# fixture_server() -> context manager yielding the base URL (http://127.0.0.1:<port>).
_DEV_MODULES = ("vanish.engine._dev", "vanish._dev", "vanish.engine.devrun")


def _load_dev():
    try:
        runner = importlib.import_module("vanish.engine.runner")
        run = runner.run
    except (ImportError, AttributeError) as e:
        pytest.skip(f"vanish.engine.runner.run not landed yet (automation-engineer): {e}")
    for name in _DEV_MODULES:
        try:
            mod = importlib.import_module(name)
        except ImportError:
            continue
        if hasattr(mod, "fixture_registry") and hasattr(mod, "fixture_server"):
            return run, mod.fixture_registry, mod.fixture_server
    pytest.skip("dev fixture registry/server not landed yet (automation-engineer); looked in "
                + ", ".join(_DEV_MODULES) + " for fixture_registry() + fixture_server()")


@pytest.fixture
def no_smtp(monkeypatch):
    sent: list[tuple] = []

    class _Boom:
        def __init__(self, *a, **k):
            sent.append(a)
            raise AssertionError("SMTP used during dry run")

    monkeypatch.setattr(smtplib, "SMTP", _Boom)
    monkeypatch.setattr(smtplib, "SMTP_SSL", _Boom)
    return sent


def _mailbox():
    return MailboxConfig(address="removals.testperson@example.com", imap_host="imap.example.com",
                         smtp_host="smtp.example.com", username="removals.testperson@example.com")


def _expected_tier(broker, has_mailbox: bool) -> Tier:
    """D1 + D2 rules."""
    if (broker.form and broker.verification_status == "verified"
            and broker.method == "web_form"):
        return Tier.AUTOMATIC
    if broker.opt_out_email and has_mailbox:
        return Tier.EMAIL
    return Tier.ASSISTED


def _forbidden_values(profile, allowed: set[ProfileField]) -> list[str]:
    """Profile values that must never appear in copy_fields given the allowed fields."""
    bad: list[str] = [*profile.relatives, *profile.emails]   # personal emails: never
    if profile.dob:
        d = profile.dob
        bad += [d.isoformat(), f"{d.month:02d}/{d.day:02d}/{d.year}", str(d.year)]
    if not (ProfileField.PHONE in allowed and profile.permissions.allow_phone_disclosure):
        bad += profile.phones
    if ProfileField.STREET_ADDRESS not in allowed:
        bad += [a.street for a in profile.addresses]
    if ProfileField.ZIP not in allowed:
        bad += [a.zip for a in profile.addresses if a.zip]
    return [b for b in bad if b]


def _run(store, registry, profiles, run):
    return run(store, registry, profiles, scan_only=False, dry_run=True, interactive=False)


@pytest.mark.parametrize("with_mailbox", [True, False], ids=["mailbox", "no-mailbox"])
def test_dryrun_end_to_end(store, no_smtp, with_mailbox):
    run, fixture_registry, fixture_server = _load_dev()
    profile = make_profile(mailbox=_mailbox() if with_mailbox else None)
    store.save_profile(profile)

    with fixture_server():
        registry = fixture_registry()
        report = _run(store, registry, [profile], run)

    assert report.errors == 0, report.summary_lines()

    # D1: every broker gets a tier, and the right one.
    statuses = {s.broker_id: s for s in store.list_statuses(profile.id)}
    for b in registry.brokers:
        st = statuses.get(b.id)
        assert st is not None and st.tier is not None, b.id
        assert st.tier is _expected_tier(b, with_mailbox), (b.id, st.tier)

    # D1: ASSISTED todos only carry data-minimized copy_fields.
    listings = {}
    for li in store.list_listings(profile.id):
        listings.setdefault(li.broker_id, []).append(li)
    brokers = {b.id: b for b in registry.brokers}
    todos = store.list_todos(profile.id)
    for t in todos:
        if t.kind not in (TodoKind.ASSISTED_OPT_OUT, TodoKind.SEND_EMAIL_MANUALLY):
            continue
        assert t.broker_id in brokers, t.kind
        allowed = {f for li in listings.get(t.broker_id, []) for f in li.shown_fields}
        allowed |= {ProfileField.EMAIL, ProfileField.LISTING_URL}
        values = " | ".join(t.copy_fields.values())
        for v in _forbidden_values(profile, allowed):
            assert v not in values, (t.broker_id, t.kind)
        # The only email a broker ever gets is the removal mailbox.
        for v in t.copy_fields.values():
            if "@" in v and with_mailbox:
                assert v in (profile.mailbox.address, brokers[t.broker_id].opt_out_email), t.kind
    # D2: without a mailbox, email-tier brokers become manual-send/assisted todos.
    if not with_mailbox:
        assert not any(s.tier is Tier.EMAIL for s in statuses.values())

    # Dry run: nothing sent, nothing submitted.
    assert no_smtp == []
    for r in store.list_requests(profile.id):
        assert r.status is not RequestStatus.SENT, r.id
        assert r.dry_run, r.id
    assert not any(s.state is ListingState.SUBMITTED for s in statuses.values())
    assert all(s.last_submitted_at is None for s in statuses.values())
