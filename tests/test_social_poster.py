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


@pytest.fixture(autouse=True)
def ledger_dir(tmp_path: Path, monkeypatch) -> Path:
    """Every test gets its own posted ledger; never the real ~/.local/state (SEC-77)."""
    d = tmp_path / "state" / "freemyid-poster"
    monkeypatch.setenv("STATE_DIRECTORY", str(d))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    assert poster.default_ledger_path() == d / "posted.jsonl"
    return d


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


@pytest.mark.posix_only
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
    text = ("Café 🇺🇸 👨\u200d👩\u200d👧 privacy — https://freemyid.org/%C3%BCber?a=1 and "
            "(https://example.org/x)!")
    facets = poster.link_facets(text)
    raw = text.encode("utf-8")
    got = [raw[f["index"]["byteStart"] : f["index"]["byteEnd"]].decode() for f in facets]
    assert got == ["https://freemyid.org/%C3%BCber?a=1", "https://example.org/x"]
    assert [f["features"][0]["uri"] for f in facets] == got
    # char offset differs from byte offset because of the multibyte prefix
    assert facets[0]["index"]["byteStart"] > text.index("https://")


def test_facets_ignore_http_and_bare_scheme():
    assert poster.link_facets("http://insecure.example and https:// alone") == []


def test_grapheme_count():
    assert poster.grapheme_count("abc") == 3
    assert poster.grapheme_count("🇺🇸") == 1
    assert poster.grapheme_count("👨\u200d👩\u200d👧") == 1
    assert poster.grapheme_count("👍🏽") == 1
    assert poster.grapheme_count("é") == 1
    assert poster.grapheme_count("❤️") == 1


@pytest.mark.posix_only
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


@pytest.mark.posix_only
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


@pytest.mark.posix_only
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


@pytest.mark.posix_only
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
@pytest.mark.posix_only
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


@pytest.mark.posix_only
def test_handle_override_and_env(files, monkeypatch):
    rec = Recorder()
    monkeypatch.setenv(poster.HANDLE_ENV, "@env.bsky.social")
    q, o = files
    assert poster.run(
        backend=poster.BlueskyBackend(), queue_path=q, outreach_path=o,
        kr_get=fake_keyring({"bluesky_token": SECRET}), transport=rec.transport(), now=lambda: NOW,
    ) == 0
    assert json.loads(rec.requests[0].content)["identifier"] == "env.bsky.social"


@pytest.mark.posix_only
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


@pytest.mark.posix_only
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


@pytest.mark.posix_only
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


@pytest.mark.posix_only
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


@pytest.mark.posix_only
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


@pytest.mark.posix_only
def test_secrets_absent_from_success_logs(files, caplog, capsys):
    with caplog.at_level(logging.DEBUG):
        assert do_run(files, Recorder()) == 0
    captured = capsys.readouterr()
    blob = caplog.text + captured.out + captured.err + files[1].read_text("utf-8")
    blob += files[0].read_text("utf-8")
    for s in (SECRET, JWT, REFRESH, "nope", "x@example.invalid"):
        assert s not in blob


@pytest.mark.posix_only
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


@pytest.mark.posix_only
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


@pytest.mark.posix_only
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


@pytest.mark.posix_only
@pytest.mark.parametrize("kind", ["read-timeout", "queue-write-oserror", "bad-uri"])
def test_qa_sec57_no_repost_after_ambiguous_failure(files, kind):
    # Own MonkeyPatch: undoing the shared one would also drop the ledger_dir env and
    # send the second run to the real ~/.local/state.
    with pytest.MonkeyPatch.context() as mp:
        rec1 = _ambiguous_failure(kind, mp)
        assert do_run(files, rec1) != poster.EXIT_OK
    rec2 = Recorder()
    do_run(files, rec2)  # the next timer run (or a Persistent=true catch-up)
    q2 = [r for r in rec2.requests if r.url.path.endswith("createRecord")]
    first_text = "Free My ID removes you"
    reposted = [r for r in q2 if first_text in r.content.decode()]
    assert _create_record_count(rec1) == 1 and reposted == []


@pytest.mark.parametrize("ch", ["\u200b", "\u202e", "\u2060", "\ufeff"])
def test_qa_sec58_invisible_chars_never_reach_a_facet(ch):
    text = f"Visit https://freemyid.org{ch}.evil.example/ today"
    for f in poster.link_facets(text):
        uri = f["features"][0]["uri"]
        assert not any(unicodedata.category(c) == "Cf" for c in uri)


