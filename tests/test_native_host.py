"""Native messaging host stub (src/freemyid/native_host.py): framing round trip, the four
message types, refusal of anything that could carry personal details, and the host manifests."""
from __future__ import annotations

import ast
import io
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

import pytest

from freemyid import __version__, native_host

ROOT = Path(__file__).resolve().parents[1]
HOST_DIR = ROOT / "extension" / "native-host"


def _frame(obj: object) -> bytes:
    body = json.dumps(obj).encode("utf-8")
    return struct.pack("=I", len(body)) + body


def _unframe(data: bytes) -> list[dict]:
    out = []
    while data:
        (length,) = struct.unpack("=I", data[:4])
        out.append(json.loads(data[4:4 + length].decode("utf-8")))
        data = data[4 + length:]
    return out


def _req(msg_type: str, **fields: object) -> dict:
    return {"v": 1, "type": msg_type, "id": "3f2c9d1e-0000-4000-8000-000000000001", **fields}

@pytest.fixture(autouse=True)
def _paired_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Most tests here are about framing and reply rules, not pairing: treat the caller as a
    paired extension. Pairing itself is tested in tests/test_extension_link.py."""
    monkeypatch.setattr(native_host, "_is_paired", lambda origin: True)



# --------------------------------------------------------------------------------- framing

@pytest.mark.parametrize("message", [
    {"v": 1, "type": "ping", "id": "a"},
    {"v": 1, "type": "site_check", "id": "b", "hostname": "www.spokeo.com"},
    {"text": "café ✓ \U0001f512", "nested": {"list": [1, 2.5, None, True]}},
    {},
    {"long": "x" * 60000},
])
def test_framing_round_trip(message: dict) -> None:
    data = native_host.encode_message(message)
    (length,) = struct.unpack("=I", data[:4])
    assert length == len(data) - 4                       # 4-byte length, machine byte order
    assert data[:4] == len(data[4:]).to_bytes(4, sys.byteorder)
    assert native_host.read_message(io.BytesIO(data)) == message


def test_several_messages_in_one_stream_then_clean_end() -> None:
    first, second = {"v": 1, "type": "ping", "id": "one"}, {"v": 1, "type": "status", "id": "two"}
    stream = io.BytesIO(native_host.encode_message(first) + native_host.encode_message(second))
    assert native_host.read_message(stream) == first
    assert native_host.read_message(stream) == second
    assert native_host.read_message(stream) is None      # the browser closed the pipe
    assert native_host.read_message(io.BytesIO(b"")) is None


def test_write_message_flushes_one_frame() -> None:
    out = io.BytesIO()
    native_host.write_message(out, {"ok": True})
    assert _unframe(out.getvalue()) == [{"ok": True}]


def test_reads_survive_a_pipe_that_delivers_one_byte_at_a_time() -> None:
    class Trickle(io.BytesIO):
        def read(self, size: int = -1) -> bytes:
            return super().read(min(size, 1))

    message = {"v": 1, "type": "ping", "id": "slow"}
    assert native_host.read_message(Trickle(native_host.encode_message(message))) == message


@pytest.mark.parametrize("data", [
    b"\x01",                                              # half a length prefix
    struct.pack("=I", 10) + b"{}",                        # body shorter than promised
    struct.pack("=I", native_host.MAX_REQUEST_BYTES + 1) + b"x",
    struct.pack("=I", 0xFFFFFFFF),
    struct.pack("=I", 5) + b"hello",                      # not JSON
    struct.pack("=I", 2) + b"\xff\xfe",                   # not UTF-8
    struct.pack("=I", 0),                                 # empty body
])
def test_bad_frames_raise_without_echoing_the_bytes(data: bytes) -> None:
    with pytest.raises(native_host.FramingError) as excinfo:
        native_host.read_message(io.BytesIO(data))
    assert "hello" not in str(excinfo.value)
    assert excinfo.value.__cause__ is None                 # the bad bytes are not chained on


def test_reply_size_is_capped() -> None:
    with pytest.raises(native_host.FramingError):
        native_host.encode_message({"big": "x" * (native_host.MAX_REPLY_BYTES + 1)})


# -------------------------------------------------------------------------------- messages

def test_ping() -> None:
    request = _req("ping")
    assert native_host.handle_message(request) == {
        "v": 1, "id": request["id"], "type": "ping", "ok": True, "pong": True}


def test_status_reports_the_app_version() -> None:
    reply = native_host.handle_message(_req("status"), app_open=lambda: False)
    assert reply == {"v": 1, "id": _req("status")["id"], "type": "status", "ok": True,
                     "connected": True, "app_version": __version__, "paired": True,
                     "app_open": False}


def test_site_check_without_a_status_file_knows_nothing() -> None:
    reply = native_host.handle_message(_req("site_check", hostname="www.spokeo.com"))
    assert reply["ok"] is True and "stub" not in reply
    assert reply["broker_id"] is None and reply["listing_state"] == "unknown"


def test_start_removal_is_queued_for_the_app() -> None:
    from freemyid import extension_link
    reply = native_host.handle_message(_req("start_removal", broker_id="spokeo"),
                                       origin="firefox:extension@freemyid.org")
    assert reply["ok"] is True and reply["accepted"] is True and reply["now"] is False
    assert extension_link.take_inbox() == ["spokeo"]


def test_every_reply_is_an_envelope_for_its_request() -> None:
    for request in (_req("ping"), _req("status"), _req("site_check", hostname="radaris.com"),
                    _req("start_removal", broker_id="radaris"), _req("nope"), _req("ping", v=2)):
        reply = native_host.handle_message(request)
        assert reply["v"] == 1 and reply["id"] == request["id"] and isinstance(reply["ok"], bool)
        json.dumps(reply)


@pytest.mark.parametrize(("request_", "error"), [
    (_req("ping", v=2), "unsupported_version"),
    (_req("ping", v=0), "unsupported_version"),
    (_req("ping", v="1"), "bad_request"),
    (_req("ping", v=True), "bad_request"),
    (_req("ping", v=1.0), "bad_request"),
    (_req("launch_missiles"), "unknown_type"),
    (_req(""), "unknown_type"),
    ({"v": 1, "type": "ping"}, "bad_request"),
    ({"v": 1, "type": "ping", "id": ""}, "bad_request"),
    ({"v": 1, "type": "ping", "id": "x" * 65}, "bad_request"),
    ({"v": 1, "type": "ping", "id": "has space"}, "bad_request"),
    ({"v": 1, "type": "ping", "id": 7}, "bad_request"),
    ({"type": "ping", "id": "abc"}, "bad_request"),
    ("ping", "bad_request"),
    (["ping"], "bad_request"),
    (None, "bad_request"),
    (_req("site_check"), "bad_request"),
    (_req("site_check", hostname=""), "bad_request"),
    (_req("site_check", hostname="WWW.SPOKEO.COM"), "bad_request"),
    (_req("site_check", hostname="www.spokeo.com/jane-q-testperson"), "bad_request"),
    (_req("site_check", hostname="https://www.spokeo.com"), "bad_request"),
    (_req("site_check", hostname="localhost"), "bad_request"),
    (_req("site_check", hostname="127.0.0.1"), "bad_request"),
    (_req("site_check", hostname=["www.spokeo.com"]), "bad_request"),
    (_req("site_check", hostname="a" * 250 + ".com"), "bad_request"),
    (_req("start_removal"), "bad_request"),
    (_req("start_removal", broker_id="Spokeo"), "bad_request"),
    (_req("start_removal", broker_id="spokeo; rm -rf"), "bad_request"),
    (_req("start_removal", broker_id="../../etc"), "bad_request"),
    (_req("start_removal", broker_id="x" * 65), "bad_request"),
    (_req("start_removal", broker_id=None), "bad_request"),
])
def test_bad_requests_are_refused(request_: object, error: str) -> None:
    reply = native_host.handle_message(request_)
    assert reply["ok"] is False and reply["error"] == error


@pytest.mark.parametrize("request_", [
    _req("ping", name="Jane Q Testperson"),
    _req("status", email="jane@example.invalid"),
    _req("site_check", hostname="www.spokeo.com", url="https://www.spokeo.com/Jane-Testperson"),
    _req("site_check", hostname="www.spokeo.com", broker_id="spokeo"),
    _req("start_removal", broker_id="spokeo", hostname="www.spokeo.com"),
    _req("start_removal", broker_id="spokeo", fields={"full_name": "Jane Q Testperson"}),
    _req("start_removal", broker_id="spokeo", profile_id=1),
])
def test_there_is_no_room_for_personal_details(request_: dict) -> None:
    """Unknown fields are refused outright, and nothing from them comes back."""
    called = []
    reply = native_host.handle_message(request_, site_check=lambda h: called.append(h) or {"ok": True},
                                       start_removal=lambda b: called.append(b) or {"ok": True})
    assert reply == {"v": 1, "id": request_["id"], "type": request_["type"], "ok": False,
                     "error": "bad_request"}
    assert called == []
    assert "Testperson" not in json.dumps(reply)


def test_handlers_can_be_replaced_and_get_only_the_checked_value() -> None:
    seen = []

    def site_check(hostname: str) -> dict:
        seen.append(hostname)
        return {"ok": True, "broker_id": "spokeo", "listing_state": "submitted"}

    def start_removal(broker_id: str, origin: str) -> dict:
        seen.append(broker_id)
        return {"ok": True, "accepted": True}

    reply = native_host.handle_message(_req("site_check", hostname="www.spokeo.com"), site_check=site_check)
    assert reply["ok"] is True and reply["broker_id"] == "spokeo" and reply["listing_state"] == "submitted"
    reply = native_host.handle_message(_req("start_removal", broker_id="spokeo"), start_removal=start_removal)
    assert reply["ok"] is True and reply["accepted"] is True
    assert seen == ["www.spokeo.com", "spokeo"]


def test_a_handler_cannot_replace_the_envelope() -> None:
    request = _req("site_check", hostname="www.spokeo.com")
    reply = native_host.handle_message(
        request, site_check=lambda _h: {"ok": "yes", "v": 99, "id": "other", "type": "ping"})
    assert (reply["v"], reply["id"], reply["type"], reply["ok"]) == (1, request["id"], "site_check", False)


def test_a_failing_handler_gives_a_bare_error_code() -> None:
    def boom(_value: str, _origin: str) -> dict:
        raise RuntimeError("Jane Q Testperson, 12 Oak Street, Springfield IL")

    reply = native_host.handle_message(_req("start_removal", broker_id="spokeo"), start_removal=boom)
    assert reply == {"v": 1, "id": _req("x")["id"], "type": "start_removal", "ok": False,
                     "error": "internal_error"}


# ---------------------------------------------------------------------------------- serving

def test_serve_answers_each_request_in_order() -> None:
    stdin = io.BytesIO(_frame(_req("ping")) + _frame(_req("status")) + _frame({"v": 1, "type": "x", "id": "q"}))
    stdout = io.BytesIO()
    assert native_host.serve(stdin, stdout) == 0
    replies = _unframe(stdout.getvalue())
    assert [r["type"] for r in replies] == ["ping", "status", ""]
    assert [r["ok"] for r in replies] == [True, True, False]


def test_serve_stops_on_a_broken_stream_after_answering_what_came_before() -> None:
    stdin = io.BytesIO(_frame(_req("ping")) + struct.pack("=I", 50) + b"{")
    stdout = io.BytesIO()
    assert native_host.serve(stdin, stdout) == 1
    assert [r["type"] for r in _unframe(stdout.getvalue())] == ["ping"]


def test_real_process_speaks_only_frames_on_stdout() -> None:
    """Run it the way a browser does: bytes in on stdin, frames out on stdout, nothing else."""
    dev_id = "abcdefghijklmnop" * 2
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), native_host.EXTENSION_IDS_ENV: dev_id}
    stdin = (_frame(_req("ping")) + _frame(_req("status"))
             + _frame(_req("site_check", hostname="www.spokeo.com"))
             + _frame(_req("start_removal", broker_id="spokeo")))
    done = subprocess.run([sys.executable, "-m", "freemyid.native_host",
                           f"chrome-extension://{dev_id}/"], input=stdin,
                          capture_output=True, env=env, timeout=60, check=False)
    assert done.returncode == 0
    assert done.stderr == b""                                   # nothing logged about messages
    replies = _unframe(done.stdout)
    assert [r["type"] for r in replies] == ["ping", "status", "site_check", "start_removal"]
    assert replies[1]["app_version"] == __version__
    assert replies[1]["paired"] is False                     # nobody paired this extension yet
    for reply in replies[2:]:
        assert reply["ok"] is False and reply["error"] == "not_paired"


def test_host_module_has_no_network_file_or_process_imports() -> None:
    tree = ast.parse((ROOT / "src" / "freemyid" / "native_host.py").read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert imported == {"__future__", "json", "re", "struct", "sys", "collections.abc", "typing",
                        "freemyid", "msvcrt", "os"}
    # os is there for os.environ (the developer id list) and the Windows binary-mode switch only
    os_uses = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
               and isinstance(node.value, ast.Name) and node.value.id == "os"}
    assert os_uses == {"environ", "O_BINARY"}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not names & {"open", "print", "logging", "eval", "exec"}


# ---------------------------------------------------------------------------- host manifests

def _template(name: str, **values: str) -> dict:
    text = (HOST_DIR / name).read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    assert "{{" not in text
    return json.loads(text)


def test_chromium_manifest_matches_its_template() -> None:
    ext_id = "abcdefghijklmnopabcdefghijklmnop"
    rendered = native_host.host_manifest("chromium", "/opt/freemyid/freemyid-native-host", (ext_id,))
    assert rendered == _template("org.freemyid.host.chromium.json.template",
                                 HOST_PATH="/opt/freemyid/freemyid-native-host",
                                 CHROME_EXTENSION_ID=ext_id)
    assert rendered["name"] == "org.freemyid.host" and rendered["type"] == "stdio"
    assert rendered["allowed_origins"] == [f"chrome-extension://{ext_id}/"]
    assert "allowed_extensions" not in rendered


def test_firefox_manifest_matches_its_template_and_the_extension_id() -> None:
    rendered = native_host.host_manifest("firefox", "/opt/freemyid/freemyid-native-host")
    assert rendered == _template("org.freemyid.host.firefox.json.template",
                                 HOST_PATH="/opt/freemyid/freemyid-native-host")
    firefox = json.loads((ROOT / "extension" / "manifests" / "firefox.json").read_text(encoding="utf-8"))
    assert rendered["allowed_extensions"] == [firefox["browser_specific_settings"]["gecko"]["id"]]
    assert "allowed_origins" not in rendered


@pytest.mark.parametrize(("browser", "ids"), [
    ("chromium", ()),
    ("chromium", ("*",)),
    ("chromium", ("short",)),
    ("chromium", ("ABCDEFGHIJKLMNOPABCDEFGHIJKLMNOP",)),
    ("chromium", ("abcdefghijklmnopabcdefghijklmnop", "*")),
    ("safari", ()),
])
def test_host_manifest_refuses_wildcards_and_unknown_browsers(browser: str, ids: tuple) -> None:
    with pytest.raises(ValueError, match="chromium|browser"):
        native_host.host_manifest(browser, "/x", ids)


def test_install_locations_cover_three_systems_and_three_browsers() -> None:
    data = json.loads((HOST_DIR / "install-locations.json").read_text(encoding="utf-8"))
    assert data["host_name"] == native_host.HOST_NAME
    for system in ("windows", "macos", "linux"):
        for browser in ("chrome", "edge", "firefox"):
            entry = data[system][browser]
            assert (HOST_DIR / entry["manifest"]).is_file()
            assert ("firefox" in entry["manifest"]) == (browser == "firefox")
            where = entry.get("registry_key") or entry["path"]
            assert native_host.HOST_NAME in where
            if system == "windows":
                assert where.startswith("HKEY_CURRENT_USER\\")          # per user, no admin
            else:
                assert where.startswith("~/") and where.endswith(f"{native_host.HOST_NAME}.json")
    reg = (HOST_DIR / "windows-registry.reg.template").read_text(encoding="utf-8")
    for browser in ("chrome", "edge", "firefox"):
        assert f"[{data['windows'][browser]['registry_key']}]" in reg
    assert "HKEY_LOCAL_MACHINE" not in reg
    used = set()
    for path in HOST_DIR.glob("*.template"):
        text = path.read_text(encoding="utf-8")
        used |= {part.split("}}")[0] for part in text.split("{{")[1:]}
    assert used == set(data["placeholders"])
