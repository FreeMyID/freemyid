#!/usr/bin/env bash
# Outside vendor teams: Google Antigravity (`agy`) and OpenAI Codex (`codex`). Process: docs/VENDOR.md.
# Pick the vendor with VENDOR=agy|codex (default: the work order's 'Vendor:' line, else agy).
#
#   tools/vendor.sh ask "question"                 read-only advisor answer
#   tools/vendor.sh start   WO-NNN                 vendor starts the work order (builder mode)
#   tools/vendor.sh checkin WO-NNN "owner notes"   owner check-in; vendor continues
#   tools/vendor.sh status  WO-NNN                 VENDOR_STATUS.md + diff + scope check
#   tools/vendor.sh pr      WO-NNN                 push vendor/wo-NNN and open/update a draft PR (owner tooling)
#   tools/vendor.sh webcheck WO-NNN                owner: build + site checks on a vendor branch
#   tools/vendor.sh auto    [N]                    Codex team runs itself: lead writes up to N work orders, specialists build, PRs open
#   tools/vendor.sh close   WO-NNN                 remove the worktree (branch kept)
#   tools/vendor.sh lead    "message"              talk to the Codex team lead (plans, proposes work orders)
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
TEAM_DIR="$ROOT/docs/vendor/codex-team"
agent_of() { sed -nE "s/^Agent: *([a-z-]+).*/\1/p" "$1" | head -1; }
role_prompt() {   # codex team charter + the named member's role file
  local a="${AGENT:-}"; [ -n "$a" ] && [ -f "$TEAM_DIR/$a.md" ] || return 0
  printf '%s\n\nYOUR ROLE:\n%s\n' "$(cat "$TEAM_DIR/TEAM.md")" "$(cat "$TEAM_DIR/$a.md")"
}
author_of() {     # commit author for the session
  local a="${AGENT:-}" n=""
  [ -n "$a" ] && [ -f "$TEAM_DIR/$a.md" ] && n="$(sed -nE 's/^Name: *(.+)$/\1/p' "$TEAM_DIR/$a.md" | head -1)"
  if [ -n "$n" ]; then echo "$n [freemyid-codex]"; elif [ "${VENDOR:-agy}" = codex ]; then echo "Codex team [freemyid-codex]"; else echo "Antigravity team [freemyid-vendor]"; fi
}
wo_file() { local f="$ROOT/docs/vendor/$1.md"; [ -f "$f" ] || { echo "no work order $f" >&2; exit 2; }; echo "$f"; }
wo_check() { [[ "$1" =~ ^WO-[0-9]{3}$ ]] || { echo "work order id must look like WO-001" >&2; exit 2; }; }
wt_of() { echo "$SCRATCH/$(echo "$1" | tr 'A-Z' 'a-z')"; }
branch_of() { echo "vendor/$(echo "$1" | tr 'A-Z' 'a-z')"; }

# In-house only: no vendor change may touch these, whatever its work order says (docs/VENDOR.md).
DENY_PREFIXES=(src/freemyid/crypto.py src/freemyid/secrets.py src/freemyid/secret_backends.py
  src/freemyid/netpolicy.py src/freemyid/config.py src/freemyid/models.py src/freemyid/state.py
  src/freemyid/consent.py src/freemyid/storage/ src/freemyid/engine/mail src/freemyid/wizard/server.py
  .github/ packaging/ pyproject.toml tools/social/ tools/cloudflare tools/mail/ tools/vendor.sh
  brokers/registry docs/research/ AGENTS.md GEMINI.md CLAUDE.md docs/VENDOR.md docs/vendor/codex-team/ .claude/)

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
    codex exec -s workspace-write -C "$1" -o "$1/.vendor-last-message.txt" "$(role_prompt)
$CODEX_RULES

$2"
  else
    cd "$1" && agy -p "$NO_SHELL

$2" --mode accept-edits --sandbox --print-timeout 3600s ${VENDOR_WATCH:+--remote-control}
  fi
  rm -f "$1/.vendor-last-message.txt.lock" 2>/dev/null || true
  git -C "$1" add -A
  git -C "$1" -c user.name="$(author_of)" commit -q -m "vendor session $(date -u +%FT%TZ)" || true
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
    for d in "${DENY_PREFIXES[@]}"; do [[ "$f" == "$d"* ]] && { echo "IN-HOUSE ONLY: $f"; bad=1; ok=1; }; done
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
    VENDOR="${VENDOR:-$(vendor_of "$file")}"; VENDOR="${VENDOR:-agy}"; AGENT="$(agent_of "$file")"; need_agy
    [ -e "$wt" ] && { echo "$wt exists: use checkin" >&2; exit 2; }
    git -C "$ROOT" worktree add -q -b "$(branch_of "$wo")" "$wt" main
    run_vendor "$wt" "You are in BUILDER mode for work order $wo. Read GEMINI.md and docs/VENDOR.md first.
Change ONLY the allowed paths. End by updating VENDOR_STATUS.md (Done / Next / Questions for the owner / How to test).

