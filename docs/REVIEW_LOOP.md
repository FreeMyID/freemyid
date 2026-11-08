# Review loop: CodeRabbit on every change, in-house applies the fixes

Owner rule (2026-11-08): CodeRabbit reviews every pull request automatically, including our own in-house work, and the in-house team applies the findings that are right. A finding is never just left as a comment.

## 1. Everything goes through a PR (auto-review)

- `.coderabbit.yaml` reviews every PR to `main` automatically, drafts included (`auto_review.drafts: true`). It never writes commits.
- **Vendor work** (Codex WOs) already arrives as draft PRs.
- **In-house work** gets a draft PR too, before it merges:
  `git push origin <branch>` then `gh pr create --draft --base main --head <branch> --title "<area>: <what>" --body "<WO/SEC/BL id, tests run>"`.
  The branch is reviewed in public, like any open-source PR. No secrets, no private files and no real personal data, as always.
- The merge itself stays local `--no-ff` under the noreply identity (docs/SDLC.md, SEC-93c). When main is pushed, GitHub marks the PR merged. Never use the web merge button or `gh pr merge`.

## 2. Collect the findings

```
tools/coderabbit_findings.py <PR> [<PR> ...]      # or --open for every open PR
tools/coderabbit_findings.py --open --out docs/reviews/coderabbit-YYYY-MM-DD.md
```

The tool merges duplicate findings, sorts them by severity (Critical, Major, Minor, Nitpick) and prints one checklist row each with a link. It only reads; it never posts.

## 3. Triage and apply (in-house)

qa-security (Marcus) owns the triage. Each row gets one disposition, checked against the **current** code (CodeRabbit may have reviewed an older commit):

| Disposition | What happens |
|---|---|
| **VALID** | The owning in-house agent fixes it with a regression test (failing first for bugs). The commit message names the finding. |
| **ALREADY FIXED** | Name the commit that fixed it. |
| **INVALID** | One line on why: wrong premise, out of scope, or it conflicts with a project rule. Never weaken a test to make a finding go away. |

Critical/Major VALID findings block the push, the same as MED+ SEC findings (docs/AUTONOMY.md). Minor and Nitpick VALID findings are fixed in the same cycle or get a tracked row in `docs/pm/tracked.json`. The disposition table goes in `docs/handoff/qa-security.md` under the review date.

## 4. The gate does not change

CodeRabbit is advice. A push still needs qa-security PASS plus a clean full suite on the exact SHA being pushed (memory: push tested SHA).
