"""WO-605 review fixes F1-F5 (Theo Park). Fake in-memory keyring only (conftest
MemoryKeyring), never the real system keychain. Fake people only."""
from __future__ import annotations

import base64
import os
import sqlite3
import sys
from pathlib import Path

import keyring
import pytest
from typer.testing import CliRunner

from freemyid import crypto, paths, secret_backends
from freemyid.crypto import Cipher
from tests.conftest import MemoryKeyring, make_profile

posix_only = pytest.mark.posix_only


def _quiet_backends(monkeypatch) -> None:
    assert isinstance(keyring.get_keyring(), MemoryKeyring)   # never the real keychain
    monkeypatch.delenv("FREEMYID_TEST_KEY", raising=False)
    monkeypatch.delenv("FREEMYID_PASSPHRASE_FILE", raising=False)
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    monkeypatch.setattr(secret_backends, "SCRYPT_N", 2**14)
    monkeypatch.setattr(secret_backends, "_interactive", lambda: False)
    monkeypatch.setattr(secret_backends, "_noticed", False)


@pytest.fixture
def homes(freemyid_env, tmp_path, monkeypatch):
    _quiet_backends(monkeypatch)
    main, second = tmp_path / "main", tmp_path / "second"
    monkeypatch.setattr(crypto, "default_home", lambda: main)
    secret_backends.clear_cache()
    yield main, second
    secret_backends.clear_cache()


def _use(monkeypatch, home: Path) -> None:
    monkeypatch.setenv("FREEMYID_HOME", str(home))
    secret_backends.clear_cache()
    paths.home()


def _entries(kr: MemoryKeyring) -> dict[str, str]:
    return {user: v for (svc, user), v in kr.store.items() if svc == crypto.SERVICE}


def _b64(key: bytes) -> str:
    return base64.b64encode(key).decode()


def _old_style_folder(home: Path, key: bytes, *, key_check: bool = True) -> str:
    from freemyid.storage import Store
    home.mkdir(parents=True, exist_ok=True)
    s = Store(path=home / "freemyid.db", cipher=Cipher(key))
    p = make_profile()
    s.save_profile(p)
    s.close()
    if not key_check:   # a DB from before key_check values existed
        con = sqlite3.connect(home / "freemyid.db")
        con.execute("DELETE FROM meta WHERE k='key_check'")
        con.commit()
        con.close()
    return p.id


def _opens(pid: str) -> bool:
    from freemyid.storage import Store
    s = Store()
    try:
        return s.get_profile(pid) is not None
    finally:
        s.close()


# ---------------------------------------------------------------- F1: auto-copy proven key

def test_f1_copies_proven_shared_key_and_never_touches_shared(homes, monkeypatch,
                                                               memkeyring):
    _, second = homes
    k1 = os.urandom(32)
    memkeyring.set_password(crypto.SERVICE, crypto.KEY_NAME, _b64(k1))
    _old_style_folder(second, k1)
    _use(monkeypatch, second)
    assert crypto._keyring_get_or_create_key(create=False) == k1
    assert _entries(memkeyring) == {crypto.KEY_NAME: _b64(k1),
                                    crypto.folder_key_name(second): _b64(k1)}


def test_f1_never_copies_without_key_check(homes, monkeypatch, memkeyring):
    _, second = homes
    k1 = os.urandom(32)
    memkeyring.set_password(crypto.SERVICE, crypto.KEY_NAME, _b64(k1))
    _old_style_folder(second, k1, key_check=False)
    _use(monkeypatch, second)
    assert crypto.db_key_check() == (True, None)
    assert crypto._keyring_get_or_create_key(create=False) == k1   # Store proves it later
    assert set(_entries(memkeyring)) == {crypto.KEY_NAME}


def test_f1_never_overwrites_an_existing_own_entry(homes, monkeypatch, memkeyring):
    _, second = homes
    k1, stale = os.urandom(32), _b64(os.urandom(32))
    memkeyring.set_password(crypto.SERVICE, crypto.KEY_NAME, _b64(k1))
    _old_style_folder(second, k1)
    memkeyring.set_password(crypto.SERVICE, crypto.folder_key_name(second), stale)
    _use(monkeypatch, second)
    assert crypto._keyring_get_or_create_key(create=False) == k1
    assert _entries(memkeyring) == {crypto.KEY_NAME: _b64(k1),
                                    crypto.folder_key_name(second): stale}


def test_f1_copy_that_does_not_read_back_still_uses_shared_key(homes, monkeypatch,
                                                                memkeyring):
    _, second = homes
    k1 = os.urandom(32)
    memkeyring.set_password(crypto.SERVICE, crypto.KEY_NAME, _b64(k1))
    _old_style_folder(second, k1)
    _use(monkeypatch, second)
    real_set = memkeyring.set_password
    own = crypto.folder_key_name(second)

    def lossy_set(service, user, value):
        if user != own:
            real_set(service, user, value)

    monkeypatch.setattr(memkeyring, "set_password", lossy_set)
    assert crypto._keyring_get_or_create_key(create=False) == k1
    assert set(_entries(memkeyring)) == {crypto.KEY_NAME}


