"""qa-security review of integrate/browser-extension (SEC-EXT-1..6).

Each test states the behaviour the code should have. They are strict xfails while the finding is
open: once the fix lands the test passes, strict mode turns that into a failure, and the marker
must be removed so the test guards the fix from then on.
"""
from __future__ import annotations

import importlib.util
import io
import json
import struct
import sys
from pathlib import Path

import pytest

from freemyid import native_host

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location("build_extension_review",
                                               ROOT / "tools" / "build_extension.py")
build_extension = importlib.util.module_from_spec(_spec)
sys.modules["build_extension_review"] = build_extension
_spec.loader.exec_module(build_extension)


def _frame_bytes(body: bytes) -> bytes:
    return struct.pack("=I", len(body)) + body


def _req(msg_type: str, **fields: object) -> dict:
    return {"v": 1, "type": msg_type, "id": "3f2c9d1e-0000-4000-8000-000000000001", **fields}


# ------------------------------------------------------------------------------ native host

def test_deeply_nested_json_is_a_framing_error() -> None:
    body = b"[" * 50_000   # well under MAX_REQUEST_BYTES
    with pytest.raises(native_host.FramingError):
        native_host.read_message(io.BytesIO(_frame_bytes(body)))


@pytest.mark.parametrize("body", [
    b"[" * 5 + b"]" * 5,                                  # one level past the limit
    b'{"a":' * 5 + b"1" + b"}" * 5,
    b'{"v":1,"type":"ping","id":"a","x":[[[[1]]]]}',      # nested inside an envelope
    b'{"a":"\\\\"' + b"[" * 50_000,                      # an escaped backslash ends the string
])
def test_json_nested_past_the_limit_is_refused_without_echoing_it(body: bytes) -> None:
    """SEC-EXT-1: a request is one flat object; anything deeper never reaches the parser."""
    with pytest.raises(native_host.FramingError) as caught:
        native_host.read_message(io.BytesIO(_frame_bytes(body)))
    assert str(caught.value) == "message is nested too deeply"
    assert native_host.serve(io.BytesIO(_frame_bytes(body)), io.BytesIO()) == 1


@pytest.mark.parametrize("message", [
    {"v": 1, "type": "ping", "id": "a"},
    {"a": {"b": {"c": {"d": 1}}}},                        # exactly MAX_JSON_DEPTH levels
    {"text": "[[[[[[[[ {{{{{{{{ \\\" [[[[[[[[ not nesting, just a string"},
])
def test_flat_messages_and_brackets_inside_strings_still_parse(message: dict) -> None:
    body = json.dumps(message).encode("utf-8")
    assert native_host.read_message(io.BytesIO(_frame_bytes(body))) == message


def test_a_recursion_error_from_the_parser_is_a_framing_error(monkeypatch) -> None:
    """SEC-EXT-1: even if the depth scan were wrong, the parser's RecursionError cannot escape."""
    def explode(_text: str) -> object:
        raise RecursionError("maximum recursion depth exceeded")

    monkeypatch.setattr(native_host.json, "loads", explode)
    with pytest.raises(native_host.FramingError):
        native_host.read_message(io.BytesIO(_frame_bytes(b"{}")))


@pytest.mark.parametrize("request_", [
    {"v": 1, "type": "ping", "id": "abc\n"},
    _req("site_check", hostname="www.spokeo.com\n"),
    _req("start_removal", broker_id="spokeo\n"),
])
def test_a_trailing_newline_is_refused(request_: dict) -> None:
    reply = native_host.handle_message(request_)
    assert reply["ok"] is False and reply["error"] == "bad_request"


def test_a_trailing_newline_never_reaches_a_handler_or_the_reply() -> None:
    """SEC-EXT-2: the handler is not called, and the bad id is not echoed back."""
    seen: list[str] = []

    def record(value: str) -> dict:
        seen.append(value)
        return {"ok": True}

    for request_ in (_req("site_check", hostname="www.spokeo.com\n"),
                     _req("start_removal", broker_id="spokeo\n")):
        native_host.handle_message(request_, site_check=record, start_removal=record)
    assert seen == []
    assert native_host.handle_message({"v": 1, "type": "ping", "id": "abc\n"})["id"] == ""


def test_host_manifest_refuses_an_extension_id_with_a_trailing_newline() -> None:
    """SEC-EXT-2: the id goes into allowed_origins, so it must be exactly 32 letters."""
    with pytest.raises(ValueError, match="32-letter"):
        native_host.host_manifest("chromium", "/opt/freemyid/host", ("a" * 32 + "\n",))
    assert native_host.host_manifest("chromium", "/opt/freemyid/host", ("a" * 32,))[
        "allowed_origins"] == ["chrome-extension://" + "a" * 32 + "/"]


