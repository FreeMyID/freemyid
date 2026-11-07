"""Dashboard page rendering (status, to-dos, outbox, evidence)."""
from __future__ import annotations

import re
from urllib.parse import quote

from ..models import (
    BrokerStatus,
    EvidenceKind,
    ListingState,
    Profile,
    Request,
    Todo,
    TodoKind,
)
from .ui import _check, chip, csrf_field, esc, layout

SUMMARY_ORDER = [ListingState.NEEDS_HUMAN, ListingState.FOUND, ListingState.REAPPEARED,
                 ListingState.AWAITING_VERIFICATION, ListingState.SUBMITTED,
                 ListingState.CONFIRMED, ListingState.REMOVED]


def _dt(d) -> str:
    return d.strftime("%Y-%m-%d") if d else "-"


DONE_STATES = (ListingState.REMOVED, ListingState.CONFIRMED)
WAITING_STATES = (ListingState.SUBMITTED, ListingState.AWAITING_VERIFICATION,
                  ListingState.FOUND, ListingState.REAPPEARED)
COMPOSE = {
    "gmail": ("Gmail", "https://mail.google.com/mail/?view=cm&fs=1&to={to}&su={su}&body={body}"),
    "outlook": ("Outlook", ("https://outlook.live.com/mail/0/deeplink/compose?to={to}"
                           "&subject={su}&body={body}")),
    "yahoo": ("Yahoo Mail", "https://compose.mail.yahoo.com/?to={to}&subject={su}&body={body}"),
}
CANT = "I couldn't"   # escaped by _post_btn
_MAX_COMPOSE_BODY = 1800   # long URLs get cut by some mail sites; Copy is the fallback


def compose_url(provider: str, to: str, subject: str, body: str) -> str | None:
    if provider not in COMPOSE:
        return None
    return COMPOSE[provider][1].format(to=quote(to, safe=""), su=quote(subject, safe=""),
                                       body=quote(body[:_MAX_COMPOSE_BODY], safe=""))


def email_parts(t: Todo) -> tuple[str, str, str]:
    """(to, subject, letter) of a SEND_EMAIL_MANUALLY todo. Keys in copy_fields: To, Subject."""
    low = {k.strip().lower(): v for k, v in t.copy_fields.items()}
    return low.get("to", ""), low.get("subject", ""), t.body


def open_url_of(t: Todo, index: int = 0) -> str | None:
    urls = [u for u in t.links if u.startswith("https://")]
    return urls[index] if 0 <= index < len(urls) else None


def status_sentence(statuses: list[BrokerStatus], n_todos: int, running: bool,
                    has_people: bool = True) -> tuple[str, bool]:
    """(sentence, all_good)."""
    if running:
        return "Free My ID is checking now. This page updates by itself.", True
    done = sum(1 for s in statuses if s.state in DONE_STATES)
    waiting = sum(1 for s in statuses if s.state in WAITING_STATES)
    if not statuses and not n_todos:
        return "Free My ID is set up. Nothing to do yet.", True
    if done == 0 and not any(s.state in (ListingState.SUBMITTED, ListingState.AWAITING_VERIFICATION,
                                         ListingState.REAPPEARED) for s in statuses):
        return ("Free My ID has made a list of sites to work through. Start with the first one "
                "below when you have a few minutes." if n_todos else
                "Free My ID has made a list of sites to work through. Nothing needs you yet.",
                n_todos == 0)
    sites = f"{done} site{'s have' if done != 1 else ' has'} confirmed or no longer list{'s' if done == 1 else ''} you"
    wait = f"{waiting} {'is' if waiting == 1 else 'are'} still waiting"
    if n_todos == 0:
        return f"Free My ID is working. {sites}, {wait}. Nothing needs you right now.", True
    return f"Free My ID is working. {sites}, {wait}, {n_todos} need{'s' if n_todos == 1 else ''} you.", False


def _steps_list(body: str) -> list[str]:
    out = []
    for ln in body.splitlines():
        ln = re.sub(r"^\s*(\d+[.)]|[-*])\s*", "", ln).strip()
        if ln:
            out.append(ln)
    return out


def _copy_rows(fields: dict[str, str]) -> str:
    return "".join(
        f'<div class="copyrow"><span class="lbl">{esc(k)}</span><span class="val">{esc(v)}</span>'
        f'<button type="button" class="secondary" data-copy="{esc(v)}">Copy</button></div>'
        for k, v in fields.items())


