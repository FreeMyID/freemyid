"""Native messaging host for the Free My ID browser extension (STUB).

The extension (extension/, docs/EXTENSION.md) never uses the network. It talks to this program
only, which the browser starts and connects to over stdin/stdout:

    python -m freemyid.native_host

Wire format (set by the browsers): each message is a 4-byte length in the machine's own byte
order, then that many bytes of UTF-8 JSON.

Messages are versioned envelopes, ``{"v": 1, "type": ..., "id": ...}`` plus at most one field:

    ping            -> {"ok": true, "pong": true}
    status          -> {"ok": true, "connected": true, "app_version": "0.3.1"}
    site_check      hostname   -> broker id and listing state        (stub: always "unknown")
    start_removal   broker_id  -> the app starts the removal itself  (stub: "not_implemented")

No message carries personal details, and unknown fields are refused, so none can be slipped in.
Nothing about a message is logged. ``site_check`` and ``start_removal`` are stubs: wiring them to
the store and the engine needs the change requests in docs/handoff/wizard-packager.md.

The browser says who is calling on the command line, and the host checks it before it reads a
single byte: Chrome and Edge pass ``chrome-extension://<id>/`` as the first argument, Firefox
passes the host manifest's path and then the add-on id. A caller that is not on the list gets
no answer at all (exit code 2). The browser already enforces the host manifest's own list; this
is a second check that does not depend on that file.

This module opens no files, no database and no network connection.
"""
from __future__ import annotations

import json
import os
import re
import struct
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import Any, BinaryIO

from freemyid import __version__

HOST_NAME = "org.freemyid.host"
PROTOCOL_VERSION = 1
FIREFOX_EXTENSION_ID = "extension@freemyid.org"
# Chrome Web Store and Edge Add-ons ids of the published extension. Empty until it is published
# (docs/EXTENSION.md section 11): put the store ids here and in the host manifest together.
CHROME_EXTENSION_IDS: tuple[str, ...] = ()
# Developers: the id of an unpacked extension changes from machine to machine, so the launcher
# script may name it here (comma separated). See docs/EXTENSION.md section 9.
EXTENSION_IDS_ENV = "FREEMYID_EXTENSION_IDS"
EXIT_CALLER_REFUSED = 2

# The extension's messages are tiny. Anything bigger is not ours.
MAX_REQUEST_BYTES = 64 * 1024
# The browsers refuse a reply over 1 MB.
MAX_REPLY_BYTES = 1024 * 1024
# A request is one flat object. A few levels are tolerated, deep nesting is refused before the
# JSON parser sees it (the parser recurses once per level).
MAX_JSON_DEPTH = 4

MESSAGE_TYPES = ("ping", "status", "site_check", "start_removal")
# The one extra field each type may carry, next to v/type/id.
_EXTRA_FIELD = {"ping": None, "status": None, "site_check": "hostname",
                "start_removal": "broker_id"}

# Always used with .fullmatch(): "$" would let a trailing newline through, .fullmatch() does not.
_ID = re.compile(r"[A-Za-z0-9-]{1,64}")
_HOSTNAME = re.compile(r"(?=.{4,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}")
_BROKER_ID = re.compile(r"[a-z0-9_]{1,64}")
_CHROME_EXTENSION_ID = re.compile(r"[a-p]{32}")
# Reply text is a broker id, a state word or an error code. Nothing else fits, so a name, an
# address or a sentence cannot ride along in a reply.
_REPLY_WORD = re.compile(r"[a-z0-9_]{1,64}")
# What a handler may add to a reply, per message type ("error" too, when ok is false).
_REPLY_FIELDS = {"site_check": ("broker_id", "listing_state", "stub"),
                 "start_removal": ("accepted",)}
_LENGTH = struct.Struct("=I")

Handler = Callable[[str], dict[str, Any]]


class FramingError(Exception):
    """The byte stream is not a valid native message. The connection must be closed."""


# ------------------------------------------------------------------------------------ framing

