# WO-601 handoff: search specs for the exposure scan (broker-researcher, Priya Shah)

Date: 2026-11-11. Scope: the 20 enabled brokers in `brokers/registry.yaml` that have `search_url_pattern`
(radaris and advancedbackgroundchecks are disabled and were skipped).

## Result

**0 of 20 brokers get a `search:` spec.** No result page could be read without getting around a block.

- Each broker got one plain request to its own `search_url_pattern`, filled in with the fake test person
  "Jane Testperson", Springfield IL (`testperson` for familytreenow). No real names were used, nothing was retried, and nothing was worked around:
  no UA spoofing, no proxies, no archive mirrors, no stealth tooling (shared rule 5).
- 14 brokers returned **HTTP 403** with no body. 6 were **refused by the research fetch tool's own domain policy**
  (whitepages, beenverified, intelius, truepeoplesearch, fastpeoplesearch, usphonebook), so those sites were
  never reached and those results say nothing new about the sites.
- **peoplesearchnow changed from `open` to blocked.** Its home page and `/names` loaded on 2026-11-07, but
  `/person/jane-testperson` now gets 403. So it is the result pages that are blocked. The value `open` in
  `brokers/registry.sample.yaml:520` and `brokers/registry.yaml:887` is now wrong.
- No HTML was seen for any broker (all 403s came back with no body), so I am not proposing any selectors or
  `no_results_text`. Search snippets only describe fields at the text level ("age, addresses, phones,
  relatives"). They give no markup, and making up selectors would break the never-invent rule.

Caveat: a 403 to the research tool, which uses a cloud egress and its own UA, does not prove that a person in a
normal browser on a home connection is blocked. By the schema definition ("Can the public search page be
read by a plain fetch?") `bot_blocked` is still the correct value.

## Criterion-5 table

| broker | access before | access after | observed 2026-11-11 | spec added | why not |
|---|---|---|---|---|---|
| peoplesearchnow | open | bot_blocked | HTTP 403 on /person/<first>-<last> | no | result page 403; home/names were open 11-07 |
| spokeo | bot_blocked | bot_blocked | HTTP 403 | no | 403, no HTML |
| whitepages | bot_blocked | bot_blocked (unchanged) | tool refused domain | no | site not reached |
| beenverified | bot_blocked | bot_blocked (unchanged) | tool refused domain | no | site not reached |
| peoplelooker | unknown | bot_blocked | HTTP 403 | no | 403, no HTML |
| intelius | bot_blocked | bot_blocked (unchanged) | tool refused domain | no | site not reached |
| instantcheckmate | unknown | bot_blocked | HTTP 403 | no | 403, no HTML |
| truthfinder | unknown | bot_blocked | HTTP 403 | no | 403, no HTML |
| ussearch | unknown | bot_blocked | HTTP 403 | no | 403, no HTML |
| peoplefinders | unknown | bot_blocked | HTTP 403 | no | 403, no HTML |
| truepeoplesearch | bot_blocked | bot_blocked (unchanged) | tool refused domain | no | site not reached |
| fastpeoplesearch | bot_blocked | bot_blocked (unchanged) | tool refused domain | no | site not reached |
| mylife | unknown | bot_blocked | HTTP 403 | no | 403, no HTML |
| nuwber | bot_blocked | bot_blocked | HTTP 403 | no | 403, no HTML |
| thatsthem | bot_blocked | bot_blocked | HTTP 403 | no | 403, no HTML |
| usphonebook | bot_blocked | bot_blocked (unchanged) | tool refused domain | no | site not reached |
| familytreenow | bot_blocked | bot_blocked | HTTP 403 | no | 403, no HTML |
| searchpeoplefree | bot_blocked | bot_blocked | HTTP 403 | no | 403, no HTML |
| smartbackgroundchecks | unknown | bot_blocked | HTTP 403 | no | 403, no HTML |
| veripages | unknown | bot_blocked | HTTP 403 | no | 403, no HTML |

Totals: 14 x HTTP 403, 6 x tool-refused. Access changes: 9 (peoplesearchnow open->bot_blocked; peoplelooker,
instantcheckmate, truthfinder, ussearch, peoplefinders, mylife, smartbackgroundchecks, veripages unknown->bot_blocked).

## Proposed registry edits (orchestrator wires these)

There are no `search:` blocks. Only the access fields change. Set `search_url_checked: 2026-11-11` on every
broker the fetch actually reached (the 14 that returned 403). Line numbers are the current `search_access` line in
`brokers/registry.yaml`. Each note is 300 characters or fewer.

```yaml
# peoplesearchnow  (registry.yaml:887, registry.sample.yaml:520)
search_access: bot_blocked
search_access_note: 'Plain fetch of /person/<first>-<last> (fake test name) returned HTTP 403 on 2026-11-11. Home page and /names had loaded on 2026-11-07, so the block is on result pages. Not worked around. Other paths: /phone-number, /phone, /address, /names.'
search_url_checked: 2026-11-11

# spokeo (registry.yaml:88, sample:63)
search_access_note: 'Plain fetch HTTP 403 on 2026-11-07 and 2026-11-11 (fake test name, state+city URL). Not worked around. Indexed name-only and state-only pages also exist: /John-Smith/Colorado.'
search_url_checked: 2026-11-11

# peoplelooker (registry.yaml:215)
search_access: bot_blocked
search_access_note: 'Plain fetch of /people-search/<first>-<last>/ (fake test name) returned HTTP 403 on 2026-11-11. Only one indexed page seen earlier; no state or city variant seen.'
search_url_checked: 2026-11-11

# instantcheckmate (registry.yaml:309)
search_access: bot_blocked
search_access_note: 'Plain fetch of /people/<first>-<last>/<state>/<city>/ (fake test name) returned HTTP 403 on 2026-11-11. Indexed: /people/john-smith/, /people/<name>/illinois/, /people/<name>/georgia/atlanta/. Listing URL not seen.'
search_url_checked: 2026-11-11

# truthfinder (registry.yaml:340, sample has no search_access line)
search_access: bot_blocked
search_access_note: 'Plain fetch of /people-search/<first>-<last>/<state>/ (fake test name) returned HTTP 403 on 2026-11-11. No city level seen. Single-person listing URL not seen.'
search_url_checked: 2026-11-11

# ussearch (registry.yaml:367)
search_access: bot_blocked
search_access_note: 'Plain fetch of /people-search/<first>-<last>/<state>/ (fake test name) returned HTTP 403 on 2026-11-11. Also /people-search-name/<first>-<last>. PeopleConnect family.'
search_url_checked: 2026-11-11

# peoplefinders (registry.yaml:445, sample has no search_access line)
search_access: bot_blocked
search_access_note: 'Plain fetch of /name/<first>-<last>/<st>/<city> (fake test name) returned HTTP 403 on 2026-11-11. Person reports are paywalled; address pages are /address/<slug>/<id>.'
search_url_checked: 2026-11-11

# mylife (registry.yaml:581, sample has no search_access line)
search_access: bot_blocked
search_access_note: 'Plain fetch of /<first>-<last>/ (fake test name) returned HTTP 403 on 2026-11-11. Alternate state page seen: /people-search/{state}/find/{first}-{last}. No city parameter seen.'
search_url_checked: 2026-11-11

# nuwber (registry.yaml:615, sample:394)
search_access_note: 'HTTP 403 on 2026-11-07 (/search?...) and 2026-11-11 (/name/<first>-<last>/<st>/<city>, fake test name). Not worked around. Indexed: /name/john-smith, /name/john-smith/dc/washington; listings /person/<24 hex>.'
search_url_checked: 2026-11-11

# thatsthem (registry.yaml:645, sample:417): keep the existing note, add the date
search_url_checked: 2026-11-11   # /name/Jane-Testperson returned HTTP 403

# familytreenow (registry.yaml:712, sample:443): keep the existing note, add the date
search_url_checked: 2026-11-11   # /records/genealogy/testperson returned HTTP 403

# searchpeoplefree (registry.yaml:835, sample:482): keep the existing note, add the date
search_url_checked: 2026-11-11   # /find/jane-testperson returned HTTP 403

# smartbackgroundchecks (registry.yaml:936)
search_access: bot_blocked
search_access_note: 'Plain fetch of /people/<first>-<last> (fake test name) returned HTTP 403 on 2026-11-11. Listings are /people/<name>/<opaque token>. No state or city parameter seen.'
search_url_checked: 2026-11-11

# veripages (registry.yaml:1102)
search_access: bot_blocked
search_access_note: 'Plain fetch of /name/<First>/<Last>/<ST>/ (fake test name) returned HTTP 403 on 2026-11-11. Listing page is the name page; no city level.'
search_url_checked: 2026-11-11

# whitepages, beenverified, intelius, truepeoplesearch, fastpeoplesearch, usphonebook:
# no change. The research tool refused the domain, so there is no new observation and search_url_checked stays 2026-11-07.
```

## Fixture sketches (synthetic, fake people only)

I saw no site markup, so I am not sketching any per-site result page. A copy of a site's layout would be made up.
The two fixtures below are generic. They guard the behaviour that matters while specs are missing.

`tests/fixtures/search/blocked_403.html` (served with status 403). A blocked page must never be read as "not found".
```html
<!doctype html>
<html><head><title>403 Forbidden</title></head>
<body><h1>Access denied</h1><p>You do not have permission to access this page.</p></body></html>
```
Expected: listing state `NEEDS_HUMAN` (or scan item "check it yourself"), never `NOT_FOUND`, never `FOUND`.

`tests/fixtures/search/no_spec_open_page.html` (status 200, broker has `search_access: open` but `search: null`).
```html
<!doctype html>
<html><head><title>Jane Testperson - Springfield, IL</title></head>
<body><main><h1>Jane Testperson</h1><p>Age 64</p><p>Springfield, IL</p>
<a href="/person/jane-testperson/x1y2z3">View details</a></main></body></html>
```
Expected: with no `search` spec the engine must not claim `NOT_FOUND`. It should report "could not check" or hand the
check to the person, because there is no `no_results_text` to prove absence.

## How to get real specs (needs a human; not a workaround)

1. A person opens each pattern URL in their own everyday browser for the fake name and uses Save Page As (HTML only).
   That gives the real `no_results_text` and page skeleton. If that browser also shows a challenge, record it
   (`bot_blocked`, `js_required`) and stop.
2. Results-card selectors need a page that has results. The owner has agreed to tests on their own data, so the
   owner can save their own listing page. That file must stay in the private, untracked area. Before it becomes a
   fixture, replace every name, address, phone, age and relative with fake values (Jane Q Testperson, Springfield IL,
   217-555-01xx). I then derive `result_selector`, `name_selector`, `age_selector`, `location_selector`,
   `relatives_selector`, `link_selector` and `no_results_text` from the scrubbed files. qa-security adds parser tests.
3. Start with the Mississippi Tornado Alley family (peoplesearchnow, searchpeoplefree, fastpeoplesearch,
   usphonebook, smartbackgroundchecks). They are thought to share templates, so one capture may cover several. This is
   unconfirmed until the files can be compared.
