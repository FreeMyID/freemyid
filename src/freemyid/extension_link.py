"""The link between the Free My ID app and its browser extension (docs/EXTENSION.md).

The browser starts the native host (`freemyid.native_host`) once per message. That process holds
no database key and no personal details, so everything it needs lives in a few small files in
`paths.extension_dir()`, all PII-free:

    pairing.json   which extension installs the person connected to this app (browser origin
                   strings only), plus one pending six-digit pairing code
    status.json    broker id -> the most urgent listing state across the people on this
                   computer, and hostname -> broker id from the registry in use
    inbox/         "Remove me" requests from the extension: a broker id and a time, nothing else
    bridge.json    while the app window is open: the port and secret of the local bridge

The one thing that needs personal details is "Fill in the form": the values come from the
encrypted store, so only the running app can answer. The host relays that one request over the
bridge (an HTTP server on 127.0.0.1 with its own random secret, not the dashboard's), and the
app decides what to fill with the same rules as "Fill it in for me" (`engine.filler`).

Pairing: the extension asks for a code (`pair_start`), shows it, and the person confirms the same
code in the app (Settings > Browser helper, or `freemyid extension pair <code>`). Until then the
host answers only `ping`, `status` and `pair_start`.
"""
from __future__ import annotations

import hmac
import http.client
import json
import logging
import os
import re
import secrets
import sys
import threading
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import Broker, Profile, Registry
    from .storage import Store

log = logging.getLogger(__name__)

PAIRING_FILE = "pairing.json"
STATUS_FILE = "status.json"
BRIDGE_FILE = "bridge.json"
INBOX_DIR = "inbox"

PAIR_CODE_TTL = timedelta(minutes=10)
MAX_PAIR_ATTEMPTS = 5          # wrong codes before the pending code is thrown away
MAX_PAIRED = 8                 # browsers / profiles one person may connect
MAX_INBOX = 50                 # removal requests waiting at most (a page cannot flood us)
MAX_BRIDGE_BODY = 128 * 1024
BRIDGE_TIMEOUT_S = 8.0

# chrome-extension://<32 letters a-p>/  (Chrome, Edge)   or   firefox:<add-on id>
ORIGIN_RE = re.compile(r"chrome-extension://[a-p]{32}/|firefox:[A-Za-z0-9@._-]{3,80}")
BROKER_ID_RE = re.compile(r"[a-z0-9_]{1,64}")
CODE_RE = re.compile(r"\d{6}")

# Most urgent first: what the banner should react to when several people share a computer.
URGENCY = ("reappeared", "found", "needs_human", "error", "awaiting_verification", "submitted",
           "confirmed", "removed", "not_found", "unknown")


# ------------------------------------------------------------------------------------ files

def _dir() -> Path:
    from . import paths
    return paths.extension_dir()


def _now(now: datetime | None) -> datetime:
    return now if now is not None else datetime.now(UTC)


def _write_private(path: Path, data: dict[str, Any]) -> None:
    """Atomic write, readable by this user only."""
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"), sort_keys=True)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _read(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def valid_origin(origin: object) -> bool:
    return isinstance(origin, str) and ORIGIN_RE.fullmatch(origin) is not None


# ---------------------------------------------------------------------------------- pairing

def _pairing() -> dict[str, Any]:
    data = _read(_dir() / PAIRING_FILE)
    paired = data.get("paired")
    data["paired"] = [p for p in paired if isinstance(p, dict) and valid_origin(p.get("origin"))] \
        if isinstance(paired, list) else []
    return data


def paired_origins() -> list[str]:
    return [p["origin"] for p in _pairing()["paired"]]


def is_paired(origin: object) -> bool:
    return valid_origin(origin) and origin in paired_origins()


def start_pairing(origin: str, now: datetime | None = None) -> str:
    """A fresh six-digit code for this extension origin. Replaces any earlier pending code."""
    if not valid_origin(origin):
        raise ValueError("not an extension origin")
    code = f"{secrets.randbelow(10 ** 6):06d}"
    data = _pairing()
    data["pending"] = {"origin": origin, "code": code, "attempts": 0,
                       "expires": (_now(now) + PAIR_CODE_TTL).isoformat()}
    _write_private(_dir() / PAIRING_FILE, data)
    return code


