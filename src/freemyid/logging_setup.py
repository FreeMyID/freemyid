"""Logging with PII redaction. OWNER: orchestrator.

Every log record passes through RedactingFilter, including tracebacks (exc_info) and
stack_info. Known profile values are registered at runtime via `register_pii` /
`register_profile` (Store does this whenever it loads a profile) and are redacted in
their common encodings: any separator between words (space, `+`, `%20`, `_`, `-`, `.`),
URL-encoded forms, case-insensitive. A registered DOB is redacted in ISO and US formats.
Regexes catch emails, phones, ISO/US calendar dates (not timestamps) and street addresses as a backstop.
Rule for all code: log ids and enums, never names/addresses/URLs containing names.
"""
from __future__ import annotations

import logging
import re
import threading
from datetime import date
from logging.handlers import RotatingFileHandler
from typing import Any
from urllib.parse import quote, quote_plus

from . import paths

_EMAIL = re.compile(r"[\w.+-]+(?:@|%40)[\w-]+\.[\w.-]+", re.IGNORECASE)
_PHONE = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)")
_US_DATE = re.compile(r"(?<!\d)(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}(?!\d)")
# ISO calendar dates (not timestamps: a following "T12:" / " 12:" time part is left alone).
_ISO_DATE = re.compile(
    r"(?<![\d-])(?:19|20)\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])(?![\d-])(?![T ]\d{2}:)"
)
_STREET = re.compile(
    r"(?<!\w)\d{1,6}(?:\s+|\+|%20)(?:[A-Za-z0-9.'#-]+(?:\s+|\+|%20)){0,4}"
    r"(?:street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|lane|ln|court|ct|way|place|pl|"
    r"terrace|ter|circle|cir|parkway|pkwy|highway|hwy|trail|trl|square|sq)\b\.?",
    re.IGNORECASE,
)
_SEP = r"(?:[\s+_.\-]|%20|%2[bB])+"   # between words of a registered value
_MIN_LEN = 2          # shorter values (initials) are not redactable without destroying logs
_SUBSTRING_LEN = 4    # values shorter than this, or all-digit, match on word boundaries only

_lock = threading.Lock()
_pii: set[str] = set()
_cache: tuple[frozenset[str], list[re.Pattern[str]]] = (frozenset(), [])  # compiled patterns


def _date_forms(d: date) -> list[str]:
    m, dd, y = d.month, d.day, d.year
    return [
        d.isoformat(), f"{y}/{m:02d}/{dd:02d}", f"{y}{m:02d}{dd:02d}",
        f"{m:02d}/{dd:02d}/{y}", f"{m}/{dd}/{y}", f"{m:02d}-{dd:02d}-{y}", f"{m}-{dd}-{y}",
        f"{m:02d}/{dd:02d}/{y % 100:02d}", f"{m}/{dd}/{y % 100:02d}",
    ]


def register_pii(*values: str | date | None) -> None:
    """Register literal PII values (names, streets, cities, zips, emails, phones, DOB)."""
    with _lock:
        for v in values:
            if isinstance(v, date):
                _pii.update(_date_forms(v))
            elif isinstance(v, str) and len(v.strip()) >= _MIN_LEN:
                _pii.add(v.strip())


def register_profile(profile: Any) -> None:
    """Register every PII-bearing field of a models.Profile (duck-typed; no models import)."""
    vals: list[str | date | None] = [getattr(profile, "label", None)]
    for n in [getattr(profile, "name", None), *getattr(profile, "previous_names", [])]:
        if n is None:
            continue
        parts = [n.first, n.middle, n.last, n.suffix]
        vals += parts
        vals += [" ".join(p for p in parts if p), f"{n.first} {n.last}", f"{n.last} {n.first}"]
    vals += getattr(profile, "nicknames", [])
    for a in getattr(profile, "addresses", []):
        vals += [a.street, a.city, a.zip]
    vals += [getattr(profile, "dob", None)]
    vals += getattr(profile, "phones", [])
    vals += getattr(profile, "emails", [])
    vals += getattr(profile, "relatives", [])
    consent = getattr(profile, "consent", None)
    if consent is not None:
        vals.append(getattr(consent, "attested_by", None))
    mb = getattr(profile, "mailbox", None)
    if mb is not None:
        vals += [mb.address, mb.username]
    register_pii(*vals)


def _pattern_for(v: str) -> str:
    words = [w for w in re.split(r"\s+", v) if w]
    flex = _SEP.join(re.escape(w) for w in words)
    alts = {flex, re.escape(quote(v, safe="")), re.escape(quote_plus(v, safe=""))}
    body = "(?:" + "|".join(sorted(alts, key=len, reverse=True)) + ")"
    if len(v) < _SUBSTRING_LEN or v.replace("-", "").replace(" ", "").isdigit():
        return r"(?<![A-Za-z0-9])" + body + r"(?![A-Za-z0-9])"
    return body


def _compiled() -> list[re.Pattern[str]]:
    global _cache
    with _lock:
        key = frozenset(_pii)
        if key != _cache[0]:
            vals = sorted(key, key=len, reverse=True)
            _cache = (key, [re.compile(_pattern_for(v), re.IGNORECASE) for v in vals])
        return _cache[1]


def redact(text: str) -> str:
    text = _EMAIL.sub("[email]", text)
    for pat in _compiled():
        text = pat.sub("[pii]", text)
    text = _PHONE.sub("[phone]", text)
    text = _US_DATE.sub("[date]", text)
    text = _ISO_DATE.sub("[date]", text)
    text = _STREET.sub("[street]", text)
    return text


_FMT = logging.Formatter()


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:  # noqa: BLE001  bad format args: never let them through unredacted
            msg = f"{record.msg!s} {record.args!r}"
        record.msg = redact(msg)
        record.args = ()
        if record.exc_info:
            record.exc_text = _FMT.formatException(record.exc_info)
            record.exc_info = None
        if record.exc_text:
            record.exc_text = redact(record.exc_text)
        if record.stack_info:
            record.stack_info = redact(record.stack_info)
        return True


def setup(verbose: bool = False) -> None:
    root = logging.getLogger()
    if any(isinstance(f, RedactingFilter) for h in root.handlers for f in h.filters):
        return
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    fh = RotatingFileHandler(paths.logs_dir() / "freemyid.log", maxBytes=2_000_000, backupCount=3)
    sh = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    for h in (fh, sh):
        h.setFormatter(fmt)
        h.addFilter(RedactingFilter())
        root.addHandler(h)
