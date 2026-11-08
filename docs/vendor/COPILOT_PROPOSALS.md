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

Status, 2026-11-08 (CLAUDE-P008): WO-139..WO-150 are the bulk lane in docs/BACKLOG.md. GP-06..GP-11 below are extra
CP-lane items Morgan asked for. All paths are new files inside the CP lane. Collisions: BOARD.md (my copy) has no
WO-139+ rows, so I checked against BACKLOG.md and the WO files only. Not verified by running anything.

Status, 2026-11-08 (CLAUDE-P009): recipes live in `distro/`, not `packaging/`. GP-09 now scans `distro/**/README.md`;
GP-10 only reads `packaging/docker/`. GP-06..GP-11 still open. Decision on WO-148 versus
`tests/test_cli_docs_match_source.py` still waits for Morgan.

Status, 2026-11-08 (CLAUDE-P010): GP-06 accepted as WO-151, GP-07 as WO-152 (Claire), GP-08 as WO-153, GP-09 as
WO-154 (after 151/152), GP-10 as WO-155 (Malik), GP-11 as WO-156 (Lucia). Morgan added WO-157 (Claire, CLI.md
`app`/`fill`/`wipe` examples). The WO-148 versus `tests/test_cli_docs_match_source.py` question is closed: WO-148
says not to duplicate. No open proposals.

Status, 2026-11-08 (CLAUDE-P012): GP-12..GP-17 accepted as WO-158..163 and merged (Malik's WO-163 is the glob-based
wording guard). WO-126 merged. Fifth batch GP-18..GP-23 below. Evidence is from reading the repo only; no tests or
builds run. BOARD.md (my copy) has no rows after WO-122, so collisions were checked against paths only.

Status, 2026-11-08 (CLAUDE-P013): GP-18 accepted as WO-165 (Malik), GP-19 as WO-166 (Claire, notes only), GP-23 as
WO-167 (Arjun), GP-22 as WO-168 (Malik; core items: Social Security number, bank or card details, never charges you).
GP-20 queued until WO-165 and WO-166 deliver, then GP-21 after GP-20. No new proposals this round.

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

## GP-06: docs/user/ install guide by platform
- Agent: app-features (Claire Dubois)
- Evidence: `site_src/data/release.yaml` says version 0.2.0 is the published release; WO-139..143 add recipes for channels that are not published yet. Nothing in `docs/user/` (does not exist yet) tells a reader which way to install on which system.
- Proposed allowed paths: `docs/user/INSTALL.md` (new).
- Deliverable: one page, plain words, "available" only for what release.yaml lists, everything else "coming". Links to the recipes' READMEs only after they merge.
- Collisions: new file; WO-144/146 use other files in `docs/user/`.

## GP-07: docs/user/ plain-words glossary
- Agent: app-features (Claire Dubois)
- Evidence: not verified. Terms such as "broker", "opt-out", "app password" and "Bridge" appear across USER_GUIDE and the how-tos; a short shared glossary lets the how-tos link instead of re-explaining.
- Proposed allowed paths: `docs/user/GLOSSARY.md` (new).
- Deliverable: about 15 terms, one or two sentences each, taken from existing repo wording (cite the file) or marked "not sure". No absolute privacy claims.
- Collisions: new file.

## GP-08: Link checker for CP-owned docs
- Agent: test-quality (Malik Johnson)
- Evidence: not verified; I have not found a broken link. CP-10 (WO-148) checks commands and flags, not links, and nothing I saw checks relative links or anchors.
- Proposed allowed paths: `tests/copilot/test_cp_doc_links.py` (new).
- Deliverable: every relative link and `#anchor` in README.md, docs/USER_GUIDE.md, docs/CLI.md and `docs/user/*.md` points at a file or heading that exists. No network; external links are listed, not fetched.
- Collisions: new file; must not duplicate WO-148 cases.

