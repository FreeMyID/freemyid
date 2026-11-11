# Python dependencies and safe updates

Free My ID has separate dependency lists for the installed app, optional features, and release
tooling. Keep each list in its current format: ordinary version ranges for the app, and exact
versions plus hashes for the reproducible build tools.

## Runtime and optional dependencies

The `[project].dependencies` list in `pyproject.toml` is the app's runtime set. Most entries are
lower bounds, such as `pydantic>=2.7`; pip resolves a compatible version when installing the app.
Extras add dependencies only when a task needs them: `dev` for tests and development tools, `pdf`
for PDF output, `package` for Windows packaging, and `tray` for tray support. The Windows build
installs `.[package,dev]`; the regular CI test job installs `.[dev]`.
(`pyproject.toml:27-50`; `.github/workflows/build.yml:37-40,226-227`)

Playwright has a deliberate upper bound: `playwright>=1.45,<1.65`. The v0.3.1 pin records that
1.65, released 2026-11-09, had not been tested on Windows, and says to bump only with a VM run.
Treat a move past this cap as a compatibility change, not a routine patch update.
(`pyproject.toml:36`; v0.3.1 release note: `docs/vendor/CLAUDE_TO_CODEX.md:928-932`)

## CI and release-tool dependencies

The test matrix uses Python 3.12 on Ubuntu, macOS, and Windows. It installs the project with the
`dev` extra, runs Ruff and pytest, and installs Chromium separately for each operating system.
Linux uses `playwright install --with-deps`; macOS and Windows install the browser without that
Linux system-package option. Browser tests must be required during validation so a missing browser
does not silently count as a pass. (`.github/workflows/build.yml:20-52`;
`docs/dev/TESTING.md:28-34`)

The source-distribution and wheel build use `tools/ci/build-requirements.txt`, and the upload check
adds `tools/ci/twine-requirements.txt`. These files pin every tool and transitive dependency to an
exact version and SHA-256 hash. CI installs them with `--require-hashes`, builds with the pinned
toolchain, checks the result with Twine, and compares a second build for reproducibility.
(`tools/ci/build-requirements.txt:1-12`; `tools/ci/twine-requirements.txt:1-6`;
`.github/workflows/build.yml:100-114`)

Dependabot opens weekly update PRs. Python and GitHub Actions minor/patch updates are grouped by
ecosystem; major updates arrive separately with their own changelog review. The `/tools/ci` Python
pins have their own update rule and must be reviewed with regenerated hashes. Nothing auto-merges.
(`.github/dependabot.yml:1-23`)

The Docker image installs `libatomic1` before the package and Chromium. The Dockerfile explains
that Playwright's bundled Node needs this library starting with Playwright 1.65, and the slim base
image does not include it. Keep the package installation if the Playwright pin moves past 1.65;
then build and smoke-test the image as part of that change.
(`packaging/docker/Dockerfile:22-28`)

## Safe dependency bump procedure

1. **Choose the right list.** Change the app's compatible range in `pyproject.toml` for a runtime
   dependency. Change `tools/ci/*-requirements.txt` only for build/upload tooling. Keep those
   toolchain files exact-pinned and hash-checked; never remove `--require-hashes` to get a build
   through. (`pyproject.toml:27-50`; `tools/ci/build-requirements.txt:1-5`;
   `tools/ci/twine-requirements.txt:1-5`)
2. **Review compatibility before merging.** Read the dependency's release notes, check supported
   Python versions and platform wheels, and consider its transitive changes. For hash-pinned tools,
   regenerate hashes in the approved release environment and review the complete dependency set.
   Dependabot PRs are reviewed; they do not merge themselves. (`.github/dependabot.yml:1-4,13-23`)
3. **Run the full CI matrix.** Require lint, the full test suite, and browser tests on Ubuntu,
   macOS, and Windows. Verify that each runner installs the matching Chromium build and that no
   required browser test is merely skipped. The CI matrix and install steps are in
   `.github/workflows/build.yml:20-52`; browser-test skip behavior is described in
   `docs/dev/TESTING.md:28-34`.
4. **Check affected packages.** For build or release tool changes, build the source distribution
   and wheel, run the strict Twine check, and confirm the reproducibility job passes
   (`.github/workflows/build.yml:100-114`). For a Playwright upgrade, build and smoke-test the
   Docker image with `libatomic1` present (`packaging/docker/Dockerfile:22-28`).
5. **Before release, do a Windows VM check.** Install and launch the packaged app on Windows; check
   first-start and slow-start behavior as well as the normal app window. CI's Windows test job does
   not replace this manual packaged-app check. A prior Windows VM run exposed a first-start delay
   that needed clearer splash guidance (`docs/vendor/CLAUDE_TO_CODEX.md:898-899`). The current
   Playwright pin also explicitly requires a VM run before moving past 1.65
   (`pyproject.toml:36`).

Do not widen a version range or remove a pin just to quiet an update bot. If a dependency cannot
pass the platform and release checks, keep the current constraint and document what still needs
verification.
