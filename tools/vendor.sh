#!/usr/bin/env bash
# Outside vendor teams: Google Antigravity (`agy`) and OpenAI Codex (`codex`). Process: docs/VENDOR.md.
# Pick the vendor with VENDOR=agy|codex (default: the work order's 'Vendor:' line, else agy).
#
#   tools/vendor.sh ask "question"                 read-only advisor answer
#   tools/vendor.sh start   WO-NNN                 vendor starts the work order (builder mode)
#   tools/vendor.sh checkin WO-NNN "owner notes"   owner check-in; vendor continues
#   tools/vendor.sh status  WO-NNN                 VENDOR_STATUS.md + diff + scope check
#   tools/vendor.sh pr      WO-NNN                 push vendor/wo-NNN and open/update a draft PR (owner tooling)
#   tools/vendor.sh close   WO-NNN                 remove the worktree (branch kept)
#
# The vendor only ever sees a fresh git worktree (gitignored private files never exist there),
# runs with --sandbox, never gets git or push, and its work is reviewed like an outside PR.
# VENDOR_WATCH=1 tools/vendor.sh ...  also opens a remote connection so the owner can watch the
# session live in the Antigravity app.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRATCH="${VENDOR_DIR:-${TMPDIR:-/tmp}/freemyid-vendor}"
mkdir -p "$SCRATCH"
need_agy() { command -v "${VENDOR:-agy}" >/dev/null || { echo "${VENDOR:-agy} not installed" >&2; exit 4; }; }
vendor_of() { sed -nE "s/^Vendor: *(agy|codex).*/\1/p" "$1" | head -1; }
wo_file() { local f="$ROOT/docs/vendor/$1.md"; [ -f "$f" ] || { echo "no work order $f" >&2; exit 2; }; echo "$f"; }
wo_check() { [[ "$1" =~ ^WO-[0-9]{3}$ ]] || { echo "work order id must look like WO-001" >&2; exit 2; }; }
wt_of() { echo "$SCRATCH/$(echo "$1" | tr 'A-Z' 'a-z')"; }
branch_of() { echo "vendor/$(echo "$1" | tr 'A-Z' 'a-z')"; }

allowed_paths() {   # lines under "## Allowed paths" in the work order, as path prefixes
  awk '/^## Allowed paths/{f=1;next} /^## /{f=0} f' "$1" | sed -nE 's/^[-*] *`?([^` ]+)`?.*/\1/p'
}

NO_SHELL="IMPORTANT: shell/terminal commands are NOT available to you in this engagement; do not try any
(no ls, cat, pytest, ruff, git). Use only your file read, search and edit tools. The owner reads your diff and
runs the tests, then sends you the results at the next check-in. Write the tests anyway."

CODEX_RULES="You run inside OpenAI Codex's workspace-write sandbox (no network). You MAY run read-only shell
commands and the project's tests INSIDE THIS FOLDER ONLY, using the owner's virtualenv:
PYTHONPATH=src $ROOT/.venv/bin/pytest -q <tests>   and   $ROOT/.venv/bin/ruff check <files>.
Never read, list or print anything outside this folder (no ~, no /home, no /etc, no keyrings, no env dumps).
Never run git, never install packages, never try to reach the network."

run_vendor() {   # $1 worktree, $2 prompt
  if [ "${VENDOR:-agy}" = codex ]; then
    codex exec -s workspace-write -C "$1" -o "$1/.vendor-last-message.txt" "$CODEX_RULES

$2"
  else
    cd "$1" && agy -p "$NO_SHELL

$2" --mode accept-edits --sandbox --print-timeout 3600s ${VENDOR_WATCH:+--remote-control}
  fi
  rm -f "$1/.vendor-last-message.txt.lock" 2>/dev/null || true
  git -C "$1" add -A
  git -C "$1" -c user.name="Vendor Antigravity [freemyid-vendor]" commit -q -m "vendor session $(date -u +%FT%TZ)" || true
}