def test_a_handler_cannot_add_fields_to_the_reply() -> None:
    def leaky(_hostname: str) -> dict:
        return {"ok": True, "broker_id": "spokeo", "listing_state": "found",
                "full_name": "Jane Q Testperson", "city": "Springfield"}

    reply = native_host.handle_message(_req("site_check", hostname="www.spokeo.com"),
                                       site_check=leaky)
    assert set(reply) <= {"v", "id", "type", "ok", "error", "broker_id", "listing_state", "stub"}
    assert "Testperson" not in json.dumps(reply) and "Springfield" not in json.dumps(reply)
    assert reply["broker_id"] == "spokeo" and reply["listing_state"] == "found"


def test_reply_fields_are_listed_per_message_type() -> None:
    """SEC-EXT-3: a field that belongs to one type is dropped from the other."""
    everything = {"ok": True, "broker_id": "spokeo", "listing_state": "found", "stub": True,
                  "accepted": True, "error": "ignored_when_ok", "pong": True, "app_version": "9"}
    site = native_host.handle_message(_req("site_check", hostname="www.spokeo.com"),
                                      site_check=lambda _h: dict(everything))
    assert set(site) == {"v", "id", "type", "ok", "broker_id", "listing_state", "stub"}
    removal = native_host.handle_message(_req("start_removal", broker_id="spokeo"),
                                         start_removal=lambda _b: dict(everything))
    assert set(removal) == {"v", "id", "type", "ok", "accepted"}
    assert removal["accepted"] is True


@pytest.mark.parametrize("value", [
    "Jane Q Testperson",                 # spaces and capitals: not an id or a state word
    "jane.testperson@example.test",
    "x" * 65,                            # too long
    "",
    "found\n",
    12, 1.5, ["found"], {"state": "found"}, b"found",
])
def test_reply_values_must_be_a_short_word_true_false_or_null(value: object) -> None:
    """SEC-EXT-3: anything else is dropped, whichever listed field it sits in."""
    reply = native_host.handle_message(
        _req("site_check", hostname="www.spokeo.com"),
        site_check=lambda _h: {"ok": True, "broker_id": value, "listing_state": value,
                               "stub": value})
    assert reply == {"v": 1, "id": _req("x")["id"], "type": "site_check", "ok": True}
    kept = native_host.handle_message(
        _req("site_check", hostname="www.spokeo.com"),
        site_check=lambda _h: {"ok": True, "broker_id": None, "listing_state": "x" * 64,
                               "stub": False})
    assert (kept["broker_id"], kept["listing_state"], kept["stub"]) == (None, "x" * 64, False)


@pytest.mark.parametrize("result", [
    {"ok": False},
    {"ok": False, "error": "Jane Q Testperson was not found"},
    {"ok": False, "error": 7},
    {"ok": "yes", "error": None},
    {},
    {7: "x", None: "y"},
])
def test_a_failed_reply_always_carries_a_plain_error_code(result: dict) -> None:
    """SEC-EXT-3: ok false means an error code, and only a code."""
    reply = native_host.handle_message(_req("start_removal", broker_id="spokeo"),
                                       start_removal=lambda _b: result)
    assert reply == {"v": 1, "id": _req("x")["id"], "type": "start_removal", "ok": False,
                     "error": "internal_error"}
    stub = native_host.handle_message(_req("start_removal", broker_id="spokeo"))
    assert stub["error"] == "not_implemented"


def test_serve_answers_internal_error_when_a_reply_cannot_be_encoded(monkeypatch) -> None:
    def too_big(message: object) -> dict:
        return {"v": 1, "id": "a", "type": "ping", "ok": True, "x": "a" * (2 * 1024 * 1024)}

    monkeypatch.setattr(native_host, "handle_message", too_big)
    out = io.BytesIO()
    stdin = io.BytesIO(native_host.encode_message(_req("ping")))
    assert native_host.serve(stdin, out) in (0, 1)   # no exception, no traceback on stderr
    (length,) = struct.unpack("=I", out.getvalue()[:4])
    assert json.loads(out.getvalue()[4:4 + length])["error"] == "internal_error"


def _replies(data: bytes) -> list[dict]:
    out = []
    while data:
        (length,) = struct.unpack("=I", data[:4])
        out.append(json.loads(data[4:4 + length]))
        data = data[4 + length:]
    return out


