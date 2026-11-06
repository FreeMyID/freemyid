"""HTML rendering helpers. Plain server-side HTML, no external assets."""
from __future__ import annotations

import json
from html import escape as _e
from typing import Any

from ..models import ListingState
from .draft import BASIS_LABELS, CONSENT_TEXT, CONSENT_VERSION, PRESETS, STEP_TITLES, STEPS, Draft

HONESTY = ("Please know: some brokers need a manual step from you, listings can reappear "
           "later, and \"removed\" only means removed from that one broker, not from the "
           "whole internet. Vanish keeps checking so you do not have to.")

CHIP_LABEL = {
    ListingState.UNKNOWN: "not checked yet", ListingState.NOT_FOUND: "not found",
    ListingState.FOUND: "found", ListingState.SUBMITTED: "submitted",
    ListingState.AWAITING_VERIFICATION: "pending verification",
    ListingState.CONFIRMED: "broker confirmed", ListingState.REMOVED: "removed",
    ListingState.REAPPEARED: "reappeared", ListingState.NEEDS_HUMAN: "needs you",
    ListingState.ERROR: "error",
}
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def esc(v: Any) -> str:
    return _e(str(v if v is not None else ""), quote=True)


def chip(state: ListingState) -> str:
    return f'<span class="chip {esc(state.value)}">{esc(CHIP_LABEL.get(state, state.value))}</span>'


def layout(title: str, body: str, nav: bool = True) -> str:
    links = ""
    if nav:
        links = ('<a href="/">Dashboard</a><a href="/outbox">Emails to approve</a>'
                 '<a href="/wizard/consent?new=1">Add a person</a>'
                 '<a href="/settings">Background checks</a>')
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)} - Vanish</title><link rel="stylesheet" href="/static/style.css">'
            f'</head><body><header><a class="brand" href="/">Vanish</a>{links}</header>'
            f'<main>{body}</main><script src="/static/app.js"></script></body></html>')


def csrf_field(csrf: str) -> str:
    return f'<input type="hidden" name="csrf" value="{esc(csrf)}">'


def errors_html(errs: list[str]) -> str:
    return "".join(f'<div class="error" role="alert">{esc(x)}</div>' for x in errs)


def _inp(name: str, label: str, value: Any = "", typ: str = "text", hint: str = "",
         req: bool = False, extra: str = "") -> str:
    h = f'<span class="hint"> {esc(hint)}</span>' if hint else ""
    r = " required" if req else ""
    return (f'<label for="{name}">{esc(label)}{h}</label>'
            f'<input id="{name}" name="{name}" type="{typ}" value="{esc(value)}"{r} {extra}>')


def _area(name: str, label: str, lines: list[str], hint: str = "") -> str:
    h = f'<span class="hint"> {esc(hint)}</span>' if hint else ""
    return (f'<label for="{name}">{esc(label)}{h}</label>'
            f'<textarea id="{name}" name="{name}" rows="3">{esc(chr(10).join(lines))}</textarea>')


def _check(name: str, text: str, on: bool, hint: str = "") -> str:
    h = f'<div class="hint">{esc(hint)}</div>' if hint else ""
    return (f'<label class="check"><input type="checkbox" name="{name}" value="1"'
            f'{" checked" if on else ""}><span>{esc(text)}{h}</span></label>')


def steps_bar(cur: str, editing: bool) -> str:
    items = [s for s in STEPS if not (editing and s == "consent")]
    li = "".join(f'<li class="{"cur" if s == cur else ""}">{esc(STEP_TITLES[s])}</li>'
                 for s in items)
    return f'<ol class="steps" aria-label="Setup steps">{li}</ol>'


