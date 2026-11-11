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

**Part 2 below supersedes this table for usphonebook, fastpeoplesearch, smartbackgroundchecks, searchpeoplefree
and peoplesearchnow.**

## Proposed registry edits (orchestrator wires these)

There are no `search:` blocks. Only the access fields change. Set `search_url_checked: 2026-11-11` on every
broker the fetch actually reached (the 14 that returned 403). Line numbers are the current `search_access` line in
`brokers/registry.yaml`. Each note is 300 characters or fewer.

```yaml
# peoplesearchnow: SUPERSEDED by Part 2 (human-checked note)

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

# veripages (registry.yaml:1102)
search_access: bot_blocked
search_access_note: 'Plain fetch of /name/<First>/<Last>/<ST>/ (fake test name) returned HTTP 403 on 2026-11-11. Listing page is the name page; no city level.'
search_url_checked: 2026-11-11

# whitepages, beenverified, intelius, truepeoplesearch: no change. The research tool refused the domain,
# so there is no new observation and search_url_checked stays 2026-11-07.
# usphonebook, fastpeoplesearch, smartbackgroundchecks, searchpeoplefree: see Part 2.
```

## Fixture sketches (synthetic, fake people only)

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

---

# Part 2: specs from owner-saved pages (2026-11-11)

Sources, all in the owner's private data folder (`~/.local/share/freemyid-owner-test-results/`):
- **Fake-name pages** (`pages-clean/*-fakename.html`): what each site shows for "Jane Testperson, Springfield IL", saved
  in the owner's home browser.
- **Layout skeletons of real listing pages** for a family member (owner-consented), with all personal text blanked to
  `[text]` and ids and hrefs removed: `usphonebook-real-2`, `fastpeoplesearch-real-4` (results list), `fastpeoplesearch-real-5`
  (detail page), `smartbackgroundchecks-real-3` (results list), and `searchpeoplefree-real-1` (detail page, not a list).
- **One raw page** (`pages-raw/unknown-fakename-springfield.html`). Its title and canonical show it is **usphonebook**
  (`/jane-testperson/il/springfield`). It is the *server* HTML: its scripts are intact and it has no post-JS classes.

I used these files only to learn structure: tags, classes, and where each field sits. No real person's name, address, phone, age or
relative went into any file. Every fixture holds only invented people. The fixtures' labels ("Example relatives:" and so on) are
invented too, because the real labels were blanked.

Selectors use only the `engine/htmlsel.py` subset: tag, `.class`, `[attr]`, `[attr=value]`, compounds, and the descendant and `>`
combinators. Field selectors run inside each card. `select_one` returns the first match, and the card element itself is
not part of its own scope. Wherever possible, a selector uses only tags, classes and attributes that appear in **both** the fake-name page
and the real-listing skeleton.

## Summary

| broker | spec | result_selector | fixture | wire now? |
|---|---|---|---|---|
| usphonebook | yes | `div.success-wrapper-block[itemscope]` | `tests/fixtures/search/usphonebook.html` | yes (CR-C advised; CR-D improves relatives) |
| fastpeoplesearch | yes | `div.people-list > div.card` | `tests/fixtures/search/fastpeoplesearch.html` | yes (CR-C advised) |
| smartbackgroundchecks | yes | `div.card-block.w-100` | `tests/fixtures/search/smartbackgroundchecks.html` | after CR-A (city is lost otherwise) |
| searchpeoplefree | written, NOT for wiring | `ol.inline > li.toc` | `tests/fixtures/search/searchpeoplefree.html` | no: needs CR-B |
| peoplesearchnow | no | none | none | n/a: bot_blocked, human-checked |

Checked against the real-listing skeletons: the fake-name pages' cards are **real search results** (the sites'
fuzzy matches), not ads or suggestions. They have the same card structure as the family member's real cards on
usphonebook, fastpeoplesearch and smartbackgroundchecks.

No-results fixtures: **none**. Every saved page shows results, because the sites fuzzy-match other "Testperson"
people. No no-results wording was visible, so no `no_results_text` is set (see CR-C).

Search URL shapes are now confirmed from the saved-page URLs. Each was previously marked "background knowledge, UNCONFIRMED":
usphonebook `/jane-testperson/il/springfield`, fastpeoplesearch `/name/jane-testperson_springfield-il`,
smartbackgroundchecks `/people/jane-testperson`, searchpeoplefree `/find/jane-testperson` (nationwide, no location).

### search_access value: `js_required` (proposed, your call)