def _post_btn(action: str, csrf: str, label: str, cls: str = "", extra: str = "") -> str:
    return (f'<form method="post" action="{esc(action)}" class="inline">{csrf_field(csrf)}'
            f'{extra}<button type="submit" class="{cls}">{esc(label)}</button></form>')


def todo_card(t: Todo, who: str, bname: str, csrf: str, show_who: bool = False,
              fill: bool = False) -> str:
    tid = esc(t.id)
    head = (f'<h2>{esc(bname) or esc(t.title)}</h2>'
            + (f'<p class="hint">For {esc(who)}</p>' if show_who else ""))
    done = f"/todo/{tid}/done"
    couldnt = f"/todo/{tid}/couldnt"
    if t.kind == TodoKind.ASSISTED_OPT_OUT:
        steps = _steps_list(t.body)
        ol = ("<ol>" + "".join(f"<li>{esc(x)}</li>" for x in steps) + "</ol>") if steps else ""
        url = open_url_of(t)
        primary = (_post_btn(f"/todo/{tid}/open", csrf, "Open the site", "primary")
                   if url else "")
        if fill and t.broker_id:
            primary = (_post_btn(f"/todo/{tid}/fill", csrf, "Fill it in for me", "primary big")
                       + (_post_btn(f"/todo/{tid}/open", csrf, "Open the site myself",
                                    "secondary") if url else ""))
        copies = _copy_rows(t.copy_fields)
        if copies:
            copies = ("<p><b>Copy and paste these when the site asks:</b></p>" + copies)
        return (f'<div class="card todo" data-kind="assisted_opt_out">{head}'
                f'<p>{esc(t.title)}</p>{ol}{copies}<div class="actions">{primary}'
                f'{_post_btn(done, csrf, "I did it", "secondary")}'
                f'{_post_btn(couldnt, csrf, CANT, "secondary")}</div></div>')
    if t.kind == TodoKind.SEND_EMAIL_MANUALLY:
        letter = email_parts(t)[2]
        rest = dict(t.copy_fields)
        buttons = "".join(
            _post_btn(f"/todo/{tid}/compose/{k}", csrf, f"Open in {COMPOSE[k][0]}",
                      "primary" if k == "gmail" else "secondary") for k in COMPOSE)
        return (f'<div class="card todo" data-kind="send_email_manually">{head}'
                f'<p>{esc(t.title)}</p><p><b>This is the message. Send it from your own '
                f'email.</b></p>'
                f'<div class="letter" aria-label="Message preview">{esc(letter)}</div>'
                f'<div class="actions"><button type="button" class="secondary" '
                f'data-copy="{esc(letter)}">Copy the message</button></div>'
                f'{_copy_rows(rest)}<div class="actions">{buttons}</div>'
                f'<div class="actions">{_post_btn(done, csrf, "I sent it", "secondary")}'
                f'{_post_btn(couldnt, csrf, CANT, "secondary")}</div></div>')
    # everything else: one primary button
    url = open_url_of(t)
    opener = _post_btn(f"/todo/{tid}/open", csrf, "Open the page", "secondary") if url else ""
    if t.resume_token:
        primary = _post_btn(f"/todo/{tid}/resolve", csrf, "I finished it", "primary")
    else:
        primary = _post_btn(done, csrf, "Done", "primary")
    return (f'<div class="card todo" data-kind="{esc(t.kind.value)}">{head}<p>{esc(t.title)}</p>'
            f'<p class="hint">{esc(t.body)}</p><div class="actions">{opener}{primary}</div></div>')


