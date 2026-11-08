"""v0.1.3 wizard/installer fixes: calm Bridge copy, honest password hint, uninstall closes app."""
from __future__ import annotations

from pathlib import Path

from freemyid.wizard import draft as dr
from freemyid.wizard import ui

ROOT = Path(__file__).resolve().parents[1]


def test_unreachable_message_is_calm_and_has_no_exception_name():
    for host in ("127.0.0.1", "imap.example.org"):
        m = dr.unreachable_message(host)
        assert "Error" not in m and "Exception" not in m and "(" not in m
    assert "Proton Mail Bridge" in dr.unreachable_message("127.0.0.1")


def test_check_mailbox_refused_connection_is_calm():
    d = dr.Draft()
    mb = {"provider": "other", "address": "a@example.org", "imap_host": "127.0.0.1",
          "imap_port": 1, "imap_ssl": True, "imap_starttls": False, "smtp_host": "127.0.0.1",
          "smtp_port": 1, "smtp_starttls": False, "username": "a@example.org"}
    mb["tls_cert_sha256"] = "ab" * 32
    ok, msg, _status = dr.check_mailbox(mb, "pw")
    assert not ok and "Error" not in msg
    assert d.saved_password is False


def _hint(d: dr.Draft) -> str:
    return ui._mailbox_body(d)


def test_password_wording_only_when_saved():
    d = dr.Draft()
    assert "A password is saved" not in _hint(d)
    d.password = "typed-but-unsaved"
    html = _hint(d)
    assert "A password is saved" not in html and "not saved yet" in html
    d.saved_password = True
    assert "A password is saved" in _hint(d)


def test_uninstaller_closes_running_app_first():
    iss = (ROOT / "packaging" / "windows" / "freemyid.iss").read_text()
    assert "taskkill.exe" in iss and "FreeMyID.exe" in iss
    assert iss.index("CloseRunningApp;") < iss.index("wipe --yes")
    assert "DisableReadyPage" not in iss


def test_installer_explains_first_start_wait():
    """Every wait has a reason: the finish page warns that the first launch is slow (unverified
    on Windows; read from the .iss only)."""
    iss = (ROOT / "packaging" / "windows" / "freemyid.iss").read_text()
    assert "[Messages]" in iss and "FinishedLabel=" in iss
    assert "15 seconds" in iss and "That is normal" in iss
    assert iss.index("[Messages]") < iss.index("[Files]")


def test_finish_step_timeline_is_honest():
    from freemyid.wizard import ui
    from freemyid.wizard.draft import Draft
    html = ui._screen_body("finish", Draft())
    for w in ("Right after you finish", "Over the next weeks", "that one site only"):
        assert w in html
