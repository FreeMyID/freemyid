"""Read/set the Cloudflare zone setting email_obfuscation for freemyid.org (SEC-66 follow-up).

Usage: python tools/cloudflare_email_obfuscation.py              print current value
       python tools/cloudflare_email_obfuscation.py --apply      back up the value, then set "off"
       python tools/cloudflare_email_obfuscation.py --rollback FILE   restore the value saved in FILE

Why off: with it on, Cloudflare injects email-decode.min.js (blocked by our CSP) and rewrites
mailto links to /cdn-cgi/l/email-protection, so contact links open a Cloudflare page.
Token handling is shared with cloudflare_headers.py (never printed). Only this one zone setting.
"""
import importlib.util
import json
import os
import sys
import time

_spec = importlib.util.spec_from_file_location(
    "cloudflare_headers", os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloudflare_headers.py"))
cfh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cfh)

SETTING = "email_obfuscation"


def zone_path():
    z = cfh.api("GET", f"/zones?name={cfh.ZONE}")
    if not z.get("success") or not z["result"]:
        sys.exit(f"cannot read zone: {cfh.errs(z)}")
    return f"/zones/{z['result'][0]['id']}/settings/{SETTING}"


def read(path):
    r = cfh.api("GET", path)
    if not r.get("success"):
        sys.exit(f"cannot read setting: {cfh.errs(r)}")
    return r["result"]["value"]


def write(path, value):
    r = cfh.api("PATCH", path, {"value": value})
    if not r.get("success"):
        sys.exit(f"FAILED: {cfh.errs(r)}")
    return r["result"]["value"]


def main():
    path = zone_path()
    cur = read(path)
    if "--rollback" in sys.argv:
        with open(sys.argv[sys.argv.index("--rollback") + 1]) as f:
            val = json.load(f)["value"]
        print("rolled back to", write(path, val))
        return
    print(f"{SETTING} currently:", cur)
    if "--apply" not in sys.argv:
        print('dry run; would set "off"')
        return
    bak = os.path.join(cfh.CFG, f"cf_email_obfuscation_backup_{time.strftime('%Y%m%d-%H%M%S')}.json")
    fd = os.open(bak, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"setting": SETTING, "value": cur}, f)
    print("backup saved:", bak)
    print(f"{SETTING} now:", write(path, "off"))


if __name__ == "__main__":
    main()
