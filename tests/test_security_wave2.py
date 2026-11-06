"""Security review, v1 wave 2 (engine runner/outbox/mail, wizard dashboard/desktop, scheduler,
`vanish wipe`). See docs/SECURITY_REVIEW.md SEC-16 onward. Fake people and fake domains only.

Strict xfails mark open findings: when the fix lands the test XPASSes and fails the run, so
remove the marker then.
"""
from __future__ import annotations

import asyncio
import glob
import os
import smtplib
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET
from datetime import date
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from tests.conftest import make_profile
from vanish import config as cfgmod
from vanish.consent import CURRENT_TEXT_VERSION
from vanish.models import (
    Broker,
    Consent,
    ConsentBasis,
    Listing,
    MailboxConfig,
    MatchLevel,
    Permissions,
    ProfileField,
    RequestStatus,
    Todo,
    TodoKind,
)
from vanish.wizard.server import _csrf_for, create_app

F = ProfileField
TOKEN = "tok-sec-wave2"
MB = MailboxConfig(address="removals.testperson@example.com", imap_host="imap.example.com",
                   smtp_host="smtp.example.com", username="removals.testperson@example.com")
# Values that must never reach a broker (letters, copy buttons) unless explicitly allowed.
NEVER = ("1980-04-01", "04/01/1980", "John Testperson", "jane.testperson@example.com")
PHONE = "217-555-0142"

BROKER = Broker(id="fakeb", name="Fake B", url="https://fakeb.example/", category="data_broker",
                domains=["fakeb.example"], method="email", opt_out_email="privacy@fakeb.example",
                confirmation_domains=["mail.fakeb.example"],
                required_fields=[F.FULL_NAME, F.CITY, F.STATE, F.PHONE, F.DOB, F.AGE,
                                 F.STREET_ADDRESS, F.ZIP, F.EMAIL, F.LISTING_URL])


def person(**over):
    c = Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
                text_version=CURRENT_TEXT_VERSION)
    return make_profile(consent=c, **over)


def listing(p, shown):
    return Listing(profile_id=p.id, broker_id=BROKER.id, url="https://fakeb.example/p/1",
                   name_shown="Jane Testperson", match_level=MatchLevel.CONFIRMED, match_score=1.0,
                   shown_fields=list(shown))


