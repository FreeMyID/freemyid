# VENDOR_STATUS.md — WO-318 (issue pending)

Linda Moreau, support writer. Worktree `.vendor-wt/wo-318`. Docs only. No `src/` or `web/` edits.

## Done

- Added `docs/user/never-asks.md`. It is a short page for the person, or a helper, about what Free My ID never asks for, how a real on-screen message looks, and what to do if someone asks in its name.
- The page quotes the app lines named in the order: `src/freemyid/wizard/ui.py:266-267`, `src/freemyid/wizard/dashboard.py:529`, and `src/freemyid/wizard/views.py:273`.
- It names the same three core items as the website Is it safe? page: Social Security number; bank account, credit or debit card details; a payment of any kind (`web/src/pages/safety/index.astro:71`, `:72`, `:74`).
- It says a people-search site or a credit bureau may ask for a photo ID, an account, or similar on its own site, and that Free My ID stops and asks first unless that step was already allowed.
- If a caller, text, or email asks for money, a password, a code, or a Social Security number, the page says it is not Free My ID. Hang up or do not reply. Tell someone you trust.
- No phone number, email address, or web address was added for reporting. None was found in the app for that purpose.
- Example person only: Jane Q Testperson, Springfield IL.
- `docs/pm/issue_map.json` has no WO-318 number, so this status cites "WO-318 (issue pending)".

## Next

- WO-330 is the order that links this page. Until that lands, `never-asks.md` stays unlinked on purpose. Do not link it from `INSTALL.md` or `GLOSSARY.md` in this order.
- In-house review, then merge with WO-330 before push.
- `docs/vendor/GROK_TO_CLAUDE.md` and `docs/vendor/GROK_BOARD.md` are outside this order's allowed paths, so they were not updated here.

## Questions

- Should the welcome card (`src/freemyid/wizard/ui.py:266-267`) also say that Free My ID never takes a payment, so it matches the three core items?
- Should the Protect yourself hint (`src/freemyid/wizard/views.py:273`) also name bank or card details? It names a Social Security number and paying, and stops there.
- Which payment sentence should the other copies use: "A payment of any kind", "It never pays.", or "never charges you"?
- The About note says birth year, relatives, and personal email addresses are "never sent" (`src/freemyid/wizard/ui.py:309-310`). This page does not repeat that. Is that sentence still wanted on the screen?

## How to test

Ran in `.vendor-wt/wo-318`. No network, git, gh, pip, or app launch.

1. `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_doc_links.py tests/copilot/test_cp_source_citations.py tests/copilot/test_cp_wording_guard.py`

   Result: **318 passed**, exit 0. No failures, no skips.

2. `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_user_docs_reachable.py`

   Result: **1 failed, 9 passed**, exit 1.

   The one failure is `test_user_page_is_reachable[never-asks.md]`: `docs/user/never-asks.md` is not linked from `INSTALL.md` or `GLOSSARY.md` (one hop). That is the expected failure. WO-330 adds the link. No other failure.

3. `tests/grok/` is not in this worktree, so `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/grok` was not run.

## Findings

The new page uses the website's three core items. The app screens do not use those same words. Not edited. File and line on both sides:

1. **Payment.** The website says "A payment of any kind" (`web/src/pages/safety/index.astro:74`). The welcome card does not mention a payment (`src/freemyid/wizard/ui.py:266-267`). Settings says "It never pays." (`src/freemyid/wizard/dashboard.py:529`). Protect yourself says "Free My ID never pays for you" (`src/freemyid/wizard/views.py:273`). The full consent wording says "It never pays anyone." (`src/freemyid/wizard/draft.py:50`). The real-requests screen says "Nothing is paid for." (`src/freemyid/wizard/dashboard.py:485`). The terminal setup says "it never pays" (`src/freemyid/wizard/flows.py:127`). The user guide and helper guide say "never charges you" (`docs/USER_GUIDE.md:29`, `docs/USER_GUIDE.md:246`, `docs/HELPER_GUIDE.md:88`). The safety page does not contain the words "never charges you". The parity test still looks for "never charges you" in the older copies (`tests/copilot/test_cp_never_asks_parity.py:29`) and checks the safety page for "A payment of any kind" (`tests/copilot/test_cp_never_asks_parity.py:70-71`).

2. **Bank or card details.** The website says "Bank account, credit or debit card details" (`web/src/pages/safety/index.astro:72`). The welcome card and Settings say "bank or card details" (`src/freemyid/wizard/ui.py:267`, `src/freemyid/wizard/dashboard.py:529`). The Protect yourself hint does not name bank or card details (`src/freemyid/wizard/views.py:273-274`).

3. **Helper guide claims a match it does not have.** `docs/HELPER_GUIDE.md:88` says its short form is the same words as the website. The website's payment item is "A payment of any kind" (`web/src/pages/safety/index.astro:74`), not "never charges you".

4. **About screen uses "never sent".** `src/freemyid/wizard/ui.py:309-310` says "A birth year, relatives and personal email addresses are never sent." The terminal heading says the same kind of thing (`src/freemyid/wizard/flows.py:116-117`). User docs are not allowed to say "never sent". This page does not copy those sentences. The safety page's "never does" list is narrower: it says the year of birth and relatives' names are not sent to a site (`web/src/pages/safety/index.astro:87`). I did not trace the send path, so I am not calling this a functional bug.

The page also names the two extra Is it safe? rows (full birthday, everyday email password) at `web/src/pages/safety/index.astro:75` and `:77`. The setup label is "Year of birth" (`src/freemyid/wizard/ui.py:311`), and an empty year is accepted (`src/freemyid/wizard/draft.py:324`). The mailbox error says the app password is not the normal email password (`src/freemyid/wizard/draft.py:386`). Those agree in substance with the website. The website's call line is "it isn't us" (`web/src/pages/safety/index.astro:97`). This page says "it is not Free My ID", as the order asked.

## What I could not verify

- I did not run Free My ID or open the screens. Quotes were checked against the source files only.
- I did not open Equifax, Experian, or any other site. Bureau lines are from `brokers/checklists.yaml` in the repo. The TransUnion checklist is marked partial in that file, so this page does not use it.
- I did not trace whether birth year and relatives are in fact withheld from every request. See finding 4.
- I did not run the tests on Windows. They only read files.
- `tests/grok/` is absent, so that suite was not run.
- No reporting phone, email, or web address was verified beyond a search of the wizard sources and the safety page. I did not add one.
