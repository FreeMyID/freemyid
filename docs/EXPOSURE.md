# Exposure scan ("find me first")

ROADMAP 3.2, v0.3. Shows which people-search sites have a listing for a person, before any
removal is sent, and gives a 0-100 exposure score with plain-English reasons.

Code: `src/freemyid/engine/exposure.py` (scan, score, storage), `src/freemyid/exposure_models.py`
(result models), `src/freemyid/engine/htmlsel.py` (static HTML reading).
CLI: `freemyid exposure [--profile P] [--json] [--offline] [--refresh] [--headless]`.
Dashboard hook: `exposure.latest_exposure(store, profile) -> ExposureResult | None` and
`exposure.exposure_history(store, profile_id) -> [(when, score)]` for a trend line.

## What it checks

Every enabled broker with a `search_url_pattern`, highest priority first, at most once per
run and at most once a day (results from the last 24 hours are reused; `--refresh` skips the
cache). The search URL comes from the person's first and last name and current city/state.
`Broker.slug_case` sets how names are written in the URL (`lower` = `jane-testperson`,
`title` = `Jane-Testperson`, `as_is`).

| `search_access` | What happens |
|---|---|
| `open` | One plain HTTPS GET. User-Agent `FreeMyID/<version> (+https://freemyid.org/safety/)`, no cookies, at most 2 redirects, every hop has to stay on the broker's domains and pass NetPolicy. Pages over 2 MB are refused. |
| `js_required` | One headless page load through BrowserManager (NetPolicy routing, challenge detection, no retries). If there's no browser, "check by hand". |
| `bot_blocked`, `unknown` | Not fetched. "Check by hand", with the link to open. |

When a site has to be fetched, there's a polite random gap between sites
(`config.min_delay_s..max_delay_s`). A challenge or CAPTCHA page, an HTTP error, a changed
page, a selector the reader can't run, or any other failure makes that one site
"check by hand". Nothing is retried, and one site's failure never stops the scan. Free My ID
never works around bot protection.

The results page is read with the registry's `Broker.search` selectors. No scripts run:
`htmlsel` supports tag, `.class`, `#id`, `[attr]`, `[attr=value]`, descendant and child.
The results are scored by the existing matcher:

- **confirmed**: name plus at least 2 signals
- **possible**: name plus 1 signal
- **no match**: dropped

Signals are city/state, age within 2 years, relative, phone and email.

When a checked site has possible matches and no confirmed match, the scan immediately
adds an “Is this you?” review to-do to the dashboard, using the same review process as
`scan`. An open review for that site is reused on later scans. Confirmed matches and
sites that need to be checked by hand create no new review to-do.

### Old addresses (optional, off by default)

Set `exposure_old_addresses: true` in config.yaml (or pass `old_addresses=True` to
`scan_exposure`) to also search ONE previous address per broker. Only brokers whose
`search_url_pattern` uses `{city}`, `{state}` or `{state_name}` get the extra search. The
address used is the most recent one not marked current (highest `to_year`, then `from_year`,
then list order) that gives a different URL from the current-address search; a broker whose
URL only uses `{state}` gets no extra request when you moved within the same state.

Same rules as the main search: the same fetcher and `search_access`, the polite random gap
before the request, consent and practice mode, the 24-hour cache (a cached site gets no
extra request either). The extra search only runs when the main search was read; a failed
old-address page is ignored and the main answer stands. Both pages' listings are saved in one
merge, so neither marks the other's listings gone. `old_address_checked` on the entry says
whether the extra page was read. The matcher already counts any current or previous address
as the location signal.

`--offline` fetches nothing. It lists every site as "check by hand", with its link, and counts
what earlier scans and runs already found.

Practice mode and consent work exactly as they do for `scan`. The exposure scan only reads,
so it also runs in practice mode. People without valid permission are skipped.

## What is stored

- Matched listings go into the encrypted listings table, the same record that `scan` keeps
  (`runner.merge_listings`). The user's earlier "yes, that's me" or "no" answers are kept.
  Listings a clean re-check no longer shows are marked gone.
- One audit event per scan (`action = "exposure_scan"`, encrypted like every event) holds
  only PII-free data:
  - the score and the explanation lines
  - for each site: broker id, status, reason code, match level, signal names, and the time
    it was checked
  - for each listing: listing id, level, signal names, "contact shown" yes/no, and how many
    relatives are named.
- One `exposure_check` event per site that was looked at, with its status, reason, level and
  number of listings.
