"""CLI v0.2: --json on read commands, run --headless, exit codes. Fake people only."""
from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from freemyid import cli_json as cj
from freemyid.models import (
    ConsentBasis,
    ListingState,
    Method,
    Request,
    RequestKind,
    RequestStatus,
    Tier,
    Todo,
    TodoKind,
)

from .conftest import make_profile


@pytest.fixture
def runner():
    return CliRunner()


def _json(res) -> dict:
    assert res.stdout.strip(), res.output
    return json.loads(res.stdout)


def _app():
    from freemyid.cli import app
    return app


def _fake_report(**over):
    from freemyid.engine.runner import RunReport
    r = RunReport(dry_run=True)
    for k, v in over.items():
        setattr(r, k, v)
    return r


@pytest.fixture
def fake_run(monkeypatch):
    """Replace the engine; record its keyword arguments."""
    from freemyid.engine import runner as rmod
    box: dict = {"calls": [], "report": _fake_report()}

    def run(store, reg, people, **kw):
        box["calls"].append({"people": [p.id for p in people], **kw})
        rep = box["report"]
        for p in people:
            rep.labels.setdefault(p.id, p.label)
            rep.per_profile.setdefault(p.id, {ListingState.NOT_FOUND: 2})
            rep.tiers.setdefault(p.id, {Tier.EMAIL: 2})
        return rep
    monkeypatch.setattr(rmod, "run", run)
    return box


# ----------------------------------------------------------------------------- read commands


def test_profile_list_json(store, runner):
    p = make_profile(label="Mom")
    store.save_profile(p)
    doc = _json(runner.invoke(_app(), ["profile", "list", "--json"]))
    assert doc["schema"] == "profiles/1"
    [row] = doc["profiles"]
    assert row == {"id": p.id, "label": "Mom", "state_of_residence": "IL",
                   "consent_basis": "self", "consent_ok": True, "has_mailbox": False,
                   "email_mode": "approve_each", "created_at": p.created_at.isoformat()}
    # no PII beyond the label: no names, streets, phones, emails
    raw = json.dumps(doc)
    for pii in ("Testperson", "Evergreen", "555-0142", "example.com", "1980"):
        assert pii not in raw


def test_status_json_shape_and_skips(store, runner, fake_registry, monkeypatch):
    from freemyid import cli
    monkeypatch.setattr(cli, "_registry", lambda: fake_registry)
    good = make_profile(label="Dad")
    bad = make_profile(label="Kid", is_minor=True)   # SELF consent on a minor: refused
    store.save_profile(good)
    store.save_profile(bad)
    bid = fake_registry.brokers[0].id
    st = store.get_status(good.id, bid).model_copy(update={"state": ListingState.FOUND,
                                                           "tier": Tier.ASSISTED})
    store.save_status(st)
    store.save_todo(Todo(profile_id=good.id, broker_id=bid, kind=TodoKind.OTHER, title="t"))
    res = runner.invoke(_app(), ["status", "--json"])
    assert res.exit_code == 0, res.output
    doc = _json(res)
    assert doc["schema"] == "status/1"
    [prof] = doc["profiles"]
    assert prof["label"] == "Dad" and prof["open_todos"] == 1
    [b] = prof["brokers"]
    assert b["broker_id"] == bid and b["state"] == "found" and b["tier"] == "assisted"
    assert b["broker_name"] == fake_registry.brokers[0].name
    assert set(b) == {"broker_id", "broker_name", "state", "tier", "updated_at",
                      "last_scan_at", "last_submitted_at", "next_check_at", "attempts",
                      "escalation_level"}
    assert [s["label"] for s in doc["skipped"]] == ["Kid"]
    assert "guardian" in doc["skipped"][0]["reason"]


def test_todo_list_json_never_includes_copy_fields_or_body(store, runner):
    p = make_profile()
    store.save_profile(p)
    store.save_todo(Todo(profile_id=p.id, broker_id="spokeo", kind=TodoKind.CAPTCHA,
                         title="Finish on Spokeo", body="secret body",
                         copy_fields={"Name": "Jane Q Testperson"}))
    doc = _json(runner.invoke(_app(), ["todo", "list", "--json"]))
    [t] = doc["todos"]
    assert t["kind"] == "captcha" and t["title"] == "Finish on Spokeo"
    assert t["broker_id"] == "spokeo" and t["label"] == "Tester"
    raw = json.dumps(doc)
    assert "secret body" not in raw and "Jane Q" not in raw


