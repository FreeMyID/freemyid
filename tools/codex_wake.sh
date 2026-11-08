#!/usr/bin/env bash
# Wake the Codex channel session when its usage window allows it.
#   tools/codex_wake.sh status            -> prints "free" or "limited until <time>" (exit 0 / 1)
#   tools/codex_wake.sh send "message"    -> queues the message to the channel session if free
# Reads ONLY the rate-limit snapshot fields from Codex's local session logs (no conversation text).
# Thread: $CODEX_CHANNEL_THREAD, else the newest interactive (codex-tui) session whose cwd is this repo.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SESS="${CODEX_HOME:-$HOME/.codex}/sessions"

snapshot() {  # prints "<used_percent> <resets_at>" from the newest log that has a primary window
  local f
  for f in $(ls -t "$SESS"/*/*/*/rollout-*.jsonl 2>/dev/null | head -20); do
    local s
    s=$(grep -o '"primary":{"used_percent":[0-9.]*,"window_minutes":[0-9]*,"resets_at":[0-9]*}' "$f" | tail -1) || true
    if [ -n "$s" ]; then
      python3 -c 'import json,sys; d=json.loads(sys.argv[1][10:]); print(d["used_percent"], d["resets_at"])' "$s"
      return 0
    fi
  done
  echo "0 0"
}

thread() {
  if [ -n "${CODEX_CHANNEL_THREAD:-}" ]; then echo "$CODEX_CHANNEL_THREAD"; return; fi
  local f
  for f in $(ls -t "$SESS"/*/*/*/rollout-*.jsonl 2>/dev/null | head -40); do
    head -1 "$f" | python3 -c '
import json, sys
p = json.loads(sys.stdin.readline()).get("payload", {})
if p.get("originator") == "codex-tui" and p.get("cwd") == sys.argv[1]:
    print(p["id"]); sys.exit(0)
sys.exit(1)' "$ROOT" && return 0
  done
  return 1
}

is_free() {
  read -r used resets < <(snapshot)
  local now; now=$(date +%s)
  if python3 -c 'import sys; u,r,n=float(sys.argv[1]),int(sys.argv[2]),int(sys.argv[3]); sys.exit(0 if (u < 95 or n >= r) else 1)' "$used" "$resets" "$now"; then
    echo "free (last snapshot ${used}% used)"; return 0
  fi
  echo "limited until $(date -d "@$resets" '+%Y-%m-%d %H:%M %Z')"; return 1
}

case "${1:-status}" in
  status) is_free ;;
  send)
    [ $# -ge 2 ] || { echo 'usage: tools/codex_wake.sh send "message"' >&2; exit 2; }
    is_free || exit 1
    t=$(thread) || { echo "no Codex channel session found (set CODEX_CHANNEL_THREAD)" >&2; exit 3; }
    codex queue --thread "$t" --message "$2" --resume && echo "queued to $t" ;;
  *) echo 'usage: tools/codex_wake.sh status | send "message"' >&2; exit 2 ;;
esac
