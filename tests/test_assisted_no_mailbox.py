"""Adopted from engine/_test_drafts: VM walkthrough finding 7. Without a removal mailbox the
Assisted card must not ask for "your removal email"."""
from __future__ import annotations

from freemyid.models import Broker, MailboxConfig
from freemyid.submitters import assisted
from tests.conftest import make_profile

B = Broker.model_validate({
    "id": "fakew", "name": "Fake W", "url": "https://fakew.example/",
    "category": "people_search", "domains": ["fakew.example"], "method": "web_form",
    "opt_out_url": "https://fakew.example/optout",
    "steps": ["Open the opt-out page.", "Find your listing and copy its web address.",
              "Type your removal email address.",
              "Paste it on the opt-out page and type your removal email."]})
MB = MailboxConfig(address="removals@mail.example", imap_host="imap.mail.example",
                   smtp_host="smtp.mail.example", username="removals@mail.example")


def test_no_mailbox_steps_point_to_an_email_you_can_check():
    t = assisted.assisted_todo(make_profile(), B, [])
    assert "removal email" not in t.body.lower()
    assert "3. Type an email address you can check." in t.body
    assert assisted.NO_MAILBOX_NOTE in t.body
    assert "Email for removals" not in t.copy_fields


def test_with_mailbox_steps_unchanged_and_copy_field_present():
    t = assisted.assisted_todo(make_profile(mailbox=MB), B, [])
    assert "3. Type your removal email address." in t.body
    assert assisted.NO_MAILBOX_NOTE not in t.body