# ----------------------------------------------------------------------------- SEC-57 state


def _status(q: Path, item_id: str) -> str:
    return {i.item_id: i for i in poster.parse_queue(q.read_text("utf-8"))}[item_id].status


@pytest.mark.posix_only
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


@pytest.mark.posix_only
@pytest.mark.parametrize("status", [500, 502, 503])
def test_sec57_server_error_on_create_record_stays_posting(files, status):
    rec = Recorder(fail_on="createRecord", status=status)
    assert do_run(files, rec) == poster.EXIT_CHECK
    assert _status(files[0], "Q-002").startswith("posting ")
    assert files[1].read_text("utf-8") == LOG


@pytest.mark.posix_only
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


@pytest.mark.posix_only
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


@pytest.mark.posix_only
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


@pytest.mark.posix_only
def test_sec57_claim_failure_sends_nothing(files, monkeypatch):
    def broken(path, content):
        raise OSError("read-only")

    monkeypatch.setattr(poster, "atomic_write", broken)
    rec = Recorder()
    assert do_run(files, rec) == poster.EXIT_USAGE
    assert rec.requests == []
    assert files[0].read_text("utf-8") == QUEUE


@pytest.mark.posix_only
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


@pytest.mark.posix_only
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
@pytest.mark.posix_only
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
    ledger = files[0].parent / "state" / "freemyid-poster" / "posted.jsonl"
    assert [r["status"] for r in map(json.loads, ledger.read_text().splitlines())
            if r["id"] == "Q-002"] == ["claimed", "unknown"]
    assert files[1].read_text("utf-8") == LOG


def test_sec57_outreach_row_escapes_uri_and_url():
    item = poster.parse_queue(QUEUE)[1]
    row = poster.outreach_row(
        NOW, poster.BlueskyBackend(), item, poster.PostResult(uri="at://a|b", web_url="https://x|y")
    )
    assert "a\\|b" in row and "x\\|y" in row


# ----------------------------------------------------------------------------- SEC-58


@pytest.mark.parametrize(
    "ch", ["\u200b", "\u200c", "\u200e", "\u202a", "\u202e", "\u2060", "\u2066", "\u2069",
           "\ufeff", "\u00ad"],
)
@pytest.mark.posix_only
def test_sec58_item_with_hidden_char_is_skipped_and_next_posted(files, ch, caplog):
    q, _ = files
    q.write_text(QUEUE.replace("https://freemyid.org", f"https://freemyid.org{ch}.evil.example/"),
                 "utf-8")
    rec = Recorder()
    with caplog.at_level(logging.WARNING):
        assert do_run(files, rec) == poster.EXIT_OK
    assert "Q-002 has an invisible/bidi character" in caplog.text
    assert json.loads(rec.requests[-1].content)["record"]["text"] == "Second queued post."
    assert _status(q, "Q-002") == "queued"


@pytest.mark.parametrize(
    "text",
    [
        "Family \U0001f468\u200d\U0001f469\u200d\U0001f467 https://freemyid.org/über",
        "Pride \U0001f3f3️\u200d\U0001f308 flag",
        "Wales \U0001f3f4\U000e0067\U000e0062\U000e0077\U000e006c\U000e0073\U000e007f",
        "Skin \U0001f44d\U0001f3fd\u200d♂️ ok",
        "Plain text https://github.com/FreeMyID/freemyid (über)",
    ],
)
def test_sec58_emoji_sequences_and_idn_paths_still_allowed(text):
    assert poster.hidden_char_error(text) is None


@pytest.mark.parametrize(
    "text",
    ["a\u200db", "\u200d\U0001f468", "x\U000e0067\U000e007f", "\U0001f468\u200d", "\u2067rtl"],
)
def test_sec58_stray_joiners_and_tags_refused(text):
    assert poster.hidden_char_error(text) is not None


def test_sec58_url_followed_by_hidden_char_gets_no_facet():
    assert poster.link_facets("see https://freemyid.org\u200b now") == []
    # SEC-79: printable ASCII only in a link. A raw non-ASCII path gets no facet (the
    # text is still posted); the %-encoded form is linked.
    assert poster.link_facets("see https://freemyid.org/über now") == []
    assert len(poster.link_facets("see https://freemyid.org/%C3%BCber now")) == 1


