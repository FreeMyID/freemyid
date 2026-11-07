"""secret_backends.py: keyring (default, unchanged), passphrase (scrypt), systemd-creds,
auto-fallback, mailbox secrets per backend, and `migrate` round-trips with a fake keyring."""
from __future__ import annotations

import base64
import json
import os
import sys

import keyring
import pytest
from keyring.backends import fail

from freemyid import config, crypto, paths, secret_backends
from freemyid.crypto import Cipher
from freemyid.models import MailboxConfig
from freemyid.secrets import delete_mailbox_password, get_mailbox_password, set_mailbox_password
from tests.conftest import make_profile

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes")

PW = "correct horse battery staple"
MB = MailboxConfig(address="removals.testperson@example.com", imap_host="imap.example.com",
                   smtp_host="smtp.example.com", username="removals.testperson@example.com")


@pytest.fixture
def env(freemyid_env, monkeypatch, tmp_path):
    """Real key paths (no test key), cheap scrypt, fresh cache, no TTY."""
    monkeypatch.delenv("FREEMYID_TEST_KEY")
    monkeypatch.delenv("FREEMYID_PASSPHRASE_FILE", raising=False)
    monkeypatch.delenv("FREEMYID_PASSPHRASE", raising=False)
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    monkeypatch.setattr(secret_backends, "SCRYPT_N", 2**14)
    monkeypatch.setattr(secret_backends, "_interactive", lambda: False)
    monkeypatch.setattr(secret_backends, "_noticed", False)
    secret_backends.clear_cache()
    paths.home().mkdir(parents=True, exist_ok=True)
    yield freemyid_env
    secret_backends.clear_cache()


def _pwfile(tmp_path, monkeypatch, pw=PW, mode=0o600, name="pass.txt"):
    f = tmp_path / name
    f.write_text(pw + "\n")
    f.chmod(mode)
    monkeypatch.setenv("FREEMYID_PASSPHRASE_FILE", str(f))
    return f


def _use(name):
    cfg = config.load()
    cfg.secrets_backend = name
    config.save(cfg)


def _wrap():
    return secret_backends.PassphraseBackend.wrap_path()


# ---------------------------------------------------------------- keyring (default)

def test_default_is_keyring_and_unchanged(env, memkeyring):
    assert secret_backends.select().name == "keyring"
    c = Cipher()
    stored = memkeyring.store[(crypto.SERVICE, crypto.KEY_NAME)]
    assert len(base64.b64decode(stored)) == 32
    assert not _wrap().exists()
    assert Cipher().decrypt(c.encrypt(b"x")) == b"x"


def test_existing_keyring_key_is_used_as_is(env, memkeyring):
    """Existing (e.g. Windows Credential Manager) installs: same entry, same blob format."""
    key = os.urandom(32)
    memkeyring.set_password(crypto.SERVICE, crypto.KEY_NAME, base64.b64encode(key).decode())
    blob = Cipher(key).encrypt(b"Jane Q Testperson", b"profiles:1")
    assert Cipher().decrypt(blob, b"profiles:1") == b"Jane Q Testperson"
    assert memkeyring.store[(crypto.SERVICE, crypto.KEY_NAME)] == base64.b64encode(key).decode()


def test_keyring_mailbox_password(env, memkeyring):
    set_mailbox_password("p1", MB, "app-password-not-real")
    assert memkeyring.store[(MB.keyring_service, f"p1:{MB.address}")] == "app-password-not-real"
    assert get_mailbox_password("p1", MB) == "app-password-not-real"
    delete_mailbox_password("p1", MB)
    delete_mailbox_password("p1", MB)   # missing is fine
    assert get_mailbox_password("p1", MB) is None


def test_explicit_keyring_never_falls_back(env):
    keyring.set_keyring(fail.Keyring())
    _use("keyring")
    with pytest.raises(crypto.KeyUnavailable):
        Cipher()
    assert not _wrap().exists()


# ---------------------------------------------------------------- passphrase

@posix_only
def test_passphrase_file_roundtrip(env, tmp_path, monkeypatch, memkeyring):
    _pwfile(tmp_path, monkeypatch)
    _use("passphrase")
    blob = Cipher().encrypt(b"secret")
    assert (crypto.SERVICE, crypto.KEY_NAME) not in memkeyring.store
    assert _wrap().stat().st_mode & 0o777 == 0o600
    doc = json.loads(_wrap().read_text())
    assert doc["kdf"] == "scrypt" and doc["n"] == 2**14
    secret_backends.clear_cache()            # a fresh process re-derives from the file
    assert Cipher().decrypt(blob) == b"secret"


