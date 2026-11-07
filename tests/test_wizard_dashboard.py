"""Draft tests for the D7 dashboard (status sentence, to-do cards). Fake people only."""
from __future__ import annotations

import keyring
import pytest
from fastapi.testclient import TestClient

from freemyid.models import (
    Address,
    BrokerStatus,
    Consent,
    ConsentBasis,
    ListingState,
    PersonName,
    Profile,
    Todo,
    TodoKind,
)
from freemyid.storage import Store
from freemyid.wizard import dashboard as dash
from freemyid.wizard.server import _csrf_for, create_app

TOKEN = "tok-test"


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("FREEMYID_HOME", str(tmp_path))
    monkeypatch.setenv("FREEMYID_TEST_KEY", "dev")
    monkeypatch.setattr(keyring, "set_password", lambda *a: None)
    store = Store()
    opened: list[str] = []
    app = create_app(store, TOKEN, {"testserver"}, registry_loader=lambda: None,
                     open_url=lambda u: opened.append(u) or True)
    c = TestClient(app, follow_redirects=False)
    c.cookies.set("freemyid_session", TOKEN)
    p = Profile(label="Jane", name=PersonName(first="Jane", last="Testperson"),
                addresses=[Address(city="Springfield", state="IL", current=True)],
                consent=Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
                                text_version="t"))
    store.save_profile(p)
    return c, store, p, opened, {"csrf": _csrf_for(TOKEN)}


def _assisted(p):
    return Todo(profile_id=p.id, broker_id="examplebroker", kind=TodoKind.ASSISTED_OPT_OUT,
                title="Remove your listing", body="1. Find your listing\n2. Click Remove",
                links=["https://example.com/optout"],
                copy_fields={"Name": "Jane Testperson", "City": "Springfield, IL"})


def _email(p):
    return Todo(profile_id=p.id, broker_id="mailbroker", kind=TodoKind.SEND_EMAIL_MANUALLY,
                title="Send this letter", body="Please delete my data. Thank you.",
                copy_fields={"To": "privacy@example.com", "Subject": "Deletion request"})


def test_status_sentence():
    sts = [BrokerStatus(profile_id="a" * 32, broker_id=f"b{i}", state=s) for i, s in enumerate(
        [ListingState.REMOVED, ListingState.REMOVED, ListingState.SUBMITTED])]
    s, good = dash.status_sentence(sts, 2, False)
    assert s == "Free My ID is working. 2 sites have confirmed or no longer list you, 1 is still waiting, 2 need you." and not good
    assert dash.status_sentence(sts, 0, False)[1]
    assert "checking now" in dash.status_sentence(sts, 0, True)[0]


def test_assisted_card_buttons_and_copy(env):
    c, store, p, opened, f = env
    t = _assisted(p)
    store.save_todo(t)
    html = c.get("/").text
    assert "Open the site" in html and "I did it" in html and "couldn&#x27;t" in html
    assert html.count('data-copy="') == 2 and "<ol>" in html and "Click Remove" in html
    assert "https://example.com/optout" not in html     # opened server-side only
    assert c.post(f"/todo/{t.id}/open", data=f).status_code == 303
    assert opened == ["https://example.com/optout"]


def test_open_rejects_non_http(env):
    c, store, p, opened, f = env
    t = _assisted(p).model_copy(update={"links": ["file:///etc/passwd", "javascript:alert(1)"]})
    store.save_todo(t)
    c.post(f"/todo/{t.id}/open", data=f)
    assert opened == []


def test_i_did_it_completes_and_could_not(env):
    c, store, p, _, f = env
    t = _assisted(p)
    store.save_todo(t)
    assert c.post(f"/todo/{t.id}/done", data=f).status_code == 303
    assert store.list_todos() == []
    t2 = _assisted(p)
    store.save_todo(t2)
    assert c.post(f"/todo/{t2.id}/couldnt", data=f).status_code == 303
    assert store.list_todos() == []


def test_email_card_and_compose_links(env):
    c, store, p, opened, f = env
    t = _email(p)
    store.save_todo(t)
    html = c.get("/").text
    assert "Please delete my data." in html and "Open in Gmail" in html
    assert "Open in Outlook" in html and "Open in Yahoo Mail" in html
    c.post(f"/todo/{t.id}/compose/gmail", data=f)
    assert opened[0].startswith("https://mail.google.com/") and "privacy%40example.com" in opened[0]
    assert c.post(f"/todo/{t.id}/compose/evil", data=f).status_code == 303
    assert len(opened) == 1


def test_compose_url_encodes_and_truncates():
    u = dash.compose_url("yahoo", "a@b.co", "Hi & bye", "x" * 5000)
    assert u and "%26" in u and len(u) < 2500
    assert dash.compose_url("nope", "a", "b", "c") is None


def test_card_escapes_html(env):
    c, store, p, _, _ = env
    store.save_todo(_assisted(p).model_copy(update={"title": "<script>alert(1)</script>"}))
    assert "<script>alert(1)" not in c.get("/").text


def test_csrf_required_on_todo_post(env):
    c, store, p, _, _ = env
    t = _assisted(p)
    store.save_todo(t)
    assert c.post(f"/todo/{t.id}/done").status_code == 403


def test_status_sentence_first_run_is_gentle():
    sts = [BrokerStatus(profile_id="a" * 32, broker_id=f"b{i}", state=ListingState.FOUND)
           for i in range(3)]
    s, good = dash.status_sentence(sts, 3, False)
    assert s.startswith("Free My ID has made a list of sites") and "need" not in s and not good
    assert dash.status_sentence(sts, 0, False)[1]


def test_outbox_page_discloses_released_emails_escaped():
    from freemyid.models import Method, Request, RequestKind

    r = Request(profile_id="a" * 32, broker_id="b1", kind=RequestKind.OPT_OUT,
                method=Method.EMAIL)
    items = [(r, "Jane <b>", "Site", ("to@x.test", "S", "body"))]
    page = dash.outbox_page(items, "tok", releases={r.id: ["A<script>", "B"]})
    assert "This is the first email for Jane &lt;b&gt;. Approving it also sends the 2 other emails" in page
    assert "(to: A&lt;script&gt;, B)" in page
    assert 'data-confirm="Send this email and 2 others now?"' in page
    assert "<script>" not in page
    plain = dash.outbox_page(items, "tok")
    assert 'data-confirm="Send this email now?"' in plain and "first email for" not in plain
