"""Free My ID scheduled social poster (Bluesky). Plain script, no AI.

Posts at most ONE queued item per run from docs/marketing/seo/bluesky-queue.md.

Queue format, one block per post (text outside blocks is ignored):

    ## Q-001
    status: queued
    ```text
    <post text>
    ```

On success the block's status line becomes
``status: posted <ISO UTC timestamp> <at:// uri>`` (atomic rewrite) and a row is
appended to docs/marketing/seo/outreach-log.md.

Secrets: the app password (keyring service "freemyid-social", entry "bluesky_token")
and the session accessJwt are never printed, logged or put in exception text.
Network: only https://bsky.social, checked before every request.

Run:  .venv/bin/python tools/social/poster.py [--dry-run] [--handle HANDLE]
Exit: 0 = posted or nothing to do, 1 = network/HTTP error (item stays queued),
      2 = posted but the queue could not be updated (fix by hand; URI is logged),
      3 = bad arguments / unreadable queue.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import tempfile
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit

import httpx

log = logging.getLogger("freemyid.social.poster")

REPO = Path(__file__).resolve().parents[2]
SEO_DIR = REPO / "docs" / "marketing" / "seo"
KEYRING_SERVICE = "freemyid-social"
HANDLE_ENV = "FREEMYID_BLUESKY_HANDLE"
TIMEOUT_S = 20.0

EXIT_OK = 0
EXIT_HTTP = 1
EXIT_RECORD = 2
EXIT_USAGE = 3


# --------------------------------------------------------------------------- secrets


class Scrubber:
    """Holds secret strings and redacts them from any text."""

    def __init__(self) -> None:
        self._secrets: set[str] = set()

    def add(self, value: str | None) -> None:
        if value and len(value) >= 4:
            self._secrets.add(value)

    def __call__(self, text: object) -> str:
        out = str(text)
        for s in sorted(self._secrets, key=len, reverse=True):
            out = out.replace(s, "[REDACTED]")
        return out


class ScrubFilter(logging.Filter):
    """Logging filter that redacts secrets after %-formatting."""

    def __init__(self, scrub: Scrubber) -> None:
        super().__init__()
        self.scrub = scrub

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self.scrub(record.getMessage())
        record.args = None
        return True


class PosterError(Exception):
    """Raised with an already-scrubbed message."""


# --------------------------------------------------------------------------- queue parser

HEADING_RE = re.compile(r"^## ([A-Z]{1,4}-\d{1,6})\s*$")
STATUS_RE = re.compile(r"^status: (\S.*?)\s*$")
FENCE_OPEN = "```text"
FENCE_CLOSE = "```"


@dataclass(frozen=True)
class QueueItem:
    item_id: str
    status: str
    text: str
    status_line: int  # 0-based index into the file's lines


def _strip_eol(line: str) -> str:
    return line.rstrip("\r\n")


def parse_queue(content: str) -> list[QueueItem]:
    """Strict parser. Malformed blocks are skipped with a warning, never half-used."""
    lines = content.splitlines(keepends=True)
    items: list[QueueItem] = []
    seen: set[str] = set()
    i = 0
    n = len(lines)
    while i < n:
        m = HEADING_RE.match(_strip_eol(lines[i]))
        if not m:
            if _strip_eol(lines[i]).startswith("## Q-"):
                log.warning("queue line %d: malformed heading; block skipped", i + 1)
            i += 1
            continue
        item_id = m.group(1)
        start = i
        i += 1
        # status line must be the very next line
        sm = STATUS_RE.match(_strip_eol(lines[i])) if i < n else None
        if not sm:
            log.warning("queue %s (line %d): missing status line; skipped", item_id, start + 1)
            continue
        status_idx = i
        status = sm.group(1)
        i += 1
        if i >= n or _strip_eol(lines[i]) != FENCE_OPEN:
            log.warning("queue %s (line %d): missing ```text fence; skipped", item_id, start + 1)
            continue
        i += 1
        body: list[str] = []
        closed = False
        while i < n:
            raw = _strip_eol(lines[i])
            if raw == FENCE_CLOSE:
                closed = True
                i += 1
                break
            if HEADING_RE.match(raw):
                break  # next block began before this one closed
            body.append(raw)
            i += 1
        if not closed:
            log.warning("queue %s (line %d): unclosed text fence; skipped", item_id, start + 1)
            continue
        text = "\n".join(body).strip()
        if not text:
            log.warning("queue %s (line %d): empty post text; skipped", item_id, start + 1)
            continue
        if item_id in seen:
            log.warning("queue %s (line %d): duplicate id; skipped", item_id, start + 1)
            continue
        seen.add(item_id)
        items.append(QueueItem(item_id, status, text, status_idx))
    return items


def next_queued(items: Iterable[QueueItem]) -> list[QueueItem]:
    return [it for it in items if it.status == "queued"]


def rewrite_status(content: str, item: QueueItem, new_status: str) -> str:
    """Return content with the item's status line replaced. Re-verifies the block first."""
    if "\n" in new_status or "\r" in new_status:
        raise PosterError("status must be a single line")
    current = {it.item_id: it for it in parse_queue(content)}
    found = current.get(item.item_id)
    if found is None or found.status != "queued" or found.text != item.text:
        raise PosterError(f"queue block {item.item_id} changed or vanished; not rewritten")
    lines = content.splitlines(keepends=True)
    old = lines[found.status_line]
    eol = old[len(_strip_eol(old)):]
    lines[found.status_line] = f"status: {new_status}{eol}"
    return "".join(lines)


