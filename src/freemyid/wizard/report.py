"""Plain progress report (HTML, or PDF when weasyprint is installed).

Deliberately PII-light: the person's on-screen label, site names, states and dates only.
No addresses, phone numbers or evidence images, so the file is safe to share with family.
"""
from __future__ import annotations

from pathlib import Path

from .. import paths
from ..models import ListingState, utcnow
from .ui import CHIP_LABEL, HONESTY, esc

_CSS = ("body{font:18px/1.5 system-ui,sans-serif;max-width:46rem;margin:2rem auto;padding:0 1rem}"
        "table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ccc;"
        "padding:.4rem;text-align:left}.note{background:#f4f4f4;padding:.8rem;border-radius:6px}")


_GOOD = {ListingState.CONFIRMED, ListingState.REMOVED}
_WAIT = {ListingState.SUBMITTED, ListingState.AWAITING_VERIFICATION}
_ASKED = _GOOD | _WAIT | {ListingState.REAPPEARED, ListingState.NEEDS_HUMAN}


def build_report(store, registry, profile_id: str, fmt: str = "html") -> Path:
    p = store.get_profile(profile_id)
    if p is None:
        raise ValueError("no such profile")
    if fmt not in ("html", "pdf"):
        raise ValueError("fmt must be 'html' or 'pdf'")
    names = {b.id: b.name for b in registry.brokers} if registry else {}
    sts = sorted(store.list_statuses(profile_id), key=lambda s: names.get(s.broker_id, s.broker_id))
    counts: dict[ListingState, int] = {}
    for s in sts:
        counts[s.state] = counts.get(s.state, 0) + 1
    asked = sum(n for k, n in counts.items() if k in _ASKED)
    good = sum(n for k, n in counts.items() if k in _GOOD)
    wait = sum(n for k, n in counts.items() if k in _WAIT)
    rows = "".join(
        f"<tr><td>{esc(names.get(s.broker_id, s.broker_id))}</td><td>{esc(CHIP_LABEL[s.state])}"
        f"</td><td>{s.last_scan_at.date() if s.last_scan_at else '-'}</td>"
        f"<td>{s.last_submitted_at.date() if s.last_submitted_at else '-'}</td></tr>"
        for s in sts)
    todos = store.list_todos(profile_id)
    doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Free My ID report'
           f"</title><style>{_CSS}</style></head><body><h1>{esc(p.label)}: what Free My ID has asked, and what came back</h1>"
           f"<p>As of {utcnow().date()}, Free My ID has asked {asked} people-search sites to "
           f"delete this person's details. {good} have confirmed or no longer list them. "
           f"{wait} are still waiting. {len(todos)} need a person to do one step. "
           f"Sites can put details back up, so Free My ID checks again.</p>"
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