def test_f1_default_folder_never_copies(homes, monkeypatch, memkeyring):
    main, _ = homes
    k1 = os.urandom(32)
    memkeyring.set_password(crypto.SERVICE, crypto.KEY_NAME, _b64(k1))
    _old_style_folder(main, k1)
    _use(monkeypatch, main)
    assert crypto._keyring_get_or_create_key(create=False) == k1
    assert set(_entries(memkeyring)) == {crypto.KEY_NAME}


# ---------------------------------------------------------------- F2: unreadable DB

@pytest.fixture
def unreadable_second(homes, monkeypatch, memkeyring):
    _, second = homes
    k1 = os.urandom(32)
    memkeyring.set_password(crypto.SERVICE, crypto.KEY_NAME, _b64(k1))
    second.mkdir(parents=True)
    (second / "freemyid.db").write_bytes(b"not a sqlite file at all, just junk bytes" * 4)
    _use(monkeypatch, second)
    return second


def test_f2_db_state_reports_unreadable(unreadable_second):
    st = crypto.db_state()
    assert not st.readable and st.has_data and st.key_check is None
    with pytest.raises(crypto.KeyUnavailable) as e:
        crypto.db_key_check()
    assert not isinstance(e.value, crypto.KeyMismatch)   # retry later, not "key lost"
    assert crypto.db_key_check(strict=False) == (True, None)   # wipe: fail closed


def test_f2_keyring_load_raises_retry_later_and_writes_nothing(unreadable_second,
                                                               memkeyring):
    with pytest.raises(crypto.KeyUnavailable) as e:
        crypto._keyring_get_or_create_key(create=True)
    assert not isinstance(e.value, crypto.KeyMismatch)
    assert "try again" in str(e.value)
    assert set(_entries(memkeyring)) == {crypto.KEY_NAME}


def test_f2_entry_status_unreadable_not_shared(unreadable_second):
    assert secret_backends.KeyringBackend().entry_status() == "unreadable"
    assert secret_backends.KeyringBackend().adopt_own_entry() is False


def test_f2_passphrase_backend_unreadable_db_never_makes_key(unreadable_second):
    with pytest.raises(crypto.KeyUnavailable) as e:
        secret_backends.PassphraseBackend(lambda confirm: "pw").load_data_key()
    assert not isinstance(e.value, crypto.KeyMismatch)
    assert not secret_backends.PassphraseBackend.wrap_path().exists()


def test_f2_readable_db_with_people_but_no_key_check_may_use_shared(homes, monkeypatch,
                                                                    memkeyring):
    _, second = homes
    k1 = os.urandom(32)
    memkeyring.set_password(crypto.SERVICE, crypto.KEY_NAME, _b64(k1))
    pid = _old_style_folder(second, k1, key_check=False)
    _use(monkeypatch, second)
    assert crypto.db_state().readable
    assert _opens(pid)                         # Store proves it by decrypting, writes kc
    assert crypto.db_key_check()[1] is not None


def test_f2_wipe_still_runs_with_unreadable_db(unreadable_second, memkeyring):
    crypto.delete_key()
    assert set(_entries(memkeyring)) == {crypto.KEY_NAME}   # never the shared entry


# ---------------------------------------------------------------- F3: stale own entry

def test_f3_damaged_own_entry_is_replaced_by_proven_key(homes, monkeypatch, memkeyring):
    _, second = homes
    k1 = os.urandom(32)
    memkeyring.set_password(crypto.SERVICE, crypto.KEY_NAME, _b64(k1))
    pid = _old_style_folder(second, k1)
    memkeyring.set_password(crypto.SERVICE, crypto.folder_key_name(second), "not-a-key")
    _use(monkeypatch, second)
    assert secret_backends.KeyringBackend().entry_status() == "shared"
    assert secret_backends.KeyringBackend().adopt_own_entry() is True
    assert _entries(memkeyring) == {crypto.KEY_NAME: _b64(k1),
                                    crypto.folder_key_name(second): _b64(k1)}
    assert _opens(pid)


def test_f3_unproven_stale_entry_left_alone_with_passphrase_advice(homes, monkeypatch,
                                                                   memkeyring):
    """No key_check yet, so nothing proves which key is right: refuse, and say what to do."""
    _, second = homes
    k1, stale = os.urandom(32), _b64(os.urandom(32))
    memkeyring.set_password(crypto.SERVICE, crypto.KEY_NAME, _b64(k1))
    _old_style_folder(second, k1, key_check=False)
    memkeyring.set_password(crypto.SERVICE, crypto.folder_key_name(second), stale)
    _use(monkeypatch, second)
    kb = secret_backends.KeyringBackend()
    assert kb.entry_status() == "own"          # unproven either way: own entry wins
    monkeypatch.setattr(kb, "entry_status", lambda: "shared")   # force the adopt path
    with pytest.raises(crypto.KeyUnavailable) as e:
        kb.adopt_own_entry()
    msg = str(e.value)
    assert "secrets migrate --to passphrase" in msg and "another data folder" not in msg
    assert _entries(memkeyring)[crypto.folder_key_name(second)] == stale


