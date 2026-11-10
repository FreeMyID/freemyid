# VENDOR_STATUS

WO-315 (issue pending). Vendor: grok. Agent: Simon Fairley (user-guide writer).
Worktree: `.vendor-wt/wo-315`. Docs only. No `src/`, `web/`, `brokers/`, or `docs/vendor/` edits.

## Done

- Wrote `docs/user/google-and-bing.md`. It walks through the "Google and Bing" group on "Protect yourself".
- Confirmed the guessed lines. The heading "Google and Bing" is `src/freemyid/wizard/views.py:228`. "Open the page for me" is `views.py:241`. "Or open the link yourself" is `views.py:243`. "I did this" / "I have not done this" is `views.py:246`.
- The same two checklist items are drawn a second time by `_checklist_item` (`views.py:191-219`), called for every entry in `protect_page` (`views.py:271-272`). That draw uses "Open the web page" (`views.py:215`) and the same "I did this" / "I have not done this" words (`views.py:218`). The guide says so.
- Quoted all four `STATUS_TEXT` lines (`src/freemyid/engine/search_engines.py:66-70`), including "do it again" after a site removes a listing. That status is Bing only (`search_engines.py:60`, `redo_after_removal=True`). Google stays "Done." (`search_engines.py:54`).
- Named both steps from `brokers/checklists.yaml`: Google title at line 320, Bing title at line 343. Web addresses in the guide are only the ones in that file: `https://goo.gle/resultsaboutyou` (line 322), `https://www.bing.com/webmasters/tools/contentremoval` (line 345), and `https://www.microsoft.com/en-us/concern/bing` (line 353).
- A Google account is required for Google's tool because `brokers/checklists.yaml`, line 325, lists one. Bing accepts a Microsoft, Google, or Facebook account (line 348).
- The page says Free My ID does not search Google or Bing, does not take the page off the other website, and that Google or Bing decide. It says "requested".

## Next

- Leave this page unlinked. WO-330 adds the help-topics page that links it. In-house merges this WO and WO-330 together before pushing.
- No further edit in this worktree unless review asks for a wording change.

## Questions

- Is the second draw of Google and Bing on the lower checklist intentional? The top card does not list the steps, so the lower card is the only place those steps, tips, and the partial note appear. If it is not intentional, skip search-engine ids in the loop at `src/freemyid/wizard/views.py:271`.
- Should the top card also show the partial-verification note and the tip that the other website keeps the page? Today only the lower card does.

## How to test

Run from `.vendor-wt/wo-315`.

1. `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_doc_links.py tests/copilot/test_cp_source_citations.py tests/copilot/test_cp_wording_guard.py`

   Result: **364 passed** in 1.25s. Exit 0.

2. `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_user_docs_reachable.py`

   Result: **1 failed, 9 passed** in 0.19s. Exit 1.

   The only failure is `test_user_page_is_reachable[google-and-bing.md]`: `docs/user/google-and-bing.md` is not linked from `INSTALL.md` or `GLOSSARY.md` (one hop). Expected. WO-330 links it.

3. `tests/grok/`: directory not present. Not run.

## Findings

1. Two draws, two open actions. `engine_group` (`src/freemyid/wizard/views.py:222-248`, called at `views.py:265`) and the full checklist loop (`views.py:271-272`) both render `google_results_about_you` and `bing_content_removal`. "Open the page for me" posts to `/protect/{pid}/search/{cid}/open` and calls `open_step` (`src/freemyid/wizard/server.py:314-315`), which records an opened status. "Or open the link yourself" (`views.py:243`) is a plain link and records nothing. "Open the web page" (`views.py:215`) posts to `/protect/{pid}/{cid}/open`, which only calls `open_url` (`server.py:326-331`) and does not record `search_step_opened`. Both "I did this" buttons end in `checklist_state.set_done`, so the tick is shared. A person can open the page and still see "Not done yet."

2. The warning is only on the lower card. Both entries are `verification: partial` (`brokers/checklists.yaml`, lines 339 and 362). `PARTIAL_NOTE` (`views.py:185-188`) is rendered only in `_checklist_item` (`views.py:199-200`). `engine_group` does not show that note, the steps, the tips, or "To undo it:". The tip that Google hides a result from Search only, and that the other page stays up, is easy to miss (`brokers/checklists.yaml`, line 335).

3. Bing "do it again" still shows a finished date. When `redo_after_removal` is set and a removal is newer than the tick, status is `do_again` (`search_engines.py:132-134`) but `done_at` is still set, so the line also appends "Done on" (`views.py:232-233`). The button returns to "I did this" because `done` is only `status == "done"` (`views.py:236`). The guide tells the reader both can show at once.

4. Not a code defect, recorded so the steps are not treated as a live layout. Google's note says exact screen names may differ (`brokers/checklists.yaml`, line 340). Bing's note says the form behind sign-in was not seen, and that the "still live" tip is from community answers (`brokers/checklists.yaml`, line 363). The guide quotes the public steps and the partial note, and does not add a layout past that.

## Could not verify

- Did not open Google or Bing, and did not run the app. Anything their screens do beyond `brokers/checklists.yaml` and the wizard strings is not checked.
- Did not run git, gh, pip, curl, wget, or any network.
- `tests/grok/` is not in this worktree, so that suite was not run.
- Did not check that a future WO-330 link will satisfy `test_user_page_is_reachable`. The failure above is the current tree only.
