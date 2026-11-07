"""SMTP send + IMAP confirmation polling for a profile's dedicated removal mailbox.

* Password comes ONLY from the OS keychain (`secrets.get_mailbox_password`).
* Every host is checked with NetPolicy before connecting.
* `wait_for_confirmation` returns only https links whose host is inside the broker's
  `confirmation_domains` (or `domains` if that is empty). Mail text is data, never
  instructions: we extract URLs and nothing else.
* `FakeMailer` records sends in memory: used for dry runs, dev runs and tests.
"""
from __future__ import annotations

import asyncio
import contextlib
import email
import email.policy
import imaplib
import logging
import re
import smtplib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, parsedate_to_datetime
from html import unescape
from typing import TYPE_CHECKING

from ..models import Broker, MailboxConfig, Profile, utcnow
from ..netpolicy import host_of
from .mail_tls import TlsPinError, check_peer, client_context

# Never announce this computer's hostname (often the owner's name) in EHLO; also avoids a
# slow reverse lookup on macOS.
_EHLO_NAME = "localhost"

if TYPE_CHECKING:
    from ..netpolicy import NetPolicy

log = logging.getLogger(__name__)

_URL = re.compile(r"https://[^\s<>\"')\]]+", re.IGNORECASE)
_HREF = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_ANCHOR = re.compile(r"""<a\b[^>]*?href\s*=\s*["']([^"']+)["'][^>]*>(.*?)</a\s*>""",
                     re.IGNORECASE | re.DOTALL)
# SEC-18: links that would cancel/undo/unsubscribe (or are just boilerplate) are never clicked
_AVOID = re.compile(r"cancel|unsubscribe|opt.?in|not (you|me)|did ?n.?t (request|ask)|"
                    r"did not (request|ask)|report|preferences|privacy|terms|login|sign.?in",
                    re.IGNORECASE)
_CONFIRM = re.compile(r"confirm|verif|validate|activate|complete", re.IGNORECASE)
# A broker reply that asks for an identity document. Such mail is never auto-handled: no link
# in it is clicked and the runner opens an ID_UPLOAD to-do (Free My ID never sends ID).
_ID_REQUEST = re.compile(
    r"(government|state)[- ]issued|photo (id\b|identification)|driver'?s?[- ]licen[cs]e|"
    r"passport|(copy|scan|photo|picture|image) of (your |a )?(valid )?"
    r"(photo )?(id\b|identification|identity|license|licence)|social security (number|card)|"
    r"\bssn\b|last (4|four) digits|notari[sz]ed|utility bill|"
    r"proof of (identity|address|residency)|identity document|id document",
    re.IGNORECASE)
DATE_SLACK = timedelta(hours=1)     # broker clock skew vs. our last_submitted_at
MAX_MESSAGES = 50            # per poll; we only need recent broker mail
MAX_MESSAGE_BYTES = 2_000_000


class MailError(RuntimeError):
    """PII-free mail failure (message holds a short reason only)."""


def _host_in(host: str | None, domains: list[str]) -> bool:
    if not host:
        return False
    return any(host == d or host.endswith("." + d) for d in (x.lower() for x in domains))


def confirmation_hosts(broker: Broker) -> list[str]:
    return list(broker.confirmation_domains or broker.domains)


def build_message(mb: MailboxConfig, to: str, subject: str, body: str,
                  request_id: str) -> EmailMessage:
    """Plain-text message from the removal mailbox. Message-ID carries the request id so
    replies can be tied to a Request without any PII."""
    msg = EmailMessage()
    msg["From"] = mb.address
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=False)
    domain = mb.address.rpartition("@")[2] or "freemyid.invalid"
    msg["Message-ID"] = make_msgid(idstring=f"freemyid.{request_id}", domain=domain)
    msg.set_content(body)
    return msg


