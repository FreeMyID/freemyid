# broker-researcher handoff

## Pass 6 (2026-11-08): WR-61/62 clearance and timeline-claims check. Tools: Read, Write, WebFetch, WebSearch only (no shell, no grep, no git).
Deliverable: `docs/research/timeline-claims-2026-11.md` (WR answers plus claims table). Commit as Priya Shah [freemyid], paths: `docs/research/timeline-claims-2026-11.md docs/handoff/broker-researcher.md`. `brokers/registry.yaml` untouched.
- WR-61 S2 (sites list people again): cleared, sources Spokeo Compass blog and CPPA DROP page. Keep "some sites ... can".
- WR-62 S2 (whole profile removed): NOT cleared; forms are per listing. Suggested wording in the doc. S3 cleared. S4 cleared with FTC DNC FAQ wording and donotcall.gov / reportfraud.ftc.gov. The "phone numbers reach these sites from..." line has no primary source; hedge kept or soften "often" to "can".
- Timeline table: found and checked the claims in USER_GUIDE.md (145, 151, 223, 248, 250), README.md (174-175) and site_src/data/faq.yaml (66). Not found: the literal phrases "within a day" and "2-6 weeks". I had no grep, and could not scan docs/CLI.md past line 5, web/src (only faq page read), or registry lines 500+. Orchestrator: run the grep in the doc and send me the hits.
- Worth a decision: escalation fires at `typical_processing_days + 15` (3 + 15 = day 18 for Spokeo) and rung 2 cites state law, which is inside the 45-day legal window. See the table row.
- Whitepages `typical_processing_days: 2` has no primary source (site blocked to my tools).
- Spokeo's pages 403 to the fetcher; its "real time" / "1 business day" / "24-48 hours" statements came through search summaries only.

## Pass 5 (2026-11-08): v0.3 state-law letters, Bing checklist, checklist re-checks. Tools: Read, Write, WebFetch, WebSearch only (no shell, no git, no registry validate run).
Commit as Priya Shah [freemyid], explicit paths: `brokers/state_laws.yaml brokers/checklists.yaml docs/handoff/broker-researcher.md`. Run a YAML load of both files and `StateLawRegistry` first (I could not).

### state_laws.yaml (version 2026.11.2)
- Whole file rewritten. Only existing fields used. Every in-force comprehensive-law entry now has `citation` in the form "(deletion: <section>; response: <section>)", a `last_verified`, and source_urls pointing at the official text.
- STATUTE TEXT read (deletion section and 45-day window): CA (oag.ca.gov), VA 59.1-577, CO 6-1-1306 (enacted bill), UT 13-61-201(2)/203(2) (enacted 2022 bill), TX 541.051(b)(3)/541.052(b) (enrolled bill), OR 646A.574(1)(c)/646A.576(5)(a), MT 30-14-2808, DE 12D-104, IA 715D.3 (90 days), NH 507-H:4, NJ 56:8-166.10/.7, TN 47-18-3203 (bill text), MN 325M.14 subd 1(d)/subd 4(e), MD 14-4705, KY 367.3615, RI 6-48.1-5/6.  New today: MN, OR 646A.576.
- Partly verified: NE (87-1101 to 87-1130 'Data Privacy Act'; delete right is 87-1107(2)(c), read today; the 45+45 response window is NOT in 87-1107, background). IN (IC 24-15-3-1(b) delete and (c)(1) 45+45 read only on the findlaw mirror; iga.in.gov unreadable, section letters unverified). FL (501.705(2)(c) delete; no deadline in text, 45+15 is background; template stays generic).
- NOT verified: CT section number 42-518 (cga.ct.gov certificate error, justia 403). The CT AG page confirms the act name, delete right, 45 days + 45; do not quote 42-518 in a letter until a human checks. CT ag_complaint_url is the link from the AG page, form page not opened.
- Family states NC, SC, AZ are explicit `generic` with sources (checked 2026-11-06, not re-fetched). NC: S 1022 stalled; SC: only minors' AADC law; AZ: SB 1815 died, SB 1790 no evidence of enactment.
- Newer laws: nothing new in force before Nov 2026. IN, KY, RI took effect 2026-01-01. OK (2027-01-01), LA (2027-01-01), AL (2027-05-01), VT (2028-01-01) stay generic. Arkansas HB 1717 is a minors law, not comprehensive. CT amendments (2026-07-01, SB 4 on 2026-10-01) and Utah HB 418 (2026-07-01) are noted from secondary summaries only.
- Registries: Texas (SOS) and Vermont (SOS) noted as lists only; Oregon, Connecticut, NJ (2027-03-27) noted; none verified against statute.
- Engine caution: UT and IA delete rights cover only data the consumer gave the company; MD, TN, DE, UT exclude publicly available information. Letters must be requests, not demands. Authorized-agent rules were verified only for CA; other states' `authorized_agent_allowed` is left unset.