A human browser on a home connection loaded all four pages. A plain fetch from the research tool got HTTP 403
(smartbackgroundchecks, searchpeoplefree) or was refused by the tool (usphonebook, fastpeoplesearch). No plain fetch from a
home connection has been tried. `js_required` routes these sites through the engine's browser path, which already
detects challenge pages and stops with "check by hand". That is the closest match to what was observed, and it
works around nothing.

usphonebook is the exception. The raw server HTML contains the result cards, so a plain GET would be enough *if* the site
answers one. usphonebook sits behind Cloudflare (`/cdn-cgi/` rocket-loader in the raw page), so a challenge is possible.
If a single plain GET with the honest UA works from the owner's machine, set usphonebook to `open`.

## Proposed YAML

The indentation below matches `brokers/registry.yaml` (`- id:` at column 0, fields at 2 spaces). In
`brokers/registry.sample.yaml`, add 2 more spaces. "replace line N" means overwrite that existing key, and "insert after line N" means
add new keys there. Line numbers are taken from the files as they stood at the start of this WO.

### usphonebook: `brokers/registry.yaml` 653-685 (not in the sample)

```yaml
  search_access: js_required                    # replace line 682 (was bot_blocked); `open` if a home plain GET works
  search_access_note: 'Structure from an owner-saved page, 2026-11-11 (fake test name; URL /jane-testperson/il/springfield confirmed). Raw server HTML holds the cards. Home browser loaded it; research fetch tool refused the domain. Cloudflare-fronted. Teaser ads sit outside cards.'   # replace line 683
  search_url_checked: 2026-11-11                # replace line 685
  # insert after line 685:
  listing_url_pattern: ^/[a-z0-9-]+/[A-Za-z0-9]{20,}$
  search:
    result_selector: 'div.success-wrapper-block[itemscope]'
    name_selector: 'h3.ls_number-text > span[itemprop=name]'
    age_selector: 'h3.ls_number-text'
    location_selector: 'span[itemprop=address]'
    relatives_selector: 'a[itemprop=relatedTo] > span[itemprop=name]'
    link_selector: 'a.ls_contacts-btn'
```

Structure seen on both the fake-name page and the real-listing skeleton:
- **Card:** `div.success-wrapper-block`, carrying schema.org Person microdata (`itemscope`, `itemid` = listing URL).
- **Name and age:** in `h3.ls_number-text`, as `<span itemprop="name">` followed by the age as a bare text node
  (", Age 60"). `parse_age` reads the age from the whole h3. With no age shown, the h3 holds only the name, and
  `parse_age` returns None.
- **Current city:** the first `div.ls_success-content-extra-info`, "Lives in:" `<span itemprop="address">City, ST</span>`.
  It is the first `span[itemprop=address]` in the card, so `select_one` returns it.

Real card only (skeleton), absent from the fake-name cards:
- A second `ls_success-content-extra-info` block (label blanked, probably past places) holding several
  `span.ls_success-black-text > span[itemprop=address]`. Only the first address is read today (see CR-D).
- A third block of relatives, `a[itemprop=relatedTo][itemscope] > span[itemprop=name]` (9 on the real card). The
  name selector is anchored to the h3 so that it never picks up a relative's `span[itemprop=name]`.

Other details:
- **Link:** `a.ls_contacts-btn`. In the raw HTML its href is relative (`/<first>-<last>/<token>`), and the engine's `urljoin` handles that.
- **Decoys:** an ad slot reuses `div.success-wrapper-block` without `itemscope` and is excluded. The partner teasers
  (`div.awl-data` in `#teaserWidgets`) are also excluded.

### fastpeoplesearch: `brokers/registry.yaml` 490-528, `brokers/registry.sample.yaml` 302-330

```yaml
  search_access: js_required                    # replace registry.yaml:525 / sample:328 (was bot_blocked)
  search_access_note: 'Structure from an owner-saved page, 2026-11-11 (fake test name; URL /name/jane-testperson_springfield-il confirmed). Home browser loaded it; research fetch tool refused the domain. span.grey shows age OR city; relatives blocks have no class hooks.'   # replace registry.yaml:526 / sample:329
  search_url_checked: 2026-11-11                # replace registry.yaml:528 / sample:330
  # insert after registry.yaml:528 / sample:330:
  listing_url_pattern: ^/[a-z0-9-]+_id_G-?[0-9]+$
  search:
    result_selector: 'div.people-list > div.card'
    name_selector: 'h3.card-title span.larger'
    age_selector: 'h3.card-title span.grey'
    location_selector: 'h3.card-title span.grey'
    link_selector: 'a.link-to-details'
```