def extract_links(raw: bytes, allowed_domains: list[str]) -> list[str]:
    """Pure: https links in a raw RFC822 message whose host is inside `allowed_domains`."""
    if len(raw) > MAX_MESSAGE_BYTES:
        return []
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    texts: list[str] = []
    for part in msg.walk():
        if part.get_content_maintype() != "text":
            continue
        try:
            texts.append(part.get_content())
        except (LookupError, ValueError):
            continue
    found: list[str] = []
    text_of: dict[str, str] = {}
    for t in texts:
        for href, inner in _ANCHOR.findall(t):
            u = unescape(href).strip()
            label = " ".join(unescape(re.sub(r"<[^>]+>", " ", inner)).split())
            text_of[u] = f"{text_of.get(u, '')} {label}".strip()
        cands = [unescape(h) for h in _HREF.findall(t)] + _URL.findall(unescape(t))
        for u in cands:
            u = u.strip().rstrip(".,;")
            if not u.lower().startswith("https://"):
                continue
            h = host_of(u)
            if h and _host_in(h, allowed_domains) and u not in found:
                found.append(u)
    keep = [u for u in found if not _avoid(u, text_of.get(u, ""))]
    return rank_links(keep, text_of)


def _url_tail(u: str) -> str:
    """Path, query and fragment only (a host like privacy.broker.example is not a signal)."""
    rest = u.split("://", 1)[-1]
    i = min((rest.find(c) for c in "/?#" if c in rest), default=len(rest))
    return rest[i:]


def _avoid(u: str, text: str) -> bool:
    return bool(_AVOID.search(_url_tail(u)) or _AVOID.search(text))


def rank_links(links: list[str], text_of: dict[str, str] | None = None) -> list[str]:
    """Confirm/verify-looking links first (stable)."""
    t = text_of or {}
    return sorted(links, key=lambda u: not (_CONFIRM.search(_url_tail(u))
                                             or _CONFIRM.search(t.get(u, ""))))


def sender_domain(raw: bytes) -> str | None:
    msg = email.message_from_bytes(raw[:65536], policy=email.policy.default)
    frm = str(msg.get("From", ""))
    m = re.search(r"@([A-Za-z0-9.-]+)", frm)
    return m.group(1).lower().rstrip(".") if m else None


@dataclass
class ReplyScan:
    """What the broker's replies say, PII-free (links are confirmation URLs only)."""
    links: list[str] = field(default_factory=list)   # newest message first, ranked inside
    id_requested: bool = False      # some reply asks for an ID document -> human to-do
    messages: int = 0               # distinct broker messages considered
    duplicates: int = 0             # same Message-ID (or same bytes) seen again
    stale: int = 0                  # older than the submission this reply would answer


def message_date(raw: bytes) -> datetime | None:
    msg = email.message_from_bytes(raw[:65536], policy=email.policy.default)
    try:
        d = parsedate_to_datetime(str(msg.get("Date", "")))
    except (TypeError, ValueError, IndexError):
        return None
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def _message_key(raw: bytes) -> str:
    msg = email.message_from_bytes(raw[:65536], policy=email.policy.default)
    mid = str(msg.get("Message-ID", "")).strip()
    if mid:
        return mid
    import hashlib
    return hashlib.sha256(raw).hexdigest()


def _plain_text(raw: bytes) -> str:
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    parts: list[str] = [str(msg.get("Subject", ""))]
    for part in msg.walk():
        if part.get_content_maintype() != "text":
            continue
        try:
            parts.append(unescape(re.sub(r"<[^>]+>", " ", part.get_content())))
        except (LookupError, ValueError):
            continue
    return " ".join(" ".join(parts).split())


def asks_for_id(raw: bytes) -> bool:
    """Pure: does this message ask for an identity document (ID, licence, SSN, ...)?"""
    if len(raw) > MAX_MESSAGE_BYTES:
        return False
    return bool(_ID_REQUEST.search(_plain_text(raw)))


