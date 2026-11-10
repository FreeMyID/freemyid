# WO-306 vendor status

Vendor: Margaret Lund (Grok). Worktree: `.vendor-wt/wo-306`. Files edited: `FAMILY_QUICK_START.md`, `VENDOR_STATUS.md`. No edits under `src/`, `web/`, `docs/vendor/`, or `tests/`.

## Done

`FAMILY_QUICK_START.md` is one page again (about 58 visible lines; the HTML comment does not show when the page is rendered). It now matches the 0.3.1 app:

- Today is one card. Everything else is behind **More: safety steps and details**.
- The answer buttons are **Yes, this is me** and **No, this is not me**. The first answer stays.
- Practice mode still searches. No removal requests go out until the person says so. The page does not say "nothing is sent", "guarantee", "erase", or "100%".
- First start uses this sentence: "The first time can take up to a minute. Please wait; there is no need to click it again."
- Updating with the new installer keeps the person's details and the scheduled check. The app may need to be opened again.
- The app version is 0.3.1. The website download is version 0.3.0, about 64.5 MB, dated 2026-11-09. The page does not call 0.2.0 the current download.
- The only example person is Jane Q Testperson, Springfield IL.
- `src/freemyid` lines are cited in the HTML comment as `file.py:line`. The splash is cited in words ("splash_win.py, line 20"), not as `packaging/windows/splash_win.py:20`.

The short "never asks" sentence and the "only the age" age line are still in the page, so the existing wording tests still apply.

## Next

Owner review of `FAMILY_QUICK_START.md` on return. No further edit from this work order unless the owner asks. A later work order can align `docs/USER_GUIDE.md` and `docs/HELPER_GUIDE.md`, and can fix the welcome sentence in `src/` if the owner wants that.

## Questions for the owner

- The guide describes the 0.3.1 app, and it says the file on freemyid.org is still 0.3.0. Should that stay until `site_src/data/release.yaml` is updated to 0.3.1?
- `src/freemyid/wizard/ui.py:265` says sites are asked "in the written form they have to answer," with no state-law qualifier. Is that meant as "their own form," or is it the claim `docs/POSITIONING.md:51` forbids? I did not change it.
- The first-start sentence you required is not one string on the first splash. splash_win.py, line 20, says "The first time can take up to a minute" and "Please wait." "Please wait; there is no need to click it again" is the slow splash (splash_win.py, line 23), after 120 seconds. Should a later change put the full sentence on the first splash?

## How to test

From this worktree:

`PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot tests -k "doc or wording or family"`

Result: **571 passed, 18 skipped, 2086 deselected, 1 xfailed**, 1 warning, in about 6 seconds.

The xfail is the existing one, not from this work order: `tests/copilot/test_cp_never_asks_parity.py::test_existing_copy_has_all_core_promise_concepts[docs/FRIDGE_CARD.md]` — `docs/FRIDGE_CARD.md:17` missing "never charges you".

Read `FAMILY_QUICK_START.md` and confirm the Today card, the two answer buttons, practice mode, the first-start sentence, the update sentences, versions 0.3.1 and 0.3.0, and Jane Q Testperson, Springfield IL.

## Findings

Product copy, not edited (`src/` is closed on this work order). No new strict xfail was added, because `tests/` is not an allowed path and no current test guards this sentence.

- `src/freemyid/wizard/ui.py:265` — welcome text says "in the written form they have to answer." `docs/POSITIONING.md:51` says not to write "they have to answer" without the state-law qualifier. `tools/site_check.py:340` flags that phrase. The quick start does not repeat it.

Stale docs outside the allowed paths. Not edited. The quick start no longer copies them.

- `docs/USER_GUIDE.md:177` — "While practice mode is on, nothing is actually sent." The Today banner says practice mode looks for listings and that no removal requests go out until you say so (`src/freemyid/wizard/dashboard.py:237`).
- `docs/USER_GUIDE.md:180` — says a wrong Yes or No can be fixed before the next check. The first personal answer is kept (`src/freemyid/wizard/server.py:539`). A second press does not flip it. Already tested by `tests/test_wizard_review_match.py:87` and `tests/test_qa_is_this_you.py:87`. Those tests were not duplicated.
- `docs/HELPER_GUIDE.md:62` — practice mode "sends nothing."
- `docs/HELPER_GUIDE.md:29` — still teaches the version 0.2.0 finish-box label **Start Free My ID now** as the pair to look for. The 0.3.1 installer label is **Open Free My ID now** (`freemyid.iss`, line 56).

Splash wording, not edited (packaging is closed):

- The required first-start sentence is split. splash_win.py, line 20, is the first window. splash_win.py, line 23, is the slow window. `freemyid.iss`, line 34, says "Please wait, and do not click it again," which is not the same sentence. The quick start uses the required sentence as the instruction to the reader.

## Could not verify

- No Windows run. The installer, the splash, and an upgrade over an existing install were not opened. `freemyid run`, `send`, and `schedule install` were not run. The update sentences follow the installer script: same app id (`freemyid.iss`, line 9), details in the user data folder (line 83), the scheduled check removed only on uninstall (line 64), and the running app closed during install (line 28). The script comment says the first-start wait text is unverified on Windows.
- The published 0.3.0 installer file was not downloaded (no network). Version, size, and date are from `site_src/data/release.yaml` only. `docs/RELEASE_v0.3.md` says the 0.3.0 finish page said "up to 15 seconds." That older installer was not opened, so this page's first-start sentence is checked against the 0.3.1 source, not against the 0.3.0 file on the website.