# ----------------------------------------------------------------------------- SEC-59 install.sh

SOCIAL = ROOT / "tools" / "social"
# systemd-analyze --user needs a short real runtime dir; captured before any fixture runs
_UID = os.getuid() if hasattr(os, "getuid") else 0  # module must import on Windows
_RUNTIME_DIR = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{_UID}"
INSTALL_FILES = ("install.sh", "poster.py", "verify.sh", "requirements.lock",
                 "freemyid-poster.service", "freemyid-poster.timer")


def _hermetic_env(home: Path, bin_dir: Path, tmp: Path) -> dict[str, str]:
    """Minimal env for every subprocess: nothing leaks in from the caller or other tests."""
    return {
        "HOME": str(home),
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "TMPDIR": str(tmp),
        "LC_ALL": "C",
        "FREEMYID_POSTER_TEST_SKIP_PIP": "1",
    }


@pytest.fixture
def sandbox(tmp_path: Path, monkeypatch):
    """A fake repo and a temp HOME. Nothing outside tmp_path is touched."""
    import shutil
    import stat

    tmp_path = tmp_path.resolve()  # install.sh uses pwd -P; compare like with like
    for key in list(os.environ):
        if key.startswith(("XDG_", "PYTHON", "FREEMYID_", "VIRTUAL_ENV", "PIP_")):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    repo = tmp_path / "repo"
    (repo / "tools" / "social").mkdir(parents=True)
    (repo / "docs" / "marketing" / "seo").mkdir(parents=True)
    for name in INSTALL_FILES:
        shutil.copy2(SOCIAL / name, repo / "tools" / "social" / name)
    home = tmp_path / "home"
    home.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "systemctl-calls"
    fake = bin_dir / "systemctl"
    fake.write_text(f"#!/bin/sh\necho \"$@\" >> {calls}\n")
    fake.chmod(0o755)
    (tmp_path / "tmp").mkdir()
    yield repo, home, bin_dir, calls
    for p in [tmp_path, *tmp_path.rglob("*")]:  # read-only tree: let pytest clean it up
        if not p.is_symlink():
            p.chmod(p.stat().st_mode | stat.S_IWUSR)


def _system_python() -> str:
    """A root-owned Python >= 3.12 for install.sh (it refuses user-owned ones, SEC-81b)."""
    import subprocess

    for cand in ("/usr/bin/python3", "/usr/local/bin/python3"):
        real = os.path.realpath(cand)
        if os.path.isfile(real) and os.stat(real).st_uid == 0:
            ok = subprocess.run([real, "-I", "-c", "import sys; sys.exit(sys.version_info < (3, 12))"],
                                check=False, capture_output=True, timeout=30).returncode == 0
            if ok:
                return cand
    pytest.skip("no root-owned Python >= 3.12 for install.sh")


def run_install(sandbox, *args: str, uid0: bool = False):
    import subprocess

    repo, home, bin_dir, _ = sandbox
    if uid0:
        fake_id = bin_dir / "id"
        fake_id.write_text("#!/bin/sh\necho 0\n")
        fake_id.chmod(0o755)
    return subprocess.run(
        ["/bin/bash", str(repo / "tools" / "social" / "install.sh"),
         "--python", _system_python(), *args],
        check=False, env=_hermetic_env(home, bin_dir, home.parent / "tmp"),
        capture_output=True, text=True, timeout=120, cwd=home, umask=0o022,
    )


def _paths(home: Path) -> tuple[Path, Path, Path]:
    prefix = home / ".local" / "share" / "freemyid-poster"
    units = home / ".config" / "systemd" / "user"
    return prefix, units / "freemyid-poster.service", units / "freemyid-poster.timer"


def _pre_checks(unit: Path) -> list[int]:
    """Run each ExecStartPre the way systemd would (shell-like word splitting)."""
    import shlex
    import subprocess

    home = unit.parents[3]  # <home>/.config/systemd/user/<unit>
    env = _hermetic_env(home, home.parent / "bin", home.parent / "tmp")
    rcs = []
    for line in unit.read_text().splitlines():
        if line.startswith("ExecStartPre="):
            argv = shlex.split(line.removeprefix("ExecStartPre="))
            res = subprocess.run(argv, check=False, capture_output=True, timeout=60, env=env,
                                 cwd="/", umask=0o022)
            rcs.append(res.returncode)
    return rcs


