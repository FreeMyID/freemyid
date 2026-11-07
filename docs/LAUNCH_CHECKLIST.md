# Launch checklist: before FreeMyID/freemyid goes public

## Status and plan (orchestrator, 2026-11-06 night)

Done items are ticked below. What's left, in order:

1. **History rewrite → fresh repo** (O, user-approved; old repo renamed freemyid-old, cleaned history pushed to a new FreeMyID/freemyid): waiting on qa-security's hanging-test fix → session 00 pauses its agents → d7 runs scrub.sh → O verifies → force-push → peers re-sync → `git config user.name "Free My ID"` + noreply email in the repo.
2. **Quality gate** (O + qa-security): suite green with and without brokers/registry.yaml; mypy 0. Open work: move `src/freemyid/engine/_test_drafts/` into tests/ (it would ship inside the package) and fix its 4 mypy errors; confirm every SEC item is closed in docs/SECURITY_REVIEW.md (no strict xfails remain); sign off SEC-38 (accepted as designed).
3. **CI + v0.1.0** (O): push → CI green → tag `v0.1.0` → release with SHA256SUMS.txt → send version/size/hash to the site (site_src/data/release.yaml).
4. **VM walkthrough** (O): install the v0.1.0 release on the clean Windows 11 snapshot through SmartScreen; all 6 screens + dashboard + a practice-mode run; real screenshots for the download page. Windows 10 VM still needed (none yet).
5. **Repo hygiene** (session 00 / brand-marketing): issue templates (bug, "broker is wrong"), repo description + topics + social preview; README re-read for public visitors. SPDX headers: optional (pyproject + LICENSE already declare AGPL-3.0-or-later).
6. **User decisions still open:** trademark clearance timing; which internal files ship (CLAUDE.md, .claude/agents/, docs/handoff/, PROGRESS.md; recommended: keep, they're scrubbed); social handles.
7. **Go day** (user says go): flip public → branch protection on main → enable Pages → check https://freemyid.github.io/freemyid/ + download from a clean machine → site re-check of "open source"/source links (WR-8) → PyPI + winget submissions (ONBOARDING_PATHS.md) → first social post.

Making the repo public is hard to undo: forks, caches and archive crawlers keep copies. Every box must be ticked, and **the user gives the final go** (CLAUDE.md: ask before outward-facing steps). Owner names follow the session split: **O** = orchestrator, **B** = brand/docs session, **U** = user.

Findings from a scan on 2026-11-06 are marked 🔎.

## 1. Legal and name

- [ ] **Trademark clearance for "Free My ID"** by an attorney (paid, so the user decides when). Known risks: the registered MYID mark (Intercede, identity software) and MYIDCARE (identity protection). Web screening only so far; see docs/BRAND.md. **U**
- [ ] No ™/® used until something is filed. **B**
- [x] **Registry data license chosen.** **U decides, O implements** ✅ 2026-11-06: sample-only public registry (`brokers/registry.sample.yaml`) under CC BY-NC 4.0; full registry private, all rights reserved (brokers/LICENSE-DATA.md).
- [ ] LICENSE (AGPL-3.0-or-later) present, with SPDX/headers consistent. **O**
- [x] Marketing and site copy checked against the "never use" list in docs/MARKETING_COPY.md: no "terrorists/thieves/illegal", no insults attached to named brokers, no "guaranteed/erased". **B** ✅ (2026-11-07) README, MARKETING_COPY, POSITIONING and docs/marketing/ audited against the never-use list; unsourced price/time claims and 'make them' wording removed.
- [x] Every factual claim with a citation verified (ODNI 2023 report on agencies buying commercially available information, PADFA 2024, DOJ bulk-data rule) before it appears publicly. **B** ✅ (2026-11-07) ODNI (Jan 2022 report, released June 2023), PADFA (Pub. L. 118-50) and the DOJ rule (28 CFR 202, effective 8 Apr 2025) verified with live URLs, listed in MARKETING_COPY Sources. The CFPB Dec 2024 'scammers, stalkers' proposal was withdrawn 15 May 2025, so it is dropped.
- [ ] No implied government affiliation ("Do Not List"-style wording avoided; the site footer says "not a government service"). ✅ done in site/ **B**

## 2. Personal and family information, including the git history

Public means **the whole history is public**, not just the latest files.

- [x] 🔎 **zzz_legacy/ is tracked (17 files)**: the earlier family-privacy-sweep prototype, including `data/brokers.json`, agent prompts and `.claude/settings.json`. Decide whether to delete it from the history, or review every file and keep it. Recommended: drop it from the public history; it's reference-only. **U decides, O does it** ✅ dropped from the whole history (filter-repo, d7's scrub.sh).
- [x] 🔎 **Family details in docs:** docs/PLAN_V1.md, docs/POSITIONING.md and docs/handoff/wizard-packager-positioning.md mention family-specific details. Generalise them ("users in states without a comprehensive privacy law; EU residents"). **B for docs, O for PLAN_V1** ✅ generalised at HEAD (80ff6bb) and rewritten in every old commit.
- [x] 🔎 **Commit author email is the placeholder `your@email.com`** on all commits. That's harmless, but set a GitHub noreply address for future commits (`git config user.email <id>+<login>@users.noreply.github.com`). Rewriting old commits is optional. **U/O** ✅ all commits rewritten to `Free My ID <242299803+the old personal account@users.noreply.github.com>`; repo-local git config set after the push.
- [x] 🔎 Done: old personal repo names removed from PROGRESS.md/BRAND.md (and history). Still consider whether PROGRESS.md (an internal log) should ship publicly at all. **O**
- [x] Full secret and PII scan of the whole history (e.g. `gitleaks detect` or `trufflehog git file://.`, both free) with no findings: real names, addresses, phone numbers, real profile exports (`*.freemyid-profile`), mailbox passwords, `.db` files, screenshots. **O / qa-security** ✅ gitleaks 8.21.2: 0 findings on the rewritten history; fast-export grep for handles/family states/emails: 0.
- [ ] Test fixtures and dev sites use only obviously fake people (`*.example`, `.invalid`). **qa-security**
- [x] If the history needs rewriting: do it **before** the first public push, using `git filter-repo` on a fresh clone, then force-push once with the user's approval. Everyone re-clones afterwards. **O, with U approval** ✅ user approved the force-push 2026-11-06.