def pending_pairing(now: datetime | None = None) -> dict[str, Any] | None:
    """{"origin", "code", "expires"} while a code is waiting to be confirmed."""
    p = _pairing().get("pending")
    if not isinstance(p, dict) or not valid_origin(p.get("origin")):
        return None
    if not isinstance(p.get("code"), str) or not CODE_RE.fullmatch(p["code"]):
        return None
    try:
        expires = datetime.fromisoformat(str(p.get("expires")))
    except ValueError:
        return None
    if expires <= _now(now):
        return None
    return {"origin": p["origin"], "code": p["code"], "expires": expires}


def confirm_pairing(code: str, now: datetime | None = None) -> str | None:
    """The person typed (or clicked) the code shown in the browser. Returns the newly paired
    origin, or None for a wrong or expired code (after MAX_PAIR_ATTEMPTS the code is void)."""
    data = _pairing()
    pending = pending_pairing(now)
    if pending is None:
        return None
    if not (isinstance(code, str) and hmac.compare_digest(code.strip(), pending["code"])):
        raw = data.get("pending")
        stored = raw if isinstance(raw, dict) else {}
        attempts = int(stored.get("attempts", 0)) + 1
        if attempts >= MAX_PAIR_ATTEMPTS or not stored:
            data.pop("pending", None)
        else:
            stored["attempts"] = attempts
        _write_private(_dir() / PAIRING_FILE, data)
        return None
    origin = pending["origin"]
    paired = [p for p in data["paired"] if p["origin"] != origin]
    paired.append({"origin": origin, "since": _now(now).isoformat()})
    data["paired"] = paired[-MAX_PAIRED:]
    data.pop("pending", None)
    _write_private(_dir() / PAIRING_FILE, data)
    return origin


def cancel_pairing() -> None:
    data = _pairing()
    if data.pop("pending", None) is not None:
        _write_private(_dir() / PAIRING_FILE, data)


def unpair(origin: str | None = None) -> int:
    """Forget one paired origin, or all of them (None). Returns how many were removed."""
    data = _pairing()
    before = len(data["paired"])
    data["paired"] = [] if origin is None else [p for p in data["paired"]
                                                if p["origin"] != origin]
    data.pop("pending", None)
    _write_private(_dir() / PAIRING_FILE, data)
    return before - len(data["paired"])


def describe_origin(origin: str) -> str:
    """Plain words for a paired origin (no ids a person would not recognise)."""
    if origin.startswith("firefox:"):
        return "Firefox"
    return "Chrome or Edge"


# ----------------------------------------------------------------------------------- status

def _hosts_of(b: Broker) -> Iterable[str]:
    yield from (d.lower().strip(".") for d in b.domains)
    yield str(b.url.host or "").lower().strip(".")


def write_status(store: Store, registry: Registry | None, now: datetime | None = None) -> None:
    """Refresh status.json. Never raises: the app must not fail because the link did."""
    try:
        rank = {s: i for i, s in enumerate(URGENCY)}
        states: dict[str, str] = {}
        for st in store.list_statuses():
            word = st.state.value
            old = states.get(st.broker_id)
            if old is None or rank.get(word, len(URGENCY)) < rank.get(old, len(URGENCY)):
                states[st.broker_id] = word
        hosts: dict[str, str] = {}
        for b in (registry.brokers if registry is not None else []):
            for h in _hosts_of(b):
                if h and h not in hosts:
                    hosts[h] = b.id
        _write_private(_dir() / STATUS_FILE, {"schema": 1, "updated": _now(now).isoformat(),
                                               "brokers": states, "hosts": hosts})
    except Exception as e:  # noqa: BLE001
        log.warning("extension status not written: %s", type(e).__name__)


def site_state(hostname: str) -> tuple[str | None, str]:
    """(broker id or None, listing state word) for a bare hostname, from status.json."""
    data = _read(_dir() / STATUS_FILE)
    raw_hosts, raw_brokers = data.get("hosts"), data.get("brokers")
    hosts: dict[str, Any] = raw_hosts if isinstance(raw_hosts, dict) else {}
    brokers: dict[str, Any] = raw_brokers if isinstance(raw_brokers, dict) else {}
    labels = hostname.lower().strip(".").split(".")
    broker_id = None
    for i in range(len(labels) - 1):          # www.a.example.com, a.example.com, example.com
        cand = hosts.get(".".join(labels[i:]))
        if isinstance(cand, str) and BROKER_ID_RE.fullmatch(cand):
            broker_id = cand
            break
    if broker_id is None:
        return None, "unknown"
    state = brokers.get(broker_id, "unknown")
    return broker_id, state if state in URGENCY else "unknown"


