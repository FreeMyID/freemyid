#!/usr/bin/env bash
# Wake the Grok vendor session (in-house tool; vendors never run or edit it).
#   tools/grok_wake.sh status            -> live interactive session? last session for this repo? (exit 0 if one exists)
#   tools/grok_wake.sh send "message"    -> resumes the newest repo session for ONE headless turn with the message,
#                                           under the freemyid sandbox. Refuses while an interactive session is open
#                                           (a message can't be pushed into a running TUI): the owner is asked to
#                                           type "read docs/vendor/CLAUDE_TO_GROK.md" there instead.
# Reads only ~/.grok/active_sessions.json and the session folder names (no conversation text).
# Session: $GROK_CHANNEL_SESSION, else the newest session whose cwd is this repo or one of its worktrees.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GROK="${GROK_BIN:-$HOME/.grok/bin/grok}"
GHOME="${GROK_HOME:-$HOME/.grok}"

live() {  # prints "<session_id> <pid> <cwd>" for each open interactive session under the repo's parent folder
  python3 - "$GHOME/active_sessions.json" "$ROOT" <<'PY'
import json, os, sys
try:
    rows = json.load(open(sys.argv[1]))
except (OSError, ValueError):
    rows = []
root = sys.argv[2]
for r in rows:
    pid, cwd = r.get("pid"), r.get("cwd", "")
    if not pid or not (root.startswith(cwd) or cwd.startswith(root)):
        continue
    try:
        os.kill(int(pid), 0)
    except OSError:
        continue
    print(r.get("session_id"), pid, cwd)
PY
}

newest() {  # newest session id stored for this repo or a folder that contains it
  if [ -n "${GROK_CHANNEL_SESSION:-}" ]; then echo "$GROK_CHANNEL_SESSION"; return 0; fi
  python3 - "$GHOME/sessions" "$ROOT" <<'PY'
import os, sys, urllib.parse
base, root = sys.argv[1], sys.argv[2]
best = None
for d in os.listdir(base) if os.path.isdir(base) else []:
    cwd = urllib.parse.unquote(d)
    if not (root.startswith(cwd) or cwd.startswith(root)):
        continue
    for s in os.listdir(os.path.join(base, d)):
        p = os.path.join(base, d, s)
        if os.path.isdir(p) and (best is None or os.path.getmtime(p) > best[0]):
            best = (os.path.getmtime(p), s)
if best:
    print(best[1]); sys.exit(0)
sys.exit(1)
PY
}

case "${1:-status}" in
  status)
    l=$(live)
    if [ -n "$l" ]; then echo "interactive Grok session open: $l"; exit 0; fi
    s=$(newest) && { echo "no open session; newest repo session: $s"; exit 0; }
    echo "no Grok session found for this repo"; exit 1 ;;
  send)
    [ $# -ge 2 ] || { echo 'usage: tools/grok_wake.sh send "message"' >&2; exit 2; }
    l=$(live)
    if [ -n "$l" ]; then
      echo "interactive Grok session is open ($l)."
      echo "Ask the owner to type there: read docs/vendor/CLAUDE_TO_GROK.md"; exit 4
    fi
    s=$(newest) || { echo "no Grok session found (set GROK_CHANNEL_SESSION)" >&2; exit 3; }
    "$GROK" --resume "$s" --sandbox freemyid --no-subagents --disable-web-search \
      --output-format plain -p "$2" && echo "delivered to $s" ;;
  *) echo 'usage: tools/grok_wake.sh status | send "message"' >&2; exit 2 ;;
esac
