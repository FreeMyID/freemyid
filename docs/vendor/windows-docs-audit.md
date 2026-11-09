# Windows user-documents audit — WO-124

## Scope and evidence

This is a source-only audit of `FAMILY_QUICK_START.md`, the Windows and
troubleshooting material in `docs/USER_GUIDE.md`, `docs/HELPER_GUIDE.md`,
`docs/FRIDGE_CARD.md`, and the Windows FAQ answer in
`site_src/data/faq.yaml`. It uses the Windows installer and launchers,
the v0.2.0 release notes, and the stated screenshot captions. It does not
claim a real-Windows result unless the source proves it.

The v0.2.0 notes say the Ready page remains (`docs/marketing/release-notes-v0.2.0.md:40-44`)
and that the installer was not re-checked on a fresh Windows 10/11 VM
(`docs/marketing/release-notes-v0.2.0.md:77-85`). The first-start waiting
message in `packaging/windows/freemyid.iss:30-35,56` is **unreleased main
work** from `07fdbcc`, not v0.2.0 behaviour. The matching caption text in
`docs/HELPER_GUIDE.md:27-30` identifies the three v0.1.0 walkthrough
screens; image files have no line-addressable text, so captions are only
corroboration, not proof of current release behaviour.

**Audited revision:** the user documents as committed in `cfc273d` (before `d9b507f`). Line numbers refer to that revision. See "Follow-up status" at the end for which rows are already applied.