def atomic_write(path: Path, content: str) -> None:
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        if path.exists():
            os.chmod(tmp, path.stat().st_mode & 0o777)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


# --------------------------------------------------------------------------- text helpers

URL_RE = re.compile(r"https://[^\s<>\"'`]+")
TRAILING = ".,;:!?'\"*_"
REGIONAL = range(0x1F1E6, 0x1F200)
SKIN_TONES = range(0x1F3FB, 0x1F400)
ZWJ = "\u200d"
OPENER = {")": "(", "]": "[", "}": "{"}


def find_urls(text: str) -> list[tuple[int, int, str]]:
    """(char_start, char_end, url) for each https:// URL, trailing punctuation trimmed."""
    out = []
    for m in URL_RE.finditer(text):
        url = m.group(0)
        while url:
            last = url[-1]
            unbalanced = last in ")]}" and url.count(last) > url.count(OPENER[last])
            if last in TRAILING or unbalanced:
                url = url[:-1]
            else:
                break
        if len(url) > len("https://") and urlsplit(url).hostname:
            out.append((m.start(), m.start() + len(url), url))
    return out


def link_facets(text: str) -> list[dict[str, Any]]:
    """app.bsky.richtext.facet#link facets with UTF-8 byte offsets."""
    facets = []
    for start, end, url in find_urls(text):
        b_start = len(text[:start].encode("utf-8"))
        b_end = b_start + len(text[start:end].encode("utf-8"))
        facets.append(
            {
                "index": {"byteStart": b_start, "byteEnd": b_end},
                "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}],
            }
        )
    return facets


def grapheme_count(text: str) -> int:
    """Approximate extended-grapheme count (stdlib only).

    Combining marks, variation selectors, skin-tone modifiers, ZWJ sequences and
    regional-indicator pairs (flags) do not start a new grapheme. CRLF counts once.
    """
    count = 0
    prev_zwj = False
    ri_open = False
    prev = ""
    for ch in text:
        cp = ord(ch)
        joins = (
            unicodedata.combining(ch) != 0
            or unicodedata.category(ch) in ("Mn", "Me", "Mc")
            or 0xFE00 <= cp <= 0xFE0F
            or 0xE0020 <= cp <= 0xE007F  # emoji tag sequences
            or cp in SKIN_TONES
            or ch == ZWJ
            or prev_zwj
            or (ch == "\n" and prev == "\r")
        )
        if cp in REGIONAL:
            if ri_open:
                joins = True
                ri_open = False
            else:
                ri_open = True
        else:
            ri_open = False
        if not joins:
            count += 1
        prev_zwj = ch == ZWJ
        prev = ch
    return count