def home_page(*, statuses: list[BrokerStatus], todos: list[tuple[Todo, str, str]],
              people: list[dict], outbox_count: int, csrf: str, flash: str = "",
              practice: bool = False, running: bool = False, fill: bool = False,
              filling: bool = False) -> str:
    """todos = (todo, person label, broker name)."""
    sentence, good = status_sentence(statuses, len(todos), running)
    body = (f'{_flash(flash)}<p class="status-line{" ok" if good else ""}" role="status">'
            f'{esc(sentence)}</p>')
    if practice:
        body += ('<div class="banner"><b>Practice mode.</b> Free My ID is looking but is not sending '
                 'anything yet. <a href="/settings">Change this in Settings</a> when you are '
                 'ready.</div>')
    for r in people:
        if r["consent_problem"]:
            body += (f'<div class="note">Not running yet for {esc(r["profile"].label)}: '
                     f'{esc(r["consent_problem"])} <a href="/profile/{esc(r["profile"].id)}">'
                     'Fix it</a></div>')
    if outbox_count:
        body += (f'<div class="card todo"><h2>{outbox_count} email(s) waiting for your OK</h2>'
                 '<p>Look at each one, then press Approve. Nothing is sent until you do.</p><div class="actions">'
                 '<a class="btn primary" href="/outbox">Look at them</a></div></div>')
    if filling:
        body += ('<div class="banner">A form is being filled in. <a href="/fill">'
                 'Go to that window</a></div>')
    multi = len({w for _, w, _ in todos}) > 1
    for t, who, bname in todos:
        body += todo_card(t, who, bname, csrf, multi, fill and not filling)
    if not todos and not outbox_count and not running:
        body += '<div class="card"><p>You have nothing to do right now. That is good.</p></div>'
    body += '<h2>More</h2><div class="card">'
    for r in people:
        p = r["profile"]
        body += (f'<p><a class="btn secondary" href="/profile/{esc(p.id)}">All the details for '
                 f'{esc(p.label)}</a></p>')
    body += ('<p class="hint">A site that says it deleted you has done that for that one site only. '
             'Details can reappear, which is why Free My ID keeps checking. Free My ID does '
             'not change anything on Facebook or Google.</p></div>')
    return layout("Home", body, refresh=6 if running else 0)


FILL_WAIT = ("A window opened. Free My ID filled in the form. Tick the \"I'm not a robot\" box "
             "and press Submit.")


def fill_page(state: str, tid: str, csrf: str, bname: str = "") -> str:
    """state: waiting | pressed (Submit seen but not confirmed) | none."""
    who = f" for {esc(bname)}" if bname else ""
    if state == "waiting":
        return layout("Filling in the form", (
            f'<div class="card"><h1>Your turn{who}</h1><p class="big">{esc(FILL_WAIT)}</p>'
            '<p>This page will update by itself when you are done. You can take your time. '
            'Free My ID never presses Submit for you.</p></div>'), refresh=3)
    if state == "pressed":
        return layout("Did it go through?", (
            f'<div class="card"><h1>Did it go through{who}?</h1>'
            '<p>Free My ID could not see a confirmation on the page. If you pressed Submit and the '
            'site thanked you, tell us here. Otherwise your to-do stays on the list.</p>'
            f'<div class="actions">{_post_btn(f"/todo/{esc(tid)}/done", csrf, "I did it", "primary")}'
            '<a class="btn secondary" href="/">Not yet</a></div></div>'))
    return layout("Fill it in", (
        '<div class="card"><h1>Nothing is being filled in</h1><div class="actions">'
        '<a class="btn primary" href="/">Back to home</a></div></div>'))


def fill_confirm_page(tid: str, csrf: str) -> str:
    return layout("Before we fill it in", (
        '<div class="card"><h1>This sends a real request to the site.</h1>'
        '<p class="big">You are in practice mode, but this step is different. Free My ID will '
        'open the site and fill in the form. When you press Submit on the site, your request '
        'is real.</p><p>We only ask this once. Free My ID never presses Submit for you.</p>'
        f'<form method="post" action="/todo/{esc(tid)}/fill" class="inline">{csrf_field(csrf)}'
        '<input type="hidden" name="confirm" value="yes"><div class="actions">'
        '<button type="submit" class="primary big">I understand, continue</button>'
        '<a class="btn secondary" href="/">Not now</a></div></form></div>'))


def _flash(msg: str) -> str:
    return f'<div class="note" role="status">{esc(msg)}</div>' if msg else ""


