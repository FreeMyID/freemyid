"""WO-605: one keychain entry per data folder; wiping a second folder never destroys the
main folder's key. Fake in-memory keyring only (conftest MemoryKeyring), never the real
system keychain; FREEMYID_TEST_KEY is unset only inside these tests. Fake people only."""
from __future__ import annotations

import base64
import os
import re
from pathlib import Path

import keyring
import pytest
from cryptography.exceptions import InvalidTag

from freemyid import config, crypto, doctor, paths, secret_backends
from freemyid.crypto import Cipher
from tests.conftest import MemoryKeyring, make_profile

posix_only = pytest.mark.posix_only   # skip logic: tests/conftest.py
# Read at import, before any fixture replaces it (the conftest may stand the test home in
# for the default folder).
_REAL_DEFAULT_HOME = getattr(crypto, "default_home", None)


@pytest.fixture
def homes(freemyid_env, tmp_path, monkeypatch):
    """`main` stands in for the platform default folder (legacy entry name); `second` is
    any other FREEMYID_HOME (a test folder, a relative's folder, support)."""
    assert isinstance(keyring.get_keyring(), MemoryKeyring)   # never the real keychain
    monkeypatch.delenv("FREEMYID_TEST_KEY")
    monkeypatch.delenv("FREEMYID_PASSPHRASE_FILE", raising=False)
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    monkeypatch.setattr(secret_backends, "SCRYPT_N", 2**14)
    monkeypatch.setattr(secret_backends, "_interactive", lambda: False)
    monkeypatch.setattr(secret_backends, "_noticed", False)
    main, second = tmp_path / "main", tmp_path / "second"
    # raising=False: the same tests run against the pre-WO-605 code (no default_home there)
    monkeypatch.setattr(crypto, "default_home", lambda: main, raising=False)
    secret_backends.clear_cache()
    yield main, second
    secret_backends.clear_cache()


def _use(monkeypatch, home: Path) -> None:
    monkeypatch.setenv("FREEMYID_HOME", str(home))
    secret_backends.clear_cache()
    paths.home()


def _seed() -> str:
    """Save one fake person in the current folder (creates the key and DB key_check)."""
    from freemyid.storage import Store
    s = Store()
    p = make_profile()
    s.save_profile(p)
    s.close()
    return p.id


def _opens(pid: str) -> bool:
    from freemyid.storage import Store
    s = Store()
    try:
        return s.get_profile(pid) is not None
    finally:
        s.close()


def _key_entries(kr: MemoryKeyring) -> dict[str, str]:
    return {user: v for (svc, user), v in kr.store.items() if svc == crypto.SERVICE}


def _set_legacy(kr: MemoryKeyring, key: bytes) -> None:
    kr.set_password(crypto.SERVICE, crypto.KEY_NAME, base64.b64encode(key).decode())


def _old_style_folder(home: Path, key: bytes) -> str:
    """A non-default folder made before WO-605: its DB key_check is made with `key`, the
    shared legacy entry's key, and it has no entry of its own."""
    from freemyid.storage import Store
    home.mkdir(parents=True, exist_ok=True)
    s = Store(path=home / "freemyid.db", cipher=Cipher(key))
    p = make_profile()
    s.save_profile(p)
    s.close()
    return p.id


# ---------------------------------------------------------------- naming

def test_entry_names(homes):
    main, second = homes
    assert crypto.folder_key_name(main) == crypto.KEY_NAME == "db-key-v1"
    name = crypto.folder_key_name(second)
    assert re.fullmatch(r"db-key-v1:[0-9a-f]{16}", name)
    assert crypto.folder_key_name(second / "." ) == name          # resolved path
    assert crypto.folder_key_name(main.parent / "third") != name
    assert str(second) not in name and "second" not in name       # no path text in the name


