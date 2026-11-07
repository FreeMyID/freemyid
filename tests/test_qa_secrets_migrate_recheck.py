"""qa-security re-check of the SEC-70..76 fixes (3856b8d..3d868b0): resumable migrate,
ownership-checked wipe, atomic config.save, the secrets.enc lock and the O_EXCL fallback.

The kill-point resume test is adopted from the automation-engineer's ad-hoc draft. Fake data
only, cheap scrypt, in-memory keyring (conftest). Strict xfails mark the new findings."""
from __future__ import annotations

import base64
import errno
import os
import threading
import time

import pytest

from freemyid import config, crypto, paths
from freemyid import secret_backends as sb
from freemyid.secrets import get_mailbox_password
from tests import test_qa_secret_backends_review as review
from tests.test_qa_secret_backends_review import APP_PW, KEY_ID, MB, _seed

pytestmark = pytest.mark.posix_only
env = review.env   # cheap scrypt, passphrase file, no FREEMYID_TEST_KEY


class Die(BaseException):
    """Stands in for SIGKILL / power loss: not an Exception, and no rollback runs."""


def _die(*a, **kw):
    raise Die


def _close_store():
    from freemyid.storage import Store
    Store().close()   # opens with the selected backend's key and checks key_check


def _kill_migrate(monkeypatch, direction: str, kill: str) -> None:
    """Run migrate(direction) and kill it at `kill`, with the rollback disabled."""
    with monkeypatch.context() as m:
        m.setattr(sb, "_rollback", lambda *a, **k: None)
        tgt = sb.PassphraseBackend if direction == "passphrase" else sb.KeyringBackend
        if kill == "set_secret":
            m.setattr(tgt, "set_secret", _die)
        elif kill == "config_save":
            m.setattr(config, "save", _die)
        elif kill == "cleanup":
            m.setattr(sb, "_cleanup_source", _die)
        else:   # the marker write that flips phase "copy" -> "cleanup"
            real = sb._write_pending

            def wp(d):
                if d["phase"] == "cleanup":
                    raise Die
                real(d)
            m.setattr(sb, "_write_pending", wp)
        with pytest.raises(Die):
            sb.migrate(direction)
    sb.clear_cache()


# --- SEC-70/71: a migrate killed at any step stays readable and a re-run finishes it -------

@pytest.mark.parametrize("kill", ["set_secret", "config_save", "write_pending_cleanup", "cleanup"])
@pytest.mark.parametrize("direction", ["passphrase", "keyring"])
def test_qa_sec71_sigkill_at_each_step_resumes(env, memkeyring, monkeypatch, kill, direction):
    p = _seed()
    if direction == "keyring":   # start from a passphrase folder
        sb.migrate("passphrase")
        sb.clear_cache()
    _kill_migrate(monkeypatch, direction, kill)

    assert sb._pending_path().exists()
    assert get_mailbox_password(p.id, MB) == APP_PW   # readable while the marker is there
    _close_store()

    r = sb.migrate(direction)
    sb.clear_cache()
    assert r.changed
    assert not sb._pending_path().exists()
    assert config.load().secrets_backend == direction
    assert get_mailbox_password(p.id, MB) == APP_PW
    if direction == "passphrase":   # passwords leave; the shared key stays (SEC-82)
        assert set(memkeyring.store) == {KEY_ID}
    else:
        assert not sb.PassphraseBackend.wrap_path().exists()
        assert not sb.PassphraseBackend.secrets_path().exists()
    _close_store()


def test_qa_sec71_pending_to_other_target_is_refused(env, memkeyring, monkeypatch):
    _seed()
    _kill_migrate(monkeypatch, "passphrase", "set_secret")
    with pytest.raises(crypto.KeyUnavailable, match="didn't finish"):
        sb.migrate("systemd-creds")


def test_qa_sec71_rollback_restores_auto_config(env, memkeyring, monkeypatch):
    p = _seed()
    assert config.load().secrets_backend is None
    with monkeypatch.context() as m:
        m.setattr(sb.PassphraseBackend, "set_secret", _die)
        with pytest.raises(Die):
            sb.migrate("passphrase")
    sb.clear_cache()
    assert config.load().secrets_backend is None     # None stays None, not "keyring"
    assert not sb._pending_path().exists()
    assert not sb.PassphraseBackend.wrap_path().exists()
    assert KEY_ID in memkeyring.store
    assert get_mailbox_password(p.id, MB) == APP_PW


def test_qa_sec83_failed_resume_restores_original_config(env, memkeyring, monkeypatch):
    """Killed after config.save but before the phase flip (config already says passphrase,
    marker says copy). A resume that then fails must still put config back to `orig`."""
    p = _seed()
    _kill_migrate(monkeypatch, "passphrase", "write_pending_cleanup")
    assert config.load().secrets_backend == "passphrase"

    def boom(*a, **k):
        raise crypto.KeyUnavailable("simulated failure on resume")
    with monkeypatch.context() as m:
        m.setattr(sb.PassphraseBackend, "set_secret", boom)
        with pytest.raises(crypto.KeyUnavailable):
            sb.migrate("passphrase")
    sb.clear_cache()
    assert config.load().secrets_backend is None
    assert get_mailbox_password(p.id, MB) == APP_PW


