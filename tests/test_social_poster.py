"""tools/social/poster.py: fixture queue, mocked HTTP (httpx.MockTransport), fake keyring."""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import sys
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("social_poster", ROOT / "tools/social/poster.py")
assert _spec and _spec.loader
poster = importlib.util.module_from_spec(_spec)
sys.modules["social_poster"] = poster
_spec.loader.exec_module(poster)

SECRET = "abcd-efgh-ijkl-mnop"
JWT = "eyJ.fake-access-jwt.SIG"
REFRESH = "eyJ.fake-refresh-jwt.SIG"
HANDLE = "testperson.bsky.social"
DID = "did:plc:testpersonfake"
URI = f"at://{DID}/app.bsky.feed.post/3kfakerkey"
NOW = datetime(2026, 11, 7, 15, 0, 0, 123000, tzinfo=UTC)

QUEUE = """# Bluesky queue

Notes outside blocks are ignored. status: queued
```text
not a block
```

## Q-001
status: posted 2026-11-01T10:00:00Z at://did:plc:x/app.bsky.feed.post/old
```text
Already posted.
```

## Q-002
status: queued
```text
Free My ID removes you from people-search sites. https://freemyid.org
```

## Q-003
status: queued
```text
Second queued post.
```
"""

LOG = """# Outreach log

| Date | Site / person | Action | What was sent | Link | Result | New contacts today |
|---|---|---|---|---|---|---|
"""


def fake_keyring(entries: dict[str, str]):
    def get(service: str, name: str) -> str | None:
        assert service == "freemyid-social"
        return entries.get(name)

    return get


FULL_KEYS = {
    "bluesky_token": SECRET,
    "bluesky": json.dumps({"user": HANDLE, "email": "x@example.invalid", "password": "nope"}),
}


class Recorder:
    def __init__(self, fail_on: str | None = None, status: int = 500) -> None:
        self.requests: list[httpx.Request] = []
        self.fail_on = fail_on
        self.status = status

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if self.fail_on and path.endswith(self.fail_on):
            # a hostile/buggy server echoes back whatever it was sent
            echoed = request.headers.get("authorization", "") + " " + request.content.decode()
            return httpx.Response(
                self.status, json={"error": "AuthFailed", "message": f"bad input {echoed}"}
            )
        if path.endswith("createSession"):
            return httpx.Response(
                200, json={"accessJwt": JWT, "refreshJwt": REFRESH, "did": DID, "handle": HANDLE}
            )
        if path.endswith("createRecord"):
            return httpx.Response(200, json={"uri": URI, "cid": "bafyfake"})
        return httpx.Response(404)

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self)


@pytest.fixture
def files(tmp_path: Path) -> tuple[Path, Path]:
    q = tmp_path / "bluesky-queue.md"
    q.write_text(QUEUE, encoding="utf-8")
    o = tmp_path / "outreach-log.md"
    o.write_text(LOG, encoding="utf-8")
    return q, o


def do_run(files, rec=None, keys=FULL_KEYS, dry_run=False, out=None):
    q, o = files
    return poster.run(
        backend=poster.BlueskyBackend(),
        queue_path=q,
        outreach_path=o,
        dry_run=dry_run,
        kr_get=fake_keyring(keys),
        transport=rec.transport() if rec else None,
        now=lambda: NOW,
        out=out or (lambda s: None),
    )


# ----------------------------------------------------------------------------- parser


def test_parser_reads_only_well_formed_blocks():
    items = poster.parse_queue(QUEUE)
    assert [i.item_id for i in items] == ["Q-001", "Q-002", "Q-003"]
    assert items[1].status == "queued"
    assert items[1].text.endswith("https://freemyid.org")
    assert [i.item_id for i in poster.next_queued(items)] == ["Q-002", "Q-003"]


