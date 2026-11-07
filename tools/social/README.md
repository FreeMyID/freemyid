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
4. Takes an exclusive lock (`docs/marketing/seo/.bluesky-queue.md.lock`). If another run holds
   it, this run logs a skip and exits 0. Then, **before** anything is sent, it appends a
   `claimed` record to the posted ledger (fsynced, see below) and rewrites the block to
   `status: posting <UTC ISO>`.
5. Calls `createSession`, then `createRecord` (`app.bsky.feed.post`) with link facets that use
   UTF-8 byte offsets for every `https://` URL.
6. On success it rewrites the line to `status: posted <UTC ISO> <at:// uri>` (temp file, then
   `os.replace`), adds a `posted` record with the uri to the ledger, and appends a row to
   `docs/marketing/seo/outreach-log.md`.

### The posted ledger (SEC-77)

The queue file is shared and tracked by git, so `git checkout`, a merge or a stale editor buffer
can put an old `status: queued` line back. The poster therefore keeps its own append-only record
outside the repo and outside the pinned install: `~/.local/state/freemyid-poster/posted.jsonl`
(the unit's `StateDirectory=`, the same file when you run it by hand). Each line is
`{"id", "sha256" (of the post text), "status", "uri", "at"}`, where status is `claimed`,
`posted`, `unknown` or `released`.

An item whose id **or** text is in the ledger as claimed, posted or unknown is never posted
again, whatever the queue says. The run logs "... is NOT posted again" and exits 4. Fix the queue
line to `status: posted ...` by hand. Items already marked posted in the queue are copied into
the ledger on the next run. A damaged ledger also stops posting (exit 4) until fixed by hand.

Items are also skipped (with a warning, left `queued`) if they contain an invisible or bidi
character (Unicode category Cf: zero-width space, word joiner, BOM, soft hyphen, RTL/LTR
overrides) or another invisible character (variation selectors, U+034F, Hangul fillers). Emoji
joiners inside emoji sequences, the emoji variation selector after an emoji, and the England,
Scotland and Wales flags are fine; any other hidden tag text is refused. These characters can make
a link look like it goes somewhere it doesn't. A link becomes clickable only if it is plain
printable ASCII: write `https://freemyid.org/%C3%BCber`, not `/über` (the text still posts,
without a link).

Safety: requests go only to `https://bsky.social` (an allowlist checked before every request,
full TLS verification, no redirects, 20 s timeouts, proxy env ignored). The app password and
session tokens are scrubbed from every log line and error message.

### If an item is stuck in `posting`

`posting` means "a post may or may not exist". This happens when the reply was lost (timeout),
the server returned a 5xx, the run was killed, or the queue could not be updated. It is **never
retried**, and nothing else is posted until you fix it, so a post can never go out twice.

1. Open the Free My ID Bluesky profile and look for that post.
2. If it's there, change the line to `status: posted <UTC ISO> <at:// uri>` (any text after
   `posted` is fine). If not, change it back to `status: queued` **and** release it in the
   ledger, otherwise the next run refuses it:

       ~/.local/share/freemyid-poster/venv/bin/python -I -B \
           ~/.local/share/freemyid-poster/poster.py --release Q-012

   `--release` only frees a `claimed`/`unknown` item; a `posted` one is never released (add a
   new item with new text instead).

A definite failure before anything was created (allowlist refusal, connection refused, a 4xx
answer such as a bad password, any session error) puts the item back to `queued` automatically.

Exit codes: `0` posted, nothing to do, or another run holds the lock · `1` definite failure, item
back to `queued` · `2` posted, but the queue or log could not be updated (the URI is in the
journal, so mark the item by hand) · `3` the queue file can't be read or claimed · `4` outcome
unknown, an item is stuck in `posting`, the ledger already has a "queued" item, or the ledger
is damaged: check the account. Any unexpected error after the claim also exits 4.

## Try it without posting

    .venv/bin/python tools/social/poster.py --dry-run

This prints the next post and its facets. It makes no network calls, doesn't read the keyring and
writes no files.

## How it is installed (SEC-59)

The timer never runs code from the repo, because every agent session can write the repo. Instead
`install.sh` builds a separate copy:

