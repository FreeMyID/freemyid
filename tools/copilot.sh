#!/usr/bin/env bash
# GitHub Copilot vendor team. Roster: docs/vendor/copilot-team/TEAM.md. Process: docs/vendor/COPILOT.md. Owner tooling only.
#
# Live channel (local Copilot CLI, in a clean desk worktree; no git, no GitHub tools, no network):
#   tools/copilot.sh liaison            Tomás acknowledges new CLAUDE-P### messages and briefs Grace
#   tools/copilot.sh lead ["note"]      Grace (project engineer) reads the brief/channel and answers or proposes work
#   tools/copilot.sh sync               liaison, then lead (one live round trip)
#   tools/copilot.sh watch [secs]       loop: run `sync` whenever CLAUDE_TO_COPILOT.md gets a new CLAUDE-P### (default 60s)
# Local builders (Copilot CLI in .vendor-wt/wo-NNN, sandboxed, no git; the owner commits):
#   tools/copilot.sh start WO-NNN       the WO's specialist starts the work order
#   tools/copilot.sh checkin WO-NNN "notes"
#   tools/copilot.sh commit WO-NNN      commit the allowed paths as "<Name> [freemyid-copilot]" (scope-checked)
# Cloud coding agent (GitHub):
#   tools/copilot.sh issue WO-NNN       open the WO as a GitHub issue labelled vendor:copilot
#   tools/copilot.sh scope PR           check a Copilot PR's files against its WO's allowed paths and the in-house list
#   tools/copilot.sh merge PR           scope check, then squash the PR onto local main (no push, no co-author trailer)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="FreeMyID/freemyid"
LABEL="vendor:copilot"
EMAIL="242299803+GrayManSam@users.noreply.github.com"
VD="docs/vendor"
TEAM="$ROOT/$VD/copilot-team"
SCRATCH="$ROOT/.vendor-wt"
DESK="$SCRATCH/copilot-desk"

# Same in-house-only list as the other vendors: read from tools/vendor.sh so there is one source of truth.
mapfile -t DENY < <(awk '/^DENY_PREFIXES=\(/{f=1} f{print} f&&/\)/{exit}' "$ROOT/tools/vendor.sh" \
  | sed -E 's/^DENY_PREFIXES=\(//; s/\)$//' | tr ' ' '\n' | sed '/^$/d')
DENY+=(tools/copilot.sh .github/ $VD/WO- $VD/BOARD.md $VD/COPILOT.md $VD/AGENT_CHANNEL.md $VD/CLAUDE_TO_CODEX.md $VD/CODEX_
       $VD/CLAUDE_TO_COPILOT.md $VD/COPILOT_TO_CLAUDE.md $VD/COPILOT_PROPOSALS.md $VD/copilot-team/)

# Every local Copilot run: OS command sandbox, no GitHub MCP tools, no network, no git/gh, no installs, no memory.
SAFE=(--trust-folder --sandbox --disable-builtin-mcps --disable-client-telemetry -s
  --deny-tool 'shell(git:*)' 'shell(gh:*)' 'shell(curl:*)' 'shell(wget:*)' 'shell(ssh:*)' 'shell(scp:*)'
  'shell(pip:*)' 'shell(pip3:*)' 'shell(npm:*)' 'shell(npx:*)' 'shell(pnpm add:*)' 'shell(pnpm install:*)' 'shell(sudo:*)'
  'shell(bash:*)' 'shell(sh:*)' 'shell(zsh:*)' 'shell(env:*)' 'shell(uv:*)' 'shell(pipx:*)' 'shell(/usr/bin/git:*)'
  'url' 'memory')
# Builders: the OS sandbox is the real barrier (SEC-107); name-based deny rules are only a second layer. Builders get no
# access to the in-house .venv (SEC-105): if they can run tests at all, it is with tools inside their own worktree.

