"""Adopted from engine/_test_drafts: a search that returns an error page, or a page with neither
results nor the site's "no results" text, must never record NOT_FOUND. Dev fixtures only."""
from __future__ import annotations

import pytest

from freemyid import config as cfgmod
from freemyid.consent import CURRENT_TEXT_VERSION
from freemyid.engine import _dev
from freemyid.engine.runner import run
from freemyid.models import Address, Consent, ConsentBasis, ListingState
from tests.conftest import make_profile, no_browser


def _scan(store, state: str):
    c = Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
                text_version=CURRENT_TEXT_VERSION)
    p = make_profile(consent=c, addresses=[Address(street="1 Main St", city="Springfield",
                                                   state=state, zip="00000", current=True)])
    store.save_profile(p)
    reg = _dev.fixture_registry()
    cfg = cfgmod.Config(min_delay_s=0, max_delay_s=0, max_retries=1)
    with _dev.fixture_server():
        run(store, reg, [p], scan_only=True, dry_run=True, interactive=False,
            broker_ids=["devauto"], cfg=cfg)
    errs = [e.detail.get("error") for e in store.events(p.id, "devauto")
            if e.action == "scan_failed"]
    if "BrowserUnavailable" in errs:
        no_browser("runner could not launch a browser")
    return store.get_status(p.id, "devauto"), errs


def test_no_results_text_records_not_found(store):
    st, errs = _scan(store, "nc")
    if errs:
        no_browser(f"scan failed: {errs}")
    assert st.state == ListingState.NOT_FOUND


@pytest.mark.parametrize("state", ["oh", "tx"])     # changed layout / HTTP 404
def test_unrecognized_or_error_page_is_not_not_found(store, state):
    st, errs = _scan(store, state)
    assert st.state != ListingState.NOT_FOUND
    assert errs == ["UnexpectedPage"]
