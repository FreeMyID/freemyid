"""`freemyid doctor`: is this computer ready to run Free My ID? OWNER: automation-engineer.

Every check returns ok / warn / fail plus one plain fix line, and never raises. Checks are
read-only: nothing is installed, no login is attempted, and the only network traffic is a
TCP/TLS hello to the user's own mail servers (allowed by NetPolicy), skipped with
``network=False``.
"""
from __future__ import annotations

import importlib
import os
import shutil
import socket
import ssl
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from . import paths

if TYPE_CHECKING:  # pragma: no cover
    from .models import MailboxConfig, Profile

Status = Literal["ok", "warn", "fail"]
REGISTRY_WARN_DAYS = 120
NET_TIMEOUT_S = 5.0


@dataclass
class Check:
    id: str
    title: str
    status: Status
    detail: str
    fix: str = ""

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def _guard(cid: str, title: str, fn: Callable[[], Check]) -> Check:
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 - a broken check must not break the others
        return Check(cid, title, "warn", f"could not check ({type(e).__name__})",
                     "Run `freemyid doctor -v` and send the log to whoever helps you.")


# --------------------------------------------------------------------------- python


def check_python() -> Check:
    v = sys.version_info
    frozen = bool(getattr(sys, "frozen", False))
    how = "installed app (frozen build)" if frozen else f"Python at {sys.executable}"
    detail = f"Python {v.major}.{v.minor}.{v.micro}, {how}"
    if (v.major, v.minor) < (3, 12):
        return Check("python", "Python", "fail", detail,
                     "Free My ID needs Python 3.12 or newer: `pipx install --python python3.12 "
                     "freemyid`.")
    return Check("python", "Python", "ok", detail)


# --------------------------------------------------------------------------- home folder


def check_home() -> Check:
    h = paths.home()
    if not h.is_dir():
        return Check("home", "Data folder", "fail", f"{h} is missing",
                     f"Create it with `mkdir -p {h}` or set FREEMYID_HOME.")
    if not os.access(h, os.W_OK):
        return Check("home", "Data folder", "fail", f"{h} is not writable",
                     f"Make it yours again: `chown -R $USER {h}`.")
    if sys.platform != "win32":
        mode = h.stat().st_mode & 0o777
        if mode & 0o077:
            return Check("home", "Data folder", "warn",
                         f"{h} can be read by other users (mode {mode:o})",
                         f"Make it private: `chmod 700 {h}`.")
        return Check("home", "Data folder", "ok", f"{h} (private, mode {mode:o})")
    return Check("home", "Data folder", "ok", str(h))


# --------------------------------------------------------------------------- secrets


def check_secrets() -> Check:
    """Which secrets backend holds the encryption key, and can it be used right now."""
    from . import secret_backends as sb
    from .crypto import KeyUnavailable
    title = "Secrets backend"
    keychain = sb.KeyringBackend().usable()
    try:
        be = sb.select()
    except KeyUnavailable as e:
        return Check("secrets", title, "fail", str(e),
                     "Unlock or start the keychain, then consider `freemyid secrets migrate "
                     "--to passphrase`.")
    except ValueError as e:   # unknown backend name in config.yaml
        return Check("secrets", title, "fail", str(e),
                     "Fix `secrets_backend` in config.yaml (keyring, passphrase or "
                     "systemd-creds), or remove it for automatic choice.")
    extra = "" if be.name == "keyring" else (
        "; system keychain also available" if keychain else "; no system keychain")
    if be.usable():
        if be.name == "passphrase" and not os.environ.get(sb.PASSPHRASE_FILE_ENV):
            return Check("secrets", title, "warn",
                         f"passphrase, typed at a prompt{extra}",
                         f"Scheduled and headless runs can't type it: set "
                         f"{sb.PASSPHRASE_FILE_ENV} to a file only you can read (chmod 600), "
                         "or use systemd credentials.")
        if isinstance(be, sb.KeyringBackend):
            entry = be.entry_status()
            if entry == "shared":
                return Check("secrets", title, "warn",
                             "keyring: this data folder still uses the keychain entry it "
                             "shares with the main Free My ID folder, so wiping the main "
                             "folder would also lock this one",
                             "Give this folder its own key: `freemyid secrets migrate --to "
                             "keyring` (keeps the keychain) or `freemyid secrets migrate --to "
                             "passphrase` (key protected by a passphrase, kept in this folder).")
            if entry == "unreadable":
                return Check("secrets", title, "warn",
                             "keyring: this folder's saved data could not be read just now, "
                             "so the key could not be checked",
                             "Close other Free My ID windows and try again in a minute. If it "
                             "keeps happening, check that you can open this data folder.")
            if entry == "lost":
                from .crypto import KEY_RECOVERY_HELP
                return Check("secrets", title, "fail",
                             "keyring: no key in the keychain opens this folder's saved data",
                             KEY_RECOVERY_HELP)
        return Check("secrets", title, "ok", f"{be.name}{extra}")
    fixes = {
        "keyring": "Install and unlock a keychain (GNOME Keyring or KWallet), or run "
                   "`freemyid secrets migrate --to passphrase`.",
        "passphrase": f"Set {sb.PASSPHRASE_FILE_ENV} to a file only you can read (chmod 600), "
                      "or run Free My ID in a terminal.",
        "systemd-creds": f"Add LoadCredential={sb.CRED_NAME}:<path> to the service.",
    }
    return Check("secrets", title, "fail", f"{be.name} is selected but not usable here{extra}",
                 fixes.get(be.name, "Run `freemyid secrets status`."))


