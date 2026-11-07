#!/usr/bin/env bash
# Free My ID backups (orchestrator/devops run this at every checkpoint; safe to re-run).
#  1) FreeMyID/freemyid-backup  (private): full mirror of this repo's branches and tags (history-rewrite safety net).
#  2) FreeMyID/freemyid-private (private): files that are gitignored here and exist nowhere else
#     (full broker registry, research notes, private host hashes).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PRIV="${FREEMYID_PRIVATE_DIR:-$HOME/.local/share/freemyid-private}"
ID=(-c "user.name=Backup Bot [freemyid]" -c "user.email=242299803+GrayManSam@users.noreply.github.com")

git -C "$ROOT" push --quiet --mirror https://github.com/FreeMyID/freemyid-backup.git 2>/dev/null \
  || git -C "$ROOT" push --quiet --force --all https://github.com/FreeMyID/freemyid-backup.git
git -C "$ROOT" push --quiet --force --tags https://github.com/FreeMyID/freemyid-backup.git
echo "mirror: ok"

[ -d "$PRIV/.git" ] || git clone --quiet https://github.com/FreeMyID/freemyid-private.git "$PRIV"
mkdir -p "$PRIV/brokers" "$PRIV/docs" "$PRIV/tools"
cp -p "$ROOT/brokers/registry.yaml" "$PRIV/brokers/"
rsync -a --delete "$ROOT/docs/research/" "$PRIV/docs/research/"
cp -p "$ROOT/tools/private_host_hashes.txt" "$PRIV/tools/"
cd "$PRIV"
git add -A
if git diff --cached --quiet; then echo "private: unchanged"; else
  git "${ID[@]}" commit --quiet -m "Backup $(date -u +%FT%TZ)"; git push --quiet origin HEAD:main; echo "private: pushed"; fi
