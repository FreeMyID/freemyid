# broker-researcher handoff (registry refresh pass, 2026-11-07)

## Pass 4 (2026-11-07): suppression lists and credit freezes (ROADMAP 3.4). Tools: Read, Write, WebFetch, WebSearch only. No git, no in-place edit.
Compared the existing `brokers/checklists.yaml` (version 2026.11.07.2) against official pages re-fetched this pass. The file already covers every item requested (DMAchoice, optoutprescreen, national_do_not_call, freeze_equifax, _experian, _transunion, _innovis, _chexsystems, _nctue, _lexisnexis). I did NOT rewrite the 348-line file by hand (typo risk); nothing in it is wrong. Apply these small edits as Priya Shah [freemyid], explicit path `brokers/checklists.yaml` plus this handoff.

Fetched today:
- https://consumer.risk.lexisnexis.com/freeze : LOADS, matches. Says "LexisNexis Risk Solutions does not charge a fee to apply, lift or remove a security freeze". Online forms (freeze, temporary lift, permanent removal, replacement PIN; for self, a minor under 16 or a protected consumer); mail LexisNexis Risk Solutions Consumer Center, Attn: Security Freeze, P.O. Box 105108, Atlanta, GA 30348-5108; phone 1-800-456-1244. A confirmation letter arrives by mail. Page does not say what ID is needed or how a PIN is used by phone/mail. Applies only at LexisNexis. ANSWER: freeze_lexisnexis CAN be published (verification official_page, already set). Edits: (a) in `tips` add "A replacement PIN can be ordered on the same online form." (b) add tip "Parents and guardians can use the same online forms for a child under 16." (c) `notes`: "Re-read 2026-11-07, all steps and phone match. Page does not say what ID is needed."
- https://www.equifax.com/personal/credit-report-services/credit-freeze/ : matches existing entry (free, (888) 298-0045, myEquifax 18+, text one-time PIN or credit-report questions). Add tip: "Under 18 or no online account? Call (888) 298-0045. Parents or guardians can freeze a child under 16 with Equifax's Minor Freeze Request form."
- https://www.consumer.ftc.gov/articles/what-know-about-credit-freezes-fraud-alerts : "There's no cost to place or lift a credit freeze"; anyone can freeze for any reason; lasts until you lift it; contact all three bureaus; suggests lifting only at the bureau the lender will use, then putting it back. No PINs or phone numbers on the page. Add tip to freeze_transunion or freeze_equifax: "Applying for a loan? Ask the lender which bureau it uses, lift the freeze only there, then put it back."
- Still HTTP 403, so UNVERIFIED and left as `partial`: transunion.com/credit-freeze, optoutprescreen.com, chexsystems.com/security-freeze/place-freeze. No workaround tried. Existing public text for these already stays within what the FTC/CFPB pages support.
- donotcall.gov and donotcall.gov/faq.html load but return only navigation text (no steps), so national_do_not_call remains sourced from the FTC FAQ (official, previously read). Correct `verification` is arguably `official_page` (FTC is the owner); keep, and note in `notes` that donotcall.gov itself returns no step text to our fetcher.
- DMAchoice, Innovis, NCTUE, Experian, IRS, SSA: no re-fetch this pass; entries unchanged from pass 3.

No new files, no model changes. CHANGE REQUEST: none beyond the earlier list below.

## Refresh pass 3 (2026-11-07): tool limits and ready-to-apply edits
This session had only WebFetch, WebSearch, Read and Write. No shell, no in-place edit, no git. I did NOT rewrite `brokers/registry.yaml` (large, not fully read) or `registry.sample.yaml` by hand (typo risk). Nothing is committed; `pytest -k registry` and the health check were NOT run. The two DROP/PSN edits below are small; apply them (as Priya Shah [freemyid], explicit paths `brokers/registry.yaml brokers/registry.sample.yaml`).