# ------------------------------------------------------------------------------------ inbox

def queue_removal(broker_id: str, origin: str, now: datetime | None = None) -> bool:
    """Save a "Remove me" request from a paired extension. False when the inbox is full."""
    if not BROKER_ID_RE.fullmatch(broker_id) or not valid_origin(origin):
        return False
    box = _dir() / INBOX_DIR
    box.mkdir(exist_ok=True, mode=0o700)
    if sum(1 for _ in box.glob("*.json")) >= MAX_INBOX:
        return False
    t = _now(now)
    _write_private(box / f"{t.strftime('%Y%m%dT%H%M%S%f')}-{secrets.token_hex(4)}.json",
                   {"broker_id": broker_id, "origin": origin, "requested": t.isoformat()})
    return True


def take_inbox() -> list[str]:
    """Broker ids waiting in the inbox, oldest first, without repeats. The files are removed."""
    box = _dir() / INBOX_DIR
    out: list[str] = []
    for f in sorted(box.glob("*.json")) if box.is_dir() else []:
        bid = _read(f).get("broker_id")
        f.unlink(missing_ok=True)
        if isinstance(bid, str) and BROKER_ID_RE.fullmatch(bid) and bid not in out:
            out.append(bid)
    return out


RunFn = Callable[..., Any]


def process_inbox(store: Store, registry: Registry | None, *, dry_run: bool,
                  run: RunFn | None = None) -> list[str]:
    """Start removals the extension asked for. The engine applies every usual rule (consent,
    confirmed matches only, data minimisation, practice mode). Returns the broker ids run."""
    from .consent import consent_ok
    from .models import Actor, Event
    ids = take_inbox()
    known = {b.id for b in registry.brokers} if registry is not None else set()
    ids = [i for i in ids if i in known]
    if not ids or registry is None:
        return []
    people = [p for p in store.list_profiles() if consent_ok(p, store)[0]]
    if not people:
        log.info("extension removal requests dropped: nobody has given permission")
        return []
    for p in people:
        for bid in ids:
            store.log(Event(profile_id=p.id, broker_id=bid, actor=Actor.USER,
                            action="extension_removal_request", detail={}))
    if run is None:
        from .engine.runner import run as engine_run
        run = engine_run
    run(store, registry, people, scan_only=False, dry_run=dry_run, interactive=False,
        broker_ids=ids)
    write_status(store, registry)
    return ids


# ------------------------------------------------------------------------------------- fill

