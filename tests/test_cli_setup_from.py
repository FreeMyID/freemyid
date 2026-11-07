"""`freemyid setup --from config.yaml`: same validators as the wizard, explicit consent,
passwords never in the file. Fake people only."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from freemyid import setup_config as sc

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "docs" / "examples" / "setup-config.example.yaml"
SCHEMA = ROOT / "schema" / "setup-config.schema.json"


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture(autouse=True)
def _no_real_scheduler(monkeypatch):
    from freemyid import scheduler
    calls: list[str] = []
    monkeypatch.setattr(scheduler, "install", lambda: calls.append("install") or "installed")
    return calls


def _base() -> dict:
    return yaml.safe_load(EXAMPLE.read_text())


def _write(tmp_path: Path, data: dict, name: str = "setup.yaml") -> Path:
    p = tmp_path / name
    p.write_text(yaml.safe_dump(data))
    return p


def _invoke(runner, path: Path, *extra: str, input: str | None = None):
    from freemyid.cli import app
    return runner.invoke(app, ["setup", "--from", str(path), *extra], input=input)


@pytest.fixture
def pw_env(monkeypatch):
    monkeypatch.setenv("FREEMYID_MAILBOX_PASSWORD", "fake-app-password")


def test_example_is_valid_and_matches_published_schema():
    jsonschema = pytest.importorskip("jsonschema")
    data = _base()
    sc.SetupConfig.model_validate(data)
    published = json.loads(SCHEMA.read_text())
    jsonschema.validate(data, published)
    current = sc.SetupConfig.model_json_schema()
    assert published["$defs"] == current["$defs"], "run tools/gen_schema.py"
    assert published["properties"] == current["properties"]


def test_setup_from_yes_saves_profile_and_mailbox_password(store, runner, tmp_path, pw_env,
                                                           memkeyring):
    res = _invoke(runner, _write(tmp_path, _base()), "--yes")
    assert res.exit_code == 0, res.output
    [p] = store.list_profiles()
    assert p.label == "Jane" and p.name.last == "Testperson"
    assert p.consent.attested_by == "Jane Q Testperson" and p.consent.basis.value == "self"
    assert [a.city for a in p.addresses] == ["Springfield", "Shelbyville"]
    assert p.addresses[0].current and p.dob is None and p.age is not None
    assert p.mailbox and p.mailbox.imap_host == "imap.gmail.com"
    assert "fake-app-password" in memkeyring.store.values()
    from freemyid.consent import consent_ok
    assert consent_ok(p, store)[0]
    assert "Signed: Jane Q Testperson" in res.stdout and "Saved Jane" in res.stdout


def test_interactive_confirm_yes_and_no(store, runner, tmp_path, pw_env):
    path = _write(tmp_path, _base())
    res = _invoke(runner, path, input="n\n")
    assert res.exit_code == 2 and "nothing saved" in res.stderr
    assert store.list_profiles() == []
    res = _invoke(runner, path, input="y\n")
    assert res.exit_code == 0, res.output
    assert len(store.list_profiles()) == 1


def test_no_input_and_no_yes_saves_nothing(store, runner, tmp_path, pw_env):
    res = _invoke(runner, _write(tmp_path, _base()), input="")
    assert res.exit_code == 2 and store.list_profiles() == []


def test_check_validates_without_saving(runner, tmp_path, pw_env):
    from freemyid import paths
    res = _invoke(runner, _write(tmp_path, _base()), "--check")
    assert res.exit_code == 0, res.output
    assert "nothing was saved" in res.stdout
    assert not paths.db_path().exists()


@pytest.mark.parametrize(("mutate", "needle"), [
    (lambda d: d["consent"].update(agreed=False), "consent.agreed must be true"),
    (lambda d: d["consent"].pop("signed_name"), "consent.signed_name"),
    (lambda d: d["consent"].update(basis="authorized_agent"), "authorization_file"),
    (lambda d: d.update(version=2), "version"),
    (lambda d: d["person"].update(addresses=[]), "person.addresses"),
    (lambda d: d["person"]["addresses"][0].update(state="Illinois"), "state"),
    (lambda d: d["mailbox"].update(password="hunter2"), "never put the password"),
    (lambda d: d["mailbox"].update(password_file="pw.txt"), "exactly one"),
    (lambda d: d["mailbox"].update(provider="outlook"), "mailbox.provider"),
    (lambda d: d.update(surprise=1), "surprise"),
    (lambda d: d["person"].update(birth_year=2015), "guardian"),
])
def test_invalid_files_exit_2_and_never_echo_values(store, runner, tmp_path, pw_env,
                                                     mutate, needle):
    data = _base()
    mutate(data)
    res = _invoke(runner, _write(tmp_path, data), "--yes")
    assert res.exit_code == 2, res.output
    assert needle in res.stderr
    assert "hunter2" not in res.output and "Evergreen" not in res.output
    assert store.list_profiles() == []


def test_missing_password_env_is_reported(store, runner, tmp_path, monkeypatch):
    monkeypatch.delenv("FREEMYID_MAILBOX_PASSWORD", raising=False)
    res = _invoke(runner, _write(tmp_path, _base()), "--yes")
    assert res.exit_code == 2 and "FREEMYID_MAILBOX_PASSWORD is not set" in res.stderr


def test_password_file_relative_to_yaml(store, runner, tmp_path, memkeyring):
    (tmp_path / "pw.txt").write_text("file-app-password\n")
    data = _base()
    data["mailbox"] = {"provider": "other", "address": "jane.removals@example.com",
                       "password_file": "pw.txt", "imap_host": "imap.example.com",
                       "smtp_host": "smtp.example.com", "smtp_port": 587,
                       "smtp_starttls": True}
    res = _invoke(runner, _write(tmp_path, data), "--yes")
    assert res.exit_code == 0, res.output
    [p] = store.list_profiles()
    assert p.mailbox and (p.mailbox.smtp_port, p.mailbox.smtp_starttls) == (587, True)
    assert p.mailbox.imap_ssl is True
    assert "file-app-password" in memkeyring.store.values()


def test_proton_bridge_needs_fingerprint(store, runner, tmp_path, pw_env):
    data = _base()
    data["mailbox"] = {"provider": "proton_bridge", "address": "jane.removals@example.com",
                       "password_env": "FREEMYID_MAILBOX_PASSWORD"}
    res = _invoke(runner, _write(tmp_path, data), "--yes")
    assert res.exit_code == 2 and "tls_cert_sha256" in res.stderr
    data["mailbox"]["tls_cert_sha256"] = "ab" * 32
    res = _invoke(runner, _write(tmp_path, data), "--yes")
    assert res.exit_code == 0, res.output
    assert store.list_profiles()[0].mailbox.tls_cert_sha256 == "ab" * 32


def test_no_mailbox_and_guardian_for_minor(store, runner, tmp_path):
    data = _base()
    del data["mailbox"]
    data["person"]["birth_year"] = 2015
    data["consent"]["basis"] = "guardian_of_minor"
    data["consent"]["signed_name"] = "John Testperson"
    res = _invoke(runner, _write(tmp_path, data), "--yes")
    assert res.exit_code == 0, res.output
    [p] = store.list_profiles()
    assert p.mailbox is None and p.is_minor
    assert p.consent.basis.value == "guardian_of_minor"


def test_same_label_needs_update(store, runner, tmp_path, pw_env):
    path = _write(tmp_path, _base())
    assert _invoke(runner, path, "--yes").exit_code == 0
    first = store.list_profiles()[0]
    res = _invoke(runner, path, "--yes")
    assert res.exit_code == 2 and "--update" in res.stderr
    data = _base()
    data["person"]["phones"] = []
    res = _invoke(runner, _write(tmp_path, data, "v2.yaml"), "--yes", "--update")
    assert res.exit_code == 0, res.output
    [p] = store.list_profiles()
    assert p.id == first.id and p.phones == []
    assert p.created_at == first.created_at


def test_install_job_only_when_asked(store, runner, tmp_path, pw_env, _no_real_scheduler):
    data = _base()
    data["schedule"]["install_job"] = True
    assert _invoke(runner, _write(tmp_path, data), "--yes").exit_code == 0
    assert _no_real_scheduler == ["install"]


def test_not_yaml_and_missing_file(runner, tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("- just\n- a list\n")
    res = _invoke(runner, bad, "--yes")
    assert res.exit_code == 2 and "mapping" in res.stderr
    res = _invoke(runner, tmp_path / "nope.yaml", "--yes")
    assert res.exit_code == 2 and "cannot read" in res.stderr