need_cli() { command -v copilot >/dev/null || { echo "copilot CLI not installed" >&2; exit 4; }; }
wo_check() { [[ "${1:-}" =~ ^WO-[0-9]{3}$ ]] || { echo "work order id must look like WO-001" >&2; exit 2; }; }
wo_file() { local f="$ROOT/$VD/$1.md"; [ -f "$f" ] || { echo "no work order $f" >&2; exit 2; }; echo "$f"; }
agent_of() { sed -nE 's/^Agent: *([a-z-]+).*/\1/p' "$1" | head -1; }
name_of() { sed -nE 's/^Name: *(.+)$/\1/p' "$TEAM/$1.md" 2>/dev/null | head -1; }
allowed_paths() { awk '/^## Allowed paths/{f=1;next} /^## /{f=0} f' "$1" | sed -nE 's/^[-*] *`?([^` ]+)`?.*/\1/p'; }
wt_of() { echo "$SCRATCH/$(echo "$1" | tr 'A-Z' 'a-z')"; }
wo_of_pr() { gh pr view "$1" --repo "$REPO" --json title -q .title | grep -oE 'WO-[0-9]{3}' | head -1; }

check_paths() {   # check_paths WO-FILE < paths ; prints problems, returns 1 if any
  local f="$1" bad=0 path d a ok
  mapfile -t allow < <(allowed_paths "$f")
  while read -r path; do
    [ -n "$path" ] || continue
    [[ "$path" == VENDOR_STATUS.md ]] && continue
    for d in "${DENY[@]}"; do [[ "$path" == "$d"* ]] && { echo "IN-HOUSE ONLY: $path"; bad=1; continue 2; }; done
    ok=0   # SEC-106: an allowed file matches exactly; only an allowed entry ending in '/' covers what is under it
    for a in "${allow[@]}"; do if [[ "$a" == */ ]]; then [[ "$path" == "$a"* ]] && ok=1; else [[ "$path" == "$a" ]] && ok=1; fi; done
    [ $ok = 1 ] || { echo "OUT OF SCOPE: $path"; bad=1; }
  done
  return $bad
}

# --- desk: a clean detached worktree of local main for Grace and Tomás (no gitignored private files) ---
DESK_FILES=(CLAUDE_TO_COPILOT.md COPILOT_TO_CLAUDE.md COPILOT_PROPOSALS.md BOARD.md copilot-team/inbox.md copilot-team/lead-log.md)
desk_prepare() {
  git -C "$ROOT" worktree remove --force "$DESK" >/dev/null 2>&1 || true
  git -C "$ROOT" worktree add -q --detach "$DESK" main
  local f; for f in "${DESK_FILES[@]}"; do [ -f "$ROOT/$VD/$f" ] && cp "$ROOT/$VD/$f" "$DESK/$VD/$f"; done; return 0
}
desk_return() {   # copy back ONLY the files the role may write
  local f; for f in "$@"; do [ -f "$DESK/$VD/$f" ] && cp "$DESK/$VD/$f" "$ROOT/$VD/$f"; done; return 0
}
run_role() {   # run_role ROLE PROMPT WRITABLE...
  local role="$1" prompt="$2"; shift 2
  local allow=() f; for f in "$@"; do allow+=(--allow-tool "write($DESK/$VD/$f)"); done
  need_cli; desk_prepare
  # No --sandbox here: Grace and Tomás get no shell at all (non-interactive denies it) and may write only their
  # channel files; the OS sandbox only broke their read-only search tools.
  local nosb=() a; for a in "${SAFE[@]}"; do [ "$a" = --sandbox ] || nosb+=("$a"); done
  copilot -C "$DESK" --agent "$role" "${nosb[@]}" "${allow[@]}" -p "$prompt" || true
  desk_return "$@"
  git -C "$ROOT" worktree remove --force "$DESK" >/dev/null 2>&1 || true
}

