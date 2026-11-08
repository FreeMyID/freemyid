"""qa-security review of the 2026-11-07 wave (docs/SECURITY_REVIEW.md, "Wave review 2026-11-07").

SEC-90 letter wording, SEC-93a one exposure card per person (no cross-profile leakage), and the
SEC-93c commit-email guard (tools/ci/check_commit_emails.sh). Fake people and *.example only.
Strict xfails mark open findings: each one starts passing (and so fails the suite) when fixed.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import keyring
import pytest
from fastapi.testclient import TestClient

from freemyid.engine import exposure as ex
from freemyid.engine import outbox
from freemyid.engine._dev import fixture_registry
from freemyid.models import Address, Broker, Request, RequestKind
from freemyid.registry import load_state_laws
from freemyid.wizard.server import create_app
from tests.conftest import make_profile

ROOT = Path(__file__).resolve().parents[1]

# --------------------------------------------------------------------------- SEC-90

B = Broker(id="fakeb", name="Fake B", url="https://fakeb.example/", category="data_broker",
           domains=["fakeb.example"], method="email", opt_out_email="privacy@fakeb.example",
           typical_processing_days=30)
LAWS = load_state_laws()


def _letter(state: str, kind: RequestKind, broker: Broker = B) -> str:
    p = make_profile(addresses=[Address(city="Testville", state=state, current=True)])
    orig = Request(profile_id=p.id, broker_id=broker.id, kind=RequestKind.OPT_OUT,
                   method="email", created_at=datetime(2026, 9, 1, tzinfo=UTC))
    return outbox.compose(p, broker, [], LAWS.get(state), kind, original=orig)[1]


@pytest.mark.parametrize("state", ["OR", "NC"])
def test_sec90_unverified_window_is_worded_as_a_request(state):
    fu = _letter(state, RequestKind.FOLLOW_UP)
    ld = _letter(state, RequestKind.LEGAL_DEMAND)
    assert "hoped for a reply within 30 days (by 2026-10-01)" in fu
    assert "30 days (to 2026-10-01) is a reasonable time" in ld
    for body in (fu, ld):
        low = body.lower()
        assert "was due" not in low and "period ended" not in low and "you must" not in low


def test_sec90_no_processing_days_means_no_date_at_all():
    b = B.model_copy(update={"typical_processing_days": 0})
    for kind in (RequestKind.FOLLOW_UP, RequestKind.LEGAL_DEMAND):
        body = _letter("NC", kind, b)
        assert "2026-10" not in body and "reply within" not in body


def test_sec90_verified_window_does_not_also_add_request_wording():
    body = _letter("VA", RequestKind.LEGAL_DEMAND)
    assert "Your response was due by 2026-10-16" in body
    assert "reasonable time" not in body


# --------------------------------------------------------------------------- SEC-93a

CARD = '<section class="card"><h2><span class="ico ico-map"'
PAGE_URL = "https://devauto.example/name/jane-testperson/IL"
RESULT = ('<html><body><div class="result"><a class="view" href="/p/1">View</a>'
          '<span class="name">Jane Q Testperson</span><span class="age">Age 46</span>'
          '<span class="loc">Springfield, IL</span><span class="rel">John Testperson</span>'
          "</div></body></html>")


def test_sec93a_one_card_per_person_without_cross_profile_leakage(store, monkeypatch):
    monkeypatch.setattr(keyring, "set_password", lambda *a: None)
    a = make_profile(label="Alpha <i>one</i>")
    b = make_profile(label="Beta")
    store.save_profile(a)
    store.save_profile(b)
    ex.scan_exposure(store, a.id, registry=fixture_registry(),
                     fetch=lambda br, u: ex.Fetched(PAGE_URL, 200, RESULT), use_browser=False)
    app = create_app(store, "tok-qa", {"testserver"}, registry_loader=lambda: None,
                     open_url=lambda u: True)
    c = TestClient(app, follow_redirects=False)
    c.cookies.set("freemyid_session", "tok-qa")
    page = c.get("/more").text
    cards = [CARD + part.split("</section>")[0] for part in page.split(CARD)[1:]]
    assert len(cards) == 2
    by_label = {("Alpha" if "Alpha" in x else "Beta"): x for x in cards}
    assert "Results for Alpha &lt;i&gt;one&lt;/i&gt;" in by_label["Alpha"]
    assert "<i>one</i>" not in page
    assert "out of 100" in by_label["Alpha"]
    # Beta was never scanned: Alpha's result must not show up under Beta's name
    assert "No picture yet" in by_label["Beta"] and "out of 100" not in by_label["Beta"]
    for x in cards:
        assert "https://" not in x and "Springfield" not in x and "Testperson" not in x


def test_sec95_protect_card_names_the_person_when_several(store, monkeypatch):
    monkeypatch.setattr(keyring, "set_password", lambda *a: None)
    from freemyid import checklist_state as cs
    a = make_profile(label="Alpha")
    b = make_profile(label="Beta")
    store.save_profile(a)
    store.save_profile(b)
    cf = cs.load_checklists()
    assert cf is not None and cf.checklists
    cs.set_done(store, a.id, cf.checklists[0].id, True)
    app = create_app(store, "tok-qa", {"testserver"}, registry_loader=lambda: None,
                     open_url=lambda u: True)
    c = TestClient(app, follow_redirects=False)
    c.cookies.set("freemyid_session", "tok-qa")
    page = c.get("/more").text
    protect = page.split("Protect yourself</h2>", 1)[1].split("</section>", 1)[0]
    first = store.list_profiles()[0].label
    assert first in protect


# --------------------------------------------------------------------------- SEC-93c guard

SCRIPT = ROOT / "tools" / "ci" / "check_commit_emails.sh"
GOOD = "242299803+GrayManSam@users.noreply.github.com"
BAD = "jane.testperson@example.com"


def _real_bash() -> str | None:
    """Full path of a usable bash. On Windows, CreateProcess searches System32 before PATH, so a
    bare "bash" can hit the WSL launcher (System32\\bash.exe, UTF-16 output, often no distro).
    Resolve through PATH instead and refuse the WSL stubs."""
    b = shutil.which("bash")
    if b and os.name == "nt" and any(d in b.lower() for d in ("\\system32\\", "\\windowsapps\\")):
        return None
    return b


BASH = _real_bash()
needs_git = pytest.mark.skipif(not (shutil.which("git") and BASH),
                               reason="git and a real bash (not the Windows WSL launcher) needed")


def _git(repo: Path, *args: str, email: str = GOOD, cemail: str | None = None) -> str:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": email,
           "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": cemail or email}
    return subprocess.run(["git", "-C", str(repo), *args], env=env, check=True,
                          capture_output=True, text=True).stdout.strip()


def _commit(repo: Path, msg: str, **kw) -> str:
    _git(repo, "commit", "-q", "--allow-empty", "-m", msg, **kw)
    return _git(repo, "rev-parse", "HEAD")


def _check(repo: Path, base: str, head: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([BASH or "bash", str(SCRIPT), base, head], check=False, cwd=repo, capture_output=True,
                          text=True, env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull})


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "r"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    return r


@needs_git
def test_guard_passes_noreply_and_flags_personal_email_masked(repo):
    base = _commit(repo, "one")
    ok = _commit(repo, "two")
    assert _check(repo, base, ok).returncode == 0
    bad = _commit(repo, "three", email=BAD)
    r = _check(repo, base, bad)
    assert r.returncode == 1
    assert BAD not in r.stdout + r.stderr and "jane.testperson" not in r.stdout + r.stderr
    assert "j***@e***" in r.stdout and "author" in r.stdout and "committer" in r.stdout


@needs_git
def test_guard_checks_committer_separately(repo):
    base = _commit(repo, "one")
    head = _commit(repo, "two", email=GOOD, cemail=BAD)
    r = _check(repo, base, head)
    assert r.returncode == 1 and "committer" in r.stdout and "author email" not in r.stdout


@needs_git
def test_guard_zero_before_checks_all_unpushed_commits(repo):
    _commit(repo, "one", email=BAD)
    head = _commit(repo, "two")
    r = _check(repo, "0" * 40, head)
    assert r.returncode == 1 and "j***@e***" in r.stdout


@needs_git
def test_guard_allowlist_is_exact_full_shas_only():
    allow = SCRIPT.read_text().split('ALLOW="', 1)[1].split('"', 1)[0].split()
    assert allow and all(len(s) == 40 and all(ch in "0123456789abcdef" for ch in s)
                         for s in allow)


@needs_git
def test_sec96_guard_fails_closed_on_unknown_base(repo):
    _commit(repo, "one", email=BAD)
    head = _commit(repo, "two", email=BAD)
    r = _check(repo, "deadbeef" * 5, head)
    assert r.returncode != 0