Structure seen on both the fake-name page and the real results-list skeleton:
- **Cards:** `div.people-list > div.card[data-link] > div.card-block`.
- **Name and age/city:** inside `h3.card-title > a` sit `span.larger` (the name) and `span.grey`. `span.grey` held "Age 60" on one fake-name card
  and "City, ST" on another. A card showing both was not seen. If both appear, `<br>` becomes a newline and `_split` keeps both parts.
  `parse_age` ignores a city-only value.
- **Link:** `a.link-to-details` (absolute, `/<first>-<last>_id_G<digits>`, where the G may be followed by `-`).

Real card only (skeleton): three **unclassed** `<div><h4>[label]</h4> …</div>` blocks. Two are lists of links and one is text.
The labels are blanked, and without a class or `:nth-child` there is no way to tell which one holds relatives, so no
`relatives_selector` is set.

Decoys excluded: the Ancestry block (`#ancestry-ad`) and `#teaserWidgets` both sit outside `div.people-list`.

`fastpeoplesearch-real-5` is a detail page (an h1 plus unclassed lists). It is not used by the search spec.

### smartbackgroundchecks: `brokers/registry.yaml` 915-940 (not in the sample)

```yaml
  search_access: js_required                    # replace line 936 (was unknown)
  search_access_note: 'Structure from an owner-saved page, 2026-11-11 (fake test name, /people/jane-testperson). Home browser loaded it; plain research fetch got HTTP 403. Results are card-block w-100; sponsored cards are card-block mw-100. Age and city share one span.'   # replace line 937
  search_url_checked: 2026-11-11                # replace line 939
  # insert after line 940 (listing_url_pattern already there and consistent with the saved page):
  search:
    result_selector: 'div.card-block.w-100'
    name_selector: 'a.name-list-title'
    age_selector: 'h2 > span.h2SubTitle'
    location_selector: 'h2 > span.h2SubTitle'
    link_selector: 'a.name-list-title'
```

Structure seen on both the fake-name page and the real results-list skeleton:
- **Card:** `div.card-block.card-normal.w-100 > div.p-1.w-100`.
  - The `id` seen on the fake-name cards cannot be confirmed, because the skeletons drop ids. So the selector uses `w-100`, which both files carry.
  - The sponsored WAM cards are `div.card-block.cardhoverbold.mw-100[data-wam-slot-id]`. Their `mw-100` is a different class token, so they are excluded.
- **Name and link:** `a.name-list-title`, inside the `h2`, with href `/people/<first>-<last>/<token>`.
- **Age and city:** `span.h2SubTitle`, also inside the `h2`, reading "Age 60 - City, ST" (or "Age  Unknown - City, ST").

Real card only (skeleton): two `div.h2SubTitle` blocks. One is text. The other is a list of `span > a.link-underline`,
probably relatives or places, but the label was blanked so I can't tell which. No `relatives_selector` is set. The age and
location selectors are anchored to `h2 >` so they never read these divs.

The WAM decoys show *other* real people's full names, towns and ages, and are excluded.

**Wire after CR-A.** Today `location_selector` yields "Age 60 - City, ST" as one string, and `parse_location` turns it
into city "age 60 city", which never equals the person's city. A real listing showing "Age Unknown" would therefore score
NO_MATCH, which means a false "not found".

### searchpeoplefree: `brokers/registry.yaml` 790-839, `brokers/registry.sample.yaml` 446-484

```yaml
  search_access: js_required                    # replace registry.yaml:835 / sample:482 (was bot_blocked)
  search_access_note: 'Structure from an owner-saved page, 2026-11-11 (/find/jane-testperson, nationwide). Home browser loaded it; plain research fetch got HTTP 403. Name is a bare text node beside location and aka spans; no spec wired until the parser can isolate it.'   # replace registry.yaml:836 / sample:483
  search_url_checked: 2026-11-11                # replace registry.yaml:838 / sample:484
  # DO NOT insert yet. Proposed spec, valid only after CR-B:
  # search:
  #   result_selector: 'ol.inline > li.toc'
  #   name_selector: 'h2 > a'                   # needs own-text (CR-B)
  #   age_selector: 'h3'
  #   location_selector: 'h2 > a > span'        # "in City, ST": needs the leading "in " stripped (CR-B)
  #   relatives_selector: 'article > a'         # first relative only until CR-D
  #   link_selector: 'a.btn-continue'
```

Structure, from the fake-name page only:
- **Card:** `ol.inline > li.toc.l-i > article`.
- **Name block:** `h2 > a` contains the name as a bare text node, then `<span>in City, ST</span>`, then optionally
  `<span><b class="text-aka">also</b> Other Name</span>`.
