# VENDOR_STATUS.md

WO-329 (issue pending). Plain-language glossary. Margaret Lund.
Status: Done.

## Done

`docs/user/GLOSSARY.md` already held WO-304's delivered text when this session started (21 entries, that order). This session did not recopy it and did not open `.vendor-wt/wo-304`. Every WO-304 entry is still here, in the same order. None was removed.

Built on that text:

- Release line no longer calls 0.2.0 the current download. It now follows `site_src/data/release.yaml:5-7`: version 0.3.1, dated 2026-11-10, about 64.6 MB. The app reports 0.3.1 (`src/freemyid/__init__.py:2`).
- Kept the practice-mode definition and added the banner label "Practice mode" (`dashboard.py:237`).
- Named the review card "Is this you?" and kept the Yes / No meaning.
- Kept requested, confirmed, and relisted. Relisted also says came back. The screen words "reappeared" and "It came back. We are asking again" are quoted.
- Real requests quotes "Start sending real requests" (`dashboard.py:515`).
- Assisted step quotes "Do it with me", "I did it", and "Fill it in for me".
- Run automatically is also the scheduled check. The heading quoted is "Run automatically" at `dashboard.py:502` (not 501).
- Added, at the end: credit freeze, Larger text, SHA-256 check (what it is for, not how to work the code out), and placeholder (for helpers reading distro notes).
- App labels sit on the same line as a `src/freemyid/...py:NNN` HTML comment. No new links. Example person remains Jane Q Testperson, Springfield IL.

One citation inside the practice-mode entry was dropped, not the entry. Reason: `src/freemyid/engine/runner.py:467` is now `listings, scanned = await self._scan(...)`, not practice-mode words. The other practice-mode citations stay (`dashboard.py:237-238`, `runner.py:270-271`).

## Next

In-house review. This work order allows only `docs/user/GLOSSARY.md` and this file, so `docs/vendor/GROK_TO_CLAUDE.md` and `docs/vendor/GROK_BOARD.md` were not updated. WO-330 is the pass that links the new help pages. A later pass should refresh `docs/user/INSTALL.md` so it stops calling 0.2.0 the current download (see Findings).

## Questions

- The work-order note said the release record was 0.3.0, dated 2026-11-09, about 64.5 MB, and that the app reports 0.3.1. On disk, `site_src/data/release.yaml` is 0.3.1, 2026-11-10, 64.6 MB, and `src/freemyid/__init__.py:2` is also 0.3.1. The glossary follows the file. Should it instead still say 0.3.0?
- `AGENTS.md:8` says v0.3.1 was released 2026-11-09 (and v0.3.0 the same day). The yaml date is 2026-11-10. Which date should user pages use?
- May a later work order correct `docs/user/INSTALL.md` (still 0.2.0)? It is outside this order's allowed paths.

## How to test

From `.vendor-wt/wo-329`:

`PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/copilot/test_cp_doc_links.py tests/copilot/test_cp_source_citations.py tests/copilot/test_cp_wording_guard.py tests/copilot/test_cp_user_docs_reachable.py`

Result: 410 passed in 1.22s. 0 failed.

Collected counts: `test_cp_doc_links.py` 15, `test_cp_source_citations.py` 348, `test_cp_wording_guard.py` 38, `test_cp_user_docs_reachable.py` 9. Total 410.

`tests/grok/` is not in this worktree, so that extra check was not run.

## Findings

- Release record on disk is not the 0.3.0 / 2026-11-09 / about 64.5 MB figure in the work-order note. `site_src/data/release.yaml:5-7` is version 0.3.1, date 2026-11-10, size_mb 64.6. `src/freemyid/__init__.py:2` is `__version__ = "0.3.1"`. `AGENTS.md:8` dates that release 2026-11-09. The glossary uses the yaml. It does not call 0.2.0 the current download.
- `docs/user/INSTALL.md:12-18`, `:48`, `:71-73`, and `:78` still say version 0.2.0 is what is published today. That is stale against `release.yaml`. Not edited: outside this order's allowed paths.
- `distro/CHECKLIST.md:3` still says `release.yaml` records version 0.2.0. Same limit. Not edited.
- The on-screen review title is not the literal words "Is this you?". `src/freemyid/engine/runner.py:1000` builds `Is this {profile.label}?`. The literal "Is this you?" card is the name in `src/freemyid/wizard/dashboard.py:113`. Buttons "Yes, this is me" and "No, this is not me" are `dashboard.py:122-123`.
- "Fill it in for me" is `src/freemyid/wizard/dashboard.py:157`. "I did it" is `dashboard.py:165`. The glossary cites that range.
- "Run automatically" is the heading at `src/freemyid/wizard/dashboard.py:502`, not line 501.
- SHA-256 in the app (`src/freemyid/engine/mail_tls.py:5`) is the mail-certificate check, which the screen calls a security code (`mail_tls.py:198`). The download check is the published code in `site_src/data/release.yaml:8`. The glossary says what each is for and does not say how to compute either.
- Placeholder in this glossary means a stand-in checksum in the distro notes (`distro/CHECKLIST.md:20`), not the blank hint in a web form.
- No product bug was fixed in `src/`. No new markdown links were added, so the existing `docs/user/` pages stay reachable the same way. New help pages from WO-311..320 were not linked.
