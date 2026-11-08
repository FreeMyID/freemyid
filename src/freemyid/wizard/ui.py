"""HTML rendering helpers. Plain server-side HTML, no external assets."""
from __future__ import annotations

import re
from html import escape as _e
from typing import Any

from ..models import ListingState
from .draft import (
    BASIS_LABELS,
    CONSENT_TEXT,
    CONSENT_VERSION,
    STEP_TITLES,
    STEPS,
    Draft,
    birth_year_of,
)

HONESTY = ("Good to know: a few sites need a step from you. Sites can put your details back "
           "up, which is why Free My ID keeps checking. When a site says it has deleted your "
           "details, that is true for that one site only. Free My ID works on people-search "
           "sites. It does not change anything on Facebook or Google.")

CHIP_LABEL = {
    ListingState.UNKNOWN: "not checked yet", ListingState.NOT_FOUND: "not found",
    ListingState.FOUND: "your details are listed", ListingState.SUBMITTED: "asked",
    ListingState.AWAITING_VERIFICATION: "waiting for the site to reply",
    ListingState.CONFIRMED: "site confirmed", ListingState.REMOVED: "not listed now",
    ListingState.REAPPEARED: "reappeared", ListingState.NEEDS_HUMAN: "needs you",
    ListingState.ERROR: "error",
}
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def esc(v: Any) -> str:
    return _e(str(v if v is not None else ""), quote=True)


def chip(state: ListingState) -> str:
    return f'<span class="chip {esc(state.value)}">{esc(CHIP_LABEL.get(state, state.value))}</span>'


NAV = (("/", "Today"), ("/protect", "Protect yourself"), ("/outbox", "Emails"),
       ("/settings", "Settings"))


def layout(title: str, body: str, nav: bool = True, refresh: int = 0, current: str = "") -> str:
    """`current` is the nav path of this page (marks it for screen readers and sighted users)."""
    links = ""
    if nav:
        cur = ' aria-current="page"'
        links = "".join(
            f'<a href="{href}"{cur if href == current else ""}>{label}</a>'
            for href, label in NAV)
        links = f'<nav aria-label="Main">{links}</nav>'
    toggle = ('<button type="button" class="theme secondary" id="theme-toggle" hidden '
              'aria-pressed="false"><span class="ico" aria-hidden="true"></span> '
              '<span id="theme-label">Dark</span></button>') if nav else ""
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="color-scheme" content="light dark">'
            + (f'<meta http-equiv="refresh" content="{int(refresh)}">' if refresh else "")
            + f'<title>{esc(title)} - Free My ID</title>'
            '<link rel="stylesheet" href="/static/tokens.css">'
            '<link rel="stylesheet" href="/static/style.css">'
            '<script src="/static/theme.js"></script>'
            '</head><body><a class="skip" href="#main">Skip to the page</a>'
            '<header class="top"><a class="brand" href="/">'
            '<img src="/static/freemyid.png" alt="" width="30" height="30">Free My ID</a>'
            f'{links}{toggle}</header>'
            f'<main id="main" tabindex="-1">{body}</main><script src="/static/app.js"></script>'
            '</body></html>')


def error_page(heading: str, lines: list[str]) -> str:
    """Calm, plain-English page for a refused request (shown with its 403 status)."""
    paras = "".join(f"<p>{esc(x)}</p>" for x in lines)
    return layout("Please try again", (
        f'<div class="card"><h1>{esc(heading)}</h1>{paras}'
        '<p>Nothing was changed and nothing was sent.</p><div class="actions">'
        '<a class="btn primary" href="/" data-back="1">Go back and try again</a></div></div>'),
        nav=False)


def csrf_field(csrf: str) -> str:
    return f'<input type="hidden" name="csrf" value="{esc(csrf)}">'


def errors_html(errs: list[str], prefix: str = "err") -> str:
    return "".join(f'<div class="error" role="alert" id="{prefix}-{i}">{esc(x)}</div>'
                   for i, x in enumerate(errs))


# Which form fields each server-side error message belongs to (SEC-98). Messages are plain
# strings from draft.py, so match on their wording. Radios are left out on purpose.
_FIELD_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("type your full name", ("attested_by",)),
    ("tick the box", ("ack",)),
    ("file is too large", ("authorization",)),
    ("First and last name", ("first", "last")),
    ("a first and last name for", ("previous_names",)),
    ("Birth year", ("birth_year",)),
    ("under 18", ("birth_year",)),
    ("Ports must", ("imap_port", "smtp_port")),
    ("unprotected", ("imap_ssl", "imap_starttls")),
    ("mailbox's email address", ("address",)),
    ("valid mail server", ("imap_host", "smtp_host")),
    ("app password", ("password",)),
)


