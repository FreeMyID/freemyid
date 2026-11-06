"""SEC-06 consent gate, SEC-12 exact-one id matching, SEC-14 private files. Fake people only."""
from __future__ import annotations

import os
import stat
import sys
from datetime import date

import pytest
from typer.testing import CliRunner

from freemyid import consent as cg
from freemyid.models import Consent, ConsentBasis, Todo, TodoKind

from .conftest import make_profile

TODAY = date(2026, 11, 5)


def _consent(basis=ConsentBasis.SELF, **kw):
    kw.setdefault("attested_by", "Jane Q Testperson")
    kw.setdefault("text_version", cg.CURRENT_TEXT_VERSION)
    return Consent(basis=basis, **kw)


def _p(basis=ConsentBasis.SELF, consent_kw=None, **over):
    return make_profile(consent=_consent(basis, **(consent_kw or {})), **over)


def _attach_auth(store, p):
    from freemyid.wizard.draft import save_authorization
    doc = save_authorization(store, p.id, "auth.pdf", b"%PDF-1.4 signed")
    return p.model_copy(update={"consent": p.consent.model_copy(
        update={"authorization_doc": doc})})


# --------------------------------------------------------------------------- SEC-06


def test_adult_self_ok():
    assert cg.consent_ok(_p(), today=TODAY) == (True, "")


def test_blank_attestation_refused():
    ok, why = cg.consent_ok(_p(consent_kw={"attested_by": "  "}), today=TODAY)
    assert not ok and "attesting" in why


@pytest.mark.parametrize("version", ["v1", "", "import", "2099-01-z"])
def test_unknown_text_version_refused(version):
    ok, why = cg.consent_ok(_p(consent_kw={"text_version": version}), today=TODAY)
    assert not ok and "consent text" in why


def test_wizard_shows_the_version_the_gate_accepts():
    from freemyid.wizard import draft
    assert draft.CONSENT_VERSION in cg.ACCEPTED_TEXT_VERSIONS


def test_dob_minor_with_self_consent_refused():
    p = _p(dob=date(2014, 6, 1), is_minor=False)   # 12 years old, flag not set
    assert cg.is_minor(p, TODAY)
    ok, why = cg.consent_ok(p, today=TODAY)
    assert not ok and "guardian" in why


def test_age_only_minor_refused():
    p = _p(dob=None, age=16)
    assert cg.is_minor(p, TODAY)
    assert not cg.consent_ok(p, today=TODAY)[0]


def test_flagged_minor_needs_guardian():
    assert not cg.consent_ok(_p(is_minor=True), today=TODAY)[0]
    assert cg.consent_ok(_p(ConsentBasis.GUARDIAN_OF_MINOR, is_minor=True), today=TODAY)[0]


def test_dob_minor_with_guardian_ok():
    p = _p(ConsentBasis.GUARDIAN_OF_MINOR, dob=date(2014, 6, 1))
    assert cg.consent_ok(p, today=TODAY) == (True, "")


def test_eighteenth_birthday_boundary():
    assert cg.is_minor(_p(dob=date(2008, 11, 6)), TODAY)        # turns 18 tomorrow
    assert not cg.is_minor(_p(dob=date(2008, 11, 5)), TODAY)    # 18 today


def test_unknown_age_is_adult_unless_flagged():
    assert not cg.is_minor(_p(dob=None, age=None), TODAY)


def test_guardian_basis_refused_for_adult():
    ok, why = cg.consent_ok(_p(ConsentBasis.GUARDIAN_OF_MINOR), today=TODAY)
    assert not ok and "under 18" in why


def test_agent_without_doc_refused(store):
    ok, why = cg.consent_ok(_p(ConsentBasis.AUTHORIZED_AGENT), store, today=TODAY)
    assert not ok and "authorization" in why


def test_agent_with_dangling_doc_id_refused(store):
    p = _p(ConsentBasis.AUTHORIZED_AGENT, consent_kw={"authorization_doc": "nope"})
    store.save_profile(p)
    assert not cg.consent_ok(p, store, today=TODAY)[0]


def test_agent_with_stored_doc_ok(store):
    p = _p(ConsentBasis.AUTHORIZED_AGENT)
    store.save_profile(p)
    p = _attach_auth(store, p)
    assert cg.authorization_on_file(p, store)
    assert cg.consent_ok(p, store, today=TODAY) == (True, "")


def test_agent_without_store_fails_closed(store):
    p = _p(ConsentBasis.AUTHORIZED_AGENT)
    store.save_profile(p)
    p = _attach_auth(store, p)
    assert not cg.consent_ok(p, today=TODAY)[0]