def _pinned(unit: Path) -> str:
    import re

    m = re.search(r'echo "([0-9a-f]{64})  SHA256SUMS"', unit.read_text())
    assert m
    return m.group(1)


@pytest.mark.linux_only
def test_sec59_install_layout_permissions_and_pin(sandbox):
    import hashlib
    import re
    import stat

    repo, home, _, calls = sandbox
    res = run_install(sandbox)
    assert res.returncode == 0, res.stdout + res.stderr
    prefix, service, timer = _paths(home)
    assert stat.S_IMODE(prefix.stat().st_mode) == 0o555
    assert stat.S_IMODE((prefix / "poster.py").stat().st_mode) == 0o444
    for p in prefix.rglob("*"):
        if not p.is_symlink():
            assert p.stat().st_mode & 0o222 == 0, p
    for unit in (service, timer):
        assert not unit.is_symlink()
        assert stat.S_IMODE(unit.stat().st_mode) == 0o444
        assert not re.search(r"@[A-Z_0-9]+@", unit.read_text())
    assert timer.read_text() == (repo / "tools/social/freemyid-poster.timer").read_text()
    text = service.read_text()
    assert f"ExecStart={prefix}/venv/bin/python -I -B {prefix}/poster.py" in text
    assert f"ReadWritePaths={repo}/docs/marketing/seo" in text
    for real in (ROOT / "tools", ROOT / ".venv", ROOT / "docs"):
        assert f"{real}/" not in text  # never points at the real repo
    sums = hashlib.sha256((prefix / "SHA256SUMS").read_bytes()).hexdigest()
    assert _pinned(service) == sums and sums in res.stdout
    assert (prefix / "poster.py").read_bytes() == (SOCIAL / "poster.py").read_bytes()
    assert _pre_checks(service) == [0, 0, 0]
    assert not calls.exists()  # never runs systemctl, never enables the timer
    assert "enable --now freemyid-poster.timer" in res.stdout  # only printed


@pytest.mark.linux_only
@pytest.mark.parametrize("tamper", ["poster", "pth", "symlink", "sums", "writable"])
def test_sec59_any_change_to_the_copy_refuses_to_start(sandbox, tamper):
    _, home, _, _ = sandbox
    assert run_install(sandbox).returncode == 0
    prefix, service, _ = _paths(home)
    site = next(prefix.glob("venv/lib/python3*/site-packages"))
    if tamper == "poster":
        target = prefix / "poster.py"
        target.chmod(0o644)
        target.write_text(target.read_text() + "\n# changed\n")
        target.chmod(0o444)
    elif tamper == "pth":
        site.chmod(0o755)
        (site / "evil.pth").write_text("import os\n")
        (site / "evil.pth").chmod(0o444)
        site.chmod(0o555)
    elif tamper == "symlink":
        site.chmod(0o755)
        (site / "keyring").symlink_to("/tmp")
        site.chmod(0o555)
    elif tamper == "sums":
        prefix.chmod(0o755)
        (prefix / "SHA256SUMS").chmod(0o644)
        with (prefix / "SHA256SUMS").open("a") as fh:
            fh.write("0" * 64 + "  extra\n")
        (prefix / "SHA256SUMS").chmod(0o444)
        prefix.chmod(0o555)
    elif tamper == "writable":
        (prefix / "poster.py").chmod(0o644)
    assert any(rc != 0 for rc in _pre_checks(service))


@pytest.mark.linux_only
def test_sec59_update_repins_and_install_refuses_twice(sandbox):
    repo, home, _, _ = sandbox
    assert run_install(sandbox).returncode == 0
    prefix, service, _ = _paths(home)
    first = _pinned(service)
    again = run_install(sandbox)
    assert again.returncode != 0 and "--update" in again.stderr
    src = repo / "tools/social/poster.py"
    src.write_text(src.read_text() + "\n# reviewed change\n")
    res = run_install(sandbox, "--update")
    assert res.returncode == 0, res.stderr
    assert _pinned(service) != first and _pinned(service) in res.stdout
    assert (prefix / "poster.py").read_text().endswith("# reviewed change\n")
    assert _pre_checks(service) == [0, 0, 0]