# --- SEC-72: wipe and migrate never remove another folder's keychain key ------------------

def _other_home(tmp_path, monkeypatch, name: str):
    h = tmp_path / name
    monkeypatch.setenv("FREEMYID_HOME", str(h))
    h.mkdir(parents=True, exist_ok=True)
    sb.clear_cache()
    return h


def test_qa_sec72_wipe_keeps_another_folders_keychain_key(env, memkeyring, tmp_path, monkeypatch):
    other = base64.b64encode(os.urandom(32)).decode()
    memkeyring.set_password(*KEY_ID, other)          # the main install's key
    cfg = config.load()
    cfg.secrets_backend = "passphrase"               # this folder: passphrase, own key
    config.save(cfg)
    _seed()
    assert sb.PassphraseBackend.wrap_path().exists()

    crypto.delete_key()
    assert memkeyring.store[KEY_ID] == other
    assert not sb.PassphraseBackend.wrap_path().exists()
    assert not sb.PassphraseBackend.secrets_path().exists()


def test_qa_sec72_wipe_without_proof_keeps_keychain_key(env, memkeyring):
    other = base64.b64encode(os.urandom(32)).decode()
    memkeyring.set_password(*KEY_ID, other)          # no DB, no wrap here: nothing proves it
    crypto.delete_key()
    assert memkeyring.store[KEY_ID] == other


def test_qa_sec72_wipe_removes_own_and_damaged_keychain_key(env, memkeyring):
    _seed()                                          # keyring folder: the key is ours
    assert KEY_ID in memkeyring.store
    crypto.delete_key()
    assert KEY_ID not in memkeyring.store
    memkeyring.set_password(*KEY_ID, "not-a-key")    # damaged entry: no folder can use it
    crypto.delete_key()
    assert KEY_ID not in memkeyring.store


def test_qa_sec72_wipe_keeps_key_when_marker_damaged(env, memkeyring):
    _seed()
    sb._pending_path().write_text("{not json")
    with pytest.raises(crypto.KeyUnavailable, match="damaged"):
        sb.select()
    crypto.delete_key()                              # wipe still works and clears the marker
    assert not sb._pending_path().exists()


def test_qa_sec82_migrate_off_keyring_keeps_key_shared_by_another_folder(
        env, memkeyring, tmp_path, monkeypatch):
    """Two keyring folders always share the one global entry (the second folder's first run
    reuses the existing key). Moving folder B to a passphrase must not delete that entry,
    or folder A's data can never be opened again."""
    from freemyid.storage import Store
    home_a = paths.home()
    pa = _seed()                                     # folder A: keyring (auto)
    _other_home(tmp_path, monkeypatch, "vhome_b")
    _seed()                                          # folder B: keyring, same key
    sb.migrate("passphrase")

    monkeypatch.setenv("FREEMYID_HOME", str(home_a))
    sb.clear_cache()
    s = Store()
    try:
        assert s.get_profile(pa.id) is not None
    finally:
        s.close()


# --- SEC-75: no hard links on this filesystem -> O_EXCL create ----------------------------

@pytest.mark.parametrize("err", [errno.EPERM, errno.ENOTSUP, errno.EXDEV])
def test_qa_sec75_exclusive_write_without_hard_links(tmp_path, monkeypatch, err):
    def no_link(src, dst, *a, **k):
        raise OSError(err, os.strerror(err))
    monkeypatch.setattr(os, "link", no_link)
    target = tmp_path / "datakey.wrapped.json"
    sb._atomic_write(target, b"first", exclusive=True)
    assert target.read_bytes() == b"first"
    assert target.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        sb._atomic_write(target, b"second", exclusive=True)
    assert target.read_bytes() == b"first"
    assert [p.name for p in tmp_path.iterdir()] == [target.name]   # no temp files left


def test_qa_sec75_passphrase_first_run_without_hard_links(env, memkeyring, monkeypatch):
    def no_link(src, dst, *a, **k):
        raise OSError(errno.EPERM, "Operation not permitted")
    monkeypatch.setattr(os, "link", no_link)
    cfg = config.load()
    cfg.secrets_backend = "passphrase"
    config.save(cfg)
    key = sb.PassphraseBackend().load_data_key()
    sb.clear_cache()
    assert sb.PassphraseBackend().load_data_key(create=False) == key


# --- SEC-74: two writers of secrets.enc serialise on the lock -----------------------------

def _passphrase_folder():
    cfg = config.load()
    cfg.secrets_backend = "passphrase"
    config.save(cfg)
    b = sb.PassphraseBackend()
    b.load_data_key()
    return b


