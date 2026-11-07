# Free My ID: Cloudflare zone hardening applied 2026-11-07 (idempotent-ish; re-running re-adds CAA records).
# Needs tools/cf.py-style helper with token from ~/.config/freemyid/cf_token. Kept for reference.
from cf import api, Z
def show(label, r): print(label, r.get("success"), [e.get("message") for e in r.get("errors", [])])
# 1) proxy the web records (A/AAAA apex + www); mail/verification records untouched
for x in api("GET", f"/zones/{Z}/dns_records?per_page=100")["result"]:
    if x["type"] in ("A", "AAAA") or (x["type"] == "CNAME" and x["name"] == "www.freemyid.org"):
        show(f"proxy {x['type']} {x['name']} {x['content']}", api("PATCH", f"/zones/{Z}/dns_records/{x['id']}", {"proxied": True}))
# 2) zone settings
for k, v in [("ssl", "full"), ("always_use_https", "on"), ("min_tls_version", "1.2"), ("tls_1_3", "on"),
             ("automatic_https_rewrites", "on"), ("opportunistic_encryption", "on"), ("browser_check", "on"),
             ("security_header", {"strict_transport_security": {"enabled": True, "max_age": 15552000,
                                  "include_subdomains": False, "preload": False, "nosniff": True}})]:
    show(f"setting {k}", api("PATCH", f"/zones/{Z}/settings/{k}", {"value": v}))
# 3) DNSSEC
r = api("PATCH", f"/zones/{Z}/dnssec", {"status": "active"}); show("dnssec", r); print("  dnssec status", (r.get("result") or {}).get("status"))
# 4) CAA: GitHub Pages (Let's Encrypt) + Cloudflare Universal SSL CAs
for tag, val in [("issue", "letsencrypt.org"), ("issue", "pki.goog"), ("issue", "ssl.com"), ("issue", "digicert.com"),
                 ("issuewild", ";"), ("iodef", "mailto:security@freemyid.org")]:
    show(f"caa {tag} {val}", api("POST", f"/zones/{Z}/dns_records", {"type": "CAA", "name": "freemyid.org", "ttl": 1,
        "data": {"flags": 0, "tag": tag, "value": val}, "comment": "certificate issuers"}))
# 5) security response headers
hdr = {"X-Frame-Options": "DENY", "Referrer-Policy": "strict-origin-when-cross-origin",
       "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()",
       "Cross-Origin-Opener-Policy": "same-origin", "X-Content-Type-Options": "nosniff"}
rule = {"expression": "true", "description": "Free My ID security headers", "action": "rewrite",
        "action_parameters": {"headers": {k: {"operation": "set", "value": v} for k, v in hdr.items()}}}
show("headers rule", api("PUT", f"/zones/{Z}/rulesets/phases/http_response_headers_transform/entrypoint", {"rules": [rule]}))
