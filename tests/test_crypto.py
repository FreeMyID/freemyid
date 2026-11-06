"""crypto.py: AES-GCM blob format, AAD binding, file encryption, passphrase export."""
from __future__ import annotations

import sys

import pytest
from cryptography.exceptions import InvalidTag

from freemyid import crypto
from freemyid.crypto import Cipher, export_with_passphrase, import_with_passphrase


def test_roundtrip_and_format():
    c = Cipher()
    blob = c.encrypt(b"Jane Q Testperson", b"profiles:1")
    assert blob[:2] == b"V1"
    assert b"Testperson" not in blob
    assert c.decrypt(blob, b"profiles:1") == b"Jane Q Testperson"


def test_fresh_nonce_each_time():
    c = Cipher()
    assert c.encrypt(b"x") != c.encrypt(b"x")


def test_aad_binding():
    c = Cipher()
    blob = c.encrypt(b"secret", b"profiles:a")
    with pytest.raises(InvalidTag):
        c.decrypt(blob, b"profiles:b")


def test_tamper_detected():
    c = Cipher()
    blob = bytearray(c.encrypt(b"secret"))
    blob[-1] ^= 1
    with pytest.raises(InvalidTag):
        c.decrypt(bytes(blob))


def test_unknown_magic_rejected():
    with pytest.raises(ValueError):
        Cipher().decrypt(b"XX" + b"\0" * 40)


def test_wrong_key_fails():
    blob = Cipher(b"\1" * 32).encrypt(b"secret")
    with pytest.raises(InvalidTag):
        Cipher(b"\2" * 32).decrypt(blob)


def test_test_key_is_deterministic():
    assert Cipher().decrypt(Cipher().encrypt(b"x")) == b"x"


def test_keyring_key_created_once(monkeypatch, memkeyring):
    monkeypatch.delenv("FREEMYID_TEST_KEY")
    c1 = Cipher()
    assert (crypto.SERVICE, crypto.KEY_NAME) in memkeyring.store
    assert Cipher().decrypt(c1.encrypt(b"x")) == b"x"


def test_keyring_error_becomes_key_unavailable(monkeypatch):
    import keyring
    from keyring.errors import KeyringError
    monkeypatch.delenv("FREEMYID_TEST_KEY")

    def boom(*a, **k):
        raise KeyringError("locked")
    monkeypatch.setattr(keyring, "get_password", boom)
    with pytest.raises(crypto.KeyUnavailable):
        Cipher()


def test_encrypt_file(tmp_path):
    c = Cipher()
    dest = tmp_path / "p" / "shot.png"
    sha = c.encrypt_file(b"Jane Q Testperson screenshot", dest)
    assert len(sha) == 64
    assert b"Testperson" not in dest.read_bytes()
    if sys.platform != "win32":  # POSIX mode bits; Windows relies on per-user %APPDATA% ACLs
        assert dest.stat().st_mode & 0o077 == 0
    assert c.decrypt_file(dest) == b"Jane Q Testperson screenshot"


def test_passphrase_roundtrip():
    blob = export_with_passphrase(b"profile json", "correct horse")
    assert blob[:3] == b"VP1"
    assert import_with_passphrase(blob, "correct horse") == b"profile json"
    with pytest.raises(InvalidTag):
        import_with_passphrase(blob, "wrong")
    with pytest.raises(ValueError):
        import_with_passphrase(b"nope" + blob, "correct horse")


# ---- regressions for fixed findings ----

def test_empty_key_rejected():
    with pytest.raises((ValueError, TypeError)):
        Cipher(b"")


def test_evidence_file_aad_binds_directory(tmp_path):
    c = Cipher()
    a, b = tmp_path / "p1" / "s.png", tmp_path / "p2" / "s.png"
    c.encrypt_file(b"one", a)
    c.encrypt_file(b"two", b)
    a.write_bytes(b.read_bytes())          # swap p2's file into p1's slot
    with pytest.raises(InvalidTag):
        c.decrypt_file(a)
