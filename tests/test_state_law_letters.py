"""State-law deletion letters: cite a law only where the deletion matrix says the statute
text was checked (engine/law_matrix.py). Fake people and *.example brokers only."""
from __future__ import annotations

from datetime import date

import pytest

from freemyid.engine import law_matrix, outbox
from freemyid.engine.mail import FakeMailer
from freemyid.models import Address, Broker, EmailMode, RequestStatus, StateLaw
from freemyid.registry import load_state_laws
from tests.conftest import make_profile

B = Broker(id="fakeb", name="Fake B", url="https://fakeb.example/", category="data_broker",
           domains=["fakeb.example"], method="email", opt_out_email="privacy@fakeb.example")
B2 = B.model_copy(update={"id": "fakec", "name": "Fake C",
                          "opt_out_email": "privacy@fakec.example"})
LAWS = load_state_laws()
MATRIX = law_matrix.load()
# Every state the bundled matrix does NOT let us cite, plus states with no entry at all.
NOT_CITABLE = sorted({s for s, e in MATRIX.states.items() if not e.citable()}
                     | {"NC", "SC", "AZ"})


def person(state: str, **kw):
    return make_profile(addresses=[Address(city="Testville", state=state, current=True)], **kw)


def letter(state: str, **kw) -> tuple[str, str]:
    return outbox.compose(person(state, **kw), B, [], LAWS.get(state))


# --------------------------------------------------------------------------- the matrix

def test_bundled_matrix_cites_only_statute_text_states():
    citable = {s for s, e in MATRIX.states.items() if e.citable()}
    assert citable == {s for s, e in MATRIX.states.items()
                       if e.evidence == "statute_text" and e.in_force
                       and e.deletion_right == "yes"}
    assert {"VA", "MN", "OR", "CA"} <= citable
    for s in ("OK", "LA", "AL", "VT"):         # enacted, not in force yet
        assert not MATRIX.states[s].citable(), s


def test_yaml_yes_is_read_as_a_deletion_right():
    m = law_matrix.parse({"version": "t", "states": [
        {"state": "va", "in_force": True, "deletion_right": True, "citation": "X 1",
         "evidence": "statute_text"}]})
    assert m.get("VA") is not None and m.get("VA").citable()


@pytest.mark.parametrize("bad", ["not: [valid", "states: 3", ""])
def test_broken_matrix_fails_closed(tmp_path, bad):
    p = tmp_path / "m.yaml"
    p.write_text(bad, encoding="utf-8")
    assert law_matrix.load(p).states == {}
    assert law_matrix.load(tmp_path / "missing.yaml").states == {}


def test_duplicate_state_rejected():
    with pytest.raises(ValueError):
        law_matrix.parse({"version": "t", "states": [{"state": "VA"}, {"state": "va"}]})


# --------------------------------------------------------------------------- verified states

@pytest.mark.parametrize("state,cite", [
    ("VA", "Va. Code 59.1-577"),
    ("MN", "Minn. Stat. 325M.14 subd. 1(d)"),
    ("OR", "ORS 646A.574(1)(c)"),
    ("CA", "Cal. Civ. Code 1798.105"),
])
def test_verified_states_cite_the_matrix_citation(state, cite):
    p = person(state)
    assert outbox.initial_template(p, LAWS[state]) == ("ccpa" if state == "CA"
                                                       else "state_privacy")
    subj, body = letter(state)
    assert cite in body
    assert LAWS[state].statute_name.split(";")[0] in body
    # the background citation from state_laws.yaml is never used instead
    if LAWS[state].citation and LAWS[state].citation not in MATRIX.states[state].citation:
        assert LAWS[state].citation not in body
    assert "45 days from receiving this request" in body
    assert "45 more days" in body
    assert "do not ask for more information" in body
    assert subj


def test_virginia_and_minnesota_state_their_verification_rules():
    _s, va = letter("VA")
    _s, mn = letter("MN")
    for body in (va, mn):
        assert "Verifying this request" in body
        assert "reasonable effort" in body
        assert "minimal record" in body
    assert "good-faith belief" in mn and "good-faith belief" not in va


def test_oregon_and_california_have_no_invented_verification_rule():
    for st in ("OR", "CA"):
        _s, body = letter(st)
        assert "Verifying this request" not in body
        assert "good-faith" not in body


def test_california_agent_rule_only_for_an_agent():
    from freemyid.consent import CURRENT_TEXT_VERSION
    from freemyid.models import Consent, ConsentBasis
    agent = Consent(basis=ConsentBasis.AUTHORIZED_AGENT, attested_by="John Testperson",
                    text_version=CURRENT_TEXT_VERSION)
    _s, own = letter("CA")
    _s, by_agent = letter("CA", consent=agent)
    assert "authorized agent make this request" not in own
    assert "California Secretary of State" in by_agent


