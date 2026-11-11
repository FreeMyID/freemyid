"""WO-609: a dry run's notice says it was practice; big to-do lists get a next step, not
"5 minutes"; "send it yourself" letters are counted. Fake people and fake brokers only.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from freemyid import notify
from freemyid.engine import runner as rmod
from freemyid.engine.runner import (
    MAILBOX_HINT_MIN,
    SMALL_NOTICE_MAX,
    end_notice,
    run,
)
from freemyid.models import Broker, Registry, TodoKind
from tests.conftest import make_profile

T0 = datetime(2026, 11, 1, tzinfo=UTC)
N_BROKERS = 50


class Rec:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None]] = []

    def notify(self, title: str, body: str, url: str | None = None) -> None:
        self.calls.append((title, body, url))


@pytest.fixture(autouse=True)
def _reset_window():
    notify.ThrottledNotifier._shared_started_at = None
    yield
    notify.ThrottledNotifier._shared_started_at = None


def _email_registry(n: int = N_BROKERS) -> Registry:
    brokers = [Broker(id=f"mail{i:02d}", name=f"Fake Mail {i}", url=f"https://mail{i:02d}.example/",
                      category="data_broker", domains=[f"mail{i:02d}.example"], method="email",
                      opt_out_email=f"privacy@mail{i:02d}.example") for i in range(n)]
    return Registry(version="2026.11.11-test", updated=T0.date(), brokers=brokers)


def _dry_run(store, notifier, n: int = N_BROKERS):
    p = make_profile(mailbox=None)
    store.save_profile(p)
    rep = run(store, _email_registry(n), [p], scan_only=False, dry_run=True,
              interactive=False, notifier=notifier, now=T0)
    return p, rep


def _no_pii(text: str) -> None:
    for pii in ("Jane", "Testperson", "Springfield", "@", "://", "mail0"):
        assert pii not in text


def test_dry_run_notice_is_labelled_practice_and_names_the_mailbox(store) -> None:
    rec = Rec()
    p, rep = _dry_run(store, rec)
    letters = [t for t in store.list_todos(p.id) if t.kind == TodoKind.SEND_EMAIL_MANUALLY]
    assert len(letters) == N_BROKERS
    assert rep.drafted_letters == N_BROKERS          # WO-609: letters are counted
    assert rep.drafted_emails == 0                    # nothing Free My ID would send itself
    assert rep.letters_need_mailbox == N_BROKERS
    assert len(rec.calls) == 1
    title, body, url = rec.calls[0]
    assert title.startswith("Practice run:")
    assert "minute" not in (title + body).lower()
    assert "removal mailbox" in body
    assert url is None
    _no_pii(title + body)


def test_summary_leads_with_add_a_mailbox(store) -> None:
    _p, rep = _dry_run(store, Rec())
    lines = rep.summary_lines()
    assert lines[0].startswith("Add a removal mailbox")
    assert sum("removal mailbox" in ln for ln in lines) == 1        # one line, not repeated
    assert f"{N_BROKERS} letter(s) written for you to send yourself." in lines


def test_few_letters_keep_the_plain_summary(store) -> None:
    _p, rep = _dry_run(store, Rec(), n=3)
    assert rep.drafted_letters == 3
    assert not rep.summary_lines()[0].startswith("Add a removal mailbox")


def test_dry_run_through_a_throttled_notifier_is_labelled_too(store) -> None:
    rec = Rec()
    _dry_run(store, notify.ThrottledNotifier(rec, now=lambda: T0), n=3)
    assert [c[0] for c in rec.calls] == ["Practice run: Free My ID needs 5 minutes of your help"]


def test_built_notifier_is_labelled_in_a_dry_run(store, monkeypatch) -> None:
    rec = Rec()
    monkeypatch.setattr(rmod.hmod, "get_notifier", lambda: notify.ThrottledNotifier(rec))
    _dry_run(store, None, n=2)
    assert len(rec.calls) == 1 and rec.calls[0][0].startswith("Practice run:")


def test_practice_label_is_added_once() -> None:
    rec = Rec()
    n = notify.practice(notify.practice(rec))
    n.notify("Practice run: hi", "b")
    n.notify("hi", "b")
    assert [c[0] for c in rec.calls] == ["Practice run: hi", "Practice run: hi"]


@pytest.mark.parametrize("n", [1, 3, SMALL_NOTICE_MAX])
def test_small_counts_keep_the_friendly_line(n) -> None:
    title, body = end_notice(n)
    assert title == "Free My ID needs 5 minutes of your help"
    assert body.startswith(f"{n} thing")


def test_large_counts_name_the_next_step_not_a_time() -> None:
    big = SMALL_NOTICE_MAX + 400
    title, body = end_notice(big, letters_need_mailbox=MAILBOX_HINT_MIN + 1)
    assert "minute" not in (title + body).lower() and str(big) not in title + body
    assert "Set up a removal mailbox" in body
    title, body = end_notice(big, letters_need_mailbox=0)
    assert "minute" not in (title + body).lower() and str(big) not in title + body
    assert "start with the first one" in body
    _no_pii(title + body)