@pytest.mark.parametrize("bad_reply", [
    {"v": 1, "id": "a", "type": "ping", "ok": True, "x": {1, 2}},            # not JSON
    {"v": 1, "id": "a", "type": "ping", "ok": True, "x": "\ud800"},          # not UTF-8
    {"v": 1, "id": "a", "type": "ping", "ok": True, "x": b"bytes"},
    RuntimeError("Jane Q Testperson"),                                       # a bug in a handler
])
def test_serve_keeps_going_after_a_reply_it_cannot_send(monkeypatch, capsys,
                                                        bad_reply: object) -> None:
    """SEC-EXT-4: the bad reply becomes internal_error for that request id; the next request is
    answered normally; nothing reaches stderr."""
    real = native_host.handle_message
    calls: list[object] = []

    def flaky(message: object) -> dict:
        calls.append(message)
        if len(calls) == 1:
            if isinstance(bad_reply, Exception):
                raise bad_reply
            return bad_reply
        return real(message)

    monkeypatch.setattr(native_host, "handle_message", flaky)
    stdin = io.BytesIO(native_host.encode_message(_req("status"))
                       + native_host.encode_message(_req("ping")))
    out = io.BytesIO()
    assert native_host.serve(stdin, out) == 0
    first, second = _replies(out.getvalue())
    assert first == {"v": 1, "id": _req("x")["id"], "type": "status", "ok": False,
                     "error": "internal_error"}
    assert second["ok"] is True and second["pong"] is True
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_serve_stops_quietly_when_the_browser_closes_the_pipe() -> None:
    """SEC-EXT-4: a write that fails ends the host with exit code 1, not a traceback."""
    class ClosedPipe(io.BytesIO):
        def write(self, _data: bytes) -> int:   # type: ignore[override]
            raise BrokenPipeError

    stdin = io.BytesIO(native_host.encode_message(_req("ping")))
    assert native_host.serve(stdin, ClosedPipe()) == 1


# ------------------------------------------------------------------------------ build script

def test_a_sample_name_that_points_at_the_private_registry_is_refused(tmp_path: Path) -> None:
    private = tmp_path / "registry.yaml"
    private.write_text("version: x\nbrokers: []\n", encoding="utf-8")
    disguised = tmp_path / "public.sample.yaml"
    disguised.symlink_to(private)
    with pytest.raises(build_extension.BuildError):
        build_extension.sample_registry_path(ROOT, disguised)


_PRIVATE_YAML = ('version: "private"\nbrokers:\n  - id: private_only_broker\n'
                 "    name: Private Only\n    url: https://www.private-only.example/\n"
                 "    category: people_search\n    domains: [www.private-only.example]\n")
_SAMPLE_YAML = _PRIVATE_YAML.replace("private", "public").replace("Private", "Public")


def _fake_repo(tmp_path: Path) -> Path:
    """A stand-in repository root: brokers/ with a sample and a private registry, and tests/."""
    root = tmp_path / "repo"
    (root / "brokers").mkdir(parents=True)
    (root / "tests" / "fixtures").mkdir(parents=True)
    (root / "brokers" / "registry.sample.yaml").write_text(_SAMPLE_YAML, encoding="utf-8")
    (root / "brokers" / "registry.yaml").write_text(_PRIVATE_YAML, encoding="utf-8")
    (root / "tests" / "fixtures" / "tiny.sample.yaml").write_text(_SAMPLE_YAML, encoding="utf-8")
    return root


def test_only_the_sample_or_a_file_under_tests_is_accepted(tmp_path: Path) -> None:
    """SEC-EXT-5: the answer depends on where the path really leads."""
    root = _fake_repo(tmp_path)
    sample = (root / "brokers" / "registry.sample.yaml").resolve()
    fixture = (root / "tests" / "fixtures" / "tiny.sample.yaml").resolve()
    assert build_extension.sample_registry_path(root) == sample
    assert build_extension.sample_registry_path(root, sample) == sample
    assert build_extension.sample_registry_path(root, fixture) == fixture
    # the same two files through a path with ".." in it
    assert build_extension.sample_registry_path(
        root, root / "tests" / ".." / "brokers" / "registry.sample.yaml") == sample
    assert build_extension.load_domain_list(root, fixture)["hosts"] == {
        "www.public-only.example": "public_only_broker"}

    elsewhere = tmp_path / "elsewhere.sample.yaml"
    elsewhere.write_text(_SAMPLE_YAML, encoding="utf-8")
    other_dir = root / "brokers" / "other.sample.yaml"
    other_dir.write_text(_SAMPLE_YAML, encoding="utf-8")
    for refused in (elsewhere, other_dir, root / "brokers" / "registry.yaml",
                    root / "tests" / ".." / "brokers" / "registry.yaml",
                    root / "tests" / "fixtures" / "tiny.yaml"):
        with pytest.raises(build_extension.BuildError, match="public sample"):
            build_extension.sample_registry_path(root, refused)


