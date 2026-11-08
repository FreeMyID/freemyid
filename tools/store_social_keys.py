"""Paste Free My ID posting keys into the OS keyring (service "freemyid-social").

Run:  .venv/bin/python tools/store_social_keys.py
Input is hidden. Press Enter on a prompt to skip that key. Nothing is printed or written to disk.
"""
import getpass

import keyring

SERVICE = "freemyid-social"
KEYS = [
    ("github_token", "GitHub token (FreeMyID-USA, starts with ghp_)"),
    ("bluesky_token", "Bluesky app password (xxxx-xxxx-xxxx-xxxx)"),
    ("mastodon_token", "Mastodon access token"),
    ("reddit_client_id", "Reddit app client ID (reddit.com/prefs/apps, under the app name; blank to skip)"),
    ("reddit_client_secret", "Reddit app secret (blank to skip)"),
    ("reddit_refresh_token", "Reddit OAuth refresh token for u/FreeMyID (blank to skip)"),
    ("discord_bot_token", "Discord bot token (Developer Portal > your app > Bot > Reset Token; leave blank to skip)"),
]

for name, label in KEYS:
    value = getpass.getpass(f"{label}: ").strip()
    if not value:
        print(f"  skipped {name}")
        continue
    keyring.set_password(SERVICE, name, value)
    ok = keyring.get_password(SERVICE, name) == value
    print(f"  {name}: {'saved' if ok else 'FAILED'}")

if keyring.get_password(SERVICE, "mastodon_token") and not keyring.get_password(SERVICE, "mastodon_server"):
    keyring.set_password(SERVICE, "mastodon_server", "mastodon.social")
print("done")
