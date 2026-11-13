"""Email pacing per removal mailbox (roadmap 0.7 "Registry at scale").

With 700+ email-route brokers, one run (or one click on "approve" in AUTO mode, which
releases every held email) used to hand hundreds of letters to the person's own mailbox in
a few seconds. Mail providers cap daily sends and flag bursts from personal accounts, and a
flagged account stops the removal letters for everyone who shares it.

Rules (per mailbox address, so people who share one removal mailbox share one budget):
- At most `daily_cap(provider)` real emails are handed to the mailer in any WINDOW.
- New email requests are only created while (sent in WINDOW + still queued) < cap. So the
  approval list never holds more than a day's worth, and approving the first email can
  release at most one day's worth.
- A site that was paced stays FOUND and is retried at the next run after RETRY_AFTER.
- An email the person approves by hand always goes out: it is one email they asked for.

The caps are deliberately far below what providers publish for personal accounts (not sure
of the exact current numbers per provider; check the provider's help pages before raising
them). WINDOW is 20 hours rather than 24 so a daily scheduled run that starts a few minutes
earlier than yesterday's still gets a full budget.
"""
from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from ..models import Method, Profile, RequestStatus

if TYPE_CHECKING:
    from ..storage import Store

WINDOW = timedelta(hours=20)
RETRY_AFTER = timedelta(hours=20)
#: emails per removal mailbox per WINDOW, by MailboxConfig.provider
PROVIDER_DAILY_CAP: dict[str, int] = {
    "gmail": 100,
    "yahoo": 100,
    "icloud": 100,
    "outlook": 100,
    "proton_bridge": 50,
    "other": 50,
}
DEFAULT_DAILY_CAP = 50
PACED_EVENT = "email_paced"   # Event action: ids and counts only


def daily_cap(profile: Profile) -> int:
    if profile.mailbox is None:
        return 0
    return PROVIDER_DAILY_CAP.get(profile.mailbox.provider, DEFAULT_DAILY_CAP)


def _addr(profile: Profile) -> str | None:
    return profile.mailbox.address.strip().lower() if profile.mailbox else None


def _utc(ts: datetime) -> datetime:
    return ts if ts.tzinfo is not None else ts.replace(tzinfo=UTC)


class SendPacer:
    """Send budget for one run (or one approval). Reads the requests table once, lazily."""

    def __init__(self, store: Store, now: datetime) -> None:
        self.store = store
        self.now = _utc(now)
        self._sent: Counter[str] | None = None       # sent in WINDOW, per mailbox address
        self._queued: Counter[str] = Counter()       # open real email requests, per address
        self.paced: Counter[str] = Counter()         # profile id -> sites held back this run

    def _load(self) -> Counter[str]:
        if self._sent is None:
            addr_of = {p.id: _addr(p) for p in self.store.list_profiles()}
            since = self.now - WINDOW
            sent: Counter[str] = Counter()
            for status in (RequestStatus.SENT, RequestStatus.QUEUED_FOR_APPROVAL):
                for r in self.store.list_requests(status=status):
                    addr = addr_of.get(r.profile_id)
                    if not addr or r.dry_run or r.method != Method.EMAIL:
                        continue
                    if status == RequestStatus.QUEUED_FOR_APPROVAL:
                        self._queued[addr] += 1
                    elif r.sent_at is not None and _utc(r.sent_at) >= since:
                        sent[addr] += 1
            self._sent = sent
        return self._sent

    def sends_left(self, profile: Profile) -> int:
        addr = _addr(profile)
        if addr is None:
            return 0
        return max(0, daily_cap(profile) - self._load()[addr])

    def new_left(self, profile: Profile) -> int:
        addr = _addr(profile)
        if addr is None:
            return 0
        return max(0, self.sends_left(profile) - self._queued[addr])

    def take_new(self, profile: Profile) -> bool:
        """Reserve room for one NEW email request. False = pace it (try again later)."""
        if self.new_left(profile) <= 0:
            self.paced[profile.id] += 1
            return False
        self._queued[str(_addr(profile))] += 1
        return True

    def take_send(self, profile: Profile) -> bool:
        """Room to hand one stored request to the mailer now. Moves it from queued to sent."""
        if self.sends_left(profile) <= 0:
            return False
        addr = str(_addr(profile))
        self._load()[addr] += 1
        if self._queued[addr] > 0:
            self._queued[addr] -= 1
        return True

    def note_sent(self, profile: Profile) -> None:
        """An email went out without asking (the person approved it by hand)."""
        addr = _addr(profile)
        if addr is None:
            return
        self._load()[addr] += 1
        if self._queued[addr] > 0:
            self._queued[addr] -= 1

    def cancel_new(self, profile: Profile) -> None:
        """A reserved request was not created after all (an open one was reused)."""
        addr = _addr(profile)
        if addr is not None and self._queued[addr] > 0:
            self._queued[addr] -= 1
