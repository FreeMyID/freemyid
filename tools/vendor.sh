#!/usr/bin/env bash
# Google Antigravity CLI (`agy`) as an outside vendor. Owner-approved 2026-11-07.
# Gemini CLI no longer works for individual accounts (Google moved it to Antigravity).
#
#   tools/vendor.sh ask   "question"           read-only answer (plan mode), printed to stdout
#   tools/vendor.sh build <task-name> "spec"   vendor writes code on branch vendor/<task-name>
#
# Safety:
#   * The vendor ONLY ever sees a fresh git worktree of HEAD. Gitignored private files
#     (brokers/registry.yaml, docs/research/, keys, recovery codes...) are never in it.
#   * --sandbox restricts its terminal. It never pushes: there is no credential in the worktree
#     remote config it can use, and our review merges, not the vendor.
#   * Its output is UNTRUSTED vendor work: the owning agent + qa-security review the diff
#     (tools/vendor.sh build prints `git diff main...vendor/<task>`) before anything merges.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRATCH="${VENDOR_DIR:-${TMPDIR:-/tmp}/freemyid-vendor}"
command -v agy >/dev/null || { echo "agy not installed (curl -fsSL https://antigravity.google/cli/install.sh | bash)" >&2; exit 4; }
mode="${1:-}"; shift || true
mkdir -p "$SCRATCH"
case "$mode" in
  ask)
    [ $# -ge 1 ] || { echo 'usage: tools/vendor.sh ask "question"' >&2; exit 2; }
    wt="$(mktemp -d "$SCRATCH/ask.XXXXXX")"
    git -C "$ROOT" worktree add -q --detach "$wt" HEAD
    trap 'git -C "$ROOT" worktree remove --force "$wt" >/dev/null 2>&1 || true' EXIT
    cd "$wt" && agy -p "$(cat "$ROOT/GEMINI.md")

$1" --mode plan --sandbox --print-timeout 600s
    ;;
  build)
    [ $# -ge 2 ] || { echo 'usage: tools/vendor.sh build <task-name> "spec"' >&2; exit 2; }
    name="$1"; spec="$2"
    [[ "$name" =~ ^[a-z0-9-]{3,40}$ ]] || { echo "task name: lowercase letters, digits, dashes" >&2; exit 2; }
    branch="vendor/$name"; wt="$SCRATCH/$name"
    git -C "$ROOT" worktree add -q -b "$branch" "$wt" HEAD
    cd "$wt"
    agy -p "You are an outside vendor writing code for Free My ID. Follow GEMINI.md, except that for
this task you MAY edit and create files inside this folder. Do not run git, do not install
packages, do not access the network except to read documentation. Finish with a short summary
of every file you changed and how to test it.

TASK: $spec" --mode accept-edits --sandbox --print-timeout 1800s
    git add -A && git -c user.name="Vendor (Antigravity) [freemyid-vendor]" commit -q -m "vendor: $name" || true
    echo "--- vendor diff for review: git -C $ROOT diff main...$branch"
    git -C "$ROOT" diff --stat "main...$branch"
    ;;
  *) echo 'usage: tools/vendor.sh ask "q" | build <task-name> "spec"' >&2; exit 2 ;;
esac