def error_fields(step: str, errs: list[str]) -> dict[str, list[int]]:
    """Map field name -> indexes of the errors that concern it."""
    out: dict[str, list[int]] = {}
    for i, msg in enumerate(errs):
        names: tuple[str, ...] = ()
        m = re.search(r"for address (\d)\.", msg)
        if m:
            n = int(m.group(1)) - 1
            names = (f"city{n}", f"state{n}")
        elif step == "address" and "at least one city" in msg:
            names = ("city0", "state0")
        else:
            for needle, fields in _FIELD_HINTS:
                if needle in msg:
                    names = fields
                    break
        for n in names:
            out.setdefault(n, []).append(i)
    return out


def mark_invalid(body: str, step: str, errs: list[str], prefix: str = "err") -> str:
    """Give each rejected input aria-invalid and aria-describedby (keeping existing ids)."""
    for name, idxs in error_fields(step, errs).items():
        ids = " ".join(f"{prefix}-{i}" for i in idxs)
        pat = re.compile(r'<(input|textarea)\b[^>]*?\b(?:id|name)="' + re.escape(name) + r'"[^>]*>')

        def fix(m: re.Match[str], ids: str = ids) -> str:
            tag = m.group(0)
            if "aria-invalid" in tag:
                return tag
            d = re.search(r'\baria-describedby="([^"]*)"', tag)
            if d:
                tag = tag.replace(d.group(0), f'aria-describedby="{d.group(1)} {ids}"')
                extra = ' aria-invalid="true"'
            else:
                extra = f' aria-invalid="true" aria-describedby="{ids}"'
            return tag[:-1].rstrip("/").rstrip() + extra + ">"
        body = pat.sub(fix, body, count=1)
    return body


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
    if d.editing:       # editing skips consent and the mailbox (that lives in Settings)
        return [s for s in STEPS if s not in ("consent", "mailbox")]
    return list(STEPS)


def steps_bar(cur: str, d: Draft) -> str:
    vs = visible_steps(d)
    n = vs.index(cur) + 1 if cur in vs else 0
    dots = "".join(f'<li class="{"cur" if s == cur else ("done" if vs.index(s) < n - 1 else "")}">'
                   f'<span class="sr">{esc(STEP_TITLES[s])}</span></li>' for s in vs)
    return (f'<ol class="dots" aria-label="Progress">{dots}</ol>'
            f'<p class="stepcount">Step {n} of {len(vs)}</p>')


def _radio(name: str, value: str, label: str, current: str, hint: str = "") -> str:
    h = f'<span class="hint">{esc(hint)}</span>' if hint else ""
    return (f'<label class="check choice"><input type="radio" name="{name}" value="{esc(value)}"'
            f'{" checked" if value == current else ""}><span>{esc(label)}{h}</span></label>')


_AREA_HINT = "Separate with commas if there is more than one. You can leave this empty."

MAILBOX_CHOICES = (
    ("gmail", "Gmail", "A free Gmail address made just for Free My ID works best."),
    ("yahoo", "Yahoo Mail", ""),
    ("icloud", "iCloud Mail (Apple)", ""),
    ("proton_bridge", "Proton Mail (needs the Proton Bridge app)", ""),
    ("other", "Another email service", ""),
    ("outlook", "Outlook.com or Hotmail", "Not possible, see below."),
    ("skip", "Skip, I'll do these by hand", ("Free My ID prepares each message and opens your "
     "email for you. You press Send yourself.")),
)