@posix_only
@pytest.mark.parametrize("mode", [0o644, 0o640, 0o604, 0o660])
def test_passphrase_file_must_be_owner_only(env, tmp_path, monkeypatch, mode):
    _pwfile(tmp_path, monkeypatch, mode=mode)
    _use("passphrase")
    with pytest.raises(crypto.KeyUnavailable, match="chmod 600"):
        Cipher()
    assert not _wrap().exists()


@posix_only
def test_passphrase_file_symlink_refused(env, tmp_path, monkeypatch):
    real = _pwfile(tmp_path, monkeypatch)
    link = tmp_path / "link.txt"
    link.symlink_to(real)
    monkeypatch.setenv("FREEMYID_PASSPHRASE_FILE", str(link))
    _use("passphrase")
    with pytest.raises(crypto.KeyUnavailable):
        Cipher()


@posix_only
def test_wrong_passphrase_fails_closed(env, tmp_path, monkeypatch):
    _pwfile(tmp_path, monkeypatch)
    _use("passphrase")
    Cipher()
    before = _wrap().read_bytes()
    secret_backends.clear_cache()
    _pwfile(tmp_path, monkeypatch, pw="not the right passphrase")
    with pytest.raises(crypto.KeyUnavailable, match="wrong passphrase"):
        Cipher()
    assert _wrap().read_bytes() == before     # never replaced with a new key


@posix_only
def test_tampered_scrypt_params_rejected(env, tmp_path, monkeypatch):
    _pwfile(tmp_path, monkeypatch)
    _use("passphrase")
    Cipher()
    doc = json.loads(_wrap().read_text())
    doc["n"] = 2**4
    _wrap().write_text(json.dumps(doc))
    secret_backends.clear_cache()
    with pytest.raises(crypto.KeyUnavailable, match="corrupt"):
        Cipher()


def test_plain_env_var_passphrase_refused(env, monkeypatch):
    monkeypatch.setenv("FREEMYID_PASSPHRASE", PW)
    _use("passphrase")
    with pytest.raises(crypto.KeyUnavailable, match="FREEMYID_PASSPHRASE_FILE") as ei:
        Cipher()
    assert PW not in str(ei.value)


def test_no_source_and_no_tty_fails_closed(env):
    _use("passphrase")
    with pytest.raises(crypto.KeyUnavailable, match="can't ask"):
        Cipher()


def test_interactive_prompt_confirms_new_passphrase(env, monkeypatch):
    calls = []

    def fake_prompt(confirm):
        calls.append(confirm)
        return PW
    monkeypatch.setattr(secret_backends, "_interactive", lambda: True)
    monkeypatch.setattr(secret_backends, "prompt", fake_prompt)
    _use("passphrase")
    Cipher()
    secret_backends.clear_cache()
    Cipher()
    assert calls == [True, False]


def test_short_new_passphrase_refused(env, monkeypatch):
    monkeypatch.setattr(secret_backends, "_interactive", lambda: True)
    monkeypatch.setattr(secret_backends, "prompt", lambda confirm: "short")
    _use("passphrase")
    with pytest.raises(crypto.KeyUnavailable, match="at least"):
        Cipher()


@posix_only
def test_passphrase_mailbox_password_encrypted_in_home(env, tmp_path, monkeypatch, memkeyring):
    _pwfile(tmp_path, monkeypatch)
    _use("passphrase")
    set_mailbox_password("p1", MB, "app-password-not-real")
    assert not memkeyring.store
    raw = secret_backends.PassphraseBackend.secrets_path().read_bytes()
    assert b"app-password-not-real" not in raw and b"testperson" not in raw
    secret_backends.clear_cache()
    assert get_mailbox_password("p1", MB) == "app-password-not-real"
    delete_mailbox_password("p1", MB)
    assert get_mailbox_password("p1", MB) is None


# ---------------------------------------------------------------- systemd-creds

@posix_only
def test_systemd_creds_backend(env, tmp_path, monkeypatch):
    creds = tmp_path / "creds"
    creds.mkdir()
    (creds / "freemyid-passphrase").write_text(PW)
    (creds / "freemyid-passphrase").chmod(0o400)
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(creds))
    _use("systemd-creds")
    blob = Cipher().encrypt(b"secret")
    # Same wrap file as the passphrase backend: an interactive login opens it too.
    monkeypatch.delenv("CREDENTIALS_DIRECTORY")
    secret_backends.clear_cache()
    _pwfile(tmp_path, monkeypatch)
    _use("passphrase")
    assert Cipher().decrypt(blob) == b"secret"


def test_systemd_creds_missing_fails_closed(env):
    _use("systemd-creds")
    with pytest.raises(crypto.KeyUnavailable, match="LoadCredential"):
        Cipher()


