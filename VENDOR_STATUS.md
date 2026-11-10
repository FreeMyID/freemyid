# WO-310 VENDOR_STATUS

Vendor: Linda Moreau (Grok). Worktree: `.vendor-wt/wo-310`. Docs only.

## Done

- Added one new section, "The blue Windows box", to `docs/user/troubleshooting.md`.
  It is written in plain words. It covers the blue "Windows protected your PC"
  box and "Unknown publisher", says the installer is not code-signed yet, and
  tells a reader (with a helper) how to compare the file with the SHA-256 on
  the download page. It does not tell anyone to turn security off, and it has
  no GitHub link.
- The HTML comment on the checksum cites `site_src/data/release.yaml` line 8,
  the SHA-256 for version 0.3.0 in this tree. The words a reader sees say to
  use the code on the download page, not a pasted hash.
- Same section: "The download page shows a certificate warning at work or
  school." A network filter is checking web traffic. Try another network.
  Never ignore a certificate warning on other sites.
- Example person only: Jane Q Testperson, Springfield IL.
- Left the WO-301 section "Starting and updating" in place, including this
  exact sentence: "The first time can take up to a minute. Please wait; there
  is no need to click it again."
- Added a short pointer under the page intro so that section can be found.
  Did not rewrite "Starting and updating".
- Did not add a test. Existing doc and wording guards already cover this file.
  No duplicate guard.

## Next

- Owner review of the new section. No further edits planned in this session.

## Questions for the owner

- In this tree, `site_src/data/release.yaml` and `site/download/index.html`
  still show version 0.3.0 and the line 8 SHA-256. The "Starting and updating"
  section, which I did not change, says version 0.3.1, and `AGENTS.md` says
  v0.3.1 is released. Readers are told to use the code on the download page.
  Should release data be updated to 0.3.1 before this page is treated as
  current? I did not edit `site_src/` or `site/`.
- WO-310 says to note the start on the Grok board. Allowed paths here are only
  `docs/user/troubleshooting.md` and `VENDOR_STATUS.md`, so I did not edit
  `docs/vendor/GROK_BOARD.md`. Please mark WO-310 on the board if it should
  not stay "queued".

## How to test

From this worktree:

```
PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot tests -k "doc or wording"
```

Second run (same command, with `-rx` so the xfail name is visible): exit 0.
Exact counts: 560 passed, 17 skipped, 2102 deselected, 1 xfailed, 1 warning
in 5.67s.

The one xfail is pre-existing and not in this work order's file:

`tests/copilot/test_cp_never_asks_parity.py::test_existing_copy_has_all_core_promise_concepts[docs/FRIDGE_CARD.md]`

Reason: `docs/FRIDGE_CARD.md:17 missing never charges you`.

The new external link listed and not fetched is
`docs/user/troubleshooting.md:160` `https://freemyid.org/download/#checksum`.

## Findings

- No product bug in `src/`. No new strict xfail. I did not edit `src/`.
- Doc mismatch, left as-is outside the new section: "Starting and updating"
  says version 0.3.1 (`docs/user/troubleshooting.md:89`). The checksum this
  tree publishes is version 0.3.0 at `site_src/data/release.yaml:5` and
  `site_src/data/release.yaml:8`
  (`a234c8cd560e436c81f48aacffb91da6408618d979f039bf2f5612de57ccfe9c`).
  The built page `site/download/index.html` shows that same version and code
  under "For helpers: check the download is genuine".
- Could not verify: the live freemyid.org download page (no network); a real
  Windows "protected your PC" box; running `Get-FileHash` on Windows; that
  the line 8 SHA-256 matches an installer file on disk (no installer was
  hashed). The PowerShell line follows the download page command
  `Get-FileHash .\FreeMyIDSetup.exe`, with the Downloads path and
  `-Algorithm SHA256` added so one paste works. That form was not run here.
- 17 skipped tests in the required run were not reclassified as passes. I did
  not investigate each skip name beyond the xfail above.
