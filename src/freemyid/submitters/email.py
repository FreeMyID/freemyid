"""Email tier: privacy-request letter from the removal mailbox (via engine.outbox).

* dry run           -> DRAFT request (dry_run=True), never sent.
* APPROVE_EACH      -> QUEUED_FOR_APPROVAL; state unchanged until the user approves.
* AUTO              -> sent now; the runner marks the broker SUBMITTED.
* no mailbox        -> falls back to a SEND_EMAIL_MANUALLY to-do (D2).
* send failed       -> "not sent" plus a plain reason and a to-do; never raises.
"""
from __future__ import annotations

import re
from typing import Any

from ..interfaces import RunContext, Submitter
from ..models import (
    Listing,
    ListingState,
    Request,
    RequestKind,
    RequestStatus,
    SubmitOutcome,
    Todo,
    TodoKind,
)
from . import assisted, base

# Fixed reasons. The exception text is never copied: a refused recipient often
# includes the address, and that address must not reach the person or the logs.
REASON_MAILER = "mailer not set up"
REASON_REFUSED = "refused address"
REASON_CONNECTION = "connection error"
REASON_FIRST = "first-email approval missing"
REASON_OTHER = "could not send"

_SETUP_PHRASES = (
    "no removal mailbox",
    "password not in keychain",
    "mail host not on allowlist",
    "not set up",
    "not configured",
    "real email sending is not enabled",
)
_REFUSED_PHRASES = ("refused address", "address refused", "recipient refused")
_AUTH_NAMES = frozenset({"SMTPAuthenticationError"})
_REFUSED_NAMES = frozenset({
    "SMTPRecipientsRefused", "SMTPSenderRefused", "SMTPDataError",
})
_CONNECTION_NAMES = frozenset({
    "ConnectionError", "ConnectionRefusedError", "ConnectionResetError",
    "ConnectionAbortedError", "BrokenPipeError", "TimeoutError", "socket.timeout",
    "OSError", "SMTPServerDisconnected", "SMTPConnectError", "gaierror",
})
# Real mailer: MailError("smtp failed: <TypeName>"). Outbox then keeps only the outer type.
_SMTP_FAILED = re.compile(r"^smtp failed: ([A-Za-z_][A-Za-z0-9_.]*)$")
_SEND_FAILED = re.compile(r"^send failed: ([A-Za-z_][A-Za-z0-9_.]*)$")

_TODO_TEXT: dict[str, tuple[str, str]] = {
    REASON_MAILER: (
        "Set up the removal mailbox",
        ("This email was not sent because the removal mailbox is not ready. "
         "Add the mailbox and save its password, then run the check again."),
    ),
    REASON_REFUSED: (
        "The site refused the removal email",
        ("This email was not sent. The site refused the letter. "
         "You can send it yourself from your own email program, or try again later."),
    ),
    REASON_CONNECTION: (
        "The removal email could not reach the mail server",
        ("This email was not sent because the connection to the mail server failed. "
         "Check the internet connection and that the mail app is running, then try again."),
    ),
    REASON_FIRST: (
        "Approve the first removal email",
        ("This email was not sent. The first email for this person waits for your OK. "
         "Open the emails waiting for approval and approve one. After that, routine "
         "emails can go out on their own. Formal demands still wait for you."),
    ),
    REASON_OTHER: (
        "The removal email was not sent",
        "This email was not sent. Nothing was changed at the site. Try again later.",
    ),
}
_TOKEN = {
    REASON_MAILER: "mailer_not_set_up",
    REASON_REFUSED: "refused_address",
    REASON_CONNECTION: "connection_error",
    REASON_FIRST: "first_email_approval",
    REASON_OTHER: "could_not_send",
}