# (title, steps) for each service. Plain words, one action per line.
MAILBOX_GUIDES: dict[str, tuple[str, list[str]]] = {
    "gmail": ("How to get a Gmail app password (about 3 minutes)", [
        ("Open a new browser tab and go to myaccount.google.com. Sign in to the Gmail "
        "address you made for Free My ID."),
        "Click Security on the left. Turn on 2-Step Verification if it is not already on.",
        "Click the search box at the top and type: App passwords. Open it.",
        "Type Free My ID as the name and click Create.",
        ("Google shows a box of 16 letters. Copy them, then paste them in the Password box "
        "below. This is not your usual Gmail password.")]),
    "yahoo": ("How to get a Yahoo app password (about 3 minutes)", [
        "Open a new browser tab and go to login.yahoo.com/account/security. Sign in.",
        "Find Generate app password (or App passwords) and click it.",
        "Type Free My ID as the app name and click Generate password.",
        ("Yahoo shows a password. Copy it and paste it in the Password box below. This is "
        "not your usual Yahoo password.")]),
    "icloud": ("How to get an Apple app-specific password (about 3 minutes)", [
        "Open a new browser tab and go to account.apple.com. Sign in.",
        "Click Sign-In and Security, then App-Specific Passwords.",
        "Click the plus button, type Free My ID, and click Create.",
        ("Apple shows a password like abcd-efgh-ijkl-mnop. Copy it and paste it in the "
        "Password box below.")]),
    "proton_bridge": ("Using Proton Mail", [
        ("Proton needs a free helper app called Proton Mail Bridge. Install it from "
        "proton.me/mail/bridge and sign in. It must be running when Free My ID checks mail."),
        "Bridge shows a username and a password just for programs. Copy them below."]),
    "other": ("Using another email service", [
        "Ask your email company for an app password (sometimes called a program password).",
        "Their help page lists the mail server names. Fill them in below."]),
    "outlook": ("Why Outlook.com does not work", [
        "Microsoft no longer lets programs like Free My ID sign in to Outlook.com and Hotmail.",
        ("Please choose Skip, I'll do these by hand, above. Free My ID will prepare each message "
        "and open Outlook for you. You press Send. Or choose another service.")]),
}


def _when(name: str, values: str) -> str:
    return f' data-when="{esc(name)}:{esc(values)}"'