def test_agent_doc_of_another_profile_refused(store):
    other = _p(label="Other")
    store.save_profile(other)
    other = _attach_auth(store, other)
    p = _p(ConsentBasis.AUTHORIZED_AGENT,
           consent_kw={"authorization_doc": other.consent.authorization_doc})
    store.save_profile(p)
    assert not cg.authorization_on_file(p, store)
    assert not cg.consent_ok(p, store, today=TODAY)[0]


def test_agent_doc_file_missing_refused(store):
    from freemyid import paths
    p = _p(ConsentBasis.AUTHORIZED_AGENT)
    store.save_profile(p)
    p = _attach_auth(store, p)
    ev = next(e for e in store.list_evidence(p.id) if e.id == p.consent.authorization_doc)
    (paths.evidence_dir() / ev.relpath).unlink()
    assert not cg.consent_ok(p, store, today=TODAY)[0]


def test_cli_reexports_the_same_gate():
    from freemyid import cli
    assert cli.consent_ok is cg.consent_ok


# --------------------------------------------------------------------------- SEC-12


@pytest.fixture
def runner():
    return CliRunner()


def _hid(s: str) -> str:
    return s.ljust(32, "0")


def _two_profiles(store, prefix="ab"):
    a = _p(label="Alice", id=_hid(prefix + "1"))
    b = _p(label="Bob", id=_hid(prefix + "2"))
    store.save_profile(a)
    store.save_profile(b)
    return a, b


def test_remove_ambiguous_prefix_refuses(store, runner):
    from freemyid.cli import app
    a, b = _two_profiles(store)
    r = runner.invoke(app, ["profile", "remove", "ab", "--yes"])
    assert r.exit_code == 2
    assert "matches 2" in r.output and a.id[:8] in r.output and b.id[:8] in r.output
    assert {p.id for p in store.list_profiles()} == {a.id, b.id}


def test_remove_unique_prefix_deletes_only_that_one(store, runner):
    from freemyid.cli import app
    a, _ = _two_profiles(store)
    r = runner.invoke(app, ["profile", "remove", "ab2", "--yes"])
    assert r.exit_code == 0, r.output
    assert [p.id for p in store.list_profiles()] == [a.id]


def test_remove_no_match_exits_nonzero(store, runner):
    from freemyid.cli import app
    _two_profiles(store)
    r = runner.invoke(app, ["profile", "remove", "ee", "--yes"])
    assert r.exit_code == 2 and "No profile" in r.output
    assert len(store.list_profiles()) == 2


def test_label_and_prefix_collision_is_ambiguous(store, runner):
    from freemyid.cli import app
    a = _p(label="ab", id=_hid("ff1"))
    b = _p(label="Bob", id=_hid("ab2"))
    store.save_profile(a)
    store.save_profile(b)
    r = runner.invoke(app, ["profile", "remove", "ab", "--yes"])
    assert r.exit_code == 2
    assert len(store.list_profiles()) == 2


def test_export_without_consent_exits_cleanly(store, runner):
    from freemyid.cli import app
    p = _p(is_minor=True)   # SELF consent on a minor -> refused
    store.save_profile(p)
    r = runner.invoke(app, ["profile", "export", p.id[:8], "out.bin"])
    assert r.exit_code == 1
    assert "guardian" in r.output
    assert not isinstance(r.exception, IndexError)


def test_todo_done_ambiguous_prefix(store, runner):
    from freemyid.cli import app
    p = _p()
    store.save_profile(p)
    for tid in (_hid("cd1"), _hid("cd2")):
        store.save_todo(Todo(id=tid, profile_id=p.id, broker_id="b", kind=TodoKind.OTHER,
                             title="t"))
    r = runner.invoke(app, ["todo", "done", "cd"])
    assert r.exit_code == 2
    assert len(store.list_todos()) == 2
    r = runner.invoke(app, ["todo", "done", "cd1"])
    assert r.exit_code == 0, r.output
    assert [t.id for t in store.list_todos()] == [_hid("cd2")]


# --------------------------------------------------------------------------- SEC-14


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions")
def test_cli_start_sets_umask_and_private_home(freemyid_env, runner):
    from freemyid import paths
    from freemyid.cli import app
    home = paths.home()
    home.chmod(0o755)
    old = os.umask(0o022)
    try:
        r = runner.invoke(app, ["profile", "list"])
        assert r.exit_code == 0, r.output
        assert stat.S_IMODE(home.stat().st_mode) == 0o700
        cur = os.umask(0o022)
        assert cur == 0o077
        probe = home / "probe"
        os.umask(cur)
        probe.write_text("x")
        assert stat.S_IMODE(probe.stat().st_mode) == 0o600
    finally:
        os.umask(old)
