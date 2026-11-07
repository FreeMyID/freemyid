"""Assisted tier ("Do it with me"): build to-dos for the user to do in their own browser.

Nothing here touches the network. Todos are deduplicated by `handoff.persist_todo`.

* ASSISTED_OPT_OUT     web form / account-required / captcha brokers: steps from the
                       registry, the opt-out link and data-minimized Copy fields.
* SEND_EMAIL_MANUALLY  email brokers when the profile has no removal mailbox (D2): the
                       rendered letter plus Gmail / Outlook / Yahoo compose links.
* POSTAL_LETTER / PHONE_CALL for postal / phone-only brokers.
* GOVERNMENT_PORTAL    California DROP for CA residents (D3).
"""
from __future__ import annotations

import re

from ..engine import letters
from ..interfaces import RunContext, Submitter
from ..models import (
    Broker,
    Listing,
    ListingState,
    Method,
    Profile,
    StateLaw,
    SubmitOutcome,
    Todo,
    TodoKind,
)
from . import base

DROP_BROKER_ID = "ca_drop"
DROP_URL = "https://consumer.drop.privacy.ca.gov"
DROP_STEPS = [
    "Open the California DROP website with the button below.",
    "Sign in or create a free account and confirm you live in California.",
    "Fill in the details you are comfortable sharing. More details help brokers find you.",
    "Send one deletion request. It goes to more than 500 data brokers at once.",
    "Come back here and click \"I did it\".",
]


_REMOVAL_EMAIL = re.compile(r"\b(?:your |the )?removal email(?: address)?\b", re.IGNORECASE)
OWN_EMAIL = "an email address you can check"
NO_MAILBOX_NOTE = ("About the email box: use an email address you can check (your own is "
                   "fine). If the site says email is optional, you can leave it empty.")


def no_mailbox_step(step: str) -> str:
    """Registry steps say "removal email" (the dedicated mailbox). Without one, point the
    person at an address they can actually check (VM walkthrough finding 7)."""
    return _REMOVAL_EMAIL.sub(OWN_EMAIL, step)


def _steps(broker: Broker, reason: str | None, has_mailbox: bool = True) -> str:
    lines: list[str] = []
    if reason == "challenge":
        lines.append("Free My ID stopped because the site asked for a human check. "
                     "Please finish it yourself.")
    elif reason == "error":
        lines.append("Free My ID could not finish this one automatically. Please do it yourself.")
    steps = broker.steps or [
        "Open the opt-out page with the button below.",
        "Find your listing and follow the site's removal steps.",
        "Use the Copy buttons to fill in the form.",
    ]
    if not has_mailbox:
        steps = [no_mailbox_step(st) for st in steps]
    lines += [f"{i}. {s}" for i, s in enumerate(steps, 1)]
    if broker.needs_email_verification:
        lines.append(f"{len(steps) + 1}. Open the confirmation email the site sends and "
                     "click its link.")
    if not has_mailbox and any(OWN_EMAIL in st for st in steps):
        lines.append(NO_MAILBOX_NOTE)
    lines.append("Never pay. Removal is free.")
    return "\n".join(lines)


def opt_out_link(broker: Broker) -> str:
    return str(broker.opt_out_url or broker.url)


def assisted_todo(profile: Profile, broker: Broker, listings: list[Listing], *,
                  reason: str | None = None, again: bool = False) -> Todo:
    title = f"Remove {profile.label} from {broker.name}"
    if again:
        title = f"Ask {broker.name} again to remove {profile.label}"
    return Todo(profile_id=profile.id, broker_id=broker.id, kind=TodoKind.ASSISTED_OPT_OUT,
                title=title,
                body=_steps(broker, reason, has_mailbox=profile.mailbox is not None), links=[opt_out_link(broker)],
                copy_fields=base.copy_fields(profile, broker, listings),
                resume_token=f"assisted:{broker.id}")