@pytest.fixture
def no_smtp(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("SMTP used")
    monkeypatch.setattr(smtplib, "SMTP", boom)
    monkeypatch.setattr(smtplib, "SMTP_SSL", boom)


@pytest.fixture
def client(store):
    opened: list[str] = []
    app = create_app(store, TOKEN, {"testserver"}, registry_loader=lambda: None,
                     open_url=lambda u: opened.append(u) or True)
    c = TestClient(app, follow_redirects=False)
    return c, app, opened


def _authed(c):
    c.cookies.set("vanish_session", TOKEN)
    return {"csrf": _csrf_for(TOKEN)}


# --------------------------------------------------------------------------- real-send guard


def test_runner_forces_dry_run_unless_real_enabled(store, fake_registry, monkeypatch):
    from vanish.engine.runner import Runner
    monkeypatch.delenv("VANISH_DEV_FIXTURES", raising=False)
    kw = {"scan_only": False, "dry_run": False, "interactive": False, "broker_ids": None,
          "only_due": False, "state_laws": {}}
    assert Runner(store, fake_registry, cfg=cfgmod.Config(), **kw).dry_run is True
    on = cfgmod.Config(real_submissions_enabled=True)
    assert Runner(store, fake_registry, cfg=on, **kw).dry_run is False
    assert Runner(store, fake_registry, cfg=on, **{**kw, "scan_only": True}).dry_run is True


def test_approve_and_send_refuses_without_real_enabled(store, fake_registry, no_smtp,
                                                      monkeypatch):
    from vanish.engine.outbox import OutboxError, approve_and_send, queue_email, send_request
    monkeypatch.delenv("VANISH_DEV_FIXTURES", raising=False)
    p = person(mailbox=MB)
    store.save_profile(p)
    b = fake_registry.get("fakemail")
    req = queue_email(store, p, b, [], dry_run=False, mailer=None)
    assert req.status == RequestStatus.QUEUED_FOR_APPROVAL
    with pytest.raises(OutboxError):
        approve_and_send(store, req.id, registry=fake_registry)
    assert store.get_request(req.id).status == RequestStatus.QUEUED_FOR_APPROVAL
    draft = queue_email(store, p, b, [], dry_run=True, mailer=None)
    with pytest.raises(OutboxError):
        send_request(store, draft, p, mailer=SimpleNamespace(send=None))


def test_first_run_thread_is_practice_mode(store, monkeypatch):
    from vanish.engine import runner
    from vanish.wizard import server
    p = person()
    store.save_profile(p)
    calls: list[dict] = []
    monkeypatch.setattr(runner, "run", lambda *a, **k: calls.append(k))
    monkeypatch.setattr(server, "_background_disabled", lambda: False)
    app = SimpleNamespace(state=SimpleNamespace(running=False))
    server._default_finish(app, lambda: SimpleNamespace(brokers=[]), p, False)
    for t in threading.enumerate():
        if t.name == "vanish-first-run":
            t.join(10)
    assert calls and calls[0]["dry_run"] is True and calls[0]["scan_only"] is False


def test_real_submissions_switch_needs_session_csrf_and_origin(client):
    c, _app, _ = client
    assert c.post("/settings/submissions/on").status_code == 403          # no session
    form = _authed(c)
    assert c.post("/settings/submissions/on").status_code == 403          # no csrf
    assert c.post("/settings/submissions/on", data={"csrf": "x" * 64}).status_code == 403
    r = c.post("/settings/submissions/on", data=form,
               headers={"Origin": "http://evil.example"})
    assert r.status_code == 403
    assert cfgmod.load().real_submissions_enabled is False
    assert 'data-confirm="Start sending real removal requests?"' in c.get("/settings").text
    assert c.post("/settings/submissions/on", data=form).status_code == 303
    assert cfgmod.load().real_submissions_enabled is True
    c.post("/settings/submissions/off", data=form)
    assert cfgmod.load().real_submissions_enabled is False


def test_focus_endpoint_needs_session_and_csrf(client):
    c, app, _ = client
    hits: list[int] = []
    app.state.on_focus = lambda: hits.append(1)
    assert c.post("/_focus").status_code == 403
    _authed(c)
    assert c.post("/_focus").status_code == 403
    assert c.post("/_focus", headers={"X-CSRF": _csrf_for(TOKEN)}).status_code == 200
    assert hits == [1]


def test_scheduled_run_in_practice_mode_runs_dry(store, monkeypatch):
    from vanish import cli
    from vanish.engine import runner
    store.save_profile(person())
    calls: list[dict] = []
    monkeypatch.setattr(runner, "run",
                        lambda *a, **k: calls.append(k) or SimpleNamespace(summary_lines=list))
    res = CliRunner().invoke(cli.app, ["run", "--scheduled"])
    assert res.exit_code == 0
    assert calls and calls[0]["dry_run"] is True


@pytest.mark.xfail(strict=True, reason="SEC-21: VANISH_DEV_FIXTURES honored for any URL")
def test_dev_fixture_base_must_be_loopback(monkeypatch):
    from vanish.engine.runner import dev_fixture_base
    monkeypatch.setenv("VANISH_DEV_FIXTURES", "http://collector.example:80")
    assert dev_fixture_base() is None


# --------------------------------------------------------------------------- dashboard opens


def test_open_only_http_links_from_the_stored_todo(client, store):
    c, _app, opened = client
    form = _authed(c)
    p = person()
    store.save_profile(p)
    bad = Todo(profile_id=p.id, broker_id="fakeb", kind=TodoKind.ASSISTED_OPT_OUT, title="t",
               body="b", links=["javascript:alert(1)", "file:///etc/passwd",
                                "data:text/html,x", "mailto:a@fakeb.example"])
    store.save_todo(bad)
    assert c.post(f"/todo/{bad.id}/open", data=form).status_code == 303
    assert c.post("/todo/not-a-todo/open", data=form).status_code == 303
    assert c.post(f"/todo/{bad.id}/compose/evil", data=form).status_code == 303
    assert opened == []
    good = Todo(profile_id=p.id, broker_id="fakeb", kind=TodoKind.ASSISTED_OPT_OUT,
                title="t", body="b",
                links=["file:///x", "https://fakeb.example/optout?next=/x"])
    store.save_todo(good)
    c.post(f"/todo/{good.id}/open", data=form, params={"url": "https://evil.example/"})
    assert opened == ["https://fakeb.example/optout?next=/x"]


@pytest.mark.xfail(strict=True, reason="SEC-19: plain http:// links are opened")
def test_open_refuses_plain_http(client, store):
    c, _app, opened = client
    form = _authed(c)
    p = person()
    store.save_profile(p)
    t = Todo(profile_id=p.id, broker_id="fakeb", kind=TodoKind.ASSISTED_OPT_OUT, title="t",
             body="b", links=["http://fakeb.example/optout"])
    store.save_todo(t)
    c.post(f"/todo/{t.id}/open", data=form)
    assert opened == []


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX modes")
def test_instance_file_is_private(vanish_env):
    from vanish.wizard import desktop
    desktop.write_instance(1234, "secret-token")
    assert (desktop._instance_path().stat().st_mode & 0o077) == 0
    assert (Path(vanish_env).stat().st_mode & 0o077) == 0


# --------------------------------------------------------------------------- IMAP links


def _mail(sender: str, html: str) -> bytes:
    m = EmailMessage()
    m["From"] = sender
    m["To"] = MB.address
    m["Subject"] = "Confirm your request"
    m.set_content("see html")
    m.add_alternative(html, subtype="html")
    return m.as_bytes()


def test_confirmation_links_only_on_confirmation_domains():
    from vanish.engine.mail import SmtpImapMailer, extract_links
    hrefs = [
        "https://mail.fakeb.example/confirm?t=1",               # ok
        "https://mail.fakeb.example.evil.example/confirm",      # suffix lookalike
        "https://evilmail.fakeb.example.com/confirm",
        "https://xmail.fakeb.example/confirm",                  # no dot boundary
        "https://mail.fakeb.example@evil.example/confirm",      # userinfo trick
        "https://evil.example\\@mail.fakeb.example/confirm",    # backslash trick
        "https://mail.fakeb.exаmple/confirm",                   # Cyrillic a
        "http://mail.fakeb.example/confirm",                    # not https
        "javascript:alert(1)",
        "https://fakeb.example/privacy",                         # broker, not confirmation
    ]
    html = "".join(f'<a href="{h}">x</a>' for h in hrefs)
    raw = _mail("Fake B <no-reply@fakeb.example>", html)
    assert extract_links(raw, BROKER.confirmation_domains) == [hrefs[0]]
    m = SmtpImapMailer.__new__(SmtpImapMailer)
    assert m.links_from([raw], BROKER) == [hrefs[0]]
    spoof = _mail("Someone <x@evil.example>", html)
    assert m.links_from([spoof], BROKER) == []


@pytest.mark.xfail(strict=True, reason="SEC-18: every confirmation-domain link is clicked")
def test_cancel_and_unsubscribe_links_are_not_clicked():
    from vanish.engine.mail import SmtpImapMailer
    html = ('<a href="https://mail.fakeb.example/confirm?t=1">Confirm</a>'
            '<a href="https://mail.fakeb.example/cancel?t=1">I did not ask for this</a>'
            '<a href="https://mail.fakeb.example/unsubscribe?t=1">Unsubscribe</a>')
    raw = _mail("Fake B <no-reply@fakeb.example>", html)
    m = SmtpImapMailer.__new__(SmtpImapMailer)
    assert m.links_from([raw], BROKER) == ["https://mail.fakeb.example/confirm?t=1"]


def _browser_exe() -> str | None:
    if exe := os.environ.get("VANISH_BROWSER_EXECUTABLE"):
        return exe
    found = sorted(glob.glob(os.path.expanduser(
        "~/.cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell")))
    return found[-1] if found else None


class _Hits(BaseHTTPRequestHandler):
    hits: ClassVar[list[str]] = []
    target = ""

    def do_GET(self):
        if self.path == "/r":
            self.send_response(302)
            self.send_header("Location", self.target)
            self.end_headers()
            return
        type(self).hits.append(self.path)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<p>page</p>")

    def log_message(self, *a):
        pass


@pytest.mark.xfail(strict=True, reason="SEC-16: redirects bypass the Playwright route allowlist")
def test_browser_does_not_follow_redirect_off_allowlist(monkeypatch):
    exe = _browser_exe()
    if not exe:
        pytest.xfail("no local Chromium to test with")
    pytest.importorskip("playwright")
    from vanish.engine.browser import BlockedByPolicy, BrowserManager
    from vanish.netpolicy import NetPolicy
    monkeypatch.setenv("VANISH_BROWSER_EXECUTABLE", exe)

    class Evil(_Hits):
        hits: ClassVar[list[str]] = []

    evil = ThreadingHTTPServer(("127.0.0.1", 0), Evil)

    class Broker_(_Hits):
        target = f"http://localhost:{evil.server_address[1]}/exfil"

    good = ThreadingHTTPServer(("127.0.0.1", 0), Broker_)
    for s in (evil, good):
        threading.Thread(target=s.serve_forever, daemon=True).start()

    async def go():
        cfg = cfgmod.Config(min_delay_s=0, max_delay_s=0, max_retries=1, browser_channel=None)
        bm = BrowserManager(NetPolicy(None, allow_loopback=True), headless=True, cfg=cfg)
        try:
            await bm.start()
            ctx = await bm.new_context(["127.0.0.1"])      # localhost is NOT allowed
            page = await ctx.new_page()
            with pytest.raises(BlockedByPolicy):
                await bm.goto(page, f"http://127.0.0.1:{good.server_address[1]}/r",
                              check_challenge=False)
        finally:
            await bm.close()
    try:
        asyncio.run(go())
    finally:
        evil.shutdown()
        good.shutdown()
    # Not asserted: Evil.hits == []. Chromium resolves loopback without the host resolver,
    # so only the full allowlisting-proxy fix (SEC-16 option A) can stop the hop itself here.


# --------------------------------------------------------------------------- minimization


def _values(d) -> str:
    return " ".join(str(v) for v in (d.values() if isinstance(d, dict) else d))


@pytest.mark.parametrize("phone_ok", [False, True])
def test_copy_fields_and_letters_are_minimized(phone_ok):
    from vanish.engine.outbox import compose
    from vanish.submitters import assisted
    from vanish.submitters.base import copy_fields, form_vars
    p = person(mailbox=MB, permissions=Permissions(allow_phone_disclosure=phone_ok))
    every = [f for f in ProfileField if f != F.ID_DOCUMENT]
    li = listing(p, every)
    cf = copy_fields(p, BROKER, [li])
    _subj, body = compose(p, BROKER, [li], None)
    todo = assisted.manual_email_todo(p, BROKER, _subj, body)
    fv = form_vars(p, BROKER, li)["profile"].__dict__
    for blob in (_values(cf), body, _values(todo.copy_fields), _values(fv)):
        for bad in NEVER:
            assert bad not in blob
        if not phone_ok:
            assert PHONE not in blob
    assert (PHONE in _values(cf)) == phone_ok and (PHONE in _values(fv)) == phone_ok
    assert cf["Email for removals"] == MB.address
    # blind (no listing): name only, plus city/state when required; never street/zip/phone
    blind = copy_fields(p, BROKER, [])
    assert "742 Evergreen Terrace" not in _values(blind)
    assert PHONE not in _values(blind) and "62704" not in _values(blind)
    _s, blind_body = compose(p, BROKER, [], None)
    for bad in (*NEVER, PHONE, "742 Evergreen", "62704", "Springfield"):
        assert bad not in blind_body


def test_fields_not_shown_are_not_sent():
    from vanish.engine.outbox import compose
    from vanish.submitters.base import copy_fields
    p = person(mailbox=MB, permissions=Permissions(allow_phone_disclosure=True))
    li = listing(p, [F.FULL_NAME, F.CITY])
    cf = copy_fields(p, BROKER, [li])
    _s, body = compose(p, BROKER, [li], None)
    for blob in (_values(cf), body):
        for bad in (PHONE, "742 Evergreen", "62704", *NEVER):
            assert bad not in blob


# --------------------------------------------------------------------------- scheduler


def test_windows_task_xml_paths_with_spaces_and_xml_metachars():
    from vanish.scheduler import render
    exe = r"C:\Users\Jane Q\AppData\Local\Programs\Vanish & Co <x>\Vanish.exe"
    root = ET.fromstring(render.windows_task_xml([exe, "run", "--scheduled"]).split("\n", 1)[1])
    ns = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
    assert root.find(".//t:Exec/t:Command", ns).text == exe
    assert root.find(".//t:Exec/t:Arguments", ns).text == "run --scheduled"
    py = r"C:\Program Files\Python312\pythonw.exe"
    dev = [py, "-c", "from vanish.cli import app; app()", "run", "--scheduled"]
    root = ET.fromstring(render.windows_task_xml(dev).split("\n", 1)[1])
    assert root.find(".//t:Exec/t:Arguments", ns).text == \
        '-c "from vanish.cli import app; app()" run --scheduled'


@pytest.mark.xfail(strict=True, reason="SEC-24: _win_quote is not CommandLineToArgvW-safe")
def test_windows_arguments_quote_like_list2cmdline():
    from vanish.scheduler import render
    args = ["run", r"C:\dir with space" + "\\", 'say "hi"', ""]
    xml = render.windows_task_xml([r"C:\x\Vanish.exe", *args])
    root = ET.fromstring(xml.split("\n", 1)[1])
    ns = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
    assert root.find(".//t:Exec/t:Arguments", ns).text == subprocess.list2cmdline(args)


# --------------------------------------------------------------------------- wipe


@pytest.fixture
def no_scheduler(monkeypatch):
    from vanish import scheduler
    calls: list[int] = []
    monkeypatch.setattr(scheduler, "remove", lambda: calls.append(1) or "removed")
    return calls


def test_wipe_removes_home_key_and_mailbox_password(store, memkeyring, no_scheduler,
                                                    vanish_env):
    from vanish import cli, crypto, secrets
    p = person(mailbox=MB)
    store.save_profile(p)
    secrets.set_mailbox_password(p.id, MB, "app-password-not-real")
    memkeyring.set_password(crypto.SERVICE, crypto.KEY_NAME, "stand-in-key")
    store.close()
    res = CliRunner().invoke(cli.app, ["wipe", "--yes"])
    assert res.exit_code == 0, res.output
    assert no_scheduler == [1]
    assert not any(v == "app-password-not-real" for v in memkeyring.store.values())
    assert not any(k[0] == crypto.SERVICE for k in memkeyring.store)
    assert not any(Path(vanish_env).rglob("*"))


def test_wipe_never_deletes_a_non_vanish_directory(tmp_path, monkeypatch, no_scheduler):
    from vanish import cli
    danger = tmp_path / "Documents"
    danger.mkdir()
    (danger / "taxes-2025.pdf").write_bytes(b"not vanish data")
    monkeypatch.setenv("VANISH_HOME", str(danger))
    CliRunner().invoke(cli.app, ["wipe", "--yes"])
    assert (danger / "taxes-2025.pdf").exists()


# --------------------------------------------------------------------------- notifications


def test_handoff_and_run_notifications_hold_no_pii(store):
    from vanish.engine import _dev
    from vanish.engine.handoff import QueuedHandoff
    from vanish.engine.runner import run

    class Rec:
        def __init__(self):
            self.calls: list[tuple] = []

        def notify(self, title, body, url=None):
            self.calls.append((title, body, url or ""))

    p = person(label="Mom", mailbox=MB)
    store.save_profile(p)
    rec = Rec()
    reg = _dev.fixture_registry()
    with _dev.fixture_server():
        run(store, reg, [p], scan_only=False, dry_run=True, interactive=False, notifier=rec)
    t = Todo(profile_id=p.id, broker_id="fakeb", kind=TodoKind.ASSISTED_OPT_OUT, title="t",
             body="b", copy_fields={"Full name": "Jane Testperson"})
    asyncio.run(QueuedHandoff(store, rec, p.label).request(t, None))
    assert len(rec.calls) == 2
    text = " ".join(" ".join(c) for c in rec.calls)
    for bad in ("Jane", "Testperson", "Evergreen", "62704", "Springfield", PHONE,
                "jane.testperson@example.com", MB.address, "1980"):
        assert bad not in text
    assert date.today().isoformat() not in text


# --------------------------------------------------------------------------- browser cleanup


@pytest.mark.xfail(strict=True, reason="SEC-26: failed browser launch leaks the Playwright "
                   "driver (Windows CI 'Event loop is closed' warnings)")
def test_failed_browser_launch_stops_playwright(monkeypatch):
    pytest.importorskip("playwright")
    from vanish.engine.browser import BrowserManager
    from vanish.netpolicy import NetPolicy
    monkeypatch.setenv("VANISH_BROWSER_EXECUTABLE", str(Path("/nonexistent") / "chrome"))
    bm = BrowserManager(NetPolicy(None), headless=True,
                        cfg=cfgmod.Config(min_delay_s=0, max_delay_s=0))

    async def go():
        with pytest.raises(Exception):  # noqa: B017 - any launch error
            await bm.start()
        leaked = bm._pw
        if leaked is not None:          # clean up so this xfail itself leaks nothing
            await leaked.stop()
        return leaked
    assert asyncio.run(go()) is None