class _CaughtMailer:
    """Forwards send and remembers the mailer's own error.

    ``send_request`` replaces that error with ``send failed: <type name>`` and drops
    the message, so the submitter would otherwise be unable to tell a refused address
    from a connection error.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.error: BaseException | None = None

    def send(self, profile: Any, to: str, subject: str, body: str, request_id: str) -> str:
        try:
            mid = self._inner.send(profile, to, subject, body, request_id)
        except Exception as exc:
            self.error = exc
            raise
        return str(mid)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def _names(exc: BaseException) -> set[str]:
    names = {cls.__name__ for cls in type(exc).__mro__}
    text = str(exc).strip()
    for pat in (_SMTP_FAILED, _SEND_FAILED):
        match = pat.fullmatch(text)
        if match:
            names.add(match.group(1))
    return names


def _classify(exc: BaseException) -> str:
    """A fixed reason. The exception text itself is never returned."""
    names = _names(exc)
    if names & _AUTH_NAMES:
        return REASON_MAILER
    if names & _REFUSED_NAMES:
        return REASON_REFUSED
    if names & _CONNECTION_NAMES:
        return REASON_CONNECTION
    text = str(exc).strip().lower()
    if any(phrase in text for phrase in _SETUP_PHRASES):
        return REASON_MAILER
    if any(phrase in text for phrase in _REFUSED_PHRASES):
        return REASON_REFUSED
    if text.startswith("smtp refused:"):
        return REASON_CONNECTION
    return REASON_OTHER


def _reason_from_failure(wrapped: BaseException, origin: BaseException | None) -> str:
    return _classify(origin if origin is not None else wrapped)


def _failed_request_id(ctx: RunContext) -> str | None:
    rows = ctx.store.list_requests(ctx.profile.id, ctx.broker.id, status=RequestStatus.FAILED)
    return rows[-1].id if rows else None


def _todo(ctx: RunContext, reason: str, request_id: str | None) -> Todo:
    title, body = _TODO_TEXT.get(reason, _TODO_TEXT[REASON_OTHER])
    kind = TodoKind.APPROVE_EMAIL if reason == REASON_FIRST else TodoKind.OTHER
    slug = _TOKEN.get(reason, _TOKEN[REASON_OTHER])
    return Todo(
        profile_id=ctx.profile.id, broker_id=ctx.broker.id, kind=kind,
        title=title, body=body, request_id=request_id,
        resume_token=f"email_not_sent:{ctx.broker.id}:{slug}",
    )


class EmailSubmitter(Submitter):
    method = "email"

    async def search(self, ctx: RunContext) -> list[Listing]:
        return []          # email brokers are not searched; the letter names the person

    def _unsent(self, ctx: RunContext, reason: str, *,
                request: Request | None = None) -> SubmitOutcome:
        req_id = request.id if request is not None else _failed_request_id(ctx)
        # A queued first email stays attached so the approval list is unchanged.
        # A failed send does not: the runner would otherwise count it as waiting.
        state = ListingState.FOUND if request is not None else ListingState.NEEDS_HUMAN
        return SubmitOutcome(new_state=state, request=request, todos=[_todo(ctx, reason, req_id)],
                             message=f"not sent: {reason}")

    async def submit(self, ctx: RunContext, listings: list[Listing]) -> SubmitOutcome:
        from ..engine.outbox import (
            OutboxError,
            compose,
            held_by_first_approval,
            needs_approval,
            queue_email,
            record_manual_letter,
        )
        kind: RequestKind = ctx.scratch.get("kind", RequestKind.OPT_OUT)
        original = ctx.scratch.get("original")
        use = base.confirmed(listings) or listings
        if ctx.profile.mailbox is None:
            subject, body = compose(ctx.profile, ctx.broker, use, ctx.state_law, kind,
                                    original=original)
            todo = record_manual_letter(
                ctx.store, assisted.manual_email_todo(ctx.profile, ctx.broker, subject, body),
                use, kind=kind, original=original, dry_run=ctx.dry_run, now=ctx.now)
            return SubmitOutcome(new_state=ListingState.NEEDS_HUMAN, todos=[todo],
                                 message="manual_email")
        watched = _CaughtMailer(ctx.mailer) if ctx.mailer is not None else None
        try:
            req = queue_email(ctx.store, ctx.profile, ctx.broker, use, kind=kind,
                              state_law=ctx.state_law, dry_run=ctx.dry_run, mailer=watched,
                              original=original, now=ctx.now)
        except OutboxError as exc:
            origin = watched.error if watched is not None else None
            return self._unsent(ctx, _reason_from_failure(exc, origin))
        if req.status == RequestStatus.SENT:
            new = (ListingState.AWAITING_VERIFICATION if ctx.broker.needs_email_verification
                   else ListingState.SUBMITTED)
            return SubmitOutcome(new_state=new, request=req, message="email_sent")
        if not ctx.dry_run and held_by_first_approval(ctx.profile, req, ctx.store):
            return self._unsent(ctx, REASON_FIRST, request=req)
        if (watched is None and not ctx.dry_run
                and not needs_approval(ctx.profile, kind, ctx.store)):
            return self._unsent(ctx, REASON_MAILER)
        return SubmitOutcome(new_state=ListingState.FOUND, request=req,
                             message="email_draft" if ctx.dry_run else "email_queued")
