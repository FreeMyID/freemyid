# USER_GUIDE TODO verify audit

Scope: every literal `TODO verify` marker in `docs/USER_GUIDE.md` and the
line-7 build banner. This is a local-source audit only; no external facts were
looked up. Line numbers below are from the current worktree/main baseline.

| Guide claim | Local source evidence | Status |
|---|---|---|
| `USER_GUIDE.md:7` — Free My ID is still being built, and marked behavior is planned and may change. | `docs/LAUNCH_CHECKLIST.md:43-45` retains unchecked build/VM work, so local project documentation still describes unfinished release work. | resolved |
| `USER_GUIDE.md:68` — new personal Google accounts can use app passwords and Gmail IMAP is enabled by default. | `src/freemyid/wizard/ui.py:213-220` contains the corresponding Gmail setup instructions, but application source cannot establish Google's current account or IMAP policy. | needs an outside fact |
| `USER_GUIDE.md:78` — Proton Mail Bridge is free and requires a paid Proton plan. | `src/freemyid/wizard/ui.py:233-236` presents Bridge as a helper app, but it does not establish Proton's current pricing or plan eligibility. | needs an outside fact |
| `USER_GUIDE.md:84` — the wizard displays Bridge's security code and asks once whether to trust it. | `src/freemyid/wizard/ui.py:382-389` renders a hidden trust dialog with the code and Yes/No buttons; `src/freemyid/wizard/server.py:726-766` obtains the code, presents the question, and saves an approved pin. | resolved |
| `USER_GUIDE.md:136` — the dashboard uses colored labels for each site, with the shown labels. | `src/freemyid/wizard/ui.py:24-40` defines and renders all ten labels used by the guide; `src/freemyid/wizard/static/style.css:112-120` assigns chip color styles. | resolved |
| `USER_GUIDE.md:168` — a person can view a possible-match screenshot and confirm or reject it through `REVIEW_MATCH` controls. | `src/freemyid/engine/handoff.py:157-175` implements the underlying yes/no resolution, but the inspected wizard/dashboard source does not establish the described screenshot and controls. | still unknown |
| `USER_GUIDE.md:178` — a person can change an ID/account/phone permission later. | `src/freemyid/wizard/dashboard.py:457-474` renders the three permission choices and Save button in Settings; `src/freemyid/wizard/server.py:611-619` saves the changed permissions. This is Settings, not a wizard-edit or documented CLI route. | resolved |
| `USER_GUIDE.md:200` — a person can open pending emails, read them, then choose **Approve and send**. | `src/freemyid/wizard/dashboard.py:377-412` renders the pending-email page and button; `src/freemyid/wizard/server.py:505-542` lists queued requests and handles approval. | resolved |
| `USER_GUIDE.md:215` — the DROP URL, agency name, and broker processing schedule are correct. | `src/freemyid/submitters/assisted.py:32-40,138-145` supplies a local URL and DROP to-do, but it does not independently verify the government agency or current processing schedule. | needs an outside fact |

Summary: 5 resolved, 1 still unknown, and 3 needing an outside fact.