liaison() {
  run_role liaison "You are Tomás Rivera. Do your run as described in your profile: acknowledge every unacknowledged
CLAUDE-P### in $VD/CLAUDE_TO_COPILOT.md and brief Grace in $VD/copilot-team/inbox.md. Today is $(date +%F)." \
    COPILOT_TO_CLAUDE.md copilot-team/inbox.md
}
lead() {
  run_role lead "You are Grace Holloway. Today is $(date +%F). Read $VD/copilot-team/inbox.md and the channel, then
answer Morgan Reyes in $VD/COPILOT_TO_CLAUDE.md and update proposals/log as your profile says. ${1:-}" \
    COPILOT_TO_CLAUDE.md COPILOT_PROPOSALS.md copilot-team/lead-log.md copilot-team/inbox.md
}
last_claude() { grep -oE "^## CLAUDE-P[0-9]{3}" "$ROOT/$VD/CLAUDE_TO_COPILOT.md" 2>/dev/null | tail -1 || true; }

cmd="${1:-}"; shift || true
case "$cmd" in
  liaison) liaison ;;
  lead) lead "${1:-}" ;;
  sync) liaison; lead ;;
  watch)
    every="${1:-60}"; seen="$(last_claude)"; echo "watching $VD/CLAUDE_TO_COPILOT.md every ${every}s (last: ${seen:-none})"
    while true; do
      now="$(last_claude)"
      if [ -n "$now" ] && [ "$now" != "$seen" ]; then echo "$(date +%T) new ${now#\#\# }: sync"; liaison; lead; seen="$now"; fi
      sleep "$every"
    done ;;
  start)
    wo_check "${1:-}"; wo="$1"; f="$(wo_file "$wo")"; wt="$(wt_of "$wo")"
    grep -qE '^Vendor: *copilot' "$f" || { echo "$wo is not a Copilot work order (Vendor: copilot)" >&2; exit 2; }
    role="$(agent_of "$f")"; [ -f "$ROOT/.github/agents/$role.agent.md" ] || { echo "no agent profile for '$role'" >&2; exit 2; }
    [ -e "$wt" ] && { echo "$wt exists: use checkin" >&2; exit 2; }
    need_cli; git -C "$ROOT" worktree add -q -b "copilot/$(echo "$wo" | tr 'A-Z' 'a-z')" "$wt" main
    # SEC-105: the builder gets its own throwaway copy of the venv (copy-on-write on btrfs), never the in-house one.
    cp -a --reflink=auto "$ROOT/.venv" "$wt/.venv"
    copilot -C "$wt" --agent "$role" "${SAFE[@]}" --allow-all-tools -p "You are $(name_of "$role") in BUILDER mode for work
order $wo, working LOCALLY in this folder (no git: the owner commits). Change ONLY the allowed paths, and create no
other files (no scratch, backup or .new/.tmp copies). If a shell is available, run only read-only commands and the tests
you can run inside this folder: PYTHONPATH=src .venv/bin/python -m pytest -q <tests> and .venv/bin/python -m ruff check <files> (that .venv is
your own throwaway copy). No network, no installs; otherwise say the owner must run them. End by WRITING THE FILE VENDOR_STATUS.md in this
folder (not only in your reply)
(Done / Next / Questions for the owner / How to test).