## GP-09: Wording and released-versus-coming guard
- Agent: test-quality (Malik Johnson)
- Evidence: rules in docs/POSITIONING.md and `.github/copilot-instructions.md` (no "guarantee", "erase", "100%", "never sent"; only released things are "available"). Today these are enforced by review only, and the CP lane will add many new pages.
- Proposed allowed paths: `tests/copilot/test_cp_wording_guard.py` (new).
- Deliverable: scan README, USER_GUIDE, `docs/user/*.md` and `distro/**/README.md` for banned words, and fail if a package channel (brew, AUR, Nix, Flatpak, winget, Scoop) is described as available while `release.yaml` does not list it. Allow quoted examples with an explicit marker.
- Collisions: new file. Depends on WO-139..146 existing; ships last.

## GP-10: Docker example config validates against the schema
- Agent: test-quality (Malik Johnson)
- Evidence: `packaging/docker/example-config.yaml` exists. I did not check whether anything validates it. CX-04 covers `setup --from` shapes in `tests/codex/`, so this one only covers the shipped example.
- Proposed allowed paths: `tests/copilot/test_cp_docker_example.py` (new).
- Deliverable: load the example (fake people only) and validate it against the matching file in `schema/` (read only); also check that compose.example.yaml mounts the path the example uses. If it fails, strict xfail plus a note for in-house.
- Collisions: new file; reads `packaging/docker/` (in-house, stays so per CLAUDE-P009), read only, no edits.

## GP-11: Source-level focus and label guard for shared UI components
- Agent: web-designer (Lucia Ferraro)
- Evidence: audit items CA-1 and CA-4 were both found by reading `web/src/components/ui/`. Not verified: whether other components have the same pattern.
- Proposed allowed paths: `tests/copilot/test_cp_ui_components.py` (new).
- Deliverable: a source-level test (labelled as such, not a browser run) that every interactive component in `web/src/components/ui/` has a visible focus style and does not set `.disabled` in a click handler. Report any hits as findings; do not fix them in the same work order.
- Collisions: new file; WO-149 edits the components, so land this after WO-149.

## GP-12: Local-test sections for distro recipes (answers CLAUDE-P011)
- Agent: app-ui (Arjun Rao)
- Evidence: `distro/` has READMEs for aur, flatpak, homebrew and nix only. winget and scoop have manifests (`distro/winget/`, `distro/scoop/freemyid.json`) and no README. I have not read the four existing READMEs, so I do not know which already have a test section.
- Proposed allowed paths: `distro/aur/README.md`, `distro/flatpak/README.md`, `distro/homebrew/README.md`, `distro/nix/README.md` (add a "Try it locally" section only if missing); `distro/winget/README.md`, `distro/scoop/README.md` (new).
- Deliverable: per channel, the exact local-test commands a maintainer runs, hashes still marked as placeholders, channel marked "coming" (release.yaml lists none). Commands not run on a real system are labelled unverified.
- Collisions: WO-139..143 and WO-150 merged; BOARD.md has no distro rows, so unchecked there.

## GP-13: Every docs/user/ page is reachable from INSTALL or the glossary
- Agent: test-quality (Malik Johnson)
- Evidence: a search of `docs/user/INSTALL.md` and `GLOSSARY.md` finds one link to another page, `troubleshooting.md`. Nothing found linking `mail-gmail.md`, `mail-other.md` or `mail-proton.md`. Searched with one pattern only, so a link in another form could be missed.
- Proposed allowed paths: `tests/copilot/test_cp_user_docs_reachable.py` (new).
- Deliverable: fail if any `docs/user/*.md` is not linked, directly or through one hop, from INSTALL or the glossary. If the mail pages really are unlinked, mark the test strict xfail and name the fix in GP-14.
- Collisions: new file; reuse the link parser in `test_cp_doc_links.py` by copying, not importing.

## GP-14: Link the how-tos from INSTALL (only if GP-13 finds a gap)
- Agent: app-features (Claire Dubois)
- Evidence: see GP-13.
- Proposed allowed paths: `docs/user/INSTALL.md`, `docs/user/GLOSSARY.md`.
- Deliverable: one plain sentence and link per missing how-tos page, where the reader first meets the email step. Remove the xfail from GP-13 in the same pass only if Morgan allows; otherwise Malik does it.
- Collisions: WO-151/152 merged; sequential with GP-13.

