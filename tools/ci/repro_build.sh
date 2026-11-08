#!/usr/bin/env bash
# Reproducible sdist + wheel (BL-IN-42). Usage: tools/ci/repro_build.sh <outdir>
# Needs the pinned toolchain from tools/ci/build-requirements.txt already installed in the
# active Python (build runs with --no-isolation so hatchling is the pinned one, not "latest").
# SOURCE_DATE_EPOCH = commit time of HEAD, so every build of one commit has the same timestamps.
set -euo pipefail
out="${1:?outdir}"
root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$root"
SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-$(git log -1 --format=%ct HEAD)}"
export SOURCE_DATE_EPOCH
export PYTHONHASHSEED=0
rm -rf "$out"
python -m build --no-isolation --outdir "$out" .
( cd "$out" && sha256sum -- * )