def scan_replies(raws: list[bytes], broker: Broker, since: datetime | None = None, *,
                 check_sender: bool = True) -> ReplyScan:
    """Pure reply matcher.

    * only mail From a broker/confirmation domain (unless check_sender=False);
    * the same message twice (Message-ID, else bytes) counts once;
    * mail dated before `since` (minus DATE_SLACK) answers an earlier request: ignored, so
      an old confirmation link is never clicked for a new submission;
    * a message that asks for ID sets id_requested and contributes no links;
    * links come newest message first (a broker that answers twice: its latest link wins).
    """
    allowed = confirmation_hosts(broker)
    out = ReplyScan()
    seen: set[str] = set()
    msgs: list[tuple[datetime | None, int, bytes]] = []
    for i, raw in enumerate(raws):
        if check_sender and not _host_in(sender_domain(raw), [*broker.domains, *allowed]):
            continue
        key = _message_key(raw)
        if key in seen:
            out.duplicates += 1
            continue
        seen.add(key)
        d = message_date(raw)
        if since is not None and d is not None:
            ref = since if since.tzinfo else since.replace(tzinfo=UTC)
            if d < ref - DATE_SLACK:
                out.stale += 1
                continue
        msgs.append((d, i, raw))
    out.messages = len(msgs)
    floor = datetime.min.replace(tzinfo=UTC)
    msgs.sort(key=lambda m: (m[0] or floor, m[1]), reverse=True)
    for _d, _i, raw in msgs:
        if asks_for_id(raw):
            out.id_requested = True
            continue
        for u in extract_links(raw, allowed):
            if u not in out.links:
                out.links.append(u)
    return out


class SmtpImapMailer:
    """Real mailer. Never used in dev/tests (they use FakeMailer)."""

    def __init__(self, netpolicy: NetPolicy, password_getter=None, timeout_s: float = 30.0,
                 poll_interval_s: float = 30.0) -> None:
        from .. import secrets
        self.netpolicy = netpolicy
        self._pw = password_getter or secrets.get_mailbox_password
        self.timeout_s = timeout_s
        self.poll_interval_s = poll_interval_s
        self.last_raw: bytes | None = None      # last sent message, for evidence

    def _password(self, profile: Profile) -> str:
        mb = profile.mailbox
        if mb is None:
            raise MailError("profile has no removal mailbox")
        pw = self._pw(profile.id, mb)
        if not pw:
            raise MailError("mailbox password not in keychain")
        return pw

    def _check_host(self, host: str) -> None:
        if not self.netpolicy.is_allowed(host):
            raise MailError("mail host not on allowlist")

    def send(self, profile: Profile, to: str, subject: str, body: str, request_id: str) -> str:
        mb = profile.mailbox
        if mb is None:
            raise MailError("profile has no removal mailbox")
        self._check_host(mb.smtp_host)
        msg = build_message(mb, to, subject, body, request_id)
        pw = self._password(profile)
        pin = mb.tls_cert_sha256
        try:
            ctx = client_context(mb.smtp_host, pin)
            if mb.smtp_starttls:
                with smtplib.SMTP(mb.smtp_host, mb.smtp_port, timeout=self.timeout_s, local_hostname=_EHLO_NAME) as s:
                    s.starttls(context=ctx)
                    check_peer(s.sock, pin)          # before any credential is sent
                    s.login(mb.username, pw)
                    s.send_message(msg)
            else:
                with smtplib.SMTP_SSL(mb.smtp_host, mb.smtp_port, context=ctx,
                                      timeout=self.timeout_s, local_hostname=_EHLO_NAME) as s:
                    check_peer(s.sock, pin)
                    s.login(mb.username, pw)
                    s.send_message(msg)
        except TlsPinError as e:
            raise MailError(f"smtp refused: {e}") from None
        except (smtplib.SMTPException, OSError) as e:
            raise MailError(f"smtp failed: {type(e).__name__}") from None
        self.last_raw = msg.as_bytes()
        return str(msg["Message-ID"])

    # ------------------------------------------------------------------ IMAP
    def _imap(self, mb: MailboxConfig) -> imaplib.IMAP4:
        """Connected (not logged-in) IMAP. With a pin, the peer certificate is checked here,
        so `login` is only ever reached on a matching certificate.

        Plaintext IMAP (no SSL and no STARTTLS) is refused on EVERY host, loopback
        included, before any socket is opened (SEC-53). The MailboxConfig validator
        refuses it too, but it can be bypassed (`model_copy`), so this check stands alone."""
        if not mb.imap_ssl and not mb.imap_starttls:
            raise MailError("mail connection is not encrypted; refusing to sign in")
        self._check_host(mb.imap_host)
        pin = mb.tls_cert_sha256
        ctx = client_context(mb.imap_host, pin)
        if mb.imap_ssl and not mb.imap_starttls:
            conn: imaplib.IMAP4 = imaplib.IMAP4_SSL(mb.imap_host, mb.imap_port,
                                                    ssl_context=ctx, timeout=self.timeout_s)
        else:
            conn = imaplib.IMAP4(mb.imap_host, mb.imap_port, timeout=self.timeout_s)
            if mb.imap_starttls:
                conn.starttls(ssl_context=ctx)
        try:
            check_peer(conn.sock, pin)
        except TlsPinError:
            with contextlib.suppress(Exception):
                conn.shutdown()
            raise
        return conn

    def fetch_since(self, profile: Profile, since: datetime) -> list[bytes]:
        mb = profile.mailbox
        if mb is None:
            raise MailError("profile has no removal mailbox")
        pw = self._password(profile)
        out: list[bytes] = []
        try:
            conn = self._imap(mb)
            try:
                conn.login(mb.username, pw)
                conn.select("INBOX", readonly=True)
                typ, data = conn.search(None, "SINCE", since.strftime("%d-%b-%Y"))
                if typ != "OK" or not data or not data[0]:
                    return []
                for num in data[0].split()[-MAX_MESSAGES:]:
                    typ, msgdata = conn.fetch(num, "(BODY.PEEK[])")
                    if typ == "OK" and msgdata and isinstance(msgdata[0], tuple):
                        out.append(msgdata[0][1])
            finally:
                with contextlib.suppress(Exception):
                    conn.logout()
        except TlsPinError as e:
            raise MailError(f"imap refused: {e}") from None
        except (imaplib.IMAP4.error, OSError) as e:
            raise MailError(f"imap failed: {type(e).__name__}") from None
        return out

    def links_from(self, raws: list[bytes], broker: Broker) -> list[str]:
        return scan_replies(raws, broker).links   # filtered + ranked (SEC-18)

    async def scan_replies(self, profile: Profile, broker: Broker, since: datetime,
                           timeout_s: int = 0) -> ReplyScan:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_s
        while True:
            raws = await asyncio.to_thread(self.fetch_since, profile, since)
            scan = scan_replies(raws, broker, since)
            if scan.links or scan.id_requested or loop.time() >= deadline:
                return scan
            await asyncio.sleep(min(self.poll_interval_s, max(0.0, deadline - loop.time())))

    async def wait_for_confirmation(self, profile: Profile, broker: Broker, since: datetime,
                                    timeout_s: int = 600) -> list[str]:
        scan = await self.scan_replies(profile, broker, since, timeout_s)
        return [] if scan.id_requested else scan.links


