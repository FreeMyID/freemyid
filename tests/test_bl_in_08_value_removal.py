"""BL-IN-08 engine: phone-only / email-only removal. Reverse-lookup hits are never
CONFIRMED by the matcher (rule 7), the letter names only the value, and the value goes out
only with its explicit permission. Fake people and brokers only, no network."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from freemyid.consent import CURRENT_TEXT_VERSION
from freemyid.engine import _dev, matcher, outbox, tiers
from freemyid.models import (
    Broker,
    Consent,
    ConsentBasis,
    MailboxConfig,
    MatchLevel,
    Permissions,
    Profile,
    ProfileField,
    RequestKind,
    Tier,
)
from freemyid.submitters import web_form
from tests.conftest import make_profile

C = Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
            text_version=CURRENT_TEXT_VERSION)
MB = MailboxConfig(address="removals@example.org", imap_host="imap.example.org",
                   smtp_host="smtp.example.org", username="removals@example.org")
PHONE = "217-555-0142"
EMAIL = "Jane.Testperson@example.com"


def phone_person(**over):
    kw = {"label": "T", "consent": C, "removal_scope": "phone", "phones": [PHONE],
          "permissions": Permissions(allow_phone_disclosure=True)}
    kw.update(over)
    return Profile(**kw)


def email_person(**over):
    kw = {"label": "T", "consent": C, "removal_scope": "email", "emails": [EMAIL],
          "permissions": Permissions(allow_email_disclosure=True)}
    kw.update(over)
    return Profile(**kw)


def broker(**over):
    data = {"id": "devphone", "name": "Dev Phone", "url": "https://devphone.example/",
            "category": "people_search", "domains": ["devphone.example"], "method": "email",
            "opt_out_email": "privacy@devphone.example",
            "phone_search_url_pattern": "https://devphone.example/phone/{phone_dashed}",
            "email_search_url_pattern": "https://devphone.example/email/{email}"}
    data.update(over)
    return Broker.model_validate(data)


def cand(**kw):
    return matcher.Candidate(url="https://devphone.example/p/1", **kw)


# ------------------------------------------------------------------ matcher (rule 7)


def test_lookup_hit_is_possible_never_confirmed():
    p = phone_person()
    for c in (cand(), cand(name="Anyone Testperson", phones=["(217) 555-0142"],
                           locations=["Springfield, IL"], age=46)):
        r = matcher.score_value(p, c, "phone")
        assert r.level is MatchLevel.POSSIBLE and r.reasons == ["phone_lookup"]


def test_lookup_page_showing_another_number_is_not_a_hit():
    assert matcher.score_value(phone_person(), cand(phones=["217-555-0199"]),
                               "phone").level is MatchLevel.NO_MATCH
    assert matcher.score_value(email_person(), cand(emails=["other@example.com"]),
                               "email").level is MatchLevel.NO_MATCH
    assert matcher.score_value(email_person(), cand(emails=[EMAIL.lower()]),
                               "email").level is MatchLevel.POSSIBLE


def test_score_lookup_listings_and_rescore_leaves_them_alone():
    p = phone_person()
    out = matcher.score_lookup(p, "devphone", [cand(), cand()], "phone")
    assert len(out) == 1
    li = out[0]
    assert li.match_level is MatchLevel.POSSIBLE and ProfileField.PHONE in li.shown_fields
    assert matcher.rescore(p, li) is li


def test_value_profile_never_name_matches():
    p = phone_person()
    c = cand(name=" ", locations=["Springfield, IL"])
    assert matcher.score(p, c).level is MatchLevel.NO_MATCH


# ------------------------------------------------------------------ search URLs


def test_value_search_urls_need_permission_and_stay_on_domain():
    b = broker()
    assert web_form.value_search_urls(b, phone_person()) == [
        "https://devphone.example/phone/217-555-0142"]
    assert web_form.value_search_urls(b, phone_person(
        permissions=Permissions())) == []
    assert web_form.value_search_urls(b, email_person()) == [
        "https://devphone.example/email/jane.testperson%40example.com"]
    assert web_form.value_search_urls(b, email_person(
        permissions=Permissions(allow_phone_disclosure=True))) == []
    many = phone_person(phones=["217-555-0101", "217-555-0102", "217-555-0103",
                                "217-555-0104", "12345"])
    assert len(web_form.value_search_urls(b, many)) == 3


def test_value_profile_has_no_name_search():
    b = broker(search_url_pattern="https://devphone.example/name/{first}-{last}")
    assert web_form.search_url(b, phone_person()) is None


def test_search_values_reads_each_lookup_page(monkeypatch):
    seen = []

    async def page(bm, ctx, url, *, lookup=None):
        seen.append((url, lookup))
        return matcher.score_lookup(ctx.profile, ctx.broker.id, [cand()], lookup), b"png"

    monkeypatch.setattr(web_form, "_search_page", page)
    p = phone_person(phones=["217-555-0142", "217-555-0143"])
    ctx = SimpleNamespace(broker=broker(), profile=p, store=None, now=None,
                          scratch={"browser": object()})
    out = asyncio.run(web_form.search_listings(ctx))
    assert [lk for _, lk in seen] == ["phone", "phone"] and len(out) == 1
    assert ctx.scratch["search_screenshot"] == b"png"


def test_search_values_unreadable_page_fails_the_search(monkeypatch):
    async def page(bm, ctx, url, *, lookup=None):
        raise web_form.UnexpectedPage("search_http_503")

    monkeypatch.setattr(web_form, "_search_page", page)
    ctx = SimpleNamespace(broker=broker(), profile=phone_person(), store=None, now=None,
                          scratch={"browser": object()})
    with pytest.raises(web_form.UnexpectedPage):
        asyncio.run(web_form.search_listings(ctx))


# ------------------------------------------------------------------ tiers


def test_value_only_is_never_automatic():
    p = phone_person(mailbox=MB)
    assert tiers.tier_for(broker(), p) is Tier.EMAIL
    assert tiers.tier_for(broker(), phone_person()) is Tier.ASSISTED


def test_value_applicable():
    p = phone_person()
    assert tiers.value_applicable(broker(), p)                               # lookup
    assert tiers.value_applicable(broker(phone_search_url_pattern=None), p)  # email route
    web = broker(phone_search_url_pattern=None, method="web_form", opt_out_email=None,
                 opt_out_url="https://devphone.example/optout")
    assert not tiers.value_applicable(web, p)
    assert tiers.value_applicable(web.model_copy(update={
        "phone_search_url_pattern": "https://devphone.example/phone/{phone_digits}"}), p)


# ------------------------------------------------------------------ letter


def _listing(p):
    return matcher.score_lookup(p, "devphone", [cand()], str(p.removal_scope))[0]


def test_phone_letter_names_only_the_number():
    p = phone_person(mailbox=MB, name=make_profile().name)   # even if a name is on file
    subject, body = outbox.compose(p, broker(), [_listing(p)], None)
    assert "Please delete the records for a phone number" in subject
    assert PHONE in body and "https://devphone.example/p/1" in body
    assert "removals@example.org" in body
    for leak in ("Jane", "Testperson", "Springfield", "Evergreen"):
        assert leak not in body and leak not in subject


def test_email_letter_names_only_the_address_and_follow_up_wording():
    p = email_person(phones=[PHONE])
    subject, body = outbox.compose(p, broker(), [], None, RequestKind.FOLLOW_UP)
    assert subject.startswith("Follow-up: ") and EMAIL in body
    assert PHONE not in body and "reminder" in body


def test_letter_refuses_without_permission():
    p = phone_person(permissions=Permissions())
    with pytest.raises(ValueError, match="permission"):
        outbox.compose(p, broker(), [], None)


# ------------------------------------------------------------------ runner


def test_dry_run_skips_brokers_a_value_removal_does_not_use(store):
    from freemyid.engine.runner import run
    p = phone_person(mailbox=MB)
    store.save_profile(p)
    reg = _dev.fixture_registry()
    with _dev.fixture_server():
        run(store, reg, [p], scan_only=False, dry_run=True, interactive=False,
            notifier=SimpleNamespace(notify=lambda *a, **k: None))
    touched = {e.broker_id for e in store.events(p.id) if e.broker_id}
    assert "devmail" in touched                    # the email route still gets a letter
    assert any(e.action == "email_drafted" for e in store.events(p.id, "devmail"))
    for b in reg.brokers:
        if not tiers.value_applicable(b, p, reg):
            assert b.id not in touched, b.id
    assert all(t.kind.value != "automatic" for t in store.list_todos(p.id))


def test_lookup_hit_review_todo_asks_about_the_number(store):
    from freemyid.engine.runner import review_todo
    from freemyid.models import TodoKind
    p = phone_person()
    store.save_profile(p)
    review_todo(store, p, broker(), _listing(p), 1)
    t = next(t for t in store.list_todos(p.id) if t.kind == TodoKind.REVIEW_MATCH)
    assert t.title == "Is this T's phone number? (Dev Phone)"
    assert PHONE not in t.title and PHONE not in t.body


# ------------------------------------------------------------------ Assisted card


def _web_broker(**over):
    data = {"phone_search_url_pattern": "https://devphone.example/phone/{phone_digits}",
            "method": "web_form", "opt_out_email": None,
            "opt_out_url": "https://devphone.example/optout"}
    data.update(over)
    return broker(**data)


def test_value_copy_fields_hold_only_the_value_links_and_mailbox():
    from freemyid.submitters import base
    p = phone_person(mailbox=MB, name=make_profile().name)
    out = base.copy_fields(p, _web_broker(), [_listing(p)])
    assert out == {"Phone number": PHONE, "Listing link": "https://devphone.example/p/1",
                   "Email for removals": "removals@example.org"}
    assert base.copy_fields(phone_person(permissions=Permissions()), _web_broker(), []) == {}
    em = base.copy_fields(email_person(phones=[PHONE]), _web_broker(), [])
    assert em == {"Email address": EMAIL}


def test_value_only_web_form_site_gets_the_value_card():
    from freemyid.models import TodoKind
    from freemyid.submitters import assisted
    p = phone_person()
    t = assisted.todo_for(p, _web_broker(), [_listing(p)], None)
    assert t.kind is TodoKind.ASSISTED_OPT_OUT
    assert t.title == "Remove T's phone number from Dev Phone"
    assert "search for the phone number" in t.body and "not for a name" in t.body
    assert "Full name" not in t.copy_fields and t.copy_fields["Phone number"] == PHONE


def test_value_only_never_gets_a_postal_letter_or_phone_script():
    from freemyid.models import TodoKind
    from freemyid.submitters import assisted
    p = phone_person()
    post = _web_broker(method="postal", postal={"recipient": "Dev Phone Privacy",
                                                "lines": ["1 Main St", "Springfield IL"]})
    assert assisted.todo_for(p, post, [], None).kind is TodoKind.ASSISTED_OPT_OUT


def test_value_only_email_site_gets_the_value_letter_to_send():
    from freemyid.models import TodoKind
    from freemyid.submitters import assisted
    p = phone_person(name=make_profile().name)
    t = assisted.todo_for(p, broker(), [], None)
    assert t.kind is TodoKind.SEND_EMAIL_MANUALLY
    assert PHONE in t.copy_fields["Letter"] and "Testperson" not in t.copy_fields["Letter"]