def test_unverified_deadline_is_not_quoted_as_law():
    m = law_matrix.parse({"version": "t", "states": [
        {"state": "OR", "in_force": True, "deletion_right": "yes", "evidence": "statute_text",
         "citation": "ORS 646A.574(1)(c)", "response_days": 45, "extension_days": 45,
         "response_days_evidence": "background"}]})
    _s, body = outbox.compose(person("OR"), B, [], LAWS["OR"], matrix=m)
    assert "ORS 646A.574(1)(c)" in body
    assert "Deadline" not in body and "45 days" not in body


# --------------------------------------------------------------------------- fallbacks

@pytest.mark.parametrize("state", NOT_CITABLE)
def test_unverified_or_no_law_states_get_the_generic_letter(state):
    p = person(state)
    assert outbox.initial_template(p, LAWS.get(state)) == "generic_removal"
    _s, body = letter(state)
    for word in ("Code", "Stat.", " Act", "Legal basis", "law gives you", "Deadline"):
        assert word not in body, (state, word)
    law = LAWS.get(state)
    if law and law.citation:
        assert law.citation not in body


def test_law_of_another_state_is_never_cited():
    p = make_profile(addresses=[Address(city="Raleigh", state="NC", current=True),
                                Address(city="Richmond", state="VA")])
    _s, body = outbox.compose(p, B, [], LAWS["VA"])
    assert "59.1" not in body and "Virginia" not in body


def test_empty_matrix_means_generic_even_for_california():
    p = person("CA")
    assert outbox.initial_template(p, LAWS["CA"], matrix=law_matrix.EMPTY) == "generic_removal"
    _s, body = outbox.compose(p, B, [], LAWS["CA"], matrix=law_matrix.EMPTY)
    assert "1798" not in body


def test_law_not_yet_in_effect_or_without_delete_right_is_generic():
    p = person("VA")
    future = LAWS["VA"].model_copy(update={"effective_date": date(2099, 1, 1)})
    assert outbox.initial_template(p, future) == "generic_removal"
    no_delete = LAWS["VA"].model_copy(update={"rights": ["opt_out_sale"]})
    assert outbox.initial_template(p, no_delete) == "generic_removal"
    m = law_matrix.parse({"version": "t", "states": [
        {"state": "VA", "in_force": True, "deletion_right": "yes", "evidence": "statute_text",
         "citation": "Va. Code 59.1-577", "effective_date": "2099-01-01"}]})
    assert outbox.initial_template(p, LAWS["VA"], matrix=m) == "generic_removal"


def test_missing_citation_in_matrix_is_generic():
    m = law_matrix.parse({"version": "t", "states": [
        {"state": "VA", "in_force": True, "deletion_right": "yes", "evidence": "statute_text"}]})
    assert outbox.initial_template(person("VA"), LAWS["VA"], matrix=m) == "generic_removal"


def test_fake_state_law_needs_a_matrix_entry():
    il = StateLaw(state="IL", statute_name="Fake Privacy Act", citation="Fake 1",
                  rights=["delete"], last_verified=date(2026, 11, 1))
    p = make_profile()                       # Springfield IL
    assert outbox.initial_template(p, il) == "generic_removal"


# --------------------------------------------------------------------------- outbox gate

def test_state_letter_goes_through_the_first_email_gate(store):
    p = person("VA", email_mode=EmailMode.AUTO)
    m = FakeMailer()
    first = outbox.queue_email(store, p, B, [], dry_run=False, mailer=m,
                               state_law=LAWS["VA"])
    second = outbox.queue_email(store, p, B2, [], dry_run=False, mailer=m,
                                state_law=LAWS["VA"])
    assert first.status == second.status == RequestStatus.QUEUED_FOR_APPROVAL
    assert m.sent == []                    # SEC-27: nothing leaves before one approval
    _to, _subj, body = outbox.letter_for(store, first)
    assert "Va. Code 59.1-577" in body     # what gets approved is the state-law letter


def test_state_letter_in_practice_mode_is_a_draft(store):
    p = person("MN", email_mode=EmailMode.AUTO)
    m = FakeMailer()
    req = outbox.queue_email(store, p, B, [], dry_run=True, mailer=m, state_law=LAWS["MN"])
    assert req.status == RequestStatus.DRAFT and req.dry_run and m.sent == []
    assert "325M.14" in outbox.letter_for(store, req)[2]


@pytest.mark.parametrize("state", sorted(s for s, e in MATRIX.states.items() if e.citable()))
def test_every_citable_state_cites_exactly_the_matrix_citation(state):
    law = LAWS.get(state)
    _s, body = letter(state)
    if law is None or not law.statute_name or not any("delet" in r for r in law.rights):
        assert "Legal basis" not in body       # state_laws.yaml lacks the law: generic
        return
    assert f"Legal basis: {MATRIX.states[state].citation}." in body
    assert body.count("Legal basis") == 1