| User instruction (file:line) | Installer/app evidence (file:line) | Finding | Plain-language suggested correction | Owning team |
|---|---|---|---|---|
| `FAMILY_QUICK_START.md:19-20` says to open a setup file someone sent. | The v0.2.0 release instructions say to download from freemyid.org (`docs/marketing/release-notes-v0.2.0.md:18-24`) and provide checksums (`:53-57`). The installer output name includes the version (`packaging/windows/freemyid.iss:21-22`). | **Mismatch.** A received file is not the documented v0.2.0 download path and the displayed name may include a version. | Say: “Download FreeMyIDSetup from freemyid.org or the GitHub release. Check the name shown on the download page.” | wizard-packager |
| `docs/HELPER_GUIDE.md:24-25` says to use the official site or GitHub releases and open `FreeMyIDSetup.exe`. | v0.2.0 directs Windows users to freemyid.org (`docs/marketing/release-notes-v0.2.0.md:18-24,53-57`); the installer build name is `FreeMyIDSetup-<version>` (`packaging/windows/freemyid.iss:21-22`). | **Partial match.** The v0.2.0 release workflow publishes both `FreeMyIDSetup-<version>.exe` and the stable `FreeMyIDSetup.exe`, which the website button downloads (v0.2.0 `.github/workflows/build.yml:213-238`). So `FreeMyIDSetup.exe` is valid; a GitHub-release download may carry the version. | Keep the safe-source advice and both names: “the FreeMyIDSetup file you downloaded (its name may include a version number).” | wizard-packager |
| `FAMILY_QUICK_START.md:21-32` and `docs/HELPER_GUIDE.md:26-28` tell readers to use **More info** then **Run anyway**; the latter includes SmartScreen captions. | v0.2.0 says an unsigned installer may show the blue box and points to the download instructions (`docs/marketing/release-notes-v0.2.0.md:53-57`). | **Match.** Whether every Windows version shows the same buttons is **unverified** by source. | Keep the steps. Add “If you do not see this box, continue with the normal installer.” | wizard-packager |
| `site_src/data/faq.yaml:83-88` explains the Windows warning and links to pictures. | v0.2.0 says the installer is not signed and the blue box is expected (`docs/marketing/release-notes-v0.2.0.md:53-57`). | **Match.** Real SmartScreen wording and availability remain **unverified**. | No factual change needed; retain the calm link to the pictured steps. | web-developer |
| `FAMILY_QUICK_START.md:33-36` says “Next, Next, then Install,” then finish; `docs/HELPER_GUIDE.md:29-30` says click **Install** and leave Start ticked. | The installer chooses the per-user folder and does not show a folder-choice page (`packaging/windows/freemyid.iss:13-18`). It deliberately keeps the Ready-to-Install page (`:66-68`) and launches after setup (`:55-56`). | **Match**, except “Next, Next” is brittle because page count is not a release contract. | Say: “Click Next when shown, then click Install. Leave the start box checked and click Finish.” Name the label per release: v0.2.0 says **Start Free My ID now** (v0.2.0 `packaging/windows/freemyid.iss:49`); from 0.3 it says **Open Free My ID now** (`:56`). | wizard-packager |
| No audited user instruction says where the program is installed. | The installer uses `%LOCALAPPDATA%\Programs\FreeMyID` and hides the folder-choice page (`packaging/windows/freemyid.iss:13-16`). | **Match (intentional omission).** It is a fixed per-user location; source does not prove a real install. | Do not add a folder path to the quick instructions. Put it only in a helper troubleshooting note if needed. | wizard-packager |
| `FAMILY_QUICK_START.md:76` and `docs/USER_GUIDE.md:95` say to reopen from the Start Menu or Desktop; `docs/HELPER_GUIDE.md:30` says it opens after install. | The installer creates both **Free My ID** shortcuts (`packaging/windows/freemyid.iss:51-53`) and runs `FreeMyID.exe` after setup (`:55-56`). The launcher opens the wizard first, then the dashboard (`packaging/windows/launcher_gui.py:1-5,26-29`). | **Match.** Shortcut creation and launch on a real Windows computer are **unverified** by source. | Keep the simple shortcut names; do not mention `FreeMyID.exe` to ordinary readers. | wizard-packager |
| `FAMILY_QUICK_START.md:36-40` moves directly from Finish to questions; `docs/HELPER_GUIDE.md:29-30` says the app opens by itself. | v0.2.0 retains the Ready page (`docs/marketing/release-notes-v0.2.0.md:40-44`). The new main-only finish-page text warns of up to 15 seconds (`packaging/windows/freemyid.iss:30-35,56`); the launcher also shows a small wait window (`packaging/windows/launcher_gui.py:26-29`, `packaging/windows/splash_win.py:1-5,12`). | **Unverified for v0.2.0; next-release update needed.** The 15-second wording is from unreleased `07fdbcc`, and its source comment says it is not verified on Windows. | In the release that contains `07fdbcc`, add: “The first opening can take up to 15 seconds. Wait for the Free My ID is starting window; do not click again.” Do not backport this as a v0.2.0 claim. | wizard-packager |
| `FAMILY_QUICK_START.md:76-77` only says to reopen from a shortcut; the other audited documents have no “window did not open” steps. | The main-only wait source explains the expected delay and starts a splash window (`packaging/windows/splash_win.py:1-5,12`); failure to show that splash is intentionally ignored (`:46-47`). | **Mismatch / incomplete troubleshooting.** There is no source-confirmed recovery path after the wait. | For the next release: “Wait 15 seconds. Then try the Start Menu shortcut once. If it still does not open, ask your helper; do not keep double-clicking.” Mark the outcome **unverified** until tested on Windows. | wizard-packager |
| `FAMILY_QUICK_START.md:77` says Windows Apps uninstall asks before deleting saved items. | Uninstall closes the app (`packaging/windows/freemyid.iss:70-77`), removes the daily task (`:62-64`), and asks whether to delete people, reports, and screenshots; **No** is the default (`:95-110`). | **Match.** Real Windows uninstall prompts are **unverified**. | Say “Choose Yes to remove saved people, reports, and screenshots; choose No to keep them for later.” | wizard-packager |
| `docs/HELPER_GUIDE.md:82` says uninstall can delete records, screenshots, and a saved mailbox password, and always removes the daily task. | The task-removal command and delete choice are explicit (`packaging/windows/freemyid.iss:62-64,95-110`). The comment says the wipe can delete mailbox passwords (`:95-96`), but this restricted audit did not inspect the wipe implementation. | **Match** for the task and listed data; saved-password deletion is **unverified** by the allowed source evidence. | Keep the task wording. For now say “saved information” rather than promising a specific password result until it is release-tested. | wizard-packager |
| `site_src/data/faq.yaml:21-23` says details are stored on the computer; `docs/USER_GUIDE.md:95` says the app runs on the computer. | The installer data folder is `%APPDATA%\FreeMyID` (`packaging/windows/freemyid.iss:80-88`); the v0.2.0 notes say details stay on the computer and requests go only to sites the person chooses (`docs/marketing/release-notes-v0.2.0.md:44,49-51`). | **Match.** Exact storage contents and network behaviour beyond these statements are outside this source-only audit. | On the troubleshooting page, add “Saved Free My ID information is in your Windows AppData FreeMyID folder” only if a helper needs that detail; keep the main FAQ plain. | web-developer |
| `docs/USER_GUIDE.md:95` says “nothing you type is sent to a website.” | v0.2.0 says removal requests go to sites after the person says so (`docs/marketing/release-notes-v0.2.0.md:49-51`). | **Mismatch.** Read literally, it conflicts with later approved requests. It also hides two transfers that happen before any request: the mailbox test signs in to the chosen mail provider with the typed address and password (`src/freemyid/wizard/draft.py`), and practice-mode exposure scans send search URLs built from the person's name and location to people-search sites (`src/freemyid/cli.py`). | Say: “Your answers are saved only on this computer. The mailbox test signs in to your email company, and practice mode searches the sites for your name and city. No removal request is sent until you choose to start requests.” Keep searches and removal requests as separate sentences. | wizard-packager |
| `docs/FRIDGE_CARD.md:11-12` says it checks every day; `:17-18` gives the safety warning. | The Windows installer removes a daily task on uninstall (`packaging/windows/freemyid.iss:62-64`), but this evidence does not establish its schedule. The v0.2.0 notes support the SSN/bank/card part of the warning (`docs/marketing/release-notes-v0.2.0.md:49-50`), not the everyday-password claim. | **Unverified** for daily timing and the password wording under this restricted evidence set. | Until the scheduler and UI are release-tested, say “It checks in the background when automatic checking is on.” Retain the SSN/bank/card warning; separately verify the password wording. | wizard-packager |

