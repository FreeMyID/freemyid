"""Network allowlist. OWNER: orchestrator.

The ONLY hosts Vanish may contact: broker domains from the registry, the profile's own
mail servers, the configured registry host, and user-approved extras. The engine must call
`is_allowed` for every browser request (Playwright route) and before any httpx/SMTP/IMAP.
"""
from __future__ import annotations

from urllib.parse import urlsplit

from . import config
from .models import Profile, Registry


def _host_ok(host: str, allowed: set[str]) -> bool:
    host = host.lower().rstrip(".")
    return any(host == a or host.endswith("." + a) for a in allowed)


class NetPolicy:
    def __init__(self, registry: Registry, profiles: list[Profile] | None = None) -> None:
        cfg = config.load()
        self.allowed: set[str] = set()
        for b in registry.brokers:
            self.allowed.update(d.lower() for d in b.domains)
            self.allowed.update(d.lower() for d in b.confirmation_domains)
        for p in profiles or []:
            if p.mailbox:
                self.allowed.update({p.mailbox.imap_host.lower(), p.mailbox.smtp_host.lower()})
        if cfg.registry_url:
            self.allowed.add((urlsplit(cfg.registry_url).hostname or "").lower())
        self.allowed.update(h.lower() for h in cfg.extra_allowed_hosts)
        self.allowed.update({"localhost", "127.0.0.1"})
        self.allowed.discard("")

    def is_allowed(self, url_or_host: str) -> bool:
        host = urlsplit(url_or_host).hostname if "://" in url_or_host else url_or_host
        return bool(host) and _host_ok(host, self.allowed)

    def for_broker(self, broker_domains: list[str], extra: list[str] | None = None) -> set[str]:
        """Narrow allowlist for a single broker run (broker + its confirmation domains)."""
        return {d.lower() for d in [*broker_domains, *(extra or [])]}
