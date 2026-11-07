"""Draft tests for engine/outbox.py template choice and compose links (qa to adopt)."""
from __future__ import annotations

from datetime import date
from urllib.parse import parse_qs, urlsplit

from freemyid.engine.outbox import compose, compose_links, initial_template
from freemyid.models import Address, Broker, StateLaw
from tests.conftest import make_profile

B = Broker(id="fakeb", name="Fake B", url="https://fakeb.example/", category="data_broker",
           domains=["fakeb.example"], method="email", opt_out_email="privacy@fakeb.example")


def law(state, **kw):
    return StateLaw(state=state, **kw)


def _matrix(state):
    from freemyid.engine import law_matrix
    return law_matrix.parse({"version": "t", "states": [
        {"state": state, "in_force": True, "deletion_right": "yes", "citation": "Fake 1",
         "evidence": "statute_text"}]})


def test_ccpa_only_with_verified_ca_law():
    from freemyid.engine import law_matrix
    p = make_profile(addresses=[Address(city="Fresno", state="CA", current=True)])
    assert initial_template(p, None) == "generic_removal"
    ca = law("CA", statute_name="CCPA", rights=["delete"])
    assert initial_template(p, ca, matrix=_matrix("CA")) == "ccpa"
    assert initial_template(p, ca, matrix=law_matrix.EMPTY) == "generic_removal"


def test_state_privacy_only_when_deletion_right_in_effect():
    p = make_profile()      # IL
    m = _matrix("IL")
    in_force = law("IL", statute_name="Fake Privacy Act", rights=["delete"],
                   effective_date=date(2020, 1, 1))
    assert initial_template(p, in_force, matrix=m) == "state_privacy"
    future = in_force.model_copy(update={"effective_date": date(2099, 1, 1)})
    assert initial_template(p, future, matrix=m) == "generic_removal"
    no_delete = in_force.model_copy(update={"rights": ["opt_out_sale"]})
    assert initial_template(p, no_delete, matrix=m) == "generic_removal"
    assert initial_template(p, in_force) == "generic_removal"   # no matrix entry for IL
    assert initial_template(p, None) == "generic_removal"


def test_no_citation_without_law_and_only_current_state():
    p = make_profile(addresses=[Address(city="Raleigh", state="NC", current=True),
                                Address(city="Fresno", state="CA")])
    ca = law("CA", statute_name="California Consumer Privacy Act", rights=["delete"],
             citation="Cal. Civ. Code 1798.105", last_verified=date(2026, 11, 1))
    _subj, body = compose(p, B, [], ca)          # law for another state: ignored
    assert "1798" not in body and "California" not in body
    assert "Jane Testperson" in body or "Jane Q Testperson" in body


def test_compose_links_prefill():
    links = compose_links("privacy@fakeb.example", "Remove me", "Hello\nthere")
    g = parse_qs(urlsplit(links["Gmail"]).query)
    assert g["to"] == ["privacy@fakeb.example"] and g["su"] == ["Remove me"]
    assert g["body"] == ["Hello\nthere"]
    assert set(links) == {"Gmail", "Outlook", "Yahoo", "Email app"}
