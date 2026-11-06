"""Human handoff (CAPTCHA, ID upload, unexpected page, match review). Never solves anything.

* `QueuedHandoff` (scheduled / headless / non-tty): persist the Todo with a resume_token,
  notify (PII-free), return False immediately. Never blocks.
* `InteractiveHandoff`: persist the Todo, open a HEADED browser on the same URL (cookies
  carried over), notify, then wait until the user presses Enter, marks the todo done in the
  dashboard, or the timeout passes. Falls back to queued behaviour when there is no tty or
  no display.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import TYPE_CHECKING, Any, cast

from ..models import Actor, Event, Todo
from ..models import ListingState as S

if TYPE_CHECKING:
    from playwright.async_api import Page

    from ..interfaces import Notifier
    from ..storage import Store
    from .browser import BrowserManager

log = logging.getLogger(__name__)


class LogNotifier:
    """Fallback when freemyid.notify is not available. Body is PII-free by contract."""

    def notify(self, title: str, body: str, url: str | None = None) -> None:
        log.info("notify: %s: %s", title, body)


def get_notifier() -> Notifier:
    try:
        from ..notify import get_notifier as _gn  # type: ignore[import-not-found]
        return _gn()
    except Exception:  # noqa: BLE001 - module may not exist yet / no desktop session
        return LogNotifier()


def resume_token(todo: Todo) -> str:
    return f"{todo.profile_id}:{todo.broker_id or '-'}:{todo.kind.value}"


def _existing_open(store: Store, todo: Todo) -> Todo | None:
    for t in store.list_todos(todo.profile_id):
        if t.broker_id == todo.broker_id and t.kind == todo.kind and t.request_id == \
                todo.request_id:
            return t
    return None


def persist_todo(store: Store, todo: Todo) -> Todo:
    """Save a todo unless an identical open one exists (dedupe across scheduled runs)."""
    if not todo.resume_token:
        todo = todo.model_copy(update={"resume_token": resume_token(todo)})
    cur = _existing_open(store, todo)
    if cur:
        return cur
    store.save_todo(todo)
    return todo


GENERIC_HELP = "Free My ID needs your help with 1 site. Open Free My ID to see it."


class QueuedHandoff:
    def __init__(self, store: Store, notifier: Notifier, label: str = "") -> None:
        self.store, self.notifier, self.label = store, notifier, label
        self.count = 0

    async def request(self, todo: Todo, page: Page | None, timeout_s: int = 900) -> bool:
        persist_todo(self.store, todo)
        self.count += 1
        # SEC-28: lock-screen text stays generic (no label, kind or site)
        self.notifier.notify("Free My ID needs you", GENERIC_HELP)
        return False


class InteractiveHandoff(QueuedHandoff):
    def __init__(self, store: Store, notifier: Notifier, browser: BrowserManager | None,
                 label: str = "") -> None:
        super().__init__(store, notifier, label)
        self.browser = browser

    @staticmethod
    def can_block() -> bool:
        if not sys.stdin or not sys.stdin.isatty():
            return False
        if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or
                                                     os.environ.get("WAYLAND_DISPLAY")):
            return False
        return True

    async def request(self, todo: Todo, page: Page | None, timeout_s: int = 900) -> bool:
        if not self.can_block():
            return await super().request(todo, page, timeout_s)
        todo = persist_todo(self.store, todo)
        self.count += 1
        headed_ctx = None
        if page is not None and self.browser is not None:
            try:
                state = await page.context.storage_state()
                hosts = sorted(getattr(page.context, "freemyid_hosts", set()))
                headed_ctx = await self.browser.new_context(hosts, storage_state=state,
                                                            headed=True)
                hp = await headed_ctx.new_page()
                await self.browser.goto(hp, page.url, check_challenge=False)
            except Exception as e:  # noqa: BLE001
                log.warning("could not open visible browser: %s", type(e).__name__)
        self.notifier.notify("Free My ID needs you", GENERIC_HELP)
        print(f"\n[Free My ID] {todo.title}\n  {todo.body}\n"
              "  Finish it in the browser window, then press Enter here "
              f"(or wait {timeout_s // 60} min to skip).", flush=True)
        done = await self._wait(todo, timeout_s)
        if headed_ctx is not None:
            try:
                if page is not None and done:
                    # carry the solved session back to the automated page's context
                    await page.context.add_cookies(cast(Any, await headed_ctx.cookies()))
                await headed_ctx.close()
            except Exception as e:  # noqa: BLE001
                log.debug("closing visible browser failed: %s", type(e).__name__)
        if done:
            self.store.complete_todo(todo.id)
        return done

    async def _wait(self, todo: Todo, timeout_s: int) -> bool:
        loop = asyncio.get_running_loop()
        enter = loop.run_in_executor(None, sys.stdin.readline)
        deadline = loop.time() + timeout_s
        while loop.time() < deadline:
            if enter.done():
                return True
            if all(t.id != todo.id for t in self.store.list_todos(todo.profile_id)):
                return True      # resolved from the dashboard
            await asyncio.sleep(1.0)
        return False


def make_handoff(store: Store, notifier: Notifier, interactive: bool,
                 browser: BrowserManager | None, label: str = "") -> QueuedHandoff:
    if interactive:
        return InteractiveHandoff(store, notifier, browser, label)
    return QueuedHandoff(store, notifier, label)


# --------------------------------------------------------------------------- resolution
# Helpers for the dashboard / CLI (wizard-packager) once a human has acted.


def confirm_review(store: Store, listing_id: str, profile_id: str, is_me: bool) -> None:
    """User answered a REVIEW_MATCH todo. A 'yes' promotes the listing to CONFIRMED (the
    matcher keeps user confirmations on re-scan); 'no' leaves it ignored."""
    from ..models import MatchLevel
    for li in store.list_listings(profile_id):
        if li.id == listing_id:
            if is_me:
                li = li.model_copy(update={
                    "match_level": MatchLevel.CONFIRMED,
                    "match_reasons": sorted({*li.match_reasons, "user_confirmed"})})
            else:
                li = li.model_copy(update={"match_level": MatchLevel.NO_MATCH,
                                           "match_reasons": ["user_rejected"]})
            store.save_listing(li)
            st = store.get_status(profile_id, li.broker_id)
            store.save_status(st.model_copy(update={"next_check_at": None}))  # re-run soon
            store.log(Event(profile_id=profile_id, broker_id=li.broker_id, actor=Actor.USER,
                            action="review_match", detail={"is_me": is_me}))
            return


def mark_manual_submitted(store: Store, profile_id: str, broker_id: str,
                          request_id: str | None = None) -> None:
    """User mailed the letter / made the call / finished the form by hand."""
    from ..models import RequestStatus, utcnow
    from ..state import transition
    now = utcnow()
    st = store.get_status(profile_id, broker_id)
    new = transition(st, S.SUBMITTED, now)
    store.save_status(new)
    if request_id and (r := store.get_request(request_id)):
        store.save_request(r.model_copy(update={"status": RequestStatus.SENT, "sent_at": now}))
    store.log(Event(profile_id=profile_id, broker_id=broker_id, actor=Actor.USER,
                    action="manual_submitted", from_state=st.state, to_state=new.state))


_SUBMIT_KINDS = frozenset({"assisted_opt_out", "send_email_manually", "postal_letter",
                           "phone_call", "account_required"})


def mark_resolved(store: Store, todo: Todo) -> None:
    """Dashboard "I did it" hook (wizard/server.py looks this up by name).

    For hand-done opt-outs (Assisted card, manual email, letter, call) the broker becomes
    SUBMITTED so the re-check and escalation clocks start. Follow-up/demand letters sent by
    hand do not restart the clock. Other kinds just get closed by the caller.
    """
    if not todo.broker_id or todo.kind.value not in _SUBMIT_KINDS:
        return
    tok = todo.resume_token or ""
    if tok.count(":") >= 2:          # manual_email:<broker>:<follow_up|legal_demand>
        store.log(Event(profile_id=todo.profile_id, broker_id=todo.broker_id,
                        actor=Actor.USER, action="manual_letter_sent",
                        detail={"todo_kind": todo.kind.value}))
        return
    from ..state import can_transition
    st = store.get_status(todo.profile_id, todo.broker_id)
    if st.state == S.SUBMITTED or not can_transition(st.state, S.SUBMITTED):
        return
    if st.state in (S.UNKNOWN, S.NOT_FOUND):
        return      # nothing was found to remove; just close the to-do
    mark_manual_submitted(store, todo.profile_id, todo.broker_id, todo.request_id)
