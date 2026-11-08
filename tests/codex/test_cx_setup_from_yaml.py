"""CLI boundary checks for the documented setup YAML schema; fake values only."""
from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from freemyid import paths
from freemyid.cli import app


def _base() -> dict:
    return {
        "version": 1,
        "consent": {
            "agreed": True,
            "signed_name": "Pat Testperson",
            "basis": "self",
        },
        "person": {
            "name": {"first": "Pat", "middle": "Q", "last": "Testperson"},
            "addresses": [{"city": "Springfield", "state": "IL", "current": True}],
        },
    }


def _write(path: Path, data: object) -> Path:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _invoke(runner: CliRunner, path: Path):
    return runner.invoke(app, ["setup", "--from", str(path), "--check"])


@pytest.mark.parametrize(
    "case",
    ["all-person-and-settings-fields", "password-file-reference", "proton-fingerprint",
     "authorized-agent-file"],
)
def test_cli_accepts_documented_schema_fields_without_saving(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CliRunner()
    home = tmp_path / "freemyid-home"
    monkeypatch.setenv("FREEMYID_HOME", str(home))
    monkeypatch.setenv("FREEMYID_TEST_MAIL_PASSWORD", "fake-mail-password-value")
    data = _base()

    if case == "all-person-and-settings-fields":
        data["person"].update({
            "label": "Pat", "nicknames": ["Patty"], "previous_names": ["Pat Q Example"],
            "age": 64, "phones": ["217-555-0142"],
            "emails": ["pat.testperson@example.test"], "relatives": ["Alex Testperson"],
        })
        data["person"]["name"].update({"suffix": "Jr."})
        data["person"]["addresses"][0].update({"street": "100 Example Road", "zip": "62704"})
        data["person"]["addresses"].append({"city": "Shelbyville", "state": "IL"})
        data["permissions"] = {
            "allow_id_upload": True,
            "allow_account_creation": True,
            "allow_phone_disclosure": True,
        }
        data["mailbox"] = {
            "provider": "other", "address": "pat.mailbox@example.test",
            "username": "pat-login", "password_env": "FREEMYID_TEST_MAIL_PASSWORD",
            "imap_host": "imap.example.test", "imap_port": 993, "imap_ssl": True,
            "imap_starttls": False, "smtp_host": "smtp.example.test", "smtp_port": 587,
            "smtp_starttls": True,
        }
        data["email_mode"] = "auto"
        data["schedule"] = {
            "weekly_recheck": False, "weekday": 2, "hour": 18, "install_job": True,
        }
    elif case == "password-file-reference":
        (tmp_path / "fake-password.txt").write_text("another-fake-password\n", encoding="utf-8")
        data["mailbox"] = {
            "provider": "other", "address": "pat.mailbox@example.test",
            "password_file": "fake-password.txt", "imap_host": "imap.example.test",
            "smtp_host": "smtp.example.test",
        }
    elif case == "proton-fingerprint":
        data["mailbox"] = {
            "provider": "proton_bridge", "address": "pat.mailbox@example.test",
            "password_env": "FREEMYID_TEST_MAIL_PASSWORD", "tls_cert_sha256": "ab" * 32,
        }
    else:
        fake_auth = tmp_path / "fake-authorization.pdf"
        fake_auth.write_bytes(b"%PDF-1.4 fake authorization fixture\n")
        data["consent"].update({
            "basis": "authorized_agent", "authorization_file": fake_auth.name,
        })

    result = _invoke(runner, _write(tmp_path / "setup.yaml", data))

    assert result.exit_code == 0, result.output
    assert "Check only" in result.output and "nothing was saved" in result.output
    assert not paths.db_path().exists()
    assert "fake-mail-password-value" not in result.output
    assert "another-fake-password" not in result.output


def _bad_version(data: dict) -> None:
    data["version"] = "one"


def _missing_name(data: dict) -> None:
    data["person"]["name"].pop("first")


def _too_many_addresses(data: dict) -> None:
    data["person"]["addresses"] = [
        {"city": "Springfield", "state": "IL"} for _ in range(5)
    ]


def _bad_permission_type(data: dict) -> None:
    data["permissions"] = {"allow_id_upload": "sometimes"}


def _bad_email_mode(data: dict) -> None:
    data["email_mode"] = "send_everything"


def _bad_schedule_range(data: dict) -> None:
    data["schedule"] = {"weekday": 7}


def _inline_password(data: dict) -> None:
    data["mailbox"] = {
        "provider": "gmail", "address": "pat.mailbox@example.test",
        "password": "fake-inline-password-marker",
    }


def _unknown_mailbox_secret(data: dict) -> None:
    data["mailbox"] = {
        "provider": "gmail", "address": "pat.mailbox@example.test",
        "password_env": "FREEMYID_TEST_MAIL_PASSWORD", "api_token": "fake-token-marker",
    }


def _root_passphrase(data: dict) -> None:
    data["FREEMYID_PASSPHRASE"] = "fake-passphrase-marker"


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (_bad_version, "version"),
        (_missing_name, "person.name.first"),
        (_too_many_addresses, "addresses"),
        (_bad_permission_type, "allow_id_upload"),
        (_bad_email_mode, "email_mode"),
        (_bad_schedule_range, "weekday"),
        (_inline_password, "never put the password"),
        (_unknown_mailbox_secret, "api_token"),
        (_root_passphrase, "FREEMYID_PASSPHRASE"),
    ],
    ids=["version-type", "required-name", "address-limit", "permission-type", "email-mode",
         "schedule-range", "inline-password", "mailbox-token", "root-passphrase"],
)
def test_invalid_shapes_and_inline_secrets_exit_two_without_echo(
    mutate: Callable[[dict], None], message: str, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CliRunner()
    monkeypatch.setenv("FREEMYID_HOME", str(tmp_path / "freemyid-home"))
    data = deepcopy(_base())
    mutate(data)
    result = _invoke(runner, _write(tmp_path / "invalid.yaml", data))

    assert result.exit_code == 2, result.output
    assert message in result.output
    assert "fake-inline-password-marker" not in result.output
    assert "fake-token-marker" not in result.output
    assert "fake-passphrase-marker" not in result.output
    assert not paths.db_path().exists()
