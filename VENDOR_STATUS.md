# WO-167 status

## Done

- Added `distro/CHECKLIST.md` with 22 release-day entries across AUR, Flatpak,
  Homebrew, Nix, Scoop, and winget.
- Recorded each current placeholder or release substitution with file and line,
  replacement, responsibility, and state. All states are `coming`: release
  data covers the Windows installer, not these channels.
- Marked source-file commands unverified and noted that Flatpak pip-source
  generation needs network access.

## Next

- In-house release tooling and channel maintainers should complete the listed
  release-day steps when each channel is ready to publish.

## Questions for the owner

- None.

## How to test

- Unverified/unavailable: `PYTHONPATH=src .venv/bin/python -m pytest -q
  tests/copilot/` could not run because `.venv/bin/python` is absent in this
  worktree (exit 127).
- Passed: `git diff --check` and `git diff --cached --check` found no
  whitespace errors.
