"""Pluggable secrets backends for the data key and mailbox passwords. OWNER: orchestrator.

The AES-GCM store format (crypto.Cipher, b"V1" blobs) never changes. A backend only decides
where the 32-byte data key lives and where small secrets (mailbox passwords) are kept:

* ``keyring`` (default, current behaviour): data key and secrets in the OS keychain.
* ``passphrase``: the data key is wrapped with AES-GCM under a key derived from a
  passphrase with scrypt, in ``FREEMYID_HOME/datakey.wrapped.json``. Secrets go into
  ``FREEMYID_HOME/secrets.enc``, encrypted with the data key. The passphrase comes from
  the file named by ``FREEMYID_PASSPHRASE_FILE`` (owner-only permissions, else refused)
  or an interactive prompt. Never from an environment variable holding the secret.
* ``systemd-creds``: same wrapped key, passphrase read from
  ``$CREDENTIALS_DIRECTORY/freemyid-passphrase`` (systemd ``LoadCredential=``) for timer runs.

Selection: ``secrets_backend`` in config.yaml wins. Otherwise auto: an existing wrapped key
file means passphrase (or systemd-creds when the credential is present), a usable keychain
means keyring, and an unusable keychain falls back to passphrase with a plain message.
Never to plaintext. Passphrases and keys are never logged.

Windows note (SEC-76): the owner-only check on ``FREEMYID_PASSPHRASE_FILE`` is POSIX mode
bits and uid, so on Windows the file gets no ACL or owner check. Windows users normally get
the ``keyring`` backend (Credential Manager); if you point it at a passphrase file there,
keep the file inside your own user profile folder.
"""
from __future__ import annotations

import base64
import functools
import getpass
import hmac
import json
import logging
import os
import stat
import sys
import tempfile
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import keyring
import keyring.errors
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from . import crypto, paths

log = logging.getLogger(__name__)

BACKENDS = ("keyring", "passphrase", "systemd-creds")
PASSPHRASE_FILE_ENV = "FREEMYID_PASSPHRASE_FILE"
CRED_NAME = "freemyid-passphrase"
WRAP_FILE = "datakey.wrapped.json"
SECRETS_FILE = "secrets.enc"
LOCK_FILE = "secrets.enc.lock"
PENDING_FILE = "migrate.pending"
MIN_PASSPHRASE_LEN = 8
MAX_PASSPHRASE_BYTES = 4096

# scrypt cost. 2**17/8/1 is the OWASP minimum (about 128 MiB, ~0.2 s). Stored params are
# accepted only inside these bounds so a tampered file can't make us burn memory forever
# or derive with a trivially weak cost.
SCRYPT_N = 2**17
SCRYPT_R = 8
SCRYPT_P = 1
# Ceiling 2**18/8/1 (~256 MiB): headroom over the default without letting an edited file
# demand gigabytes per unwrap (SEC-76).
_N_RANGE = (2**14, 2**18)
_R_RANGE = (8, 8)
_P_RANGE = (1, 1)
_WRAP_AAD = b"freemyid:datakey-wrap:v1"
_SECRETS_AAD = b"freemyid:secrets:v1"

# Data keys unwrapped this process. Deriving costs ~0.2 s. Keyed by the wrap file's path
# plus inode/mtime/size, so a folder wiped and re-created by another process is re-read
# instead of serving the old key (SEC-76).
_key_cache: dict[str, bytes] = {}


def _cache_id(wp: Path) -> str | None:
    try:
        st = wp.stat()
    except FileNotFoundError:
        return None
    return f"{wp.resolve()}|{st.st_ino}|{st.st_mtime_ns}|{st.st_size}"


def clear_cache() -> None:
    _key_cache.clear()


def _remember(wp: Path, key: bytes) -> None:
    _forget(wp)
    if (cid := _cache_id(wp)) is not None:
        _key_cache[cid] = key


def _forget(wp: Path) -> None:
    prefix = f"{wp.resolve()}|"
    for k in [k for k in _key_cache if k.startswith(prefix)]:
        del _key_cache[k]


# ------------------------------------------------------------------------------ protocol