- No HTML is kept. Names, ages and addresses from the pages never go into the scan record.
  Listing URLs are kept only in the listings table, and "check by hand" links are rebuilt
  from the profile when the record is read.

## Coverage

A score is always shown with its coverage (ROADMAP 3.2). `ExposureResult.coverage`:

| Field | Meaning |
|---|---|
| `sites_total` | Sites with a search page we know about |
| `sites_checked` | Read automatically, in this scan or from the 24-hour cache |
| `found` | Shows a confirmed listing of you (also counts what earlier runs found when the site could not be read now) |
| `uncertain` | Shows only "possible" listings: needs an "Is this you?" answer |
| `not_found` | Read, and shows nothing that matches |
| `check_by_hand` | Not read and nothing known: open the link yourself |

`found + uncertain + not_found + check_by_hand == sites_total`. `ExposureResult.coverage_note`
is one plain-English line for the UI, for example "This score is based on the 12 sites we
could check, out of 40. A low score does not mean you are safe. 28 sites need checking by
hand." It never says "you are safe". Coverage is worked out from the entries, so older stored
scans get it too.

## California: DROP first

When the person's current address is in California (`checklist_state.drop_first(profile)`,
which uses `Profile.state_of_residence`), `ExposureResult.drop_first` is true and
`first_checklist` is `"ca_drop"`. The CLI prints `exposure_models.DROP_NOTE` under the score,
and `freemyid checklist list` shows `ca_drop` first. Everyone else: false / null. This is
worked out from the profile when the result is read, so it follows a move.

## Exposure score (0-100)

| What | Points |
|---|---|
| Each site that shows a **confirmed** listing of you | 15 |
| Each extra confirmed listing on the same site (up to 2 per site) | 5 |
| Each of those sites that shows your phone number or street address | 5 |
| Each relative or associate named on your confirmed listings | 2 (10 at most) |
| Each site with only a **possible** listing (needs your review) | 5 |
| Sites that had to be checked by hand | 0 (listed, not counted) |

The total stops at 100. Every part of the score comes with a line of explanation, for example:

```
+15  1 site shows a listing that is you (15 points each)
 +2  1 relative or associate is named next to you (2 points each, up to 10)
      1 site could not be checked automatically; open it yourself (not counted)
```

Why this formula: it's simple to explain to the person and it can't be gamed by a single
site. A confirmed listing is what matters most. Contact details and family members make a
listing more harmful. "Possible" listings count a little, until the person looks at them.
If the weights change, change `score_entries` and this table together.

## Check-by-hand reasons (`reason`)

`bot_blocked`, `unknown_access`, `needs_browser`, `challenge`, `http_error`, `network`,
`blocked_by_policy`, `page_unrecognized`, `no_parser`, `offline`, `too_large`, `too_slow`,
`missing_details`. `too_large`: more than 2 MB after decompression, counted while streaming
so a gzip/deflate bomb stops early (SEC-93d). `too_slow`: the 30-second total budget for
one fetch ran out, or a read timed out (SEC-92). The plain-English text for each is in `exposure_models.HAND_REASONS`.

## Search engines (Google, Bing): guided, never scraped

Google and Bing are never searched by Free My ID. Their terms forbid automated queries, and
they would be blocked anyway. `engine/search_engines.py` is a guided step built on the
identity-safety checklists (`brokers/checklists.yaml`, read with `checklists.load`):

- `STEPS`: `google_results_about_you` (Google "Results about you") and
  `bing_content_removal` (Bing's content removal form), in that order. An entry missing from
  the checklist file is skipped. An entry whose URL is not https on that engine's own hosts
  is never shown or opened.
- `open_step(store, pid, id)` opens the official page in the user's browser and logs a USER
  Event `search_step_opened`. `mark_done` is the normal checklist tick
  (`checklist_state.set_done`), so the Protect page and `freemyid checklist` show it too.
  Both events use broker_id `_checklist` and carry only {"checklist": id}.
- Status: `not_started`, `opened`, `done`, or `do_again`. `do_again` applies to Bing only,
  when a broker status turned `removed` after the last tick, because Bing can keep showing
  the old copy of a removed page. Google's tool keeps watching by itself.
- `doc(...)` returns the `search_engines/1` JSON document, with the plain-words `INTRO`.

These steps are not part of the exposure score: nothing is measured, so nothing is scored.

## Exit codes

The same as for `scan` (docs/CLI.md):

| Exit | When |
|---|---|
| 4 | Nobody is set up, or the encryption key is unavailable |
| 3 | Nobody has valid permission |
| 0 | Otherwise, including when some sites have to be checked by hand |