def manual_email_todo(profile: Profile, broker: Broker, subject: str, body: str, *,
                      title: str | None = None) -> Todo:
    from ..engine.outbox import compose_links
    to = broker.opt_out_email or ""
    links = compose_links(to, subject, body)
    intro = ("Free My ID wrote this letter for you. Click Gmail, Outlook or Yahoo to open it "
             "ready to send, or copy it into any email program. Then click \"I did it\".\n\n")
    return Todo(profile_id=profile.id, broker_id=broker.id, kind=TodoKind.SEND_EMAIL_MANUALLY,
                title=title or f"Send {profile.label}'s removal letter to {broker.name}",
                body=intro + body, links=list(links.values()),
                copy_fields={"To": to, "Subject": subject, "Letter": body},
                resume_token=f"manual_email:{broker.id}")


def postal_todo(profile: Profile, broker: Broker, listings: list[Listing],
                state_law: StateLaw | None) -> Todo:
    from ..engine.outbox import effective_law
    v = letters.letter_vars(profile, broker, listings, effective_law(profile, state_law))
    text = letters.render("postal_letter", **v)
    return Todo(profile_id=profile.id, broker_id=broker.id, kind=TodoKind.POSTAL_LETTER,
                title=f"Mail a removal letter to {broker.name} for {profile.label}",
                body="Print this letter, sign it and mail it.\n\n" + text,
                links=[str(broker.url)], copy_fields={"Letter": text},
                resume_token=f"postal:{broker.id}")


def phone_todo(profile: Profile, broker: Broker, listings: list[Listing],
               state_law: StateLaw | None) -> Todo:
    from ..engine.outbox import effective_law
    v = letters.letter_vars(profile, broker, listings, effective_law(profile, state_law))
    text = letters.render("phone_script", broker_phone=broker.phone, **v)
    cf = {"Phone number to call": broker.phone} if broker.phone else {}
    return Todo(profile_id=profile.id, broker_id=broker.id, kind=TodoKind.PHONE_CALL,
                title=f"Call {broker.name} to remove {profile.label}",
                body=text, links=[str(broker.url)], copy_fields=cf,
                resume_token=f"phone:{broker.id}")


def drop_todo(profile: Profile, broker: Broker | None = None) -> Todo:
    """California DROP: one request reaches every registered data broker (D3)."""
    link = str(broker.opt_out_url) if broker and broker.opt_out_url else DROP_URL
    return Todo(profile_id=profile.id, broker_id=broker.id if broker else None,
                kind=TodoKind.GOVERNMENT_PORTAL,
                title=f"First step for {profile.label}: California's free removal website",
                body="\n".join(f"{i}. {s}" for i, s in enumerate(DROP_STEPS, 1)),
                links=[link], resume_token="gov:ca_drop")


def todo_for(profile: Profile, broker: Broker, listings: list[Listing],
             state_law: StateLaw | None, *, reason: str | None = None,
             again: bool = False) -> Todo:
    """The right human to-do for a broker handled in the Assisted tier."""
    from ..engine.outbox import compose
    from ..engine.tiers import has_email_route
    if broker.method == Method.EMAIL and has_email_route(broker):
        subject, body = compose(profile, broker, base.confirmed(listings) or listings,
                                state_law)
        return manual_email_todo(profile, broker, subject, body)
    if broker.method == Method.POSTAL and broker.postal:
        return postal_todo(profile, broker, listings, state_law)
    if broker.method == Method.PHONE and broker.phone and not broker.opt_out_url:
        return phone_todo(profile, broker, listings, state_law)
    return assisted_todo(profile, broker, listings, reason=reason, again=again)


class AssistedSubmitter(Submitter):
    """Generic Assisted submitter: never searches, `submit` returns a to-do."""

    method = "assisted"

    async def search(self, ctx: RunContext) -> list[Listing]:
        return []

    async def submit(self, ctx: RunContext, listings: list[Listing]) -> SubmitOutcome:
        todo = todo_for(ctx.profile, ctx.broker, listings, ctx.state_law,
                        reason=ctx.scratch.get("reason"), again=ctx.scratch.get("again", False))
        return SubmitOutcome(new_state=ListingState.NEEDS_HUMAN, todos=[todo],
                             message=f"assisted:{todo.kind.value}")
