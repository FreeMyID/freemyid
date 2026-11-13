"""Consent must be valid before searches or browser-assisted work can begin."""
from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient

from freemyid.consent import CURRENT_TEXT_VERSION, consent_ok
from freemyid.engine import exposure as exposure_mod
from freemyid.engine import fill_for_me as fill_for_me_mod
from freemyid.engine import listing_finder as listing_finder_mod
from freemyid.engine._dev import fixture_registry
from freemyid.models import Consent, ConsentBasis, Permissions, RemovalScope
from freemyid.storage import Store
from freemyid.wizard.draft import save_authorization
from freemyid.wizard.server import create_app
from tests.conftest import make_profile

TODAY = date(2026, 11, 9)
BAD_CASES = (
    "blank attestation",
    "unknown text version",
    "minor with self consent",
    "adult with guardian consent",
    "agent without authorization document",
    "phone-only without disclosure permission",
    "email-only without disclosure permission",
)


def _bad_profile(case: str):
    """Return a synthetic profile rejected by the shared consent gate."""
    p = make_profile()
    consent = p.consent
    updates: dict[str, Any] = {}
    if case == "blank attestation":
        consent = consent.model_copy(update={"attested_by": "  "})
    elif case == "unknown text version":
        consent = consent.model_copy(update={"text_version": "unknown-test-version"})
    elif case == "minor with self consent":
        updates["dob"] = date(2014, 6, 1)
    elif case == "adult with guardian consent":
        consent = consent.model_copy(update={"basis": ConsentBasis.GUARDIAN_OF_MINOR})
    elif case == "agent without authorization document":
        consent = consent.model_copy(update={"basis": ConsentBasis.AUTHORIZED_AGENT})
    elif case == "phone-only without disclosure permission":
        updates["removal_scope"] = RemovalScope.PHONE
        updates["permissions"] = Permissions()
    elif case == "email-only without disclosure permission":
        updates["removal_scope"] = RemovalScope.EMAIL
        updates["permissions"] = Permissions()
    else:
        raise AssertionError(f"unknown synthetic case: {case}")
    updates["consent"] = consent
    return p.model_copy(update=updates)


def _save_bad_profile(store: Store, case: str):
    profile = _bad_profile(case)
    store.save_profile(profile)
    return profile


class _Calls:
    def __init__(self) -> None:
        self.count = 0

    def __call__(self, *_args: object) -> str:
        self.count += 1
        return ""


@pytest.mark.parametrize("case", BAD_CASES)
def test_exposure_scan_refuses_invalid_consent_before_fetch(store: Store, case: str) -> None:
    profile = _save_bad_profile(store, case)
    fetch = _Calls()
    browser_fetch = _Calls()

    with pytest.raises(exposure_mod.ExposureRefused):
        exposure_mod.scan_exposure(
            store,
            profile.id,
            registry=fixture_registry(),
            fetch=fetch,
            browser_fetch=browser_fetch,
            use_browser=True,
            now=None,
        )

    assert fetch.count == 0
    assert browser_fetch.count == 0


@pytest.mark.parametrize("case", BAD_CASES)
@pytest.mark.parametrize("operation", ["listing finder", "fill for me"])
async def test_browser_flows_refuse_invalid_consent_before_factory(
    store: Store, monkeypatch: pytest.MonkeyPatch, case: str, operation: str,
) -> None:
    profile = _save_bad_profile(store, case)
    starts: list[str] = []

    class BrowserMustNotStart:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            starts.append("constructed")

        async def start(self) -> None:
            starts.append("started")
            raise AssertionError("browser must not start before consent is checked")

    from freemyid.engine import browser as browser_mod
    monkeypatch.setattr(browser_mod, "BrowserManager", BrowserMustNotStart)
    registry = fixture_registry()
    if operation == "listing finder":
        result = await listing_finder_mod.find_listing(
            store, profile.id, "devauto", registry=registry,
        )
    else:
        result = await fill_for_me_mod.fill_for_me(
            store, profile.id, "devauto", registry=registry,
        )

    assert result.status == "refused"
    assert result.reason == "consent"
    assert starts == []


@pytest.mark.xfail(
    strict=True,
    reason=("SEC finding: wizard server.py:88 calls consent_ok without the store, so a valid "
            "stored AUTHORIZED_AGENT authorization is reported missing on the dashboard"),
)
def test_dashboard_accepts_stored_agent_authorization(
    store: Store,
) -> None:
    profile = make_profile(consent=Consent(
        basis=ConsentBasis.AUTHORIZED_AGENT,
        attested_by="Jane Q Testperson",
        text_version=CURRENT_TEXT_VERSION,
    ))
    store.save_profile(profile)
    evidence_id = save_authorization(
        store, profile.id, "synthetic-authorization.pdf", b"%PDF-1.4 synthetic signed form",
    )
    profile = profile.model_copy(update={
        "consent": profile.consent.model_copy(update={"authorization_doc": evidence_id}),
    })
    store.save_profile(profile)
    assert consent_ok(profile, store, today=TODAY) == (True, "")

    token = "tok-test"
    app = create_app(store, token, {"testserver"},
                     registry_loader=lambda: None)
    client = TestClient(app, follow_redirects=False)
    client.cookies.set("freemyid_session", token)
    response = client.get(f"/profile/{profile.id}", headers={"host": "testserver"})

    assert response.status_code == 200
    assert "the signed authorization could not be found" not in response.text