class SecretBackend(Protocol):
    name: str

    def usable(self) -> bool: ...
    def load_data_key(self, create: bool = True) -> bytes: ...
    def store_data_key(self, key: bytes) -> None: ...
    def delete_data_key(self, expected: bytes | None = None) -> None: ...
    def get_secret(self, service: str, user: str) -> str | None: ...
    def set_secret(self, service: str, user: str, value: str) -> None: ...
    def delete_secret(self, service: str, user: str) -> None: ...


# ------------------------------------------------------------------------------ keyring

class KeyringBackend:
    """The OS keychain. Behaviour is exactly the pre-0.2 code path."""

    name = "keyring"

    def usable(self) -> bool:
        try:
            crypto._check_backend()
        except crypto.KeyUnavailable:
            return False
        return True

    def load_data_key(self, create: bool = True) -> bytes:
        if create:
            return crypto._keyring_get_or_create_key()
        try:
            crypto._check_backend()
            stored = keyring.get_password(crypto.SERVICE, crypto.KEY_NAME)
        except keyring.errors.KeyringError as e:
            raise crypto.KeyUnavailable(str(e)) from e
        if stored is None:
            raise crypto.KeyUnavailable("no data key in the OS keychain")
        return crypto._decode_key(stored)

    @staticmethod
    def _stored() -> bytes | None | bool:
        """The keychain's data key: bytes, None if absent, False if the entry is damaged
        (not a 32-byte key, so no data folder can be using it)."""
        try:
            crypto._check_backend()
            stored = keyring.get_password(crypto.SERVICE, crypto.KEY_NAME)
        except (keyring.errors.KeyringError, crypto.KeyUnavailable):
            return None
        if stored is None:
            return None
        try:
            return crypto._decode_key(stored)
        except crypto.KeyUnavailable:
            return False

    def store_data_key(self, key: bytes) -> None:
        """Put `key` in the keychain. The entry is global (not per data folder), so an
        entry holding a different valid key belongs to another folder: refuse (SEC-72)."""
        existing = self._stored()
        if isinstance(existing, bytes):
            if hmac.compare_digest(existing, key):
                return
            raise crypto.KeyUnavailable(
                "the system keychain already holds a different Free My ID key (another data "
                "folder on this computer uses it); this folder can't move its key there"
            )
        try:
            crypto._check_backend()
            keyring.set_password(crypto.SERVICE, crypto.KEY_NAME, base64.b64encode(key).decode())
        except keyring.errors.KeyringError as e:
            raise crypto.KeyUnavailable(str(e)) from e

    def delete_data_key(self, expected: bytes | None = None) -> None:
        """Delete the keychain key. With `expected`, only if it holds exactly that key (or
        a damaged entry): another folder's key is left alone (SEC-72). None = the caller
        has already proven the entry belongs to this folder."""
        if expected is not None:
            existing = self._stored()
            if existing is None:
                return
            if isinstance(existing, bytes) and not hmac.compare_digest(existing, expected):
                log.info("keychain holds another folder's key; left in place")
                return
        try:
            keyring.delete_password(crypto.SERVICE, crypto.KEY_NAME)
        except keyring.errors.KeyringError:   # missing key or no keychain at all: fine
            pass

    def get_secret(self, service: str, user: str) -> str | None:
        return keyring.get_password(service, user)

    def set_secret(self, service: str, user: str, value: str) -> None:
        keyring.set_password(service, user, value)

    def delete_secret(self, service: str, user: str) -> None:
        try:
            keyring.delete_password(service, user)
        except keyring.errors.PasswordDeleteError:
            pass


# ------------------------------------------------------------------------------ passphrase

