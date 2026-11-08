# Copilot team proposals

Written by Grace Holloway (Copilot project engineer). Items are `GP-##`. Proposals are not work orders: Morgan Reyes
accepts or declines them in docs/vendor/CLAUDE_TO_COPILOT.md and writes the work order. Check docs/vendor/BOARD.md for
path collisions before proposing; never propose an in-house-only path (.github/copilot-instructions.md).

First wave, 2026-11-08 (reply to CLAUDE-P001). Collisions checked by eye against BOARD.md (state at CODEX checkpoint
CODEX-037); none of these paths are listed there. I did not run a repo search, so evidence lines cite the audit.

Status, 2026-11-08 (CLAUDE-P002..P004): GP-01 accepted as WO-120 (Claire, includes CLI-A02 and CLI-A04 wording),
GP-02 accepted as WO-121 (Malik, queued until WO-120 merges), GP-03 accepted as WO-122 (Lucia, notes only). No open
proposals. An accessibility pass is deferred until WO-122 reports.

Status, 2026-11-08 (CLAUDE-P005): WO-119..123 merged. Second wave GP-04 and GP-05 proposed below (from Lucia's
WO-122 audit); nothing for Arjun, see the note at the end.

Status, 2026-11-08 (CLAUDE-P006): GP-04 accepted as WO-125 (Ben, Lucia reviews colour); GP-05 accepted as WO-126
(Ben, after WO-125, reproduce first). No open proposals; nothing for Arjun.

Status, 2026-11-08 (CLAUDE-P007): GP-04 merged locally as WO-125 (a9c83fd). GP-05 (WO-126) go ahead: Morgan
reproduced the focus loss in Chromium, and the scope is amended so Ben changes only the two
`to_be_disabled`/`to_be_enabled` assertions in the existing keyboard test (aria-disabled checks). This replaces
"add cases only" in GP-05 below; WO-126 is the source of truth. No open proposals; nothing for Arjun.

## GP-01: CLI docs fixes (CLI-A03, CLI-A05)
- Agent: app-features (Claire Dubois)
- Evidence: `docs/vendor/v02-cli-doc-audit.md` rows CLI-A03 (CLI.md command table omits `checklist list/show/done/undo`) and CLI-A05 (README and USER_GUIDE do not link to CLI.md). Both are labelled P3 and narrow in the audit.
- Proposed allowed paths: `docs/CLI.md`, `README.md`, `docs/USER_GUIDE.md`.
- Deliverable: add four checklist rows to the CLI.md table with the existing schema names (`checklists/1`, `checklist/1`) and a short "full reference" link in README and the USER_GUIDE helper section. Keep the user guide short and keep released versus planned wording. Optional, if Morgan agrees: CLI-A04 terminal prefill spelling.
- Collisions: WO-002 once held CLI.md and is merged; the board shows no active hold. Morgan to confirm no in-house edit of README or CLI.md is open.
- Not included: CLI-A01 (developer page, held by WO-111 and in-house), CLI-A02 and CLI-A04 wording (need Morgan's decision).

## GP-02: Docs spellings match the CLI (test only)
- Agent: test-quality (Malik Johnson)
- Evidence: CLI-A01 and CLI-A03 are both cases of docs naming a command that does not match the registered CLI. Nothing tests that. Existing tests cover JSON output, not docs.
- Proposed allowed paths: `tests/test_cli_docs_match_source.py` (new).
- Deliverable: using the Typer app in `src/freemyid/cli.py` (read only), check that every command and subcommand appears in the `docs/CLI.md` command table, and that each `freemyid <words>` example in `docs/CLI.md`, `README.md` and `docs/USER_GUIDE.md` resolves to a real command. Hidden commands such as `run --scheduled` are exempt. No network, no new dependencies, fake data only.
- Dependency: lands after GP-01. If it must go first, the checklist case ships as a strict xfail with a reason.
- Collisions: new file; no overlap on the board.

## GP-03: Website contrast and keyboard-focus audit (notes only)
- Agent: web-designer (Lucia Ferraro)
- Evidence: not verified. This is a proposal to find evidence, not a claim of a defect. The older Codex CP-09 families audit is unstarted per the board, so this one avoids `web/src/pages/families/`.
- Proposed allowed paths: `docs/vendor/web-contrast-audit.md` (new).
- Deliverable: read-only review of design tokens and shared components in `web/` for text and background contrast and visible keyboard focus, with file and line evidence, a proposed fix list and any measured ratios labelled as computed or unverified. No edits to `web/`; Morgan decides what becomes a work order.
- Collisions: new file in `docs/vendor/`; the work order must name it explicitly as allowed.

## GP-04: Fix the `onBrand` button hover (CA-1)
- Agent: web-builder (Ben Adler), with Lucia Ferraro reviewing the colour choice.
- Evidence: `docs/vendor/web-contrast-audit.md` CA-1 (computed 1.15:1 in dark on hover). I re-read
  `web/src/components/ui/button-variants.ts:19`: `onBrand: "bg-band-brand-ink text-band-brand hover:bg-bg-alt"`. Only
  user: `CtaDownload look="onBrand"` at `web/src/pages/index.astro:316`. Not re-computed by me; not run in a browser.
- Proposed allowed paths: `web/src/components/ui/button-variants.ts`, `tests/test_web_button_hover_contrast.py` (new),
  `VENDOR_STATUS.md`.
- Deliverable: change the hover so the button stays light in both themes (audit suggests
  `hover:bg-band-brand-ink/90`; builder must re-compute both themes and report the ratios, at least 4.5:1 text on
  hover). A new test reads the token values and the class string and asserts the hover pair passes 4.5:1 in light
  and dark. Run `pnpm build`, `pnpm check` and the content check.
- Not included: `tokens.css` (if a new token is needed, ask in Questions) and CA-2 (`Section.astro`): I grepped
  `web/src` for `tone="brand"` and found no use, so it is not urgent.
- Collisions: board shows no hold on these paths (WO-103/WO-107 hold `index.astro`, which is not touched).

## GP-05: Keep keyboard focus on the Copy button (CA-4)
- Agent: web-builder (Ben Adler).
- Evidence: audit CA-4 says focus may drop. Confirmed in source only: `web/src/components/CopyHash.astro` sets
  `button.disabled = true` before the clipboard call and `false` in `finally`. Whether focus really drops is **not
  verified**; browsers differ. The work order should make the builder reproduce it first, and stop if it cannot.
- Proposed allowed paths: `web/src/components/CopyHash.astro`, `tests/test_web_copy_hash.py` (existing, add cases
  only), `VENDOR_STATUS.md`.
- Deliverable: replace `disabled` with `aria-disabled="true"` plus an early return while pending, so the button keeps
  focus and the status text still announces. Test: the script no longer sets `.disabled`, and a double click copies once
  (use the browser harness already in that test file if present, otherwise a source-level check labelled as such).
- Collisions: WO-104 and WO-108 touched these files and are merged (BOARD.md); no active hold seen.

## Arjun Rao (app UI)
No proposal. The wizard finish step is in-house work in progress and I have no evidence-backed item elsewhere.
