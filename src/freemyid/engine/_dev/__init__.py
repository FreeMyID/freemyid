"""Dev fixtures: a fake registry, a local fixture web server and a fake inbox.

Used by tests/test_e2e_dryrun.py and `python -m freemyid.engine._dev.devrun`. Nothing here
talks to the internet:

* `fixture_registry()`  fake brokers on reserved `.example` hosts (registry.yaml).
* `fixture_server()`    context manager: serves `site/<host>/<path>` on 127.0.0.1:<random>
                        and sets FREEMYID_DEV_FIXTURES=<base url> while active. With that set,
                        BrowserManager answers every allowlisted request from this server
                        (route.fetch -> route.fulfill) and the runner/outbox use FakeMailer.
* `fixture_inbox()`     broker_id -> raw .eml messages for FakeMailer.
"""
from __future__ import annotations

import contextlib
import os
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from ...models import Registry
from ..outbox import DEV_FIXTURES_ENV

DEV_DIR = Path(__file__).resolve().parent
SITE_DIR = DEV_DIR / "site"
INBOX_DIR = DEV_DIR / "inbox"
REGISTRY_PATH = DEV_DIR / "registry.yaml"


def fixture_registry() -> Registry:
    from ...registry import load_registry
    return load_registry(REGISTRY_PATH)


def fixture_inbox() -> dict[str, list[bytes]]:
    out: dict[str, list[bytes]] = {}
    for f in sorted(INBOX_DIR.glob("*.eml")):
        out.setdefault(f.stem.split(".")[0], []).append(f.read_bytes())
    return out


def resolve(path: str) -> Path | None:
    """Map '/<host>/<path>' to a file under SITE_DIR (path, path.html, path/index.html)."""
    rel = unquote(urlsplit(path).path).lstrip("/")
    if not rel or "\\" in rel or any(p in ("..", "") for p in rel.rstrip("/").split("/")):
        return None
    base = (SITE_DIR / rel.rstrip("/")).resolve()
    if SITE_DIR.resolve() not in base.parents:
        return None
    for cand in (base, base.with_name(base.name + ".html"), base / "index.html"):
        if cand.is_file():
            return cand
    return None


class _Handler(BaseHTTPRequestHandler):
    def _serve(self) -> None:
        if self.command == "POST":
            n = int(self.headers.get("Content-Length") or 0)
            self.rfile.read(min(n, 1_000_000))
        f = resolve(self.path)
        if f is None:
            body = b"<html><body><h1>Not found</h1></body></html>"
            self.send_response(404)
        else:
            body = f.read_bytes()
            self.send_response(200)
        ctype = "text/html; charset=utf-8" if f is None or f.suffix in (".html", "") \
            else "application/octet-stream"
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = _serve
    do_POST = _serve

    def log_message(self, format: str, *args: object) -> None:
        return


@contextlib.contextmanager
def fixture_server() -> Iterator[str]:
    """Serve the fixture site on 127.0.0.1 and point the engine at it. Yields the base URL."""
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    old = os.environ.get(DEV_FIXTURES_ENV)
    os.environ[DEV_FIXTURES_ENV] = base
    try:
        yield base
    finally:
        if old is None:
            os.environ.pop(DEV_FIXTURES_ENV, None)
        else:
            os.environ[DEV_FIXTURES_ENV] = old
        srv.shutdown()
        srv.server_close()