@pytest.mark.linux_only
def test_sec59_update_needs_existing_install(sandbox):
    res = run_install(sandbox, "--update")
    assert res.returncode != 0 and "nothing installed" in res.stderr


@pytest.mark.linux_only
def test_sec59_refuses_root(sandbox):
    _, home, _, _ = sandbox
    res = run_install(sandbox, uid0=True)
    assert res.returncode != 0 and "root" in res.stderr
    assert not (home / ".local").exists() and not (home / ".config").exists()


@pytest.mark.linux_only
def test_sec59_replaces_old_symlinked_unit_not_its_target(sandbox, tmp_path):
    _, home, _, _ = sandbox
    target = tmp_path / "old-target.service"
    target.write_text("old\n")
    units = home / ".config" / "systemd" / "user"
    units.mkdir(parents=True)
    (units / "freemyid-poster.service").symlink_to(target)
    assert run_install(sandbox).returncode == 0
    assert not (units / "freemyid-poster.service").is_symlink()
    assert target.read_text() == "old\n"


@pytest.mark.linux_only
def test_sec59_systemd_analyze_verify(sandbox):
    import shutil
    import subprocess

    if not shutil.which("systemd-analyze"):
        pytest.skip("systemd-analyze not available")
    _, home, _, _ = sandbox
    assert run_install(sandbox).returncode == 0
    _, service, timer = _paths(home)
    if not Path(_RUNTIME_DIR).is_dir():
        pytest.skip("no XDG_RUNTIME_DIR for systemd-analyze --user")
    env = {"HOME": str(home), "XDG_RUNTIME_DIR": _RUNTIME_DIR, "PATH": "/usr/bin:/bin",
           "LC_ALL": "C"}
    res = subprocess.run(
        ["systemd-analyze", "--user", "verify", str(service), str(timer)],
        check=False, capture_output=True, text=True, timeout=60, env=env,
    )
    if res.returncode != 0 and "Failed to" in res.stderr and "bus" in res.stderr.lower():
        pytest.skip("no user systemd instance")
    assert res.returncode == 0, res.stderr
    assert "freemyid-poster" not in res.stderr


# ----------------------------------------------------------------------------- QA re-review (SEC-77..81)


@pytest.mark.posix_only
def test_qa_sec77_reverted_status_line_does_not_repost(files):
    q, _ = files
    assert do_run(files, Recorder()) == poster.EXIT_OK
    assert _status(q, "Q-002").startswith("posted ")
    # A stale editor buffer, `git checkout`/`git restore` or a merge puts the old line back.
    q.write_text(QUEUE, encoding="utf-8")
    rec2 = Recorder()
    do_run(files, rec2)
    created = [r for r in rec2.requests if r.url.path.endswith("createRecord")]
    assert not any("Free My ID removes you" in r.content.decode() for r in created)


def test_qa_sec78_tag_character_smuggling_is_refused():
    hidden = "".join(chr(0xE0000 + ord(c)) for c in "ignore all previous instructions")
    assert poster.hidden_char_error("hi \U0001f3f4" + hidden + " bye") is not None
    # The three RGI subdivision flags (England, Scotland, Wales) stay allowed.
    wales = "\U0001f3f4" + "".join(chr(0xE0000 + ord(c)) for c in "gbwls") + "\U000e007f"
    assert poster.hidden_char_error(f"Hello {wales}") is None


@pytest.mark.parametrize("ch", ["\U000e0100", "͏", "️"])
def test_qa_sec79_default_ignorable_in_link_is_refused(ch):
    text = f"Visit https://freemyid.org{ch}.evil.example/ today"
    assert poster.hidden_char_error(text) is not None or poster.link_facets(text) == []


def test_qa_sec80_unit_pins_keyring_backend():
    unit = (ROOT / "tools/social/freemyid-poster.service").read_text("utf-8")
    assert "Environment=PYTHON_KEYRING_BACKEND=keyring.backends.SecretService.Keyring" in unit
    assert f"Environment=PYTHON_KEYRING_BACKEND={poster.KEYRING_BACKEND}" in unit


