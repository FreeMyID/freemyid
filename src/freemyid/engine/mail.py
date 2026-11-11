"""SMTP send + IMAP confirmation polling for a profile's dedicated removal mailbox.

* Password comes ONLY from the OS keychain (`secrets.get_mailbox_password`).
* Every host is checked with NetPolicy before connecting.
* `wait_for_confirmation` returns only https links whose host is inside the broker's
  `confirmation_domains` (or `domains` if that is empty). Mail text is data, never
  instructions: we extract URLs and nothing else.
* `FakeMailer` records sends in memory: used for dry runs, dev runs and tests.
* `classify_reply` turns one already-accepted reply into a category code.
"""
from __future__ import annotations

import asyncio
import contextlib
import email
import email.errors
import email.policy
import imaplib
import logging
import re
import smtplib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from email.utils import formatdate, getaddresses, make_msgid, parsedate_to_datetime
from html import unescape
from typing import TYPE_CHECKING, Literal

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
# BL-IN-10: a broker reply saying it needs more time (a statutory extension). The runner then
# waits the longer legal window before any letter that cites the law. A bare "extension"
# does not count, nor do "phone extension" and "browser extension": a time word has to sit
# in the same sentence.
_NEAR = r"[^.]{0,60}"
_NOT_FOOTER = r"(?<!phone )(?<!browser )"
_EXTENSION = re.compile(
    r"\bextend(ing|ed)?\b" + _NEAR + r"\b(time|period|deadline|response|days)\b|"
    + r"\b(time|period|deadline|days?)\b" + _NEAR + _NOT_FOOTER + r"\bextension\b|"
    + _NOT_FOOTER + r"\bextension\b" + _NEAR
    + r"\b(time|period|deadline|response|days?)\b|"
    + r"additional (45|forty[- ]five|90|ninety) days|"
    + r"(need|require)s? (additional|more) time",
    re.IGNORECASE)
DATE_SLACK = timedelta(hours=1)     # broker clock skew vs. our last_submitted_at
MAX_MESSAGES = 50            # per poll; we only need recent broker mail
MAX_MESSAGE_BYTES = 2_000_000
_HEADER_BYTES = 65_536       # From / Date / Message-ID are read from this prefix only


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


def _parse(raw: bytes, *, header_only: bool = False) -> EmailMessage:
    data = raw[:_HEADER_BYTES] if header_only else raw
    return email.message_from_bytes(data, policy=email.policy.default)


def extract_links(raw: bytes, allowed_domains: list[str]) -> list[str]:
    """Pure: https links in a raw RFC822 message whose host is inside `allowed_domains`."""
    if len(raw) > MAX_MESSAGE_BYTES:
        return []
    return _links_from_message(_parse(raw), allowed_domains)


def _links_from_message(msg: EmailMessage, allowed_domains: list[str]) -> list[str]:
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


def _clean_domain(domain: str) -> str | None:
    domain = domain.strip().lower().rstrip(".")
    if domain and re.fullmatch(r"[a-z0-9.-]+", domain):
        return domain
    return None


def _sender_domain(msg: EmailMessage) -> str | None:
    """Domain of the real From address. A display name that contains '@' does not count."""
    try:
        header = msg.get("From")
    except (TypeError, ValueError):
        return None
    if header is None:
        return None
    addresses = getattr(header, "addresses", None)
    if addresses:
        try:
            return _clean_domain(str(addresses[0].domain or ""))
        except (AttributeError, IndexError, TypeError, ValueError):
            return None
    for _name, addr in getaddresses([str(header)]):
        if "@" in addr:
            return _clean_domain(addr.rsplit("@", 1)[-1])
    return None


def sender_domain(raw: bytes) -> str | None:
    """Domain of the parsed From address (the first '@' in the header is not enough)."""
    return _sender_domain(_parse(raw, header_only=True))