@pytest.mark.parametrize(
    "block",
    [
        "## Q-010\n\nstatus: queued\n```text\nx\n```\n",  # blank line before status
        "## Q-010\nstatus queued\n```text\nx\n```\n",  # no colon
        "## Q-010\nstatus: queued\n```\nx\n```\n",  # wrong fence language
        "## Q-010\nstatus: queued\nx\n",  # no fence at all
        "## Q-010\nstatus: queued\n```text\nnever closed\n",  # unclosed
        "## Q-010\nstatus: queued\n```text\n\n```\n",  # empty text
        "## Q-010\nstatus: queued\n```text\nhalf\n## Q-011\nstatus: queued\n```text\nok\n```\n",
    ],
)
def test_parser_skips_malformed_blocks(block, caplog):
    with caplog.at_level(logging.WARNING):
        items = poster.parse_queue(block)
    assert all(i.item_id != "Q-010" for i in items)
    assert any("Q-010" in r.getMessage() for r in caplog.records)


def test_parser_allows_note_lines_between_status_and_fence():
    text = "## Q-001\nstatus: queued\nnote: intro\nnote: day 1\n```text\nhello\n```\n"
    (item,) = poster.parse_queue(text)
    assert item.text == "hello" and item.status_line == 1
    bad = "## Q-001\nstatus: queued\nnotes: x\n```text\nhello\n```\n"
    assert poster.parse_queue(bad) == []
    before_status = "## Q-001\nnote: x\nstatus: queued\n```text\nhello\n```\n"
    assert poster.parse_queue(before_status) == []


def test_parser_recovers_next_block_after_unclosed_one():
    text = "## Q-010\nstatus: queued\n```text\nhalf\n## Q-011\nstatus: queued\n```text\nok\n```\n"
    items = poster.parse_queue(text)
    assert [(i.item_id, i.text) for i in items] == [("Q-011", "ok")]


def test_parser_duplicate_id_and_bad_heading(caplog):
    text = (
        "## Q-001\nstatus: queued\n```text\nfirst\n```\n"
        "## Q-001\nstatus: queued\n```text\nsecond\n```\n"
        "## Q-abc\nstatus: queued\n```text\nbad\n```\n"
    )
    with caplog.at_level(logging.WARNING):
        items = poster.parse_queue(text)
    assert [i.text for i in items] == ["first"]
    msgs = " ".join(r.getMessage() for r in caplog.records)
    assert "duplicate" in msgs and "malformed heading" in msgs


def test_parser_multiline_text_and_crlf():
    text = "## Q-001\r\nstatus: queued\r\n```text\r\nline one\r\nline two\r\n```\r\n"
    items = poster.parse_queue(text)
    assert items[0].text == "line one\nline two"
    out = poster.rewrite_status(text, items[0], "posted X at://y")
    assert out.splitlines(keepends=True)[1] == "status: posted X at://y\r\n"


def test_empty_queue_and_missing_file(tmp_path, caplog):
    assert poster.parse_queue("") == []
    q = tmp_path / "bluesky-queue.md"
    q.write_text("# nothing queued\n", encoding="utf-8")
    o = tmp_path / "log.md"
    rec = Recorder()
    with caplog.at_level(logging.INFO):
        assert do_run((q, o), rec) == 0
        assert do_run((tmp_path / "absent.md", o), rec) == 0
    assert rec.requests == []
    assert not o.exists()


# ----------------------------------------------------------------------------- facets


def test_facets_ascii():
    text = "See https://freemyid.org."
    (f,) = poster.link_facets(text)
    assert f["features"][0] == {"$type": "app.bsky.richtext.facet#link", "uri": "https://freemyid.org"}
    assert text.encode()[f["index"]["byteStart"] : f["index"]["byteEnd"]] == b"https://freemyid.org"


def test_facets_byte_offsets_with_emoji_and_non_ascii():
    text = "Café 🇺🇸 👨‍👩‍👧 privacy — https://freemyid.org/über?a=1 and (https://example.org/x)!"
    facets = poster.link_facets(text)
    raw = text.encode("utf-8")
    got = [raw[f["index"]["byteStart"] : f["index"]["byteEnd"]].decode() for f in facets]
    assert got == ["https://freemyid.org/über?a=1", "https://example.org/x"]
    assert [f["features"][0]["uri"] for f in facets] == got
    # char offset differs from byte offset because of the multibyte prefix
    assert facets[0]["index"]["byteStart"] > text.index("https://")