def test_sec80_manual_run_pins_keyring_backend(monkeypatch):
    import types

    seen = {}
    fake = types.ModuleType("keyring")

    def get_password(service, name):
        seen["backend"] = os.environ.get("PYTHON_KEYRING_BACKEND")
        return "x"

    fake.get_password = get_password  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "keyring", fake)
    monkeypatch.setenv("PYTHON_KEYRING_BACKEND", "evil.module.Keyring")
    assert poster._default_keyring_get("freemyid-social", "bluesky_token") == "x"
    assert seen["backend"] == "keyring.backends.SecretService.Keyring"


@pytest.mark.posix_only
def test_qa_sec81_unexpected_error_after_claim_returns_check(files):
    rec = Recorder()

    def handler(request):
        if request.url.path.endswith("createRecord"):
            raise RecursionError("deeply nested reply")  # not an httpx error
        return rec(request)

    rc = poster.run(
        backend=poster.BlueskyBackend(), queue_path=files[0], outreach_path=files[1],
        kr_get=fake_keyring(FULL_KEYS), transport=httpx.MockTransport(handler), now=lambda: NOW,
    )
    assert rc == poster.EXIT_CHECK
    assert _status(files[0], "Q-002").startswith("posting ")
    ledger = files[0].parent / "state" / "freemyid-poster" / "posted.jsonl"
    assert [r["status"] for r in map(json.loads, ledger.read_text().splitlines())
            if r["id"] == "Q-002"] == ["claimed", "unknown"]


# ----------------------------------------------------------------------------- SEC-77 ledger


def _ledger(ledger_dir: Path, item: str | None = "Q-002") -> list[dict]:
    """Ledger records, by default only Q-002's (Q-001 is adopted as posted on every run)."""
    path = ledger_dir / "posted.jsonl"
    if not path.exists():
        return []
    recs = [json.loads(line) for line in path.read_text("utf-8").splitlines()]
    return [r for r in recs if item is None or r["id"] == item]


@pytest.mark.posix_only
def test_sec77_ledger_records_claim_then_posted(files, ledger_dir):
    seen_at_send = []

    rec = Recorder()

    def handler(request):
        if request.url.path.endswith("createRecord"):
            seen_at_send.append([r["status"] for r in _ledger(ledger_dir)])
        return rec(request)

    rc = poster.run(
        backend=poster.BlueskyBackend(), queue_path=files[0], outreach_path=files[1],
        kr_get=fake_keyring(FULL_KEYS), transport=httpx.MockTransport(handler), now=lambda: NOW,
    )
    assert rc == poster.EXIT_OK
    assert seen_at_send == [["claimed"]]  # fsynced before the post was sent
    recs = _ledger(ledger_dir)
    assert [(r["id"], r["status"]) for r in recs] == [("Q-002", "claimed"), ("Q-002", "posted")]
    assert recs[1]["uri"] == URI
    assert recs[0]["sha256"] == poster.text_hash(poster.parse_queue(QUEUE)[1].text)
    assert ledger_dir.stat().st_mode & 0o777 == 0o700
    assert (ledger_dir / "posted.jsonl").stat().st_mode & 0o777 == 0o600


@pytest.mark.posix_only
def test_sec77_reverted_line_exits_check_with_plain_message(files, caplog):
    assert do_run(files, Recorder()) == poster.EXIT_OK
    files[0].write_text(QUEUE, encoding="utf-8")
    rec = Recorder()
    with caplog.at_level(logging.ERROR):
        assert do_run(files, rec) == poster.EXIT_CHECK
    assert rec.requests == []
    assert "NOT posted again" in caplog.text and "Q-002" in caplog.text


@pytest.mark.posix_only
def test_sec77_same_text_under_new_id_is_refused(files):
    q, _ = files
    assert do_run(files, Recorder()) == poster.EXIT_OK
    text = poster.parse_queue(QUEUE)[1].text
    q.write_text(q.read_text("utf-8") + f"\n## Q-099\nstatus: queued\n```text\n{text}\n```\n",
                 encoding="utf-8")
    # Q-003 is next in order; post it, then Q-099 (same text as Q-002) must be refused
    assert do_run(files, Recorder()) == poster.EXIT_OK
    rec = Recorder()
    assert do_run(files, rec) == poster.EXIT_CHECK
    assert rec.requests == []