def _read_secret_file(path: Path, *, allow_group: bool = False) -> str:
    """Read a passphrase file. POSIX: must be a regular file owned by us with no group/other
    access (0600/0400). Checked on the opened fd (no symlink, no swap after the check)."""
    # O_NONBLOCK: a FIFO or device node must not block open() before the S_ISREG check
    # (SEC-73). Regular files ignore it. O_NOCTTY: never adopt a terminal as ctty.
    flags = (os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
             | getattr(os, "O_NOCTTY", 0))
    try:
        fd = os.open(path, flags)
    except OSError as e:
        raise crypto.KeyUnavailable(f"can't open the passphrase file ({e.strerror})") from e
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise crypto.KeyUnavailable("the passphrase file is not a regular file")
        if sys.platform != "win32":
            bad_bits = 0o007 if allow_group else 0o077
            if st.st_mode & bad_bits:
                raise crypto.KeyUnavailable(
                    "the passphrase file can be read by other users; "
                    f"run: chmod 600 {path}"
                )
            if hasattr(os, "getuid") and st.st_uid != os.getuid():
                raise crypto.KeyUnavailable("the passphrase file is owned by another user")
        data = os.read(fd, MAX_PASSPHRASE_BYTES + 1)
    finally:
        os.close(fd)
    if len(data) > MAX_PASSPHRASE_BYTES:
        raise crypto.KeyUnavailable("the passphrase file is too large")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise crypto.KeyUnavailable("the passphrase file is not UTF-8 text") from e
    if text.endswith("\r\n"):
        text = text[:-2]
    elif text.endswith("\n"):
        text = text[:-1]
    if not text:
        raise crypto.KeyUnavailable("the passphrase file is empty")
    return text


def _tty_prompt(confirm: bool) -> str:
    print("Free My ID needs your passphrase to unlock its data.", file=sys.stderr)
    pw = getpass.getpass("Passphrase: ")
    if confirm:
        if len(pw) < MIN_PASSPHRASE_LEN:
            raise crypto.KeyUnavailable(
                f"the passphrase must be at least {MIN_PASSPHRASE_LEN} characters"
            )
        if not hmac.compare_digest(pw.encode(), getpass.getpass("Type it again: ").encode()):
            raise crypto.KeyUnavailable("the two passphrases did not match")
    return pw


# Replaceable in tests. Called with confirm=True when a new passphrase is being chosen.
prompt: Callable[[bool], str] = _tty_prompt


def _interactive() -> bool:
    try:
        return sys.stdin is not None and sys.stdin.isatty()
    except (AttributeError, ValueError):
        return False


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def _unb64(s: object) -> bytes:
    if not isinstance(s, str):
        raise TypeError("expected base64 text")
    return base64.b64decode(s, validate=True)