@dataclass
class SentMail:
    profile_id: str
    to: str
    subject: str
    body: str
    request_id: str
    message_id: str


@dataclass
class FakeMailer:
    """In-memory mailer for dry runs, the dev fixture run and tests. Sends nothing."""
    inbox: dict[str, list[bytes]] = field(default_factory=dict)   # broker_id -> raw mails
    sent: list[SentMail] = field(default_factory=list)
    last_raw: bytes | None = None

    def send(self, profile: Profile, to: str, subject: str, body: str, request_id: str) -> str:
        mb = profile.mailbox or MailboxConfig(address="removal@freemyid.invalid",
                                              imap_host="imap.freemyid.invalid",
                                              smtp_host="smtp.freemyid.invalid",
                                              username="fake")
        msg = build_message(mb, to, subject, body, request_id)
        self.last_raw = msg.as_bytes()
        mid = str(msg["Message-ID"])
        self.sent.append(SentMail(profile.id, to, subject, body, request_id, mid))
        return mid

    async def scan_replies(self, profile: Profile, broker: Broker, since: datetime,
                           timeout_s: int = 0) -> ReplyScan:
        return scan_replies(self.inbox.get(broker.id, []), broker, since)

    async def wait_for_confirmation(self, profile: Profile, broker: Broker, since: datetime,
                                    timeout_s: int = 600) -> list[str]:
        scan = await self.scan_replies(profile, broker, since, timeout_s)
        return [] if scan.id_requested else scan.links


def now() -> datetime:
    return utcnow()
