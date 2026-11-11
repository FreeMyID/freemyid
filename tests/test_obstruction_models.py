"""WO-620: compliance-evidence engine contracts (docs/EVIDENCE_ENGINE.md section 4)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from freemyid.models import (
    BUNDLE_GENESIS,
    TECHNICAL_OBSTRUCTIONS,
    BundleEntry,
    BundleManifest,
    EvidenceKind,
    ObstructionKind,
    ObstructionRecord,
    new_id,
)

T0 = datetime(2026, 11, 11, 15, 0, tzinfo=UTC)
H = "a" * 64


def _rec(**kw) -> ObstructionRecord:
    base = {"profile_id": new_id(), "broker_id": "spokeo", "surface": "optout_form",
            "kind": ObstructionKind.CAPTCHA_ON_REQUEST, "observed_at": [T0], "state": "sc"}
    base.update(kw)
    return ObstructionRecord(**base)


def test_state_is_uppercased_and_defaults_to_observed():
    r = _rec()
    assert r.state == "SC" and r.confidence == "observed"


def test_search_surface_is_not_a_request_surface():
    with pytest.raises(ValidationError):
        _rec(surface="search_page")


@pytest.mark.parametrize("kind", sorted(TECHNICAL_OBSTRUCTIONS - {ObstructionKind.UNAVAILABLE}))
def test_technical_kind_needs_two_days_to_confirm(kind):
    with pytest.raises(ValidationError, match="two different days"):
        _rec(kind=kind, confidence="confirmed", observed_at=[T0, T0 + timedelta(hours=3)])
    ok = _rec(kind=kind, confidence="confirmed", observed_at=[T0, T0 + timedelta(days=1)])
    assert ok.confidence == "confirmed"


@pytest.mark.parametrize("kind", [ObstructionKind.REQUEST_DENIED, ObstructionKind.DEADLINE_MISSED,
                                  ObstructionKind.AGENT_REFUSED])
def test_reply_and_clock_kinds_confirm_at_once(kind):
    assert _rec(kind=kind, surface="email", confidence="confirmed").confidence == "confirmed"


def test_needs_at_least_one_sighting_and_sane_fields():
    with pytest.raises(ValidationError):
        _rec(observed_at=[])
    with pytest.raises(ValidationError):
        _rec(http_status=99)
    with pytest.raises(ValidationError):
        _rec(vendor="Not A Slug!")
    assert _rec(vendor="recaptcha-v2", http_status=403).vendor == "recaptcha-v2"


def test_record_has_no_free_text_fields_for_pii():
    """Every field is an id, enum, slug, number, date, state code or id list."""
    allowed = {"id", "profile_id", "broker_id", "request_id", "surface", "kind", "vendor",
               "http_status", "observed_at", "request_sent_at", "legal_due_on", "state",
               "statute_ids", "evidence_ids", "confidence"}
    assert set(ObstructionRecord.model_fields) == allowed


def test_new_evidence_kinds():
    assert EvidenceKind("block_capture") is EvidenceKind.BLOCK_CAPTURE
    assert EvidenceKind("response_timeline") is EvidenceKind.RESPONSE_TIMELINE


def _entry(seq: int) -> BundleEntry:
    return BundleEntry(seq=seq, evidence_id=new_id(), kind=EvidenceKind.HTML, created_at=T0,
                       sha256=H, prev_hash=H)


def test_manifest_requires_ordered_entries_and_hex_hashes():
    m = BundleManifest(obstruction_id=new_id(), app_version="0.5.0",
                       entries=[_entry(0), _entry(1)], chain_head=H, manifest_sha256=H)
    assert m.version == 1 and m.timestamp_token is None
    with pytest.raises(ValidationError, match="0..n-1"):
        BundleManifest(obstruction_id=new_id(), app_version="0.5.0",
                       entries=[_entry(1), _entry(0)], chain_head=H, manifest_sha256=H)
    with pytest.raises(ValidationError):
        BundleManifest(obstruction_id=new_id(), app_version="0.5.0", entries=[],
                       chain_head=H, manifest_sha256=H)
    with pytest.raises(ValidationError):
        BundleEntry(seq=0, evidence_id=new_id(), kind=EvidenceKind.HTML, created_at=T0,
                    sha256="XYZ", prev_hash=H)


def test_bundle_genesis_is_sha256_of_the_version_tag():
    import hashlib
    assert BUNDLE_GENESIS == hashlib.sha256(b"freemyid-bundle-v1").hexdigest()