class FillRefused(Exception):
    """Why the app will not fill this form. `code` is one short word for the extension."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


CONTROL_TEXT_FIELDS = ("key", "tag", "type", "name", "id", "label", "labelledby", "aria",
                       "placeholder", "autocomplete", "title")
CONTROL_BOOL_FIELDS = ("visible", "in_captcha", "disabled", "has_value")
MAX_CONTROLS = 200
MAX_OPTIONS = 120
MAX_TEXT = 200


def parse_controls(raw: object) -> list[dict[str, Any]]:
    """The page scan as the extension sent it, reduced to exactly what `Control` reads.
    Raises FillRefused("bad_request") for anything else."""
    if not isinstance(raw, list) or len(raw) > MAX_CONTROLS:
        raise FillRefused("bad_request")
    out: list[dict[str, Any]] = []
    for c in raw:
        if not isinstance(c, dict):
            raise FillRefused("bad_request")
        allowed = {*CONTROL_TEXT_FIELDS, *CONTROL_BOOL_FIELDS, "maxlength", "option_values",
                   "option_texts"}
        if set(c) - allowed:
            raise FillRefused("bad_request")
        d: dict[str, Any] = {}
        for k in CONTROL_TEXT_FIELDS:
            v = c.get(k, "")
            if not isinstance(v, str) or len(v) > MAX_TEXT:
                raise FillRefused("bad_request")
            d[k] = v
        for k in CONTROL_BOOL_FIELDS:
            v = c.get(k, False)
            if not isinstance(v, bool):
                raise FillRefused("bad_request")
            d[k] = v
        ml = c.get("maxlength", -1)
        if isinstance(ml, bool) or not isinstance(ml, int):
            raise FillRefused("bad_request")
        d["maxlength"] = ml
        vals, texts = c.get("option_values", []), c.get("option_texts", [])
        if (not isinstance(vals, list) or not isinstance(texts, list) or len(vals) != len(texts)
                or len(vals) > MAX_OPTIONS
                or not all(isinstance(x, str) and len(x) <= MAX_TEXT for x in [*vals, *texts])):
            raise FillRefused("bad_request")
        d["options"] = [{"value": v, "text": t} for v, t in zip(vals, texts, strict=True)]
        out.append(d)
    return out


def _person_for(store: Store, broker_id: str) -> tuple[Profile, Any]:
    """Whose details go into this broker's form: the one person with a confirmed listing there,
    or the only person with permission. Several candidates: the app has to ask (refused)."""
    from .consent import consent_ok
    from .engine.fill_for_me import _confirmed_listing
    people = [p for p in store.list_profiles() if consent_ok(p, store)[0]]
    if not people:
        raise FillRefused("no_permission")
    with_listing = []
    for p in people:
        listing, _ = _confirmed_listing(store, p.id, broker_id)
        if listing is not None:
            with_listing.append((p, listing))
    if len(with_listing) == 1:
        return with_listing[0]
    if not with_listing and len(people) == 1:
        return people[0], None
    raise FillRefused("choose_person")


def plan_fill(store: Store, registry: Registry | None, broker_id: str,
              controls: object) -> dict[str, str]:
    """Control key -> value for one form on one broker's page (see `filler.fill_plan`)."""
    from .engine.filler import Control, fill_plan, plan_values
    from .models import Actor, Event
    broker = next((b for b in (registry.brokers if registry else []) if b.id == broker_id), None)
    if broker is None:
        raise FillRefused("unknown_broker")
    parsed = [Control.from_js(c) for c in parse_controls(controls)]
    profile, listing = _person_for(store, broker_id)
    plan, rep = fill_plan(parsed, plan_values(profile, broker, listing))
    store.log(Event(profile_id=profile.id, broker_id=broker_id, actor=Actor.USER,
                    action="extension_fill",
                    detail={"filled": sorted(set(rep.filled)), "withheld": sorted(set(rep.withheld)),
                            "protected": rep.protected, "unknown": rep.unknown}))
    return plan


# ----------------------------------------------------------------------------------- bridge

class Bridge:
    """The app side of the extension link, on 127.0.0.1 while the app window is open."""

    def __init__(self, store_factory: Callable[[], Store],
                 registry_loader: Callable[[], Registry | None],
                 dry_run: Callable[[], bool]) -> None:
        self.store_factory, self.registry_loader, self.dry_run = (
            store_factory, registry_loader, dry_run)
        self.token = secrets.token_urlsafe(32)
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self._inbox_lock = threading.Lock()

    @property
    def port(self) -> int:
        return self.server.server_address[1] if self.server else 0

    def start(self) -> Bridge:
        bridge = self

        class Handler(_BridgeHandler):
            owner = bridge

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       name="freemyid-extension-bridge", daemon=True)
        self.thread.start()
        _write_private(_dir() / BRIDGE_FILE, {"port": self.port, "token": self.token,
                                               "pid": os.getpid()})
        self.refresh_status()
        return self

    def stop(self) -> None:
        if self.server is None:
            return
        f = _dir() / BRIDGE_FILE
        if _read(f).get("token") == self.token:
            f.unlink(missing_ok=True)
        self.server.shutdown()
        self.server.server_close()
        self.server = None

    def refresh_status(self) -> None:
        st = self.store_factory()
        try:
            write_status(st, self.registry_loader())
        finally:
            _close(st)

    # -- handlers (run on the server's threads)

    def fill(self, body: dict[str, Any]) -> dict[str, Any]:
        bid = body.get("broker_id")
        if not isinstance(bid, str) or not BROKER_ID_RE.fullmatch(bid):
            return {"ok": False, "error": "bad_request"}
        st = self.store_factory()
        try:
            plan = plan_fill(st, self.registry_loader(), bid, body.get("controls"))
        except FillRefused as e:
            return {"ok": False, "error": e.code}
        finally:
            _close(st)
        return {"ok": True, "assignments": [{"key": k, "value": v} for k, v in plan.items()]}

    def inbox(self) -> dict[str, Any]:
        if not self._inbox_lock.acquire(blocking=False):
            return {"ok": True}          # a run for earlier requests is going; it takes these

        def job() -> None:
            st = self.store_factory()
            try:
                process_inbox(st, self.registry_loader(), dry_run=self.dry_run())
            except Exception as e:  # noqa: BLE001
                log.warning("extension removal run failed: %s", type(e).__name__)
            finally:
                _close(st)
                self._inbox_lock.release()
        threading.Thread(target=job, name="freemyid-extension-run", daemon=True).start()
        return {"ok": True}


