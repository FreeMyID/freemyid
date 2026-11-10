"""Plain sentences for setup-file mistakes. Fake people only. No network."""
from __future__ import annotations

import socket
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from freemyid.setup_config import MAX_FILE_BYTES, SetupFileError, load


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch, freemyid_env: Path) -> None:
    """Any socket use fails. Runs after the shared fixture that still allows localhost."""
    assert isinstance(freemyid_env, Path)

    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise OSError("network blocked")

    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)


def _base() -> dict:
    return {
        "version": 1,
        "consent": {
            "agreed": True,
            "signed_name": "Jane Q Testperson",
            "basis": "self",
        },
        "person": {
            "name": {"first": "Jane", "middle": "Q", "last": "Testperson"},
            "addresses": [{"street": "100 Example Road", "city": "Springfield",
                           "state": "IL", "current": True}],
        },
    }


def _write(path: Path, data: object) -> Path:
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def _problems(tmp_path: Path, data: dict) -> list[str]:
    with pytest.raises(SetupFileError) as caught:
        load(_write(tmp_path / "setup.yaml", data))
    return list(caught.value.problems)


def test_socket_use_is_blocked() -> None:
    with pytest.raises(OSError, match="network blocked"):
        socket.create_connection(("example.test", 80))
    with pytest.raises(OSError, match="network blocked"):
        socket.socket().connect(("example.test", 80))


def test_valid_file_still_loads(tmp_path: Path) -> None:
    cfg = load(_write(tmp_path / "setup.yaml", _base()))
    assert cfg.person.name.first == "Jane"
    assert cfg.person.name.last == "Testperson"
    assert cfg.person.addresses[0].city == "Springfield"
    assert cfg.person.addresses[0].state == "IL"


def test_missing_field_says_add_it(tmp_path: Path) -> None:
    data = _base()
    del data["person"]["name"]["first"]
    problems = _problems(tmp_path, data)
    assert problems == ["person.name.first: is missing; add it"]
    assert "Testperson" not in problems[0]
    assert "Springfield" not in problems[0]


def test_unknown_key_suggests_a_close_setting(tmp_path: Path) -> None:
    data = _base()
    data["person"]["name"]["frist"] = "NOT-A-REAL-NAME"
    data["person"]["addresses"][0]["streat"] = "742 Evergreen Terrace"
    data["mailbox"] = {
        "provider": "gmail",
        "address": "jane.removals@example.com",
        "password_env": "FREEMYID_TEST_MAIL_PASSWORD",
        "passwrod": "fake-inline-password-marker",
    }
    problems = _problems(tmp_path, data)
    assert sorted(problems) == sorted([
        "person.name.frist: is not a setting Free My ID knows; did you mean first?",
        "person.addresses.0.streat: is not a setting Free My ID knows; did you mean street?",
        ("mailbox.passwrod: is not a setting Free My ID knows; "
         "did you mean password_env or password_file?"),
    ])
    text = "\n".join(problems)
    assert "NOT-A-REAL-NAME" not in text
    assert "742 Evergreen Terrace" not in text
    assert "fake-inline-password-marker" not in text
    assert "jane.removals@example.com" not in text


def test_unknown_key_without_a_close_name_makes_no_guess(tmp_path: Path) -> None:
    data = _base()
    data["surprise"] = 1
    data["FREEMYID_PASSPHRASE"] = "fake-passphrase-marker"
    data["mailbox"] = {
        "provider": "gmail",
        "address": "jane.removals@example.com",
        "password_env": "FREEMYID_TEST_MAIL_PASSWORD",
        "api_token": "fake-token-marker",
    }
    data["removal_scope"] = "phone"
    problems = _problems(tmp_path, data)
    assert sorted(problems) == sorted([
        "surprise: is not a setting Free My ID knows",
        "FREEMYID_PASSPHRASE: is not a setting Free My ID knows",
        "mailbox.api_token: is not a setting Free My ID knows",
        "removal_scope: is not a setting Free My ID knows",
    ])
    text = "\n".join(problems)
    assert "did you mean" not in text
    assert "fake-passphrase-marker" not in text
    assert "fake-token-marker" not in text
    assert "phone" not in text


def _version_text(data: dict) -> None:
    data["version"] = "one"


def _weekday_text(data: dict) -> None:
    data["schedule"] = {"weekday": "Monday"}


def _permission_text(data: dict) -> None:
    data["permissions"] = {"allow_id_upload": "sometimes"}


def _name_number(data: dict) -> None:
    data["person"]["name"]["first"] = 42


def _age_text(data: dict) -> None:
    data["person"]["age"] = "sixty"


@pytest.mark.parametrize(
    ("mutate", "expected", "hidden"),
    [
        (_version_text, "version: should be a number", "one"),
        (_weekday_text, "schedule.weekday: should be a number", "Monday"),
        (_permission_text, "permissions.allow_id_upload: should be yes or no", "sometimes"),
        (_name_number, "person.name.first: should be text", "42"),
        (_age_text, "person.age: should be a number", "sixty"),
    ],
)
def test_wrong_type_says_number_yes_or_no_or_text(
    mutate: Callable[[dict], None], expected: str, hidden: str, tmp_path: Path,
) -> None:
    data = _base()
    mutate(data)
    problems = _problems(tmp_path, data)
    assert problems == [expected]
    assert hidden not in problems[0]