def test_facets_ignore_http_and_bare_scheme():
    assert poster.link_facets("http://insecure.example and https:// alone") == []


def test_grapheme_count():
    assert poster.grapheme_count("abc") == 3
    assert poster.grapheme_count("🇺🇸") == 1
    assert poster.grapheme_count("👨‍👩‍👧") == 1
    assert poster.grapheme_count("👍🏽") == 1
    assert poster.grapheme_count("é") == 1
    assert poster.grapheme_count("❤️") == 1


def test_too_long_item_is_skipped_and_next_posted(files, caplog):
    q, _ = files
    q.write_text(QUEUE.replace("Free My ID removes", "é" * 301 + " Free My ID removes"), "utf-8")
    rec = Recorder()
    with caplog.at_level(logging.WARNING):
        assert do_run(files, rec) == 0
    assert any("Q-002 too long" in r.getMessage() for r in caplog.records)
    body = json.loads(rec.requests[-1].content)
    assert body["record"]["text"] == "Second queued post."
    items = {i.item_id: i for i in poster.parse_queue(q.read_text("utf-8"))}
    assert items["Q-002"].status == "queued"
    assert items["Q-003"].status.startswith("posted ")


# ----------------------------------------------------------------------------- run


def test_posts_exactly_one_and_rewrites_status(files):
    q, o = files
    rec = Recorder()
    assert do_run(files, rec) == 0
    assert [r.url.path for r in rec.requests] == [
        "/xrpc/com.atproto.server.createSession",
        "/xrpc/com.atproto.repo.createRecord",
    ]
    assert all(r.url.host == "bsky.social" and r.url.scheme == "https" for r in rec.requests)
    sess = json.loads(rec.requests[0].content)
    assert sess == {"identifier": HANDLE, "password": SECRET}
    rec_req = rec.requests[1]
    assert rec_req.headers["authorization"] == f"Bearer {JWT}"
    body = json.loads(rec_req.content)
    assert body["repo"] == DID and body["collection"] == "app.bsky.feed.post"
    record = body["record"]
    assert record["$type"] == "app.bsky.feed.post"
    assert record["createdAt"] == "2026-11-07T15:00:00.123Z"
    assert record["facets"][0]["features"][0]["uri"] == "https://freemyid.org"

    items = {i.item_id: i for i in poster.parse_queue(q.read_text("utf-8"))}
    assert items["Q-002"].status == f"posted 2026-11-07T15:00:00Z {URI}"
    assert items["Q-003"].status == "queued"
    # only the status line changed
    before, after = QUEUE.splitlines(), q.read_text("utf-8").splitlines()
    assert [i for i, (a, b) in enumerate(zip(before, after, strict=True)) if a != b] == [
        items["Q-002"].status_line
    ]
    log_text = o.read_text("utf-8")
    assert log_text.startswith(LOG)
    assert log_text.count("\n") == LOG.count("\n") + 1
    assert URI in log_text and "Q-002" in log_text and "| Bluesky |" in log_text

    # second run posts the next one, never two at once
    rec2 = Recorder()
    assert do_run(files, rec2) == 0
    assert len(rec2.requests) == 2
    assert json.loads(rec2.requests[1].content)["record"]["text"] == "Second queued post."


def test_no_facets_key_when_no_links(files):
    q, _ = files
    q.write_text(QUEUE.replace(" https://freemyid.org", ""), "utf-8")
    rec = Recorder()
    assert do_run(files, rec) == 0
    assert "facets" not in json.loads(rec.requests[1].content)["record"]


def test_rewrite_refuses_if_block_changed():
    items = poster.parse_queue(QUEUE)
    changed = QUEUE.replace("Second queued post.", "Edited.")
    with pytest.raises(poster.PosterError):
        poster.rewrite_status(changed, items[2], "posted x")
    with pytest.raises(poster.PosterError):
        poster.rewrite_status(QUEUE, items[2], "posted\nstatus: queued")