## 3. Product truth (site/ and app copy)

- [ ] Each site/ claim matches the shipping build (wizard-packager is checking): per-user install with no admin; "six screens" (✅ confirmed: wizard/draft.py STEPS has 6); the uninstall prompt asking whether to delete records; keyring = Windows Credential Manager; network allowlist; practice mode on by default; never asks for SSN, bank or card details. **O (wizard-packager)**
- [ ] SmartScreen walkthrough checked on a clean Windows 10 and 11 VM, with real screenshots added. **O**
- [ ] On the VM, confirm the installer still shows a page with an **Install** button (the site's download steps say "Click Install"; freemyid.iss has DisableReadyPage=yes). If not, fix the site copy. **O**
- [ ] The download link `releases/latest/download/FreeMyIDSetup.exe` resolves (needs the first release). **O**
- [x] SHA256SUMS published with the release and mentioned on the download page. **O, B for copy** ✅ build.yml release job uploads SHA256SUMS.txt.
- [ ] **Site claims re-checked on launch day**, especially "open source" and "source code" links (true only once the repo is public), the install time and the legal wording ("must answer" only where a state law applies). **B**
- [ ] The site works with no scripts, on a phone at 360 px width, in dark mode, and reads well at 200% zoom. **B**

## 4. Security and quality gate

- [ ] All open SEC items in docs/SECURITY_REVIEW.md closed or explicitly accepted. **qa-security, O**
- [ ] Tests, ruff and mypy green on CI; CI installer build and silent install/uninstall test green. **O**
- [x] `SECURITY.md` with how to report a vulnerability (a GitHub private security advisory is free). **B drafts, O commits**
- [x] The default config ships in practice mode, with no real submissions until the user turns them on. **O** ✅ `real_submissions_enabled = False` (config.py).
- [ ] Code signing: knowingly unsigned for launch (free-only decision), with the SmartScreen page explaining it. Revisit when there's revenue. **U**

## 5. Repository hygiene

- [x] README rewritten for public visitors: what it is, the scope line, the download link, "for helpers/developers" section, license. **B** ✅ (2026-11-07) README now has status/v0.1.0 link, scope line, helper note, 'For developers and contributors' heading, license.
- [x] `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (Contributor Covenant), issue templates (bug, broker-is-wrong report). **B drafts** ✅ (2026-11-07) CONTRIBUTING (data-license line fixed), CODE_OF_CONDUCT and the issue templates reviewed for tone and accuracy.
- [ ] Decide what internal files ship: CLAUDE.md, .claude/agents/, docs/handoff/, PROGRESS.md. Recommended: keep the agent setup (it's interesting and harmless once family references are scrubbed), but review each file first. **U decides**
- [ ] Repo description, topics (`privacy`, `data-brokers`, `opt-out`, `ccpa`, `gdpr`), and the social-preview image. **B**
- [ ] Branch protection on main (free for public repos). **O**
- [ ] After the fresh-repo move: old repo renamed `FreeMyID/freemyid-old` (private, archived). It still holds 5 CI artifacts containing the FULL private registry; delete those artifacts or the whole old repo before launch. **U decides, O does it**
- [ ] New repo settings re-applied: Actions workflow permissions, Pages source, topics, branch protection; collaborator re-invites only if the user wants (the old repo had one besides the owner). **O, U for invites**

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