## GP-15: Helper path through docs/user/ (narrower than Morgan's idea)
- Agent: app-features (Claire Dubois)
- Evidence: `docs/HELPER_GUIDE.md` already exists, with six sections including "What Free My ID will never ask for" (section 6). A second helper guide would duplicate it and could drift.
- Proposed allowed paths: `docs/user/HELPING.md` (new).
- Deliverable: a short signpost page (under one screen): who it is for, which parts of INSTALL and the mail how-tos to do together, then a link to HELPER_GUIDE for the screens. Every claim cited to a repo file or marked "not sure". No consent or practice-mode wording beyond what HELPER_GUIDE says.
- Collisions: new file.

## GP-16: "What the app will never ask you for" (conditional)
- Agent: app-features (Claire Dubois)
- Evidence: the same content exists in `docs/HELPER_GUIDE.md` section 6 and on the website (`web/src/components/Footer.astro` links `safety/#never-asks`). I have not checked that the three versions agree.
- Proposed allowed paths: `docs/vendor/never-asks-consistency.md` (new, notes only; needs a WO that allows it).
- Deliverable: compare the app guide, the HELPER_GUIDE and the website list; report differences. A new docs/user/ page only after that, to avoid a third copy.
- Collisions: new file.

## GP-17: Wording guard covers new pages automatically
- Agent: test-quality (Malik Johnson)
- Evidence: WO-154's guard scans README, USER_GUIDE, `docs/user/*.md` and `distro/**/README.md`. GP-12 and GP-15 add files. I have not read how the guard finds files, so cannot say if a glob already covers them.
- Proposed allowed paths: `tests/copilot/test_cp_wording_guard.py` (only if it uses a fixed file list).
- Deliverable: switch to globs, and include `docs/HELPER_GUIDE.md` if it is not already scanned. If a glob already covers everything, report that and change nothing.
- Collisions: after GP-12 and GP-15 land.

## GP-18: Source citations in docs/user/ still point at real code
- Agent: test-quality (Malik Johnson)
- Evidence: the pages carry many `file.py:NNN` citations (grep count of that pattern: mail-proton 25, mail-other 26, mail-gmail 28, troubleshooting 17, INSTALL 4, HELPING 1, GLOSSARY 1), for example `ui.py:384` and `server.py:738` in `docs/user/mail-proton.md`. In-house changes `src/` often, so line numbers drift silently. I have not checked how many are already wrong.
- Proposed allowed paths: `tests/copilot/test_cp_source_citations.py` (new).
- Deliverable: for each citation, the file resolves under `src/freemyid/` (bare names like `ui.py` must match exactly one file, otherwise report as ambiguous) and the line number is within the file. Where the same line quotes a UI string in backticks or quotes, check the string exists in the cited file. Report stale citations as findings; fix them in GP-20, not here. If many fail today, mark the failing cases strict xfail with the list.
- Collisions: new file; reads `src/` only. WO-153 (link checker) covers links, not citations.

## GP-19: Audit the `TODO verify` markers in USER_GUIDE (notes only)
- Agent: app-features (Claire Dubois)
- Evidence: `docs/USER_GUIDE.md` lines 68, 78, 84, 136, 168, 178, 200, 215 carry `TODO verify`, and line 7 still says "Free My ID is still being built" although `site_src/data/release.yaml` lists v0.2.0. `docs/user/GLOSSARY.md` lines 38, 41 and 69 say "not sure" because of those markers. WO-162 shows copies of the same facts drift.
- Proposed allowed paths: `docs/vendor/user-guide-todo-audit.md` (new, notes only; the WO must allow it).
- Deliverable: one row per marker: what the guide claims, what the source says (file and line, read only), and one of resolved / still unknown / needs an outside fact (for example Google app passwords, Proton Bridge plan: say "not sure", do not fetch). No edits to the guide in this order.
- Collisions: new file.

