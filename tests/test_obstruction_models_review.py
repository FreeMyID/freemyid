"""qa-security review of WO-620 (evidence engine contracts), 2026-11-11.

Strict xfails pin findings SEC-WO620-1..6: each one flips to XPASS (and fails the suite) once
the contract is fixed, so the fixer must drop the marker. The passing tests are guards for
what the review confirmed is already right.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from freemyid.models import (
    BundleEntry,
    BundleManifest,
    EvidenceKind,
    ObstructionKind,
    ObstructionRecord,
    new_id,
)
from freemyid.submitters import base
from tests.conftest import make_profile

T0 = datetime(2026, 11, 11, 15, 0, tzinfo=UTC)
H = "a" * 64


def _rec(**kw) -> ObstructionRecord:
    data = {"profile_id": new_id(), "broker_id": "spokeo", "surface": "optout_form",
            "kind": ObstructionKind.CAPTCHA_ON_REQUEST, "observed_at": [T0], "state": "sc"}
    data.update(kw)
    return ObstructionRecord(**data)


def _entry(seq: int, evidence_id: str | None = None) -> BundleEntry:
    return BundleEntry(seq=seq, evidence_id=evidence_id or new_id(), kind=EvidenceKind.HTML,
                       created_at=T0, sha256=H, prev_hash=H)


# --------------------------------------------------------------- SEC-WO620-1 (MEDIUM)
# "Two different days" is checked with t.date() on each value's own tzinfo, so it measures
# calendar labels, not elapsed time. A complaint (a legal act in the person's name) could
# rest on one transient blip.

def test_two_sightings_minutes_apart_across_midnight_do_not_confirm():
    late = datetime(2026, 11, 11, 23, 55, tzinfo=UTC)
    with pytest.raises(ValidationError):
        _rec(confidence="confirmed", observed_at=[late, late + timedelta(minutes=10)])


def test_same_instant_in_two_timezones_is_one_sighting():
    t = datetime(2026, 11, 11, 2, 0, tzinfo=UTC)
    eastern = t.astimezone(timezone(timedelta(hours=-5)))     # 2026-11-10 21:00 local
    with pytest.raises(ValidationError):
        _rec(confidence="confirmed", observed_at=[t, eastern])


def test_observed_at_must_be_timezone_aware():
    with pytest.raises(ValidationError):
        _rec(observed_at=[datetime(2026, 11, 11, 1, 0)])


# --------------------------------------------------------------- SEC-WO620-2 (MEDIUM)
# EVIDENCE_ENGINE.md section 4/5: UNAVAILABLE needs >= 3 runs over >= 7 days. The validator
# gives it the generic two-day rule.

def test_unavailable_needs_three_runs_over_seven_days():
    with pytest.raises(ValidationError):
        _rec(kind=ObstructionKind.UNAVAILABLE, confidence="confirmed",
             observed_at=[T0, T0 + timedelta(days=1)])
    ok = _rec(kind=ObstructionKind.UNAVAILABLE, confidence="confirmed",
              observed_at=[T0, T0 + timedelta(days=3), T0 + timedelta(days=7)])
    assert ok.confidence == "confirmed"


# --------------------------------------------------------------- SEC-WO620-3 (MEDIUM)
# The record is documented "PII-free by construction, safe for Events and statistics", but
# statute_ids takes any string of any length, and vendor/state take anything slug- or
# two-character-shaped.

def test_statute_ids_cannot_carry_free_text():
    with pytest.raises(ValidationError):
        _rec(statute_ids=["Jane Q Testperson, 12 Elm St, Springfield IL 62701"])


def test_vendor_is_a_known_vendor_not_any_slug():
    with pytest.raises(ValidationError):
        _rec(vendor="jane.q.testperson")


def test_state_is_two_letters():
    with pytest.raises(ValidationError):
        _rec(state="1!")


# --------------------------------------------------------------- SEC-WO620-4 (LOW)

def test_lists_are_bounded():
    with pytest.raises(ValidationError):
        _rec(observed_at=[T0] * 10_000)


# --------------------------------------------------------------- SEC-WO620-5 (LOW)

def test_bundle_rejects_duplicate_evidence():
    eid = new_id()
    with pytest.raises(ValidationError):
        BundleManifest(obstruction_id=new_id(), app_version="0.5.0",
                       entries=[_entry(0, eid), _entry(1, eid)], chain_head=H,
                       manifest_sha256=H)


def test_app_version_is_a_version_string():
    with pytest.raises(ValidationError):
        BundleManifest(obstruction_id=new_id(), app_version="Jane Q Testperson",
                       entries=[_entry(0)], chain_head=H, manifest_sha256=H)


# --------------------------------------------------------------- guards (pass today)

@pytest.mark.parametrize("bad", [H + "\n", H.upper(), "a" * 63, "g" * 64])
def test_sha256_fields_reject_non_lowercase_hex(bad):
    with pytest.raises(ValidationError):
        BundleEntry(seq=0, evidence_id=new_id(), kind=EvidenceKind.HTML, created_at=T0,
                    sha256=bad, prev_hash=H)


def test_reply_kind_confirms_with_one_sighting():
    r = _rec(kind=ObstructionKind.REQUEST_DENIED, surface="email", confidence="confirmed")
    assert r.observed_at == [T0]


@pytest.mark.parametrize("kind", [EvidenceKind.BLOCK_CAPTURE, EvidenceKind.RESPONSE_TIMELINE])
def test_new_evidence_kinds_round_trip_through_the_store(store, kind):
    p = make_profile()
    store.save_profile(p)
    payload = b'{"status": 403, "vendor": "cloudflare-block"}'
    ev = store.save_evidence(base.evidence(p.id, "spokeo", kind, "json"), payload)
    (got,) = store.list_evidence(p.id, "spokeo")
    assert ev.sha256 and got.kind is kind and store.read_evidence(got) == payload
