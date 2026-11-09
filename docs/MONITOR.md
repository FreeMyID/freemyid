# Broker monitor (BL-IN-06)

`freemyid monitor` checks each enabled broker that has a web opt-out page: does the page
still load, and do the registry's form selectors still match? It is meant for maintainers
and for the weekly GitHub Actions job (Dana's job spec in docs/handoff/automation-engineer.md),
not for people's own computers. It needs no profile and reads no personal data.

Code: `src/freemyid/monitor.py`. `tools/registry_health.py --online` uses the same fetch,
redirect, allowlist and selector checks.

## What it never does

- It never fills in, clicks or submits anything. It loads one page per broker: the page named
  by the registry's `goto` step if there is one, otherwise the opt-out page. The other form
  steps only give their selector.
- Limitation: when a broker has a `goto` step, only the `goto` page is checked. The registry's
  `opt_out_url` itself is not loaded, so a broken opt-out page can still report `ok` if the
  `goto` page is fine. `tools/registry_health.py` checks each `opt_out_url` separately.
- It never works around bot protection. A challenge or CAPTCHA page, or HTTP 403/429/503, is
  `blocked` (check by hand). Nothing is retried.
- It never leaves the allowlist. Every hop, redirects included, must be https and pass
  `NetPolicy`. An off-list hop is reported and never fetched.
- It never stores page text. The report holds broker ids, health, HTTP status, the registry's
  own selectors, `scheme://host/path` (no query string) and a hash.

## Checks

One GET per page (2 MB cap), at most 5 redirects, a random 2-5 s gap between requests
(1 s minimum; the headless browser load waits its turn too), and a 30 s budget per broker,
checked before each request. A single page body that takes longer than 30 s to read is cut
off and reported `unreachable` (`request failed: TimeoutError`), never checked half-read. With `--browser`, a form built by JavaScript
(no form fields in the HTML) is loaded once in the headless browser (the goto runs through
BrowserManager, with NetPolicy routing and challenge detection) and the rendered HTML is
checked the same way.

| health | meaning |
|---|---|
| `ok` | loads, the simple selectors match, and the form is the same as last week |
| `moved` | the page now ends at another host or path (a trailing slash doesn't count) |
| `form_changed` | a registry selector is missing, or the fingerprint changed since last week |
| `blocked` | challenge page or 403/429/503: check by hand |
| `unreachable` | network error, HTTP 4xx/5xx, not https, off the allowlist, too many redirects |
| `unknown` | the form is built by JavaScript and `--browser` was not used, or the check failed |

Simple selectors (`#id`, `[name=x]`, `tag[name=x]`) are checked. Others are counted in
`selectors_unchecked`. The **fingerprint** is a sha256 (16 hex characters) of the registry
selectors that matched plus each form field's tag, type and name. Hidden fields are left
out because their tokens change on every load. Labels, values and other text are never
included.

## Week over week

`--previous last.json` (last week's monitor/1 output) fills `previous_health`, `changed`
(health differs), `first_seen_bad` and `weeks_bad`. A fingerprint change on an otherwise
`ok` page becomes `form_changed`. When the same bad health shows two weeks in a row, the
monitor sets `demote_suggested`. Priya then moves the broker off `verified` (Automatic) to
Assisted with a normal registry edit. The monitor and CI never write the registry. A
`--previous` file that isn't monitor/1 is ignored, with a warning on stderr.
