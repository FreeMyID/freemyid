"""Wizard request guard: every response carries the security headers, and input the guard
cannot read is refused instead of crashing it. Regression tests for the WO-239 finding (the
bad-Host response went out without the headers) and what turned up on the same path."""
from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from starlette.responses import Response

from freemyid.storage import Store
from freemyid.wizard import server
from freemyid.wizard.server import COOKIE, _csrf_for, create_app

TOKEN = "tok-guard-regression"
ORIGIN = {"origin": "http://testserver"}
SECURITY_HEADERS = {
    "Content-Security-Policy": server.CSP,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "Cache-Control": "no-store",
    "X-Frame-Options": "DENY",
}


def _client(store: Store, *, cookie: bool = True, raise_errors: bool = True) -> TestClient:
    app = create_app(store, TOKEN, {"testserver"}, registry_loader=lambda: None)
    client = TestClient(app, follow_redirects=False, raise_server_exceptions=raise_errors)
    if cookie:
        client.cookies.set(COOKIE, TOKEN)
    return client


def _assert_hardened(response: Response) -> None:
    for name, value in SECURITY_HEADERS.items():
        assert response.headers.get(name) == value, f"{response.status_code}: {name}"


# ------------------------------------------------------------------ Host rejection
@pytest.mark.parametrize(
    "send",
    [
        lambda c: c.get("/", headers={"host": "evil.example"}),
        lambda c: c.get(f"/?t={TOKEN}", headers={"host": "evil.example"}),
        lambda c: c.get("/static/style.css", headers={"host": "evil.example"}),
        lambda c: c.get("/missing-route", headers={"host": "evil.example"}),
        lambda c: c.post("/_focus", data={"csrf": _csrf_for(TOKEN)},
                         headers={"host": "evil.example", "origin": "http://evil.example"}),
        lambda c: c.get("/", headers={"host": ""}),
        lambda c: c.get("/", headers={"host": "testserver.evil.example"}),
    ],
    ids=["get", "get-with-token", "static", "not-found", "post", "empty-host", "suffix-host"],
)
@pytest.mark.parametrize("cookie", [True, False], ids=["signed-in", "signed-out"])
def test_bad_host_is_refused_with_headers_and_no_session(
    store: Store, send: Callable[[TestClient], Response], cookie: bool,
) -> None:
    response = send(_client(store, cookie=cookie))

    assert response.status_code == 403
    _assert_hardened(response)
    assert response.headers.get_list("set-cookie") == []
    assert "location" not in response.headers
    assert TOKEN.encode() not in response.content
    assert _csrf_for(TOKEN).encode() not in response.content


def test_bad_host_post_never_reaches_the_route(store: Store) -> None:
    client = _client(store)
    focused: list[str] = []
    client.app.state.on_focus = lambda: focused.append("called")

    response = client.post("/_focus", data={"csrf": _csrf_for(TOKEN)},
                           headers={"host": "evil.example", **ORIGIN})

    assert response.status_code == 403
    assert focused == []


# ------------------------------------------------------------------ error paths
def test_unhandled_route_error_still_sets_security_headers(
    store: Store, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken() -> list:
        raise RuntimeError("synthetic failure: Jane Q Testperson")

    monkeypatch.setattr(store, "list_profiles", broken)
    response = _client(store, raise_errors=False).get("/")

    assert response.status_code == 500
    _assert_hardened(response)
    assert response.headers.get_list("set-cookie") == []
    assert "synthetic failure" not in response.text
    assert "Testperson" not in response.text
    assert TOKEN not in response.text


def test_unhandled_route_error_is_still_raised_to_the_server(
    store: Store, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The hardened 500 page must not swallow the error: the server log still needs it."""
    def broken() -> list:
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr(store, "list_profiles", broken)
    with pytest.raises(RuntimeError, match="synthetic failure"):
        _client(store).get("/")


@pytest.mark.parametrize(
    "content_type, body",
    [
        ("multipart/form-data; boundary=x", b"--x\r\nnot a form part"),
        ("multipart/form-data", b"no boundary at all"),
    ],
    ids=["broken-part", "no-boundary"],
)
def test_unreadable_form_is_refused_as_a_csrf_failure(
    store: Store, content_type: str, body: bytes,
) -> None:
    client = _client(store, raise_errors=False)
    focused: list[str] = []
    client.app.state.on_focus = lambda: focused.append("called")

    response = client.post("/_focus", content=body,
                           headers={"content-type": content_type, **ORIGIN})

    assert response.status_code == 403
    _assert_hardened(response)
    assert focused == []


@pytest.mark.parametrize(
    "send",
    [
        lambda c: c.get("/", headers={"cookie": f"{COOKIE}=caf\xe9".encode("latin-1")}),
        lambda c: c.get("/?t=caf%C3%A9"),
        lambda c: c.get("/", params={"t": "caf\xe9"}),
    ],
    ids=["cookie", "query-escaped", "query-raw"],
)
def test_non_ascii_session_value_is_refused_not_a_server_error(
    store: Store, send: Callable[[TestClient], Response],
) -> None:
    response = send(_client(store, cookie=False, raise_errors=False))

    assert response.status_code == 403
    _assert_hardened(response)
    assert response.headers.get_list("set-cookie") == []


@pytest.mark.parametrize(
    "send",
    [
        lambda c: c.post("/_focus", headers={"x-csrf": "caf\xe9".encode("latin-1"), **ORIGIN}),
        lambda c: c.post("/_focus", data={"csrf": "caf\xe9"}, headers=ORIGIN),
    ],
    ids=["header", "form-field"],
)
def test_non_ascii_csrf_value_is_refused_not_a_server_error(
    store: Store, send: Callable[[TestClient], Response],
) -> None:
    client = _client(store, raise_errors=False)
    focused: list[str] = []
    client.app.state.on_focus = lambda: focused.append("called")

    response = send(client)

    assert response.status_code == 403
    _assert_hardened(response)
    assert focused == []
