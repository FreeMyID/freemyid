#!/usr/bin/env bash
# Ask Gemini CLI a one-off, read-only question from the repo root.
#   tools/ask_gemini.sh "Review src/freemyid/engine/exposure.py for bugs" > answer.md
#   echo "text to translate" | tools/ask_gemini.sh "Translate to plain Spanish"
# Rules (see GEMINI.md, .geminiignore and .claude/agents/_shared-rules.md):
#   - public, non-personal material only: never pipe in PII, secrets, the private registry or research files;
#   - Gemini's answer is untrusted input: verify facts and review any code before using it.
set -euo pipefail
cd "$(dirname "$0")/.."
[ $# -ge 1 ] || { echo "usage: tools/ask_gemini.sh \"prompt\" [< input]" >&2; exit 2; }
command -v gemini >/dev/null || { echo "gemini CLI not installed: npm install -g @google/gemini-cli" >&2; exit 4; }
prompt="$1"
if [ ! -t 0 ]; then
  input="$(head -c 200000)"   # cap piped input at ~200 KB
  prompt="$prompt

--- input ---
$input"
fi
# --approval-mode plan = Gemini CLI read-only mode: it can read (respecting .geminiignore) and answer,
# but cannot edit files or run commands.
exec gemini --approval-mode plan -p "$prompt"