def test_queue_edited_during_post_returns_record_error(files, caplog):
    q, _ = files
    rec = Recorder()

    def edit_then_respond(request):
        resp = rec(request)
        if request.url.path.endswith("createRecord"):
            q.write_text(QUEUE.replace("## Q-002", "## Q-099"), "utf-8")
        return resp

    with caplog.at_level(logging.ERROR):
        rc = poster.run(
            backend=poster.BlueskyBackend(), queue_path=q, outreach_path=files[1],
            kr_get=fake_keyring(FULL_KEYS), transport=httpx.MockTransport(edit_then_respond),
            now=lambda: NOW,
        )
    assert rc == poster.EXIT_RECORD
    assert any("POSTED Q-002" in r.getMessage() and URI in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize(
    "keys",
    [{}, {"bluesky": FULL_KEYS["bluesky"]}, {"bluesky_token": SECRET}],
    ids=["no-keys", "no-token", "no-handle"],
)
def test_missing_key_is_silent_skip(files, keys, caplog, capsys, monkeypatch):
    monkeypatch.delenv(poster.HANDLE_ENV, raising=False)
    rec = Recorder()
    with caplog.at_level(logging.DEBUG):
        assert do_run(files, rec, keys=keys) == 0
    assert rec.requests == []
    assert files[0].read_text("utf-8") == QUEUE
    assert files[1].read_text("utf-8") == LOG
    assert all(r.levelno <= logging.INFO for r in caplog.records)
    assert SECRET not in caplog.text and SECRET not in capsys.readouterr().out


def test_handle_override_and_env(files, monkeypatch):
    rec = Recorder()
    monkeypatch.setenv(poster.HANDLE_ENV, "@env.bsky.social")
    q, o = files
    assert poster.run(
        backend=poster.BlueskyBackend(), queue_path=q, outreach_path=o,
        kr_get=fake_keyring({"bluesky_token": SECRET}), transport=rec.transport(), now=lambda: NOW,
    ) == 0
    assert json.loads(rec.requests[0].content)["identifier"] == "env.bsky.social"


def test_dry_run_no_calls_no_writes(files, monkeypatch):
    q, o = files
    lines: list[str] = []
    rec = Recorder()

    def boom(*a, **k):
        raise AssertionError("keyring must not be read in dry-run")

    def no_write(*a, **k):
        raise AssertionError("no writes in dry-run")

    monkeypatch.setattr(poster, "atomic_write", no_write)
    monkeypatch.setattr(poster, "Http", no_write)
    rc = poster.run(
        backend=poster.BlueskyBackend(), queue_path=q, outreach_path=o, dry_run=True,
        kr_get=boom, transport=rec.transport(), now=lambda: NOW, out=lines.append,
    )
    assert rc == 0
    assert rec.requests == []
    assert q.read_text("utf-8") == QUEUE and o.read_text("utf-8") == LOG
    joined = "\n".join(lines)
    assert "Q-002" in joined and "https://freemyid.org" in joined
    facets = json.loads(lines[-1].removeprefix("facets: "))
    assert facets[0]["index"] == {"byteStart": 49, "byteEnd": 69}


def test_main_dry_run_cli(files, capsys):
    q, o = files
    assert poster.main(["--dry-run", "--queue", str(q), "--outreach-log", str(o)]) == 0
    assert "would post Q-002" in capsys.readouterr().out


# ----------------------------------------------------------------------------- allowlist


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/xrpc/x",
        "http://bsky.social/xrpc/x",
        "https://bsky.social.evil.example/x",
        "https://user:pw@bsky.social/x",
        "https://bsky.social:8443/x",
        "https://api.bsky.app/x",
    ],
)
def test_non_bsky_url_refused_before_request(url):
    rec = Recorder()
    http = poster.Http(frozenset({"bsky.social"}), poster.Scrubber(), transport=rec.transport())
    with pytest.raises(poster.PosterError, match="allowlist"):
        http.post_json(url, {})
    assert rec.requests == []
    http.check_url("https://bsky.social/xrpc/ok")  # allowed one passes