### checklists.yaml (version 2026.11.08.1)
- bing_content_removal rewritten, still `partial`. The old URL (singular /webmaster/tools/contentremovalform) loads only a title. New url https://www.bing.com/webmasters/tools/contentremoval opens a sign-in (Microsoft, Google or Facebook) so I could not see the form. Official Microsoft Support page (support.microsoft.com/en-us/topic/1831f0fe-...) read: reporting does not guarantee removal; contact the webmaster. microsoft.com/en-us/concern/bing returned empty to the fetcher. Page-removal vs outdated-cache options and the 'word that is in the cached copy' rule come from Microsoft Q&A community answers, not official pages (in notes; the cache/remove choice is in the public steps, and one tip, 'Bing will not remove a page that is still live', is community-sourced: drop it if the site wants official-only tips).
- Re-read official pages today, all still match: Experian freeze, Innovis freeze, NCTUE freeze, DMAchoice fee ($8 online / $9 mail, 10 years, payable to ANA), FTC Do Not Call FAQ. date_checked set to 2026-11-08 for these.
- Not re-fetched (bot-blocked 2026-11-07): TransUnion, ChexSystems, optoutprescreen, SSA. Equifax, LexisNexis, IRS, USPS, Google, CA DROP unchanged from 2026-11-07.
- All groups unchanged (ids unchanged), so no /protect/ group is broken. The Bing `url` host is bing.com (no new host).

### Not done
- Task 3 (re-verify the 10 oldest registry entries): not started; out of budget and the fetch tool refuses or 403s most priority sites (see Pass 3 notes). `brokers/registry.yaml` untouched.

### Needs a human or engine follow-up
1. A person with a browser: open the Bing tool, TransUnion, ChexSystems, optoutprescreen.com, and the CT statute (cga.ct.gov 42-518) and IN code (iga.in.gov).
2. Engine: use only `state_privacy` entries with `citation` whose notes say STATUTE TEXT; for CT, IN, NE quote the act name and avoid the section number.
3. Merge state_law_deletion_matrix.yaml into state_laws.yaml or a loader (still open from earlier passes). Its NE/IN/CT rows are older than this file.

## Earlier passes (kept, condensed)
- Pass 4 (2026-11-07): suppression lists and freezes compared with official pages; LexisNexis freeze is publishable (Morgan ruling 2026-11-08). Optional Pass 4 tips (replacement PIN, parents/guardians, lift only at the lender's bureau) are deferred by Morgan.
- Pass 3: DROP `required_fields` should be [full_name, dob, zip] (privacy.ca.gov/drop/how-drop-works); email/phone verification only possibly prompted. PeopleSearchNow `/opt-out` is correct; add phone 888-553-5506. Spokeo, PeopleFinders, Nuwber, MyLife 403; Whitepages, BeenVerified, TruePeopleSearch, FastPeopleSearch refused by the fetcher; Radaris still shows the Atlas transfer notice (keep disabled).
- Statute citations were checked on official legislature sites in the second pass; MT, MD and RI cites were corrected.
- CHANGE REQUESTS still open: models.py `Broker` fields `search_access`, `search_access_note`, `search_url_evidence`, `search_url_checked`, `slug_case`; `.gitignore` for `docs/research/exposure_scan_patterns.yaml`; a `Checklist` model and loader; SOURCES.md pointers; a human browser pass for the four refused sites.
- Still uncertain: Whitepages `suppression_requests` vs `suppression-requests`; BeenVerified live opt-out path; FastPeopleSearch `/removal` vs `/optout`; Cotality portal URL; whether DROP email verification is mandatory.
