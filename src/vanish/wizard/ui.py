"""HTML rendering helpers. Plain server-side HTML, no external assets."""
from __future__ import annotations

from html import escape as _e
from typing import Any

from ..models import ListingState
from .draft import BASIS_LABELS, CONSENT_TEXT, CONSENT_VERSION, STEP_TITLES, STEPS, Draft

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


def visible_steps(d: Draft) -> list[str]:
    out = []
    for s in STEPS:
        if d.editing and s in ("consent", "sign"):
            continue
        if s == "mailbox_login" and d.skip_mailbox:
            continue
        out.append(s)
    return out


def steps_bar(cur: str, d: Draft) -> str:
    vs = visible_steps(d)
    n = vs.index(cur) + 1 if cur in vs else 0
    dots = "".join(f'<li class="{"cur" if s == cur else ("done" if vs.index(s) < n - 1 else "")}">'
                   f'<span class="sr">{esc(STEP_TITLES[s])}</span></li>' for s in vs)
    return (f'<p class="stepcount">Step {n} of {len(vs)}</p>'
            f'<ol class="dots" aria-label="Progress">{dots}</ol>')


_AREA_HINT = "Type one on each line. You can leave this empty."


def _screen_body(step: str, d: Draft) -> str:
    if step == "consent":
        radios = "".join(_radio("basis", v, t, d.basis) for v, t in BASIS_LABELS.items())
        return (radios + '<div class="note">If you are helping an adult, you need their '
                'signed permission. <a href="/wizard/authorization-form" target="_blank">'
                'Open the form to print</a>. You will attach it on the next screen.</div>')
    if step == "sign":
        paras = "".join(f"<p>{esc(t)}</p>" for t in CONSENT_TEXT)
        up = ""
        if d.basis == "authorized_agent":
            up = ('<label for="authorization">Photo or scan of the signed form</label>'
                  '<input id="authorization" name="authorization" type="file" '
                  'accept="image/*,application/pdf"><p class="hint">You can also add it later. '
                  'Vanish will not start until it is attached.</p>')
        return (paras + up + _inp("attested_by", "Type your full name here to sign",
                                  d.attested_by, req=True)
                + _check("ack", "I have read this and I agree.", d.consent_ack)
                + f'<p class="hint">Wording version {esc(CONSENT_VERSION)}</p>')
    if step == "names":
        return (_inp("first", "First name", d.first, req=True)
                + _inp("last", "Last name", d.last, req=True)
                + _inp("label", "What should we call them on screen?", d.label,
                       hint="For example: Mom. Only shown on this computer."))
    if step == "othernames":
        return (_inp("middle", "Middle name", d.middle) + _inp("suffix", "Jr., Sr., III", d.suffix)
                + _area("nicknames", "Nicknames", d.nicknames, "Like Bill for William.")
                + _area("previous_names", "Maiden or earlier names", d.previous_names,
                        "Full names, one per line. Leave empty if none."))
    if step in ("addresses", "moreaddr"):
        rows = list(d.addresses) + [{}] * 4
        idx = [0] if step == "addresses" else [1, 2, 3]
        intro = ('<p>A city and state is enough.</p>' if step == "addresses" else
                 '<p>Websites often show old addresses too. Add up to three. '
                 'You can leave this empty.</p>')
        out = intro
        for i in idx:
            a = rows[i]
            out += ('<div class="row">' + _inp(f"city{i}", "City", a.get("city", ""),
                                               req=step == "addresses")
                    + _inp(f"state{i}", "State (2 letters, like IL)", a.get("state", ""),
                           req=step == "addresses", extra='maxlength="2" size="3"') + "</div>")
        return out
    if step == "birth":
        return ('<div class="note">This is only used to tell the right person apart from '
                'people with the same name. It is never sent to a website.</div>'
                + _inp("dob", "Date of birth", d.dob, typ="date")
                + _inp("age", "Or just their age", d.age, typ="number"))
    if step in ("phones", "emails", "relatives"):
        what = {"phones": ("phones", "Phone numbers", d.phones),
                "emails": ("emails", "Email addresses", d.emails),
                "relatives": ("relatives", "Relatives (full names)", d.relatives)}[step]
        extra = ("Websites often list relatives; this helps tell people with the same name "
                 "apart. " if step == "relatives" else "")
        return ('<div class="note">Only used for recognising the right person. Never sent to '
                'a website.</div>' + _area(what[0], what[1], what[2], extra + _AREA_HINT))
    if step == "permissions":
        return ('<p>Everything here is <b>off</b> unless you tick it. If a website asks for '
                'something you did not allow, Vanish stops and asks you. Vanish never pays '
                'for anything.</p>'
                + _check("allow_id_upload", "Vanish may upload a copy of an ID if a website "
                         "requires it", d.allow_id_upload)
                + _check("allow_account_creation", "Vanish may create an account on a website "
                         "if required", d.allow_account_creation)
                + _check("allow_phone_disclosure", "Vanish may give a phone number if "
                         "required", d.allow_phone_disclosure))
    if step == "mailbox":
        opts = (("gmail", "Gmail"), ("outlook", "Outlook or Hotmail"),
                ("proton_bridge", "Proton Mail"), ("other", "Other"))
        radios = "".join(_radio("provider", k, n, d.provider) for k, n in opts)
        return ('<p>Vanish asks websites to reply to a separate email address, so your '
                'everyday inbox stays private. A free new Gmail address works well. Which '
                'service is it with?</p>' + radios
                + _check("skip_mailbox", "I will do this later (some websites will wait)",
                         d.skip_mailbox))
    if step == "mailbox_login":
        return _mailbox_login_body(d)
    if step == "email":
        return ('<p>When Vanish needs to email a website to remove information, who decides?'
                '</p>' + _radio("email_mode", "approve_each", "Ask me before every email "
                                "(recommended)", d.email_mode)
                + _radio("email_mode", "auto", "Send ordinary removal emails by itself. "
                         "Legal letters will still ask me.", d.email_mode))
    if step == "schedule":
        return ('<p>Information often comes back. Vanish can look again once a week.</p>'
                + _check("weekly_recheck", "Check for me every week", d.weekly_recheck,
                         "This adds a small Vanish task to Windows (Task Scheduler) so it "
                         "can run even when this window is closed. If the computer was off, "
                         "it runs the next time it is on. You can turn it off in Settings.")
                + '<p class="hint">Leave it unticked and nothing is added to your computer.</p>')
    if step == "browser":
        return ('<div id="browser-box" data-status-url="/browser/status" '
                'data-install-url="/browser/install"><p id="browser-msg">Checking...</p>'
                '<div class="bar" hidden><div class="fill" id="browser-fill"></div></div>'
                '<div class="actions"><button type="button" id="browser-btn" hidden>'
                'Download it now</button></div></div>')
    return ""


