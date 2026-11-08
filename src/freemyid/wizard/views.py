"""v0.3 pages: exposure card, broker detail, Protect yourself, 'What we did for you'."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..storage import Store

from fastapi import HTTPException

from ..models import (
    ChecklistFile,
    EvidenceKind,
    ListingState,
    Profile,
    utcnow,
)
from .dashboard import _dt, _flash
from .ui import CHIP_LABEL, HONESTY, chip, csrf_field, esc, layout

log = logging.getLogger(__name__)

# Plain words for the printable report and the broker page.
PLAIN = {
    ListingState.UNKNOWN: "Not checked yet",
    ListingState.NOT_FOUND: "Not listed there",
    ListingState.FOUND: "Listed. A request has not gone out yet",
    ListingState.SUBMITTED: "We asked them to delete it",
    ListingState.AWAITING_VERIFICATION: "We asked. They need to confirm",
    ListingState.CONFIRMED: "They confirmed",
    ListingState.REMOVED: "No longer listed",
    ListingState.REAPPEARED: "It came back. We are asking again",
    ListingState.NEEDS_HUMAN: "Needs a step from you",
    ListingState.ERROR: "We hit a problem. We will try again",
}
_GOOD = {ListingState.CONFIRMED, ListingState.REMOVED}
ACTION_WORDS = {
    "submitted": "Sent a request", "request_sent": "Sent a request", "scan": "Checked the site",
    "found": "Found a listing", "removed": "Listing gone", "reappeared": "Listing came back",
    "checklist_done": "Ticked a safety step", "checklist_undone": "Un-ticked a safety step",
}


# ------------------------------------------------------------------ exposure placeholder
def exposure_card(store: Store, profile: Profile | None) -> str:
    """Wired to freemyid.engine.exposure.latest_exposure(store, profile) when it exists."""
    head = ('<section class="card"><h2><span class="ico ico-map" aria-hidden="true"></span> '
            'Where you are listed</h2>')
    try:
        from ..engine.exposure import latest_exposure
    except ImportError:   # engine module not shipped in this build
        return head + ('<p><b>Coming soon.</b> This version does not include the listing '
                       'check.</p></section>')
    if profile is not None:
        head += f'<p><b>Results for {esc(profile.label)}</b></p>'
    try:
        result = latest_exposure(store, profile) if profile else None
    except Exception as e:  # noqa: BLE001  a broken helper must never break the home page
        log.warning("exposure unavailable: %s", type(e).__name__)
        return head + ('<p>Your saved result is not available right now. '
                       'This does not tell us whether any sites list you.</p></section>')
    if result is None:
        return head + ('<p>No picture yet. There is no saved result to show. '
                       'Results will appear here after a check.</p></section>')
    found = len(result.by_status("found"))
    hand = len(result.by_status("check_by_hand"))
    lines = "".join(f"<li>{esc(ln.text)}</li>" for ln in result.explanation[:5])
    hidden = len(result.explanation) - 5
    if hidden > 0:
        lines += f"<li>…and {hidden} more reason{'' if hidden == 1 else 's'}</li>"
    found_text = ("No listings found on the sites checked." if found == 0 else
                  f"Listings found on {found} site{'' if found == 1 else 's'}.")
    hand_text = (" 1 site needs a manual check." if hand == 1 else
                 f" {hand} sites need a manual check." if hand > 1 else "")
    return (head + f'<p>{found_text}{hand_text}</p>'
            '<p>These results cover only the sites checked, not every website.</p>'
            f'<p>Checked {esc(_dt(result.created_at))}.</p>'
            f'<p class="lead"><b>{esc(result.score)}</b> out of 100 '
            '<span class="hint">(lower is better)</span></p>'
            '<p>This score describes this check, not your overall safety.</p>'
            + (f'<ul class="hint">{lines}</ul>' if lines else "")
            + "</section>")


# ------------------------------------------------------------------ broker detail
def _kind_words(kind: str) -> str:
    return {"opt_out": "Deletion request", "resubmit": "Second request",
            "follow_up": "Follow-up", "legal_demand": "Formal demand"}.get(kind, kind)


def broker_page(p: Profile, broker, bid: str, status, listings: list, requests: list,
                evidence: list, events: list, todos: list) -> str:
    if bid.startswith("_"):
        raise HTTPException(status_code=404, detail="Not found")
    name = broker.name if broker else bid
    body = (f'<p><a href="/profile/{esc(p.id)}">All sites for {esc(p.label)}</a></p>'
            f'<h1>{esc(name)}</h1><p>{chip(status.state)} <span class="hint">'
            f'{esc(PLAIN.get(status.state, ""))}</span></p>')
    if status.needs_human_reason:
        body += f'<div class="note">{esc(status.needs_human_reason)}</div>'
    if todos:
        body += '<div class="note">This site needs a step from you. <a href="/">Go to Today</a></div>'
    # what they hold
    body += '<section class="card"><h2>What this site shows about you</h2>'
    if not listings:
        body += "<p>Nothing found yet.</p>"
    for li in listings:
        bits = []
        if li.name_shown:
            bits.append(f"Name: {li.name_shown}")
        if li.age_shown:
            bits.append(f"Age: {li.age_shown}")
        if li.locations_shown:
            bits.append("Places: " + "; ".join(li.locations_shown[:5]))
        if li.relatives_shown:
            bits.append(f"Relatives listed: {len(li.relatives_shown)}")
        gone = f" Gone since {_dt(li.gone_since)}." if li.gone_since else ""
        body += ("<p>" + "<br>".join(esc(b) for b in bits) +
                 f'<br><span class="hint">First seen {_dt(li.first_seen)}.{esc(gone)}</span></p>')
    body += ('<p class="hint">This is only what the site itself shows. Free My ID sends a site '
             'nothing more than that.</p></section>')
    # what we sent
    body += '<section class="card"><h2>What we sent</h2>'
    if not requests:
        body += "<p>No request has gone to this site yet.</p>"
    else:
        body += '<div class="tablewrap"><table><tr><th>When</th><th>What</th><th>How</th><th>State</th></tr>'
        for r in sorted(requests, key=lambda x: x.created_at, reverse=True):
            when = _dt(r.sent_at or r.created_at)
            how = r.method.value.replace("_", " ")
            state = r.status.value.replace("_", " ") + (" (practice)" if r.dry_run else "")
            ref = f' <span class="hint">Reference {esc(r.reference)}</span>' if r.reference else ""
            body += (f"<tr><td>{when}</td><td>{esc(_kind_words(r.kind.value))}{ref}</td>"
                     f"<td>{esc(how)}</td><td>{esc(state)}</td></tr>")
        body += "</table></div>"
    body += "</section>"
    # replies
    replies = [e for e in evidence if e.kind == EvidenceKind.EMAIL_RECEIVED]
    body += '<section class="card"><h2>What came back</h2>'
    if replies:
        for e in replies:
            body += (f'<p><a class="btn secondary" href="/evidence/{esc(p.id)}/{esc(e.id)}">'
                     f'Reply received {_dt(e.created_at)}</a></p>')
    else:
        body += "<p>No reply yet. Many sites never reply. Free My ID checks the listing itself.</p>"
    body += "</section>"
    # next check
    nxt = _dt(status.next_check_at) if status.next_check_at else "not planned yet"
    body += (f'<section class="card"><h2>Next check</h2><p class="lead">{esc(nxt)}</p>'
             f'<p class="hint">Last checked {_dt(status.last_scan_at)}. Last request '
             f'{_dt(status.last_submitted_at)}. Sites can put details back up, so Free My ID '
             'looks again.</p></section>')
    # evidence
    body += '<section class="card"><h2>Receipts</h2>'
    if not evidence:
        body += "<p>No receipts yet.</p>"
    else:
        body += ('<p class="hint">What the site showed and replied, kept encrypted on this '
                 'computer.</p><div class="gallery">')
        for e in sorted(evidence, key=lambda x: x.created_at):
            cap = esc(e.caption or e.kind.value.replace("_", " "))
            if e.kind == EvidenceKind.SCREENSHOT:
                body += (f'<figure><a href="/evidence/{esc(p.id)}/{esc(e.id)}" target="_blank">'
                         f'<img loading="lazy" alt="{cap}" src="/evidence/{esc(p.id)}/{esc(e.id)}">'
                         f'</a><figcaption class="hint">{_dt(e.created_at)} {cap}</figcaption></figure>')
            else:
                body += (f'<a class="btn secondary" href="/evidence/{esc(p.id)}/{esc(e.id)}">'
                         f'{cap} {_dt(e.created_at)}</a>')
        body += "</div>"
    body += "</section>"
    # timeline (action words only; events carry no PII by contract)
    if events:
        body += '<section class="card"><h2>What happened</h2><ul>'
        for ev in events[:12]:
            words = ACTION_WORDS.get(ev.action, ev.action.replace("_", " ").capitalize())
            to = f" ({esc(CHIP_LABEL.get(ev.to_state, ''))})" if ev.to_state else ""
            body += f"<li>{_dt(ev.ts)}: {esc(words)}{to}</li>"
        body += "</ul></section>"
    return layout(name, body)


# ------------------------------------------------------------------ Protect yourself
PARTIAL_NOTE = ("We could not read this company's own page when we prepared these steps, so some "
                "details come from trusted consumer-help sites. This is still a good thing to do. "
                "Before you type anything in or call a number, check the address and the phone "
                "number on the company's own page.")


def _checklist_item(c, done: bool, pid: str, csrf: str) -> str:
    cid = esc(c.id)
    tick = ('<span class="tick" aria-hidden="true">'
            + ('<span class="ico ico-check"></span>' if done else "") + "</span>")
    state = "done" if done else "to do"
    need = ("".join(f"<li>{esc(x)}</li>" for x in c.need_on_hand))
    steps = "".join(f"<li>{esc(x)}</li>" for x in c.steps)
    tips = "".join(f"<li>{esc(x)}</li>" for x in (getattr(c, "tips", None) or []))
    partial = (f'<p class="note calm">{esc(PARTIAL_NOTE)}</p>'
               if c.verification == "partial" else "")
    extra = f'<p class="note calm">{esc(c.status_note)}</p>' if c.status_note else ""
    return (
        f'<details class="card cl{" done" if done else ""}" id="c-{cid}">'
        f'<summary>{tick}<span>{esc(c.title)} <span class="sr">({state})</span></span></summary>'
        f'<div class="cl-body"><p>{esc(c.why)}</p>'
        f'<p class="meta"><span>Cost: {esc(c.cost)}</span><span>Time: {esc(c.time_needed)}</span></p>'
        f'{partial}{extra}'
        + (f"<h2 class=\"sub\">Have these ready</h2><ul>{need}</ul>" if need else "")
        + f"<h2 class=\"sub\">Steps</h2><ol>{steps}</ol>"
        + (f"<h2 class=\"sub\">Good to know</h2><ul>{tips}</ul>" if tips else "")
        + f'<p><b>To undo it:</b> {esc(c.how_to_undo)}</p>'
        f'<p class="hint">Checked on {_dt(datetime.combine(c.date_checked, datetime.min.time()))}.</p>'
        f'<div class="actions"><form method="post" action="/protect/{esc(pid)}/{cid}/open" '
        f'class="inline">{csrf_field(csrf)}<button type="submit" class="secondary">'
        'Open the web page</button></form>'
        f'<form method="post" action="/protect/{esc(pid)}/{cid}/{"undo" if done else "done"}" '
        f'class="inline">{csrf_field(csrf)}<button type="submit" class="'
        f'{"secondary" if done else "primary"}">{"I have not done this" if done else "I did this"}'
        "</button></form></div></div></details>")


def engine_group(steps: list, pid: str, csrf: str) -> str:
    """The 'Google and Bing' group: one card per guided step (engine tool, no auto-search)."""
    from ..engine.search_engines import INTRO, STATUS_TEXT
    if not steps:
        return ""
    out = ('<section class="card engines" aria-labelledby="engines-h"><h2 id="engines-h">'
           f'Google and Bing</h2><p>{esc(INTRO)}</p>')
    for g in steps:
        cid = esc(g.checklist.id)
        when = ""
        if g.done_at:
            when = f" Done on {_dt(g.done_at)}."
        elif g.opened_at:
            when = f" Opened on {_dt(g.opened_at)}."
        done = g.status == "done"
        base = f"/protect/{esc(pid)}/search/{cid}"
        out += (f'<div class="engine-step" id="e-{cid}"><h3>{esc(g.step.engine)}: '
                f'{esc(g.checklist.title)}</h3><p>{esc(g.step.why_now)}</p>'
                f'<p class="progress" role="status">{esc(STATUS_TEXT[g.status])}{esc(when)}</p>'
                f'<div class="actions"><form method="post" action="{base}/open" class="inline">'
                f'{csrf_field(csrf)}<button type="submit" class="primary">Open the page for me'
                f'</button></form> <a class="btn secondary" href="{esc(str(g.checklist.url))}" '
                f'target="_blank" rel="noopener noreferrer">Or open the link yourself</a> '
                f'<form method="post" action="{base}/{"undo" if done else "done"}" class="inline">'
                f'{csrf_field(csrf)}<button type="submit" class="secondary">'
                f'{"I have not done this" if done else "I did this"}</button></form></div></div>')
    return out + "</section>"


def protect_page(cf: ChecklistFile | None, people: list[Profile], cur: Profile | None,
                 prog: dict[str, bool], csrf: str, flash: str = "",
                 engines: list | None = None) -> str:
    body = (f'<h1>Protect yourself</h1>{_flash(flash)}<p class="lead">Removing your details from '
            'people-search sites is one part. These steps help stop someone using them. Each one '
            'is optional, most are free, and you can tick them off as you go. The ticks stay on '
            'this computer.</p>')
    if cf is None or cur is None:
        return layout("Protect yourself", body + '<div class="card"><p>The list is not '
                      'available right now.</p></div>', current="/protect")
    if len(people) > 1:
        body += '<p>' + " ".join(
            f'<a class="btn {"primary" if p.id == cur.id else "secondary"}" '
            f'href="/protect?p={esc(p.id)}">{esc(p.label)}</a>' for p in people) + "</p>"
    body += engine_group(engines or [], cur.id, csrf)
    done = sum(1 for c in cf.checklists if prog.get(c.id))
    total = len(cf.checklists)
    body += (f'<p class="progress" role="status">{done} of {total} done for {esc(cur.label)}</p>'
             f'<progress max="{total}" value="{done}" aria-label="Safety steps done">'
             f'{done} of {total}</progress>')
    for c in cf.checklists:
        body += _checklist_item(c, bool(prog.get(c.id)), cur.id, csrf)
    body += ('<p class="hint">Free My ID never pays for you and never asks for your Social Security '
             'number. These steps happen on the real company websites, in your own browser.</p>')
    return layout("Protect yourself", body, current="/protect")


# ------------------------------------------------------------------ 'What we did for you'
def summary_page(p: Profile, statuses: list, names: dict[str, str], n_todos: int,
                 sent: int) -> str:
    def nm(bid: str) -> str:
        return names.get(bid, bid).split(" (")[0]

    statuses = [s for s in statuses if not s.broker_id.startswith("_")]
    good = [s for s in statuses if s.state in _GOOD]
    waiting = [s for s in statuses if s.state in (ListingState.SUBMITTED,
                                                  ListingState.AWAITING_VERIFICATION)]
    clean = [s for s in statuses if s.state == ListingState.NOT_FOUND]
    rows = ""
    for s in sorted((x for x in statuses if x.state not in (ListingState.UNKNOWN,
                                                              ListingState.NOT_FOUND)),
                    key=lambda x: nm(x.broker_id).lower()):
        when = s.last_submitted_at or s.updated_at
        rows += (f"<tr><td>{esc(nm(s.broker_id))}</td><td>{esc(PLAIN[s.state])}</td>"
                 f"<td>{_dt(when)}</td></tr>")
    table = ('<table><tr><th scope="col">Site</th><th scope="col">What happened</th>'
             f'<th scope="col">Date</th></tr>{rows}</table>' if rows else
             "<p>No site has needed a request so far.</p>")
    body = (
        '<div class="summary wrap-narrow"><div class="actions noprint"><button type="button" class="primary" '
        'data-print="1"><span class="ico ico-report" aria-hidden="true"></span> Print this page'
        '</button> <a class="btn secondary" href="/">Back</a></div>'
        f"<h1>What Free My ID did for {esc(p.label)}</h1>"
        f"<p>Written on {_dt(utcnow())}.</p>"
        f"<p class=\"lead\">Free My ID has sent {sent} request{'' if sent == 1 else 's'} asking "
        f"people-search sites to delete {esc(p.label)}'s details. {len(good)} "
        f"site{' has' if len(good) == 1 else 's have'} confirmed or no longer list them. "
        f"{len(waiting)} {'is' if len(waiting) == 1 else 'are'} still waiting to reply. "
        f"{n_todos} {'needs' if n_todos == 1 else 'need'} a step from a person. "
        f"{len(clean)} site{' was' if len(clean) == 1 else 's were'} checked and did not list "
        "them.</p>"
        f"<h2>The list</h2>{table}"
        f'<h2>Please remember</h2><p>{esc(HONESTY)}</p>'
        "<p>Free My ID keeps checking and asks again if details come back. This page holds "
        "only a name and site names. It has no address, phone number or date of birth, so it is "
        "safe to hand to a family member.</p></div>")
    return layout(f"What we did for {p.label}", body)