def test_outbox_list_json(store, runner):
    p = make_profile()
    store.save_profile(p)
    r = Request(profile_id=p.id, broker_id="spokeo", kind=RequestKind.OPT_OUT,
                method=Method.EMAIL, status=RequestStatus.QUEUED_FOR_APPROVAL)
    store.save_request(r)
    doc = _json(runner.invoke(_app(), ["outbox", "list", "--json"]))
    assert doc["schema"] == "outbox/1"
    assert doc["requests"][0]["id"] == r.id
    assert doc["requests"][0]["status"] == "queued_for_approval"


def test_registry_show_and_source_json(runner, monkeypatch, fake_registry):
    from freemyid import cli, registry
    monkeypatch.setattr(cli, "_registry", lambda: fake_registry)
    monkeypatch.setattr(registry, "load_registry", lambda path=None: fake_registry)
    doc = _json(runner.invoke(_app(), ["registry", "show", "--json"]))
    assert doc["schema"] == "registry/1" and doc["version"] == fake_registry.version
    assert {b["id"] for b in doc["brokers"]} == {b.id for b in fake_registry.brokers}
    prios = [b["priority"] for b in doc["brokers"]]
    assert prios == sorted(prios, reverse=True)
    src = _json(runner.invoke(_app(), ["registry", "source", "--json"]))
    assert src["schema"] == "registry-source/1"
    assert src["brokers"] == len(fake_registry.brokers)


@pytest.mark.parametrize(("detail", "installed"), [
    ("not installed", False), ("systemd timer: active", True),
    ("Scheduling is not supported on this system.", False)])
def test_schedule_status_json(runner, monkeypatch, detail, installed):
    from freemyid import scheduler
    monkeypatch.setattr(scheduler, "status", lambda: detail)
    doc = _json(runner.invoke(_app(), ["schedule", "status", "--json"]))
    assert doc == {"schema": "schedule/1", "platform": scheduler.platform_name(),
                   "installed": installed, "detail": detail}


def test_report_json(store, runner, monkeypatch, tmp_path):
    from freemyid.wizard import report as rmod
    p = make_profile()
    store.save_profile(p)
    out = tmp_path / "r.html"
    monkeypatch.setattr(rmod, "build_report", lambda s, reg, pid, fmt: out)
    doc = _json(runner.invoke(_app(), ["report", "--json"]))
    assert doc["reports"] == [{"profile_id": p.id, "label": "Tester", "format": "html",
                               "path": str(out)}]


def test_json_errors_go_to_stderr_not_stdout(store, runner):
    store.save_profile(make_profile())
    res = runner.invoke(_app(), ["status", "--json", "--profile", "nomatch"])
    assert res.exit_code == cj.EXIT_USAGE
    assert res.stdout == ""
    assert "No profile" in res.stderr


# ----------------------------------------------------------------------------- run / scan


def test_scan_json_reports_counts(store, runner, fake_run):
    p = make_profile()
    store.save_profile(p)
    res = runner.invoke(_app(), ["scan", "--json"])
    assert res.exit_code == 0, res.output
    doc = _json(res)
    assert doc["schema"] == "run/1" and doc["scan_only"] is True and doc["dry_run"] is True
    assert doc["profiles"][0]["states"] == {"not_found": 2}
    assert doc["profiles"][0]["tiers"] == {"email": 2}
    assert fake_run["calls"][0]["scan_only"] is True


def test_headless_without_setup_exits_4(runner, fake_run):
    res = runner.invoke(_app(), ["run", "--headless", "--dry-run"])
    assert res.exit_code == cj.EXIT_NOT_CONFIGURED
    assert "not configured" in res.stderr and len(res.stderr.strip().splitlines()) == 1
    assert fake_run["calls"] == []


def test_headless_json_failure_document(runner, fake_run):
    res = runner.invoke(_app(), ["run", "--headless", "--dry-run", "--json"])
    assert res.exit_code == 4
    doc = _json(res)
    assert doc["schema"] == "error/1" and doc["exit_code"] == 4


def test_headless_practice_mode_refuses_real_run(store, runner, fake_run):
    store.save_profile(make_profile())
    res = runner.invoke(_app(), ["run", "--headless"])
    assert res.exit_code == cj.EXIT_NOT_CONFIGURED
    assert "practice mode" in res.stderr
    assert fake_run["calls"] == []


