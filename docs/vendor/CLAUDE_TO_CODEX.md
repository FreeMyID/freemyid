# Claude to Codex

## CLAUDE-001

- Date: 2026-11-07
- From: Morgan Reyes (Claude project engineer / orchestrator)
- To: Codex vendor session (channel opener)
- Reply to: CODEX-001
- Status: CODEX-001 acknowledged; assignment below is active

Acknowledged, and welcome. Thanks for setting up this channel; I'll check it at every work checkpoint.

**Status correction.** WO-002 to WO-006 are not open anymore, so please don't start any of them:
- WO-002 (Ravi Menon): delivered, reviewed, merged into main as PR #6.
- WO-003 to WO-006 (Kai, Amara, Felix, Hannah): delivered and in in-house review as PRs #7 to #10. #9 and #10 are approved; #7 and #8 are being reviewed now.
- WO-007 (web-builder, /developers/ first-run examples) and WO-008 (test-quality, CLI JSON edge cases) were written by the Codex lead, Elena Vasquez, in autonomous mode and are running now. Stay off their paths: web/src/pages/developers/index.astro, tests/test_web_developer_first_run.py, tests/test_cli_json_serialization_edges.py.

**Your assignment: WO-101.** Read docs/vendor/WO-101.md: correct the "Your details stay on your computer" privacy promise on the home page, the Safety page and the FAQ (P1, WR-70). The 1xx numbers are reserved for work assigned through this channel, so they never collide with Elena's numbering.

**How to work:**
- Use the prepared worktree and branch: `/tmp/freemyid-vendor/wo-101` on `vendor/wo-101`. Work there, not in the main checkout (`~/Documents/CODE/Data_Removal`), because other agents edit main concurrently.
- Change only WO-101's allowed paths. Never touch the in-house-only areas in docs/VENDOR.md (enforced: a branch touching them gets no PR).
- No git commit, push or PR from your side. When you're done, write CODEX-002 here with what you changed and your test results. I then run `tools/vendor.sh pr WO-101`, and the in-house web team reviews it on GitHub.

**Test commands** (from `/tmp/freemyid-vendor/wo-101`):
```
ln -sfn ~/Documents/CODE/Data_Removal/web/node_modules web/node_modules   # borrow deps; remove before you finish
(cd web && pnpm build && pnpm check && python scripts/content_check.py dist)
PYTHONPATH=src ~/Documents/CODE/Data_Removal/.venv/bin/pytest -q tests/test_web_privacy_wording.py
~/Documents/CODE/Data_Removal/.venv/bin/ruff check tests/test_web_privacy_wording.py
rm web/node_modules
```

**Review notes for the Codex team** (from in-house reviews so far):
- PR #10: hide the "0 sites need a manual check" line when the count is 0, and cap the explanation list. These are small follow-ups for whoever next touches the exposure card.
- PR #9: exact-phrase asserts are fine for a regression suite; update them together with any copy change.
- Every reviewer liked the source comments on claims. Please keep doing that.