def test_no_kind_of_link_reaches_the_private_registry(tmp_path: Path) -> None:
    """SEC-EXT-5: a symlink (file or folder) or a hard link with an innocent name is refused."""
    root = _fake_repo(tmp_path)
    private = root / "brokers" / "registry.yaml"
    fixtures = root / "tests" / "fixtures"

    file_link = fixtures / "linked.sample.yaml"
    file_link.symlink_to(private)
    harmless_link = fixtures / "also-tiny.sample.yaml"
    harmless_link.symlink_to(fixtures / "tiny.sample.yaml")          # links are refused as such
    folder_link = root / "tests" / "linked-brokers"
    folder_link.symlink_to(root / "brokers", target_is_directory=True)
    hard_link = fixtures / "hard.sample.yaml"
    hard_link.hardlink_to(private)
    private_dir = tmp_path / "private"
    private_dir.mkdir()
    (private_dir / "registry.sample.yaml").write_text(_PRIVATE_YAML, encoding="utf-8")
    outside_link = root / "tests" / "outside"
    outside_link.symlink_to(private_dir, target_is_directory=True)

    for refused in (file_link, harmless_link, folder_link / "registry.yaml", hard_link,
                    outside_link / "registry.sample.yaml"):
        with pytest.raises(build_extension.BuildError, match="public sample"):
            build_extension.sample_registry_path(root, refused)
        with pytest.raises(build_extension.BuildError):
            build_extension.load_domain_list(root, refused)


def test_a_sample_that_is_itself_a_link_to_the_private_registry_is_refused(tmp_path: Path) -> None:
    """SEC-EXT-5: the default path gets the same check as an override."""
    root = _fake_repo(tmp_path)
    sample = root / "brokers" / "registry.sample.yaml"
    sample.unlink()
    sample.symlink_to(root / "brokers" / "registry.yaml")
    with pytest.raises(build_extension.BuildError, match="public sample"):
        build_extension.sample_registry_path(root)
    sample.unlink()
    sample.hardlink_to(root / "brokers" / "registry.yaml")
    with pytest.raises(build_extension.BuildError, match="public sample"):
        build_extension.sample_registry_path(root)


def test_the_command_line_refuses_a_disguised_private_registry(tmp_path: Path, capsys) -> None:
    """SEC-EXT-5 end to end: --registry with a link writes nothing and names no file content."""
    private = tmp_path / "registry.yaml"
    private.write_text(_PRIVATE_YAML, encoding="utf-8")
    disguised = tmp_path / "public.sample.yaml"
    disguised.symlink_to(private)
    out = tmp_path / "out"
    assert build_extension.main(["--registry", str(disguised), "--out", str(out)]) == 1
    assert not out.exists()
    assert "private-only" not in capsys.readouterr().err


def test_validator_refuses_a_match_pattern_with_a_newline() -> None:
    domains = build_extension.load_domain_list()
    manifest = build_extension.build_manifest("chrome", domains)
    manifest["content_scripts"][0]["matches"] = ["https://www.spokeo.com\n/*"]
    assert build_extension.validate_manifest(manifest, "chrome")


def test_validator_refuses_a_version_with_a_trailing_newline() -> None:
    """SEC-EXT-2: same rule for the version string."""
    manifest = build_extension.build_manifest("chrome", build_extension.load_domain_list())
    assert build_extension.validate_manifest(manifest, "chrome") == []
    manifest["version"] += "\n"
    assert build_extension.validate_manifest(manifest, "chrome") == [
        "version must be 1 to 4 dot-separated numbers"]


@pytest.mark.parametrize(("broker_id", "host"), [
    ("examplebroker\n", "www.examplebroker.test"),
    ("examplebroker", "www.examplebroker.test\n"),
])
def test_domain_list_refuses_an_id_or_host_with_a_trailing_newline(broker_id: str,
                                                                   host: str) -> None:
    """SEC-EXT-2: build_extension's own _BROKER_ID and _HOST checks."""
    broker = {"id": broker_id, "name": "Example Broker", "category": "people_search",
              "url": "https://www.examplebroker.test/", "domains": [host]}
    with pytest.raises(build_extension.BuildError):
        build_extension.build_domain_list("test", [broker])
    broker.update(id="examplebroker", domains=["www.examplebroker.test"])
    assert build_extension.build_domain_list("test", [broker])["hosts"] == {
        "www.examplebroker.test": "examplebroker"}
