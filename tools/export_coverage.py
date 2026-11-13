"""Export the public coverage list from the private broker registry.

    python tools/export_coverage.py [REGISTRY] [-o brokers/coverage.public.yaml] [--hold-back] [--check]

The full registry (brokers/registry.yaml) is private. The coverage list is the part of it that is
safe to publish: which sites are on our list and how each one is handled. It feeds the website page
/brokers/ ("Sites we cover"). Orchestrator decision 2026-11-12: publish a coverage list, not the registry.

Every row is built field by field from an allowlist. Nothing is copied through, so a new field in
the registry can never reach the output. Exported per site, and nothing else:

    name        display name (text before " (" in the registry name, a trailing ", Inc." removed)
    site        hostname of the broker's main website (no scheme, no path, no "www.")
    category    people_search | background_check | phone_lookup | family_tree | data_broker |
                risk_data | other
    route       how Free My ID handles the site with default settings (see route_of)
    status      verified | not_verified (see status_of)
    checked     month of the last check, YYYY-MM (never the day); left out when there is none
    registered  the states whose official data broker registry lists the company: "CA", "VT" or
                "CA,VT" (ca_registered, vt_registered); left out when neither flag is true
    family      the display name of the covered_by parent, whose removal also covers this site;
                left out when there is none or it is the site's own name

parent_company is NOT exported. The registry does not record where an ownership name came from
(the registry importers never set the field), so it cannot be shown as a fact from a filing
(orchestrator ruling 2026-11-13).

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

Broken and switched-off entries (verification_status: broken, or enabled: false), and sites whose
covered_by parent is one of those, are NOT named (orchestrator ruling 2026-11-13). They are left
out of the rows and only counted: counts.not_available. counts.listed is the number of rows
(verified + not_verified).

A display name shorter than 3 characters, or one that starts with "formerly", is refused: both have
been import mistakes ("No", "formerly FullContact"). A real short name keeps its legal suffix
("L2, Inc") instead of being cut to two characters. A name with an underscore is refused too: it is
an internal id, not a name ("datacloudoptout_oracle").

The `site` must be the company's main website, because a removal address is private. Refused:
a hostname that is itself a removal address (a label with "optout", "opt-out", "unsubscribe",
"suppression" or "donotsell", or a "privacy." / "dsar." host), and any hostname on a subdomain
(portal.example.com), which is how a removal form or consumer portal usually looks. Two ways
past the subdomain rule: the public sample registry already names the hostname (official tools
such as privacy.ca.gov), or a person confirmed it is the main site and added it to
MAIN_SITE_SUBDOMAINS below.

By default one refused entry stops the whole export, and the message lists every refused entry so
they can be fixed in the registry in one go. With --hold-back the refused entries are left out of
the list instead (not named, not counted) and printed, and the rest is exported. Use the same flag
with --check.

`updated` is the newer of the registry's own `updated` month and the newest check month in the
rows. Deterministic: rows are sorted by name, then site; no clock is read; same input, same bytes.
License of the output: CC BY-NC 4.0, credit "Free My ID" (brokers/LICENSE-DATA.md).
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

FORMAT = 2
# The allowlist, in file order.
FIELDS = ("name", "site", "category", "route", "status", "checked", "registered", "family")
REQUIRED = ("name", "site", "category", "route", "status")
CATEGORIES = ("people_search", "background_check", "phone_lookup", "family_tree", "data_broker",
              "risk_data", "other")
ROUTES = ("automatic", "email", "assisted", "by_hand")
STATUSES = ("verified", "not_verified")          # the statuses a row can have
NOT_AVAILABLE = "not_available"                  # counted, never listed
COUNT_KEYS = ("listed", "verified", "not_verified", "not_available")
REGISTRIES = (("ca_registered", "CA"), ("vt_registered", "VT"))   # registry flag -> state code

_HOST = re.compile(r"[a-z0-9-]+(\.[a-z0-9-]+)+")
_MONTH = re.compile(r"\d{4}-(0[1-9]|1[0-2])")
# A name is a company or site name. Anything that looks like contact data or a link is refused.
_NOT_A_NAME = re.compile(r"@|://|\bwww\.|[\x00-\x1f\x7f]", re.IGNORECASE)
# A hostname label that marks a removal address rather than a company's main site.
_REMOVAL_LABEL = re.compile(r"opt-?out|unsubscribe|suppress|do-?not-?sell|^privacy$|^dsar$")
SAMPLE_REGISTRY = ROOT / "brokers" / "registry.sample.yaml"
# Suffixes under which a company registers its own name, so "name.co.uk" is not a subdomain.
TWO_LABEL_SUFFIXES = frozenset({"co.uk", "org.uk", "com.au", "co.nz", "us.com"})
# Hostnames on a subdomain that a person confirmed are the company's main website (not a removal
# form or a portal). All of these were in the list the orchestrator approved on 2026-11-13.
MAIN_SITE_SUBDOMAINS = frozenset({"dashboard.propertyrecs.com", "risk.lexisnexis.com", "www2.arccorp.com"})
_INTERACTIVE = {"fill", "select", "check", "click", "submit"}  # tiers._INTERACTIVE_STEPS
_OWN_EFFORT = {"account_required", "phone", "postal"}
MIN_NAME, MAX_NAME = 3, 80


class ExportError(ValueError):
    """The registry has a value that must not or cannot be published."""


def display_name(raw: object) -> str:
    """Same rule as the public guides (web/src/lib/site.ts displayName), plus whitespace clean-up."""
    text = re.sub(r"\s+", " ", str(raw or "")).strip()
    text = text.split(" (")[0].strip(" ,")
    short = re.sub(r"[.,]? Inc\.?$", "", text).strip(" ,")
    return short if len(short) >= MIN_NAME else text   # "L2, Inc" stays whole; "L2" would be refused


def _checked_name(raw: object, where: str) -> str:
    name = display_name(raw)
    if not name:
        raise ExportError(f"{where}: empty name")
    if _NOT_A_NAME.search(name):
        raise ExportError(f"{where}: name looks like contact data or a link, not a name")
    if len(name) > MAX_NAME:
        raise ExportError(f"{where}: name is longer than {MAX_NAME} characters")
    if len(name) < MIN_NAME:
        raise ExportError(f"{where}: name is shorter than {MIN_NAME} characters (fix it in the registry)")
    if name.casefold().startswith("formerly"):
        raise ExportError(f"{where}: name starts with 'formerly' (fix it in the registry)")
    if "_" in name:
        raise ExportError(f"{where}: name has an underscore, so it is an id, not a name (fix it in the registry)")
    return name


def _host(url: object) -> str:
    return (urlsplit(str(url or "")).hostname or "").lower().rstrip(".").removeprefix("www.")


def site_host(url: object, where: str, public: frozenset[str] = frozenset()) -> str:
    """The main site's hostname. `public`: hostnames the public sample registry already names."""
    host = _host(url)
    if not _HOST.fullmatch(host):
        raise ExportError(f"{where}: url has no usable hostname")
    if host in public:
        return host
    labels = host.split(".")
    if any(_REMOVAL_LABEL.search(label) for label in labels):
        raise ExportError(f"{where}: url is a removal address, not the company's main site "
                          "(fix it in the registry)")
    own = 3 if ".".join(labels[-2:]) in TWO_LABEL_SUFFIXES else 2
    if len(labels) > own and host not in MAIN_SITE_SUBDOMAINS:
        raise ExportError(f"{where}: url is on a subdomain, which may be a removal form or a portal; use "
                          "the company's main site in the registry, or confirm this one and add it to "
                          "MAIN_SITE_SUBDOMAINS")
    return host