def _mailbox_login_body(d: Draft) -> str:
    mb = d.mailbox or {}
    prov = d.provider
    guides = {
        "gmail": ("Make a password just for Vanish",
                  ["Open myaccount.google.com and sign in to the Gmail address you chose.",
                   "Click Security, then turn on 2-Step Verification if it is not on.",
                   "In the search box at the top, type App passwords and open it.",
                   "Name it Vanish and click Create.",
                   "Google shows 16 letters. Copy them and paste them below. (Not your "
                   "normal Gmail password.)"]),
        "proton_bridge": ("Use Proton Mail Bridge",
                          ["Install and open the free Proton Mail Bridge app on this computer "
                           "and sign in.",
                           "Bridge shows a username and a password just for programs. Copy "
                           "them below."]),
        "other": ("Use an app password if your email has one",
                  ["Ask your email provider for an app password or program password.",
                   "Your provider's help page lists its mail server names. Fill them in below."]),
    }
    title, steps = guides.get(prov, guides["other"])
    helplist = "".join(f"<li>{esc(x)}</li>" for x in steps)
    pw_hint = "Leave empty to keep the saved one." if d.editing else ""
    out = (f'<input type="hidden" name="provider" value="{esc(prov)}">'
           f'<div class="note"><b>{esc(title)}</b><ol>{helplist}</ol></div>'
           + _inp("address", "Email address", mb.get("address", ""), typ="email", req=True)
           + _inp("password", "Password", "", typ="password", hint=pw_hint))
    if prov == "proton_bridge":
        out += _inp("username", "Bridge username", mb.get("username", ""))
    if prov == "other":
        out += ('<div class="row">' + _inp("imap_host", "Incoming mail server",
                                           mb.get("imap_host", ""))
                + _inp("imap_port", "Port", mb.get("imap_port", 993), typ="number")
                + '</div><div class="row">'
                + _inp("smtp_host", "Outgoing mail server", mb.get("smtp_host", ""))
                + _inp("smtp_port", "Port", mb.get("smtp_port", 465), typ="number") + "</div>"
                + _check("imap_ssl", "Incoming is secure (SSL)", mb.get("imap_ssl", True))
                + _check("smtp_starttls", "Outgoing uses STARTTLS", mb.get("smtp_starttls", False)))
    out += ('<div class="actions"><button type="button" class="secondary" id="test-conn">'
            'Test that it works</button></div><div id="test-result" role="status"></div>'
            '<p class="hint">The test only talks to your email company. The password is kept '
            "in Windows' protected store, not in Vanish's files.</p>")
    return out


def step_page(step: str, d: Draft, csrf: str, errs: list[str], summary: str = "") -> str:
    body = summary if step == "review" else _screen_body(step, d)
    multipart = ' enctype="multipart/form-data"' if step == "sign" else ""
    vs = visible_steps(d)
    i = vs.index(step) if step in vs else 0
    back = (f'<a class="btn secondary big" href="/wizard/{vs[i - 1]}">Back</a>' if i > 0 else "")
    nxt = "Save and finish" if step == "review" else "Next"
    return layout(STEP_TITLES[step],
                  f'{steps_bar(step, d)}<h1>{esc(STEP_TITLES[step])}</h1>{errors_html(errs)}'
                  f'<form method="post" action="/wizard/{step}"{multipart} class="card" '
                  f'autocomplete="off">{csrf_field(csrf)}{body}'
                  f'<div class="actions">{back}<button class="big" type="submit">{nxt}</button>'
                  f'</div></form><p class="hint">{esc(HONESTY)}</p>')


def next_page(label: str, sched_on: bool, mailbox: bool, email_mode: str) -> str:
    items = [f"Vanish has saved the details for {esc(label)} on this computer only.",
             "Next, do a practice run. It looks for listings but sends nothing.",
             "Anything that needs a person (like a puzzle on a website) appears on the "
             "main page under Needs you."]
    items.append("Check for me every week is ON." if sched_on else
                 "Weekly checking is off. You can turn it on in Settings.")
    if email_mode == "approve_each":
        items.append("Before any email goes out, you will see it and press Approve.")
    if not mailbox:
        items.append("Your removal email is not set up yet; some websites will wait for it.")
    lis = "".join(f"<li>{x}</li>" for x in items)
    return layout("What happens next", f'<h1>What happens next</h1><div class="card"><ol class='
                  f'"big-list">{lis}</ol><p class="hint">{esc(HONESTY)}</p><div class="actions">'
                  '<a class="btn big" href="/">Go to my main page</a></div></div>')


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

