"""Email tier: privacy-request letter from the removal mailbox (via engine.outbox).

* dry run           -> DRAFT request (dry_run=True), never sent.
* APPROVE_EACH      -> QUEUED_FOR_APPROVAL; state unchanged until the user approves.
* AUTO              -> sent now; the runner marks the broker SUBMITTED.
* no mailbox        -> falls back to a SEND_EMAIL_MANUALLY to-do (D2).
"""
from __future__ import annotations

from ..interfaces import RunContext, Submitter
from ..models import Listing, ListingState, RequestKind, RequestStatus, SubmitOutcome
from . import assisted, base


class EmailSubmitter(Submitter):
    method = "email"

    async def search(self, ctx: RunContext) -> list[Listing]:
        return []          # email brokers are not searched; the letter names the person

    async def submit(self, ctx: RunContext, listings: list[Listing]) -> SubmitOutcome:
        from ..engine.outbox import compose, queue_email
        kind: RequestKind = ctx.scratch.get("kind", RequestKind.OPT_OUT)
        original = ctx.scratch.get("original")
        use = base.confirmed(listings) or listings
        if ctx.profile.mailbox is None:
            subject, body = compose(ctx.profile, ctx.broker, use, ctx.state_law, kind,
                                    original=original)
            todo = assisted.manual_email_todo(ctx.profile, ctx.broker, subject, body)
            return SubmitOutcome(new_state=ListingState.NEEDS_HUMAN, todos=[todo],
                                 message="manual_email")
        req = queue_email(ctx.store, ctx.profile, ctx.broker, use, kind=kind,
                          state_law=ctx.state_law, dry_run=ctx.dry_run, mailer=ctx.mailer,
                          original=original, now=ctx.now)
        if req.status == RequestStatus.SENT:
            new = (ListingState.AWAITING_VERIFICATION if ctx.broker.needs_email_verification
                   else ListingState.SUBMITTED)
            return SubmitOutcome(new_state=new, request=req, message="email_sent")
        return SubmitOutcome(new_state=ListingState.FOUND, request=req,
                             message="email_draft" if ctx.dry_run else "email_queued")