$(cat "$f")"
    git -C "$wt" status --short ;;
  checkin)
    wo_check "${1:-}"; [ $# -ge 2 ] || { echo 'usage: checkin WO-NNN "notes"' >&2; exit 2; }
    wo="$1"; f="$(wo_file "$wo")"; wt="$(wt_of "$wo")"; role="$(agent_of "$f")"; need_cli
    copilot -C "$wt" --agent "$role" "${SAFE[@]}" --allow-all-tools -p "Owner check-in for $wo from Morgan Reyes:
$2

Continue within the allowed paths only (create no other files), rerun the tests with
PYTHONPATH=src .venv/bin/python -m pytest -q <tests>, and update VENDOR_STATUS.md."
    git -C "$wt" status --short ;;
  commit)
    wo_check "${1:-}"; wo="$1"; f="$(wo_file "$wo")"; wt="$(wt_of "$wo")"; role="$(agent_of "$f")"
    changed="$(git -C "$wt" status --porcelain -z -uall | tr '\0' '\n' | sed -E 's/^...//' | grep -vE '^(VENDOR_STATUS\.md|web/node_modules(/.*)?)$' || true)"
    [ -n "$changed" ] || { echo "nothing to commit in $wt" >&2; exit 2; }
    check_paths "$f" <<<"$changed" || { echo "refusing to commit: out-of-scope changes" >&2; exit 3; }
    n="$(name_of "$role")"; mapfile -t paths <<<"$changed"
    git -C "$wt" add -- "${paths[@]}"
    git -C "$wt" -c user.name="$n [freemyid-copilot]" -c user.email="$EMAIL" commit -q -m "$(head -1 "$f" | sed 's/^# //')"
    echo "committed on $(git -C "$wt" rev-parse --abbrev-ref HEAD) as $n [freemyid-copilot]" ;;
  issue)
    wo_check "${1:-}"; f="$(wo_file "$1")"
    grep -qE '^Vendor: *copilot' "$f" || { echo "$1 is not a Copilot work order (Vendor: copilot)" >&2; exit 2; }
    gh label create "$LABEL" --repo "$REPO" --color 5319e7 --description "Work order for the Copilot vendor team" >/dev/null 2>&1 || true
    role="$(agent_of "$f")"
    body="$(printf 'Copilot vendor work order for %s (custom agent `%s`). Follow `.github/copilot-instructions.md`.\nChange ONLY the allowed paths. PR description: Done / Next / Questions for the owner / How to test.\nSource of truth: docs/vendor/%s.md (the owner updates it; this issue is a copy).\n\n---\n\n' "$(name_of "$role")" "$role" "$1"; cat "$f")"
    gh issue create --repo "$REPO" --label "$LABEL" --title "$(head -1 "$f" | sed 's/^# //')" --body "$body"
    echo "Next: assign the issue to Copilot and choose agent '$role' in the assignee dialog." ;;
  scope)
    [[ "${1:-}" =~ ^[0-9]+$ ]] || { echo "usage: scope PR" >&2; exit 2; }
    wo="$(wo_of_pr "$1")"; [ -n "$wo" ] || { echo "PR #$1 title has no WO-NNN" >&2; exit 2; }
    gh pr view "$1" --repo "$REPO" --json files -q '.files[].path' | check_paths "$(wo_file "$wo")" \
      && echo "PR #$1 ($wo): all files inside the allowed paths" ;;
  merge)
    [[ "${1:-}" =~ ^[0-9]+$ ]] || { echo "usage: merge PR" >&2; exit 2; }
    pr="$1"; "$0" scope "$pr" || { echo "refusing to merge: fix scope first" >&2; exit 3; }
    [ "$(git -C "$ROOT" rev-parse --abbrev-ref HEAD)" = main ] || { echo "check out main first" >&2; exit 2; }
    git -C "$ROOT" diff --cached --quiet || { echo "index not clean (staged changes): commit or unstage first" >&2; exit 2; }
    title="$(gh pr view "$pr" --repo "$REPO" --json title -q .title)"; wo="$(wo_of_pr "$pr")"
    n="$(name_of "$(agent_of "$(wo_file "$wo")")")"
    git -C "$ROOT" fetch -q origin "pull/$pr/head:copilot/pr-$pr"
    git -C "$ROOT" diff --name-only "main...copilot/pr-$pr" | check_paths "$(wo_file "$wo")" \
      || { echo "refusing to merge: the fetched branch differs from the reviewed scope" >&2; exit 3; }
    git -C "$ROOT" merge --squash -q "copilot/pr-$pr"
    GIT_AUTHOR_NAME="${n:-Copilot team} [freemyid-copilot]" GIT_AUTHOR_EMAIL="$EMAIL" \
      git -C "$ROOT" commit -q -m "$title (vendor: copilot, PR #$pr)"
    echo "Squashed PR #$pr as $(git -C "$ROOT" rev-parse --short HEAD). Run the full suite on that SHA, push it, then:"
    echo "  gh pr close $pr --repo $REPO --comment 'Merged locally as <sha> after in-house review.'" ;;
  *) sed -n '2,19p' "$0"; exit 2 ;;
esac