@posix_only
def test_systemd_cred_world_readable_refused(env, tmp_path, monkeypatch):
    creds = tmp_path / "creds"
    creds.mkdir()
    (creds / "freemyid-passphrase").write_text(PW)
    (creds / "freemyid-passphrase").chmod(0o444)
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(creds))
    _use("systemd-creds")
    with pytest.raises(crypto.KeyUnavailable):
        Cipher()


# ---------------------------------------------------------------- auto-detect

@posix_only
def test_auto_falls_back_to_passphrase_without_keychain(env, tmp_path, monkeypatch, caplog):
    keyring.set_keyring(fail.Keyring())
    _pwfile(tmp_path, monkeypatch)
    Cipher()
    assert secret_backends.select().name == "passphrase"
    assert _wrap().exists()
    assert "passphrase" in caplog.text and PW not in caplog.text


def test_auto_refuses_new_key_when_keychain_data_exists(env):
    keyring.set_keyring(fail.Keyring())
    paths.db_path().write_bytes(b"")
    with pytest.raises(crypto.KeyUnavailable, match="keychain"):
        Cipher()
    assert not _wrap().exists()


@posix_only
def test_auto_prefers_existing_wrap(env, tmp_path, monkeypatch, memkeyring):
    _pwfile(tmp_path, monkeypatch)
    _use("passphrase")
    Cipher()
    _use(None)
    assert secret_backends.select().name == "passphrase"


# ---------------------------------------------------------------- migration + wipe

def _seed_store_with_mailbox():
    from freemyid.storage import Store
    s = Store()
    p = make_profile(mailbox=MB)
    s.save_profile(p)
    s.close()
    set_mailbox_password(p.id, MB, "app-password-not-real")
    return p


@posix_only
def test_migrate_roundtrip(env, tmp_path, monkeypatch, memkeyring):
    from freemyid.storage import Store
    p = _seed_store_with_mailbox()
    key0 = memkeyring.store[(crypto.SERVICE, crypto.KEY_NAME)]
    _pwfile(tmp_path, monkeypatch)

    r = secret_backends.migrate("passphrase")
    assert (r.from_backend, r.to_backend, r.secrets_moved, r.changed) == (
        "keyring", "passphrase", 1, True)
    assert config.load().secrets_backend == "passphrase"
    assert not memkeyring.store                      # key and password left the keychain
    secret_backends.clear_cache()
    s = Store()                                      # same data key: store opens
    assert s.get_profile(p.id) is not None
    s.close()
    assert get_mailbox_password(p.id, MB) == "app-password-not-real"

    r = secret_backends.migrate("keyring")
    assert (r.from_backend, r.secrets_moved) == ("passphrase", 1)
    assert memkeyring.store[(crypto.SERVICE, crypto.KEY_NAME)] == key0
    assert not _wrap().exists()
    assert not secret_backends.PassphraseBackend.secrets_path().exists()
    s = Store()
    assert s.get_profile(p.id) is not None
    s.close()
    assert get_mailbox_password(p.id, MB) == "app-password-not-real"


@posix_only
def test_migrate_same_backend_is_noop(env, tmp_path, monkeypatch, memkeyring):
    _pwfile(tmp_path, monkeypatch)
    _use("passphrase")
    Cipher()
    r = secret_backends.migrate("systemd-creds")   # shares the wrap: only the setting moves
    assert r.changed and r.secrets_moved == 0
    assert config.load().secrets_backend == "systemd-creds"
    assert secret_backends.migrate("systemd-creds").changed is False


def test_migrate_unknown_backend():
    with pytest.raises(ValueError, match="unknown secrets backend"):
        secret_backends.migrate("plaintext")


@posix_only
def test_migrate_failure_keeps_source(env, tmp_path, monkeypatch, memkeyring):
    _seed_store_with_mailbox()
    before = dict(memkeyring.store)
    _pwfile(tmp_path, monkeypatch, mode=0o644)       # target refuses this file
    with pytest.raises(crypto.KeyUnavailable):
        secret_backends.migrate("passphrase")
    assert memkeyring.store == before
    assert config.load().secrets_backend is None


@posix_only
def test_delete_key_removes_all_backends(env, tmp_path, monkeypatch, memkeyring):
    memkeyring.set_password(crypto.SERVICE, crypto.KEY_NAME, "stand-in")
    _pwfile(tmp_path, monkeypatch)
    _use("passphrase")
    set_mailbox_password("p1", MB, "app-password-not-real")
    crypto.delete_key()
    assert (crypto.SERVICE, crypto.KEY_NAME) not in memkeyring.store
    assert not _wrap().exists()
    assert not secret_backends.PassphraseBackend.secrets_path().exists()


def test_delete_key_without_any_keychain(env):
    keyring.set_keyring(fail.Keyring())
    crypto.delete_key()   # headless wipe must not crash