def test_default_home_mirrors_paths_home(tmp_path, monkeypatch):
    """crypto.default_home() must stay the folder paths.home() picks without FREEMYID_HOME
    (paths.py is the source of truth; crypto mirrors it without creating the folder)."""
    if _REAL_DEFAULT_HOME is None:
        pytest.fail("crypto.default_home is missing (pre-WO-605 code)")
    fake_user = tmp_path / "user"
    fake_user.mkdir()
    monkeypatch.delenv("FREEMYID_HOME")
    monkeypatch.setenv("HOME", str(fake_user))
    monkeypatch.setenv("USERPROFILE", str(fake_user))
    monkeypatch.setenv("APPDATA", str(fake_user / "AppData" / "Roaming"))
    monkeypatch.setattr(crypto, "default_home", _REAL_DEFAULT_HOME)
    assert crypto.default_home().resolve() == paths.home().resolve()
    assert crypto.is_default_home(paths.home())
    assert crypto.folder_key_name() == crypto.KEY_NAME


# ---------------------------------------------------------------- criterion 1

def test_two_homes_two_entries(homes, monkeypatch, memkeyring):
    main, second = homes
    _use(monkeypatch, main)
    a = _seed()
    _use(monkeypatch, second)
    b = _seed()
    entries = _key_entries(memkeyring)
    assert set(entries) == {crypto.KEY_NAME, crypto.folder_key_name(second)}
    assert entries[crypto.KEY_NAME] != entries[crypto.folder_key_name(second)]
    assert _opens(b)
    _use(monkeypatch, main)
    assert _opens(a)


def test_new_folder_never_adopts_existing_key(homes, monkeypatch, memkeyring):
    _, second = homes
    k1 = os.urandom(32)
    _set_legacy(memkeyring, k1)
    _use(monkeypatch, second)
    blob = Cipher(k1).encrypt(b"x")
    with pytest.raises(InvalidTag):            # a different key: K1's blob does not open
        Cipher().decrypt(blob)
    assert memkeyring.get_password(crypto.SERVICE, crypto.KEY_NAME) == \
        base64.b64encode(k1).decode()


def test_default_home_legacy_entry_unchanged(homes, monkeypatch, memkeyring):
    """Existing installs (e.g. Windows Credential Manager): same entry, same key, nothing
    added or moved."""
    main, _ = homes
    k = os.urandom(32)
    _set_legacy(memkeyring, k)
    _use(monkeypatch, main)
    pid = _seed()
    assert _key_entries(memkeyring) == {crypto.KEY_NAME: base64.b64encode(k).decode()}
    assert _opens(pid)
    assert secret_backends.KeyringBackend().entry_status() == "own"


# ---------------------------------------------------------------- criterion 2 + 5 (Goal)

def _goal_sequence(monkeypatch, main: Path, second: Path) -> str:
    """WO-605 Goal: the real folder uses K1, a second folder starts, `wipe` runs on the
    second folder, then the real folder is opened again."""
    _use(monkeypatch, main)
    pid = _seed()
    _use(monkeypatch, second)
    _seed()
    crypto.delete_key()                     # the key part of `freemyid wipe`
    _use(monkeypatch, main)
    return pid


def test_goal_sequence_wipe_second_keeps_main_decryptable(homes, monkeypatch, memkeyring):
    main, second = homes
    pid = _goal_sequence(monkeypatch, main, second)
    assert _opens(pid)


@pytest.mark.xfail(strict=True, reason="pre-WO-605 naming: every folder shares db-key-v1, so "
                   "the second folder adopts K1 and its wipe deletes it")
def test_goal_sequence_with_old_shared_naming_loses_main_key(homes, monkeypatch, memkeyring):
    """The old behaviour, reproduced by forcing the old (global) entry name."""
    main, second = homes
    monkeypatch.setattr(crypto, "folder_key_name", lambda home=None: crypto.KEY_NAME)
    pid = _goal_sequence(monkeypatch, main, second)
    assert _opens(pid)


def test_wipe_deletes_only_own_entry(homes, monkeypatch, memkeyring):
    main, second = homes
    _use(monkeypatch, main)
    _seed()
    _use(monkeypatch, second)
    _seed()
    own = crypto.folder_key_name(second)
    crypto.delete_key()
    assert set(_key_entries(memkeyring)) == {crypto.KEY_NAME}
    assert own not in _key_entries(memkeyring)


def test_wipe_default_deletes_legacy_when_key_check_matches(homes, monkeypatch, memkeyring):
    main, _ = homes
    _use(monkeypatch, main)
    _seed()
    crypto.delete_key()
    assert crypto.KEY_NAME not in _key_entries(memkeyring)


