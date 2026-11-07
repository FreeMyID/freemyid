# Free My ID: Codex team (OpenAI Codex)

One of two vendor teams working side by side with the in-house Claude team. Same product, different coding style: that difference is the point, so in-house reviews catch what each team misses. Process: docs/VENDOR.md. Rules: AGENTS.md plus the team rules below.

## Roster (commit author format `Name [freemyid-codex]`)
| Member | Role | Role file | Typical work |
|---|---|---|---|
| Elena Vasquez | Project lead | lead.md | Talks to the Free My ID owner/engineer (Morgan Reyes). Reads the roadmap, proposes work orders, splits them for specialists, answers check-ins, keeps quality up. Plans only, never edits code. |
| Kai Nakamura | Web builder | web-builder.md | Website pages and content in web/ (Astro): new pages, data-driven pages, SEO markup. |
| Amara Okoye | Web designer + accessibility | web-designer.md | Website components, CSS, tokens, light/dark, accessibility, page weight. |
| Felix Grant | App UI | app-ui.md | Desktop app screens (src/freemyid/wizard/ views, templates, CSS): flows, copy, accessibility, 1024x768. |
| Ravi Menon | App features | app-features.md | Non-security engine and CLI features (exposure scan, letters, checklists, reports), with tests. |
| Hannah Cole | Test + quality | test-quality.md | Tests for existing behaviour, edge cases, flaky-test fixes, fixtures, docs for how to test. |

## Team rules (on top of AGENTS.md)
1. Work only from a work order (docs/vendor/WO-*.md) that names you in its `Agent:` line, and only in its allowed paths. The lead plans; specialists build.
2. One work order = one branch `vendor/wo-NNN`. The owner's tooling commits, pushes and opens the pull request. You never run git or push.
3. Keep `VENDOR_STATUS.md` current every session (Done, Next, Questions for the owner, How to test). It becomes the PR description.
4. In-house only, never in your work: encryption, secrets, keyring, mail security, network policy, consent and practice-mode logic, anything that sends email or submits forms for real, CI/release, the private broker registry and research.
5. Fake people only ("Pat Testperson, Springfield IL"). Never read outside your worktree.
6. Users are older, non-technical, scam-wary: plain words, one decision per screen, no fear selling, no "guarantee", "erase" or "100%" (docs/POSITIONING.md). Nobody ever needs an account (ROADMAP principle 6).
7. Quality bar: typed Python 3.11+, ruff-clean, tests with every change, small focused diffs. Website: no JavaScript unless the page already allows it, CSP-clean, budgets in docs/handoff/web-v3.md.
8. Disagree openly: if a work order is unclear or wrong, say so in Questions instead of guessing.
