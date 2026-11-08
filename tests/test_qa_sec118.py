"""qa-security: SEC-118 (follow-up to the SEC-117 fix, ce62909). Runner._manual_to_email
retires the person's "send it yourself" to-do and resets the site to FOUND on ANY run once a
mailbox exists, including scan-only, dry-run and practice-mode runs (real_submissions_enabled
false, the default). Those runs then queue nothing real, so the person loses the actionable
letter with no approval item in its place until a real run happens. Nothing is sent, so this
is not a gate bypass. Strict xfail until _manual_to_email skips non-real runs."""
from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest

from freemyid import config as cfgmod
from freemyid.engine.runner import Runner
from freemyid.models import TodoKind
from freemyid.registry import Registry
from tests.test_proof_vault import MB, T0, B, FakeMailer, _no_mailbox_person, _run_once


def _run(store, p, now, *, scan_only: bool, dry_run: bool, real: bool):
    reg = Registry(version="t", updated=T0.date(), brokers=[B])
    cfg = cfgmod.Config(real_submissions_enabled=real, min_delay_s=0, max_delay_s=0)
    r = Runner(store, reg, scan_only=scan_only, dry_run=dry_run, interactive=False,
               broker_ids=None, only_due=False, mailer=FakeMailer(), cfg=cfg,
               state_laws={}, now=now)
    return asyncio.run(r.process(p, B))


@pytest.mark.parametrize("mode", [
    {"scan_only": True, "dry_run": True, "real": True},
    {"scan_only": False, "dry_run": True, "real": True},
    {"scan_only": False, "dry_run": False, "real": False},      # practice mode
], ids=["scan_only", "dry_run", "practice"])
def test_sec118_non_real_run_keeps_the_send_it_yourself_todo(store, mode):
    p = _no_mailbox_person(store)
    _run_once(store, p)
    p = p.model_copy(update={"mailbox": MB})
    store.save_profile(p)
    _run(store, p, T0 + timedelta(days=8), **mode)
    kinds = [t.kind for t in store.list_todos(p.id)]
    assert TodoKind.SEND_EMAIL_MANUALLY in kinds, \
        "a run that cannot queue the real email must not retire the manual letter"
