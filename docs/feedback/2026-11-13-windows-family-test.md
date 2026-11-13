# Field report: Windows install and first run, 2026-11-13

Source: owner, testing at home with a family member on Windows (Windows 11 assumed; confirm).
Build: the installer live on freemyid.org on 2026-11-13. Presumed v0.3.1 (pyproject); confirm against the release page hash.
Recorded by: Morgan Reyes (in-house). No personal data from the session is recorded here.

## What happened, in order

| # | Where | What the owner saw | Severity | Work order |
|---|-------|--------------------|----------|------------|
| F1 | Download | Malwarebytes tried to block the download. Windows Defender deleted the file and would not keep the .exe until Defender was turned off. | HIGH (blocks every real user) | WO-632 |
| F2 | After install | Windows Defender flagged Free My ID as a Trojan. | HIGH | WO-632 |
| F3 | First launch | The blue SmartScreen "Windows protected your PC" step appeared; "More info, Run anyway" worked as documented. | OK (expected while unsigned) | none |
| F4 | Wizard step 6 (finish) | A "you do not have consent" message kept appearing and the details seemed not to save. After closing and reopening the app, everything had been saved. | HIGH | WO-633 |
| F5 | Fill for me | On 4 sites, Edge opened and then closed ("crashed") the moment it tried to load the site. Owner suspects it was being blocked. | HIGH (core feature) | WO-634 |
| F6 | Fill for me | On 1 site the form loaded and filled, but the Cloudflare "Verify you are human" box answered "Error, can't verify" when clicked, so the form could not be submitted. | HIGH | WO-635 |

Retest of all of the above on the Windows test VM: WO-636.

## First read of the code (in-house, 2026-11-13; to be confirmed by each WO)

- **F1/F2:** the installer is an unsigned PyInstaller build (`packaging/windows/freemyid.spec`, UPX already off). Unsigned PyInstaller bootloaders are a common antivirus false-positive pattern. Code signing was deferred (memory note, SignPath Foundation declined 2026-11-09). Signing costs money, so it is a Tier 3 owner decision.
- **F4:** `wizard_post` (`src/freemyid/wizard/server.py`, finish branch) saves the profile, clears `app.state.draft`, then runs `_default_finish`, which installs the Windows scheduled task synchronously before answering. If that is slow and Finish is pressed again (or the page re-posts), the second POST gets a fresh empty draft and `build_profile` raises `SaveError("Consent has not been given.")` (`src/freemyid/wizard/draft.py:520`), although the first POST already saved. That matches "keeps popping up, but it was saved after reopening". Separately, `_consent_problem` (`server.py:86-89`) calls `consent_ok(p)` without the store, so a profile set up for a family member (authorized agent) always shows a consent problem on the dashboard. Already fixed on origin/main by 682929ed (2026-11-12), after v0.3.1, so the live build still has it.
- **F5:** the fill window runs under a strict per-broker host allowlist plus a browser-wide `--host-resolver-rules` floor (`src/freemyid/engine/browser.py`). A redirect to a host missing from `broker.domains` (for example `www.`, a regional domain, or an opt-out portal on another domain) raises `BlockedByPolicy`, and `fill_for_me` closes the window right away with `fallback("blocked")` (`src/freemyid/engine/fill_for_me.py`). To the person that looks like a crash, with no message.
- **F6:** Cloudflare Turnstile regularly fails inside an automation-controlled browser even when a real person clicks. Project rule (EVIDENCE_ENGINE.md, shared rule 5): no evasion, ever. The fix is a clear hand-off to the person's normal browser, not hiding automation.