def profile_page(p: Profile, statuses: list[BrokerStatus], names: dict[str, str],
                 todos: list[Todo], evidence_by_broker: dict[str, list], csrf: str,
                 consent_problem: str, flash: str = "", fill: bool = False) -> str:
    body = f'<h1>{esc(p.label)}</h1>{_flash(flash)}'
    if consent_problem:
        body += f'<div class="note">Not running yet: {esc(consent_problem)}</div>'
        if "authorization" in consent_problem:
            body += (f'<form class="card" method="post" action="/profile/{esc(p.id)}/authorization"'
                     f' enctype="multipart/form-data">{csrf_field(csrf)}'
                     '<label for="authorization">Attach the signed authorization (photo or PDF)'
                     '</label><input id="authorization" name="authorization" type="file" '
                     'required><div class="actions"><button type="submit">Attach</button></div>'
                     '</form>')
    body += (f'<p><a class="btn secondary" href="/profile/{esc(p.id)}/edit">Edit details</a> '
             f'<a class="btn secondary" href="/profile/{esc(p.id)}/report">Download report</a></p>')
    # todos
    body += "<h2>Needs you</h2><div>"
    if not todos:
        body += "<p>Nothing right now.</p>"
    for t in todos:
        body += todo_card(t, p.label, names.get(t.broker_id or "", ""), csrf, fill=fill)
    body += "</div>"
    # per-broker table
    body += ('<div class="card"><h2>Sites</h2><table><tr><th>Site</th><th>State</th>'
             '<th>Updated</th><th>Next check</th></tr>')
    for st in sorted(statuses, key=lambda s: (names.get(s.broker_id, s.broker_id)).lower()):
        extra = (f'<br><span class="hint">{esc(st.needs_human_reason)}</span>'
                 if st.needs_human_reason else "")
        body += (f'<tr><td>{esc(names.get(st.broker_id, st.broker_id))}</td>'
                 f'<td>{chip(st.state)}{extra}</td><td>{_dt(st.updated_at)}</td>'
                 f'<td>{_dt(st.next_check_at)}</td></tr>')
    if not statuses:
        body += '<tr><td colspan="4">No sites checked yet.</td></tr>'
    body += "</table></div>"
    # evidence
    body += '<div class="card"><h2>Receipts</h2><p class="hint">Pictures of what each site showed and replied. ' \
            'Kept on this computer only, encrypted.</p>'
    any_ev = False
    for bid, evs in sorted(evidence_by_broker.items()):
        shots = [e for e in evs if e.kind == EvidenceKind.SCREENSHOT]
        others = [e for e in evs if e.kind != EvidenceKind.SCREENSHOT]
        any_ev = True
        body += f'<h3>{esc(names.get(bid, bid))}</h3><div class="gallery">'
        for e in shots:
            body += (f'<figure><a href="/evidence/{esc(p.id)}/{esc(e.id)}" target="_blank">'
                     f'<img loading="lazy" alt="{esc(e.caption or "screenshot")}" '
                     f'src="/evidence/{esc(p.id)}/{esc(e.id)}"></a>'
                     f'<figcaption class="hint">{_dt(e.created_at)} {esc(e.caption)}'
                     '</figcaption></figure>')
        for e in others:
            body += (f'<a class="btn secondary" href="/evidence/{esc(p.id)}/{esc(e.id)}">'
                     f'{esc(e.kind.value)} {_dt(e.created_at)}</a>')
        body += "</div>"
    if not any_ev:
        body += "<p>No receipts yet.</p>"
    body += "</div>"
    return layout(p.label, body)


def outbox_page(items: list[tuple[Request, str, str, tuple[str, str, str]]], csrf: str, flash: str = "") -> str:
    body = f'<h1>Emails waiting for your approval</h1>{_flash(flash)}'
    if not items:
        body += "<p>Nothing is waiting.</p>"
    for r, who, bname, (to, subj, text) in items:
        body += (f'<div class="card"><b>{esc(who)}</b> to <b>{esc(bname)}</b> '
                 f'<span class="chip">{esc(r.kind.value.replace("_", " "))}</span>'
                 f'<p><b>To:</b> {esc(to)}<br><b>Subject:</b> {esc(subj)}</p>'
                 f'<pre class="letter">{esc(text)}</pre>'
                 f'<p class="hint">Drafted {_dt(r.created_at)}. Approving sends this email from '
                 'the removal mailbox.</p>'
                 f'<form method="post" action="/outbox/{esc(r.id)}/approve" class="actions">'
                 f'{csrf_field(csrf)}<button type="submit" data-confirm="Send this email now?">'
                 f'Approve and send</button>'
                 f'<button type="submit" class="secondary" '
                 f'formaction="/outbox/{esc(r.id)}/cancel">Cancel it</button></form></div>')
    return layout("Emails", body)