scope_report() {   # $1 WO id
  local wo="$1" wt branch file bad=0
  wt="$(wt_of "$wo")"; branch="$(branch_of "$wo")"; file="$(wo_file "$wo")"
  mapfile -t allow < <(allowed_paths "$file")
  echo "== $wo on $branch"; [ -f "$wt/VENDOR_STATUS.md" ] && cat "$wt/VENDOR_STATUS.md"
  echo "== changed files"; git -C "$ROOT" diff --stat "main...$branch" | tail -20
  while read -r f; do
    [ "$f" = "VENDOR_STATUS.md" ] && continue
    ok=0; for a in "${allow[@]}"; do [[ "$f" == "$a"* ]] && ok=1; done
    [ $ok = 1 ] || { echo "OUT OF SCOPE: $f"; bad=1; }
  done < <(git -C "$ROOT" diff --name-only "main...$branch")
  [ $bad = 0 ] && echo "scope check: OK" || { echo "scope check: FAILED (reject or ask the vendor to revert these)"; return 1; }
}

cmd="${1:-}"; shift || true
case "$cmd" in
  ask)
    need_agy; [ $# -ge 1 ] || { echo 'usage: tools/vendor.sh ask "question"' >&2; exit 2; }
    wt="$(mktemp -d "$SCRATCH/ask.XXXXXX")"; rmdir "$wt"
    git -C "$ROOT" worktree add -q --detach "$wt" HEAD
    trap 'git -C "$ROOT" worktree remove --force "$wt" >/dev/null 2>&1 || true' EXIT
    cd "$wt" && agy -p "You are in ADVISOR mode (read-only). $1" --mode plan --sandbox --print-timeout 900s ;;
  start)
    wo_check "${1:-}"; wo="$1"; file="$(wo_file "$wo")"; wt="$(wt_of "$wo")"
    VENDOR="${VENDOR:-$(vendor_of "$file")}"; VENDOR="${VENDOR:-agy}"; need_agy
    [ -e "$wt" ] && { echo "$wt exists: use checkin" >&2; exit 2; }
    git -C "$ROOT" worktree add -q -b "$(branch_of "$wo")" "$wt" main
    run_vendor "$wt" "You are in BUILDER mode for work order $wo. Read GEMINI.md and docs/VENDOR.md first.
Change ONLY the allowed paths. End by updating VENDOR_STATUS.md (Done / Next / Questions for the owner / How to test).

$(cat "$file")"
    scope_report "$wo" || true ;;
  checkin)
    wo_check "${1:-}"; wo="$1"; [ $# -ge 2 ] || { echo 'usage: checkin WO-NNN "notes"' >&2; exit 2; }
    file="$(wo_file "$wo")"; wt="$(wt_of "$wo")"
    VENDOR="${VENDOR:-$(vendor_of "$file")}"; VENDOR="${VENDOR:-agy}"; need_agy; [ -d "$wt" ] || { echo "not started" >&2; exit 2; }
    run_vendor "$wt" "BUILDER mode, work order $wo, owner check-in. Re-read VENDOR_STATUS.md and the work order below,
then act on the owner's notes. Change ONLY the allowed paths. Update VENDOR_STATUS.md at the end.

OWNER NOTES:
$2

WORK ORDER:
$(cat "$file")"
    scope_report "$wo" || true ;;
  status) wo_check "${1:-}"; scope_report "$1" ;;
  pr)   # the OWNER's credentials push the vendor branch; vendors never get push access
    wo_check "${1:-}"; wo="$1"; file="$(wo_file "$wo")"; br="$(branch_of "$wo")"; wt="$(wt_of "$wo")"
    scope_report "$wo" || { echo "refusing to open a PR with out-of-scope changes" >&2; exit 3; }
    git -C "$ROOT" push -q -u origin "$br"
    title="$(head -1 "$file" | sed 's/^# //') (vendor: $(vendor_of "$file"))"
    body="$(printf 'Vendor work order %s. Scope and acceptance criteria: docs/vendor/%s.md\n\nIn-house review required before merge (docs/VENDOR.md). Do not merge without the owner.\n\n---\n' "$wo" "$wo"; cat "$wt/VENDOR_STATUS.md" 2>/dev/null)"
    if gh pr view "$br" --repo FreeMyID/freemyid >/dev/null 2>&1; then
      gh pr edit "$br" --repo FreeMyID/freemyid --body "$body" >/dev/null && echo "updated PR for $br"
    else
      gh pr create --repo FreeMyID/freemyid --draft --base main --head "$br" --title "$title" --body "$body"
    fi ;;
  close)
    wo_check "${1:-}"; git -C "$ROOT" worktree remove --force "$(wt_of "$1")" && echo "closed $1 (branch $(branch_of "$1") kept)" ;;
  *) sed -n '2,9p' "$0" >&2; exit 2 ;;
esac
