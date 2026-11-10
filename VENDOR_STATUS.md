# VENDOR_STATUS — WO-316 (issue pending)

Agent: Wesley Tran (reference-writer). Docs only. No network, no git, no app run, no bureau sites opened. `web/`, `brokers/`, and `src/` were not edited.

## Done

- Added `docs/user/protect-yourself.md` for the Protect yourself screen, led by credit freezes.
- Lead quote is the screen's own sentence at `src/freemyid/wizard/views.py:254-257`. Confirmed. It says "most are free", not "mostly free", and it ends with "The ticks stay on this computer."
- That quoted sentence does not contain a wording-guard banned word (`guarantee`, `erase`, `100%`, `never sent`). The guard passed, so the quote was kept with no `wording-guard` marker. No "nothing is sent" was added.
- Buttons confirmed. "Open the web page" is `src/freemyid/wizard/views.py:215`. "I did this" / "I have not done this" is `src/freemyid/wizard/views.py:218`.
- A second set is on the Google and Bing group. "Open the page for me" is `views.py:242`. "Or open the link yourself" is `views.py:244`. The tick labels are the same words again at `views.py:247`.
- Freeze titles are the eight titles in `brokers/checklists.yaml` (lines 23, 44, 65, 86, 107, 125, 145, 166), cited in words. The other nine cards get one line each, including Google (line 320), Bing (line 343), and California DROP (line 367). The work order's "lines 188-319" stops on the Google id. Those three later cards are on the screen, so they are included.
- The page says you requested the step on the company site and confirmed the tick on this computer. It does not say a freeze is in place.
- Promise: the Protect yourself line is `views.py:273-274`, quoted exactly. It says Free My ID never pays for you and never asks for your Social Security number. It does not say "bank or card details". Those words are on the welcome screen (`src/freemyid/wizard/ui.py:266-267`) and on Settings (`src/freemyid/wizard/dashboard.py:529`). Both are quoted on the user page.
- Guide check is below. Neither file was edited.
- `tests/grok/` is not in this worktree, so that check was not run.

## Next

- WO-330 is what links this page. In-house merges WO-316 and WO-330 together before pushing. This work order's allowed paths do not include `GROK_BOARD.md` or `GROK_TO_CLAUDE.md`, so those were not updated.

## Questions

- Is the shorter promise on `views.py:273` (Social Security number only) enough for this screen, with bank and card details left on the welcome screen and Settings?
- Google and Bing are drawn twice: the group at `src/freemyid/wizard/views.py:265`, then again in the full list at `views.py:271`. The tick is one shared checklist id. The user page says that. Is the double listing intended?
- The child freeze is in the app list and held off the website (`web/src/lib/protect.ts:112`). Finding F1 records that. No change was made.

## How to test

From `.vendor-wt/wo-316`:

1. `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_doc_links.py tests/copilot/test_cp_source_citations.py tests/copilot/test_cp_wording_guard.py`

   Result: **306 passed**.

2. `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_user_docs_reachable.py`

   Result: **1 failed, 9 passed**.

3. After the last prose edit, both suites together: **1 failed, 315 passed**. The only failure is the one named below.

4. `tests/grok/` does not exist. Third check not run (0 tests).

## Expected failure

`tests/copilot/test_cp_user_docs_reachable.py::test_user_page_is_reachable[protect-yourself.md]`

`docs/user/protect-yourself.md` is not linked from `INSTALL.md` or `GLOSSARY.md` (one hop). By design: WO-330 adds the link, and in-house merges the two work orders before pushing. No other failure.

## Guide-check findings

Compared `web/src/pages/protect/credit-freeze/index.astro` (read-only) with `brokers/checklists.yaml`. Titles for the seven bureaus the guide lists are filled from the checklist, so those title strings match. Mismatches:

### F1. Child freeze missing

- `brokers/checklists.yaml:165-166` — id `freeze_child_equifax`, title "Freeze your child's credit at Equifax (child under 16)".
- `web/src/pages/protect/credit-freeze/index.astro:13-14` — lists only `freeze_equifax`, `freeze_experian`, `freeze_transunion`, `freeze_innovis`, `freeze_nctue`, `freeze_lexisnexis`, `freeze_chexsystems`.
- `web/src/lib/protect.ts:110-112` — `freeze_child_equifax` is in `HOLD`, so no child step page is built.
- `index.astro:70` talks about a child under 16 and does not name this entry.

### F2. "More" list order differs

- `index.astro:14` — Innovis, NCTUE, LexisNexis, ChexSystems.
- `brokers/checklists.yaml` — Innovis line 84, ChexSystems line 106, NCTUE line 124, LexisNexis line 144.
- Same four bureaus. Order only. Not a missing bureau.

### F3. General "what a freeze does" claims are not in the checklist

`index.astro:32` says a freeze stops lenders seeing your credit file, does not close accounts you already have, still lets companies you already do business with check your file, and stays on until you lift it.

