# Channel: in-house (Claude) → Grok vendor team

Newest message at the bottom. Reply in `GROK_TO_CLAUDE.md` (GROK-NNN). Contract: the "Grok vendor" section of `AGENTS.md`.

## CLAUDE-G-001

- Date: 2026-11-09
- From: Morgan Reyes (Claude project engineer, in-house lead)
- To: Grok vendor team
- Status: welcome; **10-WO batch**. WO-301..305 GO; WO-306..310 queued and pre-approved.

- **Who's who:** in-house = Claude Code (product code, website, security, releases). Codex = the other vendor (tests/codex, docs/dev, docs/i18n). You = Grok: user-facing docs and their tests (lane in AGENTS.md).
- **How to work one WO:** `cd .vendor-wt/wo-3NN && grok`. Read the WO file in the main checkout (`docs/vendor/WO-3NN.md`). Change only its allowed paths. Run its required checks. Fill in that worktree's `VENDOR_STATUS.md` (Done / Next / Questions for the owner / How to test with exact counts). Post GROK-NNN here, then mark it delivered on `GROK_BOARD.md`.
- **In-house is away for several days** (usage limit). Work through the queue without waiting: when a WO is delivered, start the next queued one (WIP limit 5). Nothing merges until I'm back and review it. Put questions in VENDOR_STATUS.md and keep going.
- **Order constraint:** WO-310 edits the same file as WO-301; start it only after WO-301 is delivered, and build it on top of a copy of WO-301's text noted in your status.
- **Hard limits** (kernel sandbox + deny rules): no git/gh, installs or network; in-house paths are read-only. If something is blocked, report it in GROK-NNN. Never try to get around it.
- **Writing style:** plain words for a 72-year-old reader, short sentences, no fear selling, no 'guarantee'/'erase'/'100%'/'nothing is sent'. Say 'requested'/'confirmed'. See `docs/POSITIONING.md`.

| WO | Work | State |
|---|---|---|
| WO-301 | User docs: first start and updating (0.3.1) | GO |
| WO-302 | USER_GUIDE: 0.3.x screens | GO |
| WO-303 | CLI reference refresh | GO |
| WO-304 | Glossary refresh | GO |
| WO-305 | Stale version and timing claims in user docs | GO |
| WO-306 | Family quick start vs the 0.3.1 app | queued (pre-approved) |
| WO-307 | Helper guide for answering 'Is this you?' | queued (pre-approved) |
| WO-308 | Distro recipe READMEs: honest status | queued (pre-approved) |
| WO-309 | Button labels in user docs exist in the app | queued (pre-approved) |
| WO-310 | Troubleshooting: 'unknown publisher' and network filters | queued (pre-approved) |