@pytest.mark.posix_only
def test_sec77_definite_failure_releases_and_retry_posts(files, ledger_dir):
    assert do_run(files, Recorder(fail_on="createSession", status=401)) == poster.EXIT_HTTP
    assert [r["status"] for r in _ledger(ledger_dir)] == ["claimed", "released"]
    assert _status(files[0], "Q-002") == "queued"
    assert do_run(files, Recorder()) == poster.EXIT_OK
    assert _status(files[0], "Q-002").startswith("posted ")


@pytest.mark.posix_only
def test_sec77_unknown_outcome_then_release(files, ledger_dir, monkeypatch):
    rec1 = _ambiguous_failure("read-timeout", monkeypatch)
    assert do_run(files, rec1) == poster.EXIT_CHECK
    assert [r["status"] for r in _ledger(ledger_dir)] == ["claimed", "unknown"]
    # A human checks the account, finds nothing, and puts the line back to queued.
    q = files[0]
    q.write_text(q.read_text("utf-8").replace(_status(q, "Q-002"), "queued"), encoding="utf-8")
    assert do_run(files, Recorder()) == poster.EXIT_CHECK  # the ledger still holds it
    assert poster.main(["--release", "Q-002"]) == poster.EXIT_OK
    assert do_run(files, Recorder()) == poster.EXIT_OK
    assert [r["status"] for r in _ledger(ledger_dir)][-2:] == ["claimed", "posted"]


@pytest.mark.posix_only
def test_sec77_posted_item_is_never_released(files, ledger_dir):
    assert do_run(files, Recorder()) == poster.EXIT_OK
    assert poster.main(["--release", "Q-002"]) == poster.EXIT_USAGE
    assert poster.main(["--release", "Q-777"]) == poster.EXIT_OK  # not held: no-op
    assert [r["status"] for r in _ledger(ledger_dir)] == ["claimed", "posted"]
    with pytest.raises(SystemExit):
        poster.main(["--release", "../x"])


@pytest.mark.posix_only
def test_sec77_damaged_ledger_blocks_posting(files, ledger_dir):
    ledger_dir.mkdir(parents=True, mode=0o700)
    (ledger_dir / "posted.jsonl").write_text('{"id": "Q-1", "status"', encoding="utf-8")
    (ledger_dir / "posted.jsonl").chmod(0o600)
    rec = Recorder()
    assert do_run(files, rec) == poster.EXIT_CHECK
    assert rec.requests == []


@pytest.mark.posix_only
def test_sec77_ledger_inside_a_git_repo_is_refused(files, tmp_path):
    (tmp_path / "repo" / ".git").mkdir(parents=True)
    rec = Recorder()
    q, o = files
    rc = poster.run(
        backend=poster.BlueskyBackend(), queue_path=q, outreach_path=o,
        kr_get=fake_keyring(FULL_KEYS), transport=rec.transport(), now=lambda: NOW,
        ledger_path=tmp_path / "repo" / "state" / "posted.jsonl",
    )
    assert rc == poster.EXIT_USAGE and rec.requests == []
    assert _status(q, "Q-002") == "queued"


@pytest.mark.posix_only
def test_sec77_dry_run_reads_but_never_creates_the_ledger(files, ledger_dir):
    assert do_run(files, dry_run=True) == poster.EXIT_OK
    assert not ledger_dir.exists()


def test_sec77_unit_uses_state_directory():
    unit = (ROOT / "tools/social/freemyid-poster.service").read_text("utf-8")
    assert "StateDirectory=freemyid-poster" in unit
    assert "StateDirectoryMode=0700" in unit


# ----------------------------------------------------------------------------- SEC-81b --python


@pytest.mark.linux_only
def test_sec81b_install_refuses_user_owned_python(sandbox, tmp_path):
    import shutil

    if os.getuid() == 0:
        pytest.skip("running as root: every copy is root-owned")
    user_py = tmp_path / "mypy-bin" / "python3"
    user_py.parent.mkdir()
    shutil.copy2(os.path.realpath(_system_python()), user_py)
    res = run_install(sandbox, "--python", str(user_py))  # the later --python wins
    assert res.returncode != 0
    assert "not root-owned" in res.stderr
    prefix, service, _ = _paths(sandbox[1])
    assert not prefix.exists() and not service.exists()


