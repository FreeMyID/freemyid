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
(health differs), `first_seen_bad` and `weeks_bad`, and lists `new_brokers` and
`removed_brokers` (`monitor.py:371-383`). A fingerprint change on an otherwise
`ok` page becomes `form_changed`. When the same bad health shows two weeks in a row, the
monitor sets `demote_suggested`. Priya then moves the broker off `verified` (Automatic) to
Assisted with a normal registry edit. The monitor and CI never write the registry. A
`--previous` file that isn't monitor/1, can't be read, isn't valid JSON or is larger than
2 MB (`MAX_PREVIOUS`, `monitor.py:45`; only the first 2 MB + 1 byte is ever read) is not
compared. The run goes on and stderr says
`freemyid: --previous is not a monitor/1 file; not compared (<reason>)`
(`monitor.py:386-403`, `cli.py:1076-1080`).

## Output: `monitor/1`

`freemyid monitor --json` writes one JSON object (`cli.py:1091-1093`), built in
`run_monitor` (`monitor.py:358-368`). Top-level fields, all always present:

| field | type | meaning |
|---|---|---|
| `schema` | string | always `"monitor/1"` |
| `generated_at` | string | UTC time of the run, ISO 8601 to the second |
| `previous_generated_at` | string or null | `generated_at` of the `--previous` file; null when nothing was compared |
| `counts` | object | number of brokers per health value; all six keys, always in table order above |
| `changed` | list of ids | brokers whose health differs from last week |
| `demote_suggested` | list of ids | brokers bad for 2+ weeks in a row |
| `new_brokers` | list of ids | checked now, not in last week's file (sorted). Empty without a usable `--previous` |
| `removed_brokers` | list of ids | in last week's file, not checked now: removed, disabled or lost their web page (sorted). With `--broker`, only those ids count. Empty without a usable `--previous` |
| `brokers` | list | one object per broker checked, in registry order |

Each `brokers[]` object is `BrokerHealth` (`monitor.py:197-212`), all fields always present:

| field | type | meaning |
|---|---|---|
| `broker_id` | string | registry id |
| `health` | string | one of the six values above |
| `detail` | string | plain-text reason, no page content; empty when `ok` |
| `http_status` | int or null | status of the last hop; null when nothing was fetched |
| `page` | string | `scheme://host/path` of the page checked, no query |
| `selectors_missing` | list of strings | registry selectors not found |
| `selectors_unchecked` | int | selectors too complex to check without a browser |
| `fingerprint` | string or null | 16 hex characters; null when the form wasn't read |
| `used_browser` | bool | the headless browser loaded the page (`--browser`) |
| `previous_health` | string or null | last week's health; null when the broker is new or nothing was compared |
| `changed` | bool | `health` differs from `previous_health` (false for a new broker) |
| `first_seen_bad` | string or null | date (YYYY-MM-DD) the current bad health started; null when not bad |
| `weeks_bad` | int | weeks in a row with the same bad health; 0 when not bad |
| `demote_suggested` | bool | `weeks_bad` is 2 or more |

`new_brokers` and `removed_brokers` were added after the first release of `monitor/1`. The
change is additive only (no field removed, renamed or retyped), so the schema name stays
`monitor/1`. Readers should ignore fields they don't know.

## Exit codes

| code | when |
|---|---|
| 0 | the run finished, whatever the health values are (the CI job reads the file). A bad `--previous` file is a warning, not an error |
| 1 | the registry could not be read (`cli.py:1072-1074`); with `--json`, stdout holds an `error/1` object instead |
| 2 | bad command-line option (Typer's usage error) |
