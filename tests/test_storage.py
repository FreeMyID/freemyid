"""storage/db.py: encryption at rest, append-only events, deletion."""
from __future__ import annotations

import sqlite3
import sys

import pytest
from cryptography.exceptions import InvalidTag

from tests.conftest import make_profile
from vanish import paths
from vanish.models import (
    Actor,
    BrokerStatus,
    Event,
    Evidence,
    EvidenceKind,
    Listing,
    ListingState,
    MailboxConfig,
    MatchLevel,
    Method,
    Request,
    RequestKind,
    RequestStatus,
    Todo,
    TodoKind,
)
from vanish.storage import Store

PII = [b"Testperson", b"testperson", b"Evergreen", b"217-555-0142", b"Springfield",
       b"jane.testperson@example.com", b"1980-04-01"]


def _all_bytes(root) -> bytes:
    return b"".join(f.read_bytes() for f in root.rglob("*") if f.is_file())


def _populate(store: Store, p):
    store.save_profile(p)
    li = Listing(profile_id=p.id, broker_id="fakepeople",
                 url="https://fakepeople.example/name/jane-testperson/il",
                 name_shown="Jane Q Testperson", locations_shown=["Springfield, IL"],
                 match_score=90, match_level=MatchLevel.CONFIRMED)
    store.save_listing(li)
    store.save_request(Request(profile_id=p.id, broker_id="fakepeople",
                               kind=RequestKind.OPT_OUT, method=Method.WEB_FORM,
                               listing_ids=[li.id]))
    store.save_todo(Todo(profile_id=p.id, broker_id="fakepeople", kind=TodoKind.REVIEW_MATCH,
                         title="Is this Jane Q Testperson of Springfield?"))
    store.save_status(BrokerStatus(profile_id=p.id, broker_id="fakepeople",
                                   state=ListingState.FOUND))
    store.log(Event(profile_id=p.id, broker_id="fakepeople", actor=Actor.ENGINE,
                    action="scan", detail={"n": 1}))
    ev = store.save_evidence(
        Evidence(profile_id=p.id, broker_id="fakepeople", kind=EvidenceKind.SCREENSHOT,
                 relpath=f"{p.id}/shot.png", sha256=""),
        b"<html>Jane Q Testperson 742 Evergreen Terrace</html>")
    return li, ev


def test_roundtrip(store, profile):
    li, ev = _populate(store, profile)
    assert store.get_profile(profile.id) == profile.model_copy(
        update={"updated_at": store.get_profile(profile.id).updated_at})
    assert store.list_listings(profile.id)[0].url == li.url
    assert store.list_listings(profile.id, "fakepeople")[0].id == li.id
    assert store.read_evidence(ev).startswith(b"<html>Jane")
    assert len(store.list_todos(profile.id)) == 1
    assert store.get_status(profile.id, "fakepeople").state == ListingState.FOUND
    assert store.get_status(profile.id, "nobody").state == ListingState.UNKNOWN
    assert store.events(profile.id)[0].action == "scan"
    assert store.list_requests(status=RequestStatus.DRAFT)


def test_no_plaintext_pii_on_disk(vanish_env, profile):
    s = Store()
    _populate(s, profile)
    raw = _all_bytes(vanish_env)        # db + wal + shm + evidence
    s.close()
    raw += _all_bytes(vanish_env)
    for needle in PII:
        assert needle not in raw, needle


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX mode bits; Windows uses per-user ACLs")
def test_db_file_mode(store):
    assert paths.db_path().stat().st_mode & 0o077 == 0


def test_rows_cannot_be_swapped(store, profile):
    other = make_profile(label="Other")
    store.save_profile(profile)
    store.save_profile(other)
    blob = store._conn.execute("SELECT data FROM profiles WHERE id=?", (other.id,)).fetchone()[0]
    store._conn.execute("UPDATE profiles SET data=? WHERE id=?", (blob, profile.id))
    with pytest.raises(InvalidTag):
        store.get_profile(profile.id)


def test_events_append_only(store):
    store.log(Event(actor=Actor.ENGINE, action="x"))
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        store._conn.execute("UPDATE events SET action='y'")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        store._conn.execute("DELETE FROM events")
    assert [e.action for e in store.events()] == ["x"]


def test_complete_todo(store, profile):
    t = Todo(profile_id=profile.id, kind=TodoKind.REVIEW_MATCH, title="t")
    store.save_todo(t)
    assert store.complete_todo(t.id).done_at is not None
    assert store.list_todos(profile.id) == []
    assert len(store.list_todos(profile.id, open_only=False)) == 1
    assert store.complete_todo("missing") is None


def test_transaction_rollback(store, profile):
    with pytest.raises(RuntimeError), store.transaction():
        store._conn.execute("INSERT INTO meta VALUES ('k', 'v')")
        raise RuntimeError
    assert store._conn.execute("SELECT v FROM meta WHERE k='k'").fetchone() is None


