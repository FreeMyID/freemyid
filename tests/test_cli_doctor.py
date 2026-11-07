"""`freemyid doctor`: each check gives ok/warn/fail plus a fix, never raises. Fake data only."""
from __future__ import annotations

import json
import sys
from datetime import timedelta

import pytest
from typer.testing import CliRunner

from freemyid import doctor
from freemyid.models import MailboxConfig

from .conftest import make_profile


@pytest.fixture(autouse=True)
def _quiet_scheduler(monkeypatch):
    from freemyid import scheduler
    monkeypatch.setattr(scheduler, "status", lambda: "not installed")


def _mb(**over) -> MailboxConfig:
    data = {"address": "removals@example.com", "provider": "other",
            "imap_host": "imap.example.com", "smtp_host": "smtp.example.com",
            "username": "removals@example.com"}
    data.update(over)
    return MailboxConfig(**data)


def _by_id(checks):
    return {c.id: c for c in checks}


def test_all_checks_present_and_well_formed(freemyid_env):
    checks = doctor.run_checks(network=False)
    ids = [c.id for c in checks]
    assert ids == ["python", "home", "secrets", "store", "browser", "scheduler", "mailbox",
                   "registry"]
    for c in checks:
        assert c.status in ("ok", "warn", "fail")
        if c.status != "ok":
            assert c.fix, c


def test_fresh_home_is_not_set_up_and_creates_nothing(freemyid_env):
    from freemyid import paths
    c = _by_id(doctor.run_checks(network=False))
    assert c["store"].status == "warn" and "setup" in c["store"].fix
    assert c["scheduler"].status == "warn" and "schedule install" in c["scheduler"].fix
    assert not paths.db_path().exists()   # doctor never creates the database


def test_store_ok_and_permission_warning(store):
    store.save_profile(make_profile())
    assert _by_id(doctor.run_checks(network=False))["store"].status == "ok"
    store.save_profile(make_profile(label="Kid", is_minor=True))
    c = _by_id(doctor.run_checks(network=False))["store"]
    assert c.status == "warn" and "without valid permission" in c.detail


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions")
def test_home_permissions(freemyid_env):
    from freemyid import paths
    h = paths.home()
    h.chmod(0o755)
    c = doctor.check_home()
    assert c.status == "warn" and "chmod 700" in c.fix
    h.chmod(0o700)
    assert doctor.check_home().status == "ok"


def _no_keychain(monkeypatch):
    from freemyid import crypto, secret_backends
    monkeypatch.setattr(crypto, "_backend_names", lambda kr: ["keyring.backends.fail.Keyring"])
    monkeypatch.setattr(secret_backends, "_interactive", lambda: False)
    monkeypatch.delenv("FREEMYID_PASSPHRASE_FILE", raising=False)
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)


def test_secrets_keychain_ok():
    c = doctor.check_secrets()
    assert (c.status, c.detail) == ("ok", "keyring")


def test_secrets_no_keychain_no_passphrase_source_fails(monkeypatch):
    _no_keychain(monkeypatch)
    c = doctor.check_secrets()
    assert c.status == "fail" and c.detail.startswith("passphrase")
    assert "FREEMYID_PASSPHRASE_FILE" in c.fix


def test_secrets_passphrase_file_ok(monkeypatch, tmp_path):
    _no_keychain(monkeypatch)
    monkeypatch.setenv("FREEMYID_PASSPHRASE_FILE", str(tmp_path / "pp"))
    c = doctor.check_secrets()
    assert c.status == "ok" and "no system keychain" in c.detail


def test_secrets_prompt_only_warns_for_headless(monkeypatch):
    from freemyid import secret_backends
    _no_keychain(monkeypatch)
    monkeypatch.setattr(secret_backends, "_interactive", lambda: True)
    c = doctor.check_secrets()
    assert c.status == "warn" and "FREEMYID_PASSPHRASE_FILE" in c.fix


def test_secrets_locked_keychain_with_data_fails(store, monkeypatch):
    _no_keychain(monkeypatch)
    c = doctor.check_secrets()
    assert c.status == "fail" and "secrets migrate" in c.fix


