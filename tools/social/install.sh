#!/usr/bin/env bash
# Free My ID social poster: install or update the read-only copy that the
# systemd user timer runs. Lead-only step, after reviewing tools/social/.
#
#   tools/social/install.sh            first install
#   tools/social/install.sh --update   rebuild from the repo and re-pin the hash
#
# What it does (as your normal user, never root):
#   1. Builds ~/.local/share/freemyid-poster/ from scratch: poster.py, verify.sh,
#      and its own venv with only the hash-pinned packages in requirements.lock
#      (httpx, keyring and their deps). pip itself is removed afterwards.
#   2. Writes a manifest (FILES, LINKS, SHA256SUMS) and makes everything
#      read-only: files 0444 (0555 if executable), directories 0555.
#   3. Copies (never links) the unit and timer into ~/.config/systemd/user at
#      0444. The unit pins the SHA-256 of SHA256SUMS and checks it on every start.
#   4. Prints the pinned hash and the systemctl commands to run next.
# It never runs systemctl, never enables the timer, and never touches the repo.
#
# Options:
#   --update          replace an existing install (required if one exists)
#   --python PATH     interpreter for the venv (default /usr/bin/python3, >= 3.12);
#                     must resolve to a root-owned file in a root-owned directory
#   --wheelhouse DIR  install from local wheels only (pip --no-index --find-links)
#
# Test seam: FREEMYID_POSTER_TEST_SKIP_PIP=1 creates an empty venv without
# installing packages. Only tests/test_social_poster.py uses it, on a temp HOME.
set -euo pipefail
umask 022

die() { echo "install.sh: $*" >&2; exit 1; }

usage() { sed -n '2,/^set -euo/{/^set -euo/d;s/^# \{0,1\}//;p}' "${BASH_SOURCE[0]}"; }

[[ $(id -u) -ne 0 ]] || die "refusing to run as root; run it as your normal user"

mode=install
python=/usr/bin/python3
wheelhouse=""
while (($#)); do
    case $1 in
        --update) mode=update ;;
        --python) python=${2:?--python needs a path}; shift ;;
        --wheelhouse) wheelhouse=${2:?--wheelhouse needs a directory}; shift ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown option: $1 (see --help)" ;;
    esac
    shift
done