def step_page(step: str, d: Draft, csrf: str, errs: list[str], summary: str = "") -> str:
    body = ""
    multipart = ' enctype="multipart/form-data"' if step == "consent" else ""
    if step == "consent":
        body = _consent_body(d)
    elif step == "names":
        body = (_inp("label", "What should we call this person on screen?", d.label,
                     hint="For example: Mom. Only shown on this computer.")
                + '<div class="row">' + _inp("first", "First name", d.first, req=True)
                + _inp("middle", "Middle name", d.middle)
                + _inp("last", "Last name", d.last, req=True)
                + _inp("suffix", "Suffix", d.suffix, hint="Jr., III") + "</div>"
                + _area("nicknames", "Nicknames", d.nicknames, "One per line, like Bill for William.")
                + _area("previous_names", "Previous or maiden names", d.previous_names,
                        "One full name per line, like Jane Q Smith."))
    elif step == "addresses":
        body = ('<p>City and state are enough. Add places this person has lived; brokers often '
                'list older addresses too. You can add up to four here.</p>')
        rows = list(d.addresses) + [{}] * 4
        for i in range(4):
            a = rows[i]
            body += (f'<div class="card"><h2>Address {i + 1}</h2><div class="row">'
                     + _inp(f"city{i}", "City", a.get("city", ""))
                     + _inp(f"state{i}", "State (2 letters)", a.get("state", ""),
                            extra='maxlength="2" size="3"')
                     + "</div><div class=\"row\">"
                     + _inp(f"street{i}", "Street (optional)", a.get("street", ""))
                     + _inp(f"zip{i}", "ZIP (optional)", a.get("zip", "")) + "</div>"
                     + f'<label class="check"><input type="radio" name="current" value="{i}"'
                     f'{" checked" if a.get("current") else ""}><span>This is the current '
                     'address</span></label></div>')
    elif step == "details":
        body = ('<div class="note">Everything on this page is used <b>only to recognise the '
                'right person</b> in search results. It is never sent to a broker.</div>'
                + '<div class="row">'
                + _inp("dob", "Date of birth", d.dob, typ="date", hint="or enter an age instead")
                + _inp("age", "Age", d.age, typ="number") + "</div>"
                + _area("phones", "Phone numbers", d.phones, "One per line.")
                + _area("emails", "Personal email addresses", d.emails, "One per line.")
                + _area("relatives", "Relatives", d.relatives,
                        "One full name per line. Brokers often list relatives, which helps "
                        "tell people with the same name apart."))
    elif step == "permissions":
        body = ('<p>All of these are <b>off</b> unless you turn them on. If a broker asks for '
                'something you have not allowed, Vanish stops and puts it on your to-do list '
                'instead. Vanish never pays for anything.</p>'
                + _check("allow_id_upload", "Allow uploading a copy of an ID when a broker "
                         "requires one", d.allow_id_upload,
                         "Some brokers ask for a photo ID. Leave this off unless you are "
                         "comfortable with it.")
                + _check("allow_account_creation", "Allow creating an account on a broker's "
                         "site if it is required", d.allow_account_creation)
                + _check("allow_phone_disclosure", "Allow giving a phone number to a broker "
                         "if it is required", d.allow_phone_disclosure))
    elif step == "mailbox":
        body = _mailbox_body(d)
    elif step == "email":
        body = ('<p>When Vanish emails a broker, who decides?</p>'
                + _radio("email_mode", "approve_each", "Ask me before each email is sent "
                         "(recommended)", d.email_mode)
                + _radio("email_mode", "auto", "Send routine removal emails automatically. "
                         "Legal demand letters will still ask me first.", d.email_mode))
    elif step == "schedule":
        days = "".join(f'<option value="{i}"{" selected" if i == d.weekday else ""}>{n}</option>'
                       for i, n in enumerate(WEEKDAYS))
        hours = "".join(f'<option value="{h}"{" selected" if h == d.hour else ""}>'
                        f'{h:02d}:00</option>' for h in range(24))
        body = ('<p>Listings come back. Vanish re-checks in the background, only on brokers '
                'that are due.</p>'
                + _check("weekly_recheck", "Re-check regularly", d.weekly_recheck)
                + '<div class="row"><div><label for="weekday">Preferred day</label>'
                f'<select id="weekday" name="weekday">{days}</select></div>'
                f'<div><label for="hour">Preferred time</label><select id="hour" name="hour">'
                f'{hours}</select></div></div><p class="hint">If the computer is off or asleep, '
                'checks run when it wakes up. Install the background job from the '
                '"Background checks" page after saving.</p>')
    elif step == "review":
        body = summary
    return layout(STEP_TITLES[step], _form_shell(step, d, csrf, errs, body, multipart))


