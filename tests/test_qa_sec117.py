"""qa-security: SEC-117 (proof vault 792fdc0). A 'send it yourself' letter is stored as a
non-dry-run DRAFT request. Once the person adds a removal mailbox, queue_email reuses that
DRAFT (outbox._open_request) and returns it without queueing anything, so the letter never
reaches the approval screen and is never sent. Strict xfail until fixed."""
from __future__ import annotations

from datetime import timedelta

import pytest

from freemyid.models import RequestStatus
from tests.test_proof_vault import MB, T0, B, _manual_todo, _no_mailbox_person, _run_once


@pytest.mark.xfail(strict=True, reason="SEC-117: a manual-letter DRAFT blocks the real email queue")
def test_sec117_adding_a_mailbox_later_queues_the_email(store):
    p = _no_mailbox_person(store)
    _run_once(store, p)
    assert _manual_todo(store, p).request_id          # the DRAFT exists
    p = p.model_copy(update={"mailbox": MB})
    store.save_profile(p)
    _run_once(store, p, T0 + timedelta(days=8))
    live = [r for r in store.list_requests(p.id, B.id)
            if r.status in (RequestStatus.QUEUED_FOR_APPROVAL, RequestStatus.SENT)]
    assert live, "after a mailbox is added the letter must be queued for approval or sent"