def test_backend_base_pointing_elsewhere_is_refused(files, caplog):
    rec = Recorder()
    backend = poster.BlueskyBackend(base="https://evil.example/xrpc")
    rc = poster.run(
        backend=backend, queue_path=files[0], outreach_path=files[1],
        kr_get=fake_keyring(FULL_KEYS), transport=rec.transport(), now=lambda: NOW,
    )
    assert rc == poster.EXIT_HTTP
    assert rec.requests == []
    assert SECRET not in caplog.text


def test_http_client_verifies_tls_and_no_redirects():
    http = poster.Http(frozenset({"bsky.social"}), poster.Scrubber())
    assert http._client.follow_redirects is False
    assert http._client.timeout.read == poster.TIMEOUT_S
    http.close()


# ----------------------------------------------------------------------------- errors / secrets


@pytest.mark.parametrize("fail_on", ["createSession", "createRecord"])
def test_http_error_leaves_item_queued_and_hides_secrets(files, fail_on, caplog, capsys):
    rec = Recorder(fail_on=fail_on, status=401)
    with caplog.at_level(logging.DEBUG):
        rc = do_run(files, rec)
    assert rc == poster.EXIT_HTTP
    assert files[0].read_text("utf-8") == QUEUE
    assert files[1].read_text("utf-8") == LOG
    assert "HTTP 401" in caplog.text and "[REDACTED]" in caplog.text
    captured = capsys.readouterr()
    for s in (SECRET, JWT, REFRESH):
        assert s not in caplog.text
        assert s not in captured.out and s not in captured.err


def test_network_exception_is_scrubbed(files, caplog):
    def explode(request):
        raise httpx.ConnectError(f"boom {SECRET} {request.headers.get('authorization', '')}")

    with caplog.at_level(logging.DEBUG):
        rc = poster.run(
            backend=poster.BlueskyBackend(), queue_path=files[0], outreach_path=files[1],
            kr_get=fake_keyring(FULL_KEYS), transport=httpx.MockTransport(explode),
            now=lambda: NOW,
        )
    assert rc == poster.EXIT_HTTP
    assert SECRET not in caplog.text and "ConnectError" in caplog.text
    assert files[0].read_text("utf-8") == QUEUE


def test_truncation_never_leaves_partial_secret():
    scrub = poster.Scrubber()
    scrub.add(SECRET)

    def handler(request):
        msg = "x" * 290 + SECRET  # secret straddles the 300-char cut
        return httpx.Response(400, json={"error": "E", "message": msg})

    http = poster.Http(frozenset({"bsky.social"}), scrub, transport=httpx.MockTransport(handler))
    with pytest.raises(poster.PosterError) as ei:
        http.post_json("https://bsky.social/xrpc/x", {})
    assert SECRET[:6] not in str(ei.value)


def test_poster_error_message_scrubbed_directly():
    scrub = poster.Scrubber()
    scrub.add(SECRET)
    rec = Recorder(fail_on="createSession")
    http = poster.Http(frozenset({"bsky.social"}), scrub, transport=rec.transport())
    with pytest.raises(poster.PosterError) as ei:
        http.post_json("https://bsky.social/xrpc/com.atproto.server.createSession", {})
    assert SECRET not in str(ei.value)
    assert ei.value.__cause__ is None and ei.value.__context__ is None


def test_secrets_absent_from_success_logs(files, caplog, capsys):
    with caplog.at_level(logging.DEBUG):
        assert do_run(files, Recorder()) == 0
    captured = capsys.readouterr()
    blob = caplog.text + captured.out + captured.err + files[1].read_text("utf-8")
    blob += files[0].read_text("utf-8")
    for s in (SECRET, JWT, REFRESH, "nope", "x@example.invalid"):
        assert s not in blob


def test_backend_repr_hides_credentials(files):
    b = poster.BlueskyBackend()
    assert b.load_credentials(fake_keyring(FULL_KEYS), poster.Scrubber())
    assert SECRET not in repr(b)


def test_mastodon_stub_interface():
    m = poster.MastodonBackend()
    assert m.length_error("x" * 500) is None and m.length_error("x" * 501)
    with pytest.raises(NotImplementedError):
        m.load_credentials(fake_keyring({}), poster.Scrubber())
    assert "mastodon" not in poster.BACKENDS


