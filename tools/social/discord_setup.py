"""Set up the official Free My ID Discord server from docs/marketing/discord-server-plan.md.

Idempotent: re-running only fills in what is missing. Uses the bot token in keyring
(service "freemyid-social", entry "discord_bot_token"); the token is never printed.
Run:  .venv/bin/python tools/social/discord_setup.py [--dry-run]
"""
from __future__ import annotations

import sys
import time

import httpx
import keyring

GUILD = "1568799115574378617"
API = "https://discord.com/api/v10"
DRY = "--dry-run" in sys.argv

VIEW, SEND, READ_HISTORY = 1 << 10, 1 << 11, 1 << 16
SEND_THREADS, CREATE_PUB_THREADS = 1 << 38, 1 << 35

CATEGORIES = ["START HERE", "HELP", "TALK", "TEAM"]
# name -> (category, topic, read_only, private_to_mods)
CHANNELS = {
    "welcome": ("START HERE", "Start here. Download only from https://freemyid.org. Never post personal details. We never message first.", True, False),
    "rules": ("START HERE", "The short rules. Please read them.", True, False),
    "announcements": ("START HERE", "Releases, fixes and honest status from the Free My ID Team.", True, False),
    "help": ("HELP", "Questions about Free My ID. Never post personal details. We never message first.", False, False),
    "broker-reports": ("HELP", "A site is not honoring removals or its opt-out page changed. Site name and link only, never your own details.", False, False),
    "feedback": ("TALK", "Ideas, confusing screens, what would help your parents.", False, False),
    "off-topic": ("TALK", "Friendly chat. No politics or party talk, no selling.", False, False),
    "mod-chat": ("TEAM", "Moderators only.", False, True),
}

RULES = """**Free My ID server rules. Short and plain.**
1. **Never post personal details here.** No full name with address, no phone number, email, date of birth, Social Security number, passwords, codes or photos of documents. Not even if someone asks. We will never ask.
2. **We will never message you first.** The Free My ID Team never asks for money, passwords, codes or your details by private message. If someone claims to be us and does, block them and tell a moderator.
3. **Be kind.** No insults, no mocking people for the questions they ask. Every question here is a good one.
4. **No politics or party talk.** People of every view are welcome. Keep it about protecting your privacy.
5. **No selling, ads or links to other servers.** No "investment", "recovery" or "removal service" offers. These are removed and the poster is banned.
6. **Be careful with links.** Only trust downloads from freemyid.org. If a link is anywhere else, treat it as unsafe.
7. **We cannot promise results.** Free My ID asks sites to remove you, and some sites do not comply. Please do not ask for legal or medical advice here.
The team can remove messages and members to keep this a safe place. Questions: ask in #help."""

WARNING = ("**Do not post personal details in this channel.** No full name, address, phone number, email, "
           "date of birth, Social Security number or passwords, and no screenshots that show them. If you must "
           "describe a problem, say \"a site listed my address\" and leave out the actual address. A moderator will "
           "delete any message with personal details and may ask you to change a password that was posted.")

ROLES = [("Free My ID Team", 0x1B2F5B), ("Moderator", 0xA3202E)]