def test_browser_missing_says_playwright_install(monkeypatch, tmp_path):
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "none"))
    monkeypatch.delenv("FREEMYID_BROWSER_EXECUTABLE", raising=False)
    monkeypatch.setattr(doctor, "system_browser", lambda ch: None)
    c = doctor.check_browser()
    assert c.status == "warn" and "playwright install chromium" in c.fix


def test_browser_found_in_playwright_cache(monkeypatch, tmp_path):
    (tmp_path / "chromium-1234").mkdir()
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))
    monkeypatch.delenv("FREEMYID_BROWSER_EXECUTABLE", raising=False)
    monkeypatch.setattr(doctor, "system_browser", lambda ch: None)
    c = doctor.check_browser()
    assert c.status == "ok" and "chromium-1234" in c.detail


def test_browser_bad_executable_env_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("FREEMYID_BROWSER_EXECUTABLE", str(tmp_path / "nope"))
    assert doctor.check_browser().status == "fail"


def test_scheduler_installed(monkeypatch):
    from freemyid import scheduler
    monkeypatch.setattr(scheduler, "status", lambda: "systemd timer: active")
    assert doctor.check_scheduler().status == "ok"


def test_mailbox_probe_ok_and_failure_without_login():
    p = make_profile(mailbox=_mb())
    seen: list[tuple] = []

    def prober(host, port, tls):
        seen.append((host, port, tls))
    assert doctor.check_mailboxes([p], prober=prober).status == "ok"
    assert seen == [("imap.example.com", 993, True), ("smtp.example.com", 465, True)]
    c = doctor.check_mailboxes([p], prober=lambda h, port, t: "cannot connect (OSError)")
    assert c.status == "fail" and "Tester" in c.detail
    assert "removals@example.com" not in c.detail   # never the address


def test_mailbox_loopback_bridge_is_tcp_only():
    p = make_profile(mailbox=_mb(provider="proton_bridge", imap_host="127.0.0.1",
                                 imap_port=1143, imap_ssl=False, imap_starttls=True,
                                 smtp_host="127.0.0.1", smtp_port=1025, smtp_starttls=True))
    seen: list[tuple] = []
    doctor.check_mailboxes([p], prober=lambda h, port, t: seen.append((h, port, t)))
    assert seen == [("127.0.0.1", 1143, False), ("127.0.0.1", 1025, False)]


def test_mailbox_offline_and_none():
    assert doctor.check_mailboxes([], network=True).status == "warn"
    p = make_profile(mailbox=_mb())
    assert "offline" in doctor.check_mailboxes([p], network=False).detail


def test_real_probe_reports_instead_of_raising():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()                       # nothing listens there now: connection refused
    assert doctor.probe("127.0.0.1", port, True, timeout=0.5).startswith("cannot connect")


def test_registry_age(monkeypatch, fake_registry):
    from freemyid import registry
    monkeypatch.setattr(registry, "load_registry", lambda path=None: fake_registry)
    fresh = doctor.check_registry(today=fake_registry.updated)
    assert fresh.status == "ok"
    old = doctor.check_registry(today=fake_registry.updated + timedelta(days=400))
    assert old.status == "warn" and old.fix


def test_broken_check_is_a_warning_not_a_crash(monkeypatch):
    monkeypatch.setattr(doctor, "check_python", lambda: 1 / 0)
    c = _by_id(doctor.run_checks(network=False))["python"]
    assert c.status == "warn" and "ZeroDivisionError" in c.detail


def test_cli_doctor_json_and_exit_codes(freemyid_env, monkeypatch):
    from freemyid.cli import app
    r = CliRunner().invoke(app, ["doctor", "--offline", "--json"])
    doc = json.loads(r.stdout)
    assert doc["schema"] == "doctor/1" and doc["ok"] is (r.exit_code == 0)
    assert sum(doc["counts"].values()) == len(doc["checks"]) == 8
    monkeypatch.setattr(doctor, "check_python",
                        lambda: doctor.Check("python", "Python", "fail", "too old", "upgrade"))
    r = CliRunner().invoke(app, ["doctor", "--offline"])
    assert r.exit_code == 1 and "FAIL" in r.stdout and "upgrade" in r.stdout