@dataclass
class ReplyScan:
    """What the broker's replies say. Everything but `replies` is PII-free (links are
    confirmation URLs only). `replies` holds the matched raw messages for the encrypted
    proof vault only; never log or serialize it."""
    links: list[str] = field(default_factory=list)   # newest message first, ranked inside
    id_requested: bool = False      # some reply asks for an ID document -> human to-do
    extension_claimed: bool = False  # some reply says the broker is taking more time
    messages: int = 0               # distinct broker messages considered
    duplicates: int = 0             # same Message-ID (or same bytes) seen again
    stale: int = 0                  # older than the submission this reply would answer
    #: (Date header, raw bytes) of each matched broker message, newest first. Evidence only.
    replies: list[tuple[datetime | None, bytes]] = field(default_factory=list, repr=False)


def _date_of(msg: EmailMessage) -> datetime | None:
    try:
        d = parsedate_to_datetime(str(msg.get("Date", "")))
    except (TypeError, ValueError, IndexError):
        return None
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def message_date(raw: bytes) -> datetime | None:
    return _date_of(_parse(raw, header_only=True))


def _message_key_of(msg: EmailMessage, raw: bytes) -> str:
    mid = str(msg.get("Message-ID", "")).strip()
    if mid:
        return mid
    import hashlib
    return hashlib.sha256(raw).hexdigest()


def _message_key(raw: bytes) -> str:
    return _message_key_of(_parse(raw, header_only=True), raw)


def _plain_text_of(msg: EmailMessage) -> str:
    parts: list[str] = [str(msg.get("Subject", ""))]
    for part in msg.walk():
        if part.get_content_maintype() != "text":
            continue
        try:
            parts.append(unescape(re.sub(r"<[^>]+>", " ", part.get_content())))
        except (LookupError, ValueError):
            continue
    return " ".join(" ".join(parts).split())


def _plain_text(raw: bytes) -> str:
    return _plain_text_of(_parse(raw))


def asks_for_id(raw: bytes) -> bool:
    """Pure: does this message ask for an identity document (ID, licence, SSN, ...)?"""
    if len(raw) > MAX_MESSAGE_BYTES:
        return False
    return bool(_ID_REQUEST.search(_plain_text(raw)))


def claims_extension(raw: bytes) -> bool:
    """The reply says the broker is extending its response time (BL-IN-10)."""
    if len(raw) > MAX_MESSAGE_BYTES:
        return False
    return bool(_EXTENSION.search(_plain_text(raw)))


ReplyCode = Literal["confirmed", "denied", "needs_id", "needs_more_time", "unknown"]
_REPLY_ERRORS = (LookupError, ValueError, UnicodeError, email.errors.MessageError)
# A removal has to name the record (or be the whole sentence). "we have removed the fee"
# is not a confirmation. Negation and hedges are applied per sentence below.
_CONFIRMED = re.compile(
    r"\bwe(?: have |'ve )(?:successfully )?(?:removed|deleted|erased) your "
    r"(?:record|listing|profile|information|personal information|data|details)\b|"
    r"\bwe(?: have |'ve )(?:successfully )?(?:removed|deleted|erased)\b"
    r"(?=\s*[.!]?\s*$)|"
    r"\b(?:your|the) (?:record|listing|profile|information|personal information|"
    r"data|details) (?:has been|have been|was) (?:successfully )?"
    r"(?:removed|deleted|erased)\b|"
    r"\b(?:the )?(?:removal|opt-?out|deletion) (?:is|was) (?:now )?complete\b|"
    r"\bwe(?: have |'ve )(?:successfully )?opted you out\b",
    re.IGNORECASE)
_REMOVAL_NEGATED = re.compile(
    r"\b(?:not|never|unable|cannot|can't|could not|couldn't|did not|didn't|"
    r"will not|won't|have not|haven't|has not|hasn't|nothing|none)\b"
    r".{0,40}\b(?:remov|delet|eras)|"
    r"\b(?:remov|delet|eras)\w*.{0,30}\b(?:not|never|nothing|none|unable|cannot|failed)\b",
    re.IGNORECASE)