## GP-20: Apply the audit to the guide, glossary and stale citations (conditional)
- Agent: app-features (Claire Dubois)
- Evidence: see GP-18 and GP-19.
- Proposed allowed paths: `docs/USER_GUIDE.md`, `docs/user/GLOSSARY.md`, `docs/user/mail-gmail.md`, `docs/user/mail-other.md`, `docs/user/mail-proton.md`, `docs/user/troubleshooting.md`.
- Deliverable: remove only the markers GP-19 marked resolved, update the glossary "not sure" lines to match, fix citations GP-18 flagged, and update the line 7 banner to the released state. Anything marked unknown keeps its marker. The "never asks for" wording stays out: in-house is fixing it.
- Collisions: `docs/USER_GUIDE.md` is also named in WO-162's table, but WO-162 was notes only. Start after GP-19 and after in-house finishes the "never asks for" fix, since that edits the same file.

## GP-21: Keep `TODO verify` markers and glossary "not sure" lines in step
- Agent: test-quality (Malik Johnson)
- Evidence: `docs/user/GLOSSARY.md:38,41,69` say a fact is "marked TODO verify" in the guide. When GP-20 removes a marker, those lines become false and nothing would notice.
- Proposed allowed paths: `tests/copilot/test_cp_todo_markers.py` (new).
- Deliverable: (a) a glossary line that cites a `TODO verify` marker at `USER_GUIDE.md:N` must point at a line that still has one; (b) while any marker exists, the USER_GUIDE banner must still warn readers. No count ratchet.
- Collisions: new file; land after GP-20.

## GP-22: "Never asks for" copies agree (conditional on the in-house fix)
- Agent: test-quality (Malik Johnson)
- Evidence: `docs/vendor/never-asks-consistency.md` found at least five hand-written copies that disagree (differences 1, 2, 5), for example `docs/FRIDGE_CARD.md:17` says "passwords" while setup asks for an app password. WO-163's guard bans "never sent" but does not compare lists.
- Proposed allowed paths: `tests/copilot/test_cp_never_asks_parity.py` (new).
- Deliverable: once in-house names `/safety/` the master list, check that each copy it names (USER_GUIDE, HELPER_GUIDE, FRIDGE_CARD, FAMILY_QUICK_START, families page) mentions the core items (SSN, bank or card details) and does not say a bare "passwords". If the fix has not landed, ship the failing cases as strict xfail with the reason. Which items are core is Morgan's call.
- Collisions: new file. Reads web sources and docs only.

## GP-23: Release-day placeholder list for `distro/`
- Agent: app-ui (Arjun Rao)
- Evidence: `distro/aur/PKGBUILD:36` has a `FIXME` placeholder checksum, `distro/flatpak/org.freemyid.FreeMyID.yml:28` has `sources: []` with a `TODO`, and the READMEs mention placeholder hashes. Nothing lists them in one place. I did not read the winget, scoop or homebrew files for further placeholders.
- Proposed allowed paths: `distro/CHECKLIST.md` (new).
- Deliverable: a table per channel: each placeholder, file and line, what replaces it, who does it (in-house release tooling or a maintainer), and the state "coming" until release.yaml says otherwise. Commands not run are labelled unverified. Flatpak pip sources cannot be generated without network, so that row says so.
- Collisions: new file in `distro/`; no `packaging/` edits. Note WO-154 scans `distro/**/README.md` only, so this file is not covered by that guard.

## Lucia Ferraro / Ben Adler (web)
No proposal. `web/src/components/ui/` has Alert, Badge, Card and button-variants.ts; WO-149, WO-156 and WO-126 covered the known findings. I have no new evidence-backed finding and have not re-read the components.

## Arjun Rao (app UI), earlier note
Packaging work is WO-139..143. The wizard finish step is in-house work in progress and I have no evidence-backed item elsewhere.
