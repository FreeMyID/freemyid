"""Security headers and session-token handling for every wizard response."""
from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

import keyring
import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from starlette.responses import Response

from freemyid import scheduler
from freemyid.storage import Store
from freemyid.wizard import server
from freemyid.wizard.server import COOKIE, _csrf_for, create_app

TOKEN = "tok-cx-headers"
ALLOWED_HOSTS = {"testserver"}
EXPECTED_HEADERS = {
    "Content-Security-Policy": server.CSP,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "Cache-Control": "no-store",
    "X-Frame-Options": "DENY",
}


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FREEMYID_HOME", str(tmp_path))
    monkeypatch.setenv("FREEMYID_TEST_KEY", "dev")
    monkeypatch.setattr(keyring, "set_password", lambda *_args: None)
    store = Store()
    app = create_app(store, TOKEN, ALLOWED_HOSTS, registry_loader=lambda: None)
    test_client = TestClient(app, follow_redirects=False)
    test_client.cookies.set(COOKIE, TOKEN)
    return test_client


@pytest.fixture(scope="module", autouse=True)
def stub_host_scheduler() -> Iterator[None]:
    """Keep this module's /settings requests away from the host scheduler.

    Module scope: a session-scoped stub leaked into later modules and broke
    tests/test_scheduler_real.py, which needs the real scheduler.status.
    """
    patch = pytest.MonkeyPatch()
    patch.setattr(scheduler, "status", lambda: "not installed")
    yield
    patch.undo()


def assert_security_headers(response: Response) -> None:
    for name, value in EXPECTED_HEADERS.items():
        assert response.headers.get(name) == value, (
            f"{response.status_code} response is missing {name!r} or has the wrong value"
        )
    csp = response.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in csp
    assert "script-src 'self'" in csp
    assert "unsafe-inline" not in csp
    assert "unsafe-eval" not in csp


def assert_no_session_leak_or_foreign_cookie(response: Response) -> None:
    if response.headers.get("content-type", "").startswith("text/html"):
        assert TOKEN.encode() not in response.content
    cookie_names = {
        header.split("=", maxsplit=1)[0]
        for header in response.headers.get_list("set-cookie")
    }
    assert cookie_names <= {COOKIE}


def get_route_urls(app: FastAPI) -> Iterable[str]:
    for route in app.routes:
        if isinstance(route, APIRoute) and "GET" in (route.methods or set()):
            yield re.sub(r"\{[^}]+\}", "fake-id", route.path)


def test_every_get_route_sets_security_headers_and_keeps_session_private(
    client: TestClient,
) -> None:
    urls = list(get_route_urls(client.app))
    assert len(urls) >= 15

    for url in urls:
        response = client.get(url)
        assert_security_headers(response)
        assert_no_session_leak_or_foreign_cookie(response)


@pytest.mark.parametrize(
    "response_factory",
    [
        lambda client: (client.cookies.clear(), client.get("/"))[1],
        lambda client: client.post("/_focus", data={"not_csrf": "fake"}),
        lambda client: client.get("/static/style.css"),
        lambda client: client.get("/missing-route"),
        lambda client: (client.cookies.clear(), client.get(f"/?t={TOKEN}"))[1],
    ],
    ids=["unauthenticated", "csrf-refused", "static-file", "not-found", "login-redirect"],
)
def test_common_responses_set_security_headers_and_do_not_leak(
    client: TestClient,
    response_factory: Callable[[TestClient], Response],
) -> None:
    response = response_factory(client)
    assert_security_headers(response)
    assert_no_session_leak_or_foreign_cookie(response)


def test_valid_post_redirect_sets_security_headers(client: TestClient) -> None:
    response = client.post(
        "/protect/fake-pid/fake-check/done",
        data={"csrf": _csrf_for(TOKEN)},
        headers={"origin": "http://testserver"},
    )
    assert response.status_code == 303
    assert_security_headers(response)
    assert_no_session_leak_or_foreign_cookie(response)


def test_bad_host_response_sets_security_headers(client: TestClient) -> None:
    response = client.get("/", headers={"host": "evil.example"})
    assert_security_headers(response)


def test_bad_host_response_does_not_leak_token_or_set_foreign_cookie(client: TestClient) -> None:
    response = client.get("/", headers={"host": "evil.example"})
    assert_no_session_leak_or_foreign_cookie(response)