def _derive(passphrase: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return Scrypt(salt=salt, length=32, n=n, r=r, p=p).derive(passphrase.encode("utf-8"))


def _fsync_dir(d: Path) -> None:
    """Make a rename durable (POSIX). Windows can't open directories; NTFS journals it."""
    if sys.platform == "win32":
        return
    try:
        fd = os.open(d, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        view = view[os.write(fd, view):]


def _atomic_write(path: Path, data: bytes, *, exclusive: bool = False) -> None:
    """Write via a 0600 temp file. exclusive=True never overwrites an existing file
    (first-run race: the loser re-reads the winner's key)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # mkstemp: O_CREAT|O_EXCL, mode 0600, unique name, so two writers never share a temp
    # file (SEC-74).
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        try:
            _write_all(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        if exclusive:
            try:
                os.link(tmp, path)   # raises FileExistsError if someone else won
            except FileExistsError:
                raise
            except OSError:
                # No hard links here (exFAT/FAT, some SMB/NFS): an O_EXCL create is still
                # exclusive, just not atomic against a crash mid-write (SEC-75).
                _exclusive_create(path, data)
        else:
            os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
    _fsync_dir(path.parent)


def _exclusive_create(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
    try:
        _write_all(fd, data)
        os.fsync(fd)
    except BaseException:
        os.close(fd)
        path.unlink(missing_ok=True)
        raise
    os.close(fd)


@contextmanager
def _file_lock(path: Path) -> Iterator[None]:
    """Exclusive inter-process lock on `path` (created if missing) for read-modify-write
    of secrets.enc (SEC-74). flock on POSIX, msvcrt byte lock on Windows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        if sys.platform == "win32":
            import msvcrt
            while True:
                try:
                    msvcrt.locking(fd, msvcrt.LK_LOCK, 1)   # retries for ~10 s itself
                    break
                except OSError:
                    continue
            try:
                yield
            finally:
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


class PassphraseBackend:
    """Data key wrapped under scrypt(passphrase); secrets in an encrypted file in home."""

    name = "passphrase"

    def __init__(self, passphrase_getter: Callable[[bool], str] | None = None) -> None:
        self._getter = passphrase_getter

    # --- where the passphrase comes from (systemd-creds overrides this) ----------------
    def _source_available(self) -> bool:
        return bool(os.environ.get(PASSPHRASE_FILE_ENV)) or _interactive()

    def _passphrase(self, confirm: bool) -> str:
        if self._getter is not None:
            return self._getter(confirm)
        if "FREEMYID_PASSPHRASE" in os.environ:
            # A secret in a plain env var leaks through /proc, ps and crash dumps. Refuse,
            # and drop it so child processes (browser, mail tools) don't inherit it (SEC-76).
            os.environ.pop("FREEMYID_PASSPHRASE", None)
            raise crypto.KeyUnavailable(
                "FREEMYID_PASSPHRASE is not supported. Put the passphrase in a file only you "
                f"can read (chmod 600) and set {PASSPHRASE_FILE_ENV} to its path"
            )
        if fp := os.environ.get(PASSPHRASE_FILE_ENV):
            pw = _read_secret_file(Path(fp))
        elif _interactive():
            pw = prompt(confirm)
        else:
            raise crypto.KeyUnavailable(
                "Free My ID needs its passphrase but can't ask for it here. Set "
                f"{PASSPHRASE_FILE_ENV} to a file only you can read, or use systemd credentials"
            )
        if confirm and len(pw) < MIN_PASSPHRASE_LEN:
            raise crypto.KeyUnavailable(
                f"the passphrase must be at least {MIN_PASSPHRASE_LEN} characters"
            )
        return pw

    # --- files --------------------------------------------------------------------------
    @staticmethod
    def wrap_path() -> Path:
        return paths.home() / WRAP_FILE

    @staticmethod
    def secrets_path() -> Path:
        return paths.home() / SECRETS_FILE

    def usable(self) -> bool:
        return self._getter is not None or self._source_available()

    def _wrap(self, key: bytes, passphrase: str) -> bytes:
        salt, nonce = os.urandom(16), os.urandom(12)
        kek = _derive(passphrase, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
        doc = {
            "v": 1, "kdf": "scrypt", "n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P,
            "salt": _b64(salt), "nonce": _b64(nonce),
            "wrapped": _b64(AESGCM(kek).encrypt(nonce, key, _WRAP_AAD)),
        }
        return json.dumps(doc, indent=1).encode()

    @staticmethod
    def _unwrap(raw: bytes, passphrase: str) -> bytes:
        try:
            doc = json.loads(raw)
            if doc.get("v") != 1 or doc.get("kdf") != "scrypt":
                raise ValueError("unknown format")
            n, r, p = int(doc["n"]), int(doc["r"]), int(doc["p"])
            if not (_N_RANGE[0] <= n <= _N_RANGE[1] and n & (n - 1) == 0
                    and _R_RANGE[0] <= r <= _R_RANGE[1] and _P_RANGE[0] <= p <= _P_RANGE[1]):
                raise ValueError("scrypt parameters out of range")
            salt, nonce, ct = _unb64(doc["salt"]), _unb64(doc["nonce"]), _unb64(doc["wrapped"])
            if len(salt) < 16 or len(nonce) != 12:
                raise ValueError("bad salt/nonce")
        except (ValueError, KeyError, TypeError) as e:
            raise crypto.KeyUnavailable("the wrapped key file is corrupt") from e
        try:
            # GCM tag comparison is constant-time inside OpenSSL; a wrong passphrase and a
            # tampered file fail identically, without revealing which.
            key = AESGCM(_derive(passphrase, salt, n, r, p)).decrypt(nonce, ct, _WRAP_AAD)
        except InvalidTag as e:
            raise crypto.KeyUnavailable("wrong passphrase (or the key file was changed)") from e
        if len(key) != 32:
            raise crypto.KeyUnavailable("the wrapped key has the wrong length")
        return key

    def load_data_key(self, create: bool = True) -> bytes:
        wp = self.wrap_path()
        cache_id = _cache_id(wp)
        if cache_id is not None and cache_id in _key_cache:
            return _key_cache[cache_id]
        if not wp.exists():
            if not create:
                raise crypto.KeyUnavailable("no passphrase-protected key in this data folder")
            pw = self._passphrase(confirm=True)
            key = AESGCM.generate_key(bit_length=256)
            try:
                _atomic_write(wp, self._wrap(key, pw), exclusive=True)
            except FileExistsError:
                pass   # another process created it first; fall through and unwrap theirs
            else:
                _remember(wp, key)
                return key
            key = self._unwrap(wp.read_bytes(), pw)
        else:
            key = self._unwrap(wp.read_bytes(), self._passphrase(confirm=False))
        _remember(wp, key)
        return key

    def store_data_key(self, key: bytes) -> None:
        """Wrap `key` under a passphrase. An existing wrap must already hold the same key."""
        wp = self.wrap_path()
        if wp.exists():
            existing = self._unwrap(wp.read_bytes(), self._passphrase(confirm=False))
            if not hmac.compare_digest(existing, key):
                raise crypto.KeyUnavailable(
                    f"{wp.name} already holds a different key; move it aside first"
                )
        else:
            _atomic_write(wp, self._wrap(key, self._passphrase(confirm=True)))
        _remember(wp, key)

    def delete_data_key(self, expected: bytes | None = None) -> None:
        """Delete this folder's wrap and secrets file (they are per-folder by path)."""
        wp = self.wrap_path()
        _forget(wp)
        wp.unlink(missing_ok=True)
        self.secrets_path().unlink(missing_ok=True)
        (paths.home() / LOCK_FILE).unlink(missing_ok=True)

    # --- secrets: one encrypted JSON map {service: {user: value}} ----------------------
    def _cipher(self) -> crypto.Cipher:
        return crypto.Cipher(self.load_data_key())

    def _read_secrets(self) -> dict[str, dict[str, str]]:
        sp = self.secrets_path()
        if not sp.exists():
            return {}
        try:
            data = json.loads(self._cipher().decrypt(sp.read_bytes(), _SECRETS_AAD))
        except (InvalidTag, ValueError) as e:
            raise crypto.KeyUnavailable("the secrets file can't be decrypted") from e
        return data if isinstance(data, dict) else {}

    def _write_secrets(self, data: dict[str, dict[str, str]]) -> None:
        blob = self._cipher().encrypt(json.dumps(data).encode(), _SECRETS_AAD)
        _atomic_write(self.secrets_path(), blob)

    def list_secrets(self) -> list[tuple[str, str]]:
        return [(s, u) for s, users in self._read_secrets().items() for u in users]

    def get_secret(self, service: str, user: str) -> str | None:
        return self._read_secrets().get(service, {}).get(user)

    def _lock(self) -> AbstractContextManager[None]:
        return _file_lock(paths.home() / LOCK_FILE)

    def set_secret(self, service: str, user: str, value: str) -> None:
        with self._lock():
            data = self._read_secrets()
            data.setdefault(service, {})[user] = value
            self._write_secrets(data)

    def delete_secret(self, service: str, user: str) -> None:
        if not self.secrets_path().exists():
            return
        with self._lock():
            data = self._read_secrets()
            if data.get(service, {}).pop(user, None) is not None:
                if not data[service]:
                    del data[service]
                self._write_secrets(data)


class SystemdCredsBackend(PassphraseBackend):
    """Passphrase from systemd's $CREDENTIALS_DIRECTORY (LoadCredential=/SetCredential=)."""

    name = "systemd-creds"

    @staticmethod
    def cred_path() -> Path | None:
        d = os.environ.get("CREDENTIALS_DIRECTORY")
        return Path(d) / CRED_NAME if d else None

    def _source_available(self) -> bool:
        p = self.cred_path()
        return p is not None and p.is_file()

    def _passphrase(self, confirm: bool) -> str:
        if self._getter is not None:
            return self._getter(confirm)
        p = self.cred_path()
        if p is None or not p.is_file():
            raise crypto.KeyUnavailable(
                f"systemd credential '{CRED_NAME}' is missing; add "
                f"LoadCredential={CRED_NAME}:<path> to the service"
            )
        # systemd may grant the service's group read access; world access is still refused.
        pw = _read_secret_file(p, allow_group=True)
        if confirm and len(pw) < MIN_PASSPHRASE_LEN:
            raise crypto.KeyUnavailable(
                f"the passphrase must be at least {MIN_PASSPHRASE_LEN} characters"
            )
        return pw


# ------------------------------------------------------------------------------ selection

def make(name: str) -> SecretBackend:
    if name == "keyring":
        return KeyringBackend()
    if name == "passphrase":
        return PassphraseBackend()
    if name == "systemd-creds":
        return SystemdCredsBackend()
    raise ValueError(f"unknown secrets backend {name!r}; choose one of {', '.join(BACKENDS)}")


_FALLBACK_NOTICE = (
    "This computer has no system keychain Free My ID can use, so your data will be "
    "protected with a passphrase instead. Keep it somewhere safe: without it the saved "
    "data can't be opened."
)


_noticed = False


def configured_name() -> str | None:
    from . import config
    return config.load().secrets_backend


def select() -> SecretBackend:
    """The backend to use now. An unfinished migration wins (see migrate), then explicit
    config; otherwise auto-detect (see module doc)."""
    if (pend := _read_pending()) is not None:
        # "copy": the source still holds everything. "cleanup": the target does.
        return make(pend["from"] if pend["phase"] == "copy" else pend["to"])
    if (name := configured_name()) is not None:
        return make(name)
    creds = SystemdCredsBackend()
    if PassphraseBackend.wrap_path().exists():
        return creds if creds._source_available() else PassphraseBackend()
    kr = KeyringBackend()
    if kr.usable():
        return kr
    if paths.db_path().exists():
        # Data exists but has no passphrase wrap: it was locked with a keychain that is
        # gone now. Creating a fresh key would orphan it, so fail closed.
        raise crypto.KeyUnavailable(
            "Your saved data is locked with the system keychain, which isn't available "
            "right now. Unlock or start the keychain, then run 'freemyid secrets migrate "
            "--to passphrase' if you want to stop depending on it"
        )
    if creds._source_available():
        return creds
    global _noticed
    if not _noticed:
        _noticed = True
        log.warning(_FALLBACK_NOTICE)
        if _interactive():
            print(_FALLBACK_NOTICE, file=sys.stderr)
    return PassphraseBackend()


# ------------------------------------------------------------------------------ wipe

def _db_key_check() -> str | None:
    """The DB's key_check value, read straight from sqlite (no key needed)."""
    db = paths.db_path()
    if not db.exists():
        return None
    import sqlite3
    try:
        con = sqlite3.connect(f"{db.as_uri()}?mode=ro", uri=True)
        try:
            row = con.execute("SELECT v FROM meta WHERE k='key_check'").fetchone()
        finally:
            con.close()
    except sqlite3.Error:
        return None
    return row[0] if row else None


def _keychain_key_is_ours(kc_key: bytes) -> bool:
    """Does the (global) keychain key belong to this data folder? Proven by the DB's
    key_check, else by this folder's wrap holding the same key. Unproven = not ours."""
    if (kc := _db_key_check()) is not None:
        return crypto.Cipher(kc_key).verify_key_check(kc)
    pb = PassphraseBackend()
    if pb.wrap_path().exists():
        try:
            return hmac.compare_digest(pb.load_data_key(create=False), kc_key)
        except crypto.KeyUnavailable:
            return False
    return False


def wipe_data_keys() -> None:
    """`freemyid wipe`: remove this folder's wrap and secrets file, and the keychain key
    only when it is this folder's key or a damaged entry (SEC-72). Never raises for a
    missing key or a missing keychain."""
    kr = KeyringBackend()
    stored = kr._stored()
    if stored is False:
        kr.delete_data_key()
    elif isinstance(stored, bytes):
        if _keychain_key_is_ours(stored):
            kr.delete_data_key(expected=stored)
        else:
            log.info("wipe: the keychain key isn't this folder's; left in place")
    PassphraseBackend().delete_data_key()
    (paths.home() / PENDING_FILE).unlink(missing_ok=True)


# ------------------------------------------------------------------------------ migration

@dataclass
class MigrateResult:
    from_backend: str
    to_backend: str
    secrets_moved: int
    changed: bool


def _known_secret_ids(src: SecretBackend, key: bytes) -> list[tuple[str, str]]:
    """Every (service, user) that may hold a secret. The keychain can't be listed, so ask
    the store which mailboxes exist."""
    ids: set[tuple[str, str]] = set()
    if isinstance(src, PassphraseBackend):
        ids.update(src.list_secrets())
    if paths.db_path().exists():
        from .secrets import _user
        from .storage import Store
        store = Store(cipher=crypto.Cipher(key))
        try:
            for p in store.list_profiles():
                if p.mailbox:
                    ids.add((p.mailbox.keyring_service, _user(p.id, p.mailbox)))
        finally:
            store.close()
    return sorted(ids)


def _pending_path() -> Path:
    return paths.home() / PENDING_FILE


def _read_pending() -> dict[str, Any] | None:
    """The migrate.pending marker, or None. Written atomically, so damage means tampering
    or a broken disk: fail closed with a plain message."""
    pp = _pending_path()
    try:
        raw = pp.read_bytes()
    except FileNotFoundError:
        return None
    try:
        d = json.loads(raw)
        if (isinstance(d, dict) and d.get("from") in BACKENDS and d.get("to") in BACKENDS
                and d.get("phase") in ("copy", "cleanup")
                and (d.get("orig") is None or d.get("orig") in BACKENDS)
                and isinstance(d.get("target_existed"), bool)):
            return d
    except ValueError:
        pass
    raise crypto.KeyUnavailable(
        f"{pp} (left by an unfinished 'freemyid secrets migrate') is damaged. Your data is "
        "safe; ask for help before deleting it"
    )


def _write_pending(d: dict[str, Any]) -> None:
    _atomic_write(_pending_path(), json.dumps(d).encode())


def _has_data_key(b: SecretBackend) -> bool:
    if isinstance(b, PassphraseBackend):
        return b.wrap_path().exists()
    if isinstance(b, KeyringBackend):
        return b._stored() is not None
    return False


def _with_memo_passphrase(b: SecretBackend) -> SecretBackend:
    """Ask a passphrase target for its passphrase once per migrate, so the from-disk
    verify doesn't prompt a second time. Kept in this closure only."""
    if not isinstance(b, PassphraseBackend) or b._getter is not None:
        return b
    raw = type(b)()
    memo: list[str] = []

    def getter(confirm: bool) -> str:
        if not memo:
            memo.append(raw._passphrase(confirm))
        return memo[0]
    return type(b)(getter)


def _verify_on_disk(target: SecretBackend, key: bytes) -> None:
    """SEC-70: read the key back from where it now lives, not from this process's cache."""
    clear_cache()
    fresh: SecretBackend = (type(target)(target._getter) if isinstance(target, PassphraseBackend)
                            else type(target)())
    try:
        got = fresh.load_data_key(create=False)
    except crypto.KeyUnavailable as e:
        raise crypto.KeyUnavailable(
            "migration check failed: the new copy of the key can't be read back; "
            "nothing was moved"
        ) from e
    if not hmac.compare_digest(got, key):
        raise crypto.KeyUnavailable("migration check failed: the new copy of the key differs")


def _cleanup_source(source: SecretBackend, key: bytes, ids: list[tuple[str, str]]) -> None:
    if isinstance(source, PassphraseBackend):
        source.delete_data_key()   # wrap and secrets.enc are this folder's files
        return
    for svc, user in ids:
        source.delete_secret(svc, user)
    source.delete_data_key(expected=key)   # never another folder's keychain key (SEC-72)


def _rollback(target: SecretBackend, key: bytes | None, ids: list[tuple[str, str]],
              pend: dict[str, Any], config_switched: bool) -> None:
    """Undo a copy-phase failure: original config value (None = auto stays None), target
    copies removed, marker removed. Each step is best effort; if this is interrupted the
    marker stays and select() keeps reading from the intact source."""
    from . import config
    steps: list[Callable[[], None]] = []
    if config_switched:
        def restore_config() -> None:
            cfg = config.load()
            cfg.secrets_backend = pend["orig"]
            config.save(cfg)
        steps.append(restore_config)
    for svc, user in ids:
        steps.append(functools.partial(target.delete_secret, svc, user))
    if not pend["target_existed"] and key is not None:
        steps.append(lambda: target.delete_data_key(expected=key))
    steps.append(lambda: _pending_path().unlink(missing_ok=True))
    for step in steps:
        try:
            step()
        except Exception:  # noqa: BLE001  keep going; the source is untouched
            log.warning("secrets migrate: a rollback step failed")
    clear_cache()


def migrate(to: str) -> MigrateResult:
    """Re-wrap the data key (and copy mailbox passwords) into backend `to`. No data loss:

    1. write migrate.pending (phase "copy"): select() keeps using the source;
    2. store the key in the target and re-read it from disk (SEC-70), copy the passwords;
    3. switch config, set the marker to "cleanup": select() now uses the target;
    4. delete the source copies, delete the marker.

    A failure (any BaseException) in 1-3 rolls back to the original config value. A kill
    leaves the marker, and running the same migrate again resumes (SEC-71). Encrypted
    data in the store is untouched (same data key)."""
    target = make(to)
    from . import config
    cfg = config.load()
    pend = _read_pending()
    if pend is not None:
        if pend["to"] != target.name:
            raise crypto.KeyUnavailable(
                f"an earlier move to '{pend['to']}' didn't finish; run 'freemyid secrets "
                f"migrate --to {pend['to']}' first"
            )
        source = make(pend["from"])
    else:
        source = select()
        if source.name == target.name or (
            isinstance(source, PassphraseBackend) and isinstance(target, PassphraseBackend)
        ):
            # Passphrase and systemd-creds share one wrap file; only the setting changes.
            changed = cfg.secrets_backend != target.name
            if changed:
                cfg.secrets_backend = target.name  # type: ignore[assignment]
                config.save(cfg)
            return MigrateResult(source.name, target.name, 0, changed)
        pend = {"from": source.name, "to": target.name, "orig": cfg.secrets_backend,
                "target_existed": _has_data_key(target), "phase": "copy"}
        _write_pending(pend)

    target = _with_memo_passphrase(target)
    key: bytes | None = None
    ids: list[tuple[str, str]] = []
    values: dict[tuple[str, str], str] = {}
    config_switched = False
    if pend["phase"] == "copy":
        try:
            key = source.load_data_key(create=False)
            ids = _known_secret_ids(source, key)
            values = {i: v for i in ids if (v := source.get_secret(*i)) is not None}
            target.store_data_key(key)
            _verify_on_disk(target, key)
            for (svc, user), val in values.items():
                target.set_secret(svc, user, val)
                if target.get_secret(svc, user) != val:
                    raise crypto.KeyUnavailable("migration check failed for a saved password")
            cfg.secrets_backend = target.name  # type: ignore[assignment]
            config.save(cfg)
            config_switched = True
            pend["phase"] = "cleanup"
            _write_pending(pend)
        except BaseException:
            _rollback(target, key, list(values), pend, config_switched)
            raise
    else:
        # Killed during cleanup: the target is complete and authoritative.
        key = target.load_data_key(create=False)
        ids = _known_secret_ids(source, key) if isinstance(source, KeyringBackend) else []
        if cfg.secrets_backend != target.name:
            cfg.secrets_backend = target.name  # type: ignore[assignment]
            config.save(cfg)
    _cleanup_source(source, key, ids)
    _pending_path().unlink(missing_ok=True)
    log.info("secrets migrated from %s to %s (%d saved passwords)",
             source.name, target.name, len(values))
    return MigrateResult(source.name, target.name, len(values), True)
