# Launch checklist: before FreeMyID/freemyid goes public

Making the repo public is hard to undo: forks, caches and archive crawlers keep copies. Every box must be ticked, and **the user gives the final go** (CLAUDE.md: ask before outward-facing steps). Owner names follow the session split: **O** = orchestrator, **B** = brand/docs session, **U** = user.

Findings from a scan on 2026-11-06 are marked 🔎.

## 1. Legal and name

- [ ] **Trademark clearance for "Free My ID"** by an attorney (paid, so the user decides when). Known risks: the registered MYID mark (Intercede, identity software) and MYIDCARE (identity protection). Web screening only so far; see docs/BRAND.md. **U**
- [ ] No ™/® used until something is filed. **B**
- [ ] **Registry data license chosen.** brokers/LICENSE-DATA.md is still a placeholder ("all rights reserved… decision pending"). Choose before public, because it decides whether forks can reuse the broker list (that's the paid-feed question). Options: CC BY-NC-SA, ODbL, or keep it proprietary and ship only a sample registry publicly. **U decides, O implements**
- [ ] LICENSE (AGPL-3.0-or-later) present, with SPDX/headers consistent. **O**
- [ ] Marketing and site copy checked against the "never use" list in docs/MARKETING_COPY.md: no "terrorists/thieves/illegal", no insults attached to named brokers, no "guaranteed/erased". **B**
- [ ] Every factual claim with a citation verified (ODNI 2023 report on agencies buying commercially available information, PADFA 2024, DOJ bulk-data rule) before it appears publicly. **B**
- [ ] No implied government affiliation ("Do Not List"-style wording avoided; the site footer says "not a government service"). ✅ done in site/ **B**

## 2. Personal and family information, including the git history

Public means **the whole history is public**, not just the latest files.

- [ ] 🔎 **zzz_legacy/ is tracked (17 files)**: the earlier family-privacy-sweep prototype, including `data/brokers.json`, agent prompts and `.claude/settings.json`. Decide whether to delete it from the history, or review every file and keep it. Recommended: drop it from the public history; it's reference-only. **U decides, O does it**
- [ ] 🔎 **Family details in docs:** docs/PLAN_V1.md, docs/POSITIONING.md and docs/handoff/wizard-packager-positioning.md mention family-specific details. Generalise them ("users in states without a comprehensive privacy law; EU residents"). **B for docs, O for PLAN_V1**
- [ ] 🔎 **Commit author email is the placeholder `your@email.com`** on all commits. That's harmless, but set a GitHub noreply address for future commits (`git config user.email <id>+<login>@users.noreply.github.com`). Rewriting old commits is optional. **U/O**
- [ ] 🔎 PROGRESS.md line 21 now says "The empty old personal repo can be deleted". That's a find-and-replace artifact of the rename: the empty repo is actually `the old personal repo`. Fix it, and consider whether PROGRESS.md (an internal log) should ship publicly at all. **O**
- [ ] Full secret and PII scan of the whole history (e.g. `gitleaks detect` or `trufflehog git file://.`, both free) with no findings: real names, addresses, phone numbers, real profile exports (`*.freemyid-profile`), mailbox passwords, `.db` files, screenshots. **O / qa-security**
- [ ] Test fixtures and dev sites use only obviously fake people (`*.example`, `.invalid`). **qa-security**
- [ ] If the history needs rewriting: do it **before** the first public push, using `git filter-repo` on a fresh clone, then force-push once with the user's approval. Everyone re-clones afterwards. **O, with U approval**

## 3. Product truth (site/ and app copy)

- [ ] Each site/ claim matches the shipping build (wizard-packager is checking): per-user install with no admin; "six screens"; the uninstall prompt asking whether to delete records; keyring = Windows Credential Manager; network allowlist; practice mode on by default; never asks for SSN, bank or card details. **O (wizard-packager)**
- [ ] SmartScreen walkthrough checked on a clean Windows 10 and 11 VM, with real screenshots added. **O**
- [ ] The download link `releases/latest/download/FreeMyIDSetup.exe` resolves (needs the first release). **O**
- [ ] SHA256SUMS published with the release and mentioned on the download page. **O, B for copy**
- [ ] **Site claims re-checked on launch day**, especially "open source" and "source code" links (true only once the repo is public), the install time and the legal wording ("must answer" only where a state law applies). **B**
- [ ] The site works with no scripts, on a phone at 360 px width, in dark mode, and reads well at 200% zoom. **B**

## 4. Security and quality gate

- [ ] All open SEC items in docs/SECURITY_REVIEW.md closed or explicitly accepted. **qa-security, O**
- [ ] Tests, ruff and mypy green on CI; CI installer build and silent install/uninstall test green. **O**
- [ ] `SECURITY.md` with how to report a vulnerability (a GitHub private security advisory is free). **B drafts, O commits**
- [ ] The default config ships in practice mode, with no real submissions until the user turns them on. **O**
- [ ] Code signing: knowingly unsigned for launch (free-only decision), with the SmartScreen page explaining it. Revisit when there's revenue. **U**

## 5. Repository hygiene

- [ ] README rewritten for public visitors: what it is, the scope line, the download link, "for helpers/developers" section, license. **B**
- [ ] `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (Contributor Covenant), issue templates (bug, broker-is-wrong report). **B drafts**
- [ ] Decide what internal files ship: CLAUDE.md, .claude/agents/, docs/handoff/, PROGRESS.md. Recommended: keep the agent setup (it's interesting and harmless once family references are scrubbed), but review each file first. **U decides**
- [ ] Repo description, topics (`privacy`, `data-brokers`, `opt-out`, `ccpa`, `gdpr`), and the social-preview image. **B**
- [ ] Branch protection on main (free for public repos). **O**

## 6. Accounts and presence (free)

- [ ] GitHub org `FreeMyID`. ✅ created by the user
- [ ] GitHub Pages enabled once the repo is public (pages.yml is ready). **O**
- [ ] Social handles `freemyid` on Facebook, X and YouTube reserved, with no posts until launch. **U**
- [ ] PyPI `freemyid` (`pipx install freemyid`) and a winget manifest (`winget install FreeMyID.FreeMyID`) submitted at launch; see docs/ONBOARDING_PATHS.md. **O**

## 7. Release and go

- [ ] First release tag `v1.0.0` (or `v0.x` for a soft launch), signed off by the orchestrator after CI is green and the VM walkthrough passes. **O**
- [ ] Final review of this list, then **the user says "go"**. **U**
- [ ] Flip the repo to public, confirm Pages is live at https://freemyid.github.io/freemyid/, and test the download from a clean machine. **O**
- [ ] Post the first social post from docs/MARKETING_COPY.md. **U**
