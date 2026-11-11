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
    b'{"a":"\\"' + b"[" * 50_000,                        # an escaped backslash ends the string
])
def test_json_nested_past_the_limit_is_refused_without_echoing_it(body: bytes) -> None:
    """SEC-EXT-1: a request is one flat object; anything deeper never reaches the parser."""
    with pytest.raises(native_host.FramingError) as caught:
        native_host.read_message(io.BytesIO(_frame_bytes(body)))
    assert str(caught.value) in ("message is nested too deeply", "message is not UTF-8 JSON")
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


@pytest.mark.xfail(strict=True, reason="SEC-EXT-2: re.match with '$' accepts a trailing newline")
@pytest.mark.parametrize("request_", [
    {"v": 1, "type": "ping", "id": "abc\n"},
    _req("site_check", hostname="www.spokeo.com\n"),
    _req("start_removal", broker_id="spokeo\n"),
])
def test_a_trailing_newline_is_refused(request_: dict) -> None:
    reply = native_host.handle_message(request_)
    assert reply["ok"] is False and reply["error"] == "bad_request"


@pytest.mark.xfail(strict=True, reason="SEC-EXT-3: reply fields from a handler are not allow-listed")
def test_a_handler_cannot_add_fields_to_the_reply() -> None:
    def leaky(_hostname: str) -> dict:
        return {"ok": True, "broker_id": "spokeo", "listing_state": "found",
                "full_name": "Jane Q Testperson", "city": "Springfield"}

    reply = native_host.handle_message(_req("site_check", hostname="www.spokeo.com"),
                                       site_check=leaky)
    assert set(reply) <= {"v", "id", "type", "ok", "error", "broker_id", "listing_state", "stub"}


@pytest.mark.xfail(strict=True, reason="SEC-EXT-4: serve() crashes when a reply cannot be encoded")
def test_serve_answers_internal_error_when_a_reply_cannot_be_encoded(monkeypatch) -> None:
    def too_big(message: object) -> dict:
        return {"v": 1, "id": "a", "type": "ping", "ok": True, "x": "a" * (2 * 1024 * 1024)}

    monkeypatch.setattr(native_host, "handle_message", too_big)
    out = io.BytesIO()
    stdin = io.BytesIO(native_host.encode_message(_req("ping")))
    assert native_host.serve(stdin, out) in (0, 1)   # no exception, no traceback on stderr
    (length,) = struct.unpack("=I", out.getvalue()[:4])
    assert json.loads(out.getvalue()[4:4 + length])["error"] == "internal_error"


# ------------------------------------------------------------------------------ build script

@pytest.mark.xfail(strict=True,
                   reason="SEC-EXT-5: the sample-only guard checks the file name, not the target")
def test_a_sample_name_that_points_at_the_private_registry_is_refused(tmp_path: Path) -> None:
    private = tmp_path / "registry.yaml"
    private.write_text("version: x\nbrokers: []\n", encoding="utf-8")
    disguised = tmp_path / "public.sample.yaml"
    disguised.symlink_to(private)
    with pytest.raises(build_extension.BuildError):
        build_extension.sample_registry_path(ROOT, disguised)


@pytest.mark.xfail(strict=True, reason="SEC-EXT-2: the match-pattern validator accepts a newline")
def test_validator_refuses_a_match_pattern_with_a_newline() -> None:
    domains = build_extension.load_domain_list()
    manifest = build_extension.build_manifest("chrome", domains)
    manifest["content_scripts"][0]["matches"] = ["https://www.spokeo.com\n/*"]
    assert build_extension.validate_manifest(manifest, "chrome")
