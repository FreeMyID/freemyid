"""Import contactable data brokers from the state data-broker registries (PLAN D8).

Deterministic and re-runnable. Reads downloaded registry exports (inputs, never committed) and
(re)writes one generated block at the end of brokers/registry.yaml between the BEGIN/END markers.
Curated entries above the block always win and are never edited.

    PYTHONPATH=src .venv/bin/python tools/import_registries.py                 # dry run (default)
    PYTHONPATH=src .venv/bin/python tools/import_registries.py --write
    PYTHONPATH=src .venv/bin/python tools/import_registries.py --fetch-ca      # download CA CSV
    ... --ca FILE --vt FILE --tx FILE --or FILE --dir DIR --registry FILE

Sources (access status checked 2026-11-12; see docs/research/registries/README.md in a checkout):
- ca  California CPPA: official bulk CSV, https://cppa.ca.gov/data_broker_registry/registry.csv
      (fetchable with --fetch-ca; plain HTTP GET, no bot protection).
- vt  Vermont SOS (bizfilings.vermont.gov/online/DatabrokerInquire/): Angular single-page app,
      search-by-name only (min. 2 characters), no bulk download. Needs a person in a browser.
- tx  Texas SOS: the registry lives in an Appian portal (texas-sos.appianportalsgov.com/
      data-broker-registry), a JavaScript app; the SOS pages answer 403 to scripted clients.
- or  Oregon DFR/DCBS: search-only licensing portal (ordcbs.mylicense.com / mylicsearch),
      interactive form, no bulk download.
For vt/tx/or this tool does NOT scrape or work around anything. It only parses a CSV/TSV export
that a person saved from the public search (or a state-supplied file). Column names are matched
loosely (see FIELD_NEEDLES); unknown columns are ignored.

Rules (unchanged from import_ca_registry.py):
- The email must be on the broker's own registrable domain (same as its website).
- The mailbox local part must look like a role/privacy mailbox, never one person's inbox.
- https only for the privacy/opt-out page, and it must be on the broker's own domain, or on a
  known privacy-request portal vendor (PRIVACY_PORTALS: OneTrust, TrustArc, Transcend, ...).
  The portal host is added to the entry's `domains` so NetPolicy allows it for that broker only.
- No email but a usable privacy-request page: method web_form, verification_status unverified.
- Dedupe across sources and against curated entries by registrable domain and by name/DBA/parent.
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "brokers" / "registry.yaml"
DEFAULT_DIR = ROOT / "docs" / "research" / "registries"
BEGIN = "# ---- BEGIN generated: registry import (tools/import_registries.py) ----\n"
END = "# ---- END generated: registry import ----\n"
# Older tool versions wrote these (indented). Recognized so a re-run replaces them.
OLD_MARKERS = (
    ("  # ---- BEGIN generated: CA registry import (tools/import_ca_registry.py) ----\n",
     "  # ---- END generated: CA registry import ----\n"),
)
CA_CSV_URL = "https://cppa.ca.gov/data_broker_registry/registry.csv"

# source key -> (label for notes, citation URL, registered flag field or None)
SOURCES: dict[str, tuple[str, str, str | None]] = {
    "ca": ("California CPPA", CA_CSV_URL, "ca_registered"),
    "vt": ("Vermont SOS", "https://bizfilings.vermont.gov/online/DatabrokerInquire/",
           "vt_registered"),
    "tx": ("Texas SOS", "https://texas-sos.appianportalsgov.com/data-broker-registry", None),
    "or": ("Oregon DFR", "https://dfr.oregon.gov/business/licensing/data-broker-registry", None),
}
SOURCE_ORDER = tuple(SOURCES)

ROLE_WORDS = ("privacy", "dpo", "legal", "compliance", "optout", "opt-out", "opt_out", "dsar",
              "consumer", "rights", "ccpa", "gdpr", "dataprotection", "data-protection",
              "data.protection", "datarequest", "request", "support", "help", "care", "customer",
              "info", "contact", "unsubscribe", "remove", "removal", "delete", "suppression",
              "trust", "member", "service")
PEOPLE_WORDS = ("people", "person", "search", "records", "background", "lookup", "finder",
                "check", "whois", "phone", "reverse")
TWO_LEVEL_TLDS = {"co.uk", "com.au", "co.jp", "com.br", "co.in", "co.nz", "com.mx"}
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+\.)+[A-Za-z]{2,}$")
HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")
NO_VALUE = {"", "n/a", "na", "none", "null", "-"}
NAME_NOISE = {"inc", "incorporated", "llc", "llp", "lp", "ltd", "limited", "corp", "corporation",
              "co", "company", "the", "plc", "gmbh", "holdings", "group", "usa", "us"}

# Loose header matching: normalized header (lowercase alphanumerics) containing any needle.
# `not` lists substrings that disqualify a header. First match in header order wins per field.
FIELD_NEEDLES: dict[str, dict[str, tuple[str, ...]]] = {
    "name": {"any": ("databrokername", "legalname", "businessname", "entityname", "brokername",
                     "registrantname", "companyname", "organizationname", "name"),
             "not": ("dba", "doingbusiness", "tradename", "contact", "other", "assumed",
                     "parent", "agent", "officer", "person")},
    "dba": {"any": ("doingbusinessas", "dba", "tradename", "othernames", "assumedname",
                    "alternatename"), "not": ()},
    "website": {"any": ("primarywebsite", "website", "webaddress", "internetaddress", "url"),
                "not": ("details", "exercise", "optout", "privacy", "rights", "request")},
    "privacy_url": {"any": ("exercise", "optout", "privacyrequest", "privacyurl", "privacypolicy",
                            "consumerrights", "requesturl", "details"), "not": ()},
    "email": {"any": ("email",), "not": ()},
    "year": {"any": ("registrationyear", "registrationdate", "effectivedate", "filingdate",
                     "dateregistered", "issuedate", "year"), "not": ()},
}


# Vendors that host consumer privacy-request (DSAR) portals for many companies. A registry
# listing whose privacy page is on one of these is still the broker's own request channel.
# Emails are never accepted off-domain, portal or not.
PRIVACY_PORTALS = frozenset({
    "onetrust.com", "trustarc.com", "transcend.io", "datagrail.io", "securiti.ai",
    "osano.com", "ketch.com",
})


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
    try:
        h = urlsplit(url).hostname
    except ValueError:
        return None
    if not h or not HOST_RE.match(h.lower()):
        return None
    return h.lower()


def name_key(name: str) -> str:
    words = [w for w in re.sub(r"[^a-z0-9]+", " ", name.lower()).split() if w not in NAME_NOISE]
    key = " ".join(words)
    return key if len(key) >= 4 else ""


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


@dataclass
class Record:
    """Common record every source parser produces."""
    source: str
    name: str
    dbas: list[str] = field(default_factory=list)
    website: str = ""
    privacy_url: str = ""
    email: str = ""
    year: int | None = None

    @property
    def sites(self) -> list[str]:
        """Registry cells sometimes list several sites ("a.com; b.com"). Valid hosts, in order."""
        hosts = (host_of(t) for t in re.split(r"[\s;,|]+", self.website) if t)
        return [h for h in hosts if h]

    @property
    def host(self) -> str | None:
        return (self.sites or [None])[0]

    @property
    def domain(self) -> str | None:
        h = self.host
        return reg_domain(h) if h else None

    @property
    def all_domains(self) -> set[str]:
        return {reg_domain(h) for h in self.sites}

    def name_keys(self) -> set[str]:
        return {k for k in (name_key(n) for n in [self.name, *self.dbas]) if k}


def _norm(h: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", h.lower())


def _clean(v: str) -> str:
    v = v.strip()
    return "" if v.lower() in NO_VALUE else v


def _year(v: str) -> int | None:
    m = re.search(r"\b(19|20)\d{2}\b", v)
    return int(m.group(0)) if m else None


def _pick_columns(headers: list[str]) -> dict[str, int]:
    norm = [_norm(h) for h in headers]
    cols: dict[str, int] = {}
    for fld, spec in FIELD_NEEDLES.items():
        for needle in spec["any"]:
            hit = next((i for i, h in enumerate(norm) if needle in h
                        and not any(x in h for x in spec["not"]) and i not in cols.values()),
                       None)
            if hit is not None:
                cols[fld] = hit
                break
    return cols


def parse_table(text: str, source: str) -> tuple[list[Record], int]:
    """Parse a CSV/TSV export into common records. Returns (records, data row count)."""
    text = text.lstrip("﻿")
    first = text.split("\n", 1)[0]
    delim = max((",", "\t", ";"), key=first.count)
    rows = [r for r in csv.reader(io.StringIO(text), delimiter=delim) if any(c.strip() for c in r)]
    # Header = first of the first 5 rows that has a name column and some contact column.
    for hi, row in enumerate(rows[:5]):
        cols = _pick_columns(row)
        if "name" in cols and ({"website", "email"} & set(cols)):
            break
    else:
        return [], max(len(rows) - 1, 0)
    records: list[Record] = []
    for r in rows[hi + 1:]:
        def get(f: str, r: list[str] = r) -> str:
            i = cols.get(f)
            return _clean(r[i]) if i is not None and i < len(r) else ""
        name = get("name")
        if not name:
            continue
        dbas = [d.strip() for d in re.split(r"[;|]", get("dba")) if _clean(d)]
        records.append(Record(source=source, name=name, dbas=dbas, website=get("website"),
                              privacy_url=get("privacy_url"), email=get("email").lower(),
                              year=_year(get("year"))))
    return records, len(rows) - hi - 1


def parse_ca(text: str) -> tuple[list[Record], int]:
    # CPPA's current CSV is a single header row; the 2025 file had two. Both work.
    return parse_table(text, "ca")


def parse_vt(text: str) -> tuple[list[Record], int]:
    return parse_table(text, "vt")


def parse_tx(text: str) -> tuple[list[Record], int]:
    return parse_table(text, "tx")


def parse_or(text: str) -> tuple[list[Record], int]:
    return parse_table(text, "or")


PARSERS = {"ca": parse_ca, "vt": parse_vt, "tx": parse_tx, "or": parse_or}


def usable_contact(rec: Record) -> tuple[str | None, str | None, str]:
    """Return (email, https privacy url, skip_reason) after the safety rules."""
    host = rec.host
    if not host:
        return None, None, "bad_site"
    dom = reg_domain(host)
    email = None
    why = "no_contact"
    if rec.email:
        if not EMAIL_RE.match(rec.email):
            why = "no_email"
        elif reg_domain(rec.email.split("@", 1)[1]) not in {reg_domain(h) for h in rec.sites}:
            why = "off_domain"
        elif not any(w in rec.email.split("@", 1)[0] for w in ROLE_WORDS):
            why = "personal"
        else:
            email = rec.email
    url = None
    if rec.privacy_url.lower().startswith("https://"):
        ph = host_of(rec.privacy_url)
        path = urlsplit(rec.privacy_url.strip()).path
        # A bare homepage is not a privacy-request page.
        if ph and (reg_domain(ph) == dom or reg_domain(ph) in PRIVACY_PORTALS) \
                and path.strip("/"):
            url = rec.privacy_url.strip()
    return email, url, ("" if (email or url) else why)


# ---------------------------------------------------------------- curated index / clustering
def split_generated(text: str) -> str:
    """Return the file text without any previously generated block."""
    pairs = ((BEGIN, END), *OLD_MARKERS)
    for b, e in pairs:
        if b in text and e in text:
            text = text[:text.index(b)] + text[text.index(e) + len(e):]
    return text


@dataclass
class CuratedIndex:
    domains: set[str] = field(default_factory=set)
    names: set[str] = field(default_factory=set)
    ids: set[str] = field(default_factory=set)
    count: int = 0


def index_curated(brokers: list[dict]) -> CuratedIndex:
    ix = CuratedIndex(count=len(brokers))
    for b in brokers:
        ix.ids.add(b["id"])
        for d in b.get("domains", []):
            ix.domains.add(reg_domain(d))
        for u in (b.get("url"), b.get("opt_out_url")):
            h = host_of(u or "")
            if h:
                ix.domains.add(reg_domain(h))
        for n in (b.get("name"), b.get("parent_company")):
            k = name_key(n or "")
            if k:
                ix.names.add(k)
    return ix


def _cluster(records: list[Record]) -> list[list[Record]]:
    parent = list(range(len(records)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen: dict[str, int] = {}
    for i, r in enumerate(records):
        toks = [f"d:{d}" for d in sorted(r.all_domains)]
        toks += [f"n:{k}" for k in r.name_keys()]
        for t in toks:
            if t in seen:
                parent[find(i)] = find(seen[t])
            else:
                seen[t] = i
    groups: dict[int, list[Record]] = {}
    for i, r in enumerate(records):
        groups.setdefault(find(i), []).append(r)
    return list(groups.values())


def _in_curated(rec: Record, ix: CuratedIndex) -> bool:
    return bool(rec.all_domains & ix.domains or rec.name_keys() & ix.names)


@dataclass
class Stats:
    rows: int = 0
    usable: int = 0
    dup_curated: int = 0
    dup_cross: int = 0
    new: int = 0
    skipped: dict[str, int] = field(default_factory=dict)


def build_entries(records: list[Record], ix: CuratedIndex, stats: dict[str, Stats],
                  ) -> list[dict]:
    """Cluster records, drop those matching curated entries, build one entry per new cluster."""
    for r in records:
        e, u, why = usable_contact(r)
        if e or u:
            stats[r.source].usable += 1
    clusters = _cluster(records)
    used = set(ix.ids)
    built: list[tuple[str, dict]] = []
    for grp in clusters:
        grp.sort(key=lambda r: (SOURCE_ORDER.index(r.source), r.name.lower()))
        if any(_in_curated(r, ix) for r in grp):
            for r in grp:
                stats[r.source].dup_curated += 1
            continue
        # Best contact: first record (source order) with each usable piece.
        email = url = None
        lead = None
        for r in grp:
            e, u, _ = usable_contact(r)
            if e and not email:
                email, lead = e, lead or r
            if u and not url:
                url, lead = u, lead or r
        if not (email or url):
            for r in grp:
                _, _, why = usable_contact(r)
                if not r.website:
                    why = "no_website"
                stats[r.source].skipped[why] = stats[r.source].skipped.get(why, 0) + 1
            continue
        assert lead is not None
        for n, r in enumerate(grp):
            if n == 0:
                stats[r.source].new += 1
            else:
                stats[r.source].dup_cross += 1
        built.append((lead.domain or "", _entry(grp, lead, email, url)))
    built.sort(key=lambda t: (t[0], t[1]["name"].lower()))
    out = []
    for dom, entry in built:
        entry["id"] = make_id(dom, used)
        out.append({"id": entry.pop("id"), **entry})
    return out


def _entry(grp: list[Record], lead: Record, email: str | None, url: str | None) -> dict:
    host = lead.host or ""
    dom = reg_domain(host)
    dba = next((d for r in grp for d in r.dbas if d and d.upper() not in ("N/A", "NA", "NONE")),
               "")
    label = (dba or lead.name).rstrip(" ,.")
    domains = {host, dom}
    if email:
        domains.add(email.split("@", 1)[1])
    if url:
        domains.add(host_of(url) or host)
    srcs = [s for s in SOURCE_ORDER if any(r.source == s for r in grp)]
    listed = ", ".join(
        SOURCES[s][0] + "".join(f" {y}" for y in sorted(
            {r.year for r in grp if r.source == s and r.year}))
        for s in srcs)
    entry: dict = {
        "name": label,
        "url": f"https://{host}/",
        "category": "people_search" if any(w in dom for w in PEOPLE_WORDS) else "data_broker",
        "domains": sorted(d for d in domains if d),
        "method": "email" if email else "web_form",
    }
    if email:
        entry["opt_out_email"] = email
    if url:
        entry["opt_out_url"] = url
    entry["legal_basis_notes"] = f"Listed on state data broker registries: {listed}."
    for s in srcs:
        flag = SOURCES[s][2]
        if flag:
            entry[flag] = True
    entry.update({
        "typical_processing_days": 45,
        "recheck_interval_days": 90,
        "source_urls": [SOURCES[s][1] for s in srcs],
        "verification_status": "unverified",
        "verification_notes": (
            f"Registry contact field ({listed}), imported by tools/import_registries.py; "
            + ("not confirmed as a deletion-request address." if email else
               "privacy-request page from the registry listing; not opened or confirmed.")),
        "priority": 20,
    })
    return entry


# ---------------------------------------------------------------- driver
def render_block(entries: list[dict], sources_used: list[str]) -> str:
    body = (yaml.safe_dump(entries, sort_keys=False, allow_unicode=True, width=100)
            if entries else "")
    note = (f"# Sources: {', '.join(SOURCES[s][0] for s in sources_used)}. "
            "Do not edit by hand; re-run the tool.\n")
    return BEGIN + note + body + END


def discover(directory: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for key in SOURCE_ORDER:
        files = sorted(p for p in directory.glob(f"{key}_*") if p.suffix.lower() in
                       (".csv", ".tsv", ".txt"))
        if files:
            found[key] = files[-1]
    return found


def run(inputs: dict[str, Path], registry: Path, write: bool, out=sys.stdout) -> dict:
    text = split_generated(registry.read_text(encoding="utf-8"))
    ix = index_curated(yaml.safe_load(text)["brokers"])
    stats = {k: Stats() for k in SOURCE_ORDER}
    records: list[Record] = []
    for key in SOURCE_ORDER:
        if key not in inputs:
            continue
        recs, rows = PARSERS[key](inputs[key].read_text(encoding="utf-8", errors="replace"))
        stats[key].rows = rows
        records += recs
    entries = build_entries(records, ix, stats)
    used = [k for k in SOURCE_ORDER if k in inputs]
    print(f"{'source':6} {'rows':>5} {'usable':>6} {'dup_curated':>11} {'dup_cross':>9} "
          f"{'new':>5}", file=out)
    for k in SOURCE_ORDER:
        s = stats[k]
        tag = "" if k in inputs else "  (no input file)"
        print(f"{k:6} {s.rows:5} {s.usable:6} {s.dup_curated:11} {s.dup_cross:9} {s.new:5}"
              f"{tag}", file=out)
        if s.skipped:
            print(f"       skipped: {dict(sorted(s.skipped.items()))}", file=out)
    web = sum(1 for e in entries if e["method"] == "web_form")
    print(f"curated {ix.count}, new {len(entries)} (email {len(entries) - web}, web_form {web}), "
          f"projected total {ix.count + len(entries)}", file=out)
    if write:
        block = render_block(entries, used)
        registry.write_text(text.rstrip("\n") + "\n\n" + block, encoding="utf-8")
        print(f"wrote {registry}", file=out)
    else:
        print("dry run: nothing written (use --write)", file=out)
    return {"stats": stats, "entries": entries, "curated": ix.count}


def fetch_ca(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(CA_CSV_URL, headers={
        "User-Agent": "FreeMyID-registry-research (+https://freemyid.org)"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    path = directory / f"ca_cppa_registry_{date.today().isoformat()}.csv"
    path.write_bytes(data)
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    for k in SOURCE_ORDER:
        ap.add_argument(f"--{k}", type=Path, help=f"{SOURCES[k][0]} export (CSV/TSV)")
    ap.add_argument("--dir", type=Path, default=DEFAULT_DIR,
                    help="folder searched for ca_*, vt_*, tx_*, or_* files")
    ap.add_argument("--registry", type=Path, default=CURATED)
    ap.add_argument("--fetch-ca", action="store_true", help="download the CA CSV into --dir")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="default")
    mode.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    if a.fetch_ca:
        print(f"fetched {fetch_ca(a.dir)}")
    inputs = discover(a.dir) if a.dir.is_dir() else {}
    for k in SOURCE_ORDER:
        if getattr(a, k):
            inputs[k] = getattr(a, k)
    if not inputs:
        ap.error("no input files; use --fetch-ca or --ca/--vt/--tx/--or")
    run(inputs, a.registry, write=a.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
