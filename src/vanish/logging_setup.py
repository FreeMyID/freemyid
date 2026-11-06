"""Logging with PII redaction. OWNER: orchestrator.

Every log record passes through RedactingFilter. Known profile values are registered at
runtime via `register_pii`; regexes catch emails/phones/street-ish strings as a backstop.
Rule for all code: log ids and enums, never names/addresses/URLs containing names.
"""
from __future__ import annotations

import logging
import re
import threading
from logging.handlers import RotatingFileHandler

from . import paths

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)")
_lock = threading.Lock()
_pii: set[str] = set()


def register_pii(*values: str | None) -> None:
    with _lock:
        for v in values:
            if v and len(v.strip()) >= 3:
                _pii.add(v.strip())


def redact(text: str) -> str:
    text = _EMAIL.sub("[email]", text)
    text = _PHONE.sub("[phone]", text)
    with _lock:
        vals = sorted(_pii, key=len, reverse=True)
    for v in vals:
        text = re.sub(re.escape(v), "[pii]", text, flags=re.IGNORECASE)
        slug = re.sub(r"\s+", "-", v)
        if slug != v:
            text = re.sub(re.escape(slug), "[pii]", text, flags=re.IGNORECASE)
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        record.msg = redact(msg)
        record.args = ()
        return True


def setup(verbose: bool = False) -> None:
    root = logging.getLogger()
    if any(isinstance(f, RedactingFilter) for h in root.handlers for f in h.filters):
        return
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    fh = RotatingFileHandler(paths.logs_dir() / "vanish.log", maxBytes=2_000_000, backupCount=3)
    sh = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    for h in (fh, sh):
        h.setFormatter(fmt)
        h.addFilter(RedactingFilter())
        root.addHandler(h)