def _close(st: Any) -> None:
    close = getattr(st, "close", None)
    if callable(close):
        close()


class _BridgeHandler(BaseHTTPRequestHandler):
    owner: Bridge
    server_version = "freemyid-bridge"
    sys_version = ""

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send(self, code: int, data: dict[str, Any]) -> None:
        body = json.dumps(data, separators=(",", ":")).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        self._send(405, {"ok": False, "error": "bad_request"})

    do_PUT = do_DELETE = do_OPTIONS = do_PATCH = do_GET

    def do_POST(self) -> None:
        o = self.owner
        # A web page cannot reach this: wrong Host (DNS rebinding), any Origin header (a page's
        # fetch always sends one), no secret, or not JSON are all refused before reading.
        if (self.headers.get("Host") != f"127.0.0.1:{o.port}" or self.headers.get("Origin")
                or self.headers.get("Content-Type") != "application/json"
                or not hmac.compare_digest(self.headers.get("Authorization", ""),
                                           f"Bearer {o.token}")):
            self._send(403, {"ok": False, "error": "not_allowed"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if not 0 < length <= MAX_BRIDGE_BODY:
            self._send(413, {"ok": False, "error": "bad_request"})
            return
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError, RecursionError):
            body = None
        if not isinstance(body, dict) or not is_paired(body.get("origin")):
            self._send(403, {"ok": False, "error": "not_paired"})
            return
        try:
            if self.path == "/v1/fill-plan":
                self._send(200, o.fill(body))
            elif self.path == "/v1/inbox":
                self._send(200, o.inbox())
            else:
                self._send(404, {"ok": False, "error": "bad_request"})
        except Exception as e:  # noqa: BLE001 - the reason could name a person: not passed on
            log.warning("extension bridge error: %s", type(e).__name__)
            self._send(500, {"ok": False, "error": "internal_error"})


def start_bridge(store_factory: Callable[[], Store],
                 registry_loader: Callable[[], Registry | None],
                 dry_run: Callable[[], bool]) -> Bridge | None:
    """Start the bridge for an open app window. Never raises (the app works without it)."""
    try:
        return Bridge(store_factory, registry_loader, dry_run).start()
    except Exception as e:  # noqa: BLE001
        log.warning("extension bridge not started: %s", type(e).__name__)
        return None


def app_is_open() -> bool:
    """True while an app window has its bridge up (bridge.json written, not yet removed)."""
    port = _read(_dir() / BRIDGE_FILE).get("port")
    return isinstance(port, int) and not isinstance(port, bool) and 0 < port < 65536


def bridge_call(path: str, payload: dict[str, Any],
                timeout: float = BRIDGE_TIMEOUT_S) -> dict[str, Any] | None:
    """Host side: ask the running app. None when the app is not open or did not answer."""
    info = _read(_dir() / BRIDGE_FILE)
    port, token = info.get("port"), info.get("token")
    if isinstance(port, bool) or not isinstance(port, int) or not 0 < port < 65536 \
            or not isinstance(token, str) or not token:
        return None
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        conn.request("POST", path, body=body, headers={
            "Host": f"127.0.0.1:{port}", "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"})
        resp = conn.getresponse()
        data = json.loads(resp.read(MAX_BRIDGE_BODY + 1).decode("utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError, http.client.HTTPException):
        return None
    finally:
        conn.close()


# ---------------------------------------------------------------- native host registration

# Same places as extension/native-host/install-locations.json (a test keeps them in step).
HOST_FILE = "org.freemyid.host.json"
MANIFEST_PATHS = {
    "darwin": {"chrome": "~/Library/Application Support/Google/Chrome/NativeMessagingHosts",
               "edge": "~/Library/Application Support/Microsoft Edge/NativeMessagingHosts",
               "firefox": "~/Library/Application Support/Mozilla/NativeMessagingHosts"},
    "linux": {"chrome": "~/.config/google-chrome/NativeMessagingHosts",
              "edge": "~/.config/microsoft-edge/NativeMessagingHosts",
              "firefox": "~/.mozilla/native-messaging-hosts"},
}
WINDOWS_KEYS = {"chrome": r"Software\Google\Chrome\NativeMessagingHosts\org.freemyid.host",
                "edge": r"Software\Microsoft\Edge\NativeMessagingHosts\org.freemyid.host",
                "firefox": r"Software\Mozilla\NativeMessagingHosts\org.freemyid.host"}
BROWSERS = ("chrome", "edge", "firefox")


def _platform() -> str:
    return "windows" if sys.platform == "win32" else (
        "darwin" if sys.platform == "darwin" else "linux")


def host_program(chrome_ids: tuple[str, ...]) -> Path:
    """The program the browser starts. A browser passes no arguments of ours, so a small
    launcher fixes the interpreter (and the developer extension ids, when there are any)."""
    d = _dir()
    frozen = Path(sys.executable).with_name(
        "freemyid-native-host.exe" if _platform() == "windows" else "freemyid-native-host")
    if getattr(sys, "frozen", False) and frozen.exists() and not chrome_ids:
        return frozen
    ids = ",".join(chrome_ids)
    if _platform() == "windows":
        p = d / "native-host.cmd"
        env = f"set FREEMYID_EXTENSION_IDS={ids}\r\n" if ids else ""
        p.write_text(f'@echo off\r\n{env}"{sys.executable}" -m freemyid.native_host %*\r\n',
                     encoding="utf-8")
    else:
        p = d / "native-host.sh"
        env = f"FREEMYID_EXTENSION_IDS='{ids}' " if ids else ""
        p.write_text(f"#!/bin/sh\n{env}exec '{sys.executable}' -m freemyid.native_host \"$@\"\n",
                     encoding="utf-8")
        p.chmod(0o700)
    return p


def register_host(chrome_ids: tuple[str, ...] = (), browsers: Iterable[str] = BROWSERS
                  ) -> dict[str, str]:
    """Tell each browser where the host is (per user, no admin). Returns browser -> where it
    was written. Chrome and Edge are skipped without an extension id (store or developer)."""
    from .native_host import CHROME_EXTENSION_IDS, host_manifest
    ids = tuple(dict.fromkeys((*CHROME_EXTENSION_IDS, *chrome_ids)))
    program = str(host_program(tuple(chrome_ids)))
    plat, out = _platform(), {}
    for browser in browsers:
        kind = "firefox" if browser == "firefox" else "chromium"
        if kind == "chromium" and not ids:
            continue
        manifest = host_manifest(kind, program, ids if kind == "chromium" else ())
        if plat == "windows":
            target = _dir() / f"org.freemyid.host.{browser}.json"
            _write_json(target, manifest)
            _set_windows_key(WINDOWS_KEYS[browser], str(target))
            out[browser] = "HKCU\\" + WINDOWS_KEYS[browser]
        else:
            target = Path(MANIFEST_PATHS[plat][browser]).expanduser() / HOST_FILE
            target.parent.mkdir(parents=True, exist_ok=True)
            _write_json(target, manifest)
            out[browser] = str(target)
    return out


def unregister_host() -> list[str]:
    """Undo `register_host`. Returns the browsers whose entry was removed."""
    plat, removed = _platform(), []
    for browser in BROWSERS:
        if plat == "windows":
            if _delete_windows_key(WINDOWS_KEYS[browser]):
                removed.append(browser)
            (_dir() / f"org.freemyid.host.{browser}.json").unlink(missing_ok=True)
        else:
            target = Path(MANIFEST_PATHS[plat][browser]).expanduser() / HOST_FILE
            if target.exists():
                target.unlink()
                removed.append(browser)
    return removed


def registered_browsers() -> list[str]:
    plat = _platform()
    if plat == "windows":
        return [b for b in BROWSERS if _get_windows_key(WINDOWS_KEYS[b])]
    return [b for b in BROWSERS
            if (Path(MANIFEST_PATHS[plat][b]).expanduser() / HOST_FILE).exists()]


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _set_windows_key(key: str, value: str) -> None:   # pragma: no cover - Windows only
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as k:   # type: ignore[attr-defined]
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, value)        # type: ignore[attr-defined]


def _get_windows_key(key: str) -> str | None:   # pragma: no cover - Windows only
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:   # type: ignore[attr-defined]
            return str(winreg.QueryValue(k, None))                 # type: ignore[attr-defined]
    except OSError:
        return None


def _delete_windows_key(key: str) -> bool:   # pragma: no cover - Windows only
    import winreg
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)   # type: ignore[attr-defined]
        return True
    except OSError:
        return False
