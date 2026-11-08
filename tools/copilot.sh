#!/usr/bin/env bash
# GitHub Copilot vendor team (coding agent). Process: docs/vendor/COPILOT.md. Owner tooling only.
#
#   tools/copilot.sh issue WO-NNN      open the work order as a GitHub issue labelled vendor:copilot (prints the URL)
#   tools/copilot.sh scope PR          check a Copilot PR's files against its WO's allowed paths and the in-house list
#   tools/copilot.sh merge PR          scope check, then squash the PR onto local main as "Copilot team [freemyid-copilot]"
#                                      (no push; no Copilot co-author trailer). Push the tested SHA yourself, then close the PR.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="FreeMyID/freemyid"
LABEL="vendor:copilot"
EMAIL="242299803+GrayManSam@users.noreply.github.com"

# Same in-house-only list as the other vendors: read from tools/vendor.sh so there is one source of truth.
mapfile -t DENY < <(awk '/^DENY_PREFIXES=\(/{f=1} f{print} f&&/\)/{exit}' "$ROOT/tools/vendor.sh" \
  | sed -E 's/^DENY_PREFIXES=\(//; s/\)$//' | tr ' ' '\n' | sed '/^$/d')
DENY+=(tools/copilot.sh .github/ docs/vendor/WO- docs/vendor/BOARD.md docs/vendor/COPILOT.md docs/vendor/AGENT_CHANNEL.md docs/vendor/CLAUDE_TO_CODEX.md docs/vendor/CODEX_)

wo_file() { local f="$ROOT/docs/vendor/$1.md"; [ -f "$f" ] || { echo "no work order $f" >&2; exit 2; }; echo "$f"; }
allowed_paths() { awk '/^## Allowed paths/{f=1;next} /^## /{f=0} f' "$1" | sed -nE 's/^[-*] *`?([^` ]+)`?.*/\1/p'; }
wo_of_pr() { gh pr view "$1" --repo "$REPO" --json title -q .title | grep -oE 'WO-[0-9]{3}' | head -1; }

scope() {   # prints problems; exit 1 if any
  local pr="$1" wo f bad=0
  wo="$(wo_of_pr "$pr")"; [ -n "$wo" ] || { echo "PR #$pr title has no WO-NNN" >&2; return 1; }
  f="$(wo_file "$wo")"
  mapfile -t allow < <(allowed_paths "$f")
  while read -r path; do
    for d in "${DENY[@]}"; do [[ "$path" == "$d"* ]] && { echo "IN-HOUSE ONLY: $path"; bad=1; continue 2; }; done
    ok=0; for a in "${allow[@]}"; do [[ "$path" == "$a"* ]] && ok=1; done
    [[ "$path" == VENDOR_STATUS.md ]] && { echo "drop: $path (PR description replaces it)"; bad=1; continue; }
    [ $ok = 1 ] || { echo "OUT OF SCOPE ($wo): $path"; bad=1; }
  done < <(gh pr view "$pr" --repo "$REPO" --json files -q '.files[].path')
  [ $bad = 0 ] && echo "PR #$pr ($wo): all files inside the allowed paths"
  return $bad
}

cmd="${1:-}"; shift || true
case "$cmd" in
  issue)
    [[ "${1:-}" =~ ^WO-[0-9]{3}$ ]] || { echo "usage: issue WO-NNN" >&2; exit 2; }
    f="$(wo_file "$1")"
    grep -qE '^Vendor: *copilot' "$f" || { echo "$1 is not a Copilot work order (Vendor: copilot)" >&2; exit 2; }
    gh label create "$LABEL" --repo "$REPO" --color 5319e7 --description "Work order for the Copilot vendor team" >/dev/null 2>&1 || true
    title="$(head -1 "$f" | sed 's/^# //')"
    body="$(printf 'Copilot vendor work order. Follow `.github/copilot-instructions.md` and pick the custom agent named in `Agent:` below.\nChange ONLY the allowed paths. PR description: Done / Next / Questions for the owner / How to test.\nSource of truth: docs/vendor/%s.md (the owner updates it; this issue is a copy).\n\n---\n\n' "$1"; cat "$f")"
    gh issue create --repo "$REPO" --label "$LABEL" --title "$title" --body "$body"
    echo "Next: assign the issue to Copilot and choose agent '$(sed -nE 's/^Agent: *([a-z-]+).*/\1/p' "$f" | head -1)' in the assignee dialog." ;;
  scope)
    [[ "${1:-}" =~ ^[0-9]+$ ]] || { echo "usage: scope PR" >&2; exit 2; }
    scope "$1" ;;
  merge)
    [[ "${1:-}" =~ ^[0-9]+$ ]] || { echo "usage: merge PR" >&2; exit 2; }
    pr="$1"; scope "$pr" || { echo "refusing to merge: fix scope first" >&2; exit 3; }
    [ "$(git -C "$ROOT" rev-parse --abbrev-ref HEAD)" = main ] || { echo "check out main first" >&2; exit 2; }
    git -C "$ROOT" diff --cached --quiet || { echo "index not clean (staged changes): commit or unstage first" >&2; exit 2; }
    title="$(gh pr view "$pr" --repo "$REPO" --json title -q .title)"
    git -C "$ROOT" fetch -q origin "pull/$pr/head:copilot/pr-$pr"
    git -C "$ROOT" merge --squash -q "copilot/pr-$pr"
    GIT_AUTHOR_NAME="Copilot team [freemyid-copilot]" GIT_AUTHOR_EMAIL="$EMAIL" \
      git -C "$ROOT" commit -q -m "$title (vendor: copilot, PR #$pr)"
    echo "Squashed PR #$pr as $(git -C "$ROOT" rev-parse --short HEAD). Run the full suite on that SHA, push it, then:"
    echo "  gh pr close $pr --repo $REPO --comment 'Merged locally as <sha> after in-house review.'" ;;
  *) sed -n '2,8p' "$0"; exit 2 ;;
esac