def test_headless_scheduled_practice_mode_runs_dry(store, runner, fake_run):
    store.save_profile(make_profile())
    res = runner.invoke(_app(), ["run", "--headless", "--scheduled"])
    assert res.exit_code == 0, res.output
    call = fake_run["calls"][0]
    assert call["dry_run"] is True and call["interactive"] is False
    assert call["only_due"] is True


def test_headless_no_consenting_profile_exits_3(store, runner, fake_run):
    from freemyid.models import Consent
    bad = make_profile(consent=Consent(basis=ConsentBasis.SELF, attested_by="",
                                       text_version="2026-11-c"))
    store.save_profile(bad)
    res = runner.invoke(_app(), ["run", "--headless", "--dry-run"])
    assert res.exit_code == cj.EXIT_NEEDS_HUMAN
    assert "permission" in res.stderr
    assert fake_run["calls"] == []


def test_headless_never_interactive_and_never_prompts(store, runner, fake_run):
    store.save_profile(make_profile())
    res = runner.invoke(_app(), ["run", "--headless", "--dry-run"], input="")
    assert res.exit_code == 0, res.output
    assert fake_run["calls"][0]["interactive"] is False
    assert fake_run["calls"][0]["dry_run"] is True


@pytest.mark.parametrize(("needs", "errors", "code"), [
    (0, 0, 0), (2, 0, 3), (0, 1, 1), (1, 1, 3)])
def test_headless_post_run_exit_codes(store, runner, fake_run, needs, errors, code):
    store.save_profile(make_profile())
    fake_run["report"] = _fake_report(needs_human=needs, errors=errors)
    res = runner.invoke(_app(), ["run", "--headless", "--dry-run", "--json"])
    assert res.exit_code == code
    assert _json(res)["exit_code"] == code


def test_interactive_run_keeps_exit_0_even_with_needs_human(store, runner, fake_run):
    store.save_profile(make_profile())
    fake_run["report"] = _fake_report(needs_human=3)
    res = runner.invoke(_app(), ["run", "--dry-run"])
    assert res.exit_code == 0
    assert fake_run["calls"][0]["interactive"] is True


def test_headless_key_unavailable_exits_4(store, runner, fake_run, monkeypatch):
    from freemyid import cli
    from freemyid.crypto import KeyUnavailable
    store.save_profile(make_profile())

    def boom():
        raise KeyUnavailable("no secure OS keychain available")
    monkeypatch.setattr(cli, "_store", boom)
    res = runner.invoke(_app(), ["run", "--headless", "--dry-run"])
    assert res.exit_code == cj.EXIT_NOT_CONFIGURED
    assert "encryption key" in res.stderr


# ----------------------------------------------------------------------------- secrets


def test_secrets_status_plain_and_json(runner):
    res = runner.invoke(_app(), ["secrets", "status"])
    assert res.exit_code == 0 and res.stdout.strip() == "keyring"
    doc = _json(runner.invoke(_app(), ["secrets", "status", "--json"]))
    assert doc == {"schema": "secrets/1", "backend": "keyring", "configured": None,
                   "usable": True, "keychain_available": True}


def test_secrets_migrate_calls_backend(runner, monkeypatch):
    from freemyid import secret_backends
    seen: list[str] = []

    def migrate(to):
        seen.append(to)
        return secret_backends.MigrateResult("keyring", to, 2, True)
    monkeypatch.setattr(secret_backends, "migrate", migrate)
    res = runner.invoke(_app(), ["secrets", "migrate", "--to", "passphrase"])
    assert res.exit_code == 0 and seen == ["passphrase"]
    assert "Now using passphrase (was keyring); 2 saved password(s) moved." in res.stdout


@pytest.mark.parametrize("exc", ["value", "key"])
def test_secrets_migrate_errors_exit_2(runner, monkeypatch, exc):
    from freemyid import crypto, secret_backends

    def migrate(to):
        raise ValueError("unknown secrets backend 'x'") if exc == "value" else \
            crypto.KeyUnavailable("keychain locked")
    monkeypatch.setattr(secret_backends, "migrate", migrate)
    res = runner.invoke(_app(), ["secrets", "migrate", "--to", "x"])
    assert res.exit_code == 2
    assert ("unknown secrets backend" if exc == "value" else "keychain locked") in res.stderr


def test_secrets_migrate_unknown_backend_real(runner):
    res = runner.invoke(_app(), ["secrets", "migrate", "--to", "floppy"])
    assert res.exit_code == 2 and "unknown secrets backend" in res.stderr