- `~/.local/share/freemyid-poster/`: `poster.py` and `verify.sh` (0444), and a venv with only the
  hash-pinned packages from `requirements.lock` (httpx, keyring and their dependencies). pip
  is removed afterwards. Every file is read-only and every directory is 0555.
- `FILES`, `LINKS` and `SHA256SUMS` list every file and symlink in that copy.
- `~/.config/systemd/user/freemyid-poster.{service,timer}`: **copies** (0444) of the templates in
  this folder. The installed unit pins the SHA-256 of `SHA256SUMS`. Before every start it
  checks that pin, then every file in the list, then that nothing was added (for example a `.pth`
  file in site-packages) and that nothing was made writable. Any mismatch means the run fails
  and nothing is posted.

This makes tampering obvious, but it isn't a hard security boundary: anything running as your user
can still chmod the files. The real protection is that agent sandboxes can't write
`~/.local/share` or `~/.config`, and that you review changes before you re-pin them.

The script refuses to run as root. It never runs `systemctl` and never enables the timer. It
doesn't change the repo either.

## Install (lead runs these; nothing is installed by default)

    cd ~/Documents/CODE/Data_Removal
    tools/social/install.sh
    systemctl --user daemon-reload
    systemctl --user enable --now freemyid-poster.timer
    systemctl --user list-timers freemyid-poster.timer

`install.sh` prints the pinned hash. It downloads the pinned wheels from PyPI. To install
offline, use `--wheelhouse DIR`. The venv uses `/usr/bin/python3`, or pass `--python PATH`
(needs 3.12 or newer, and must resolve to a root-owned file in a root-owned directory with a
root-owned stdlib; pyenv, uv or repo `.venv` interpreters are refused, SEC-81b). The repo path is written into the unit, so if the repo moves, run
`--update` again.

To get one real post immediately, run `systemctl --user start freemyid-poster.service`, then
read the log with `journalctl --user -u freemyid-poster.service -n 50`.

The unit sets `PYTHON_KEYRING_BACKEND=keyring.backends.SecretService.Keyring` and poster.py sets
the same for manual runs, so keyring never reads `~/.config/python_keyring/keyringrc.cfg`
(SEC-80). The keyring must be unlocked when the timer fires (GNOME Keyring unlocks when you log in). If it's
locked or missing, the run logs a skip and exits 0.

## Update (after reviewing a change to tools/social/)

    git log -p -- tools/social/          # review first
    tools/social/install.sh --update     # rebuilds the copy and prints the new hash
    systemctl --user daemon-reload

`--update` deletes the old copy and builds a new one from scratch, so nothing from the old copy is
carried over. If the build fails, the copy is removed and the poster won't run until a later
update succeeds. If you upgrade `/usr/bin/python3`, run `--update` too.

To change the dependencies, edit `requirements.in` and regenerate the lock (the command is at
the top of `requirements.lock`). Review the diff before you update.

## Pause, resume, remove

    systemctl --user stop freemyid-poster.timer                  # pause until next login/boot
    systemctl --user disable --now freemyid-poster.timer         # pause until re-enabled
    systemctl --user enable --now freemyid-poster.timer          # resume

Uninstall:

    systemctl --user disable --now freemyid-poster.timer
    rm -f ~/.config/systemd/user/freemyid-poster.{service,timer}
    systemctl --user daemon-reload
    chmod -R u+w ~/.local/share/freemyid-poster && rm -r ~/.local/share/freemyid-poster

Keep `~/.local/state/freemyid-poster/posted.jsonl` unless you also retire the queue: it is what
stops old items from posting twice after a reinstall.

If an older install used `ln -sf` links, `install.sh` replaces those links with copies. It never
touches the files the links pointed to.

To hold back a single post, change its line from `status: queued` to something else, for example
`status: hold`. To stop all posting at once without touching systemd, delete the `bluesky_token`
keyring entry.

## Adding Mastodon later

`poster.py` has a `Backend` protocol: `queue_file`, `allowed_hosts`, `length_error`, `facets`,
`load_credentials`, `post`. `MastodonBackend` is a stub (500 chars, `mastodon.social`, Bearer
`mastodon_token`). To finish it, implement `load_credentials` and `post`
(`POST https://mastodon.social/api/v1/statuses`), add it to `BACKENDS`, write tests, then add a
second unit template that runs `poster.py --backend mastodon` and install it the same way.