[[ ${HOME:-} == /* && -d $HOME ]] || die "HOME must be an existing absolute directory"
src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo=$(cd -- "$src/../.." && pwd -P)
home=$(cd -- "$HOME" && pwd -P)
prefix=$home/.local/share/freemyid-poster
unit_dir=$home/.config/systemd/user
seo_dir=$repo/docs/marketing/seo

# These paths are pasted into the unit and into sh -c lines: keep them boring.
for p in "$repo" "$prefix"; do
    [[ $p =~ ^/[A-Za-z0-9._/-]+$ ]] || die "path has spaces or special characters: $p"
done
for f in poster.py verify.sh requirements.lock freemyid-poster.service freemyid-poster.timer; do
    [[ -f $src/$f ]] || die "missing $src/$f"
done
[[ -d $seo_dir ]] || die "missing $seo_dir (the unit's only writable path)"
# The venv's python symlink and the stdlib are outside the pinned manifest, so they
# must be root-owned and not group/world-writable (SEC-81b). Resolve symlinks first and
# build the venv from the real path, so no user-owned link sits in between.
root_only() { # $1 = path; true if it and its directory are root-owned and not g/o-writable
    local d
    for d in "$1" "$(dirname -- "$1")"; do
        [[ $(stat -L -c %u -- "$d") == 0 ]] || return 1
        [[ -z $(find "$d" -maxdepth 0 -perm /022 -print) ]] || return 1
    done
}
py_real=$(readlink -e -- "$python") || die "no such interpreter: $python"
[[ -f $py_real && -x $py_real ]] || die "$python is not an executable file"
root_only "$py_real" \
    || die "$python ($py_real) is not root-owned or is writable by others; use the system interpreter (/usr/bin/python3)"
python=$py_real
"$python" -I -c 'import sys; sys.exit(sys.version_info < (3, 12))' 2>/dev/null \
    || die "$python is not Python 3.12 or newer (use --python)"
stdlib=$("$python" -I -c 'import sysconfig; print(sysconfig.get_paths()["stdlib"])') \
    || die "cannot ask $python for its stdlib path"
if [[ ! -f $stdlib/os.py ]] || ! root_only "$stdlib/os.py"; then
    die "the stdlib of $python ($stdlib) is not root-owned or is writable by others"
fi
[[ -z $wheelhouse || -d $wheelhouse ]] || die "no such wheelhouse: $wheelhouse"

[[ ! -L $prefix ]] || die "$prefix is a symlink; remove it by hand"
if [[ $mode == install ]]; then
    [[ ! -e $prefix ]] || die "already installed at $prefix; use --update"
else
    [[ -d $prefix ]] || die "nothing installed at $prefix; run without --update"
fi
case $prefix in
    "$home"/.local/share/freemyid-poster) ;;
    *) die "unexpected install path: $prefix" ;;
esac

remove_prefix() {
    if [[ -d $prefix && ! -L $prefix ]]; then
        chmod -R u+w -- "$prefix"
        rm -rf -- "$prefix"
    fi
}

# ---------------------------------------------------------------- build the copy
[[ $mode == update ]] && remove_prefix
trap 'echo "install.sh: failed; removing the partial copy (the poster will not run)" >&2; remove_prefix' ERR
mkdir -p -- "$(dirname -- "$prefix")"
mkdir -m 0755 -- "$prefix"
install -m 0644 "$src/poster.py" "$src/verify.sh" "$src/requirements.lock" "$prefix/"

if [[ -n ${FREEMYID_POSTER_TEST_SKIP_PIP:-} ]]; then
    echo "install.sh: TEST MODE, venv has no packages"
    "$python" -m venv --without-pip "$prefix/venv"
else
    "$python" -m venv "$prefix/venv"
    pip_args=(--isolated --no-input --disable-pip-version-check --no-cache-dir
              install --quiet --require-hashes --only-binary=:all: --no-deps
              -r "$prefix/requirements.lock")
    [[ -z $wheelhouse ]] || pip_args+=(--no-index --find-links "$wheelhouse")
    "$prefix/venv/bin/python" -I -B -m pip "${pip_args[@]}"
    "$prefix/venv/bin/python" -I -B -m pip --isolated --disable-pip-version-check \
        uninstall --quiet --yes pip
    "$prefix/venv/bin/python" -I -B -c 'import httpx, keyring'
    "$prefix/venv/bin/python" -I -B "$prefix/poster.py" --help >/dev/null
fi

# ---------------------------------------------------------------- manifest
cd -- "$prefix"
: > FILES
: > LINKS
find . -type l -printf '%P -> %l\n' | LC_ALL=C sort > LINKS
find . -type f ! -path ./SHA256SUMS -printf '%P\n' | LC_ALL=C sort > FILES
tr '\n' '\0' < FILES | xargs -0 sha256sum -- > SHA256SUMS
sums=$(sha256sum SHA256SUMS | cut -d' ' -f1)
[[ $sums =~ ^[0-9a-f]{64}$ ]] || die "could not hash SHA256SUMS"

find . -type f -exec chmod a-w {} +
chmod 0444 poster.py verify.sh
find . -type d -exec chmod 0555 {} +
cd /

# self-check: exactly what the unit runs before every start
(cd -- "$prefix" && sha256sum --check --strict --quiet SHA256SUMS)
sh "$prefix/verify.sh" "$prefix"
trap - ERR

# ---------------------------------------------------------------- units (copies)
mkdir -p -- "$unit_dir"
put_unit() { # $1 = template file name; writes a 0444 copy via temp + rename
    local tmp
    tmp=$(mktemp "$unit_dir/.$1.XXXXXX")
    sed -e "s|@PREFIX@|$prefix|g" -e "s|@REPO@|$repo|g" -e "s|@SUMS_SHA256@|$sums|g" \
        "$src/$1" > "$tmp"
    if grep -q '@[A-Z_0-9]*@' "$tmp"; then
        rm -f -- "$tmp"
        die "unfilled placeholder in $1"
    fi
    chmod 0444 "$tmp"
    mv -f -T -- "$tmp" "$unit_dir/$1" # replaces an old symlink itself, never its target
}
put_unit freemyid-poster.service
put_unit freemyid-poster.timer

echo
echo "Installed read-only copy:  $prefix"
echo "Units (0444 copies):       $unit_dir/freemyid-poster.{service,timer}"
echo "Pinned SHA256SUMS hash:    $sums"
echo
echo "Not done by this script. Run these yourself when ready:"
echo "  systemctl --user daemon-reload"
if [[ $mode == install ]]; then
    echo "  systemctl --user enable --now freemyid-poster.timer"
fi
echo "  systemctl --user list-timers freemyid-poster.timer"
