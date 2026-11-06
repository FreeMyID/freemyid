"""At-rest encryption. Key lives in the OS keychain. OWNER: orchestrator.

Field/blob-level AES-256-GCM. Ciphertext format: b"V1" + 12-byte nonce + ct||tag.
SQLCipher was considered; blob encryption avoids cross-platform native packaging issues.
Only ids, enums and timestamps are stored in clear; all PII is inside encrypted blobs.
"""
from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path

import keyring
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SERVICE = "vanish"
KEY_NAME = "db-key-v1"
_MAGIC = b"V1"


class KeyUnavailable(RuntimeError):
    """OS keychain locked/unavailable (e.g. headless session). Surface as NEEDS_HUMAN."""


def _get_or_create_key() -> bytes:
    if test_key := os.environ.get("VANISH_TEST_KEY"):   # tests only; never documented for users
        return hashlib.sha256(test_key.encode()).digest()
    try:
        stored = keyring.get_password(SERVICE, KEY_NAME)
        if stored is None:
            key = AESGCM.generate_key(bit_length=256)
            keyring.set_password(SERVICE, KEY_NAME, base64.b64encode(key).decode())
            return key
        return base64.b64decode(stored)
    except keyring.errors.KeyringError as e:  # type: ignore[attr-defined]
        raise KeyUnavailable(str(e)) from e


class Cipher:
    def __init__(self, key: bytes | None = None) -> None:
        self._aes = AESGCM(key or _get_or_create_key())

    def encrypt(self, data: bytes, aad: bytes = b"") -> bytes:
        nonce = os.urandom(12)
        return _MAGIC + nonce + self._aes.encrypt(nonce, data, aad or None)

    def decrypt(self, blob: bytes, aad: bytes = b"") -> bytes:
        if blob[:2] != _MAGIC:
            raise ValueError("unknown ciphertext format")
        return self._aes.decrypt(blob[2:14], blob[14:], aad or None)

    def encrypt_file(self, src_bytes: bytes, dest: Path) -> str:
        """Write encrypted file; return sha256 of the plaintext."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.encrypt(src_bytes, aad=dest.name.encode()))
        dest.chmod(0o600)
        return hashlib.sha256(src_bytes).hexdigest()

    def decrypt_file(self, path: Path) -> bytes:
        return self.decrypt(path.read_bytes(), aad=path.name.encode())


# --- passphrase-based export (family installer pre-filled profiles) --------------------------

def export_with_passphrase(data: bytes, passphrase: str) -> bytes:
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

    salt = os.urandom(16)
    key = Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(passphrase.encode())
    nonce = os.urandom(12)
    return b"VP1" + salt + nonce + AESGCM(key).encrypt(nonce, data, b"vanish-profile")


def import_with_passphrase(blob: bytes, passphrase: str) -> bytes:
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

    if blob[:3] != b"VP1":
        raise ValueError("not a Vanish profile file")
    salt, nonce, ct = blob[3:19], blob[19:31], blob[31:]
    key = Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(passphrase.encode())
    return AESGCM(key).decrypt(nonce, ct, b"vanish-profile")
