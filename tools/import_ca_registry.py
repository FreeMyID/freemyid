"""Import email-contactable brokers from the California CPPA data broker registry CSV (PLAN D8).

Deterministic and re-runnable. It (re)writes the generated block at the end of
brokers/registry.yaml between the BEGIN/END markers. Curated entries above the block always win.

    .venv/bin/python tools/import_ca_registry.py path/to/registry2025.csv

Rules:
- The email must be on the broker's own registrable domain (same as its website).
- The mailbox local part must look like a role/privacy mailbox, never one person's inbox.
- Skip any broker whose domain is already in the curated registry.
"""
from __future__ import annotations

import csv
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "brokers" / "registry.yaml"
BEGIN = "  # ---- BEGIN generated: CA registry import (tools/import_ca_registry.py) ----\n"
END = "  # ---- END generated: CA registry import ----\n"
SOURCE = "https://cppa.ca.gov/data_broker_registry/registry2025.csv"

ROLE_WORDS = ("privacy", "dpo", "legal", "compliance", "optout", "opt-out", "opt_out", "dsar",
              "consumer", "rights", "ccpa", "gdpr", "dataprotection", "data-protection",
              "data.protection", "datarequest", "request", "support", "help", "care", "customer",
              "info", "contact", "unsubscribe", "remove", "removal", "delete", "suppression",
              "trust", "member", "service")
PEOPLE_WORDS = ("people", "person", "search", "records", "background", "lookup", "finder",
                "check", "whois", "phone", "reverse")
TWO_LEVEL_TLDS = {"co.uk", "com.au", "co.jp", "com.br", "co.in", "co.nz", "com.mx"}
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+\.)+[A-Za-z]{2,}$")


def reg_domain(host: str) -> str:
    parts = host.lower().strip(".").split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in TWO_LEVEL_TLDS:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def host_of(url: str) -> str | None:
    url = url.strip()
    if not url:
        return None
    if "://" not in url:
        url = "https://" + url
    h = urlsplit(url).hostname
    return h.lower() if h and "." in h else None


def make_id(dom: str, used: set[str]) -> str:
    stem = re.sub(r"[^a-z0-9]+", "_", dom.rsplit(".", 1)[0]).strip("_")
    if stem[:1].isdigit():
        stem = "x" + stem
    base, n = stem[:60], 2
    cid = base
    while cid in used:
        cid, n = f"{base}_{n}", n + 1
    used.add(cid)
    return cid


def main(csv_path: str) -> None:
    text = CURATED.read_text()
    if BEGIN in text:
        text = text[:text.index(BEGIN)] + text[text.index(END) + len(END):]
    curated = yaml.safe_load(text)["brokers"]
    taken_doms = {reg_domain(d) for b in curated for d in b.get("domains", [])}
    used_ids = {b["id"] for b in curated}
    with open(csv_path, encoding="utf-8-sig", errors="replace") as f:
        rows = list(csv.reader(f))[2:]
    out, skipped = [], {"no_email": 0, "bad_site": 0, "off_domain": 0, "personal": 0, "dup": 0}
    for r in rows:
        r = r + [""] * (15 - len(r))
        name, dba, site, email, rights_url = (r[0].strip(), r[1].strip(), r[2].strip(),
                                              r[3].strip().lower(), r[14].strip())
        if not email or not EMAIL_RE.match(email):
            skipped["no_email"] += 1
            continue
        host = host_of(site)
        if not host:
            skipped["bad_site"] += 1
            continue
        dom = reg_domain(host)
        local, ehost = email.split("@", 1)
        if reg_domain(ehost) != dom:
            skipped["off_domain"] += 1
            continue
        if not any(w in local for w in ROLE_WORDS):
            skipped["personal"] += 1
            continue
        if dom in taken_doms:
            skipped["dup"] += 1
            continue
        taken_doms.add(dom)
        domains = sorted({host, dom, ehost})
        label = dba if dba and dba.upper() not in ("N/A", "NA", "NONE") else name
        entry = {
            "id": make_id(dom, used_ids),
            "name": label.rstrip(" ,."),
            "url": f"https://{host}/",
            "category": "people_search" if any(w in dom for w in PEOPLE_WORDS) else "data_broker",
            "domains": domains,
            "method": "email",
            "opt_out_email": email,
            "ca_registered": True,
            "typical_processing_days": 45,
            "recheck_interval_days": 90,
            "source_urls": [SOURCE],
            "verification_status": "unverified",
            "verification_notes": f"CA data broker registry contact field, imported "
                                  f"{date.today().isoformat()} by tools/import_ca_registry.py; "
                                  "not confirmed as a deletion-request address.",
            "priority": 20,
        }
        rh = host_of(rights_url)
        if rh and reg_domain(rh) == dom and rights_url.lower().startswith("https://"):
            entry["opt_out_url"] = rights_url
            if rh not in entry["domains"]:
                entry["domains"] = sorted({*entry["domains"], rh})
        out.append(entry)
    body = yaml.safe_dump(out, sort_keys=False, allow_unicode=True, width=100)
    body = "".join("  " + ln + "\n" if ln else "\n" for ln in body.splitlines())
    note = (f"  # Source: {SOURCE}, imported {date.today().isoformat()}. "
            "Do not edit by hand; re-run the tool.\n")
    CURATED.write_text(text.rstrip("\n") + "\n\n" + BEGIN + note + body + END)
    print(f"imported {len(out)}; skipped {skipped}")


if __name__ == "__main__":
    main(sys.argv[1])