$(cat "$file")"
    scope_report "$wo" || true ;;
  checkin)
    wo_check "${1:-}"; wo="$1"; [ $# -ge 2 ] || { echo 'usage: checkin WO-NNN "notes"' >&2; exit 2; }
    file="$(wo_file "$wo")"; wt="$(wt_of "$wo")"
    VENDOR="${VENDOR:-$(vendor_of "$file")}"; VENDOR="${VENDOR:-agy}"; AGENT="$(agent_of "$file")"; need_agy; [ -d "$wt" ] || { echo "not started" >&2; exit 2; }
    run_vendor "$wt" "BUILDER mode, work order $wo, owner check-in. Re-read VENDOR_STATUS.md and the work order below,
then act on the owner's notes. Change ONLY the allowed paths. Update VENDOR_STATUS.md at the end.

OWNER NOTES:
$2

WORK ORDER:
$(cat "$file")"
    scope_report "$wo" || true ;;
  status) wo_check "${1:-}"; scope_report "$1" ;;
  lead)   # Codex team lead: read-only planning conversation with the owner
    VENDOR=codex; AGENT=lead; need_agy; [ $# -ge 1 ] || { echo 'usage: tools/vendor.sh lead "message"' >&2; exit 2; }
    wt="$(mktemp -d "$SCRATCH/lead.XXXXXX")"; rmdir "$wt"
    git -C "$ROOT" worktree add -q --detach "$wt" HEAD
    trap 'git -C "$ROOT" worktree remove --force "$wt" >/dev/null 2>&1 || true' EXIT
    codex exec -s read-only -C "$wt" -o "$SCRATCH/lead-last-reply.md" "$(role_prompt)

MESSAGE FROM MORGAN REYES (owner/engineer):
$1" >/dev/null
    cat "$SCRATCH/lead-last-reply.md" ;;
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
  webcheck)   # owner: build + check the vendor's website changes with the main repo's node_modules
    wo_check "${1:-}"; wt="$(wt_of "$1")"; [ -d "$wt/web" ] || { echo "no worktree" >&2; exit 2; }
    ln -sfn "$ROOT/web/node_modules" "$wt/web/node_modules"
    trap 'command rm -f "$wt/web/node_modules"' EXIT
    ( cd "$wt/web" && pnpm -s build >/dev/null && pnpm -s check && cd "$wt" && "$ROOT/.venv/bin/python" web/scripts/content_check.py web/dist ) ;;
  auto)   # Codex team runs itself: the lead picks work from the roadmap, specialists build, PRs open
    VENDOR=codex; need_agy; n="${1:-3}"
    pw="$SCRATCH/plan.$(date +%s)"; git -C "$ROOT" worktree add -q --detach "$pw" main
    trap 'git -C "$ROOT" worktree remove --force "$pw" >/dev/null 2>&1 || true' EXIT
    existing="$(command ls "$ROOT/docs/vendor" | sed -nE 's/^(WO-[0-9]{3})\.md$/\1/p' | tr '\n' ' ')"
    last="$(echo "$existing" | tr ' ' '\n' | sed -nE 's/WO-0*([0-9]+)/\1/p' | sort -n | tail -1)"
    AGENT=lead
    codex exec -s workspace-write -C "$pw" -o "$SCRATCH/lead-auto-reply.md" "$(role_prompt)

AUTONOMOUS MODE (owner-approved): you decide what the Codex team builds next. Read docs/ROADMAP.md
(release plan section 6: work on the CURRENT next release first), docs/VENDOR.md, docs/vendor/codex-team/lead-log.md
and the existing work orders ($existing). Pick up to $n pieces of valuable, well-bounded work for different
specialists (web-builder, web-designer, app-ui, app-features, test-quality). Write EACH as a new file
docs/vendor/WO-NNN.md numbered from WO-$(printf %03d $((last+1))) upwards, in the template from docs/VENDOR.md, with
Status: open, Vendor: codex, Agent: <role>, testable acceptance criteria, and Allowed paths that do not overlap
each other or any open work order and never include an in-house-only path. Create ONLY those files; edit nothing
else. Then reply with one line per work order: id, agent, title." >/dev/null
    new=()
    for f in "$pw"/docs/vendor/WO-*.md; do
      id="$(basename "$f" .md)"; [ -f "$ROOT/docs/vendor/$id.md" ] && continue
      ag="$(agent_of "$f")"
      if [ "$(vendor_of "$f")" != codex ] || [ -z "$ag" ] || [ "$ag" = lead ] || [ ! -f "$TEAM_DIR/$ag.md" ]; then
        echo "skipping $id: bad Vendor/Agent line" >&2; continue; fi
      bad=0; while read -r a; do for d in "${DENY_PREFIXES[@]}"; do [[ "$a" == "$d"* ]] && bad=1; done; done < <(allowed_paths "$f")
      [ $bad = 1 ] && { echo "skipping $id: allowed paths include an in-house area" >&2; continue; }
      cp "$f" "$ROOT/docs/vendor/$id.md"; new+=("$id")
    done
    [ ${#new[@]} -gt 0 ] || { echo "lead proposed no new work orders"; cat "$SCRATCH/lead-auto-reply.md"; exit 0; }
    git -C "$ROOT" add "${new[@]/#/docs/vendor/}".md
    git -C "$ROOT" -c user.name="Elena Vasquez [freemyid-codex]" commit -q -m "Codex lead: work orders ${new[*]} (autonomous mode)" -- "${new[@]/#/docs/vendor/}".md
    cat "$SCRATCH/lead-auto-reply.md"
    for id in "${new[@]}"; do
      echo "=== $id"; "$0" start "$id" || true
      "$0" pr "$id" || echo "$id: PR not opened (see scope check)"
    done ;;
  close)
    wo_check "${1:-}"; git -C "$ROOT" worktree remove --force "$(wt_of "$1")" && echo "closed $1 (branch $(branch_of "$1") kept)" ;;
  *) sed -n '2,9p' "$0" >&2; exit 2 ;;
esac
