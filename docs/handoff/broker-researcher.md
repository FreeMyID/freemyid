# broker-researcher handoff (v0.3 prep wave, 2026-11-07)

## Tool limits this run (read first)
No shell and no in-place edit. So: nothing is committed, `registry validate` and the YAML loaders were NOT run, and I could not append to `registry.yaml`, `registry.sample.yaml`, `state_laws.yaml` or `SOURCES.md`. New data went into new files instead. Please run the checks and commit (Priya Shah [freemyid], explicit paths).

## Files written
- `brokers/checklists.yaml` (public). 16 entries: Equifax, Experian, TransUnion, Innovis, ChexSystems, NCTUE, LexisNexis freezes, OptOutPrescreen, DMAchoice, Do Not Call, IRS IP PIN, SSA, USPS Informed Delivery, Google Results about you, California DROP. Each has url, cost, time_needed, need_on_hand, steps, how_to_undo, source_urls, date_checked, verification (`official_page` or `partial`), notes. Not loaded by any code. Needs a quick YAML parse check.
- `brokers/state_law_deletion_matrix.yaml` (public, companion to state_laws.yaml). In-force deletion rights by state, response windows, verification rules, appeal rules, the public-records caveat.
- `docs/research/exposure_scan_patterns.yaml` (PRIVATE, not covered by .gitignore, add it before any commit). Search and listing patterns for 31 brokers.

## Checklist facts that are NOT confirmed (do not ship the wording as certain)
- TransUnion (403), ChexSystems (403), OptOutPrescreen (403), SSA my account (403): official page not read. Facts come from search summaries of FTC, Experian, Norton, SSA leaflet/blog pages. ChexSystems phone numbers conflict (1-800-887-7652 vs 1-800-428-9623): publish none until read on the official page.
- DMAchoice fee: $8 online, $9 by mail for 10 years per search results; older pages show lower. Confirm on site.
- Do Not Call: FTC FAQ page read, donotcall.gov itself not opened.
- IRS: the page has no general opt-out; how_to_undo says so.
- California DROP, current status: live since 2026-01-01; brokers had to start processing 2026-08-01 and check at least every 45 days; page says all brokers should finish their first cycle by Nov 2026; status updates up to 90 days; free; over 600 brokers. Page does not say if an email is needed or how to cancel. No dated compliance report found. Note `registry.sample.yaml` ca_drop has `needs_email_verification: true` and `required_fields` including dob, street_address and email. The page does not confirm those; consider relaxing.

## State laws (task 3)
- Statute text actually read: Virginia 59.1-577 (45+45 days, may decline if cannot verify, appeal 60 days), Minnesota 325M.14 (45+45, verify by commercially reasonable efforts, opt-outs need no verification, appeal 45+60), Oregon 646A.574(1)(c) (delete right reaches data from other sources; the 45-day rule is in 646A.576, not read), California via the AG page.
- Colorado, Connecticut and Texas statute pages failed to fetch (403, certificate error, empty). Everything else is `evidence: background`.
- Section-level citations in the matrix for MT, DE, NH, NJ, TN, MD, IN, KY, RI, FL, UT, IA are from memory and may be wrong. They are NOT in the existing state_laws.yaml, which cites chapters only. Do not copy them into a letter until checked.
- Realism: a deletion right helps only in states with a law in force, only when the site meets the size threshold, and usually not for public-record data (most laws exclude "publicly available information", background). Third-party data may lawfully be suppressed instead of erased (VA and MN confirmed). CA DROP is the one tool aimed at brokers. TX, OR, VT registries are lists only.
- Newer laws: OK, LA (2027-01-01), AL (2027-05-01), VT (2028-01-01) stay `generic` until effective. Indiana, Kentucky and Rhode Island took effect 2026-01-01 and are already `state_privacy`.

## Exposure scan (task 1)
- Most people-search pages return 403 or are refused by the fetch and search tools. URL shapes are from indexed search-result URLs (fake query John Smith, Springfield IL). Confirmed from search: Spokeo, ThatsThem, Nuwber, MyLife, PeopleFinders, InstantCheckmate, TruthFinder, PeopleLooker, FamilyTreeNow, SearchPeopleFree, ClustrMaps, PeekYou, SmartBackgroundChecks, AdvancedBackgroundChecks, CocoFinder, VeriPages, USSearch, 411. From background only, unconfirmed: Whitepages, TruePeopleSearch, FastPeopleSearch, BeenVerified, Intelius, USPhonebook.
- Whether JS is needed in a real browser was not observed, so it is `unknown`. Plain-fetch access is recorded as `bot_blocked`, `unknown` or `open`.
- BIG FINDING: radaris.com now shows only an Atlas Data Privacy Corporation transfer notice (court order). No search, no listings. Do not scan it.
- The file says "11 have no constructible name URL". The real count is 7 (radaris, addresses_com, neighborwho, locatefamily, peoplebyname, peoplewhiz, publicdatadigger). Fix on commit.
- Short of 40: 31 done. Zabasearch and AnyWho are refused by the search tool; the quota ran out for peoplesearchnow and publicrecordsnow. I did not read the private registry, so the ids are my guesses from the sample and task list. Map them to real ids.
- Nothing mirrored into `registry.sample.yaml`. Only Spokeo is in the sample and its `listing_url_pattern` is already there. Optional: add its `search_url_pattern` `https://www.spokeo.com/{first}-{last}/{state_name}/{city}`, but check that the engine keeps the capitalised slug.

## CHANGE REQUESTS (orchestrator)
1. models.py `Broker`: add `search_access` (enum open/js_required/bot_blocked/unknown), `search_access_note`, `search_url_evidence`, `search_url_checked: date`. Add `slug_case` or make the slugifier per-site.
2. `.gitignore`: add `docs/research/exposure_scan_patterns.yaml`.
3. Merge `state_law_deletion_matrix.yaml` into `state_laws.yaml` (or add a loader), and add a `Checklist` model plus loader for `checklists.yaml`.
4. SOURCES.md was not updated. Sources are listed inside each new file with the access date 2026-11-07. Append a one-line pointer per file.

## Still uncertain (carried over)
Whitepages `suppression_requests` vs `suppression-requests`; BeenVerified live opt-out path; FastPeopleSearch `/removal` vs `/optout`; Cotality portal URL. The earlier re-verify findings (acxiom, liveramp, searchpeoplefree, peoplesearchnow `last_verified` bumps) are still unapplied.
