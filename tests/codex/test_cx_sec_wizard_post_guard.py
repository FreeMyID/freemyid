"""Every wizard POST stays behind the session, origin, host and CSRF guard."""
from __future__ import annotations

import re
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from freemyid.models import (
    Actor,
    Event,
    Method,
    Request,
    RequestKind,
    RequestStatus,
    Todo,
    TodoKind,
)
from freemyid.storage import Store
from freemyid.wizard.server import _csrf_for, create_app
from tests.conftest import make_profile

TOKEN = "test-session-token"
BAD_CSRF = "bad-csrf-token"


def _snapshot(store: Store) -> tuple[int, int, int, int]:
    """Count persisted records that a refused POST must not change."""
    return (
        len(store.list_profiles()),
        len(store.list_todos(open_only=False)),
        len(store.list_requests()),
        len(store.events()),
    )


def _post_routes(app) -> list[tuple[str, str]]:
    return sorted(
        (route.path, method)
        for route in app.routes
        for method in getattr(route, "methods", set())
        if method == "POST"
    )


def _path_for(template: str, ids: dict[str, str]) -> str:
    return re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}",
                  lambda match: ids[match.group(1)], template)


def _fail_if_called(name: str, calls: list[str]) -> Callable[..., None]:
    def fail(*_args, **_kwargs) -> None:
        calls.append(name)
        raise AssertionError(f"guarded request reached {name}")
    return fail


@pytest.fixture
def sweep(store: Store, monkeypatch: pytest.MonkeyPatch):
    """Create a local app with fake records and block every external side-effect helper."""
    from freemyid import scheduler
    from freemyid.engine import fill_for_me, outbox
    from freemyid.wizard import draft

    profile = make_profile()
    store.save_profile(profile)
    assisted = Todo(
        profile_id=profile.id,
        broker_id="fakebroker",
        kind=TodoKind.ASSISTED_OPT_OUT,
        title="Fake assisted task",
        links=["https://fakebroker.example/optout"],
    )
    manual = Todo(
        profile_id=profile.id,
        broker_id="fakebroker",
        kind=TodoKind.SEND_EMAIL_MANUALLY,
        title="Fake manual email task",
    )
    store.save_todo(assisted)
    store.save_todo(manual)
    request = Request(
        profile_id=profile.id,
        broker_id="fakebroker",
        kind=RequestKind.OPT_OUT,
        method=Method.EMAIL,
        status=RequestStatus.QUEUED_FOR_APPROVAL,
    )
    store.save_request(request)
    store.log(Event(actor=Actor.SYSTEM, action="test_baseline"))

    side_effects: list[str] = []
    blocked = _fail_if_called
    app = create_app(
        store,
        TOKEN,
        {"testserver"},
        registry_loader=lambda: None,
        open_url=blocked("open_url", side_effects),
        on_finish=blocked("on_finish", side_effects),
    )
    app.state.on_focus = lambda: side_effects.append("on_focus")
    client = TestClient(app, follow_redirects=False)
    client.cookies.set("freemyid_session", TOKEN)

    monkeypatch.setattr(draft, "check_mailbox", blocked("check_mailbox", side_effects))
    monkeypatch.setattr(outbox, "approve_and_send", blocked("approve_and_send", side_effects))
    monkeypatch.setattr(fill_for_me, "fill_for_me_sync",
                        blocked("fill_for_me_sync", side_effects))
    monkeypatch.setattr(scheduler, "install", blocked("scheduler.install", side_effects))
    monkeypatch.setattr(scheduler, "remove", blocked("scheduler.remove", side_effects))
    return app, client, store, side_effects, profile, assisted, manual, request


def test_every_post_route_refuses_missing_or_bad_guards_without_writes(sweep) -> None:
    app, client, store, side_effects, profile, assisted, manual, request = sweep
    routes = _post_routes(app)
    assert len(routes) >= 22, f"expected at least 22 POST routes, found {len(routes)}"

    ids = {
        "pid": profile.id,
        "tid": assisted.id,
        "rid": request.id,
        "cid": "fake_checklist",
        "action": "open",
        "provider": "gmail",
        "answer": "yes",
        "mode": "off",
        "step": "name",
    }
    anonymous = TestClient(app, follow_redirects=False)
    form = {"csrf": _csrf_for(TOKEN)}

    for template, _method in routes:
        route_ids = dict(ids)
        if "/compose/" in template:
            route_ids["tid"] = manual.id
        path = _path_for(template, route_ids)
        before = _snapshot(store)

        response = client.post(path, data={"other": "value"}, headers={"Origin": "http://testserver"})
        assert response.status_code == 403, (template, "missing csrf", response.status_code)
        assert _snapshot(store) == before, (template, "missing csrf changed store")

        response = client.post(path, data={"csrf": BAD_CSRF}, headers={"Origin": "http://testserver"})
        assert response.status_code == 403, (template, "wrong form csrf", response.status_code)
        assert _snapshot(store) == before, (template, "wrong form csrf changed store")

        response = client.post(path, headers={"Origin": "http://testserver", "X-CSRF": BAD_CSRF})
        assert response.status_code == 403, (template, "wrong header csrf", response.status_code)
        assert _snapshot(store) == before, (template, "wrong header csrf changed store")

        for origin in ("http://evil.example", "http://127.0.0.1:65534", "null"):
            response = client.post(path, data=form, headers={"Origin": origin})
            assert response.status_code == 403, (template, f"origin {origin}", response.status_code)
            assert _snapshot(store) == before, (template, f"origin {origin} changed store")

        response = client.post(
            path, data=form, headers={"Origin": "http://testserver", "Host": "evil.example"})
        assert response.status_code == 403, (template, "bad host", response.status_code)
        assert _snapshot(store) == before, (template, "bad host changed store")

        response = anonymous.post(path, data=form, headers={"Origin": "http://testserver"})
        assert response.status_code == 403, (template, "no session", response.status_code)
        assert _snapshot(store) == before, (template, "no session changed store")

        response = anonymous.post(
            f"{path}?t={TOKEN}", data=form, headers={"Origin": "http://testserver"})
        assert response.status_code == 403, (template, "POST query token", response.status_code)
        assert "freemyid_session" not in response.cookies, (template, "POST set a cookie")
        assert "freemyid_session" not in anonymous.cookies, (template, "POST logged in")
        assert _snapshot(store) == before, (template, "POST query token changed store")

    assert side_effects == []


def test_get_query_token_sets_strict_http_only_session_cookie(sweep) -> None:
    app, _client, _store, _side_effects, _profile, _assisted, _manual, _request = sweep
    anonymous = TestClient(app, follow_redirects=False)

    response = anonymous.get(f"/?t={TOKEN}")

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    cookie = response.cookies.get("freemyid_session")
    assert cookie == TOKEN
    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=strict" in set_cookie
    assert "path=/" in set_cookie


def test_harmless_post_with_valid_session_origin_and_csrf_passes(sweep) -> None:
    _app, client, _store, side_effects, _profile, _assisted, _manual, _request = sweep

    response = client.post(
        "/_focus",
        headers={"Origin": "http://testserver", "X-CSRF": _csrf_for(TOKEN)},
    )

    assert response.status_code == 200
    assert response.text == "ok"
    assert side_effects == ["on_focus"]
