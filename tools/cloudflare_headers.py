"""Add a Content-Security-Policy header (with frame-ancestors 'none') to the existing
Cloudflare response-header transform rule for freemyid.org (SEC-66 / BL-IN-41).

Usage: python tools/cloudflare_headers.py            dry run (prints the change, writes nothing)
       python tools/cloudflare_headers.py --apply    save a backup, then PUT the merged rule
       python tools/cloudflare_headers.py --rollback FILE   PUT the rules saved in FILE back

Token: ~/.config/freemyid/cf_token (chmod 600), never printed. Only the
http_response_headers_transform phase of this one zone is touched. The existing rule is edited in
place (CSP added to its headers); every other header and rule is preserved. HSTS is not changed.
The CSP mirrors the per-page meta CSP minus the per-page hashes; the built site has no inline
script or style (only JSON-LD data blocks), so no 'unsafe-inline' is needed.
"""
import copy
import json
import os
import sys
import time
import urllib.error
import urllib.request

ZONE = "freemyid.org"
PHASE = "http_response_headers_transform"
CSP = ("default-src 'self'; img-src 'self'; font-src 'self'; connect-src 'none'; object-src 'none'; "
       "frame-src 'none'; form-action 'none'; base-uri 'none'; script-src 'self'; style-src 'self'; "
       "frame-ancestors 'none'")
CFG = os.path.expanduser("~/.config/freemyid")


def token() -> str:
    p = os.path.join(CFG, "cf_token")
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
        except (ValueError, OSError):
            return {"success": False, "errors": [{"message": f"HTTP {e.code}"}]}


def errs(r):
    return [e.get("message") for e in r.get("errors", [])]


def main():
    apply = "--apply" in sys.argv
    z = api("GET", f"/zones?name={ZONE}")
    if not z.get("success") or not z["result"]:
        sys.exit(f"cannot read zone: {errs(z)}")
    path = f"/zones/{z['result'][0]['id']}/rulesets/phases/{PHASE}/entrypoint"
    if "--rollback" in sys.argv:
        with open(sys.argv[sys.argv.index("--rollback") + 1]) as f:
            saved = json.load(f)
        r = api("PUT", path, {"rules": saved})
        print("rolled back" if r.get("success") else f"FAILED: {errs(r)}")
        sys.exit(0 if r.get("success") else 1)
    cur = api("GET", path)
    if not cur.get("success"):
        sys.exit(f"cannot read ruleset: {errs(cur)}")
    old = cur["result"].get("rules", [])
    new = copy.deepcopy(old)
    hits = [r for r in new if "X-Frame-Options" in r.get("action_parameters", {}).get("headers", {})]
    if len(hits) != 1:
        sys.exit(f"expected exactly one rule setting X-Frame-Options, found {len(hits)}; not changing anything")
    hits[0]["action_parameters"]["headers"]["Content-Security-Policy"] = {"operation": "set", "value": CSP}
    for r in old:
        print("existing rule:", r.get("description"), "headers:", sorted(r.get("action_parameters", {}).get("headers", {})))
    if not apply:
        print("dry run; would add Content-Security-Policy:", CSP)
        return
    os.makedirs(CFG, exist_ok=True)
    bak = os.path.join(CFG, f"cf_headers_backup_{time.strftime('%Y%m%d-%H%M%S')}.json")
    fd = os.open(bak, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(old, f)
    print("backup saved:", bak)
    r = api("PUT", path, {"rules": new})
    print("applied" if r.get("success") else f"FAILED: {errs(r)}")
    sys.exit(0 if r.get("success") else 1)


if __name__ == "__main__":
    main()