# --------------------------------------------------------------------------- HTTP


class Http:
    """Allowlisted HTTPS client. Every request is checked before it is sent."""

    def __init__(
        self,
        allowed_hosts: frozenset[str],
        scrub: Scrubber,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.allowed_hosts = allowed_hosts
        self.scrub = scrub
        self._client = httpx.Client(
            timeout=httpx.Timeout(TIMEOUT_S),
            verify=True,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        )

    def check_url(self, url: str) -> None:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        if (
            parts.scheme != "https"
            or host not in self.allowed_hosts
            or parts.username is not None
            or parts.password is not None
            or parts.port not in (None, 443)
        ):
            raise PosterError(f"refused: {parts.scheme}://{host} is not on the allowlist")

    def post_json(
        self, url: str, payload: dict[str, Any], headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
        self.check_url(url)
        try:
            resp = self._client.post(url, json=payload, headers=headers or {})
        except httpx.HTTPError as exc:
            raise PosterError(self.scrub(f"network error: {type(exc).__name__}: {exc}")) from None
        if resp.status_code >= 400:
            detail = ""
            try:
                body = resp.json()
                if isinstance(body, dict):
                    detail = f" {body.get('error', '')}: {body.get('message', '')}"
            except ValueError:
                pass
            # scrub BEFORE truncating, so a cut can never leave part of a secret behind
            detail = self.scrub(detail)[:300]
            raise PosterError(self.scrub(f"HTTP {resp.status_code} from {url}{detail}"))
        try:
            data = resp.json()
        except ValueError:
            raise PosterError(f"non-JSON response from {url}") from None
        if not isinstance(data, dict):
            raise PosterError(f"unexpected response shape from {url}")
        return data

    def close(self) -> None:
        self._client.close()


# --------------------------------------------------------------------------- backends

KeyringGet = Callable[[str, str], "str | None"]


@dataclass
class PostResult:
    uri: str
    web_url: str


class Backend(Protocol):
    """A posting target. Add a new platform by implementing this."""

    name: str
    label: str
    queue_file: str
    allowed_hosts: frozenset[str]

    def length_error(self, text: str) -> str | None: ...

    def facets(self, text: str) -> list[dict[str, Any]]: ...

    def load_credentials(self, kr_get: KeyringGet, scrub: Scrubber) -> bool: ...

    def post(self, http: Http, text: str, now: datetime) -> PostResult: ...


@dataclass
class BlueskyBackend:
    handle_override: str | None = None
    name: str = "bluesky"
    label: str = "Bluesky"
    queue_file: str = "bluesky-queue.md"
    allowed_hosts: frozenset[str] = frozenset({"bsky.social"})
    base: str = "https://bsky.social/xrpc"
    max_graphemes: int = 300
    max_bytes: int = 3000
    _handle: str | None = field(default=None, repr=False)
    _password: str | None = field(default=None, repr=False)

    def length_error(self, text: str) -> str | None:
        g = grapheme_count(text)
        if g > self.max_graphemes:
            return f"{g} graphemes > {self.max_graphemes}"
        if len(text.encode("utf-8")) > self.max_bytes:
            return f"over {self.max_bytes} bytes"
        return None

    def facets(self, text: str) -> list[dict[str, Any]]:
        return link_facets(text)

    def _resolve_handle(self, kr_get: KeyringGet) -> str | None:
        handle = self.handle_override or os.environ.get(HANDLE_ENV)
        if not handle:
            raw = kr_get(KEYRING_SERVICE, "bluesky")
            if raw:
                try:
                    data = json.loads(raw)
                except ValueError:
                    data = None
                if isinstance(data, dict):
                    # Non-secret fields only; "password"/"email" are never read.
                    value = data.get("handle") or data.get("user")
                    handle = value if isinstance(value, str) else None
        if handle:
            handle = handle.strip().lstrip("@")
        return handle or None

    def load_credentials(self, kr_get: KeyringGet, scrub: Scrubber) -> bool:
        password = kr_get(KEYRING_SERVICE, "bluesky_token")
        if not password:
            return False
        scrub.add(password)
        handle = self._resolve_handle(kr_get)
        if not handle:
            log.info("bluesky: no handle (keyring 'bluesky' user, --handle or %s)", HANDLE_ENV)
            return False
        self._handle, self._password = handle, password
        return True

    def post(self, http: Http, text: str, now: datetime) -> PostResult:
        if not self._handle or not self._password:
            raise PosterError("bluesky: credentials not loaded")
        session = http.post_json(
            f"{self.base}/com.atproto.server.createSession",
            {"identifier": self._handle, "password": self._password},
        )
        jwt = session.get("accessJwt")
        did = session.get("did")
        if not isinstance(jwt, str) or not isinstance(did, str) or not jwt or not did:
            raise PosterError("bluesky: session response missing accessJwt/did")
        http.scrub.add(jwt)
        refresh = session.get("refreshJwt")
        if isinstance(refresh, str):
            http.scrub.add(refresh)
        record: dict[str, Any] = {
            "$type": "app.bsky.feed.post",
            "text": text,
            "createdAt": now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z",
        }
        facets = self.facets(text)
        if facets:
            record["facets"] = facets
        created = http.post_json(
            f"{self.base}/com.atproto.repo.createRecord",
            {"repo": did, "collection": "app.bsky.feed.post", "record": record},
            headers={"Authorization": f"Bearer {jwt}"},
        )
        uri = created.get("uri")
        if not isinstance(uri, str) or not uri.startswith("at://"):
            raise PosterError("bluesky: createRecord response missing at:// uri")
        rkey = uri.rsplit("/", 1)[-1]
        return PostResult(uri=uri, web_url=f"https://bsky.app/profile/{did}/post/{rkey}")


@dataclass
class MastodonBackend:
    """Stub for later: POST https://mastodon.social/api/v1/statuses, Bearer mastodon_token.

    Not wired into the CLI. Implement load_credentials/post and add to BACKENDS.
    """

    name: str = "mastodon"
    label: str = "Mastodon"
    queue_file: str = "mastodon-queue.md"
    allowed_hosts: frozenset[str] = frozenset({"mastodon.social"})
    max_chars: int = 500

    def length_error(self, text: str) -> str | None:
        return f"{len(text)} chars > {self.max_chars}" if len(text) > self.max_chars else None

    def facets(self, text: str) -> list[dict[str, Any]]:
        return []  # Mastodon detects links server-side

    def load_credentials(self, kr_get: KeyringGet, scrub: Scrubber) -> bool:
        raise NotImplementedError("mastodon backend not implemented yet")

    def post(self, http: Http, text: str, now: datetime) -> PostResult:
        raise NotImplementedError("mastodon backend not implemented yet")


BACKENDS: dict[str, Callable[..., Backend]] = {"bluesky": BlueskyBackend}


# --------------------------------------------------------------------------- outreach log


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def outreach_row(now: datetime, backend: Backend, item: QueueItem, result: PostResult) -> str:
    excerpt = item.text if len(item.text) <= 80 else item.text[:77] + "..."
    return (
        f"| {now.date().isoformat()} | {backend.label} | post (poster.py) | "
        f"{_cell(item.item_id + ': ' + excerpt)} | {result.web_url} | posted {result.uri} | 0 |\n"
    )


def append_outreach(path: Path, row: str) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if existing and not existing.endswith("\n"):
        existing += "\n"
    atomic_write(path, existing + row)


# --------------------------------------------------------------------------- run


def _default_keyring_get(service: str, name: str) -> str | None:
    try:
        import keyring
    except ImportError:
        return None
    try:
        return keyring.get_password(service, name)
    except Exception as exc:  # noqa: BLE001  locked/absent keyring backend: skip quietly
        log.info("keyring unavailable (%s); skipping", type(exc).__name__)
        return None


def run(
    *,
    backend: Backend,
    queue_path: Path,
    outreach_path: Path,
    dry_run: bool = False,
    kr_get: KeyringGet | None = None,
    transport: httpx.BaseTransport | None = None,
    now: Callable[[], datetime] | None = None,
    out: Callable[[str], None] = print,
) -> int:
    scrub = Scrubber()
    filt = ScrubFilter(scrub)
    log.addFilter(filt)
    try:
        return _run(
            backend, queue_path, outreach_path, dry_run, kr_get or _default_keyring_get,
            transport, now or (lambda: datetime.now(UTC)), out, scrub,
        )
    finally:
        log.removeFilter(filt)


def _run(
    backend: Backend,
    queue_path: Path,
    outreach_path: Path,
    dry_run: bool,
    kr_get: KeyringGet,
    transport: httpx.BaseTransport | None,
    now: Callable[[], datetime],
    out: Callable[[str], None],
    scrub: Scrubber,
) -> int:
    if not queue_path.exists():
        log.info("%s: queue file %s not found; nothing to do", backend.name, queue_path.name)
        return EXIT_OK
    try:
        content = queue_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        log.error("%s: cannot read queue: %s", backend.name, type(exc).__name__)
        return EXIT_USAGE

    candidate: QueueItem | None = None
    for item in next_queued(parse_queue(content)):
        problem = backend.length_error(item.text)
        if problem:
            log.warning("%s: %s too long (%s); skipped", backend.name, item.item_id, problem)
            continue
        candidate = item
        break
    if candidate is None:
        log.info("%s: no queued item; nothing to do", backend.name)
        return EXIT_OK

    if dry_run:
        out(f"[dry-run] {backend.label} would post {candidate.item_id}:")
        out(candidate.text)
        out("facets: " + json.dumps(backend.facets(candidate.text), ensure_ascii=False))
        return EXIT_OK

    if not backend.load_credentials(kr_get, scrub):
        log.info("%s: no credentials in keyring; skipping", backend.name)
        return EXIT_OK

    http = Http(backend.allowed_hosts, scrub, transport=transport)
    stamp = now()
    try:
        result = backend.post(http, candidate.text, stamp)
    except PosterError as exc:
        log.error("%s: %s left queued: %s", backend.name, candidate.item_id, scrub(exc))
        return EXIT_HTTP
    finally:
        http.close()

    iso = stamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    log.info("%s: posted %s as %s", backend.name, candidate.item_id, result.uri)
    try:
        fresh = queue_path.read_text(encoding="utf-8")
        atomic_write(queue_path, rewrite_status(fresh, candidate, f"posted {iso} {result.uri}"))
    except (OSError, PosterError) as exc:
        log.error(
            "%s: POSTED %s (%s) but queue not updated: %s. Mark it posted by hand.",
            backend.name, candidate.item_id, result.uri, scrub(exc),
        )
        return EXIT_RECORD
    try:
        append_outreach(outreach_path, outreach_row(stamp, backend, candidate, result))
    except OSError as exc:
        log.error("%s: outreach log not updated: %s", backend.name, type(exc).__name__)
        return EXIT_RECORD
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Post the next queued item (one per run).")
    ap.add_argument("--backend", choices=sorted(BACKENDS), default="bluesky")
    ap.add_argument("--dry-run", action="store_true", help="print only; no network, no writes")
    ap.add_argument("--handle", help=f"Bluesky handle (else ${HANDLE_ENV} or keyring 'bluesky')")
    ap.add_argument("--queue", type=Path, help="queue file (default docs/marketing/seo/...)")
    ap.add_argument("--outreach-log", type=Path, default=SEO_DIR / "outreach-log.md")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    backend = BACKENDS[args.backend](handle_override=args.handle)
    return run(
        backend=backend,
        queue_path=args.queue or SEO_DIR / backend.queue_file,
        outreach_path=args.outreach_log,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