- Supported for the big three: a thief and new credit, and the score, at `checklists.yaml:24`. Experian line 45 and TransUnion line 66 say the same reason. Cost lines 26, 47, and 68 say free, in different words.
- "Stops lenders from seeing your credit file" is not a public checklist line. The closest is LexisNexis only, `checklists.yaml:146`.
- "Doesn't close the accounts you already have" is not in the checklist.
- "Companies you already do business with can still check your file" is only the LexisNexis tip, `checklists.yaml:159`, not a rule for every bureau.
- "Stays on until you lift it" is not stated. `checklists.yaml:35` says you can lift or remove an Equifax freeze. It does not say the freeze never expires on its own.
- The score sentence is not written for Innovis, ChexSystems, NCTUE, LexisNexis, or the child freeze. The guide states it for "a freeze" at `index.astro:32`.

### F4. Federal speed claim is not in the checklist

- `index.astro:62` — one business day online or by phone, three business days by mail, lift within one hour. The comment at `index.astro:60-61` cites statute, not the checklist.
- No such deadline is in `brokers/checklists.yaml`. Experian line 48 and line 53 say online starts right away / in real time. Line 55 says Experian mail can take up to 3 days. Child Equifax line 170 says up to 3 business days after Equifax gets the papers. None of those is the one-hour lift rule.
- `tests/test_web_credit_freeze.py:16` asserts the one-business-day sentence, so the site intends it. It is still a checklist mismatch.

### F5. "Lift only at the lender's bureau" is not in the checklist

- `index.astro:64` — ask the lender which bureau it checks, and lift the freeze only there.
- `checklists.yaml:37` and line 77 say a freeze at one bureau does not freeze the others, and to freeze all three. No public line says to lift only one bureau.

### F6. Parent section is wider than the child entry

- `index.astro:70` — child under 16, or an adult with a court-appointed guardian or conservator; proof such as a court order or power of attorney; each bureau; some requests by mail only.
- `checklists.yaml:166-185` is Equifax only, child under 16, and a mail request (line 181).
- `checklists.yaml:171` also lists foster care certification. The guide does not.
- `checklists.yaml:180` — teens 16 and 17 can ask Equifax by phone or mail. The guide does not say that.
- No public checklist line describes an incapacitated adult or a conservator. Line 179 says to do the child at Experian and TransUnion too, and gives no steps.

### F7. Fraud alert is not a checklist step

- `index.astro:73-76` — a fraud alert is a separate free step, a first alert lasts one year, and one bureau tells the other two.
- No fraud-alert id in `brokers/checklists.yaml` (ids from line 22 through line 366).

### F8. Innovis price caveat dropped

- `index.astro:54` — the smaller companies are "optional and free." Innovis is in that list (`index.astro:14`).
- `checklists.yaml:88` — "Free under the FTC's rule that freezes are free. The Innovis page itself does not state a price."

### F9. "Each bureau's sign-in or PIN" disagrees with Experian

- `index.astro:48` — "Keep each bureau's sign-in or PIN somewhere safe."
- `checklists.yaml:53` — Experian online "needs no PIN."
- `checklists.yaml:33` — Equifax says to write down a user name and password, not a PIN.

### F10. ChexSystems "free" is unconfirmed in the checklist notes

- `index.astro:54` calls that whole group free. ChexSystems is in the group (`index.astro:14`).
- `checklists.yaml:111` public cost is "Free." That public line matches the guide.
- `checklists.yaml:122` notes say the Free cost and the PIN are unconfirmed on the official page. The guide comment at `index.astro:3` says snippet-only ChexSystems facts are not used, but the free sentence still covers ChexSystems.

### F11. Alert adds claims the freeze entries do not make

- `index.astro:79` — bureaus ask for a Social Security number "to find your file"; do not follow an email or text that offers to freeze credit; "Free My ID is not involved in any of this."
- `checklists.yaml:28` (also lines 49, 70, 90, 112, 130, and 150) lists "Your Social Security number" to have ready. It does not say "to find your file."
- The email or text warning is not on a freeze entry. A look-alike warning is on a different step, `checklists.yaml:203`.
- "Free My ID never asks" is not a checklist sentence. The app does say the Social Security part at `views.py:273`. That part is not a contradiction. It is extra relative to the checklist.

### Checked, not a mismatch

- `index.astro` prints no mailing address and no phone number, so there is no address string on that page to differ from `checklists.yaml`.
- Per-bureau pages were not edited and were not fully diffed. `web/src/pages/protect/[id]/index.astro` prints checklist fields (cost, steps, url, how to undo) rather than a second written copy.

## App finding (not the guide check)

`brokers/checklists.yaml:30` (and the same "web address above" pattern on the other freeze steps) tells the reader to open the address above. `src/freemyid/wizard/views.py:202-219` never prints `c.url` on the card. The "Open the web page" button at `views.py:213-215` opens it. The step text points at an address the screen does not show. Not edited.

## What I could not verify

- The app was not run, so the screen was not seen in a window. Button labels, the lead, and the double Google and Bing listing are from source, not from a live page.
- Bureau websites were not opened. Nothing here re-checks that a checklist step still matches a bureau.
- The website was not built, so `web/dist` was not read. The guide check is the Astro source against `brokers/checklists.yaml`.
- The shared Google/Bing tick is inferred from both views calling the same checklist id. It was not clicked in a running app.
- `docs/pm/issue_map.json` has no WO-316 number, so the issue is still "pending".