def test_f3_own_entry_kept_when_shared_key_does_not_pass(homes, monkeypatch, memkeyring):
    _, second = homes
    k_own, k_other = os.urandom(32), os.urandom(32)
    memkeyring.set_password(crypto.SERVICE, crypto.KEY_NAME, _b64(k_other))
    _old_style_folder(second, k_own)
    memkeyring.set_password(crypto.SERVICE, crypto.folder_key_name(second), _b64(k_own))
    _use(monkeypatch, second)
    kb = secret_backends.KeyringBackend()
    monkeypatch.setattr(kb, "entry_status", lambda: "shared")
    with pytest.raises(crypto.KeyUnavailable):
        kb.adopt_own_entry()
    assert _entries(memkeyring)[crypto.folder_key_name(second)] == _b64(k_own)


def test_f3_store_data_key_refusal_message(homes, monkeypatch, memkeyring):
    _, second = homes
    memkeyring.set_password(crypto.SERVICE, crypto.folder_key_name(second),
                            _b64(os.urandom(32)))
    _use(monkeypatch, second)
    with pytest.raises(crypto.KeyUnavailable) as e:
        secret_backends.KeyringBackend().store_data_key(os.urandom(32))
    msg = str(e.value)
    assert "secrets migrate --to passphrase" in msg and "another data folder" not in msg


# ---------------------------------------------------------------- F4: macOS case-insensitive

def test_f4_darwin_one_name_for_case_and_unicode_forms(homes, monkeypatch, tmp_path):
    main, _ = homes
    folder = tmp_path / "Café Data"
    monkeypatch.setattr(sys, "platform", "darwin")
    name = crypto.folder_key_name(folder)
    assert name != crypto.KEY_NAME
    assert crypto.folder_key_name(Path(str(folder).upper())) == name
    assert crypto.folder_key_name(Path(str(folder).lower())) == name
    assert crypto.folder_key_name(tmp_path / "Café Data") == name   # NFD form
    assert crypto.is_default_home(Path(str(main).upper()))


def test_f4_linux_stays_case_sensitive(homes, monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    folder = tmp_path / "Data"
    assert crypto.folder_key_name(folder) != crypto.folder_key_name(tmp_path / "data")


# ---------------------------------------------------------------- F5: wipe prompt, freemyid_env

def _wipe_prompt(home: Path) -> str:
    from freemyid import cli
    home.mkdir(parents=True, exist_ok=True)
    (home / paths.MARKER).touch()
    res = CliRunner().invoke(cli.app, ["wipe"], input="n\n")
    assert res.exit_code == 0
    assert home.exists()                       # answered no: nothing deleted
    return " ".join(res.output.split())


def test_f5_wipe_prompt_default_folder_warns_about_extra_folders(freemyid_env):
    out = _wipe_prompt(paths.home())
    assert "extra Free My ID folder" in out and "may stop opening" in out


def test_f5_wipe_prompt_other_folder_says_others_unaffected(freemyid_env, tmp_path,
                                                            monkeypatch):
    monkeypatch.setattr(crypto, "default_home", lambda: tmp_path / "elsewhere")
    out = _wipe_prompt(paths.home())
    assert "not affected" in out and "stop opening" not in out


def test_f5_non_default_folder_keyring_round_trip_via_freemyid_env(freemyid_env, tmp_path,
                                                                   monkeypatch, memkeyring):
    """The normal fixture, with its home made non-default: the key goes to this folder's
    own entry, and wiping it leaves the main folder's entry alone."""
    _quiet_backends(monkeypatch)
    monkeypatch.setattr(crypto, "default_home", lambda: tmp_path / "elsewhere")
    secret_backends.clear_cache()
    home = paths.home()
    k_main = _b64(os.urandom(32))
    memkeyring.set_password(crypto.SERVICE, crypto.KEY_NAME, k_main)
    assert not crypto.is_default_home(home)
    from freemyid.storage import Store
    s = Store()
    p = make_profile()
    s.save_profile(p)
    s.close()
    entries = _entries(memkeyring)
    own = crypto.folder_key_name(home)
    assert set(entries) == {crypto.KEY_NAME, own} and entries[own] != k_main
    secret_backends.clear_cache()
    assert _opens(p.id)
    crypto.delete_key()
    assert _entries(memkeyring) == {crypto.KEY_NAME: k_main}