def test_wipe_default_keeps_legacy_that_is_not_its_key(homes, monkeypatch, memkeyring):
    main, _ = homes
    _old_style_folder(main, os.urandom(32))   # DB key_check from some other key
    k = os.urandom(32)
    _set_legacy(memkeyring, k)
    _use(monkeypatch, main)
    crypto.delete_key()
    assert _key_entries(memkeyring) == {crypto.KEY_NAME: base64.b64encode(k).decode()}


def test_wipe_old_style_second_folder_never_deletes_shared_entry(homes, monkeypatch,
                                                                 memkeyring):
    main, second = homes
    k1 = os.urandom(32)
    _set_legacy(memkeyring, k1)
    main_pid = _old_style_folder(main, k1)
    _old_style_folder(second, k1)            # shares K1, provably (same key_check key)
    _use(monkeypatch, second)
    crypto.delete_key()
    assert crypto.KEY_NAME in _key_entries(memkeyring)
    _use(monkeypatch, main)
    assert _opens(main_pid)


# ---------------------------------------------------------------- existing non-default folders

def test_old_style_second_folder_doctor_warns_then_migrate_gives_own_entry(
        homes, monkeypatch, memkeyring):
    _, second = homes
    k1 = os.urandom(32)
    _set_legacy(memkeyring, k1)
    pid = _old_style_folder(second, k1)
    _use(monkeypatch, second)
    assert secret_backends.KeyringBackend().entry_status() == "shared"   # not opened yet
    c = doctor.check_secrets()
    assert c.status == "warn"
    assert "secrets migrate --to keyring" in c.fix and "--to passphrase" in c.fix
    assert set(_key_entries(memkeyring)) == {crypto.KEY_NAME}   # doctor is read-only

    r = secret_backends.migrate("keyring")                   # the per-folder rename
    assert r.changed and "own entry" in r.notice
    entries = _key_entries(memkeyring)
    b64 = base64.b64encode(k1).decode()
    assert entries == {crypto.KEY_NAME: b64, crypto.folder_key_name(second): b64}
    assert secret_backends.KeyringBackend().entry_status() == "own"
    assert doctor.check_secrets().status == "ok"
    assert _opens(pid)


def test_old_style_second_folder_gets_own_entry_on_first_use(homes, monkeypatch,
                                                             memkeyring):
    """WO-605 review F1 (owner decision: auto-copy): the first open copies the proven
    shared key into the folder's own entry; the shared entry is left exactly as it was."""
    _, second = homes
    k1 = os.urandom(32)
    _set_legacy(memkeyring, k1)
    pid = _old_style_folder(second, k1)
    _use(monkeypatch, second)
    assert _opens(pid)
    b64 = base64.b64encode(k1).decode()
    assert _key_entries(memkeyring) == {crypto.KEY_NAME: b64,
                                        crypto.folder_key_name(second): b64}
    assert secret_backends.KeyringBackend().entry_status() == "own"
    assert doctor.check_secrets().status == "ok"


@posix_only
def test_migrate_old_style_second_folder_to_passphrase_leaves_shared_entry(
        homes, monkeypatch, memkeyring, tmp_path):
    _, second = homes
    k1 = os.urandom(32)
    _set_legacy(memkeyring, k1)
    pid = _old_style_folder(second, k1)
    _use(monkeypatch, second)
    f = tmp_path / "pass.txt"
    f.write_text("correct horse battery staple\n")
    f.chmod(0o600)
    monkeypatch.setenv("FREEMYID_PASSPHRASE_FILE", str(f))
    r = secret_backends.migrate("passphrase", remove_keychain_key=True)
    # Reading the key gave the folder its own entry (F1); the move removes that copy (it
    # is this folder's alone) and the shared entry stays for the main folder.
    assert r.changed and r.notice == ""
    assert set(_key_entries(memkeyring)) == {crypto.KEY_NAME}
    secret_backends.clear_cache()
    assert _opens(pid)