# --------------------------------------------------------------------------- data store


def check_store(out: dict[str, Any]) -> Check:
    """Opens the encrypted database if it exists; puts the profiles in out['profiles']."""
    if not paths.db_path().exists():
        return Check("store", "Saved people", "warn", "nobody is set up yet",
                     "Run `freemyid setup` (or `freemyid setup --from config.yaml`).")
    from .consent import consent_ok
    from .crypto import KeyUnavailable
    from .storage import Store
    try:
        st = Store()
    except KeyUnavailable as e:
        return Check("store", "Saved people", "fail", f"cannot unlock the data ({e})",
                     "Unlock your keychain, or restore the key; see the Secrets check.")
    try:
        profiles = st.list_profiles()
        ok = sum(1 for p in profiles if consent_ok(p, st)[0])
    finally:
        st.close()
    out["profiles"] = profiles
    if not profiles:
        return Check("store", "Saved people", "warn", "nobody is set up yet",
                     "Run `freemyid setup` (or `freemyid setup --from config.yaml`).")
    if ok < len(profiles):
        return Check("store", "Saved people", "warn",
                     f"{len(profiles)} saved, {len(profiles) - ok} without valid permission",
                     "Open Free My ID and give permission again (`freemyid profile list`).")
    return Check("store", "Saved people", "ok", f"{len(profiles)} saved, all with permission")


# --------------------------------------------------------------------------- browser


def playwright_browsers_dir() -> Path:
    env = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if env and env != "0":
        return Path(env)
    if env == "0":
        try:
            import playwright
            return Path(playwright.__file__).parent / "driver" / "package" / ".local-browsers"
        except ImportError:
            pass
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ms-playwright"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "ms-playwright"
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ms-playwright"