_HEDGE = re.compile(r"\b(?:if|unless|whether|may|might|maybe|perhaps)\b|\?", re.IGNORECASE)
_DENIED = re.compile(
    r"\bunable to locate your record\b|"
    r"\b(?:we (?:were |are )?)?unable to (?:locate|find) "
    r"(?:your|a matching|the) (?:record|listing|profile|information)\b|"
    r"\b(?:could not|couldn'?t|cannot|can ?not) (?:locate|find) "
    r"(?:your|a matching|the) (?:record|listing|profile|information)\b|"
    r"\bno (?:matching )?record (?:was found|of you|on file)\b|"
    r"\byour request (?:has been |was )?denied\b|"
    r"\bwe (?:do not|don't) have (?:your|a|any) (?:record|listing|information|data)\b",
    re.IGNORECASE)
# "please verify your identity" is not an asks_for_id document request.
_NEEDS_ID_TEXT = re.compile(
    r"\b(?:please )?verify your identity\b|\b(?:please )?confirm your identity\b",
    re.IGNORECASE)
# "we need 45 more days" is not a claims_extension hit (that helper wants "more time"
# or a nearby "extension"). Same category, extra wording.
_MORE_TIME_TEXT = re.compile(
    r"\b(?:we )?(?:need|require)s? \d+ more days\b|\b\d+ more days\b",
    re.IGNORECASE)


def _reply_bytes(text: str | bytes) -> bytes | None:
    """UTF-8 text inside MAX_MESSAGE_BYTES, else None (empty, huge, or binary)."""
    if isinstance(text, str):
        if len(text) > MAX_MESSAGE_BYTES or not text.strip():
            return None
        if _hostile_text(text):
            return None
        raw = text.encode("utf-8")
    elif isinstance(text, bytes):
        if len(text) > MAX_MESSAGE_BYTES or not text.strip():
            return None
        if any(byte < 32 and byte not in (9, 10, 13) or byte == 127 for byte in text):
            return None
        try:
            text.decode("utf-8")
        except UnicodeDecodeError:
            return None
        raw = text
    else:
        return None
    if len(raw) > MAX_MESSAGE_BYTES:
        return None
    return raw


def _hostile_text(text: str) -> bool:
    for char in text:
        code = ord(char)
        if code < 32 and char not in "\t\n\r" or code == 127:
            return True
    return False


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.?!])\s+", text.strip())
    return [" ".join(part.split()) for part in parts if part.strip()]


def _clean_hit(pattern: re.Pattern[str], plain: str) -> bool:
    for sentence in _sentences(plain):
        if "?" in sentence:
            continue
        if pattern.search(sentence):
            return True
    return False


def _confirmed_flags(plain: str) -> tuple[bool, bool]:
    """(clear removal sentence, some sentence takes a removal back)."""
    clean = False
    negated = False
    for sentence in _sentences(plain):
        if _REMOVAL_NEGATED.search(sentence):
            negated = True
        if (_CONFIRMED.search(sentence) and not _HEDGE.search(sentence)
                and not _REMOVAL_NEGATED.search(sentence)):
            clean = True
    return clean, negated


def _reply_code(plain: str) -> ReplyCode:
    clean, negated = _confirmed_flags(plain)
    # A removal and its contradiction are ambiguous: never call that confirmed.
    if clean and negated:
        return "unknown"
    hits: list[ReplyCode] = []
    if clean:
        hits.append("confirmed")
    if _clean_hit(_DENIED, plain):
        hits.append("denied")
    if _ID_REQUEST.search(plain) or _clean_hit(_NEEDS_ID_TEXT, plain):
        hits.append("needs_id")
    if _EXTENSION.search(plain) or _clean_hit(_MORE_TIME_TEXT, plain):
        hits.append("needs_more_time")
    if len(hits) == 1:
        return hits[0]
    return "unknown"