def test_qa_sec74_second_writer_waits_for_the_lock(env, memkeyring):
    b = _passphrase_folder()
    done = threading.Event()

    def writer():
        sb.PassphraseBackend().set_secret("svc", "late", "v2")
        done.set()
    with b._lock():                       # another process is mid read-modify-write
        t = threading.Thread(target=writer, daemon=True)
        t.start()
        time.sleep(0.3)
        assert not done.is_set()          # flock is per open file: the thread blocks
    t.join(5)
    assert done.is_set()
    assert sb.PassphraseBackend().get_secret("svc", "late") == "v2"


def test_qa_sec74_concurrent_writers_lose_no_update(env, memkeyring, monkeypatch):
    b = _passphrase_folder()
    real_read = sb.PassphraseBackend._read_secrets

    def slow_read(self):                  # widen the read-modify-write window
        data = real_read(self)
        time.sleep(0.02)
        return data
    monkeypatch.setattr(sb.PassphraseBackend, "_read_secrets", slow_read)
    users = [f"user{i}" for i in range(8)]
    threads = [threading.Thread(target=sb.PassphraseBackend().set_secret,
                                args=("svc", u, f"pw-{u}")) for u in users]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    got = dict.fromkeys(users)
    for u in users:
        got[u] = b.get_secret("svc", u)
    assert got == {u: f"pw-{u}" for u in users}
    assert not [p for p in paths.home().iterdir() if p.name.endswith(".tmp")]


# --- SEC-76e: ConfigError names the file and the fields, never the values -----------------

MARK = "Jane-Q-Testperson-4242"


@pytest.mark.parametrize("body,field", [
    (f"min_delay_s: {MARK}\n", "min_delay_s"),
    (f"secrets_backend: {MARK}\nmax_retries: {MARK}x\n", "max_retries"),
    (f"extra_allowed_hosts:\n  - [{MARK}]\n", "extra_allowed_hosts.0"),
])
def test_qa_sec76_config_error_names_fields_not_values(freemyid_env, body, field):
    p = paths.config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)
    with pytest.raises(config.ConfigError) as ei:
        config.load()
    msg = str(ei.value)
    assert field in msg and str(p) in msg
    assert MARK not in msg
    assert isinstance(ei.value, ValueError)


@pytest.mark.parametrize("body", [f"a: [{MARK}\n", f"- {MARK}\n", f"\xff{MARK}".encode("latin-1")])
def test_qa_sec76_damaged_config_message_has_no_content(freemyid_env, body):
    p = paths.config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(body, bytes):
        p.write_bytes(body)
    else:
        p.write_text(body)
    with pytest.raises(config.ConfigError) as ei:
        config.load()
    assert MARK not in str(ei.value)


def test_qa_sec71_config_save_is_atomic_and_private(freemyid_env, monkeypatch):
    cfg = config.load()
    cfg.secrets_backend = "keyring"
    config.save(cfg)
    p = paths.config_path()
    assert p.stat().st_mode & 0o777 == 0o600
    before = p.read_bytes()
    cfg.secrets_backend = "passphrase"
    with monkeypatch.context() as m:
        m.setattr(os, "replace", _die)             # killed before the rename
        with pytest.raises(Die):
            config.save(cfg)
    assert p.read_bytes() == before                # old config intact, not truncated
    assert [x.name for x in p.parent.iterdir() if x.name.startswith(".config.")] == []


# --- SEC-76a/c: a refused env passphrase is dropped; the key cache follows the wrap file ---

def test_qa_sec76_refused_env_passphrase_is_removed(env, monkeypatch):
    monkeypatch.setenv("FREEMYID_PASSPHRASE", "never-in-env-please")
    with pytest.raises(crypto.KeyUnavailable):
        sb.PassphraseBackend()._passphrase(confirm=False)
    assert "FREEMYID_PASSPHRASE" not in os.environ


def test_qa_sec76_cache_drops_key_of_recreated_wrap(env, memkeyring):
    b = _passphrase_folder()
    k1 = b.load_data_key()
    wp = sb.PassphraseBackend.wrap_path()
    wp.unlink()                                       # another process wiped and re-created
    k2 = sb.PassphraseBackend().load_data_key()
    assert k1 != k2
    assert sb.PassphraseBackend().load_data_key(create=False) == k2


def test_qa_sec84_store_refuses_when_keychain_read_fails(env, memkeyring, monkeypatch):
    import keyring.errors
    other = base64.b64encode(os.urandom(32)).decode()
    memkeyring.set_password(*KEY_ID, other)          # another folder's key

    def flaky_get(service, user):                    # e.g. a locked or denied read
        raise keyring.errors.KeyringError("read denied")
    monkeypatch.setattr(memkeyring, "get_password", flaky_get)
    try:
        sb.KeyringBackend().store_data_key(os.urandom(32))
    except crypto.KeyUnavailable:
        pass
    assert memkeyring.store[KEY_ID] == other
