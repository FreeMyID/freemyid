# Social poster (Bluesky)

`poster.py` is a plain Python script with no AI. It posts **at most one** queued item per run from
`docs/marketing/seo/bluesky-queue.md` to the Free My ID Bluesky account. A systemd user timer runs
it at 10:00 and 16:00 local time. Missed runs (machine off or asleep) catch up once at the next boot.

## What one run does

1. Parses the queue. Each block must look like this:

       ## Q-001
       status: queued
       note: optional editor comment (zero or more lines, never posted)
       ```text
       post text
       ```

   Text outside blocks is ignored. A malformed block (missing status, wrong fence, unclosed fence,
   empty text, duplicate id) is skipped with a warning and is never posted.
2. Picks the first `status: queued` item that fits Bluesky's 300-grapheme limit. Longer items are
   skipped with a warning and stay queued.
3. Reads the app password from the keyring (service `freemyid-social`, entry `bluesky_token`). The
   handle comes from `--handle`, then `$FREEMYID_BLUESKY_HANDLE`, then the `user` field of the
   `bluesky` keyring entry (the `password` and `email` fields are never read). If either one is
   missing, it logs at info level and exits 0.
4. Calls `createSession`, then `createRecord` (`app.bsky.feed.post`) with link facets that use
   UTF-8 byte offsets for every `https://` URL.
5. On success it rewrites that block's line to `status: posted <UTC ISO> <at:// uri>` (temp file,
   then `os.replace`) and appends a row to `docs/marketing/seo/outreach-log.md`.

Safety: requests go only to `https://bsky.social` (an allowlist checked before every request,
full TLS verification, no redirects, 20 s timeouts, proxy env ignored). The app password and
session tokens are scrubbed from every log line and error message.

Exit codes: `0` posted or nothing to do · `1` network or HTTP error (the item stays queued) ·
`2` posted, but the queue or log could not be updated (the URI is in the journal, so mark the item
by hand) · `3` the queue file can't be read.

## Try it without posting

    .venv/bin/python tools/social/poster.py --dry-run

This prints the next post and its facets. It makes no network calls, doesn't read the keyring and
writes no files.

## Install (lead runs these; nothing is installed by default)

    mkdir -p ~/.config/systemd/user
    ln -sf ~/Documents/CODE/Data_Removal/tools/social/freemyid-poster.service ~/.config/systemd/user/
    ln -sf ~/Documents/CODE/Data_Removal/tools/social/freemyid-poster.timer ~/.config/systemd/user/
    systemctl --user daemon-reload
    systemctl --user enable --now freemyid-poster.timer
    systemctl --user list-timers freemyid-poster.timer

The unit assumes the repo is at `~/Documents/CODE/Data_Removal`. If it lives somewhere else, edit
the `%h/...` paths in the `.service` file. To get one real post immediately, run
`systemctl --user start freemyid-poster.service` and then read the log with
`journalctl --user -u freemyid-poster.service -n 50`.

The keyring must be unlocked when the timer fires (GNOME Keyring unlocks when you log in). If it's
locked or missing, the run logs a skip and exits 0.

## Pause, resume, remove

    systemctl --user stop freemyid-poster.timer                  # pause until next login/boot
    systemctl --user disable --now freemyid-poster.timer         # pause until re-enabled
    systemctl --user enable --now freemyid-poster.timer          # resume
    rm ~/.config/systemd/user/freemyid-poster.{service,timer} && systemctl --user daemon-reload

To hold back a single post, change its line from `status: queued` to something else, for example
`status: hold`. To stop all posting at once without touching systemd, delete the `bluesky_token`
keyring entry.

## Adding Mastodon later

`poster.py` has a `Backend` protocol: `queue_file`, `allowed_hosts`, `length_error`, `facets`,
`load_credentials`, `post`. `MastodonBackend` is a stub (500 chars, `mastodon.social`, Bearer
`mastodon_token`). To finish it, implement `load_credentials` and `post`
(`POST https://mastodon.social/api/v1/statuses`), add it to `BACKENDS`, write tests, then add a
second unit that runs `poster.py --backend mastodon`.