def test_delete_profile_removes_rows_and_evidence(store, profile):
    _, ev = _populate(store, profile)
    store.delete_profile(profile.id)
    assert store.get_profile(profile.id) is None
    for t in ("listings_found", "requests", "evidence", "todos", "broker_status"):
        n = store._conn.execute(f"SELECT count(*) FROM {t} WHERE profile_id=?",
                                (profile.id,)).fetchone()[0]
        assert n == 0, t
    assert not (paths.evidence_dir() / ev.relpath).exists()
    # audit trail survives, with ids only
    assert store.events(profile.id)


# ---- regressions for fixed findings ----

def test_delete_profile_path_traversal(vanish_env, store):
    canary = vanish_env / "canary.txt"
    canary.write_text("keep me")
    try:
        store.delete_profile("..")
    except ValueError:
        pass
    assert canary.exists()


def test_save_evidence_confined(vanish_env, store, profile):
    try:
        store.save_evidence(Evidence.model_construct(
            id="e" * 32, profile_id=profile.id, broker_id="b", kind=EvidenceKind.SCREENSHOT,
            relpath="../escaped.bin", sha256=""), b"x")
    except ValueError:
        pass
    assert not (vanish_env / "escaped.bin").exists()


def test_delete_profile_removes_all_evidence_files(store, profile):
    store.save_profile(profile)
    ev = store.save_evidence(
        Evidence(profile_id=profile.id, broker_id="b", kind=EvidenceKind.SCREENSHOT,
                 relpath="shared/shot.png", sha256=""), b"x")
    store.delete_profile(profile.id)
    assert not (paths.evidence_dir() / ev.relpath).exists()


def test_delete_profile_removes_mailbox_password(store, memkeyring):
    from vanish.secrets import get_mailbox_password, set_mailbox_password
    mb = MailboxConfig(address="removals@example.com", imap_host="imap.example.com",
                       smtp_host="smtp.example.com", username="removals@example.com")
    p = make_profile(mailbox=mb)
    store.save_profile(p)
    set_mailbox_password(p.id, mb, "hunter2")
    store.delete_profile(p.id)
    assert get_mailbox_password(p.id, mb) is None


def test_delete_profile_scrubs_ciphertext(vanish_env, profile):
    s = Store()
    s.save_profile(profile)
    blob = s._conn.execute("SELECT data FROM profiles WHERE id=?", (profile.id,)).fetchone()[0]
    s.delete_profile(profile.id)
    s.close()
    raw = _all_bytes(vanish_env)
    assert blob[14:46] not in raw


def test_events_replace_blocked(store):
    ev = Event(actor=Actor.ENGINE, action="x")
    store.log(ev)
    try:
        store._conn.execute(
            "INSERT OR REPLACE INTO events (id, ts, actor, action, data) VALUES (?,?,?,?,?)",
            (ev.id, "2026-01-01", "engine", "forged", b""))
    except sqlite3.IntegrityError:
        pass
    assert store._conn.execute("SELECT action FROM events").fetchall() == [("x",)]


# ---- v1 contract pieces: tiers + Assisted copy_fields (docs/PLAN_V1.md D1/D2) ----

def test_status_tier_roundtrip(store, profile):
    from vanish.models import Tier
    store.save_profile(profile)
    store.save_status(BrokerStatus(profile_id=profile.id, broker_id="fakepeople",
                                   state=ListingState.FOUND, tier=Tier.ASSISTED))
    assert store.get_status(profile.id, "fakepeople").tier is Tier.ASSISTED
    assert store.list_statuses(profile.id)[0].tier is Tier.ASSISTED
    assert store.get_status(profile.id, "nobody").tier is None


def _assisted_todo(pid):
    return Todo(profile_id=pid, broker_id="fakepeople", kind=TodoKind.ASSISTED_OPT_OUT,
                title="Remove your listing", links=["https://fakepeople.example/optout"],
                copy_fields={"Full name": "Jane Q Testperson", "City": "Springfield",
                             "Email": "jane.testperson@example.com"})


def test_todo_copy_fields_roundtrip_encrypted(vanish_env, profile):
    s = Store()
    s.save_profile(profile)
    t = _assisted_todo(profile.id)
    s.save_todo(t)
    s.save_todo(Todo(profile_id=profile.id, kind=TodoKind.SEND_EMAIL_MANUALLY, title="Send it",
                     copy_fields={"To": "privacy@fakemail.example"}))
    got = {x.kind: x for x in s.list_todos(profile.id)}
    assert got[TodoKind.ASSISTED_OPT_OUT] == t
    assert got[TodoKind.SEND_EMAIL_MANUALLY].copy_fields == {"To": "privacy@fakemail.example"}
    done = s.complete_todo(t.id)
    assert done is not None and done.copy_fields == t.copy_fields
    raw = _all_bytes(vanish_env)
    s.close()
    raw += _all_bytes(vanish_env)
    for needle in [*PII, b"Full name", b"privacy@fakemail.example"]:
        assert needle not in raw, needle
