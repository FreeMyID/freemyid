"""Dashboard consent gate: it reads the saved consent records through the store and fails
closed when it cannot. Regression tests for the WO-240 finding. Fake people only."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from freemyid import paths
from freemyid.consent import CURRENT_TEXT_VERSION, consent_ok
from freemyid.models import Consent, ConsentBasis
from freemyid.storage import Store
from freemyid.wizard import server
from freemyid.wizard.draft import save_authorization
from freemyid.wizard.server import COOKIE, create_app
from tests.conftest import make_profile

TOKEN = "tok-consent-gate"
NOT_RUNNING = "Not running yet"
NOT_FOUND = "the signed authorization could not be found"
NOT_CHECKED = "could not check the saved permission"
PAGES = pytest.mark.parametrize("url", ["/", "/profile/{pid}"], ids=["today", "profile"])


def _client(store: Store) -> TestClient:
    app = create_app(store, TOKEN, {"testserver"}, registry_loader=lambda: None)
    client = TestClient(app, follow_redirects=False)
    client.cookies.set(COOKIE, TOKEN)
    return client


def _agent_profile(store: Store, *, attach: bool = True):
    """A synthetic adult whose consent basis is a signed agent authorization."""
    profile = make_profile(consent=Consent(
        basis=ConsentBasis.AUTHORIZED_AGENT, attested_by="Jane Q Testperson",
        text_version=CURRENT_TEXT_VERSION))
    store.save_profile(profile)
    if attach:
        doc = save_authorization(store, profile.id, "synthetic-authorization.pdf",
                                 b"%PDF-1.4 synthetic signed form")
        profile = profile.model_copy(update={
            "consent": profile.consent.model_copy(update={"authorization_doc": doc})})
        store.save_profile(profile)
    return profile


@PAGES
def test_dashboard_reads_stored_agent_authorization(store: Store, url: str) -> None:
    profile = _agent_profile(store)
    assert consent_ok(profile, store) == (True, "")

    response = _client(store).get(url.format(pid=profile.id))

    assert response.status_code == 200
    assert NOT_RUNNING not in response.text


@PAGES
def test_dashboard_reports_agent_authorization_never_attached(store: Store, url: str) -> None:
    profile = _agent_profile(store, attach=False)

    response = _client(store).get(url.format(pid=profile.id))

    assert response.status_code == 200
    assert NOT_RUNNING in response.text
    assert "authorized agent needs the signed authorization attached" in response.text


@PAGES
def test_dashboard_reports_agent_authorization_missing_from_disk(store: Store, url: str) -> None:
    profile = _agent_profile(store)
    for evidence in store.list_evidence(profile.id, "_consent"):
        (paths.evidence_dir() / evidence.relpath).unlink()

    response = _client(store).get(url.format(pid=profile.id))

    assert response.status_code == 200
    assert NOT_RUNNING in response.text
    assert NOT_FOUND in response.text


def test_dashboard_reports_another_persons_authorization(store: Store) -> None:
    """An authorization stored for one person never satisfies the gate for another."""
    owner = _agent_profile(store)
    other = _agent_profile(store, attach=False)
    other = other.model_copy(update={"consent": other.consent.model_copy(
        update={"authorization_doc": owner.consent.authorization_doc})})
    store.save_profile(other)

    response = _client(store).get(f"/profile/{other.id}")

    assert response.status_code == 200
    assert NOT_FOUND in response.text


@PAGES
@pytest.mark.parametrize("basis", [ConsentBasis.AUTHORIZED_AGENT, ConsentBasis.SELF])
def test_dashboard_fails_closed_when_consent_cannot_be_checked(
    store: Store, monkeypatch: pytest.MonkeyPatch, url: str, basis: ConsentBasis,
) -> None:
    profile = (_agent_profile(store) if basis == ConsentBasis.AUTHORIZED_AGENT
               else make_profile())
    store.save_profile(profile)

    def unreadable(*_args: object, **_kwargs: object) -> tuple[bool, str]:
        raise OSError("synthetic store failure: Jane Q Testperson")

    monkeypatch.setattr("freemyid.consent.consent_ok", unreadable)
    response = _client(store).get(url.format(pid=profile.id))

    assert response.status_code == 200
    assert NOT_RUNNING in response.text
    assert NOT_CHECKED in response.text
    assert "synthetic store failure" not in response.text


@PAGES
def test_dashboard_fails_closed_when_the_evidence_list_cannot_be_read(
    store: Store, monkeypatch: pytest.MonkeyPatch, url: str,
) -> None:
    profile = _agent_profile(store)
    real = store.list_evidence

    def unreadable(pid: str, bid: str | None = None):
        if bid == "_consent":
            raise OSError("synthetic store failure")
        return real(pid, bid)

    monkeypatch.setattr(store, "list_evidence", unreadable)
    response = _client(store).get(url.format(pid=profile.id))

    assert response.status_code == 200
    assert NOT_RUNNING in response.text
    assert NOT_CHECKED in response.text
    assert NOT_FOUND not in response.text


def test_gate_that_refuses_without_a_reason_still_reports_a_problem(
    store: Store, monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = make_profile()
    monkeypatch.setattr("freemyid.consent.consent_ok", lambda *_a, **_k: (False, ""))

    assert server._consent_problem(profile, store) == server.CONSENT_UNCHECKED


def test_consent_check_failure_is_logged_without_the_error_text(
    store: Store, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    def unreadable(*_args: object, **_kwargs: object) -> tuple[bool, str]:
        raise OSError("synthetic store failure: Jane Q Testperson")

    monkeypatch.setattr("freemyid.consent.consent_ok", unreadable)
    with caplog.at_level("WARNING", logger="freemyid.wizard.server"):
        assert server._consent_problem(make_profile(), store) == server.CONSENT_UNCHECKED

    assert "OSError" in caplog.text
    assert "Testperson" not in caplog.text