def sample_hosts(path: Path | None = None) -> frozenset[str]:
    """Main-site hostnames in the public sample registry: already public, so never a leak."""
    path = path or SAMPLE_REGISTRY
    if not path.is_file():
        return frozenset()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return frozenset(h for h in (_host(b.get("url")) for b in data.get("brokers") or []) if h)


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
        return NOT_AVAILABLE
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


def registered_in(b: dict) -> str | None:
    """State codes of the official data broker registries that list this company, e.g. "CA,VT"."""
    codes = [code for flag, code in REGISTRIES if b.get(flag) is True]
    return ",".join(codes) or None


def _row(bid: str, b: dict, by_id: dict[str, dict], public: frozenset[str]) -> dict[str, str] | None:
    """The public row for one registry entry; None when the site is not available (never named)."""
    target = b
    if b.get("covered_by"):
        if b["covered_by"] not in by_id:
            raise ExportError(f"{bid}: covered_by names an unknown id")
        target = by_id[b["covered_by"]]
    category = b.get("category")
    if category not in CATEGORIES:
        raise ExportError(f"{bid}: unknown category")
    status = status_of(b, target)
    if status == NOT_AVAILABLE:
        return None
    name = _checked_name(b.get("name"), bid)
    row = {"name": name, "site": site_host(b.get("url"), bid, public), "category": str(category),
           "route": route_of(target), "status": status}
    month = checked_month(b.get("last_verified"), bid)
    if month:
        row["checked"] = month
    registered = registered_in(b)
    if registered:
        row["registered"] = registered
    if target is not b:              # covered_by only; parent_company is never exported
        family = _checked_name(target.get("name"), f"{bid} (family)")
        if family.casefold() != name.casefold():
            row["family"] = family
    return row


