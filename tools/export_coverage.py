"""Export the public coverage list from the private broker registry.

    python tools/export_coverage.py [REGISTRY] [-o brokers/coverage.public.yaml] [--check]

The full registry (brokers/registry.yaml) is private. The coverage list is the part of it that is
safe to publish: which sites are on our list and how each one is handled. It feeds the website page
/brokers/ ("Sites we cover"). Orchestrator decision 2026-11-12: publish a coverage list, not the registry.

Every row is built field by field from an allowlist. Nothing is copied through, so a new field in
the registry can never reach the output. Exported per site, and nothing else:

    name      display name (text before " (" in the registry name, a trailing ", Inc." removed)
    site      hostname of the broker's main website (no scheme, no path, no "www.")
    category  people_search | background_check | phone_lookup | family_tree | data_broker |
              risk_data | other
    route     how Free My ID handles the site with default settings (see route_of)
    status    verified | not_verified | not_available (see status_of)
    checked   month of the last check, YYYY-MM (never the day); left out when there is none
    family    the parent's display name when covered_by is set, else parent_company; left out
              when there is none or it is the site's own name

Never exported: opt-out URLs, email addresses, phone numbers, postal addresses, form steps and
selectors, search patterns, required fields, verification notes, legal notes, source URLs, ids,
priorities, or anything from docs/research/.

Routes follow src/freemyid/engine/tiers.py (tier_for) for a person with a removal mailbox and
the default permissions (no ID upload, no account creation, no phone disclosure):

    automatic  the app fills in the site's form itself (tiers.automatic_eligible)
    email      the app sends the request by email (tiers.has_email_route)
    by_hand    the Assisted tier, where the site only takes a phone call, a letter or a request
               from inside the person's own account: the app shows the steps, the person does them
    assisted   the Assisted tier on a web form: the app opens the form and guides the person

A covered_by site gets its parent's route, as in tiers.submit_target.

Broken and switched-off entries (verification_status: broken, or enabled: false) are LISTED with
status not_available, so a reader who looks for that site gets an honest answer. They are counted
apart: counts.listed = verified + not_verified, and counts.total = listed + not_available.

Deterministic: rows are sorted by name, then site; no timestamps; same input, same bytes.
PyYAML only (to read the registry). The output is written by hand as one flow mapping per line.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = ROOT / "brokers" / "registry.yaml"
DEFAULT_OUT = ROOT / "brokers" / "coverage.public.yaml"

FORMAT = 1
FIELDS = ("name", "site", "category", "route", "status", "checked", "family")  # the allowlist, in file order
REQUIRED = ("name", "site", "category", "route", "status")
CATEGORIES = ("people_search", "background_check", "phone_lookup", "family_tree", "data_broker",
              "risk_data", "other")
ROUTES = ("automatic", "email", "assisted", "by_hand")
STATUSES = ("verified", "not_verified", "not_available")
COUNT_KEYS = ("total", "listed", "verified", "not_verified", "not_available")

_HOST = re.compile(r"[a-z0-9-]+(\.[a-z0-9-]+)+")
_MONTH = re.compile(r"\d{4}-(0[1-9]|1[0-2])")
# A name is a company or site name. Anything that looks like contact data or a link is refused.
_NOT_A_NAME = re.compile(r"@|://|\bwww\.|[\x00-\x1f\x7f]", re.IGNORECASE)
_INTERACTIVE = {"fill", "select", "check", "click", "submit"}  # tiers._INTERACTIVE_STEPS
_OWN_EFFORT = {"account_required", "phone", "postal"}
MAX_NAME = 80


class ExportError(ValueError):
    """The registry has a value that must not or cannot be published."""


def display_name(raw: object) -> str:
    """Same rule as the public guides (web/src/lib/site.ts displayName), plus whitespace clean-up."""
    text = re.sub(r"\s+", " ", str(raw or "")).strip()
    text = text.split(" (")[0].strip()
    return re.sub(r"[.,]? Inc\.?$", "", text).strip(" ,")


def _checked_name(raw: object, where: str) -> str:
    name = display_name(raw)
    if not name:
        raise ExportError(f"{where}: empty name")
    if _NOT_A_NAME.search(name):
        raise ExportError(f"{where}: name looks like contact data or a link, not a name")
    if len(name) > MAX_NAME:
        raise ExportError(f"{where}: name is longer than {MAX_NAME} characters")
    return name


def site_host(url: object, where: str) -> str:
    host = (urlsplit(str(url or "")).hostname or "").lower().rstrip(".").removeprefix("www.")
    if not _HOST.fullmatch(host):
        raise ExportError(f"{where}: url has no usable hostname")
    return host


def has_email_route(b: dict) -> bool:
    """tiers.has_email_route."""
    return bool(b.get("opt_out_email")) and (
        b.get("method") == "email" or "email" in (b.get("alt_methods") or []))


def automatic_eligible(b: dict) -> bool:
    """tiers.automatic_eligible for the default permissions with browser automation on."""
    form = b.get("form") or []
    actions = [step.get("action") for step in form if isinstance(step, dict)]
    required = b.get("required_fields") or []
    return (
        any(a in _INTERACTIVE for a in actions)
        and b.get("verification_status") == "verified"
        and not b.get("has_captcha")
        and b.get("method") != "account_required"
        and "human" not in actions
        and not b.get("needs_id_upload")
        and "phone" not in required
        and "id_document" not in required
    )


def route_of(target: dict) -> str:
    """Route for the broker that receives the request (the covered_by parent, else the site itself)."""
    if automatic_eligible(target):
        return "automatic"
    if has_email_route(target):
        return "email"
    if target.get("method") in _OWN_EFFORT:
        return "by_hand"
    return "assisted"


def _available(b: dict) -> bool:
    return b.get("enabled", True) is not False and b.get("verification_status") != "broken"


def status_of(b: dict, target: dict) -> str:
    """verified needs a check date, as on the guide pages. A site whose parent is unavailable is
    unavailable too, because the request goes to the parent."""
    if not _available(b) or not _available(target):
        return "not_available"
    if b.get("verification_status") == "verified" and b.get("last_verified"):
        return "verified"
    return "not_verified"


def checked_month(value: object, where: str) -> str | None:
    if not value:
        return None
    month = (value.isoformat() if hasattr(value, "isoformat") else str(value))[:7]
    if not _MONTH.fullmatch(month):
        raise ExportError(f"{where}: last_verified is not a date")
    return month


def build_rows(registry: dict) -> list[dict[str, str]]:
    brokers = registry.get("brokers")
    if not isinstance(brokers, list) or not brokers:
        raise ExportError("registry has no brokers")
    by_id: dict[str, dict] = {}
    for b in brokers:
        if not isinstance(b, dict) or not b.get("id"):
            raise ExportError("registry entry without an id")
        if b["id"] in by_id:
            raise ExportError(f"{b['id']}: duplicate id")
        by_id[str(b["id"])] = b
    rows: list[dict[str, str]] = []
    for bid, b in by_id.items():
        target = b
        if b.get("covered_by"):
            if b["covered_by"] not in by_id:
                raise ExportError(f"{bid}: covered_by names an unknown id")
            target = by_id[b["covered_by"]]
        category = b.get("category")
        if category not in CATEGORIES:
            raise ExportError(f"{bid}: unknown category")
        name = _checked_name(b.get("name"), bid)
        row = {"name": name, "site": site_host(b.get("url"), bid), "category": str(category),
               "route": route_of(target), "status": status_of(b, target)}
        month = checked_month(b.get("last_verified"), bid)
        if month:
            row["checked"] = month
        family_raw = target.get("name") if target is not b else b.get("parent_company")
        if family_raw:
            family = _checked_name(family_raw, f"{bid} (family)")
            if family.casefold() != name.casefold():
                row["family"] = family
        rows.append(row)
    rows.sort(key=lambda r: (r["name"].casefold(), r["site"], r["name"]))
    return rows


def count_rows(rows: list[dict[str, str]]) -> dict[str, int]:
    by_status = {s: sum(1 for r in rows if r["status"] == s) for s in STATUSES}
    listed = by_status["verified"] + by_status["not_verified"]
    return {"total": len(rows), "listed": listed, **by_status}


def _flow(pairs: list[tuple[str, object]]) -> str:
    # JSON strings are valid YAML double-quoted scalars; every text value is quoted.
    return "{" + ", ".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in pairs) + "}"


def render(registry: dict) -> str:
    rows = build_rows(registry)
    counts = count_rows(rows)
    updated = checked_month(registry.get("updated"), "registry updated") or ""
    lines = [
        "# Free My ID coverage list: the sites on our list and how each one is handled.",
        "# Public. Generated by tools/export_coverage.py from the private registry. Do not edit by hand.",
        "# Fields per site (nothing else is ever exported): " + ", ".join(FIELDS) + ".",
        "# route: " + " | ".join(ROUTES) + ".  status: " + " | ".join(STATUSES) + ".",
        "# counts.listed = verified + not_verified; not_available sites are listed but counted apart.",
        f"format: {FORMAT}",
        f"updated: {json.dumps(updated)}",
        "counts: " + _flow([(k, counts[k]) for k in COUNT_KEYS]),
        "sites:",
    ]
    lines += ["  - " + _flow([(k, r[k]) for k in FIELDS if k in r]) for r in rows]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Export the public coverage list from the private registry.")
    ap.add_argument("registry", nargs="?", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("-o", "--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--check", action="store_true",
                    help="write nothing; exit 1 if the output file differs from a fresh export")
    args = ap.parse_args(argv)
    if not args.registry.is_file():
        print(f"export_coverage: {args.registry} not found (the full registry is private)", file=sys.stderr)
        return 2
    try:
        text = render(yaml.safe_load(args.registry.read_text(encoding="utf-8")) or {})
    except ExportError as e:
        print(f"export_coverage: refused: {e}", file=sys.stderr)
        return 2
    counts = text.split("counts: ", 1)[1].split("\n", 1)[0]
    if args.check:
        same = args.out.is_file() and args.out.read_text(encoding="utf-8") == text
        print(f"export_coverage: {args.out.name} is {'up to date' if same else 'OUT OF DATE'} {counts}")
        return 0 if same else 1
    args.out.write_text(text, encoding="utf-8")
    print(f"export_coverage: wrote {args.out.name} {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