def confirm_real_page(people: list[Profile], csrf: str) -> str:
    names = ", ".join(esc(p.label) for p in people) or "nobody yet"
    body = ('<h1>Start sending real requests?</h1>'
            f'<div class="card"><p>This is for: <b>{names}</b>.</p>'
            '<p>Free My ID will now send your requests to people-search sites by email and, where a '
            'site allows it, fill in their forms. Each request names the person and only the '
            'details the site already shows, plus the separate email address. Nothing is paid for.</p>'
            '<p>Emails for people who chose "approve each" wait for your OK first. The first '
            'email for every person always waits for your OK.</p>'
            '<p>Some sites need steps by hand, and details can come back. You can switch '
            'back to practice mode in Settings at any time. Requests already sent cannot be '
            'taken back.</p>'
            '<form method="post" action="/settings/submissions/on" class="actions">'
            f'{csrf_field(csrf)}<input type="hidden" name="confirm" value="yes">'
            '<button type="submit">Yes, start sending real requests</button>'
            '<a class="btn secondary" href="/settings">No, stay in practice mode</a>'
            '</form></div>')
    return layout("Real requests", body)


def settings_page(*, people: list[Profile], schedule_status: str, practice: bool, csrf: str,
                  flash: str = "", can_quit: bool = False) -> str:
    body = f'<h1>Settings</h1>{_flash(flash)}'
    body += ('<div class="card"><h2>Run automatically</h2><p>Once a day Free My ID can check '
             'quietly in the background. If the computer was off, it catches up when it is '
             f'next on.</p><p><b>Right now:</b> {esc(schedule_status)}</p>'
             f'<form method="post" action="/schedule/install" class="actions">{csrf_field(csrf)}'
             '<button type="submit">Turn on</button>'
             '<button type="submit" class="secondary" formaction="/schedule/remove">Turn off'
             '</button></form></div>')
    if practice:
        body += ('<div class="card"><h2>Practice mode is on</h2><p>Free My ID looks for listings but '
                 'does not send any request. When you have looked at the results and are happy, '
                 f'turn on real requests.</p><form method="post" '
                 f'action="/settings/submissions/on" class="actions">{csrf_field(csrf)}'
                 '<a class="btn primary" href="/settings/submissions/confirm">'
                 'Start sending real requests</a></form></div>')
    else:
        body += ('<div class="card"><h2>Real requests are on</h2>'
                 f'<form method="post" action="/settings/submissions/off" class="actions">'
                 f'{csrf_field(csrf)}<button type="submit" class="secondary">Go back to '
                 'practice mode</button></form></div>')
    for p in people:
        mb = (f"{p.mailbox.address}" if p.mailbox else "Not set up (you send messages by hand)")
        perms = p.permissions
        body += (f'<div class="card"><h2>{esc(p.label)}</h2>'
                 f'<h3>Email for removals</h3><p>{esc(mb)}</p>'
                 f'<p><a class="btn secondary" href="/settings/{esc(p.id)}/mailbox">Change it'
                 '</a></p><h3>What Free My ID may do</h3>'
                 '<p class="hint">Everything here is off unless you tick it. If a website asks '
                 'for something you did not allow, Free My ID stops and asks you. It never pays. It will never ask for a Social Security number or bank or card details.</p>'
                 f'<form method="post" action="/settings/{esc(p.id)}/permissions">'
                 f'{csrf_field(csrf)}'
                 + _check("allow_id_upload", "Free My ID may upload a copy of an ID if a website "
                          "requires it", perms.allow_id_upload)
                 + _check("allow_account_creation", "Free My ID may create an account on a website "
                          "if required", perms.allow_account_creation)
                 + _check("allow_phone_disclosure", "Free My ID may give a phone number if "
                          "required", perms.allow_phone_disclosure)
                 + '<div class="actions"><button type="submit">Save</button></div></form></div>')
    if not people:
        body += "<p>No one has been added yet.</p>"
    if can_quit:
        body += (f'<div class="card"><h2>Close Free My ID</h2><form method="post" action="/quit" '
                 f'class="actions">{csrf_field(csrf)}<button type="submit" class="secondary" '
                 'data-confirm="Close Free My ID now?">Close Free My ID</button></form></div>')
    return layout("Settings", body)


def mailbox_settings_page(p: Profile, body_html: str, csrf: str, errs: list[str]) -> str:
    from .ui import errors_html
    return layout("Email for removals", (
        f'<h1>Email for removals: {esc(p.label)}</h1>{errors_html(errs)}'
        f'<form method="post" action="/settings/{esc(p.id)}/mailbox" class="card" '
        f'autocomplete="off">{csrf_field(csrf)}{body_html}<div class="actions">'
        '<a class="btn secondary" href="/settings">Back</a><button type="submit" class="big">'
        'Save</button></div></form>'))