def test_model_value_errors_stay_word_for_word(tmp_path: Path) -> None:
    inline = _base()
    inline["mailbox"] = {
        "provider": "gmail",
        "address": "jane.removals@example.com",
        "password": "fake-inline-password-marker",
    }
    problems = _problems(tmp_path, inline)
    assert problems == [
        "mailbox: never put the password in the file; use password_env or password_file",
    ]
    assert "fake-inline-password-marker" not in problems[0]
    assert "jane.removals@example.com" not in problems[0]

    both = _base()
    both["mailbox"] = {
        "provider": "gmail",
        "address": "jane.removals@example.com",
        "password_env": "FREEMYID_TEST_MAIL_PASSWORD",
        "password_file": "fake-password.txt",
    }
    assert _problems(tmp_path, both) == [
        "mailbox: give exactly one of password_env or password_file",
    ]


def test_personal_values_are_not_repeated(tmp_path: Path) -> None:
    data = _base()
    data["consent"]["signed_name"] = ["Jane Q Testperson"]
    data["person"]["addresses"] = "742 Evergreen Terrace"
    data["person"]["phones"] = [2175550142]
    data["person"]["emails"] = ["jane.testperson@example.com"]
    problems = _problems(tmp_path, data)
    text = "\n".join(problems)
    assert "consent.signed_name: should be text" in problems
    assert "person.addresses: should be a list" in problems
    assert "person.phones.0: should be text" in problems
    for hidden in ("Jane Q Testperson", "742 Evergreen Terrace", "Springfield", "Testperson",
                   "2175550142", "jane.testperson@example.com", "100 Example Road"):
        assert hidden not in text

    whole = _base()
    whole["person"] = "Jane Q Testperson"
    problems = _problems(tmp_path, whole)
    assert problems == ["person: should be a group of settings"]
    assert "Jane Q Testperson" not in problems[0]


def test_ranges_choices_and_patterns_stay_plain(tmp_path: Path) -> None:
    data = _base()
    data["version"] = 2
    data["email_mode"] = "send_everything"
    data["schedule"] = {"weekday": 7}
    data["person"]["name"]["first"] = ""
    data["person"]["birth_year"] = 1800
    data["person"]["addresses"] = [
        {"city": "Springfield", "state": "IL"} for _ in range(5)
    ]
    data["mailbox"] = {
        "provider": "outlook",
        "address": "jane.removals@example.com",
        "password_env": "FREEMYID_TEST_MAIL_PASSWORD",
        "tls_cert_sha256": "not-a-fingerprint",
    }
    problems = _problems(tmp_path, data)
    assert sorted(problems) == sorted([
        "version: should be 1",
        "email_mode: should be approve_each or auto",
        "schedule.weekday: should be a number from 0 to 6",
        "person.name.first: cannot be blank",
        "person.birth_year: should be a number at least 1900",
        "person.addresses: should have at most 4 items",
        "mailbox.provider: should be gmail, yahoo, icloud, proton_bridge, or other",
        "mailbox.tls_cert_sha256: should be the certificate fingerprint you approved",
    ])
    text = "\n".join(problems)
    for hidden in ("send_everything", "not-a-fingerprint", "outlook", "Springfield", "1800"):
        assert hidden not in text

    state = _base()
    state["person"]["addresses"][0]["state"] = "Illinois"
    problems = _problems(tmp_path, state)
    assert problems == ["person.addresses.0.state: should be a 2-letter state, such as IL"]
    assert "Illinois" not in problems[0]

    empty = _base()
    empty["person"]["addresses"] = []
    assert _problems(tmp_path, empty) == ["person.addresses: should have at least 1 item"]


def test_yaml_level_messages_stay(tmp_path: Path) -> None:
    listing = tmp_path / "notes.yaml"
    listing.write_text("- just\n- a list\n", encoding="utf-8")
    with pytest.raises(SetupFileError) as caught:
        load(listing)
    assert caught.value.problems == [f"{listing.name} should be a YAML mapping (key: value)"]

    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(SetupFileError) as caught:
        load(empty)
    assert caught.value.problems == [f"{empty.name} should be a YAML mapping (key: value)"]

    broken = tmp_path / "broken.yaml"
    broken.write_text("a: [\n", encoding="utf-8")
    with pytest.raises(SetupFileError) as caught:
        load(broken)
    assert caught.value.problems == [f"{broken.name} is not valid YAML"]

    missing = tmp_path / "missing.yaml"
    with pytest.raises(SetupFileError) as caught:
        load(missing)
    assert caught.value.problems == [f"cannot read {missing}: FileNotFoundError"]

    huge = tmp_path / "huge.yaml"
    huge.write_bytes(b"x" * (MAX_FILE_BYTES + 1))
    with pytest.raises(SetupFileError) as caught:
        load(huge)
    assert caught.value.problems == [f"{huge.name} is too large to be a setup file"]
