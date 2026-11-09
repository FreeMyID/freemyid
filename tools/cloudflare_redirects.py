"""Stable download addresses on freemyid.org (Cloudflare Single Redirect rules).

  /get/windows -> GitHub releases/latest/download/FreeMyIDSetup.exe   (302)
  /get/linux   -> /developers/                                        (302, until a native package exists)
  /get/macos   -> /developers/                                        (302, until a native package exists)

Usage:  python tools/cloudflare_redirects.py [--apply] [--rollback]
  default     : dry run, prints the rules and the current state, changes nothing
  --apply     : merge our rules into the zone's redirect ruleset (other rules are kept)
  --rollback  : remove only our rules (those whose ref starts with "freemyid-get-")

Token: read from ~/.config/freemyid/cf_token (chmod 600), never printed.
Needs token permission: Zone > Single Redirect (a.k.a. "Zone Rulesets": Edit) on freemyid.org, plus Zone: Read.
Rollback by hand: Cloudflare dashboard > freemyid.org > Rules > Redirect Rules > delete the three "Free My ID get/*" rules.
"""
import http.client
import json
import os
import sys
import urllib.error
import urllib.request

ZONE = "freemyid.org"
PHASE = "http_request_dynamic_redirect"
PREFIX = "freemyid-get-"
GH = "https://github.com/FreeMyID/freemyid/releases/latest/download/FreeMyIDSetup.exe"
HOSTS = '(http.host eq "freemyid.org")'
RULES = [
    ("windows", "/get/windows", GH),
    ("linux", "/get/linux", "https://freemyid.org/developers/"),
    ("macos", "/get/macos", "https://freemyid.org/developers/"),
]


def token() -> str:
    p = os.path.expanduser("~/.config/freemyid/cf_token")
    if os.stat(p).st_mode & 0o077:
        sys.exit("cf_token must be chmod 600")
    return open(p).read().strip()


def api(method, path, body=None):
    req = urllib.request.Request("https://api.cloudflare.com/client/v4" + path, method=method,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + token(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except (ValueError, OSError, http.client.HTTPException):  # e.g. IncompleteRead
            return {"success": False, "errors": [{"message": f"HTTP {e.code}"}]}


def errs(r):
    return [e.get("message") for e in r.get("errors", [])]


def main():
    apply, rollback = "--apply" in sys.argv, "--rollback" in sys.argv
    z = api("GET", f"/zones?name={ZONE}")
    if not z.get("success") or not z["result"]:
        sys.exit(f"cannot read zone: {errs(z)} (needs Zone:Read)")
    zid = z["result"][0]["id"]
    cur = api("GET", f"/zones/{zid}/rulesets/phases/{PHASE}/entrypoint")
    if cur.get("success"):
        existing = cur["result"].get("rules", [])
    elif any("could not find" in (m or "").lower() for m in errs(cur)):
        existing = []
    else:
        sys.exit(f"cannot read redirect ruleset: {errs(cur)} (token needs Zone > Single Redirect: Edit)")
    keep = [r for r in existing if not str(r.get("ref", "")).startswith(PREFIX)]
    ours = [{
        "ref": PREFIX + name, "description": f"Free My ID get/{name}", "enabled": True, "action": "redirect",
        "expression": f'{HOSTS} and http.request.uri.path eq "{path}"',
        "action_parameters": {"from_value": {"status_code": 302, "preserve_query_string": False,
                                             "target_url": {"value": target}}},
    } for name, path, target in RULES]
    new = keep if rollback else keep + ours
    print(f"existing rules: {len(existing)} (kept: {len(keep)}); resulting rules: {len(new)}")
    if not (apply or rollback):
        print(json.dumps(ours, indent=1)); print("dry run; use --apply"); return
    r = api("PUT", f"/zones/{zid}/rulesets/phases/{PHASE}/entrypoint", {"rules": new})
    print("applied" if r.get("success") else f"FAILED: {errs(r)}")
    sys.exit(0 if r.get("success") else 1)


if __name__ == "__main__":
    main()