def encode_message(message: dict[str, Any]) -> bytes:
    """One message as bytes: length prefix + compact UTF-8 JSON."""
    body = json.dumps(message, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(body) > MAX_REPLY_BYTES:
        raise FramingError("message too large")
    return _LENGTH.pack(len(body)) + body


def write_message(stream: BinaryIO, message: dict[str, Any]) -> None:
    stream.write(encode_message(message))
    stream.flush()


def _read_exact(stream: BinaryIO, count: int) -> bytes:
    chunks = []
    while count:
        chunk = stream.read(count)
        if not chunk:
            break
        chunks.append(chunk)
        count -= len(chunk)
    return b"".join(chunks)


def _nested_too_deep(text: str) -> bool:
    """True when the JSON text opens more than MAX_JSON_DEPTH arrays/objects inside each other.

    A plain scan, no recursion: brackets inside strings do not count. Text that is not JSON at
    all may be miscounted, which does not matter: the parser refuses it next.
    """
    depth = 0
    in_string = escaped = False
    for ch in text:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                return True
        elif ch in "]}":
            depth -= 1
    return False


def read_message(stream: BinaryIO) -> Any | None:
    """Read one message. Returns None at a clean end of input (the browser closed the pipe).

    Raises FramingError for a short read, an oversized message, bytes that are not JSON or JSON
    nested more than MAX_JSON_DEPTH levels. The error text never includes the bytes.
    """
    header = _read_exact(stream, _LENGTH.size)
    if not header:
        return None
    if len(header) < _LENGTH.size:
        raise FramingError("short length prefix")
    (length,) = _LENGTH.unpack(header)
    if length > MAX_REQUEST_BYTES:
        raise FramingError("message too large")
    body = _read_exact(stream, length)
    if len(body) < length:
        raise FramingError("short message body")
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        raise FramingError("message is not UTF-8 JSON") from None
    if _nested_too_deep(text):
        raise FramingError("message is nested too deeply")
    try:
        return json.loads(text)
    except (ValueError, RecursionError):   # RecursionError: belt and braces behind the scan
        raise FramingError("message is not UTF-8 JSON") from None


# ----------------------------------------------------------------------------------- messages

def _reply(request_id: str, msg_type: str, ok: bool, **fields: Any) -> dict[str, Any]:
    return {"v": PROTOCOL_VERSION, "id": request_id, "type": msg_type, "ok": ok, **fields}


def _error(request_id: str, msg_type: str, code: str) -> dict[str, Any]:
    return _reply(request_id, msg_type, False, error=code)


def _site_check_stub(hostname: str) -> dict[str, Any]:
    """STUB. Real version: registry lookup + the stored listing state for the default person."""
    return {"ok": True, "broker_id": None, "listing_state": "unknown", "stub": True}


def _start_removal_stub(broker_id: str) -> dict[str, Any]:
    """STUB. Real version: hand the broker id to the engine, which applies every usual rule
    (consent, confirmed matches only, data minimisation, no CAPTCHA solving)."""
    return {"ok": False, "error": "not_implemented"}


def _envelope_ids(message: Any) -> tuple[str, str]:
    """(id, type) of a request when they are well formed, "" for each one that is not."""
    if not isinstance(message, dict):
        return "", ""
    raw_id, raw_type = message.get("id"), message.get("type")
    request_id = raw_id if isinstance(raw_id, str) and _ID.fullmatch(raw_id) else ""
    msg_type = raw_type if isinstance(raw_type, str) and raw_type in MESSAGE_TYPES else ""
    return request_id, msg_type


def _plain(value: Any) -> bool:
    """A reply value may be null, true/false or one short lower-case word."""
    return (value is None or isinstance(value, bool)
            or (isinstance(value, str) and _REPLY_WORD.fullmatch(value) is not None))


def _handler_reply(request_id: str, msg_type: str, fields: dict[Any, Any]) -> dict[str, Any]:
    """Build the reply from what a handler returned, keeping only the fields on the list.

    The envelope is ours. Every other key, and every value that is not null, true/false or a
    short word, is dropped without comment, so a handler cannot pass anything else through.
    """
    ok = fields.get("ok") is True
    kept = {key: fields[key] for key in _REPLY_FIELDS[msg_type]
            if key in fields and _plain(fields[key])}
    if not ok:
        error = fields.get("error")
        kept["error"] = (error if isinstance(error, str) and _REPLY_WORD.fullmatch(error)
                         else "internal_error")
    return _reply(request_id, msg_type, ok, **kept)


def handle_message(message: Any, *, site_check: Handler = _site_check_stub,
                   start_removal: Handler = _start_removal_stub) -> dict[str, Any]:
    """Answer one request envelope. Never raises; a bad request gets ``ok: false``.

    ``site_check`` and ``start_removal`` can be replaced (tests, and later the real app code).
    """
    if not isinstance(message, dict):
        return _error("", "", "bad_request")
    request_id, msg_type = _envelope_ids(message)
    if not request_id:
        return _error("", msg_type, "bad_request")
    version = message.get("v")
    if isinstance(version, bool) or not isinstance(version, int):
        return _error(request_id, msg_type, "bad_request")
    if version != PROTOCOL_VERSION:
        return _error(request_id, msg_type, "unsupported_version")
    if not msg_type:
        return _error(request_id, "", "unknown_type")
    extra = _EXTRA_FIELD[msg_type]
    allowed = {"v", "type", "id"} | ({extra} if extra else set())
    if set(message) - allowed:
        return _error(request_id, msg_type, "bad_request")   # no room for anything else

    if msg_type == "ping":
        return _reply(request_id, msg_type, True, pong=True)
    if msg_type == "status":
        return _reply(request_id, msg_type, True, connected=True, app_version=__version__)
    value = message.get(extra)
    pattern = _HOSTNAME if msg_type == "site_check" else _BROKER_ID
    if not isinstance(value, str) or not pattern.fullmatch(value):
        return _error(request_id, msg_type, "bad_request")
    handler = site_check if msg_type == "site_check" else start_removal
    try:
        fields = dict(handler(value))
    except Exception:   # noqa: BLE001 - the reason is not passed on: it could name a person
        return _error(request_id, msg_type, "internal_error")
    return _handler_reply(request_id, msg_type, fields)


def serve(stdin: BinaryIO, stdout: BinaryIO) -> int:
    """Answer requests until the browser closes the pipe. Returns a process exit code.

    Never raises and never prints a traceback (a traceback could quote a message). A reply that
    cannot be encoded, or is too large, is replaced by a bare ``internal_error``.
    """
    while True:
        try:
            message = read_message(stdin)
        except FramingError:
            return 1   # out of step with the browser: stop, the browser starts a new host
        if message is None:
            return 0
        try:
            frame = encode_message(handle_message(message))
        except Exception:   # noqa: BLE001 - not encodable, too large, or a bug: say so, go on
            request_id, msg_type = _envelope_ids(message)
            frame = encode_message(_error(request_id, msg_type, "internal_error"))
        try:
            stdout.write(frame)
            stdout.flush()
        except OSError:
            return 1   # the browser went away in the middle of a reply


# ------------------------------------------------------------------------------ host manifest

def host_manifest(browser: str, host_path: str,
                  chrome_extension_ids: tuple[str, ...] = ()) -> dict[str, Any]:
    """The JSON file that tells a browser where this program is and who may start it.

    ``browser`` is "chromium" (Chrome and Edge) or "firefox". Nothing is written or installed
    here; the installer does that later (docs/EXTENSION.md). Same content as the templates in
    extension/native-host/.
    """
    manifest: dict[str, Any] = {
        "name": HOST_NAME,
        "description": "Free My ID: lets the Free My ID browser extension talk to the app on "
                       "this computer.",
        "path": host_path,
        "type": "stdio",
    }
    if browser == "firefox":
        manifest["allowed_extensions"] = [FIREFOX_EXTENSION_ID]
    elif browser == "chromium":
        bad = [i for i in chrome_extension_ids if not _CHROME_EXTENSION_ID.fullmatch(i)]
        if bad or not chrome_extension_ids:
            raise ValueError("chromium needs one or more 32-letter extension ids")
        manifest["allowed_origins"] = [f"chrome-extension://{i}/" for i in chrome_extension_ids]
    else:
        raise ValueError("browser must be 'chromium' or 'firefox'")
    return manifest


# ------------------------------------------------------------------------------------- caller

def allowed_chrome_ids(environ: Mapping[str, str]) -> tuple[str, ...]:
    """The built-in store ids plus any developer ids from the environment. Bad ids are dropped."""
    extra = environ.get(EXTENSION_IDS_ENV, "").split(",")
    return tuple(i for i in (*CHROME_EXTENSION_IDS, *(e.strip() for e in extra))
                 if _CHROME_EXTENSION_ID.fullmatch(i))


def caller_allowed(args: Sequence[str], chrome_ids: Sequence[str]) -> bool:
    """Was this process started by our extension? ``args`` is the command line after the program.

    Chrome and Edge: the first argument is the caller's origin, ``chrome-extension://<id>/``
    (on Windows a ``--parent-window=...`` argument follows). Firefox: the first argument is the
    path of the host manifest and the second is the add-on id. No arguments (started by hand or
    by another program) is refused.
    """
    if not args:
        return False
    if args[0].startswith("chrome-extension:"):
        return any(args[0] == f"chrome-extension://{i}/" for i in chrome_ids)
    return len(args) >= 2 and args[1] == FIREFOX_EXTENSION_ID


# --------------------------------------------------------------------------------------- main

def main(argv: Sequence[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not caller_allowed(args, allowed_chrome_ids(os.environ)):
        # A fixed sentence: what was on the command line is not repeated.
        sys.stderr.write("freemyid native host: not started by the Free My ID browser "
                         "extension, so it will not answer.\n")
        return EXIT_CALLER_REFUSED
    stdin, stdout = sys.stdin.buffer, sys.stdout.buffer
    if sys.platform == "win32":   # pragma: no cover - Windows only
        import msvcrt
        msvcrt.setmode(stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(stdout.fileno(), os.O_BINARY)
    # stdout belongs to the protocol: a stray print() anywhere would corrupt it.
    sys.stdout = sys.stderr
    return serve(stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
