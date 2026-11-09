#!/usr/bin/env python3
"""Block secret-file probes at the Cloudflare edge for freemyid.org (Free plan custom WAF rule).

Why: scanners request thousands of paths like /.env, /backup.sql, /terraform.tfstate. The site is
static (GitHub Pages) and has none of them, so each probe only fetches our 20 KB 404 page from the
origin. One custom rule blocks them at the edge. Patterns never match a real site path:
tests/test_cloudflare_waf_probes.py checks every file in web/dist.

Usage:  tools/cloudflare_waf_probes.py            show the current rule (read only)
        tools/cloudflare_waf_probes.py --apply    back up, then create or update the rule
        tools/cloudflare_waf_probes.py --rollback FILE   restore the saved ruleset rules
        add --create to --apply only when the zone has no custom-rules entrypoint yet
Token: ~/.config/freemyid/cf_token (chmod 600), never printed. Only the
http_request_firewall_custom phase of this one zone is touched, and only the rule with REF.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cloudflare_headers as cf

PHASE = "http_request_firewall_custom"
REF = "freemyid_block_secret_probes"
PREFIXES = ("/wp-", "/actuator", "/vendor/", "/config/", "/.")
SUFFIXES = (".sql", ".bak", ".old", ".save", ".tfstate", ".tfvars", ".env", ".ini", ".php",
            ".yml", ".yaml", ".toml", ".properties", ".rb", ".py", ".config", ".dist", ".inc",
            ".db", "~")
ALLOW_PREFIX = "/.well-known/"


def is_probe(path: str) -> bool:
    """Python mirror of the edge expression (used by the tests)."""
    p = path.lower()
    if p.startswith(ALLOW_PREFIX):
        return False
    return p.startswith(PREFIXES) or p.endswith(SUFFIXES)


def expression() -> str:
    v = "lower(http.request.uri.path)"
    parts = [f'starts_with({v}, "{s}")' for s in PREFIXES]
    parts += [f'ends_with({v}, "{s}")' for s in SUFFIXES]
    return f'(({" or ".join(parts)}) and not starts_with({v}, "{ALLOW_PREFIX}"))'


def rule() -> dict:
    return {"ref": REF, "action": "block", "enabled": True, "expression": expression(),
            "description": "Block secret-file probes (static site has none of these paths)"}


def entrypoint(zone_id: str) -> dict:
    return cf.api("GET", f"/zones/{zone_id}/rulesets/phases/{PHASE}/entrypoint")


def main(argv: list[str]) -> int:
    z = cf.api("GET", f"/zones?name={cf.ZONE}")
    if not z.get("success") or not z["result"]:
        sys.exit(f"cannot read zone: {cf.errs(z)}")
    zid = z["result"][0]["id"]
    cur = entrypoint(zid)
    if not cur.get("success") and "--create" not in argv:
        # SEC-126: a failed read must never become "no rules", or --apply/--rollback would
        # PUT over every existing custom rule. Pass --create only when the zone has no
        # custom-rules entrypoint yet.
        print(f"cannot read the custom rules: {cf.errs(cur)}; nothing changed "
              "(use --create only if this zone has no custom rules yet)", file=sys.stderr)
        return 1
    rules = (cur.get("result") or {}).get("rules", []) if cur.get("success") else []
    if "--rollback" in argv:
        saved = json.loads(Path(argv[argv.index("--rollback") + 1]).read_text())
        res = cf.api("PUT", f"/zones/{zid}/rulesets/phases/{PHASE}/entrypoint",
                     {"rules": saved.get("rules", [])})
        print("rollback:", "ok" if res.get("success") else cf.errs(res))
        return 0 if res.get("success") else 1
    mine = [r for r in rules if r.get("ref") == REF]
    if "--apply" not in argv:
        print("rule present" if mine else "rule absent", f"({len(rules)} custom rules)")
        return 0
    backup = Path(cf.CFG) / f"cf_waf_custom_backup_{time.strftime('%Y%m%d-%H%M%S')}.json"
    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)   # never world-readable
    with os.fdopen(fd, "w") as f:
        json.dump({"rules": rules}, f, indent=2)
    keep = [{k: r[k] for k in ("ref", "action", "enabled", "expression", "description") if k in r}
            for r in rules if r.get("ref") != REF]
    res = cf.api("PUT", f"/zones/{zid}/rulesets/phases/{PHASE}/entrypoint",
                 {"rules": [*keep, rule()]})
    print("apply:", "ok" if res.get("success") else cf.errs(res), f"(backup {backup})")
    return 0 if res.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