def _radio(name: str, value: str, text: str, cur: str) -> str:
    return (f'<label class="check"><input type="radio" name="{name}" value="{esc(value)}"'
            f'{" checked" if cur == value else ""}><span>{esc(text)}</span></label>')


def _form_shell(step: str, d: Draft, csrf: str, errs: list[str], body: str, multipart: str) -> str:
    idx = STEPS.index(step)
    back = (f'<a class="btn secondary" href="/wizard/{STEPS[idx - 1]}">Back</a>'
            if idx > 0 and not (d.editing and STEPS[idx - 1] == "consent") else "")
    nxt = "Save" if step == "review" else "Next"
    test_btn = ""
    return (f'{steps_bar(step, d.editing)}<h1>{esc(STEP_TITLES[step])}</h1>{errors_html(errs)}'
            f'<form method="post" action="/wizard/{step}"{multipart} class="card" '
            f'autocomplete="off">{csrf_field(csrf)}{body}{test_btn}'
            f'<div class="actions">{back}<button type="submit">{nxt}</button></div></form>'
            f'<p class="hint">{esc(HONESTY)}</p>')


def _consent_body(d: Draft) -> str:
    paras = "".join(f"<p>{esc(t)}</p>" for t in CONSENT_TEXT)
    radios = "".join(_radio("basis", v, t, d.basis) for v, t in BASIS_LABELS.items())
    return (f'<p class="hint">Consent text version {esc(CONSENT_VERSION)}</p>{paras}'
            f'<h2>Who is giving permission?</h2>{radios}'
            '<div class="note">If you are helping an adult, you need their signed permission. '
            '<a href="/wizard/authorization-form" target="_blank">Open the printable '
            'authorization form</a>, have them sign it, then attach a scan or photo below '
            '(you can also attach it later from the person\'s page). Vanish will not run '
            'for them until it is attached.</div>'
            '<label for="authorization">Signed authorization (only for the helper option)</label>'
            '<input id="authorization" name="authorization" type="file" '
            'accept="image/*,application/pdf">'
            + _inp("attested_by", "Type your full name to sign", d.attested_by, req=True)
            + _check("ack", "I have read this and I agree.", d.consent_ack))


def _mailbox_body(d: Draft) -> str:
    mb = d.mailbox or {}
    cur = mb.get("provider", "gmail")
    helps = {
        "gmail": "Use a dedicated Gmail address and an app password (Google account, "
                 "Security, 2-Step Verification, App passwords). Not your normal password.",
        "proton_bridge": "Requires the Proton Mail Bridge app running on this computer. Use "
                         "the Bridge username and password shown inside Bridge.",
        "other": "Enter your mail provider's server names below.",
    }
    pj = json.dumps({k: {"help": helps[k]} for k in PRESETS}).replace("<", "\\u003c")
    opts = "".join(f'<option value="{k}"{" selected" if k == cur else ""}>{n}</option>' for k, n in
                   (("gmail", "Gmail (app password)"), ("proton_bridge", "Proton Mail (Bridge)"),
                    ("other", "Other provider (e.g. Fastmail app password)")))
    pw_hint = "Leave blank to keep the saved one." if d.editing else ""
    return (f'<script type="application/json" id="presets">{pj}</script>'
            '<div class="note">Outlook / Hotmail: not supported yet (Microsoft requires '
            'OAuth sign-in). Use Gmail with an app password, Proton Bridge, or another '
            'provider.</div><p>Vanish uses its own email address for removal requests, so brokers never get '
            'your everyday inbox. Create a new free address just for this.</p>'
            f'<label for="provider">Mail provider</label><select id="provider" name="provider">'
            f'{opts}</select><p class="hint" id="provider-help"></p>'
            + _inp("address", "Removal mailbox address", mb.get("address", ""), typ="email")
            + _inp("username", "Username", mb.get("username", ""),
                   hint="Usually the same as the address; leave blank to use it.")
            + _inp("password", "Password or app password", "", typ="password", hint=pw_hint)
            + '<div id="custom-hosts" hidden><div class="row">'
            + _inp("imap_host", "Incoming (IMAP) server", mb.get("imap_host", ""))
            + _inp("imap_port", "Port", mb.get("imap_port", 993), typ="number")
            + '</div><div class="row">'
            + _inp("smtp_host", "Outgoing (SMTP) server", mb.get("smtp_host", ""))
            + _inp("smtp_port", "Port", mb.get("smtp_port", 465), typ="number") + "</div>"
            + _check("imap_ssl", "Incoming uses SSL", mb.get("imap_ssl", True))
            + _check("imap_starttls", "Incoming uses STARTTLS", mb.get("imap_starttls", False))
            + _check("smtp_starttls", "Outgoing uses STARTTLS", mb.get("smtp_starttls", False))
            + '</div><div class="actions"><button type="button" class="secondary" id="test-conn">'
            'Test connection</button></div><div id="test-result" role="status"></div>'
            '<p class="hint">The test connects only to the mail servers named above. The '
            'password is stored in this computer\'s keychain, never in Vanish\'s database.</p>'
            + _check("skip_mailbox", "Skip for now (email-based removals will wait)",
                     d.skip_mailbox))


