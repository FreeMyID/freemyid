"""Plain progress report (HTML, or PDF when weasyprint is installed).

Deliberately PII-light: the person's on-screen label, site names, states and dates only.
No addresses, phone numbers or evidence images, so the file is safe to share with family.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from .. import paths
from ..models import BrokerCategory, ListingState, RequestStatus, utcnow
from .ui import CHIP_LABEL, HONESTY, esc

_CSS = ("body{font:18px/1.5 system-ui,sans-serif;max-width:46rem;margin:2rem auto;padding:0 1rem}"
        "table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ccc;"
        "padding:.4rem;text-align:left}td.d{white-space:nowrap}.cov{display:block;font-size:.8em;color:#666}"
        "@page{size:A4;margin:1.5cm}@media print{body{font-size:14px;max-width:none;margin:0}}"
        ".lead{font-size:1.15em}.note{background:#f4f4f4;padding:.8rem;border-radius:6px}")


_GOOD = {ListingState.CONFIRMED, ListingState.REMOVED}
_WAIT = {ListingState.SUBMITTED, ListingState.AWAITING_VERIFICATION}


@dataclass(frozen=True)
class ReportCounts:
    """The numbers the opening sentences state. HTML and PDF are rendered from the same ones.

    `asked` is evidence of a real send, never a state name: a site that only "needs you", or
    that only has a practice (dry-run) letter, has not been asked anything (WO-603).
    A site can be in both `asked` and `need_you` (asked, and now waiting on a step)."""
    sites: int            # rows in the report
    asked: int            # sites that really received a request
    good: int             # asked, and confirmed or no longer listing the person
    waiting: int          # asked, no answer yet
    reappeared: int       # asked, took the details down, then listed them again
    need_you: int         # sites waiting on a step from a person
    other_steps: int      # open to-dos that are not about one of the sites above
    people_search_only: bool


@dataclass(frozen=True)
class _Facts:
    statuses: list
    asked_at: dict[str, datetime]     # broker id -> latest real request
    need_you: set[str]
    shared_step: bool                 # one step covers several sites (covered_by)
    counts: ReportCounts


def _aware(t: datetime) -> datetime:
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def _facts(store, registry, profile_id: str) -> _Facts:
    brokers = list(registry.brokers) if registry else []
    names = {b.id: b.name for b in brokers}
    cats = {b.id: b.category for b in brokers}
    sts = sorted((s for s in store.list_statuses(profile_id) if not s.broker_id.startswith("_")),
                 key=lambda s: names.get(s.broker_id, s.broker_id))
    listed = {s.broker_id for s in sts}
    # A real send: the status carries a submission time (state.mark_submitted / transition set
    # it only after a send succeeded), or there is a SENT request that is not a dry run.
    asked_at: dict[str, datetime] = {
        s.broker_id: _aware(s.last_submitted_at) for s in sts if s.last_submitted_at}
    for r in store.list_requests(profile_id, status=RequestStatus.SENT):
        if r.dry_run or r.broker_id not in listed:
            continue
        when = _aware(r.sent_at or r.created_at)
        if r.broker_id not in asked_at or when > asked_at[r.broker_id]:
            asked_at[r.broker_id] = when
    todos = store.list_todos(profile_id)
    need_you = {s.broker_id for s in sts if s.state == ListingState.NEEDS_HUMAN}
    need_you |= {t.broker_id for t in todos if t.broker_id in listed}
    asked = [s for s in sts if s.broker_id in asked_at]
    counts = ReportCounts(
        sites=len(sts), asked=len(asked),
        good=sum(1 for s in asked if s.state in _GOOD),
        waiting=sum(1 for s in asked if s.state in _WAIT),
        reappeared=sum(1 for s in asked if s.state == ListingState.REAPPEARED),
        need_you=len(need_you),
        other_steps=sum(1 for t in todos if t.broker_id not in listed),
        people_search_only=bool(sts) and all(
            cats.get(s.broker_id) == BrokerCategory.PEOPLE_SEARCH for s in sts))
    shared = any((s.needs_human_reason or "").startswith("via:") for s in sts)
    return _Facts(sts, asked_at, need_you, shared, counts)


def report_counts(store, registry, profile_id: str) -> ReportCounts:
    """The counts `build_report` prints, for tests and other screens."""
    return _facts(store, registry, profile_id).counts


def _opening(c: ReportCounts, shared_step: bool, today: date) -> str:
    """The first two paragraphs. Only real sends are called "asked"."""
    kind = "people-search" if c.people_search_only else "data broker"

    def sites(n: int, first: bool = False) -> str:
        return f"{n} {kind + ' ' if first else ''}site{'' if n == 1 else 's'}"

    need = f"{'needs' if c.need_you == 1 else 'need'} a step from you."
    if c.asked == 0:
        lead = ["Nothing has been sent yet."]
        if c.need_you:
            lead.append(f"{sites(c.need_you, True)} {need}")
    else:
        done = "has confirmed or no longer lists" if c.good == 1 else \
            "have confirmed or no longer list"
        asked = (f"{sites(c.asked, True)} {'has' if c.asked == 1 else 'have'} been asked to "
                 "delete this person's details.")
        so_far = (f"So far {c.good} {done} them, and {c.waiting} "
                  f"{'has' if c.waiting == 1 else 'have'} not replied yet.")
        lead = [asked, so_far]
        if c.reappeared:
            lead.append(f"{c.reappeared} put the details back up after taking them down.")
        if c.need_you:
            lead.append(f"{sites(c.need_you)} {need}")
    more = [f"This report was made on {today}."]
    if c.asked == 0:
        more.append("That means no site has received a request to delete this person's "
                    "details so far.")
    if c.need_you:
        more.append("Open Free My ID to see the steps waiting for you."
                    + (" One step can cover several sites." if shared_step else ""))
    if c.other_steps:
        more.append(f"{c.other_steps} more step{' is' if c.other_steps == 1 else 's are'} "
                    "waiting for you in Free My ID.")
    if not c.people_search_only:
        more.append("A data broker is a company that collects details about people and sells "
                    "or shares them. People-search sites are one kind.")
    return f'<p class="lead">{esc(" ".join(lead))}</p><p>{esc(" ".join(more))}</p>'


def build_report(store, registry, profile_id: str, fmt: str = "html") -> Path:
    p = store.get_profile(profile_id)
    if p is None:
        raise ValueError("no such profile")
    if fmt not in ("html", "pdf"):
        raise ValueError("fmt must be 'html' or 'pdf'")
    names = {b.id: b.name for b in registry.brokers} if registry else {}
    members: dict[str, list[str]] = {}
    for b in (registry.brokers if registry else []):
        if getattr(b, "covered_by", None):
            members.setdefault(b.covered_by, []).append(b.name)

    def site_cell(bid: str) -> str:
        full = names.get(bid, bid)
        short = full.split(" (")[0]
        cov = members.get(bid)
        if cov:
            extra = f'<span class="cov">covers: {esc(", ".join(sorted(cov)))}</span>'
        elif short != full:
            extra = f'<span class="cov">{esc(full[len(short) + 2:].rstrip(")"))}</span>'
        else:
            extra = ""
        return esc(short) + extra

    facts = _facts(store, registry, profile_id)

    def status_cell(s) -> str:
        state = s.state
        if state == ListingState.FOUND and s.last_scan_at is None \
                and s.broker_id not in facts.asked_at:
            state = ListingState.UNKNOWN     # presumed, never searched: nothing was seen
        label = CHIP_LABEL[state]
        if s.broker_id in facts.need_you and s.state != ListingState.NEEDS_HUMAN:
            label += f" ({CHIP_LABEL[ListingState.NEEDS_HUMAN]})"
        return esc(label)

    def asked_cell(s) -> str:
        when = facts.asked_at.get(s.broker_id)
        return str(when.date()) if when else "-"

    rows = "".join(
        f"<tr><td>{site_cell(s.broker_id)}</td><td>{status_cell(s)}"
        f"</td><td class='d'>{s.last_scan_at.date() if s.last_scan_at else '-'}</td>"
        f"<td class='d'>{asked_cell(s)}</td></tr>"
        for s in facts.statuses)
    doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Free My ID report'
           f"</title><style>{_CSS}</style></head><body><h1>{esc(p.label)}: Free My ID progress "
           f"report</h1>{_opening(facts.counts, facts.shared_step, utcnow().date())}"
           f'<table><tr><th>Site</th><th>Status</th><th>Last checked</th>'
           f"<th>Last request</th></tr>{rows}</table>"
           f'<p class="note">{esc(HONESTY)}</p></body></html>')
    stem = f"report-{profile_id[:8]}-{utcnow().strftime('%Y%m%d')}"
    out = paths.artifacts_dir() / f"{stem}.html"
    out.write_text(doc, encoding="utf-8")
    out.chmod(0o600)
    if fmt == "pdf":
        try:
            from weasyprint import HTML  # optional dependency
        except ImportError:
            return out   # caller sees the .html suffix and can tell PDF was unavailable
        pdf = out.with_suffix(".pdf")
        HTML(string=doc).write_pdf(str(pdf))
        pdf.chmod(0o600)
        out.unlink(missing_ok=True)
        return pdf
    return out