@pytest.mark.linux_only
def test_sec81b_install_resolves_a_symlinked_python(sandbox, tmp_path):
    link = tmp_path / "link-bin" / "python3"
    link.parent.mkdir()
    link.symlink_to(_system_python())
    res = run_install(sandbox, "--python", str(link))
    assert res.returncode == 0, res.stderr
    prefix, _, _ = _paths(sandbox[1])
    cfg = (prefix / "venv" / "pyvenv.cfg").read_text("utf-8")
    assert str(link) not in cfg  # the venv never points through the user-owned link


# ----------------------------------------------------------------------------- SEC-78/79


@pytest.mark.parametrize("sub", ["gbeng", "gbsct", "gbwls"])
def test_sec78_rgi_tag_flags_allowed(sub):
    flag = "\U0001f3f4" + "".join(chr(0xE0000 + ord(c)) for c in sub) + "\U000e007f"
    assert poster.hidden_char_error(f"Go {flag} team") is None


@pytest.mark.parametrize("sub", ["gbeng\U000e0041", "usca", "gb", "gbwlsgbwls", ""])
def test_sec78_other_tag_runs_refused(sub):
    tags = "".join(chr(0xE0000 + ord(c)) if c.isascii() else c for c in sub)
    assert poster.hidden_char_error("x \U0001f3f4" + tags + "\U000e007f y") is not None


@pytest.mark.parametrize("text", [
    "Love ❤️ it", "Text style ☺︎ too", "Call 1️⃣ now", "Wow ‼️", "Nice 👍️",
])
def test_sec79_emoji_variation_selectors_allowed(text):
    assert poster.hidden_char_error(text) is None


@pytest.mark.parametrize("ch", ["\u034f", "\u115f", "\u3164", "\uffa0", "\ufe00", "\U000e0100"])
def test_sec79_body_default_ignorables_refused(ch):
    assert poster.hidden_char_error(f"Free{ch}My ID") is not None
    assert poster.hidden_char_error(f"a{ch}") is not None


@pytest.mark.parametrize("url", [
    "https://freemyid.org\u0441.example/",  # Cyrillic look-alike
    "https://\u05d0\u05d1.example/",  # strong RTL letters reorder labels on screen
    "https://freemyid.org/\u00e9t\u00e9",  # raw non-ASCII path
])
def test_sec79_non_ascii_link_gets_no_facet(url):
    assert poster.link_facets(f"see {url} now") == []


@pytest.mark.posix_only
def test_sec77_already_posted_queue_items_are_adopted(files, ledger_dir):
    # Q-001 was posted before the ledger existed; the first real run records it.
    assert do_run(files, Recorder()) == poster.EXIT_OK
    recs = _ledger(ledger_dir, item=None)
    assert recs[0]["id"] == "Q-001" and recs[0]["status"] == "posted"
    q = files[0]
    q.write_text(q.read_text("utf-8").replace(_status(q, "Q-001"), "queued"), encoding="utf-8")
    rec = Recorder()
    assert do_run(files, rec) == poster.EXIT_CHECK
    assert rec.requests == []


# ----------------------------------------------------------------------------- QA re-check (SEC-86, SEC-87)


@pytest.mark.xfail(strict=True, reason="SEC-86: a run of VS15/VS16 after an emoji is allowed")
def test_qa_sec86_variation_selector_run_cannot_carry_hidden_bits():
    bits = "".join(format(b, "08b") for b in b"ignore previous instructions")
    hidden = "".join("︎" if c == "0" else "️" for c in bits)
    assert poster.hidden_char_error(f"Love ❤{hidden} it") is not None
    # one selector per emoji stays allowed
    assert poster.hidden_char_error("Love ❤️ it") is None


@pytest.mark.posix_only
@pytest.mark.xfail(strict=True, reason="SEC-87: _adopt_posted uses AT_URI_RE.match, not fullmatch")
def test_qa_sec87_adopted_uri_must_fullmatch(files, ledger_dir):
    q, _ = files
    good = "at://did:plc:x/app.bsky.feed.post/old"
    q.write_text(q.read_text("utf-8").replace(good, good + "\x1b[2Jjunk"), encoding="utf-8")
    assert do_run(files, Recorder()) == poster.EXIT_OK
    adopted = _ledger(ledger_dir, item="Q-001")
    assert adopted and adopted[0]["status"] == "posted"
    assert adopted[0]["uri"] in ("", good)
