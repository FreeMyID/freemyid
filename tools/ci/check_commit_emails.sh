#!/usr/bin/env bash
# Fail if any commit in BASE..HEAD has an author or committer email that is not
# <id>+<name>@users.noreply.github.com, <name>@users.noreply.github.com or
# noreply@github.com. Offending addresses are masked, never printed in full.
# Usage: check_commit_emails.sh BASE HEAD   (BASE all zeros = new branch)
set -euo pipefail
base="${1:?base}"; head="${2:?head}"
# Known historical commits (SEC-93c); never re-flagged.
ALLOW="d647b5876cb16ab67c83c5ec265adff826911bfd f8f19a22123622c4c89ca10c1559715a988bf791 c52cab2aabd9026c4cac4836450c7cf5674e6306"
ok_re='^([A-Za-z0-9._-]+|[0-9]+\+[A-Za-z0-9._-]+)@users\.noreply\.github\.com$|^noreply@github\.com$'
mask() { local l="${1%@*}" d="${1#*@}"; printf '%s***@%s***' "${l:0:1}" "${d:0:1}"; }

die() { echo "::error::check_commit_emails: $*" >&2; exit 2; }

git rev-parse --verify --quiet "$head^{commit}" >/dev/null \
  || die "HEAD ref '$head' does not resolve to a commit; refusing to pass"

if [[ "$base" =~ ^0+$ ]]; then
  range=("$head" --not --remotes=origin)
  first=$(git rev-list -n1 "${range[@]}") || die "git rev-list failed"
  [[ -n "$first" ]] || range=(-n1 "$head")
else
  git rev-parse --verify --quiet "$base^{commit}" >/dev/null \
    || die "BASE ref '$base' does not resolve to a commit (force push or shallow checkout?); refusing to pass"
  range=("$base..$head")
fi

log=$(git log --format='%H %ae %ce' "${range[@]}") || die "git log failed for range '${range[*]}'"

if [[ -z "$log" ]]; then
  echo "no commits to check"
  exit 0
fi

bad=0
while read -r sha ae ce; do
  [[ " $ALLOW " == *" $sha "* ]] && continue
  for pair in "author:$ae" "committer:$ce"; do
    role="${pair%%:*}"; email="${pair#*:}"
    if ! [[ "$email" =~ $ok_re ]]; then
      echo "::error::commit ${sha:0:7}: $role email $(mask "$email") is not a GitHub noreply address"
      bad=1
    fi
  done
done <<< "$log"

if (( bad )); then
  echo "Fix: git config user.email <id>+<name>@users.noreply.github.com, then amend/rebase the commits." >&2
  echo "Web merges: turn on 'Keep my email addresses private' in GitHub settings." >&2
  exit 1
fi
echo "commit emails OK"