@posix_only
def test_migrate_second_folder_to_passphrase_removes_its_own_entry(homes, monkeypatch,
                                                                   memkeyring, tmp_path):
    main, second = homes
    _use(monkeypatch, main)
    _seed()
    _use(monkeypatch, second)
    pid = _seed()
    f = tmp_path / "pass.txt"
    f.write_text("correct horse battery staple\n")
    f.chmod(0o600)
    monkeypatch.setenv("FREEMYID_PASSPHRASE_FILE", str(f))
    r = secret_backends.migrate("passphrase")
    assert r.changed and r.notice == ""
    assert set(_key_entries(memkeyring)) == {crypto.KEY_NAME}   # main's key untouched
    secret_backends.clear_cache()
    assert _opens(pid)


# ---------------------------------------------------------------- criterion 3: fail closed

@pytest.mark.parametrize("which", ["main", "second"])
def test_missing_key_fails_closed_without_new_key(homes, monkeypatch, memkeyring, which):
    main, second = homes
    home = main if which == "main" else second
    _use(monkeypatch, home)
    _seed()
    name = crypto.folder_key_name(home)
    memkeyring.delete_password(crypto.SERVICE, name)
    before = dict(memkeyring.store)
    with pytest.raises(crypto.KeyMismatch) as ei:
        Cipher()
    msg = str(ei.value)
    assert "passphrase" in msg and "secrets migrate" in msg and "Nothing was deleted" in msg
    assert memkeyring.store == before                       # no new key over the data
    assert secret_backends.KeyringBackend().entry_status() == "lost"
    c = doctor.check_secrets()
    assert c.status == "fail" and "secrets migrate" in c.fix


def test_wrong_key_fails_closed_and_is_left_alone(homes, monkeypatch, memkeyring):
    _, second = homes
    _use(monkeypatch, second)
    _seed()
    name = crypto.folder_key_name(second)
    other = base64.b64encode(os.urandom(32)).decode()
    memkeyring.set_password(crypto.SERVICE, name, other)
    with pytest.raises(crypto.KeyMismatch) as ei:
        Cipher()
    assert other not in str(ei.value)                       # never a key in a message
    assert memkeyring.get_password(crypto.SERVICE, name) == other
    crypto.delete_key()                                     # wipe can't prove it: kept
    assert memkeyring.get_password(crypto.SERVICE, name) == other


def test_cli_store_open_reports_recovery(homes, monkeypatch, memkeyring):
    _, second = homes
    _use(monkeypatch, second)
    _seed()
    memkeyring.delete_password(crypto.SERVICE, crypto.folder_key_name(second))
    from freemyid.storage import Store
    with pytest.raises(crypto.KeyUnavailable, match="secrets migrate"):
        Store()


@posix_only
def test_passphrase_backend_never_makes_new_key_over_data(homes, monkeypatch, memkeyring,
                                                          tmp_path):
    _, second = homes
    _use(monkeypatch, second)
    _seed()                                   # keyring-backed data
    cfg = config.load()
    cfg.secrets_backend = "passphrase"
    config.save(cfg)
    f = tmp_path / "pass.txt"
    f.write_text("correct horse battery staple\n")
    f.chmod(0o600)
    monkeypatch.setenv("FREEMYID_PASSPHRASE_FILE", str(f))
    with pytest.raises(crypto.KeyMismatch):
        Cipher()
    assert not secret_backends.PassphraseBackend.wrap_path().exists()


def test_doctor_ok_for_own_entry(homes, monkeypatch, memkeyring):
    _, second = homes
    _use(monkeypatch, second)
    _seed()
    assert secret_backends.KeyringBackend().entry_status() == "own"
    assert doctor.check_secrets().status == "ok"


def test_stale_own_entry_falls_back_to_proven_shared_entry(homes, monkeypatch, memkeyring):
    """An old-style folder restored from backup after this path got an entry of its own:
    the shared key that its key_check proves still opens it; the stale entry is kept."""
    _, second = homes
    k1 = os.urandom(32)
    _set_legacy(memkeyring, k1)
    pid = _old_style_folder(second, k1)
    stale = base64.b64encode(os.urandom(32)).decode()
    memkeyring.set_password(crypto.SERVICE, crypto.folder_key_name(second), stale)
    _use(monkeypatch, second)
    assert _opens(pid)
    assert secret_backends.KeyringBackend().entry_status() == "shared"
    crypto.delete_key()
    assert memkeyring.get_password(crypto.SERVICE, crypto.folder_key_name(second)) == stale
    assert crypto.KEY_NAME in _key_entries(memkeyring)