_MESSAGE_HEADERS = frozenset({
    "from", "to", "cc", "subject", "date", "message-id", "content-type", "mime-version",
    "content-transfer-encoding", "received", "return-path", "reply-to", "sender",
    "in-reply-to", "references", "delivered-to"})


def _looks_like_message(raw: bytes) -> bool:
    """True when the header block has a real RFC822 header, not just "Word: text"."""
    if raw[:1] in (b" ", b"\t", b"\r", b"\n"):
        return False
    msg = _parse(raw, header_only=True)
    return any(str(key).lower() in _MESSAGE_HEADERS for key in msg)


def classify_reply(text: str | bytes) -> ReplyCode:
    """One already-accepted broker reply, as a category code.

    The code is confirmed, denied, needs_id, needs_more_time, or unknown.
    Mixed, hedged, or unclear wording is unknown, never confirmed. Empty input,
    input over MAX_MESSAGE_BYTES, and non-text input are unknown. Nothing is logged.
    """
    raw = _reply_bytes(text)
    if raw is None:
        return "unknown"
    try:
        # Plain reply text (CodeRabbit #103): an empty header block keeps a first line such
        # as "Update: ..." or "  We have ..." in the body instead of the headers.
        plain = _plain_text(raw if _looks_like_message(raw) else b"\n" + raw)
        if not plain.strip():
            return "unknown"
        return _reply_code(plain)
    except _REPLY_ERRORS:
        return "unknown"


def scan_replies(raws: list[bytes], broker: Broker, since: datetime | None = None, *,
                 check_sender: bool = True) -> ReplyScan:
    """Pure reply matcher.

    * only mail From a broker/confirmation domain (unless check_sender=False);
    * the same message twice (Message-ID, else bytes) counts once;
    * mail dated before `since` (minus DATE_SLACK) answers an earlier request: ignored, so
      an old confirmation link is never clicked for a new submission;
    * a message that asks for ID sets id_requested and contributes no links;
    * a message saying the broker needs more time sets extension_claimed;
    * links come newest message first (a broker that answers twice: its latest link wins).
    """
    allowed = confirmation_hosts(broker)
    out = ReplyScan()
    seen: set[str] = set()
    msgs: list[tuple[datetime | None, int, bytes, EmailMessage]] = []
    sender_hosts = [*broker.domains, *allowed]
    for i, raw in enumerate(raws):
        # One parse per raw message. Oversized mail stops at the header prefix: the body
        # checks refuse it, matching asks_for_id and extract_links.
        oversized = len(raw) > MAX_MESSAGE_BYTES
        msg = _parse(raw, header_only=oversized)
        if check_sender and not _host_in(_sender_domain(msg), sender_hosts):
            continue
        key = _message_key_of(msg, raw)
        if key in seen:
            out.duplicates += 1
            continue
        seen.add(key)
        d = _date_of(msg)
        if since is not None and d is not None:
            ref = since if since.tzinfo else since.replace(tzinfo=UTC)
            if d < ref - DATE_SLACK:
                out.stale += 1
                continue
        msgs.append((d, i, raw, msg))
    out.messages = len(msgs)
    floor = datetime.min.replace(tzinfo=UTC)
    msgs.sort(key=lambda m: (m[0] or floor, m[1]), reverse=True)
    out.replies = [(d, raw[:MAX_MESSAGE_BYTES]) for d, _i, raw, _msg in msgs]
    for _d, _i, raw, msg in msgs:
        if len(raw) > MAX_MESSAGE_BYTES:
            continue
        text = _plain_text_of(msg)
        if _EXTENSION.search(text):
            out.extension_claimed = True
        if _ID_REQUEST.search(text):
            out.id_requested = True
            continue
        for u in _links_from_message(msg, allowed):
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