### 1. California DROP (ca_drop) - recommendation, supported by official pages
Sources (all fetched/searched 2026-11-07):
- https://privacy.ca.gov/drop/how-drop-works/ : "You only need to provide your name, date of birth, and ZIP code to submit a request." Email and phone are listed as basics but are not stated to be required. Street address is not mentioned anywhere. MAID, connected-TV ID and VIN are optional. "Residency verification is managed via the California Identity Gateway." No email or phone verification step is described on that page.
- https://privacy.ca.gov/2026/10/drop-faq-blog/ : the second step "may" prompt the user "to enter and verify some of the same information, like your phone number and email address"; takes up to 90 days; no 45-day statement on that page (the 45-day rule is from the Delete Act, keep the existing legal note).
- https://privacy.ca.gov/drop/ : eligibility uses the California Identity Gateway (enter info directly or sign in with Login.gov); the page lists no required fields.
Decision:
- `required_fields`: change `[full_name, street_address, city, state, zip, dob, email]` to `[full_name, dob, zip]` (supported by the quote above).
- `needs_email_verification`: KEEP `true`, or set `false` if you want the strict reading. Reason: the FAQ says the user "may be prompted" to verify email and phone at the gateway step, but no page says it is mandatory. It is a human hand-off either way (TodoKind.GOVERNMENT_PORTAL), so the flag has no automation effect. I lean keep-true, label "possible".
- Add to `verification_notes`: "Required fields per privacy.ca.gov/drop/how-drop-works (2026-11-07): name, DOB, ZIP only. Email/phone verification may be prompted at the California Identity Gateway (FAQ blog 2026-10), not stated as mandatory. consumer.drop.privacy.ca.gov itself not fetched." Add the two URLs above to `source_urls`.
- Keep `last_verified: 2026-11-07`. Do not add dob/street data to what Free My ID stores for DROP: it is a human step.

### 2. Re-verification of the oldest entries
Oldest `last_verified` in the sample are experian and equifax (2026-11-05), but they are not NC/SC/AZ hotspots; most people-search entries have NO `last_verified` (they are unverified). I tried the priority sites. Results, no mirrors or bypasses used:
- Spokeo /optout: HTTP 403. Stays unverified. No change.
- PeopleFinders /opt-out: HTTP 403. Nuwber /removal/link: HTTP 403. MyLife /privacyrequest: HTTP 403. PeopleConnect /login: loads but returns only the title "PeopleConnect - Suppression Center" (JS app), flow unconfirmable. No change.
- Whitepages, BeenVerified, TruePeopleSearch, FastPeopleSearch: the fetch tool refuses these domains. Unverified. Web search (third-party only, not evidence): most guides use `whitepages.com/suppression-requests` (HYPHEN), contradicting the BADBOOL underscore in our entry; guides also name privacyrequest@whitepages.com as an email fallback (not recorded, third party). FastPeopleSearch guides split between /optout and /removal, one says they lead to the same process, and says the form is not linked from the homepage; two-step email flow with captcha and ~72 hours. Suggest: keep `unverified`, note in verification_notes "2026-11-07 third-party guides mostly use the hyphen form /suppression-requests; refetch needed". Do not switch the URL until opened by a human.
- Radaris: /control/privacy re-fetched 2026-11-07, still shows the Atlas Data Privacy Corporation transfer notice (default judgment 2026-08-27 re Radaris.com, Rehold.com, Trustoria.com). Entry stays disabled; `last_verified` may be set to 2026-11-07 as the notice itself was re-confirmed.
- Result: 0 entries upgraded to verified. All of the above are partial for the reason stated (403, refused domain, or JS-only page).

### 3. PeopleSearchNow opt-out path - resolved
Fetched both 2026-11-07:
- https://www.peoplesearchnow.com/opt-out : loads. Form: name and email, captcha, emailed link valid 24 hours, then a record-details form, confirmation page and email, "allow 3 days". Fields: Subject First/Last Name*, Subject Email*, "I am" (subject or authorized agent), authorization certification checkbox; middle name optional.
- https://www.peoplesearchnow.com/do-not-sell : loads. It is the CCPA "Do Not Sell My Personal Information" notice. Section 2 says to submit the Opt-Out Form at `/opt-out` or call 888-553-5506, and mentions Global Privacy Control. So `/do-not-sell` is an information page that points to `/opt-out`; it is not a separate form.
Conclusion: the registry's `opt_out_url: https://www.peoplesearchnow.com/opt-out` is CORRECT; leave it. Optional additions: `source_urls` += `https://www.peoplesearchnow.com/do-not-sell`; add `phone: "888-553-5506"` and `alt_methods: [phone]` (phone seen on the live page); in `required_fields` consider adding nothing (full_name, email already match). Also fix the truncated `search_access_note` in the sample (ends mid-word "in the fet"); suggested ending: "...in the fetched text, so no city/state URL is recorded." Also add the note to the form block: the authorization certification checkbox and the subject/agent radio are required.

## Earlier passes (kept)

