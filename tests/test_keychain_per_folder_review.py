"""qa-security review of WO-605 (per-folder keychain entries). Fake in-memory keyring only
(conftest MemoryKeyring), never the real system keychain. Fake people only.

Strict xfails mark findings that are still open on integrate/crypto-folder-key: each one
flips to XPASS (and fails the suite) once fixed, so the marker must then be removed."""
from __future__ import annotations

import base64
import os
from pathlib import Path

import keyring
import pytest

from freemyid import crypto, paths, secret_backends
from freemyid.crypto import Cipher
from tests.conftest import MemoryKeyring, make_profile

posix_only = pytest.mark.posix_only
windows_only = pytest.mark.windows_only


@pytest.fixture
def homes(freemyid_env, tmp_path, monkeypatch):
    assert isinstance(keyring.get_keyring(), MemoryKeyring)   # never the real keychain
    monkeypatch.delenv("FREEMYID_TEST_KEY")
    monkeypatch.delenv("FREEMYID_PASSPHRASE_FILE", raising=False)
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    monkeypatch.setattr(secret_backends, "SCRYPT_N", 2**14)
    monkeypatch.setattr(secret_backends, "_interactive", lambda: False)
    monkeypatch.setattr(secret_backends, "_noticed", False)
    main, second = tmp_path / "main", tmp_path / "second"
    monkeypatch.setattr(crypto, "default_home", lambda: main)
    secret_backends.clear_cache()
    yield main, second
    secret_backends.clear_cache()


def _use(monkeypatch, home: Path) -> None:
    monkeypatch.setenv("FREEMYID_HOME", str(home))
    secret_backends.clear_cache()
    paths.home()


def _opens(pid: str) -> bool:
    from freemyid.storage import Store
    s = Store()
    try:
        return s.get_profile(pid) is not None
    finally:
        s.close()


def _set_legacy(kr: MemoryKeyring, key: bytes) -> None:
    kr.set_password(crypto.SERVICE, crypto.KEY_NAME, base64.b64encode(key).decode())


def _old_style_folder(home: Path, key: bytes) -> str:
    from freemyid.storage import Store
    home.mkdir(parents=True, exist_ok=True)
    s = Store(path=home / "freemyid.db", cipher=Cipher(key))
    p = make_profile()
    s.save_profile(p)
    s.close()
    return p.id


# ---------------------------------------------------------------- finding 1 (MED)

@pytest.mark.xfail(strict=True, reason="WO-605 review F1: an old-style non-default folder is "
                   "never given its own entry automatically, so wiping the default folder "
                   "still deletes the only copy of its key (the reverse of the Goal sequence)")
def test_f1_wipe_default_keeps_old_style_second_folder_readable(homes, monkeypatch,
                                                                memkeyring):
    main, second = homes
    k1 = os.urandom(32)
    _set_legacy(memkeyring, k1)
    _old_style_folder(main, k1)
    second_pid = _old_style_folder(second, k1)
    _use(monkeypatch, second)
    assert _opens(second_pid)          # the folder is used after the upgrade (no doctor run)
    _use(monkeypatch, main)
    crypto.delete_key()                # `freemyid wipe` on the main folder
    _use(monkeypatch, second)
    assert _opens(second_pid)


# ---------------------------------------------------------------- finding 2 (LOW-MED)

@pytest.mark.xfail(strict=True, reason="WO-605 review F2: an unreadable DB counts as "
                   "has_data with key_check None, and _keyring_shared_legacy_key then hands "
                   "out the shared key with no proof")
def test_f2_unreadable_db_never_adopts_shared_key(homes, monkeypatch, memkeyring):
    _, second = homes
    k1 = os.urandom(32)
    _set_legacy(memkeyring, k1)
    _use(monkeypatch, second)
    (second / "freemyid.db").write_bytes(b"not a sqlite file, or one locked by a writer")
    try:
        got = crypto._keyring_get_or_create_key(create=True)
    except crypto.KeyUnavailable:
        return                          # fail closed: fine
    assert got != k1, "a new folder adopted another folder's key without key_check proof"


# ---------------------------------------------------------------- finding 3 (LOW)

@pytest.mark.xfail(strict=True, reason="WO-605 review F3: the doctor-recommended "
                   "`secrets migrate --to keyring` fails when this path already has a stale "
                   "own entry (store_data_key refuses a different key)")
def test_f3_migrate_to_keyring_with_stale_own_entry(homes, monkeypatch, memkeyring):
    _, second = homes
    k1 = os.urandom(32)
    _set_legacy(memkeyring, k1)
    pid = _old_style_folder(second, k1)
    stale = base64.b64encode(os.urandom(32)).decode()
    memkeyring.set_password(crypto.SERVICE, crypto.folder_key_name(second), stale)
    _use(monkeypatch, second)
    assert secret_backends.KeyringBackend().entry_status() == "shared"
    secret_backends.migrate("keyring")
    assert secret_backends.KeyringBackend().entry_status() == "own"
    assert _opens(pid)


# ---------------------------------------------------------------- path normalisation coverage

def test_name_stable_for_trailing_separator_and_dot_segments(homes):
    _, second = homes
    second.mkdir()
    name = crypto.folder_key_name(second)
    assert crypto.folder_key_name(Path(str(second) + os.sep)) == name
    assert crypto.folder_key_name(second / "sub" / "..") == name
    assert crypto.folder_key_name(Path(os.path.relpath(second))) == name


@posix_only
def test_name_stable_through_symlink(homes, tmp_path):
    _, second = homes
    second.mkdir()
    link = tmp_path / "link-to-second"
    link.symlink_to(second, target_is_directory=True)
    assert crypto.folder_key_name(link) == crypto.folder_key_name(second)


@posix_only
def test_symlink_to_default_counts_as_default(homes, tmp_path):
    main, _ = homes
    main.mkdir()
    link = tmp_path / "alias"
    link.symlink_to(main, target_is_directory=True)
    assert crypto.folder_key_name(link) == crypto.KEY_NAME


@windows_only
def test_windows_case_and_separators_give_one_name(homes):
    _, second = homes
    second.mkdir()
    s = str(second)
    name = crypto.folder_key_name(second)
    assert crypto.folder_key_name(Path(s.upper())) == name
    assert crypto.folder_key_name(Path(s.lower())) == name
    assert crypto.folder_key_name(Path(s.replace("\\", "/"))) == name
    drive, rest = os.path.splitdrive(s)
    assert crypto.folder_key_name(Path(drive.lower() + rest)) == name


def test_entry_name_fits_credential_manager_limits(homes):
    """Windows keyring target is `<user>@<service>` when several users share a service:
    must stay far under CRED_MAX_GENERIC_TARGET_NAME_LENGTH (32767) and the 513-char
    username cap, and use only printable ASCII."""
    _, second = homes
    name = crypto.folder_key_name(second)
    target = f"{name}@{crypto.SERVICE}"
    assert len(name) <= 64 and len(target) <= 128
    assert name.isascii() and name.isprintable()
