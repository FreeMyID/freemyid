"""Registry-at-scale time budgets (roadmap 0.7: "the full registry loads, scans and re-checks
inside time budgets").

Synthetic registries only (tests/scale/registry_gen.py, fake brokers on *.example.test);
fake people; no network; nothing is sent. Budgets are generous (several times what a
developer laptop measures, so slow CI runners pass) but each one is far below what the
O(n^2) code they guard against took. Measured on 2026-11-13, 1,000 brokers, before -> after
the fixes on integrate/registry-scale:

    registry load + validate     0.63 s           (budget 3 s)
    run planning                 0.49 s -> 0.006 s (budget 1 s)
    full dry run                 8.6 s  -> 0.42 s  (budget 5 s)
    dry re-run                   11.9 s -> 0.07 s  (budget 3 s)

Scaling checks compare 2,000 against 1,000 brokers: linear code roughly doubles, quadratic
code roughly quadruples; the limit (3x) sits between, using the best of two tries.
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

import pytest

from freemyid import config as cfgmod
from freemyid import paths
from freemyid.engine import exposure, outbox, tiers
from freemyid.engine.runner import Runner, run
from freemyid.netpolicy import NetPolicy
from freemyid.registry import load_registry
from tests.conftest import make_profile
from tests.scale import registry_gen

pytestmark = pytest.mark.scale

N = 1000
MAX_GROWTH = 3.0      # time(2N) / time(N); linear ~2, quadratic ~4


def _secs(fn: Callable[[], Any], tries: int = 1) -> float:
    best = float("inf")
    for _ in range(tries):
        t = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t)
    return best


class Notes:
    def __init__(self) -> None:
        self.n: list[tuple[str, str]] = []

    def notify(self, title: str, body: str, url: str | None = None) -> None:
        self.n.append((title, body))


def _write_registry(tmp_path, n: int):
    p = tmp_path / f"registry-{n}.yaml"
    p.write_text(registry_gen.registry_yaml(n), encoding="utf-8")
    return p


def test_generator_mix_is_realistic():
    reg = registry_gen.registry(N)
    mix = registry_gen.mix(reg)
    assert len(reg.brokers) == N
    assert 0.65 <= mix["email"] / N <= 0.75
    assert 0.20 <= mix["web_form"] / N <= 0.30
    assert 0.03 <= mix["people_search"] / N <= 0.08
    assert all(d.endswith(".example.test") for b in reg.brokers for d in b.domains)
    assert any(b.covered_by for b in reg.brokers)


def test_registry_load_and_validate_budget(tmp_path):
    p1, p2 = _write_registry(tmp_path, N), _write_registry(tmp_path, 2 * N)
    t1 = _secs(lambda: load_registry(p1), tries=2)
    assert t1 < 3.0, f"registry load+validate took {t1:.2f}s at {N} brokers"
    t2 = _secs(lambda: load_registry(p2), tries=2)
    assert t2 / t1 < MAX_GROWTH, f"registry load grows {t2 / t1:.1f}x for 2x brokers"


def test_netpolicy_budget():
    reg = registry_gen.registry(N)
    assert _secs(lambda: NetPolicy(reg)) < 0.25


def test_exposure_planner_budget(store):
    reg = registry_gen.registry(N)
    prof = make_profile()
    store.save_profile(prof)
    assert _secs(lambda: exposure.scan_brokers(reg, prof)) < 0.25
    t = _secs(lambda: exposure.scan_exposure(store, prof.id, registry=reg, offline=True))
    assert t < 2.0, f"offline exposure scan took {t:.2f}s"


def _plan(store, reg, prof) -> list[Any]:
    cfg = cfgmod.load()
    r = Runner(store, reg, scan_only=False, dry_run=True, interactive=False, broker_ids=None,
               only_due=False, state_laws={}, cfg=cfg)
    return [(tiers.tier_for(b, prof, cfg, registry=reg), tiers.submit_target(b, reg),
             r._ctx(prof, b)) for b in r.brokers()]


def test_run_planning_budget(store):
    prof = make_profile()
    store.save_profile(prof)
    r1, r2 = registry_gen.registry(N), registry_gen.registry(2 * N)
    t1 = _secs(lambda: _plan(store, r1, prof), tries=2)
    assert t1 < 1.0, f"run planning took {t1:.2f}s at {N} brokers"
    t2 = _secs(lambda: _plan(store, r2, prof), tries=2)
    # tiny absolute numbers are noisy: only judge growth once it is measurable
    assert t2 < 0.05 or t2 / t1 < MAX_GROWTH, f"run planning grows {t2 / t1:.1f}x"


def _dry_runs(store, reg) -> tuple[float, float, int, int, Notes]:
    prof = make_profile()
    store.save_profile(prof)
    notes = Notes()

    def once():
        return run(store, reg, [prof], scan_only=False, dry_run=True, interactive=False,
                   notifier=notes, state_laws={})
    e0 = len(store.events(limit=10**7))
    first = _secs(once)
    e1 = len(store.events(limit=10**7))
    again = _secs(once)
    e2 = len(store.events(limit=10**7))
    return first, again, e1 - e0, e2 - e1, notes


def test_full_dry_run_budget_and_store_growth(store):
    first, again, ev1, ev2, notes = _dry_runs(store, registry_gen.registry(N))
    assert first < 5.0, f"first dry run took {first:.2f}s at {N} brokers"
    assert again < 3.0, f"dry re-run took {again:.2f}s at {N} brokers"
    # store growth: a handful of PII-free events per broker on the first run, few after
    assert ev1 <= 5 * N, f"first run wrote {ev1} events for {N} brokers"
    assert ev2 <= N, f"re-run wrote {ev2} events for {N} brokers"
    assert len(notes.n) == 2       # exactly one calm notification per run


def test_full_dry_run_scales_linearly(tmp_path, monkeypatch):
    from freemyid.storage import Store
    times = []
    for n in (N, 2 * N):
        monkeypatch.setenv("FREEMYID_HOME", str(tmp_path / f"home-{n}"))
        s = Store()
        try:
            first, again, *_ = _dry_runs(s, registry_gen.registry(n))
        finally:
            s.close()
        times.append(first + again)
    assert times[1] / times[0] < MAX_GROWTH, \
        f"dry runs grow {times[1] / times[0]:.1f}x for 2x brokers ({times})"


def test_outbox_queue_every_email_broker_budget(store):
    reg = registry_gen.registry(N)
    prof = make_profile()
    store.save_profile(prof)
    emails = [b for b in reg.brokers if b.opt_out_email]
    t = _secs(lambda: [outbox.queue_email(store, prof, b, [], dry_run=True) for b in emails])
    assert t < 3.0, f"queueing {len(emails)} dry-run letters took {t:.2f}s"


def test_today_page_and_cli_json_budget(store, tmp_path):
    from fastapi.testclient import TestClient
    from typer.testing import CliRunner

    from freemyid import cli
    from freemyid.wizard import server

    reg = registry_gen.registry(N)
    dest = paths.registry_cache_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(registry_gen.registry_yaml(N), encoding="utf-8")
    prof = make_profile()
    store.save_profile(prof)
    run(store, reg, [prof], scan_only=False, dry_run=True, interactive=False,
        notifier=Notes(), state_laws={})
    assert len(store.list_statuses(prof.id)) == N

    # The dashboard's default loader re-reads the registry on every page (CHANGE REQUEST,
    # wizard); the budget below is for the page itself with a loaded registry.
    app = server.create_app(store, "tok", {"testserver"}, registry_loader=lambda: reg)
    c = TestClient(app)
    c.cookies.set(server.COOKIE, "tok")
    t = _secs(lambda: c.get("/"))
    assert c.get("/").status_code == 200
    assert t < 1.0, f"Today page took {t:.2f}s with {N} broker statuses"

    res = None

    def status_json():
        nonlocal res
        res = CliRunner().invoke(cli.app, ["status", "--json"])
    t = _secs(status_json)
    assert res is not None and res.exit_code == 0
    assert len(json.loads(res.stdout)["profiles"][0]["brokers"]) == N
    assert t < 3.0, f"status --json took {t:.2f}s at {N} brokers"


@pytest.mark.xfail(strict=True, reason=(
    "FINDING (roadmap 0.7): engine/exposure.py _scan_events reads only the newest 5,000 "
    "events (Store.events has no action filter), so a person's last exposure scan "
    "disappears from the dashboard once later events pass 5,000. One first run at 2,000 "
    "brokers writes 7,368. Needs CHANGE REQUEST Store.events(action=...)."))
def test_latest_exposure_survives_a_big_run(store):
    from freemyid.models import Actor, Event
    reg = registry_gen.registry(N)
    prof = make_profile()
    store.save_profile(prof)
    exposure.scan_exposure(store, prof.id, registry=reg, offline=True)
    assert exposure.latest_exposure(store, prof, reg) is not None
    for i in range(5001):     # what one first run at 2,000 brokers writes (ids/enums only)
        store.log(Event(profile_id=prof.id, broker_id=f"fakee{i % 2000:05d}",
                        actor=Actor.ENGINE, action="presumed_listed"))
    assert exposure.latest_exposure(store, prof, reg) is not None
