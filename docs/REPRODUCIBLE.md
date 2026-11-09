# Reproducible builds and SBOM

Status as of 2026-11-08 (roadmap 0.3, BL-IN-42). Owner: devops-engineer.

## Python sdist and wheel: reproducible, and CI checks it

What makes two builds of one commit byte-identical:

- The build backend and its whole toolchain are pinned with hashes in `tools/ci/build-requirements.txt`
  (hatchling, build, packaging, pathspec, pluggy, pyproject-hooks, trove-classifiers; pure-Python wheels, any OS).
  twine and its dependencies (used only for CI's `twine check`) are pinned separately in
  `tools/ci/twine-requirements.txt`, with hashes resolved for Linux x86_64 and CPython 3.12 (all CI uses).
  CI installs both files together with `pip install --require-hashes`. `pyproject.toml` still lists `hatchling>=1.24` for people building by hand; the CI
  build ignores that range because it runs `python -m build --no-isolation` against the pinned install.
- `SOURCE_DATE_EPOCH` is the commit time of the built commit (`git log -1 --format=%ct`). Hatchling uses it for every
  file timestamp in the sdist and wheel. (The old fixed value `1700000000` in `pypi.yml` is gone.)
- `tools/ci/repro_build.sh <outdir>` is the single build entry point, used by both `build.yml` (job `dist`) and
  `pypi.yml` (job `build`). It also sets `PYTHONHASHSEED=0`.
- The `dist` job in `build.yml` builds twice, the second time from a fresh `git worktree` of the same commit in a
  different directory, and fails if `sha256sum` of the files differs.

Checked locally on 2026-11-08: two builds of the same tree from two different directories gave identical
SHA-256 for `freemyid-0.2.0.tar.gz` and `freemyid-0.2.0-py3-none-any.whl`. Only CI proves it on the GitHub runner
image.

To reproduce a release yourself (Linux, or Windows through WSL): check out the tag,
`pip install --require-hashes -r tools/ci/build-requirements.txt` with Python 3.12 (twine is not needed), run `tools/ci/repro_build.sh dist`, and compare with the files on PyPI. Caveats: the same Python
minor version is expected; the package is pure Python, but the hash comparison has only been tested on Linux, so compare hashes only on Linux or WSL. `tools/ci/repro_build.sh` calls `sha256sum`, which macOS does not ship by default; on a Mac install GNU coreutils (for example `brew install coreutils`) or compare with `shasum -a 256` by hand, and treat a Mac result as untested.

## SBOM

Each GitHub release carries `freemyid.cdx.json`, a CycloneDX 1.x JSON SBOM of the wheel installed into a clean venv
(so it lists the resolved runtime dependencies), made by syft (`anchore/sbom-action`, pinned by SHA, syft v1.18.1).
It is listed in `SHA256SUMS.txt` next to the installer. The SBOM job runs separately from the build, verifies the dist
hashes first, and the release job verifies the SBOM hash recorded by that job before uploading (SEC-111 pattern). The
PyPI workflow keeps its own SPDX SBOM as a workflow artifact. The Docker image has its own SPDX SBOM attestation.

Residual risk (SEC-121): the syft version is pinned (`v1.18.1`), but `anchore/sbom-action` downloads the syft binary
at run time and we have no independent hash pin for it. The action's own download step may compare against the
checksums file published on the same GitHub release; that catches corruption, not a compromised release. The SBOM job
has read-only permissions and cannot change the wheel, which limits the damage to a wrong or missing SBOM, plus one
more risk: the action holds the job's `GITHUB_TOKEN` (its `github-token` input defaults to it) and runs syft in that
environment, so a compromised syft binary may be able to read and send out that token. Read-only permissions limit what that token can do (read this repository's contents until the
job ends); they do not stop it being disclosed. Fix later by
pinning the syft release archive by sha256 in a step of our own.

What the SBOM does not cover: the Windows installer. It describes the Python wheel and its dependencies, not the
PyInstaller bundle, the Python runtime inside it, or Inno Setup. Treat it as a close approximation for the exe's
Python packages, not an exact inventory.

## Windows exe (PyInstaller + Inno Setup): NOT reproducible today

We do not claim byte-identical installers. Reasons, none of them fixed yet:

- Dependencies are not locked. `pip install ".[package,dev]"` resolves the newest allowed `pyinstaller`, `pywebview`
  and every transitive dependency at build time, so a rebuild next week can differ.
- PyInstaller is not told to be deterministic. Its archive and bootloader embed build-time data, and PE headers get
  timestamps. We do not set `SOURCE_DATE_EPOCH` for this job and have not tested whether it is enough.
- Inno Setup is installed from Chocolatey at whatever version is current (or the runner's preinstalled one), and its
  output embeds a compile timestamp unless fixed.
- The `windows-latest` runner image (Python 3.12 patch version, MSVC runtime) changes underneath us.
- The full broker registry, when present, is copied in from a private repo, so outsiders cannot rebuild the same input.
- The exe is not code-signed yet (SignPath application pending); signing would add a signature that is not
  reproducible by design.

What you can rely on today: the published `SHA256SUMS.txt` matches the file we uploaded (CI computes it, the website
step re-checks it), and the source for the exe is the tagged commit. Nobody else can rebuild the same bytes.

Possible next steps, none started: a hash-locked requirements file for the packaging job, a pinned Inno Setup
version, a double-build comparison of the PyInstaller `dist/FreeMyID` tree, and checking what differs between two
builds before deciding if byte-identical is realistic. Windows installers are rarely bit-for-bit reproducible, so
the realistic goal may be "same file contents, differing only in timestamps and signature".