## Release boundary

For v0.2.0, describe the Ready page, the unsigned-installer warning, the shortcuts,
and the uninstall choice only. Do **not** state that v0.2.0 displayed a first-start
wait notice. After `07fdbcc` ships, update the quick start, helper guide, and
window-does-not-open troubleshooting copy together, then verify the exact wording
on clean Windows 10 and Windows 11 installations.

## Validation performed

- Read all five audited user-document files and their cited lines.
- Read `packaging/windows/freemyid.iss`, `launcher_gui.py`, `launcher_cli.py`,
  `splash_win.py`, and `freemyid.spec` without modifying them.
- Read `docs/marketing/release-notes-v0.2.0.md`.
- Compared `07fdbcc`'s installer diff to separate unreleased first-start copy from
  the v0.2.0 baseline.
- Searched the repository for the stated v0.1.0 SmartScreen and installer screenshot
  captions. No executable, installer, or Windows VM was run; real-Windows results
  remain unverified.

## Follow-up status (2026-11-08)

Applied in `d9b507f` (Jordan Ellis): quick-start download source and versioned name, helper-guide filename wording, "Next when shown", 0.3 wait and recovery steps marked "from version 0.3", uninstall Yes/No wording, USER_GUIDE:95 first rewrite.
Applied in the CodeRabbit cycle 2 fixes (Marcus Webb, branch `inhouse/fix-review-cycle2`): the **Download Free My ID** click in the quick start, both finish-page labels (v0.2.0 and 0.3) in the quick start and helper guide, and USER_GUIDE:95 separating searches and the mailbox test from removal requests.
Still open: FRIDGE_CARD daily-timing wording and the saved-password deletion claim (need a Windows release test).
