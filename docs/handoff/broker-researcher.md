# broker-researcher handoff (v0.3 prep wave, 2026-11-07)

## Tool limits (read first)
No shell and no in-place edit in either pass. So: nothing is committed, `registry validate` and the YAML loaders were NOT run, and I could not append to `registry.yaml`, `registry.sample.yaml`, `state_laws.yaml` or `SOURCES.md`. Edited files were rewritten whole. Please run a YAML parse check and commit (Priya Shah [freemyid], explicit paths: `brokers/checklists.yaml`, `brokers/state_law_deletion_matrix.yaml`, `docs/handoff/broker-researcher.md`). Do NOT commit `docs/research/exposure_scan_patterns.yaml` (private; add it to .gitignore).

## Second pass (gap closing), 2026-11-07

### 1. Statute citations (brokers/state_law_deletion_matrix.yaml)
Read on official legislature sites. `evidence: statute_text` only where the text was read.
- Verified, citation correct: DE 6 Del. C. 12D-104(a)(3)/(c)(1); NH RSA 507-H:4 I(c)/III(a); NJ N.J.S.A. 56:8-166.10 a.(3) and 56:8-166.7 (response); KY KRS 367.3615(2)(c)/(3)(a); IA 715D.3(1)(b)/(2)(a); CO C.R.S. 6-1-1306(1)(d)/(2)(a); TX Bus. & Com. 541.051(b)(3)/541.052(b); UT 13-61-201(2)/13-61-203(2); TN 47-18-3203(a)(2)(C)/(b)(1); FL 501.705(2)(c).
- Citation WAS WRONG and is corrected: MT 30-14-2806 -> 30-14-2808(1)(c)/(4)(a); MD 14-4605 -> 14-4705(b)(4)/(e)(2) (2026 Commercial Law renumbered to subtitle 14-47xx); RI 6-48.1-4 -> 6-48.1-5(e)(2) (delete) and 6-48.1-6(b)(1) (response).
- Caveats on what was read: CO, TX, UT, TN were read in the enacted or filed bill text on the legislature's site, not a current code page (CO SB21-190, TX HB 4 88R, UT SB 227 2022, TN HB1181). Later amendments not checked. FL 501.705 states no response deadline, so FL's 45 + 15 days stay background (`response_days_evidence: background`).
- Still background (official site would not give text): IN (iga.in.gov returned only a heading; 24-15-3-1 cite unconfirmed) and CT (cga.ct.gov certificate error twice; CT AG FAQ read but cites no section for delete). NE not on the list, unchanged.
- Useful findings: Iowa (90 days) and Utah delete rights are limited to data the consumer gave the company, so they are weak against brokers (now confirmed in text). Maryland, Tennessee, Delaware and Utah exclude publicly available information in the definitions (read). KY 367.3615(3)(e) allows the suppression-record route for third-party data.
- common_rules in the matrix were widened only to points actually read; version bumped to 2026.11.07.2.

### 2. Checklists (brokers/checklists.yaml)
- DMAchoice: UPGRADED to `official_page`. dmachoice.org/register.php read: $8 online (card or PayPal), $9 by mail (check or money order to ANA), both a 10-year registration. I removed the Cos Cob P.O. box (it was never confirmed; tell people to use the address on the form).
- ChexSystems phone conflict: resolved as two different numbers, not a contradiction. CFPB company listing (official, read; modified 2025-01-30) gives 800-428-9623 as the general number. ChexSystems' own freeze pages, as quoted in a search result (NOT opened by us), say 800-887-7652 is the freeze line and 800-428-9623 is for other requests. Entry stays `partial`; chexsystems.com 403 on three URLs. Recommend: show the website, show the phone numbers only with the caveat.
- OptOutPrescreen: stays `partial`. optoutprescreen.com and transunion.com/prescreen-opt-out 403. The FTC page (official, read) confirms the site, 1-888-5-OPT-OUT (1-888-567-8688), 5-year by web or phone, and permanent (start online or by phone, then sign and return the Election form).
- TransUnion: stays `partial`, 403 on /credit-freeze, /credit-freeze/place-credit-freeze, /prescreen-opt-out. Phone number 1-800-916-8800 still comes from Experian's page.
- SSA: stays `partial`, 403 on /myaccount, the FAQ and the leaflet PDF.
- I did not use mirrors, proxies or any bot-check workaround.

### 3. Exposure scan (docs/research/exposure_scan_patterns.yaml, private)
- zabasearch, anywho: the fetch tool refuses both domains and search returned no URLs from them. No pattern recorded (`not_found`).
- peoplesearchnow: opens with a plain fetch. URL shapes seen on the page: `/person/<first>-<last>`, `/phone-number`, `/address`, `/names`, `/a`..`/z`. Search form action not visible, so no city/state URL. Opt-out link on page is `/do-not-sell`; third-party guides say `/opt-out`. Check against the registry.
- publicrecordsnow: opens, but no result URL shape, no opt-out link, placeholder privacy link. May be a thin or unfinished site. No pattern recorded.
- Fixed the earlier "11 have no constructible URL" to 7 (plus 3 with none seen). Added new evidence value `seen_on_page`.
- The registry ids for these four are my guesses (I did not read the private registry).

## First-pass notes still true
- The earlier files: `brokers/checklists.yaml` (16 entries, not loaded by code), `brokers/state_law_deletion_matrix.yaml` (companion to state_laws.yaml), `docs/research/exposure_scan_patterns.yaml` (now 35 brokers).
- Do Not Call: FTC FAQ page read, donotcall.gov itself not opened. IRS: the page has no general opt-out. California DROP: live since 2026-01-01; processing from 2026-08-01, check every 45 days; free; over 600 brokers; page does not say if an email is needed, so consider relaxing `needs_email_verification: true` and the dob/street_address/email required fields in `registry.sample.yaml`.
- Realism: a deletion right helps only in states with a law in force, only when the site meets the size threshold, and usually not for public-record data. Third-party data may be suppressed rather than erased (VA, MN, KY confirmed). CA DROP is the one tool aimed at brokers. TX, OR, VT registries are lists only.
- Newer laws: OK, LA (2027-01-01), AL (2027-05-01), VT (2028-01-01) stay `generic` until effective. Indiana, Kentucky and Rhode Island took effect 2026-01-01.
- BIG FINDING: radaris.com shows only an Atlas Data Privacy Corporation transfer notice (court order). Do not scan it.

## CHANGE REQUESTS (orchestrator)
1. models.py `Broker`: add `search_access` (open/js_required/bot_blocked/unknown), `search_access_note`, `search_url_evidence` (seen_in_search/seen_on_page/background/not_found), `search_url_checked: date`. Add `slug_case` or make the slugifier per-site.
2. `.gitignore`: add `docs/research/exposure_scan_patterns.yaml`.
3. Merge `state_law_deletion_matrix.yaml` into `state_laws.yaml` (or add a loader) and fix the section-level cites in `state_laws.yaml` where it uses chapters only. Add a `Checklist` model plus loader for `checklists.yaml`.
4. SOURCES.md not updated. Sources are listed inside each new file with the access date 2026-11-07. Append a one-line pointer per file.

## Still uncertain (carried over)
Whitepages `suppression_requests` vs `suppression-requests`; BeenVerified live opt-out path; FastPeopleSearch `/removal` vs `/optout`; Cotality portal URL. The earlier re-verify findings (acxiom, liveramp, searchpeoplefree, peoplesearchnow `last_verified` bumps) are still unapplied. Still unread in statute: Indiana, Connecticut, Nebraska, the Oregon 45-day section (646A.576).
