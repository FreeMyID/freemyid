"""Shared fixtures. Every test runs with a throwaway VANISH_HOME and VANISH_TEST_KEY, an
in-memory keyring and outbound network blocked. Fake people only (Jane Q Testperson)."""
from __future__ import annotations

import logging
import socket
from datetime import date
from pathlib import Path

import keyring
import pytest
from keyring.backend import KeyringBackend

FIXTURES = Path(__file__).parent / "fixtures"


class MemoryKeyring(KeyringBackend):
    priority = 1  # type: ignore[assignment]

    def __init__(self) -> None:
        super().__init__()
        self.store: dict[tuple[str, str], str] = {}

    def get_password(self, service, username):
        return self.store.get((service, username))

    def set_password(self, service, username, password):
        self.store[(service, username)] = password

    def delete_password(self, service, username):
        from keyring.errors import PasswordDeleteError
        if (service, username) not in self.store:
            raise PasswordDeleteError("missing")
        del self.store[(service, username)]


_real_connect = socket.socket.connect


def _guarded_connect(self, address):
    host = address[0] if isinstance(address, tuple) else address
    if isinstance(host, str) and host not in ("127.0.0.1", "::1", "localhost"):
        raise RuntimeError(f"network blocked in tests: {host}")
    return _real_connect(self, address)


@pytest.fixture(autouse=True)
def vanish_env(tmp_path, monkeypatch):
    home = tmp_path / "vhome"
    monkeypatch.setenv("VANISH_HOME", str(home))
    monkeypatch.setenv("VANISH_TEST_KEY", "unit-test-key-not-secret")
    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)
    kr = MemoryKeyring()
    old = keyring.get_keyring()
    keyring.set_keyring(kr)
    from vanish import logging_setup
    with logging_setup._lock:
        saved = set(logging_setup._pii)
        logging_setup._pii.clear()
    # cli.main() calls logging_setup.setup(), which attaches a StreamHandler bound to the
    # (CliRunner / capture) stderr of that test. Without this, those handlers leak into later
    # tests, write to closed streams and make setup() a no-op (it is idempotent).
    root = logging.getLogger()
    saved_handlers, saved_level = list(root.handlers), root.level
    yield home
    for h in list(root.handlers):
        if h not in saved_handlers:
            root.removeHandler(h)
            h.close()
    root.setLevel(saved_level)
    keyring.set_keyring(old)
    with logging_setup._lock:
        logging_setup._pii.clear()
        logging_setup._pii.update(saved)


@pytest.fixture
def memkeyring() -> MemoryKeyring:
    return keyring.get_keyring()  # type: ignore[return-value]


@pytest.fixture
def store(vanish_env):
    from vanish.storage import Store
    s = Store()
    yield s
    s.close()


@pytest.fixture
def fake_registry():
    from vanish.registry import load_registry
    return load_registry(FIXTURES / "registry_min.yaml")


def make_profile(**over):
    from vanish.models import Address, Consent, ConsentBasis, PersonName, Profile
    data = {
        "label": "Tester",
        "consent": Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
                           text_version="v1"),
        "name": PersonName(first="Jane", middle="Q", last="Testperson"),
        "addresses": [Address(street="742 Evergreen Terrace", city="Springfield", state="il",
                              zip="62704", current=True)],
        "dob": date(1980, 4, 1),
        "phones": ["217-555-0142"],
        "emails": ["jane.testperson@example.com"],
        "relatives": ["John Testperson"],
    }
    data.update(over)
    return Profile(**data)


@pytest.fixture
def profile():
    return make_profile()
