# WO-302 VENDOR_STATUS

## Done

Described the 0.3.1 app window in `docs/USER_GUIDE.md`. The first draft was written at the worktree root, which is not the guide. That root file is removed. The same text is now the section "The app window in version 0.3" in `docs/USER_GUIDE.md`.

The section covers Today (one card, then **More: safety steps and details**), the "Is this you?" card, the optional phone-call note, the Google and Bing steps, and **Larger text**. Button labels are quoted from `src/freemyid/wizard/`. The yes and no labels are **Yes, this is me** and **No, this is not me**. File:line citations are HTML comments. Example person only: Jane Q Testperson, Springfield, IL.

Also corrected in the same file, because the old sentences disagreed with the app:

- Section 4 now says the window opens on **Today**, and that practice mode sends no removal request until the person says so.
- The old "Is this you?" section no longer says a wrong press can be fixed before the next check. The first answer stays. A second press says **That question was already answered. Nothing was changed.**
- The phone section names **A short note about the call (optional)** and **I finished it**.
- The setup step no longer says to update to 0.3 when it comes out. Version 0.3 is the current app.

Did not edit `src/`, `web/`, or `docs/vendor/`.

## Next

Owner review of `docs/USER_GUIDE.md`, then merge when it looks right.

## Questions for the owner

1. Today's email card says "press Approve" and "Nothing is sent until you do." The button on that card is **Look at them**. The Emails page button is **Approve and send**. Should in-house align that copy? Not changed here. The guide quotes the button labels and does not use "nothing is sent".
2. The download record in this tree is still 0.3.0 (`site_src/data/release.yaml`). The app version is 0.3.1. The new section says 0.3.1 for the window. Say if the guide should name 0.3.0 until the download record moves.

## How to test

From this worktree:

`PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot tests -k "doc or wording or guide or claims"`

Counts from that command after the move into `docs/USER_GUIDE.md`: 562 passed, 66 skipped, 2047 deselected, 1 xfailed, 1 warning in 6.00s.

The one xfail was already in the tree. It is `tests/copilot/test_cp_never_asks_parity.py::test_existing_copy_has_all_core_promise_concepts[docs/FRIDGE_CARD.md]` because `docs/FRIDGE_CARD.md:17` is missing "never charges you". This work order did not touch that file.

Of the 66 skips: 58 are `web/dist` not built (`tests/conftest.py:180`), 5 are `tests/test_web_og_images.py:124` for the same reason, and 3 are `tests/copilot/test_cp_never_asks_parity.py` looking for `docs/FAMILY_QUICK_START.md` (the file in this tree is `FAMILY_QUICK_START.md` at the root). None of those skips are from this work order.

## Could not verify

The app window was not opened. Button labels, the phone-call note, Google and Bing text, and **Larger text** were read from source, not from a running window or a Windows machine. Text size "about one quarter larger" is `font-size: 125%` at `src/freemyid/wizard/static/style.css:5`, not a measured screenshot. Six external links in other docs were reported by the link test and were not fetched.

## Findings

1. Copy mismatch, not changed: `src/freemyid/wizard/dashboard.py:253-255` tells the person to press Approve and says "Nothing is sent until you do." The button there is **Look at them**. The send button is **Approve and send** at `src/freemyid/wizard/dashboard.py:472-473`. No xfail test: `tests/` is not an allowed path.

2. Noted, not treated as a defect: **Protect yourself** shows Google and Bing twice. A short block is drawn at `src/freemyid/wizard/views.py:265` (**Open the page for me**). The same checklist items are drawn again in the full list at `src/freemyid/wizard/views.py:271-272` (**Open the web page**). Both **I did this** buttons tick the same step. The guide tells the reader that.
