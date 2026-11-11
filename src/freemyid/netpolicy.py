"""Network allowlist. OWNER: orchestrator.

The ONLY hosts Free My ID may contact: broker domains from the registry, the profile's own
mail servers, the configured registry hosts, and user-approved extras. The engine must call
`is_allowed` for every browser request (Playwright route) and before any httpx/SMTP/IMAP.

Loopback (localhost, 127.0.0.1, ::1) is NOT allowed by default: broker-page JS in the
engine browser must never reach the local wizard. Callers that legitimately need it (the
wizard, tests) opt in with `NetPolicy(..., allow_loopback=True)` or `policy.with_loopback()`.
A profile's own mailbox host (e.g. Proton Bridge on 127.0.0.1) is still allowed for mail,
but `for_broker` never hands loopback to a browser run unless loopback was opted in.
"""
from __future__ import annotations

import copy
import unicodedata
from urllib.parse import urlsplit

from . import config
from .models import Profile, Registry

LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def _norm(host: str) -> str:
    return host.strip().lower().rstrip(".").strip("[]")


def _host_ok(host: str, allowed: set[str]) -> bool:
    host = _norm(host)
    return bool(host) and any(host == a or host.endswith("." + a) for a in allowed)


def _is_loopback(host: str) -> bool:
    h = _norm(host)
    return h in LOOPBACK_HOSTS or h.endswith(".localhost") or h.startswith("127.")


def _unsafe_char(c: str) -> bool:
    """Whitespace, control, or an invisible/unassigned code point (Cf format chars such as
    U+200B zero-width space or U+200E LRM, private use, unassigned): any of these can make a
    host look like an allowed broker while naming another one."""
    return (c.isspace() or ord(c) < 0x20 or ord(c) == 0x7F
            or unicodedata.category(c) in {"Cf", "Co", "Cn", "Cs"})


def host_of(url_or_host: str) -> str | None:
    """Hostname of a URL (or a bare host); None if it is unsafe or unparsable.

    Rejects backslashes (urlsplit reads `https://evil.com\\@broker.com` as broker.com,
    browsers read it as evil.com), whitespace and control characters.
    """
    s = url_or_host
    if not s or "\\" in s or any(_unsafe_char(c) for c in s):
        return None
    if "://" in s:
        try:
            host = urlsplit(s).hostname
        except ValueError:
            return None
    else:
        host = s
    return _norm(host) if host else None


class NetPolicy:
    def __init__(self, registry: Registry | None, profiles: list[Profile] | None = None,
                 *, allow_loopback: bool = False) -> None:
        cfg = config.load()
        self.allow_loopback = allow_loopback
        self.allowed: set[str] = set()
        for b in registry.brokers if registry else []:
            self.allowed.update(_norm(d) for d in b.domains)
            self.allowed.update(_norm(d) for d in b.confirmation_domains)
        for p in profiles or []:
            if p.mailbox:
                self.allowed.update({_norm(p.mailbox.imap_host), _norm(p.mailbox.smtp_host)})
        for u in (cfg.registry_url, cfg.registry_sha256_url):
            if u:
                self.allowed.add(host_of(u) or "")
        self.allowed.update(_norm(h) for h in cfg.extra_allowed_hosts)
        if allow_loopback:
            self.allowed.update(LOOPBACK_HOSTS)
        self.allowed.discard("")

    def with_loopback(self) -> NetPolicy:
        """Copy of this policy that also allows localhost/127.0.0.1/::1 (wizard, tests)."""
        other = copy.copy(self)
        other.allowed = set(self.allowed) | LOOPBACK_HOSTS
        other.allow_loopback = True
        return other

    def is_allowed(self, url_or_host: str) -> bool:
        host = host_of(url_or_host)
        return bool(host) and _host_ok(str(host), self.allowed)

    def for_broker(self, broker_domains: list[str], extra: list[str] | None = None) -> set[str]:
        """Narrow allowlist for a single broker run: (broker + extras) ∩ global allowlist.

        Hosts not covered by the global allowlist are dropped, and loopback is dropped
        unless this policy opted in to it.
        """
        out: set[str] = set()
        for d in [*broker_domains, *(extra or [])]:
            h = host_of(d)
            if not h or not _host_ok(h, self.allowed):
                continue
            if _is_loopback(h) and not self.allow_loopback:
                continue
            out.add(h)
        return out


# --------------------------------------------------------------------------- CAPTCHA frames
# SEC-36. The human-in-the-loop windows (D9 "Fill it in for me", D10 listing finder) ask the
# person to tick the site's "I'm not a robot" box. That box is served by a CAPTCHA provider,
# not the broker. These hosts are allowed ONLY in those headed windows, ONLY as embedded
# sub-resources / sub-frames (never a main-frame navigation), and only https. Free My ID never
# reads, solves or automates them; it just stops blocking the widget the person clicks.
CAPTCHA_HOSTS: dict[str, tuple[str, ...]] = {
    # host (exact or subdomain)  -> allowed path prefixes ("" = any path)
    "www.google.com": ("/recaptcha/",),
    "www.gstatic.com": ("/recaptcha/",),
    "www.recaptcha.net": ("/recaptcha/",),
    "hcaptcha.com": ("",),
    "challenges.cloudflare.com": ("",),
}


def captcha_subresource_allowed(url: str, *, is_main_frame_navigation: bool) -> bool:
    """True if `url` is a CAPTCHA widget resource a headed fill/finder window may load."""
    if is_main_frame_navigation:
        return False
    host = host_of(url)
    if not host:
        return False
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    if parts.scheme != "https" or parts.username or parts.password or parts.port not in (
            None, 443):
        return False
    path = parts.path or "/"
    for h, prefixes in CAPTCHA_HOSTS.items():
        if host == h or (h == "hcaptcha.com" and host.endswith(".hcaptcha.com")):
            return any(path.startswith(p) for p in prefixes)
    return False


def captcha_hosts() -> set[str]:
    """Hostnames to add to the DNS/resolver allowlist of a headed fill/finder window."""
    return set(CAPTCHA_HOSTS) | {"js.hcaptcha.com", "newassets.hcaptcha.com",
                                 "api.hcaptcha.com", "imgs.hcaptcha.com"}