def build(registry: dict, public: frozenset[str] = frozenset(), hold_back: bool = False,
          ) -> tuple[list[dict[str, str]], int, list[str]]:
    """(rows to publish, number of sites left out as not available, refusals).

    An entry with a value that must not be published is refused. Without `hold_back` any refusal
    raises ExportError naming all of them; with it they are left out and returned."""
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
    refused: list[str] = []
    not_available = 0
    for bid, b in by_id.items():
        try:
            row = _row(bid, b, by_id, public)
        except ExportError as e:
            refused.append(str(e))
            continue
        if row is None:
            not_available += 1
        else:
            rows.append(row)
    if refused and not hold_back:
        raise ExportError(f"{len(refused)} entr{'y' if len(refused) == 1 else 'ies'} refused:\n  "
                          + "\n  ".join(refused))
    if not rows:
        raise ExportError("no entry left to list")
    rows.sort(key=lambda r: (r["name"].casefold(), r["site"], r["name"]))
    return rows, not_available, refused


def build_rows(registry: dict, public: frozenset[str] = frozenset()) -> list[dict[str, str]]:
    return build(registry, public)[0]


def count_rows(rows: list[dict[str, str]], not_available: int = 0) -> dict[str, int]:
    by_status = {s: sum(1 for r in rows if r["status"] == s) for s in STATUSES}
    return {"listed": len(rows), **by_status, NOT_AVAILABLE: not_available}


def _flow(pairs: list[tuple[str, object]]) -> str:
    # JSON strings are valid YAML double-quoted scalars; every text value is quoted.
    return "{" + ", ".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in pairs) + "}"


def render(registry: dict, public: frozenset[str] = frozenset(), hold_back: bool = False,
           held: list[str] | None = None) -> str:
    """The file's text. With `hold_back`, refused entries are left out and appended to `held`."""
    rows, not_available, refused = build(registry, public, hold_back)
    if held is not None:
        held.extend(refused)
    counts = count_rows(rows, not_available)
    months = [r["checked"] for r in rows if "checked" in r]
    months += [m for m in [checked_month(registry.get("updated"), "registry updated")] if m]
    if not months:
        raise ExportError("no date: the registry has no `updated` and no row has a check date")
    lines = [
        "# Free My ID coverage list: the sites on our list and how each one is handled.",
        "# Public. Generated by tools/export_coverage.py from the private registry. Do not edit by hand.",
        '# License: CC BY-NC 4.0, credit "Free My ID" (brokers/LICENSE-DATA.md).',
        "# Fields per site (nothing else is ever exported): " + ", ".join(FIELDS) + ".",
        "# route: " + " | ".join(ROUTES) + ".  status: " + " | ".join(STATUSES) + ".",
        "# registered: states whose official data broker registry lists the company (CA, VT).",
        "# counts.listed = the rows below. counts.not_available = sites left out and not named,",
        "# because there is no working way to ask them for removal right now.",
        f"format: {FORMAT}",
        f"updated: {json.dumps(max(months))}",
        "counts: " + _flow([(k, counts[k]) for k in COUNT_KEYS]),
        "sites:",
    ]
    lines += ["  - " + _flow([(k, r[k]) for k in FIELDS if k in r]) for r in rows]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Export the public coverage list from the private registry.")
    ap.add_argument("registry", nargs="?", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("-o", "--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--hold-back", action="store_true",
                    help="leave refused entries out of the list (and print them) instead of stopping")
    ap.add_argument("--check", action="store_true",
                    help="write nothing; exit 1 if the output file differs from a fresh export")
    args = ap.parse_args(argv)
    if not args.registry.is_file():
        print(f"export_coverage: {args.registry} not found (the full registry is private)", file=sys.stderr)
        return 2
    held: list[str] = []
    try:
        text = render(yaml.safe_load(args.registry.read_text(encoding="utf-8")) or {}, sample_hosts(),
                      args.hold_back, held)
    except ExportError as e:
        print(f"export_coverage: refused: {e}", file=sys.stderr)
        return 2
    if held:
        print(f"export_coverage: held back {len(held)} (not in the list; fix them in the registry):\n  "
              + "\n  ".join(held), file=sys.stderr)
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