### Tool limits (second pass)
No shell and no in-place edit in either earlier pass. Nothing committed; `registry validate` and the YAML loaders were NOT run. Edited files were rewritten whole. Please run a YAML parse check and commit (Priya Shah [freemyid], explicit paths: `brokers/checklists.yaml`, `brokers/state_law_deletion_matrix.yaml`, `docs/handoff/broker-researcher.md`). Do NOT commit `docs/research/exposure_scan_patterns.yaml` (private; add it to .gitignore).

### Statute citations (brokers/state_law_deletion_matrix.yaml)
Read on official legislature sites. `evidence: statute_text` only where the text was read.
- Verified, citation correct: DE 6 Del. C. 12D-104(a)(3)/(c)(1); NH RSA 507-H:4 I(c)/III(a); NJ N.J.S.A. 56:8-166.10 a.(3) and 56:8-166.7; KY KRS 367.3615(2)(c)/(3)(a); IA 715D.3(1)(b)/(2)(a); CO C.R.S. 6-1-1306(1)(d)/(2)(a); TX Bus. & Com. 541.051(b)(3)/541.052(b); UT 13-61-201(2)/13-61-203(2); TN 47-18-3203(a)(2)(C)/(b)(1); FL 501.705(2)(c).
- Corrected: MT 30-14-2806 -> 30-14-2808(1)(c)/(4)(a); MD 14-4605 -> 14-4705(b)(4)/(e)(2); RI 6-48.1-4 -> 6-48.1-5(e)(2) and 6-48.1-6(b)(1).
- Caveats: CO, TX, UT, TN read in enacted/filed bill text, later amendments unchecked. FL 501.705 states no response deadline (45+15 stay background).
- Still background: IN (iga.in.gov heading only) and CT (cga.ct.gov certificate error). NE unchanged. Still unread: Oregon 646A.576.
- Findings: Iowa (90 days) and Utah delete rights cover only data the consumer gave the company (weak against brokers). MD, TN, DE, UT exclude publicly available information. KY 367.3615(3)(e) allows suppression for third-party data.

### Checklists (brokers/checklists.yaml)
DMAchoice upgraded to `official_page` ($8 online, $9 mail, 10-year). ChexSystems: two numbers (800-428-9623 general per CFPB listing; 800-887-7652 freeze line per search quote, not opened); stays `partial`, chexsystems.com 403. OptOutPrescreen stays `partial` (site 403; FTC page confirms 1-888-5-OPT-OUT, 5-year or permanent). TransUnion and SSA stay `partial` (403).

### Exposure scan (docs/research/exposure_scan_patterns.yaml, private)
zabasearch, anywho refused by the fetch tool. peoplesearchnow URL shapes: `/person/<first>-<last>`, `/phone-number`, `/address`, `/names`, `/a`..`/z`. publicrecordsnow: no pattern. radaris.com: Atlas transfer notice, do not scan.

### Other first-pass notes
Do Not Call: FTC FAQ read, donotcall.gov not opened. IRS has no general opt-out. CA DROP live since 2026-01-01; broker processing from 2026-08-01. A deletion right helps only in states with a law in force, only above the size threshold, and usually not for public-record data. TX, OR, VT registries are lists only. OK, LA (2027-01-01), AL (2027-05-01), VT (2028-01-01) stay `generic` until effective. IN, KY, RI effective 2026-01-01.

## CHANGE REQUESTS (orchestrator)
1. models.py `Broker`: add `search_access` (open/js_required/bot_blocked/unknown), `search_access_note`, `search_url_evidence`, `search_url_checked`, `slug_case` (the registry files already use some of these; confirm the model accepts them).
2. `.gitignore`: add `docs/research/exposure_scan_patterns.yaml`.
3. Merge `state_law_deletion_matrix.yaml` into `state_laws.yaml` (or add a loader); add a `Checklist` model and loader for `checklists.yaml`.
4. SOURCES.md: append one-line pointers for the new files and for the 2026-11-07 DROP and peoplesearchnow sources above.
5. Hand-access: a browser-based pass by a human or the automation engineer is needed for Whitepages, BeenVerified, TruePeopleSearch, FastPeopleSearch (fetch refused) to settle URLs.

## Still uncertain
Whitepages `suppression_requests` vs `suppression-requests` (guides lean hyphen); BeenVerified live opt-out path; FastPeopleSearch `/removal` vs `/optout`; Cotality portal URL; whether DROP's email verification is mandatory.

- 2026-11-08 (Morgan): ruling: publish freeze_lexisnexis on the site (verified against consumer.risk.lexisnexis.com/freeze, 2026-11-07). The web-developer picks it up next round. Optional checklist tips from Pass 4 are deferred.