# ----------------------------------------------------------------------------- qa-security (SEC-57..59)


def _create_record_count(rec: Recorder) -> int:
    return sum(r.url.path.endswith("createRecord") for r in rec.requests)


def test_qa_never_reads_password_or_email_fields(files, monkeypatch):
    accessed: list[str] = []

    class Tracking(dict):
        def __getitem__(self, key):
            accessed.append(key)
            return super().__getitem__(key)

        def get(self, key, default=None):
            accessed.append(key)
            return super().get(key, default)

    monkeypatch.delenv(poster.HANDLE_ENV, raising=False)
    real_loads = json.loads
    def loads(s, *a, **k):
        data = real_loads(s, *a, **k)
        return Tracking(data) if s == FULL_KEYS["bluesky"] else data

    monkeypatch.setattr(poster.json, "loads", loads)
    rec = Recorder()
    assert do_run(files, rec) == 0
    assert accessed and set(accessed) <= {"handle", "user"}
    session = json.loads(rec.requests[0].content)
    assert session == {"identifier": HANDLE, "password": SECRET}
    for r in rec.requests:
        assert b"nope" not in r.content and b"x@example.invalid" not in r.content


@pytest.mark.parametrize(
    "text",
    [
        "See https://freemyid.org/faq/ (and https://github.com/FreeMyID/freemyid).",
        "\U0001f1fa\U0001f1f8 café https://freemyid.org/a_(b) next https://freemyid.org!",
        "https://freemyid.org/x?y=1&z=2#frag, done",
    ],
)
def test_qa_facet_uri_equals_visible_bytes(text):
    raw = text.encode("utf-8")
    facets = poster.link_facets(text)
    assert facets
    for f in facets:
        idx, feat = f["index"], f["features"]
        assert len(feat) == 1 and feat[0]["$type"] == "app.bsky.richtext.facet#link"
        assert raw[idx["byteStart"]:idx["byteEnd"]].decode("utf-8") == feat[0]["uri"]


def test_qa_redirect_is_not_followed():
    rec_hosts: list[str] = []

    def handler(request):
        rec_hosts.append(request.url.host)
        return httpx.Response(302, headers={"Location": "https://evil.example/xrpc/x"})

    http = poster.Http(frozenset({"bsky.social"}), poster.Scrubber(),
                       transport=httpx.MockTransport(handler))
    with pytest.raises(poster.PosterError):
        http.post_json("https://bsky.social/xrpc/x", {})
    assert rec_hosts == ["bsky.social"]


