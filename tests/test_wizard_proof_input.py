"""Optional call note (PHONE_CALL_NOTE) and mailing receipt (POSTAL_RECEIPT) on hand to-dos."""
from __future__ import annotations

import re

from freemyid.models import EvidenceKind, Todo, TodoKind
from freemyid.wizard import proof_input
from tests.test_wizard_dashboard import _assisted, env  # noqa: F401

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
PDF = b"%PDF-1.4\n" + b"0" * 64


def _call(p):
    return Todo(profile_id=p.id, broker_id="callbroker", kind=TodoKind.PHONE_CALL,
                title="Call them", body="Say: please delete me.")


def _post(p):
    return Todo(profile_id=p.id, broker_id="mailbroker", kind=TodoKind.POSTAL_LETTER,
                title="Mail the letter", body="Print and mail it.")


def _kinds(store, p, bid):
    return [e.kind for e in store.list_evidence(p.id, bid)]


def test_cards_show_optional_fields_with_labels(env):  # noqa: F811
    c, store, p, _, _ = env
    store.save_todo(_call(p))
    store.save_todo(_post(p))
    html = c.get("/more").text
    assert 'name="note"' in html and 'for="note-' in html
    assert 'name="receipt"' in html and 'multipart/form-data' in html
    assert "optional" in html
    # one form never contains another
    for m in re.finditer(r"<form[^>]*>(.*?)</form>", html, re.DOTALL):
        assert "<form" not in m.group(1)


def test_call_note_saved_as_encrypted_evidence_and_todo_done(env):  # noqa: F811
    c, store, p, _, f = env
    t = _call(p)
    store.save_todo(t)
    r = c.post(f"/todo/{t.id}/done", data={**f, "note": "Spoke to Sam, ref 123"})
    assert r.status_code == 303 and not store.list_todos()
    (ev,) = store.list_evidence(p.id, "callbroker")
    assert ev.kind == EvidenceKind.PHONE_CALL_NOTE
    body = store.read_evidence(ev).decode()
    assert "Spoke to Sam" in body and "Say: please delete me." in body
    assert b"Spoke to Sam" not in (store_file(ev))


def store_file(ev):
    from freemyid import paths
    return (paths.evidence_dir() / ev.relpath).read_bytes()


def test_empty_note_saves_nothing_but_still_completes(env):  # noqa: F811
    c, store, p, _, f = env
    t = _call(p)
    store.save_todo(t)
    assert c.post(f"/todo/{t.id}/done", data={**f, "note": "  "}).status_code == 303
    assert _kinds(store, p, "callbroker") == [] and not store.list_todos()


def test_receipt_saved_for_png_and_pdf_even_with_wrong_name(env):  # noqa: F811
    c, store, p, _, f = env
    for data in (PNG, PDF):
        t = _post(p)
        store.save_todo(t)
        r = c.post(f"/todo/{t.id}/done", data=f, files={"receipt": ("evil.exe", data)})
        assert r.status_code == 303
    evs = store.list_evidence(p.id, "mailbroker")
    assert [e.kind for e in evs] == [EvidenceKind.POSTAL_RECEIPT] * 2
    assert sorted(e.relpath.rsplit(".", 1)[1] for e in evs) == ["pdf", "png"]
    assert store.read_evidence(evs[0]) in (PNG, PDF)


def test_bad_receipt_is_refused_and_todo_stays(env):  # noqa: F811
    c, store, p, _, f = env
    t = _post(p)
    store.save_todo(t)
    r = c.post(f"/todo/{t.id}/done", data=f, files={"receipt": ("a.png", b"MZ not an image")})
    assert r.headers["location"].endswith("m=bad_receipt") or "bad_receipt" in r.headers["location"]
    assert store.list_todos() and _kinds(store, p, "mailbroker") == []
    big = PNG + b"0" * proof_input.MAX_RECEIPT_BYTES
    r = c.post(f"/todo/{t.id}/done", data=f, files={"receipt": ("a.png", big)})
    assert store.list_todos() and _kinds(store, p, "mailbroker") == []


def test_no_file_chosen_is_fine_and_other_kinds_ignore_fields(env):  # noqa: F811
    c, store, p, _, f = env
    t = _post(p)
    store.save_todo(t)
    assert c.post(f"/todo/{t.id}/done", data=f).status_code == 303
    a = _assisted(p)
    store.save_todo(a)
    c.post(f"/todo/{a.id}/done", data={**f, "note": "x"}, files={"receipt": ("a.png", PNG)})
    assert store.list_evidence(p.id, "examplebroker") == []


def test_receipt_needs_csrf(env):  # noqa: F811
    c, store, p, _, _ = env
    t = _post(p)
    store.save_todo(t)
    r = c.post(f"/todo/{t.id}/done", data={"csrf": "bad"}, files={"receipt": ("a.png", PNG)})
    assert r.status_code == 403 and store.list_todos()