def main() -> int:
    token = keyring.get_password("freemyid-social", "discord_bot_token")
    if not token:
        print("No discord_bot_token in keyring. Run tools/store_social_keys.py in a real terminal first.")
        return 2
    c = httpx.Client(base_url=API, headers={"Authorization": f"Bot {token}"}, timeout=30)

    def call(method: str, path: str, **kw):
        if DRY and method != "GET":
            print("DRY", method, path); return {}
        for _ in range(5):
            r = c.request(method, path, **kw)
            if r.status_code == 429:
                time.sleep(float(r.json().get("retry_after", 1)) + 0.2); continue
            if r.status_code >= 400:
                raise SystemExit(f"{method} {path}: {r.status_code} {r.text[:300]}")
            return r.json() if r.content else {}
        raise SystemExit(f"{method} {path}: rate limited")

    me = call("GET", "/users/@me")
    print("bot:", me.get("username"))
    roles = {r["name"]: r for r in call("GET", f"/guilds/{GUILD}/roles")}
    everyone = GUILD  # @everyone role id == guild id
    for name, colour in ROLES:
        if name not in roles:
            roles[name] = call("POST", f"/guilds/{GUILD}/roles", json={"name": name, "color": colour, "hoist": True}) or {"id": None}
            print("role +", name)
    mod_ids = [roles[n]["id"] for n, _ in ROLES if roles[n].get("id")]

    chans = call("GET", f"/guilds/{GUILD}/channels")
    by_name = {ch["name"]: ch for ch in chans}
    cat_ids = {}
    for i, cat in enumerate(CATEGORIES):
        ch = by_name.get(cat) or next((x for x in chans if x["type"] == 4 and x["name"].upper() == cat), None)
        if not ch:
            ch = call("POST", f"/guilds/{GUILD}/channels", json={"name": cat, "type": 4, "position": i}) or {"id": None}
            print("category +", cat)
        cat_ids[cat] = ch.get("id")

    for pos, (name, (cat, topic, read_only, private)) in enumerate(CHANNELS.items()):
        ow = []
        if read_only:
            ow.append({"id": everyone, "type": 0, "allow": str(VIEW | READ_HISTORY), "deny": str(SEND | SEND_THREADS | CREATE_PUB_THREADS)})
            ow += [{"id": rid, "type": 0, "allow": str(SEND), "deny": "0"} for rid in mod_ids]
        if private:
            ow.append({"id": everyone, "type": 0, "allow": "0", "deny": str(VIEW)})
            ow += [{"id": rid, "type": 0, "allow": str(VIEW | SEND | READ_HISTORY), "deny": "0"} for rid in mod_ids]
        ow.append({"id": me["id"], "type": 1, "allow": str(VIEW | SEND | READ_HISTORY), "deny": "0"})
        body = {"name": name, "type": 0, "topic": topic, "parent_id": cat_ids[cat], "position": pos,
                "permission_overwrites": ow}
        if name in by_name:
            call("PATCH", f"/channels/{by_name[name]['id']}", json={k: v for k, v in body.items() if k != "type"})
            print("channel ~", name)
        else:
            by_name[name] = call("POST", f"/guilds/{GUILD}/channels", json=body) or {"id": None}
            print("channel +", name)

    def post_once(ch: str, text: str, pin: bool) -> None:
        cid = by_name[ch].get("id")
        if not cid:
            return
        msgs = call("GET", f"/channels/{cid}/messages", params={"limit": 50})
        if any(m.get("author", {}).get("id") == me["id"] and m.get("content", "")[:40] == text[:40] for m in msgs):
            print("message =", ch); return
        m = call("POST", f"/channels/{cid}/messages", json={"content": text, "allowed_mentions": {"parse": []}})
        if pin and m.get("id") and not DRY:
            r = c.put(f"/channels/{cid}/pins/{m['id']}")
            if r.status_code >= 400:
                print(f"  could not pin in #{ch} ({r.status_code}); pin it by hand")
                pin = False
        print("message +", ch, "(pinned)" if pin else "")

    post_once("rules", RULES, pin=True)
    post_once("help", WARNING, pin=True)
    post_once("broker-reports", WARNING, pin=True)

    # Safety: verification Medium, explicit-content filter on for everyone, mentions-only notifications.
    call("PATCH", f"/guilds/{GUILD}", json={"verification_level": 2, "explicit_content_filter": 2,
                                           "default_message_notifications": 1})
    print("guild safety settings set")

    existing = {r["name"] for r in call("GET", f"/guilds/{GUILD}/auto-moderation/rules")}
    alert = by_name.get("mod-chat", {}).get("id")
    def actions(msg: str):
        a = [{"type": 1, "metadata": {"custom_message": msg}}]
        if alert:
            a.append({"type": 2, "metadata": {"channel_id": alert}})
        return a
    automod = [
        {"name": "Spam and mention spam", "event_type": 1, "trigger_type": 5,
         "trigger_metadata": {"mention_total_limit": 3}, "actions": actions("Too many mentions. Message removed.")},
        {"name": "Invites and scam words", "event_type": 1, "trigger_type": 1,
         "trigger_metadata": {"keyword_filter": ["*discord.gg*", "*discord.com/invite*", "nitro", "airdrop", "crypto",
                                                 "investment", "telegram", "whatsapp"]},
         "actions": actions("Links to other servers and money offers are not allowed here.")},
        {"name": "Personal details", "event_type": 1, "trigger_type": 1,
         "trigger_metadata": {"regex_patterns": [r"\b\d{3}-\d{2}-\d{4}\b", r"\b(?:\d[ -]?){15}\d\b",
                                                 r"\b\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b"]},
         "actions": actions("Please do not post personal details here. Message removed.")},
    ]
    for rule in automod:
        if rule["name"] in existing:
            print("automod =", rule["name"]); continue
        call("POST", f"/guilds/{GUILD}/auto-moderation/rules", json={**rule, "enabled": True})
        print("automod +", rule["name"])
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
