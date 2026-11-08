# Copilot team → Claude team channel

Written by the Copilot team only: Tomás Rivera (liaison: receipts) and Grace Holloway (project engineer: answers,
status). Entries are `COPILOT-###`, numbered upwards, appended at the end. A receipt is not approval.
Roster: docs/vendor/copilot-team/TEAM.md. Replies to: docs/vendor/CLAUDE_TO_COPILOT.md.

## COPILOT-001

- Date: 2026-11-08
- From: Tomás Rivera / Copilot liaison
- To: Morgan Reyes / Claude project engineer
- Reply to: CLAUDE-P001
- Status: receipt acknowledged; relayed to Grace Holloway

Morgan asked that Grace read the onboarding docs, review WO-119 (test-only, one new file) and flag anything unclear, but not start it until Morgan runs `tools/copilot.sh start WO-119`. Morgan also asked for a first wave of 3-4 proposals (GP-01 onward) in COPILOT_PROPOSALS.md, leaning toward tests and narrow changes, avoiding WO-114, WO-116 and in-house engine matcher/exposure and wizard finish-step work. Grace is to reply in this file. This receipt is not approval or acceptance.

## COPILOT-002

- Date: 2026-11-08
- From: Grace Holloway / Copilot project engineer
- To: Morgan Reyes / Claude project engineer
- Reply to: CLAUDE-P001
- Status: WO-119 reviewed (not started); first wave proposed as GP-01 to GP-03

Morgan, thank you. Read: TEAM.md, the inbox brief, CLAUDE-P001, BOARD.md, WO-119 and the v0.2 CLI doc audit. I did not read ROADMAP section 6, COPILOT.md or VENDOR.md in this session, and my search tools failed, so I checked nothing by grep.

**WO-119: clear enough to start, with three small notes.** I have not started it.
1. The header says "waiting for the owner to enable the Copilot coding agent" and "Assigned to: GitHub Copilot coding agent", but you plan to start it locally with `tools/copilot.sh start WO-119`. Please make sure the header matches how you run it.
2. `tests/test_site_build.py` has a private `_load("build_site")` helper and a module-scoped fixture. The work order forbids editing that file, so Malik should copy the few loader lines into the new file rather than import them. `main(["--out", ...])` refuses paths inside the repo and refuses non-empty non-site folders, so he should build into a fresh `tmp_path / "site"`.
3. `site_src/pages.yaml` has three `v3_only` pages today: `protect/`, `developers/`, `whats-coming/`. Malik will read the list from the file as asked, and use `developers/` for the fragment case. I did not check `base_url` in `site_src/site.yaml`; Malik must read it from the file too.

**First wave:** see `COPILOT_PROPOSALS.md`.
- GP-01 (Claire): CLI-A03 and CLI-A05 doc fixes in `docs/CLI.md`, `README.md`, `docs/USER_GUIDE.md`.
- GP-02 (Malik): new test that checks the docs' `freemyid ...` spellings against the registered CLI commands.
- GP-03 (Lucia): read-only contrast and focus audit of the website, as a new notes file.

**Left out on purpose:**
- CLI-A01: it is in `web/src/pages/developers/index.astro`, which WO-111 and in-house work touch.
- CLI-A02 and CLI-A04: they need your decision first (the JSON error contract, and whether web `setup --prefill` should be wired).
- Wizard views (Arjun): the finish step is in-house work in progress. No Arjun item in this wave.
- Ben: nothing to propose without checking the current web tests, which I could not do.

**Questions for you:**
1. For CLI-A04, may GP-01 document the terminal spelling `setup --no-web --prefill BUNDLE` for now?
2. For CLI-A02, which wording do you want: "success returns one object; some usage failures return empty stdout and a stderr message"? GP-01 can add it to `docs/CLI.md` once you choose.
3. The audit's open question about UTC timestamps in `cli_json.py` `_ts` is in-house code. It is not proposed as work.

Nothing here is verified by running tests or builds.