def review_summary(d: Draft, warnings: list[str]) -> str:
    def li(k: str, v: str) -> str:
        return f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>"

    cur = next((a for a in d.addresses if a.get("current")), (d.addresses or [{}])[0])
    rows = [
        li("Called", d.label), li("Name", " ".join(x for x in (d.first, d.middle, d.last) if x)),
        li("Permission given by", f'{d.attested_by or "(kept)"} ({d.basis})'),
        li("Current location", f'{cur.get("city", "")}, {cur.get("state", "")}'),
        li("Addresses", str(len(d.addresses))),
        li("Phones / emails / relatives",
           f"{len(d.phones)} / {len(d.emails)} / {len(d.relatives)} (used only for matching)"),
        li("May upload ID", "yes" if d.allow_id_upload else "no"),
        li("May create accounts", "yes" if d.allow_account_creation else "no"),
        li("May give a phone number", "yes" if d.allow_phone_disclosure else "no"),
        li("Removal mailbox", "skipped" if d.skip_mailbox or not d.mailbox
           else d.mailbox.get("address", "")),
        li("Emails", "ask me each time" if d.email_mode == "approve_each" else "automatic"),
        li("Re-check", f"{WEEKDAYS[d.weekday]} {d.hour:02d}:00" if d.weekly_recheck else "off"),
    ]
    warn = "".join(f'<div class="note">{esc(w)}</div>' for w in warnings)
    return (f'{warn}<table>{"".join(rows)}</table>'
            '<p>Real removal requests are not sent until you also run a practice (dry) run '
            'and switch on submissions in the app settings.</p>')


def authorization_form(person: str, agent: str) -> str:
    p, a = esc(person) or "______________________", esc(agent) or "______________________"
    return layout("Authorization form", (
        '<div class="printable"><h1>Authorization to act on my behalf</h1>'
        f'<p>I, <b>{p}</b>, authorize <b>{a}</b> to act as my agent in asking data brokers and '
        'people-search websites to find, delete, and stop selling my personal information, '
        'including making requests under applicable state privacy laws, using the '
        'Vanish software on their computer.</p>'
        '<p>This permission covers opt-out and deletion requests only. It does not authorize '
        'any payment, and I may withdraw it at any time by telling my agent in writing.</p>'
        '<p>Signature: ______________________________ Date: ________________</p>'
        f'<p>Printed name: {p}</p><p>Agent signature: ____________________________</p>'
        '<p class="noprint"><button data-print="1">Print this page</button></p>'
        '</div>'), nav=False)

