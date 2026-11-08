"""SEC-98: rejected wizard fields carry aria-invalid and aria-describedby to their alert."""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from freemyid.storage import Store
from freemyid.wizard import ui
from freemyid.wizard.draft import Draft
from freemyid.wizard.server import _csrf_for, create_app

TOKEN = "tok-sec98"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FREEMYID_HOME", str(tmp_path))
    monkeypatch.setenv("FREEMYID_TEST_KEY", "dev")
    app = create_app(Store(), TOKEN, {"testserver"}, registry_loader=lambda: None)
    c = TestClient(app, follow_redirects=False)
    c.cookies.set("freemyid_session", TOKEN)
    return c, {"csrf": _csrf_for(TOKEN)}


def _tag(page: str, name: str) -> str:
    m = re.search(r'<(?:input|textarea)\b[^>]*\b(?:id|name)="' + name + r'"[^>]*>', page)
    assert m, f"no field {name}"
    return m.group(0)


def _assert_linked(page: str, name: str) -> None:
    tag = _tag(page, name)
    assert 'aria-invalid="true"' in tag, tag
    ids = re.search(r'aria-describedby="([^"]+)"', tag)
    assert ids, tag
    for i in ids.group(1).split():
        assert re.search(rf'<div class="error" role="alert" id="{i}">', page), i


def _consent(c, f):
    r = c.post("/wizard/consent", data={**f, "basis": "self", "attested_by": "Pat Testperson",
                                       "ack": "1"})
    assert r.status_code == 303


def test_name_step(client):
    c, f = client
    _consent(c, f)
    r = c.post("/wizard/name", data={**f, "first": " ", "last": "Testperson"})
    assert r.status_code == 400
    _assert_linked(r.text, "first")
    _assert_linked(r.text, "last")
    assert 'role="alert"' in r.text


def test_previous_names(client):
    c, f = client
    _consent(c, f)
    r = c.post("/wizard/name", data={**f, "first": "Pat", "last": "T", "previous_names": "Madonna"})
    assert r.status_code == 400
    _assert_linked(r.text, "previous_names")


def test_consent_step(client):
    c, f = client
    r = c.post("/wizard/consent", data={**f, "basis": "self"})
    assert r.status_code == 400
    _assert_linked(r.text, "attested_by")
    _assert_linked(r.text, "ack")


def test_address_step(client):
    c, f = client
    _consent(c, f)
    r = c.post("/wizard/address", data={**f, "city0": "Springfield", "state0": "Illinois"})
    assert r.status_code == 400
    _assert_linked(r.text, "city0")
    _assert_linked(r.text, "state0")
    r = c.post("/wizard/address", data={**f, "city0": "", "state0": ""})
    assert r.status_code == 400
    _assert_linked(r.text, "city0")


def test_about_step(client):
    c, f = client
    _consent(c, f)
    r = c.post("/wizard/about", data={**f, "birth_year": "19x2"})
    assert r.status_code == 400
    _assert_linked(r.text, "birth_year")


def test_mailbox_step(client):
    c, f = client
    _consent(c, f)
    r = c.post("/wizard/mailbox", data={**f, "provider": "gmail", "address": "nope"})
    assert r.status_code == 400
    _assert_linked(r.text, "address")
    _assert_linked(r.text, "password")


def test_existing_describedby_is_kept():
    body = '<input id="first" name="first" aria-describedby="hint-1">'
    out = ui.mark_invalid(body, "name", ["First and last name are required."])
    assert 'aria-describedby="hint-1 err-0"' in out and 'aria-invalid="true"' in out


def test_no_errors_no_attributes():
    page = ui.step_page("name", Draft(), "c", [])
    assert "aria-invalid" not in page
