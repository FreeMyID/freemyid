# WO-326 (issue pending)

Vendor: grok. Agent: Wesley Tran (reference writer).
Status: Done. Docs only. `src/` was not edited.

## Done

Brought `docs/user/mail-gmail.md`, `docs/user/mail-proton.md`, and `docs/user/mail-other.md` in line with the 0.3.1 mailbox screen, title "A separate email address for replies" (`src/freemyid/wizard/draft.py:69`).

- Gmail app-password steps are the wizard's own five sentences (`src/freemyid/wizard/ui.py:214-219`). Server names are the Gmail preset (`draft.py:74-75`: `imap.gmail.com` port 993, `smtp.gmail.com` port 465).
- Proton uses the Bridge preset (`draft.py:76-77`: `127.0.0.1`, incoming 1143, outgoing 1025, STARTTLS on both).
- Other providers: the screen tells the person to ask their email company for an app password (sometimes called a program password) and for the mail server names (`ui.py:238-239`), then fill in the server, port, SSL, and STARTTLS boxes.
- Yahoo, iCloud, and Outlook stay on the other-services page so the existing INSTALL and HELPING links still match. Their steps are the wizard's sentences, with corrected line numbers.
- Every quoted screen label has an `src/freemyid/...py:NNN` citation in an HTML comment on the same line.
- Google and Proton steps the repo cannot confirm are marked "Google's page may look different" or "Proton's page may look different".
- Why a separate address is used is the screen's own sentence (`ui.py:392-393`). The password sentence is the screen's own sentence (`ui.py:390-391`): kept in this computer's protected store, not in Free My ID's files. The save note says the keychain (`draft.py:560`); the store's note says it is not kept as clear text (`secrets.py:4`).
- Example address on all three pages: `jane.testperson@example.com` (Jane Q Testperson, Springfield IL).
- Existing headings used by the old pages are still there. The Proton support link is still `https://proton.me/support/comprehensive-guide-to-bridge-settings`.

## Next

Nothing left in this work order's allowed paths. Check-in notes for `docs/vendor/GROK_TO_CLAUDE.md` and `docs/vendor/GROK_BOARD.md` are outside the allowed paths, so they were not edited.

## Questions

None that block this page update. The findings below are for the owner; `src/` and `docs/user/INSTALL.md` were out of scope.

## How to test

From `.vendor-wt/wo-326`:

`PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_doc_links.py tests/copilot/test_cp_source_citations.py tests/copilot/test_cp_wording_guard.py tests/copilot/test_cp_user_docs_reachable.py`

Result: **420 passed** in 1.25s. 0 failed. The link check listed 7 external links and did not fetch them, including the Proton Bridge settings guide.

`tests/grok/` does not exist in this worktree, so that check was not run.

## Findings

The old mail pages cited real files, so the citation test still passed, but many line numbers were not the lines that hold the words. The test only checks that the line number exists and that quoted text appears somewhere in the file.

Stale lines fixed in these pages (old citation, then the line that has the words):

- Gmail "about 3 minutes" was `ui.py:210` (blank). The guide title is `ui.py:213`.
- The separate-address reason was `ui.py:389` (end of the trust-box markup). The sentence is `ui.py:392-393`.
- The Gmail hint "works best" was `ui.py:198`. It is `ui.py:201`.
- Skip was `ui.py:204-205` (Proton and Another email service). Skip is `ui.py:207-208`.
- Gmail's five app-password steps were cited around `ui.py:211-216`. They are `ui.py:214-220`. "Password box" is `ui.py:219`.
- "Email address" was `ui.py:362` (`else:`). The label is `ui.py:365`. "Test that it works" was `ui.py:380` (the outgoing STARTTLS label). The button is `ui.py:383`. "Next" was `ui.py:409`. The word is `ui.py:407`.
- The password sentence was `ui.py:387-388` (the Yes and No buttons). It is `ui.py:390-391`.
- "Change it" was `dashboard.py:442` (`outbox_page`). It is `dashboard.py:526`, under "Email for removals" at `dashboard.py:525`.
- Proton Bridge install was `ui.py:231-232` (the Apple password step). It is `ui.py:234-235`. "Copy them below" is `ui.py:236`, not `ui.py:233` (that line is the title "Using Proton Mail"). The Proton choice is `ui.py:204`, not `ui.py:201` (Gmail). "Bridge username" is `ui.py:368`, not `ui.py:365`.
- The first-time trust message was `server.py:721-725` (the schedule route). It is `server.py:813-814`. "Not trusted. Nothing was saved and no password was sent." was `server.py:733-734` ("Report unavailable."). It is `server.py:826`. The No button is `ui.py:388`, not `ui.py:385`.
- The changed-code question was `server.py:758-766`. The text is `server.py:809-811` and the question is `server.py:817`.
- Yahoo steps were `ui.py:218-223` (that overlaps the last Gmail step). Yahoo is `ui.py:221-226`. The Yahoo choice is `ui.py:202`, not `ui.py:199`. iCloud steps were `ui.py:224-229`. They are `ui.py:227-232`. The iCloud choice is `ui.py:203`, not `ui.py:200`.
- "Another email service" was `ui.py:202` (Yahoo). It is `ui.py:205`. "Ask your email company..." was `ui.py:235` (`proton.me/mail/bridge`). It is `ui.py:238`. Server names were `ui.py:236` (the Bridge copy step). The step is `ui.py:239`; the boxes start at `ui.py:370`.
- The old other-services page mixed the on-screen hint "If unsure" (`ui.py:378-379`) with the error "If you are not sure" (`draft.py:344-345`). Those are now quoted separately.
- Outlook's on-screen reason was cited `ui.py:238`. That line is the "ask your email company" step. The Outlook sentence is `ui.py:241`. The error if you continue is `draft.py:86`, appended at `draft.py:301`.

Product notes, not changed (`src/` is out of scope):

- `models.py:266` says the mailbox password lives ONLY in the OS keychain. `secrets.py:3-4` stores it through the selected backend, which can be an encrypted file, and says "Never stored in clear text." `draft.py:572-573` always tells the person to unlock the keychain, even if another backend is in use. The pages quote the screen ("protected store", `ui.py:390-391`) and label the keychain wording as the save step's note.
- `mail_tls.py:199-201`, shown by the command-line flow at `flows.py:149`, says to click Yes if you just installed and started Bridge. The setup screen (`server.py:813-814`) asks you to check that the code matches Proton Mail Bridge. These pages follow the setup screen.
- `server.py:830` returns "Saved. Testing again..." but `src/freemyid/wizard/static/app.js:52-54` does not show that sentence. It runs the test again. The pages do not say the person will see it.
- `draft.py:496-498` (`_CHANGED_MSG`, "Nothing was sent") is not what the setup screen's Test button shows. `server.py:786` replaces a changed certificate with the text at `server.py:809-817`.

Out of scope, still stale:

- `docs/user/INSTALL.md:63-64` still cites `ui.py:389` for the separate-address sentence. The words are at `ui.py:392-393`. Not edited, per this work order. The citation test still passes because that line has no quoted label left once the citation is removed.

Could not verify:

- Google's current account pages, Proton's current Bridge screens, and the Bridge menu name "Export TLS certificates". Those sites were not opened. That button name is not in `src/`, so it is no longer stated as a label. The Proton settings-guide link was kept, and those steps are marked "Proton's page may look different". Yahoo and Apple steps are quoted only as the wizard shows them.
