"""Stable machine-readable output for the CLI (`--json`) and the documented exit codes.

OWNER: automation-engineer (CLI v0.2). Reference: docs/CLI.md.

Rules for every shape here:
* each document is one JSON object with ``"schema": "<name>/1"``; fields are only ever
  added, never renamed or removed, within a schema version;
* no PII beyond what the human output already shows (profile labels, broker names, to-do
  titles), never secrets, never copy-fields, letters, addresses or mailbox details;
* timestamps are ISO 8601 UTC strings or null.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from .engine.runner import RunReport
    from .exposure_models import ExposureResult
    from .models import BrokerStatus, Profile, Registry, Request, Todo

# Exit codes (docs/CLI.md). Never reuse a number for something else.
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_NEEDS_HUMAN = 3
EXIT_NOT_CONFIGURED = 4


def _ts(d: datetime | date | None) -> str | None:
    return d.isoformat() if d is not None else None


def emit(doc: dict[str, Any]) -> None:
    """Write one JSON document to stdout (plain print: rich would wrap long lines)."""
    sys.stdout.write(json.dumps(doc, sort_keys=False, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def skipped_entry(p: Profile, reason: str) -> dict[str, Any]:
    return {"profile_id": p.id, "label": p.label, "reason": reason}


def status_doc(rows: list[tuple[Profile, list[BrokerStatus], int]], names: dict[str, str],
               skipped: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "status/1",
        "profiles": [{
            "profile_id": p.id,
            "label": p.label,
            "open_todos": todos,
            "brokers": [{
                "broker_id": st.broker_id,
                "broker_name": names.get(st.broker_id, st.broker_id),
                "state": st.state.value,
                "tier": st.tier.value if st.tier else None,
                "updated_at": _ts(st.updated_at),
                "last_scan_at": _ts(st.last_scan_at),
                "last_submitted_at": _ts(st.last_submitted_at),
                "next_check_at": _ts(st.next_check_at),
                "attempts": st.attempts,
                "escalation_level": st.escalation_level,
            } for st in sorted(sts, key=lambda s: s.broker_id)],
        } for p, sts, todos in rows],
        "skipped": skipped,
    }


def profiles_doc(rows: list[tuple[Profile, bool]]) -> dict[str, Any]:
    return {
        "schema": "profiles/1",
        "profiles": [{
            "id": p.id,
            "label": p.label,
            "state_of_residence": p.state_of_residence,
            "consent_basis": p.consent.basis.value,
            "consent_ok": ok,
            "has_mailbox": p.mailbox is not None,
            "email_mode": p.email_mode.value,
            "created_at": _ts(p.created_at),
        } for p, ok in rows],
    }


def todos_doc(rows: list[tuple[Profile, Todo]], skipped: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "todos/1",
        "todos": [{
            "id": t.id,
            "profile_id": p.id,
            "label": p.label,
            "broker_id": t.broker_id,
            "kind": t.kind.value,
            "title": t.title,
            "request_id": t.request_id,
            "created_at": _ts(t.created_at),
        } for p, t in rows],
        "skipped": skipped,
    }


def outbox_doc(reqs: list[Request]) -> dict[str, Any]:
    return {
        "schema": "outbox/1",
        "requests": [{
            "id": r.id,
            "profile_id": r.profile_id,
            "broker_id": r.broker_id,
            "kind": r.kind.value,
            "method": r.method.value,
            "status": r.status.value,
            "attempt": r.attempt,
            "created_at": _ts(r.created_at),
        } for r in reqs],
    }


def registry_doc(reg: Registry, source: str, warnings: list[str]) -> dict[str, Any]:
    return {
        "schema": "registry/1",
        "version": reg.version,
        "updated": _ts(reg.updated),
        "source": source,
        "warnings": list(warnings),
        "brokers": [{
            "id": b.id,
            "name": b.name,
            "url": str(b.url),
            "category": b.category.value,
            "method": b.method.value,
            "verification_status": b.verification_status.value,
            "has_captcha": b.has_captcha,
            "covered_by": b.covered_by,
            "priority": b.priority,
            "enabled": b.enabled,
        } for b in sorted(reg.brokers, key=lambda b: (-b.priority, b.id))],
    }


def registry_source_doc(reg: Registry, source: str, warnings: list[str]) -> dict[str, Any]:
    return {"schema": "registry-source/1", "source": source, "version": reg.version,
            "updated": _ts(reg.updated), "brokers": len(reg.brokers),
            "warnings": list(warnings)}


def schedule_doc(platform: str | None, detail: str) -> dict[str, Any]:
    low = detail.lower()
    installed = bool(detail) and "not installed" not in low and "not supported" not in low
    return {"schema": "schedule/1", "platform": platform, "installed": installed,
            "detail": detail}


def reports_doc(rows: list[tuple[Profile, str, str]], skipped: list[dict[str, Any]]
                ) -> dict[str, Any]:
    return {"schema": "reports/1",
            "reports": [{"profile_id": p.id, "label": p.label, "format": fmt, "path": path}
                        for p, fmt, path in rows],
            "skipped": skipped}


def run_doc(rep: RunReport, *, scan_only: bool, headless: bool, exit_code: int,
            skipped: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "run/1",
        "dry_run": rep.dry_run,
        "scan_only": scan_only,
        "headless": headless,
        "exit_code": exit_code,
        "profiles": [{
            "profile_id": pid,
            "label": rep.labels.get(pid, pid[:8]),
            "states": {k.value: v for k, v in sorted(counts.items(), key=lambda kv: kv[0].value)},
            "tiers": {t.value: n for t, n in sorted(rep.tiers.get(pid, {}).items())},
        } for pid, counts in rep.per_profile.items()],
        "needs_human": rep.needs_human,
        "errors": rep.errors,
        "skipped_not_due": rep.skipped_not_due,
        "skipped_profiles": rep.skipped_profiles,
        "submitted": rep.submitted,
        "queued_emails": rep.queued_emails,
        "drafted_emails": rep.drafted_emails,
        "open_todos": rep.open_todos,
        "skipped": skipped,
        "summary": rep.summary_lines(),
    }


def secrets_doc(backend: str, configured: str | None, usable: bool,
                keychain_available: bool) -> dict[str, Any]:
    """Backend names only; never a key, passphrase, path contents or password."""
    return {"schema": "secrets/1", "backend": backend, "configured": configured,
            "usable": usable, "keychain_available": keychain_available}


def failure_doc(code: int, reason: str) -> dict[str, Any]:
    """What `run --headless --json` prints when it fails closed before running."""
    return {"schema": "error/1", "exit_code": code, "reason": reason}


def exposure_doc(rows: list[tuple[Profile, ExposureResult]], *, offline: bool,
                 headless: bool, exit_code: int,
                 skipped: list[dict[str, Any]]) -> dict[str, Any]:
    """`freemyid exposure --json` (docs/CLI.md, docs/EXPOSURE.md). Listing and check URLs
    are shown because the human output shows them too (they are what the person opens)."""
    return {
        "schema": "exposure/1",
        "offline": offline,
        "headless": headless,
        "exit_code": exit_code,
        "profiles": [{
            "profile_id": p.id,
            "label": p.label,
            "created_at": _ts(r.created_at),
            "practice_mode": r.practice_mode,
            "score": r.score,
            "explanation": [{"points": ln.points, "text": ln.text} for ln in r.explanation],
            "counts": {"confirmed_sites": r.confirmed_sites, "possible_sites": r.possible_sites,
                       "check_by_hand": len(r.by_status("check_by_hand")),
                       "not_found": len(r.by_status("not_found"))},
            "entries": [{
                "broker_id": e.broker_id,
                "broker_name": e.broker_name,
                "status": e.status,
                "reason": e.reason,
                "match_level": e.match_level.value if e.match_level else None,
                "signals": e.signals,
                "from_store": e.from_store,
                "checked_at": _ts(e.checked_at),
                "check_url": e.check_url,
                "listings": [{"url": li.url, "match_level": li.match_level.value,
                              "signals": li.signals, "contact_shown": li.contact_shown,
                              "relatives_shown": li.relatives_shown} for li in e.listings],
            } for e in r.entries],
        } for p, r in rows],
        "skipped": skipped,
    }
