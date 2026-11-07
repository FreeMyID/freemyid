#!/bin/sh
# Free My ID poster: run by the systemd unit (ExecStartPre) AFTER the pinned
# SHA256SUMS and every file it lists have been checked. Refuses to start if a
# file or symlink was added, or anything was made writable. Installed read-only
# by tools/social/install.sh; it is itself listed in SHA256SUMS.
set -eu
cd "$1"
fail() {
    echo "freemyid-poster: $1 in $PWD; refusing to run (reinstall with install.sh --update)" >&2
    exit 1
}
find . -type f ! -path ./SHA256SUMS -printf '%P\n' | LC_ALL=C sort | cmp -s - FILES \
    || fail "unexpected or missing files"
find . -type l -printf '%P -> %l\n' | LC_ALL=C sort | cmp -s - LINKS \
    || fail "unexpected or changed symlinks"
if [ -n "$(find . \( -type f -o -type d \) -perm /222 -print -quit)" ]; then
    fail "a writable file or directory"
fi