def _screen_body(step: str, d: Draft) -> str:
    if step == "consent":
        radios = "".join(_radio("basis", v, t, d.basis) for v, t in BASIS_LABELS.items())
        paras = "".join(f"<p>{esc(t)}</p>" for t in CONSENT_TEXT)
        up = ('<div class="note"' + _when("basis", "authorized_agent") + '>If you are helping '
              'an adult, you need their signed permission. <a href="/wizard/authorization-form" '
              'target="_blank">Open the form to print</a>. Then attach a photo or scan of it '
              'here (or later, from their page).<label for="authorization">Photo or scan of the '
              'signed form</label><input id="authorization" name="authorization" type="file" '
              'accept="image/*,application/pdf"></div>')
        return ('<p class="lead"><b>That post didn\'t stop anyone. This does.</b><br>'
                'Take your name off the websites that sell it.</p>'
                '<p>Free My ID asks people-search sites (websites that publish names, '
                'addresses and phone numbers, also called data brokers) to delete your '
                'details, in the written form they have to answer. Then it keeps checking.</p>'
                '<div class="card soft trust"><p><b>No account. No cloud. Never asks for your '
                'Social Security number, bank or card details. Free and open source. '
                'Uninstall anytime.</b></p></div>'
                '<p class="hint">Free My ID works on people-search sites. It does not change '
                'what Facebook itself does with your account.</p>'
                '<details class="more"><summary>Read the full wording</summary>'
                '<div class="card soft">' + paras + '</div></details>'
                '<h2>Who is this for?</h2>' + radios + up
                + _inp("attested_by", "Type your full name to sign", d.attested_by,
                       req=True)
                + _check("ack", "I have read this and I agree.", d.consent_ack)
                + f'<p class="hint">Wording version {esc(CONSENT_VERSION)}. '
                '<a href="/wizard/import">I have a family setup file</a></p>')
    if step == "name":
        return (_inp("first", "First name", d.first, req=True)
                + _inp("middle", "Middle name (if any)", d.middle)
                + _inp("last", "Last name", d.last, req=True)
                + '<details class="more"><summary>Any other names? (nicknames, maiden name)'
                '</summary>'
                + _inp("suffix", "Jr., Sr., III", d.suffix)
                + _area("nicknames", "Nicknames", d.nicknames, "Like Bill for William.")
                + _area("previous_names", "Maiden or earlier names", d.previous_names,
                        "Full names, one per line. Leave empty if none.")
                + _inp("label", "What should we call them on screen?", d.label,
                       hint="For example: Mom. Only shown on this computer.")
                + "</details>")
    if step == "address":
        rows = list(d.addresses) + [{}] * 4

        def row(i: int, req: bool) -> str:
            a = rows[i]
            return ('<div class="row">' + _inp(f"city{i}", "City", a.get("city", ""), req=req)
                    + _inp(f"state{i}", "State (2 letters, like IL)", a.get("state", ""),
                           req=req, extra='maxlength="2" size="3"') + "</div>")
        return ('<p>A city and state is enough. People-search sites show the town, so that is what '
                'Free My ID looks for.</p>' + row(0, True)
                + '<details class="more"' + (" open" if any(rows[1:4]) else "")
                + '><summary>Have they lived anywhere else in the last 10 years?</summary>'
                '<p class="hint">Websites often show old addresses too. Add up to three.</p>'
                + row(1, False) + row(2, False) + row(3, False) + "</details>")
    if step == "about":
        return ('<div class="note">These details help Free My ID pick out the right listings. A site '
                'is only sent what its own listing already shows, plus the removal email address '
                'if you set one up. A birth year, relatives and personal email addresses are '
                'never sent.</div>'
                + _inp("birth_year", "Year of birth", birth_year_of(d), typ="number",
                       hint="Four digits, like 1952.", extra='min="1900" max="2100"')
                + _inp("phones", "Phone number", ", ".join(d.phones), hint=_AREA_HINT)
                + _inp("emails", "Email address they use", ", ".join(d.emails), hint=_AREA_HINT)
                + '<details class="more"><summary>Names of relatives (helps with common '
                'names)</summary>'
                + _area("relatives", "Relatives (full names)", d.relatives,
                        "Websites often list relatives. One per line. Leave empty if unsure.")
                + "</details>")
    if step == "mailbox":
        return _mailbox_body(d)
    if step == "finish":
        items = [("Right after you finish", ("Free My ID looks for the person on people-search "
                  "sites. This takes a few minutes. You can close the window.")),
                 ("Within a day", ("Where a site allows it, Free My ID sends the request asking it "
                  "to delete the details. Some emails wait for your OK first.")),
                 ("When a site needs a person", ("A card appears with one big button to help you. "
                  "Some sites need a few steps by hand. That is normal.")),
                 ("Over the next weeks", ("Sites reply or confirm at their own pace, often 2 to 6 "
                  "weeks. The dashboard shows each one as it changes.")),
                 ("After that", ("Details can reappear, so Free My ID keeps checking. "
                  "Removed means removed from that one site only."))]
        lis = "".join(f"<li><b>{esc(w)}:</b> {esc(x)}</li>" for w, x in items)
        auto = ("" if d.editing else _check(
            "weekly_recheck", "Yes, keep checking for me automatically", d.weekly_recheck,
            "This adds one small Free My ID task to Windows (Task Scheduler) that runs once a "
            "day, even when this window is closed. If the computer was off, it runs when "
            "it is next on. Quiet unless it needs you. You can turn it off in Settings."))
        from .. import config as cfgmod
        practice = ("" if d.editing or cfgmod.load().real_submissions_enabled else
                    '<div class="note"><b>Practice mode is on.</b> Free My ID will look for '
                    'listings but will not send anything to any site until you turn that on '
                    'in Settings.</div>')
        return (practice + f'<div class="card soft"><p><b>What happens next</b></p><ol class="big-list">'
                f'{lis}</ol></div>' + auto)
    return ""


