"""Dashboard page rendering (status, to-dos, outbox, evidence)."""
from __future__ import annotations

from ..models import (
    BrokerStatus,
    EvidenceKind,
    ListingState,
    Profile,
    Request,
    Todo,
)
from .ui import chip, csrf_field, esc, layout

SUMMARY_ORDER = [ListingState.NEEDS_HUMAN, ListingState.FOUND, ListingState.REAPPEARED,
                 ListingState.AWAITING_VERIFICATION, ListingState.SUBMITTED,
                 ListingState.CONFIRMED, ListingState.REMOVED]


def _dt(d) -> str:
    return d.strftime("%Y-%m-%d") if d else "-"


def home_page(rows: list[dict], csrf: str, flash: str = "") -> str:
    body = f'<h1>Your people</h1>{_flash(flash)}'
    for r in rows:
        p: Profile = r["profile"]
        counts: dict[ListingState, int] = r["counts"]
        chips = " ".join(f'{chip(s)} {counts[s]}' for s in SUMMARY_ORDER if counts.get(s))
        warn = ""
        if r["consent_problem"]:
            warn = f'<div class="error">Not running yet: {esc(r["consent_problem"])}</div>'
        body += (f'<div class="card"><h2><a href="/profile/{esc(p.id)}">{esc(p.label)}</a></h2>'
                 f'{warn}<p>{chips or "Nothing checked yet."}</p>'
                 f'<p>{r["todos"]} thing(s) need you. {r["outbox"]} email(s) waiting for approval.'
                 f'</p><a class="btn" href="/profile/{esc(p.id)}">Open</a></div>')
    body += ('<p class="hint">"Removed" means removed from that one broker only. Listings can '
             'reappear, which is why Vanish keeps re-checking.</p>')
    return layout("Dashboard", body)


def _flash(msg: str) -> str:
    return f'<div class="note" role="status">{esc(msg)}</div>' if msg else ""


def profile_page(p: Profile, statuses: list[BrokerStatus], names: dict[str, str],
                 todos: list[Todo], evidence_by_broker: dict[str, list], csrf: str,
                 consent_problem: str, flash: str = "") -> str:
    body = f'<h1>{esc(p.label)}</h1>{_flash(flash)}'
    if consent_problem:
        body += f'<div class="error">Not running yet: {esc(consent_problem)}</div>'
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
    body += '<div class="card"><h2>Needs you</h2>'
    if not todos:
        body += "<p>Nothing right now.</p>"
    for t in todos:
        links = "".join(f'<li><a href="{esc(u)}" target="_blank" rel="noopener noreferrer">'
                        f'{esc(u)}</a></li>' for u in t.links if u.startswith(("http://",
                                                                               "https://")))
        body += (f'<div class="card"><b>{esc(names.get(t.broker_id or "", ""))}</b> '
                 f'<span class="chip">{esc(t.kind.value.replace("_", " "))}</span>'
                 f'<p>{esc(t.title)}</p><p class="hint">{esc(t.body)}</p>'
                 f'{"<ul>" + links + "</ul>" if links else ""}'
                 f'<form method="post" action="/todo/{esc(t.id)}/done" class="actions">'
                 f'{csrf_field(csrf)}'
                 + (f'<button type="submit" formaction="/todo/{esc(t.id)}/resolve">Resolve'
                    '</button>' if t.resume_token else "")
                 + '<button type="submit" class="secondary">Done</button></form></div>')
    body += "</div>"
    # per-broker table
    body += ('<div class="card"><h2>Brokers</h2><table><tr><th>Broker</th><th>State</th>'
             '<th>Updated</th><th>Next check</th></tr>')
    for st in sorted(statuses, key=lambda s: (names.get(s.broker_id, s.broker_id)).lower()):
        extra = (f'<br><span class="hint">{esc(st.needs_human_reason)}</span>'
                 if st.needs_human_reason else "")
        body += (f'<tr><td>{esc(names.get(st.broker_id, st.broker_id))}</td>'
                 f'<td>{chip(st.state)}{extra}</td><td>{_dt(st.updated_at)}</td>'
                 f'<td>{_dt(st.next_check_at)}</td></tr>')
    if not statuses:
        body += '<tr><td colspan="4">No brokers checked yet. Run <code>vanish scan</code>.</td></tr>'
    body += "</table></div>"
    # evidence
    body += '<div class="card"><h2>Evidence</h2><p class="hint">Screenshots are stored ' \
            'encrypted and only decrypted when shown here.</p>'
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
        body += "<p>No evidence yet.</p>"
    body += "</div>"
    return layout(p.label, body)


def outbox_page(items: list[tuple[Request, str, str]], csrf: str, flash: str = "") -> str:
    body = f'<h1>Emails waiting for your approval</h1>{_flash(flash)}'
    if not items:
        body += "<p>Nothing is waiting.</p>"
    for r, who, bname in items:
        body += (f'<div class="card"><b>{esc(who)}</b> to <b>{esc(bname)}</b> '
                 f'<span class="chip">{esc(r.kind.value.replace("_", " "))}</span>'
                 f'<p class="hint">Drafted {_dt(r.created_at)}. Approving sends this email from '
                 'the removal mailbox.</p>'
                 f'<form method="post" action="/outbox/{esc(r.id)}/approve" class="actions">'
                 f'{csrf_field(csrf)}<button type="submit" data-confirm="Send this email now?">'
                 f'Approve and send</button>'
                 f'<button type="submit" class="secondary" '
                 f'formaction="/outbox/{esc(r.id)}/cancel">Cancel it</button></form></div>')
    return layout("Emails", body)


def settings_page(status: str, csrf: str, flash: str = "") -> str:
    body = (f'<h1>Background checks</h1>{_flash(flash)}<div class="card">'
            '<p>Vanish can re-check brokers once a day in the background. If the computer was '
            'off or asleep, it catches up when it wakes.</p>'
            f'<pre>{esc(status)}</pre>'
            f'<form method="post" action="/schedule/install" class="actions">{csrf_field(csrf)}'
            '<button type="submit">Turn on</button>'
            '<button type="submit" class="secondary" formaction="/schedule/remove">Turn off'
            '</button></form></div>')
    return layout("Background checks", body)
