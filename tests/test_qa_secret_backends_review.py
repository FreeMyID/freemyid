"""qa-security review of the pluggable secrets backend (9a81313, f60625a, 0703216): SEC-70..73.

Strict xfails: each one XPASSes (and fails the run) once its src fix lands; then drop the
marker. Fake data only, cheap scrypt, in-memory keyring (conftest)."""
from __future__ import annotations

import base64
import os
import threading

import pytest

from freemyid import config, crypto, paths, secret_backends
from freemyid.crypto import Cipher
from freemyid.models import MailboxConfig
from freemyid.secrets import get_mailbox_password, set_mailbox_password
from tests.conftest import make_profile

pytestmark = pytest.mark.posix_only

PW = "correct horse battery staple"
APP_PW = "app-password-not-real"
MB = MailboxConfig(address="removals.testperson@example.com", imap_host="imap.example.com",
                   smtp_host="smtp.example.com", username="removals.testperson@example.com")


@pytest.fixture
def env(freemyid_env, monkeypatch, tmp_path):
    monkeypatch.delenv("FREEMYID_TEST_KEY")
    monkeypatch.delenv("FREEMYID_PASSPHRASE", raising=False)
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    monkeypatch.setattr(secret_backends, "SCRYPT_N", 2**14)
    monkeypatch.setattr(secret_backends, "_interactive", lambda: False)
    monkeypatch.setattr(secret_backends, "_noticed", False)
    secret_backends.clear_cache()
    paths.home().mkdir(parents=True, exist_ok=True)
    f = tmp_path / "pass.txt"
    f.write_text(PW + "\n")
    f.chmod(0o600)
    monkeypatch.setenv("FREEMYID_PASSPHRASE_FILE", str(f))
    yield freemyid_env
    secret_backends.clear_cache()


def _seed():
    from freemyid.storage import Store
    s = Store()
    p = make_profile(mailbox=MB)
    s.save_profile(p)
    s.close()
    set_mailbox_password(p.id, MB, APP_PW)
    return p


KEY_ID = (crypto.SERVICE, crypto.KEY_NAME)


# --- SEC-70: the post-write check in migrate() reads the in-process cache, not the disk ------

@pytest.mark.xfail(strict=True, reason="SEC-70: migrate() verifies the wrap via _key_cache, "
                   "so a bad wrap on disk passes and the keychain key is deleted")
def test_qa_sec70_migrate_verifies_wrap_on_disk(env, memkeyring, monkeypatch):
    _seed()
    real = secret_backends._atomic_write

    def bad_wrap(path, data, *, exclusive=False):
        if path.name == secret_backends.WRAP_FILE:   # wrap lands on disk damaged
            data = data.replace(b'"wrapped": "', b'"wrapped": "AAAA')
        real(path, data, exclusive=exclusive)
    monkeypatch.setattr(secret_backends, "_atomic_write", bad_wrap)

    try:
        secret_backends.migrate("passphrase")
    except crypto.KeyUnavailable:
        pass
    # Either migrate refused, or the key it left behind really opens from disk.
    if KEY_ID not in memkeyring.store:
        secret_backends.clear_cache()
        secret_backends.PassphraseBackend().load_data_key(create=False)
    assert KEY_ID in memkeyring.store


# --- SEC-71: a migrate() killed half-way strands the mailbox password --------------------

@pytest.mark.parametrize("kill_at", ["config-save", "secret-copy"])
@pytest.mark.xfail(strict=True, reason="SEC-71: killed migrate leaves passwords in the old "
                   "backend while auto/config already point at the new one; re-run is a no-op")
def test_qa_sec71_killed_migrate_is_recoverable(env, memkeyring, monkeypatch, kill_at):
    p = _seed()
    if kill_at == "config-save":
        target, name = config, "save"
    else:
        target, name = secret_backends.PassphraseBackend, "set_secret"
    real = getattr(target, name)

    def killed(*a, **kw):
        raise KeyboardInterrupt   # stands in for SIGKILL / power loss: not an Exception
    monkeypatch.setattr(target, name, killed)
    with pytest.raises(KeyboardInterrupt):
        secret_backends.migrate("passphrase")
    monkeypatch.setattr(target, name, real)
    secret_backends.clear_cache()

    # After the crash the password must still be reachable, or a re-run must finish the move.
    if get_mailbox_password(p.id, MB) != APP_PW:
        secret_backends.migrate("passphrase")
        secret_backends.clear_cache()
    assert get_mailbox_password(p.id, MB) == APP_PW


# --- SEC-72: KeyringBackend.store_data_key overwrites a different key ----------------------

def test_qa_sec72_keyring_store_refuses_different_key(env, memkeyring):
    other = base64.b64encode(os.urandom(32)).decode()
    memkeyring.set_password(*KEY_ID, other)      # e.g. the main install's keychain key
    cfg = config.load()
    cfg.secrets_backend = "passphrase"           # this data folder uses a passphrase
    config.save(cfg)
    Cipher()
    with pytest.raises(crypto.KeyUnavailable):
        secret_backends.migrate("keyring")
    assert memkeyring.store[KEY_ID] == other


# --- SEC-73: a FIFO at FREEMYID_PASSPHRASE_FILE blocks forever in open() --------------------

@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs mkfifo")
def test_qa_sec73_fifo_passphrase_file_does_not_hang(tmp_path):
    fifo = tmp_path / "pass.fifo"
    os.mkfifo(fifo, 0o600)
    box: dict[str, object] = {}

    def run():
        try:
            secret_backends._read_secret_file(fifo)
        except crypto.KeyUnavailable as e:
            box["err"] = e
    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(2)
    hung = t.is_alive()
    if hung:   # unblock the reader so the thread ends
        fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
        os.close(fd)
        t.join(5)
    assert not hung and "err" in box


def test_qa_secrets_never_in_env_or_logs(env, memkeyring, caplog):
    """Passphrase, data key and mailbox password never reach logs or os.environ."""
    caplog.set_level("DEBUG")
    _seed()
    secret_backends.migrate("passphrase")
    secret_backends.clear_cache()
    key = secret_backends.PassphraseBackend().load_data_key(create=False)
    secret_backends.migrate("keyring")
    text = caplog.text
    for s in (PW, APP_PW, base64.b64encode(key).decode()):
        assert s not in text
        assert all(s not in v for v in os.environ.values())