def _mailbox_body(d: Draft) -> str:
    mb = d.mailbox or {}
    cur = ("skip" if d.skip_mailbox else d.provider) if d.mailbox_answered else ""
    radios = "".join(_radio("provider", k, n, cur, h) for k, n, h in MAILBOX_CHOICES)
    guides = ""
    for k, (title, steps) in MAILBOX_GUIDES.items():
        lis = "".join(f"<li>{esc(x)}</li>" for x in steps)
        guides += (f'<div class="note guide"{_when("provider", k)}><b>{esc(title)}</b>'
                   f'<ol class="big-list">{lis}</ol></div>')
    if d.saved_password:
        pw_hint = "A password is saved. Leave empty to keep it."
    elif d.password:   # typed in this session, held in memory only until you finish
        pw_hint = "Your password is ready but not saved yet. Leave empty to use it."
    else:
        pw_hint = "Paste the app password here."
    creds = (f'<div{_when("provider", "gmail,yahoo,icloud,proton_bridge,other")}>'
             + _inp("address", "Email address", mb.get("address", ""), typ="email")
             + _inp("password", "App password", "", typ="password", hint=pw_hint))
    creds += (f'<div{_when("provider", "proton_bridge")}>'
              + _inp("username", "Bridge username", mb.get("username", "")) + "</div>")
    creds += (f'<div{_when("provider", "other")}><div class="row">'
              + _inp("imap_host", "Incoming mail server", mb.get("imap_host", ""))
              + _inp("imap_port", "Port", mb.get("imap_port", 993), typ="number")
              + '</div><div class="row">'
              + _inp("smtp_host", "Outgoing mail server", mb.get("smtp_host", ""))
              + _inp("smtp_port", "Port", mb.get("smtp_port", 465), typ="number") + "</div>"
              + _check("imap_ssl", "Incoming is secure (SSL)", mb.get("imap_ssl", True))
              + _check("imap_starttls", "Incoming uses STARTTLS (only if SSL is off)",
                       mb.get("imap_starttls", False),
                       "At least one of these two must be on, or your password would be "
                       "sent unprotected. If unsure, leave SSL ticked.")
              + _check("smtp_starttls", "Outgoing uses STARTTLS", mb.get("smtp_starttls", False))
              + "</div>")
    creds += ('<div class="actions"><button type="button" class="secondary" id="test-conn">'
              'Test that it works</button></div><div id="test-result" role="status"></div>'
              '<div id="trust-box" class="note" hidden role="alertdialog" aria-live="polite">'
              '<p id="trust-text"></p><p class="code" id="trust-code"></p>'
              '<p id="trust-question"><b></b></p><div class="actions">'
              '<button type="button" class="big" id="trust-yes">Yes</button>'
              '<button type="button" class="big secondary" id="trust-no">No</button>'
              '</div></div>'
              '<p class="hint">The test only talks to your email company. The password is kept '
              "in your computer's protected store, not in Free My ID's files.</p></div>")
    return ('<p class="lead">Free My ID can use a separate email address to send '
            'deletion requests and click the confirmation links for you. Pick yours, or skip it.</p>'
            + radios + guides + creds)


def step_page(step: str, d: Draft, csrf: str, errs: list[str], summary: str = "") -> str:
    body = summary or _screen_body(step, d)
    if errs:
        body = mark_invalid(body, step, errs)
    multipart = ' enctype="multipart/form-data"' if step == "consent" else ""
    vs = visible_steps(d)
    i = vs.index(step) if step in vs else 0
    back = (f'<a class="btn secondary big" href="/wizard/{vs[i - 1]}">Back</a>' if i > 0 else "")
    last = step == "finish"
    honesty = f'<p class="hint">{esc(HONESTY)}</p>' if i == 0 else ""   # once, on the first screen
    nxt = ("Save changes" if d.editing else "Finish") if last else "Next"
    return layout(STEP_TITLES[step],
                  f'{steps_bar(step, d)}<h1>{esc(STEP_TITLES[step])}</h1>{errors_html(errs)}'
                  f'<form method="post" action="/wizard/{step}"{multipart} class="card" '
                  f'autocomplete="off">{csrf_field(csrf)}{body}'
                  f'<div class="actions">{back}<button class="big" type="submit">{nxt}</button>'
                  f'</div></form>{honesty}', nav=False)


def authorization_form(person: str, agent: str) -> str:
    p, a = esc(person) or "______________________", esc(agent) or "______________________"
    return layout("Authorization form", (
        '<div class="printable"><h1>Authorization to act on my behalf</h1>'
        f'<p>I, <b>{p}</b>, give <b>{a}</b> my permission to act for me. They may ask '
        'people-search websites (websites that publish names, addresses and phone numbers) and '
        'other companies that sell personal information to find, delete, and stop selling my '
        'personal information, including by making requests under state privacy laws, using the '
        'Free My ID software on their computer.</p>'
        '<p>This permission covers requests to delete or stop selling my information only. '
        'It does not allow any payment, and it does not allow changes to my accounts on '
        'Facebook, Google or any other service. I may withdraw it at any time by telling '
        'them in writing.</p>'
        '<p>Signature: ______________________________ Date: ________________</p>'
        f'<p>Printed name: {p}</p><p>Agent signature: ____________________________</p>'
        '<p class="noprint"><button data-print="1">Print this page</button></p>'
        '</div>'), nav=False)