def test_qa_proxy_env_ignored(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:9")
    http = poster.Http(frozenset({"bsky.social"}), poster.Scrubber())
    assert http._client._trust_env is False
    assert not http._client._mounts  # no env-derived proxy mounts
    http.close()


def test_qa_network_error_has_no_exception_context():
    scrub = poster.Scrubber()
    scrub.add(SECRET)

    def explode(request):
        raise httpx.ReadTimeout(f"t {SECRET}", request=request)

    http = poster.Http(frozenset({"bsky.social"}), scrub, transport=httpx.MockTransport(explode))
    with pytest.raises(poster.PosterError) as ei:
        http.post_json("https://bsky.social/xrpc/x", {"password": SECRET})
    assert SECRET not in str(ei.value)
    assert ei.value.__cause__ is None and ei.value.__suppress_context__ is True


def test_qa_all_loggers_debug_hold_no_secrets(files, caplog, capsys):
    with caplog.at_level(logging.DEBUG, logger=""):
        for name in ("httpx", "httpcore"):
            logging.getLogger(name).setLevel(logging.DEBUG)
        assert do_run(files, Recorder()) == 0
    blob = caplog.text + "".join(capsys.readouterr())
    for s in (SECRET, JWT, REFRESH):
        assert s not in blob


def _ambiguous_failure(kind: str, monkeypatch):
    """Make run 1 fail after createRecord reached the server; return a Recorder for run 1."""
    rec = Recorder()
    if kind == "read-timeout":
        def handler(request):
            resp = rec(request)
            if request.url.path.endswith("createRecord"):
                raise httpx.ReadTimeout("server created it, reply lost", request=request)
            return resp
        rec.transport = lambda: httpx.MockTransport(handler)  # type: ignore[method-assign]
    elif kind == "queue-write-oserror":
        real = poster.atomic_write

        def flaky(path, content):
            if path.name == "bluesky-queue.md" and "status: posted 2026-11-07" in content:
                raise OSError("disk full")
            real(path, content)
        monkeypatch.setattr(poster, "atomic_write", flaky)
    elif kind == "bad-uri":
        def handler(request):
            if request.url.path.endswith("createRecord"):
                rec.requests.append(request)
                return httpx.Response(200, json={"uri": URI + "\nstatus: queued"})
            return rec(request)
        rec.transport = lambda: httpx.MockTransport(handler)  # type: ignore[method-assign]
    return rec


@pytest.mark.parametrize("kind", ["read-timeout", "queue-write-oserror", "bad-uri"])
def test_qa_sec57_no_repost_after_ambiguous_failure(files, kind, monkeypatch):
    rec1 = _ambiguous_failure(kind, monkeypatch)
    assert do_run(files, rec1) != poster.EXIT_OK
    monkeypatch.undo()
    rec2 = Recorder()
    do_run(files, rec2)  # the next timer run (or a Persistent=true catch-up)
    q2 = [r for r in rec2.requests if r.url.path.endswith("createRecord")]
    first_text = "Free My ID removes you"
    reposted = [r for r in q2 if first_text in r.content.decode()]
    assert _create_record_count(rec1) == 1 and reposted == []


@pytest.mark.xfail(strict=True, reason="SEC-58: invisible/bidi characters are accepted in links")
@pytest.mark.parametrize("ch", ["\u200b", "\u202e", "\u2060", "\ufeff"])
def test_qa_sec58_invisible_chars_never_reach_a_facet(ch):
    text = f"Visit https://freemyid.org{ch}.evil.example/ today"
    for f in poster.link_facets(text):
        uri = f["features"][0]["uri"]
        assert not any(unicodedata.category(c) == "Cf" for c in uri)


# ----------------------------------------------------------------------------- SEC-57 state


def _status(q: Path, item_id: str) -> str:
    return {i.item_id: i for i in poster.parse_queue(q.read_text("utf-8"))}[item_id].status


def test_sec57_claim_is_written_before_anything_is_sent(files):
    q, _ = files
    seen: list[str] = []
    rec = Recorder()

    def handler(request):
        seen.append(_status(q, "Q-002"))
        return rec(request)

    rc = poster.run(
        backend=poster.BlueskyBackend(), queue_path=q, outreach_path=files[1],
        kr_get=fake_keyring(FULL_KEYS), transport=httpx.MockTransport(handler), now=lambda: NOW,
    )
    assert rc == poster.EXIT_OK
    assert seen == ["posting 2026-11-07T15:00:00Z"] * 2
    assert _status(q, "Q-002") == f"posted 2026-11-07T15:00:00Z {URI}"


@pytest.mark.parametrize("status", [500, 502, 503])
def test_sec57_server_error_on_create_record_stays_posting(files, status):
    rec = Recorder(fail_on="createRecord", status=status)
    assert do_run(files, rec) == poster.EXIT_CHECK
    assert _status(files[0], "Q-002").startswith("posting ")
    assert files[1].read_text("utf-8") == LOG


def test_sec57_connect_error_on_create_record_goes_back_to_queued(files):
    rec = Recorder()

    def handler(request):
        if request.url.path.endswith("createRecord"):
            raise httpx.ConnectError("refused", request=request)
        return rec(request)

    rc = poster.run(
        backend=poster.BlueskyBackend(), queue_path=files[0], outreach_path=files[1],
        kr_get=fake_keyring(FULL_KEYS), transport=httpx.MockTransport(handler), now=lambda: NOW,
    )
    assert rc == poster.EXIT_HTTP
    assert files[0].read_text("utf-8") == QUEUE


def test_sec57_kill_during_post_leaves_posting_and_blocks_all_posting(files, caplog):
    q, _ = files
    rec = Recorder()

    def handler(request):
        if request.url.path.endswith("createRecord"):
            raise KeyboardInterrupt  # stands in for SIGTERM/power loss mid-request
        return rec(request)

    with pytest.raises(KeyboardInterrupt):
        poster.run(
            backend=poster.BlueskyBackend(), queue_path=q, outreach_path=files[1],
            kr_get=fake_keyring(FULL_KEYS), transport=httpx.MockTransport(handler),
            now=lambda: NOW,
        )
    assert _status(q, "Q-002").startswith("posting ")
    rec2 = Recorder()
    with caplog.at_level(logging.ERROR):
        assert do_run(files, rec2) == poster.EXIT_CHECK
    assert rec2.requests == []  # Q-003 is not posted either until a human looks
    assert "Check the account" in caplog.text
    # dry-run reports the stuck item too, without touching anything
    assert do_run(files, Recorder(), dry_run=True) == poster.EXIT_CHECK


def test_sec57_revert_failure_stays_posting(files, monkeypatch):
    real = poster.atomic_write

    def flaky(path, content):
        if "status: queued\n```text\nFree My ID removes" in content:
            raise OSError("disk full")
        real(path, content)

    monkeypatch.setattr(poster, "atomic_write", flaky)
    rec = Recorder(fail_on="createSession", status=401)
    assert do_run(files, rec) == poster.EXIT_CHECK
    assert _status(files[0], "Q-002").startswith("posting ")


def test_sec57_claim_failure_sends_nothing(files, monkeypatch):
    def broken(path, content):
        raise OSError("read-only")

    monkeypatch.setattr(poster, "atomic_write", broken)
    rec = Recorder()
    assert do_run(files, rec) == poster.EXIT_USAGE
    assert rec.requests == []
    assert files[0].read_text("utf-8") == QUEUE


def test_sec57_lock_held_skips_without_sending(files):
    q, _ = files
    fd = poster._try_lock(poster.lock_path(q))
    assert fd is not None
    try:
        rec = Recorder()
        assert do_run(files, rec) == poster.EXIT_OK
        assert rec.requests == []
        assert q.read_text("utf-8") == QUEUE
    finally:
        os.close(fd)
    rec = Recorder()
    assert do_run(files, rec) == poster.EXIT_OK
    assert len(rec.requests) == 2


def test_sec57_dry_run_creates_no_lock_file(files):
    q, _ = files
    assert do_run(files, Recorder(), dry_run=True) == poster.EXIT_OK
    assert not poster.lock_path(q).exists()


@pytest.mark.parametrize(
    "uri",
    [
        URI + "\n",
        URI + "|x",
        URI + " ",
        "at://did:plc:someoneelse/app.bsky.feed.post/3kfakerkey",
        f"at://{DID}/app.bsky.feed.like/3kfakerkey",
        f"at://{DID}/app.bsky.feed.post/",
        f"at://{DID}/app.bsky.feed.post/" + "a" * 513,
        f"at://{DID}/app.bsky.feed.post/rkаy",
    ],
)
def test_sec57_strict_at_uri(files, uri):
    rec = Recorder()

    def handler(request):
        if request.url.path.endswith("createRecord"):
            return httpx.Response(200, json={"uri": uri})
        return rec(request)

    rc = poster.run(
        backend=poster.BlueskyBackend(), queue_path=files[0], outreach_path=files[1],
        kr_get=fake_keyring(FULL_KEYS), transport=httpx.MockTransport(handler), now=lambda: NOW,
    )
    assert rc == poster.EXIT_CHECK
    assert _status(files[0], "Q-002").startswith("posting ")
    assert files[1].read_text("utf-8") == LOG


def test_sec57_outreach_row_escapes_uri_and_url():
    item = poster.parse_queue(QUEUE)[1]
    row = poster.outreach_row(
        NOW, poster.BlueskyBackend(), item, poster.PostResult(uri="at://a|b", web_url="https://x|y")
    )
    assert "a\\|b" in row and "x\\|y" in row