_CHANNEL_PATHS: dict[str, dict[str, list[str]]] = {
    "chrome": {
        "linux": ["google-chrome", "google-chrome-stable", "/opt/google/chrome/chrome"],
        "darwin": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"],
        "win32": [r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
                  r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
                  r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"],
    },
    "msedge": {
        "linux": ["microsoft-edge", "microsoft-edge-stable", "/opt/microsoft/msedge/msedge"],
        "darwin": ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"],
        "win32": [r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
                  r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"],
    },
}


def system_browser(channel: str | None) -> str | None:
    if not channel:
        return None
    plat = "linux" if sys.platform.startswith("linux") else sys.platform
    for cand in _CHANNEL_PATHS.get(channel, {}).get(plat, []):
        c = os.path.expandvars(cand)
        if os.sep in c or "/" in c:
            if Path(c).is_file():
                return c
        elif shutil.which(c):
            return shutil.which(c)
    return None


def check_browser() -> Check:
    from . import config as cfgmod
    cfg = cfgmod.load()
    title = "Browser for automatic removals"
    if not getattr(cfg, "browser_automation", True):
        return Check("browser", title, "ok", "automatic tier is turned off (email and "
                     "assisted removals still work)")
    try:
        importlib.import_module("playwright")
    except ImportError:
        return Check("browser", title, "warn", "Playwright is not installed",
                     "`pipx inject freemyid playwright` (or reinstall Free My ID), then "
                     "`playwright install chromium`.")
    exe = os.environ.get("FREEMYID_BROWSER_EXECUTABLE")
    if exe:
        if Path(exe).is_file():
            return Check("browser", title, "ok", f"FREEMYID_BROWSER_EXECUTABLE ({exe})")
        return Check("browser", title, "fail", f"FREEMYID_BROWSER_EXECUTABLE points to a "
                     f"missing file ({exe})", "Fix or unset FREEMYID_BROWSER_EXECUTABLE.")
    channels = (["msedge"] if sys.platform == "win32" else []) + [cfg.browser_channel or ""]
    for ch in dict.fromkeys(c for c in channels if c):
        if system_browser(ch):
            return Check("browser", title, "ok", f"system browser ({ch})")
    d = playwright_browsers_dir()
    found = sorted(d.glob("chromium-*")) + sorted(d.glob("chromium_headless_shell-*")) \
        if d.is_dir() else []
    if found:
        return Check("browser", title, "ok", f"Playwright Chromium ({found[-1].name})")
    return Check("browser", title, "warn", "no Chrome, Edge or Playwright Chromium found",
                 "Run `playwright install chromium` (email and assisted removals work "
                 "without it).")


# --------------------------------------------------------------------------- scheduler


def check_scheduler() -> Check:
    from . import scheduler
    title = "Background checks"
    try:
        detail = scheduler.status()
    except Exception as e:  # noqa: BLE001
        return Check("scheduler", title, "warn", f"could not read status ({type(e).__name__})",
                     "Run `freemyid schedule install`.")
    low = detail.lower()
    if "not supported" in low:
        return Check("scheduler", title, "warn", detail,
                     "Use cron or a container scheduler to run `freemyid run --headless`.")
    if "not installed" in low:
        return Check("scheduler", title, "warn", "not installed",
                     "Run `freemyid schedule install` (or run `freemyid run --headless` from "
                     "cron/systemd yourself).")
    return Check("scheduler", title, "ok", detail)


# --------------------------------------------------------------------------- mailbox


def _is_loopback(host: str) -> bool:
    return host in ("localhost", "127.0.0.1", "::1")


def probe(host: str, port: int, tls: bool, timeout: float = NET_TIMEOUT_S) -> str | None:
    """TCP connect (and a TLS handshake when `tls`). None if fine, else a short reason.

    No login: nothing but the TLS hello is sent.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            if tls:
                ctx = ssl.create_default_context()
                with ctx.wrap_socket(s, server_hostname=host):
                    pass
    except ssl.SSLError as e:
        return f"TLS failed ({type(e).__name__})"
    except (OSError, RuntimeError) as e:
        return f"cannot connect ({type(e).__name__})"
    return None


def _mailbox_targets(mb: MailboxConfig) -> list[tuple[str, str, int, bool]]:
    imap_tls = mb.imap_ssl and not _is_loopback(mb.imap_host)
    smtp_tls = (not mb.smtp_starttls and mb.smtp_port == 465
                and not _is_loopback(mb.smtp_host))
    return [("incoming", mb.imap_host, mb.imap_port, imap_tls),
            ("outgoing", mb.smtp_host, mb.smtp_port, smtp_tls)]


def check_mailboxes(profiles: list[Profile] | None, network: bool = True,
                    prober: Callable[[str, int, bool], str | None] | None = None) -> Check:
    title = "Removal mailbox"
    with_mb = [p for p in (profiles or []) if p.mailbox]
    if not with_mb:
        return Check("mailbox", title, "warn", "no removal mailbox set up",
                     "Add one with `freemyid profile edit <name>` so removal emails can be "
                     "sent and replies read.")
    if not network:
        return Check("mailbox", title, "ok", f"{len(with_mb)} configured (not contacted: "
                     "--offline)")
    from .netpolicy import NetPolicy
    pol = NetPolicy(None, with_mb, allow_loopback=True)
    prober = prober or probe
    problems: list[str] = []
    for p in with_mb:
        assert p.mailbox is not None
        for which, host, port, tls in _mailbox_targets(p.mailbox):
            if not pol.is_allowed(host):
                problems.append(f"{p.label}: {which} server not allowed")
                continue
            why = prober(host, port, tls)
            if why:
                problems.append(f"{p.label}: {which} {host}:{port} {why}")
    if problems:
        return Check("mailbox", title, "fail", "; ".join(problems),
                     "Check the internet connection and the mail server names "
                     "(`freemyid profile edit <name>`); for Proton, start Proton Mail Bridge.")
    return Check("mailbox", title, "ok", f"{len(with_mb)} reachable (no login attempted)")


# --------------------------------------------------------------------------- registry


def check_registry(today: date | None = None) -> Check:
    from . import config as cfgmod
    from . import registry as regmod
    title = "Broker list"
    reg = regmod.load_registry()
    age = ((today or date.today()) - reg.updated).days
    detail = (f"{regmod.registry_source()} list, version {reg.version}, "
              f"{len(reg.brokers)} brokers, updated {age} day(s) ago")
    fix = ("Run `freemyid registry update`." if cfgmod.load().registry_url else
           "Install the latest Free My ID version to get the newest broker list.")
    if regmod.load_warnings:
        return Check("registry", title, "warn", detail + "; " + "; ".join(regmod.load_warnings),
                     fix)
    if age > REGISTRY_WARN_DAYS:
        return Check("registry", title, "warn", detail, fix)
    return Check("registry", title, "ok", detail)


# --------------------------------------------------------------------------- all


def run_checks(network: bool = True,
               prober: Callable[[str, int, bool], str | None] | None = None) -> list[Check]:
    box: dict[str, Any] = {}
    checks = [
        _guard("python", "Python", check_python),
        _guard("home", "Data folder", check_home),
        _guard("secrets", "Secrets backend", check_secrets),
        _guard("store", "Saved people", lambda: check_store(box)),
        _guard("browser", "Browser for automatic removals", check_browser),
        _guard("scheduler", "Background checks", check_scheduler),
        _guard("mailbox", "Removal mailbox",
               lambda: check_mailboxes(box.get("profiles"), network, prober)),
        _guard("registry", "Broker list", check_registry),
    ]
    return checks


def doc(checks: list[Check]) -> dict[str, Any]:
    counts = {s: sum(1 for c in checks if c.status == s) for s in ("ok", "warn", "fail")}
    return {"schema": "doctor/1", "ok": counts["fail"] == 0, "counts": counts,
            "checks": [c.as_dict() for c in checks]}
