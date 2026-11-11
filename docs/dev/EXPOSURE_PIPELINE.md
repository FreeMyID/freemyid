# The exposure scan pipeline

This guide follows the reviewed source snapshot in this worktree. Start with
[Architecture](ARCHITECTURE.md) for the wider module map. The entry point is
`scan_exposure`; it loads a profile, checks consent, prepares fetchers, walks the
eligible brokers, computes a score and saves the result
(`src/freemyid/engine/exposure.py:559-624`).

## Call order

The following diagram expands the calls made by the entry point and its helpers
(`src/freemyid/engine/exposure.py:585-624,627-694,428-452,468-509`):

    scan_exposure
      -> get_profile -> consent_ok -> registry / fetcher setup
      -> scan_brokers
         -> _scan_broker
            -> _main_urls -> offline/cache/search_access checks -> polite gap
            -> _check_one
               -> _read -> fetch -> challenge/status/parser checks
                        -> parse_candidates -> matcher.score_all or score_lookup
               -> optional old-address / previous-name / other-value pages
               -> merge_listings -> possible-match review -> _fill
            -> exposure_check event (for the fetched/error path)
      -> score_entries -> ExposureResult + drivers -> _save -> return

## Profile and variants

A missing profile or unsuccessful consent check raises `ExposureRefused` before
fetcher setup or the broker loop (`src/freemyid/engine/exposure.py:585-600`).
For a name search, `search_url` uses the current name and an explicitly supplied
address or the current address; it fills the registry pattern with encoded slugs
and accepts only an on-broker URL (`src/freemyid/submitters/web_form.py:67-75,93-123`).

Search expansion and matching expansion are separate. When enabled, the reviewed
scan adds at most one distinct earlier-address URL and one distinct previous-name
URL per broker; the address helper chooses the most recent usable earlier address,
and the name helper chooses the first usable previous name
(`src/freemyid/engine/exposure.py:520-556,559-583,673-677`).
The matcher independently compares combinations of current/previous given names,
profile nicknames, common nickname groups and surnames
(`src/freemyid/engine/matcher.py:127-143,151-167`).
Phone/email-only profiles use value-search URLs instead of the name-search URL
(`src/freemyid/engine/exposure.py:414-420`).

## Broker eligibility and the tier boundary

`scan_brokers` selects enabled brokers with a suitable search pattern, ordered by
descending priority and then broker ID. Value-only profiles use the corresponding
lookup pattern (`src/freemyid/engine/exposure.py:396-406`).

The exposure loop uses `search_access`: `open` selects the HTTP fetcher,
`js_required` selects the browser fetcher, and `bot_blocked` or `unknown` becomes
a hand-check outcome. Missing fetcher support also becomes a hand check
(`src/freemyid/engine/exposure.py:656-663`).
The delivery decision function `tier_for` is a separate interface; it is not a
step in this exposure call chain. Its automatic/email/assisted decisions live in
the delivery module (`src/freemyid/engine/tiers.py:129-142`;
`src/freemyid/engine/exposure.py:607-624,627-694`).

## Search and parsing

The HTTP fetcher enforces a total deadline, redirect checks and bounded decoded
body collection, translating timeout/HTTP failures to `FetchFailed` reasons
(`src/freemyid/engine/exposure.py:204-264`).
The browser fetcher starts lazily, checks the broker URL, maps challenge and policy
failures, reads the page, and closes its per-broker context
(`src/freemyid/engine/exposure.py:269-319`).

`_read` checks for a challenge and failing HTTP status before interpreting the
registry parser. An explicit no-results marker yields an empty result; an
unsupported selector, missing parser, or unrecognized page yields a reason for
hand checking (`src/freemyid/engine/exposure.py:428-452`).
`parse_candidates` reads the declared selectors with `htmlsel`, caps the number
of results and extracted field lengths, and rejects result links outside the
broker's HTTPS URLs (`src/freemyid/engine/exposure.py:332-362`).

## Rate limits, cache and back-off

The reviewed implementation spaces fetched pages with a random configured gap,
except in fixture/fast mode, and reuses eligible recent successful answers for
24 hours unless refresh is requested
(`src/freemyid/engine/exposure.py:79,601-603,650-655,665-677`).
The same gap callback runs before extra variant pages
(`src/freemyid/engine/exposure.py:483-490`).

There is no HTTP 429/503 retry/back-off loop in this reviewed path. Challenge
classification runs first; remaining statuses of 400 or greater become
`http_error`, which the broker wrapper turns into a hand-check result. This guide
does not claim a future retry policy is implemented
(`src/freemyid/engine/exposure.py:428-448,675-686`).

## Matching and merging

Name-based results pass through `score_all`; value-only results use `score_lookup`
(`src/freemyid/engine/exposure.py:449-452`).
The name matcher requires a sufficient name score, adds supporting signals, and
applies household/age/name safety caps before returning a level and score
(`src/freemyid/engine/matcher.py:207-257`).

Extra-page results are combined by URL before one `merge_listings` call. If an
extra page could not be read, `keep_unchecked` preserves the uncertain earlier
answer; possible-only results create a review task
(`src/freemyid/engine/exposure.py:480-509`).
A failed broker becomes a hand-check entry; previously stored live listings can
still supply a `found` entry marked `from_store`
(`src/freemyid/engine/exposure.py:636-644,675-694`).

## Scoring, coverage and saving

After the broker loop, `score_entries` supplies the numeric score and explanation,
and `drivers` supplies the largest contributors. The result is then saved and
returned (`src/freemyid/engine/exposure.py:618-624`).
Confirmed and possible listings add exposure points; explanation lines include
a cap adjustment when the total exceeds 100, and the returned number is bounded
at 0–100 (`src/freemyid/engine/exposure_score.py:109-153`).

Coverage is computed from result entries, not the score: it counts automatically
checked, confirmed, uncertain, not-found and hand-check sites, with stored-only
answers excluded from `sites_checked`. The coverage note explains the checked
share and any uncertainty/hand-check work
(`src/freemyid/exposure_models.py:70-114,157-163`).
`_save` writes a scan event using listing IDs and result metadata rather than
copying listing/check URLs into the event
(`src/freemyid/engine/exposure.py:703-731`).

## Where to add a new broker search adapter

For an existing supported search shape, provide the broker's search pattern,
access declaration and selectors through the registry's existing `Broker` and
`SearchSpec` fields (`src/freemyid/models.py:414-449,494-501`).
The implementation points are `src/freemyid/submitters/web_form.py` for URL
construction, `src/freemyid/engine/exposure.py` for transport/dispatch/parsing,
and `src/freemyid/engine/htmlsel.py` for the supported static selector subset
(`src/freemyid/submitters/web_form.py:98-123`;
`src/freemyid/engine/exposure.py:204-319,332-362,656-663`).

Use injected `fetch`/`browser_fetch` functions to test a new supported shape
without a live broker request. Those injection points belong to `scan_exposure`
(`src/freemyid/engine/exposure.py:559-574`).

## What this guide does not cover

This is a map of the reviewed source, not a claim that queued work orders have
shipped. It does not define a new adapter interface, retry policy, delivery tier,
storage format, security policy or UI. Consult the cited implementation before
changing any of those boundaries.
