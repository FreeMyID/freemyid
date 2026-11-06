"""Model + registry schema validation."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.conftest import FIXTURES, make_profile
from vanish import registry
from vanish.models import Broker, Event, Actor, Registry

ROOT = Path(__file__).resolve().parent.parent


def _broker(**over):
    d = dict(id="fakeb", name="Fake", url="https://fakeb.example/", category="people_search",
             domains=["fakeb.example"], method="web_form",
             opt_out_url="https://fakeb.example/optout")
    d.update(over)
    return d


def test_profile_state_upper_and_residence():
    p = make_profile()
    assert p.state_of_residence == "IL"


def test_profile_requires_address():
    with pytest.raises(ValidationError):
        make_profile(addresses=[])


def test_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        make_profile(ssn="000-00-0000")


def test_estimated_age():
    from datetime import date
    p = make_profile(dob=date(2000, 6, 15))
    assert p.estimated_age(date(2026, 6, 14)) == 25
    assert p.estimated_age(date(2026, 6, 15)) == 26


@pytest.mark.parametrize("over,msg", [
    (dict(method="email"), "opt_out_email"),
    (dict(method="postal"), "postal"),
    (dict(method="phone"), "phone"),
    (dict(opt_out_url=None), "opt_out_url"),
    (dict(verification_status="verified"), "source_urls"),
    (dict(verification_status="verified", source_urls=["https://fakeb.example/p"]),
     "last_verified"),
    (dict(id="Bad-Id"), "pattern"),
    (dict(domains=[]), "at least 1"),
])
def test_broker_validators(over, msg):
    with pytest.raises(ValidationError, match=msg):
        Broker.model_validate(_broker(**over))


def test_registry_duplicate_and_dangling_ids():
    with pytest.raises(ValidationError, match="duplicate"):
        Registry.model_validate(dict(version="1", updated="2026-11-05",
                                     brokers=[_broker(), _broker()]))
    with pytest.raises(ValidationError, match="unknown ids"):
        Registry.model_validate(dict(version="1", updated="2026-11-05",
                                     brokers=[_broker(covered_by="nope")]))


def test_fixture_registry_loads(fake_registry):
    assert {b.id for b in fake_registry.brokers} == {"fakepeople", "fakemail"}


def test_committed_schema_matches_models():
    committed = json.loads((ROOT / "schema" / "registry.schema.json").read_text())
    assert committed == Registry.model_json_schema(), "run tools/gen_schema.py"


def test_real_registry_validates():
    p = ROOT / "brokers" / "registry.yaml"
    if not p.exists():
        pytest.skip("brokers/registry.yaml not written yet")
    reg = registry.load_registry(p)
    assert reg.brokers
    for b in reg.brokers:
        for d in [*b.domains, *b.confirmation_domains]:
            assert "." in d and "/" not in d and ":" not in d, (b.id, d)


def test_real_state_laws_validate():
    p = ROOT / "brokers" / "state_laws.yaml"
    if not p.exists():
        pytest.skip("brokers/state_laws.yaml not written yet")
    assert registry.load_state_laws(p)


# ---- findings (strict xfail: flip to normal tests once the orchestrator fixes them) ----

@pytest.mark.xfail(strict=True, reason="SEC-07: broker domains not validated (TLD/'com' allowed)")
@pytest.mark.parametrize("dom", ["com", "", "*.fakeb.example", "https://fakeb.example"])
def test_broker_domains_must_be_hostnames(dom):
    with pytest.raises(ValidationError):
        Broker.model_validate(_broker(domains=[dom]))


@pytest.mark.xfail(strict=True, reason="SEC-07: opt_out_email may point outside broker domains")
def test_opt_out_email_must_be_on_broker_domain():
    with pytest.raises(ValidationError):
        Broker.model_validate(_broker(method="email", opt_out_email="x@attacker.example"))


@pytest.mark.xfail(strict=True, reason="SEC-08: submitter accepts arbitrary module:Class")
def test_submitter_restricted_to_vanish_namespace():
    with pytest.raises(ValidationError):
        Broker.model_validate(_broker(submitter="subprocess:Popen"))


@pytest.mark.xfail(strict=True, reason="SEC-02: ids are free-form (path traversal via id)")
def test_profile_id_format_enforced():
    with pytest.raises(ValidationError):
        make_profile(id="../../..")


@pytest.mark.xfail(strict=True, reason="SEC-02: Evidence.relpath allows absolute/../ paths")
def test_evidence_relpath_confined():
    from vanish.models import Evidence
    with pytest.raises(ValidationError):
        Evidence(profile_id="a", broker_id="b", kind="html", relpath="/etc/x", sha256="")


def test_event_roundtrip_ids_only():
    ev = Event(actor=Actor.ENGINE, action="scan", detail={"n": 2})
    assert Event.model_validate_json(ev.model_dump_json()) == ev


def test_fixture_dir_has_no_obvious_real_pii():
    import re
    for f in FIXTURES.rglob("*"):
        if f.is_file():
            t = f.read_text(errors="ignore")
            assert not re.search(r"\b\d{3}-\d{2}-\d{4}\b", t), f   # SSN-shaped