- **Age:** `h3` holds "Age <span>NN <i>(YYYY or YYYY)</i></span>".
- **Relatives and link:** relative links are `article > a`, and the details link is `a.btn-continue`.

`searchpeoplefree-real-1` is a **detail page** (a `div.toc > dl` section menu plus `div.toc > article`), not a results list.
It adds nothing for the list spec. It does show that `.toc` also appears on detail pages, which is one more reason to anchor on
`ol.inline > li.toc`.

Why not wire: `h2 > a` reads "John Example in Peoria, IL also …". `token_sort_ratio` against the person's name then falls
far below 88, so every card, including the person's own, would be NO_MATCH, which means a false "not found".

A decoy must stay excluded: the sponsored slots are `div.toc.l-i.l-ip`, and their links stay on searchpeoplefree.com
(`/results/widgetsponsor?…`). They would pass the SEC-89 on-broker check if the selector were loosened to `.toc`.

The page header said "Showing 7 People", but the list held only 2 `li` cards. The rest are possibly on a later page. This is not confirmed.

### peoplesearchnow: `brokers/registry.yaml` 840-891, `brokers/registry.sample.yaml` 485-522

```yaml
  search_access: bot_blocked                    # replace registry.yaml:887 / sample:520 (was open)
  search_access_note: 'Human-checked 2026-11-11: the owner could not reach the site at all from a normal home browser. A plain research fetch of /person/<first>-<last> (fake test name) also got HTTP 403. Not worked around. No spec.'   # replace registry.yaml:888-889 / sample:521
  search_url_checked: 2026-11-11                # replace registry.yaml:891 / sample:522
```

## JS-rendering notes

- The `pages-clean` fake-name files are the browser's DOM *after* scripts ran (usphonebook's `<html>` carries
  `fontawesome-i2svg-active`, and its icons were turned into inline SVG). The raw usphonebook page, however, is the
  server response, and **it already contains both result cards**. So usphonebook results are server-rendered.
- For fastpeoplesearch, smartbackgroundchecks and searchpeoplefree, the cards carry server ids and no script hooks, so they
  look server-rendered. With no raw copies, this is not proven.
- Script-filled parts, all of which the specs exclude anyway: usphonebook `#teaserWidgets`, smartbackgroundchecks
  `#wam_placeholder` (`SbcWamProMax`), searchpeoplefree `#slots_c` (with a `#loading_widgets` loader).
  fastpeoplesearch's `#teaserWidgets` was empty.
- No cards appeared to be missing, apart from searchpeoplefree's count (7 claimed, 2 shown).

## Change requests (owner: engine / orchestrator; I did not edit src/)

- **CR-A** `src/freemyid/engine/exposure.py` `_split`: also split on `\s+-\s+`, i.e. `re.split(r"[\n;|]+|\s+-\s+", t)`.
  Then smartbackgroundchecks "Age 64 - Springfield, IL" gives the locations ["Age 64", "Springfield, IL"], and the city
  signal works. Fixture: in `smartbackgroundchecks.html`, Jane Q Testperson (Springfield IL, 64) should get city plus age.
- **CR-B** For searchpeoplefree:
  - (1) a way to read only an element's own text nodes. Options: `htmlsel.Node.own_text()` plus an optional
    `SearchSpec.name_own_text: bool`, which is a models.py and schema change.
  - (2) `matcher.parse_location` drops a leading "in " or "Lives in:".
  - Until both land, searchpeoplefree stays at "check by hand".
- **CR-C** `exposure._read`: when the spec has no `no_results_text` and zero cards parse, raise
  `FetchFailed("page_unrecognized")` instead of returning [] (which means "not found"). Without this, a layout change at any
  of the wired sites would silently report "not found". The alternative, capturing a no-results page per site, is hard
  because the sites fuzzy-match other "Testperson" people.
- **CR-D** `exposure.parse_candidates`: for `relatives_selector`, and ideally `location_selector`, read *all*
  matches in the card with `el.select(sel)`, joined by "\n", instead of `select_one`. The usphonebook real card lists about 9
  relatives and several past places as separate elements, and today only the first of each is used. Fixture:
  `usphonebook.html`, where the Jane card has 2 relatives and 2 past places.

## Privacy note on the owner's files

The "clean" fake-name pages still contain real third parties:
- smartbackgroundchecks: sponsored widgets with full names, towns and ages of unrelated people.
- searchpeoplefree: an aka full name and a relative's name.
- all four: real "<First> Testperson" fuzzy matches with their cities and ages.
- `pages-raw/unknown-fakename-springfield.html`: the same, unredacted.

None of it was copied anywhere. Keep these files private and untracked, and delete them once the specs are wired.
