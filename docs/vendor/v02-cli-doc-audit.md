# v0.2 CLI documentation consistency audit

WO-117 / CP-08. Prepared 2026-11-08 by Samir Vale for Owen Brooks and Nora Bennett.

This is a static source audit of the owner-prepared worktree, reported by the
owner as based on origin/main `07fdbcc`. No git inspection was performed. Sources
are the files in this worktree; line references describe this snapshot. No tests,
builds, help commands, feature commands, browser actions or network requests were
run. Existing tests below were read as evidence, not rerun or claimed green.

The work order and developer page identify v0.2.0 as released. That does not make
every implementation on main part of v0.2.0: the CLI reference explicitly labels
some exposure fields as v0.3 additions, and the developer page keeps the public
Docker image planned. Publication, package availability and platform behavior
were not independently verified through the network.

## Findings to assign

| ID | Priority / type | Document and evidence | Suggested correction | Responsible owner |
| --- | --- | --- | --- | --- |
| CLI-A01 | P2: command example does not list to-dos | The scheduling paragraph in [developers page](../../web/src/pages/developers/index.astro#L158) points readers to `freemyid todo`. [cli.py](../../src/freemyid/cli.py#L27) registers that group with `no_args_is_help=True`; the listing operation is specifically [todo_list](../../src/freemyid/cli.py#L704). [USER_GUIDE.md](../USER_GUIDE.md#L130) and [CLI.md](../CLI.md#L45) already use `freemyid todo list`. | Use `freemyid todo list` in the developer paragraph. Bare `todo` shows group help rather than the promised list. This conclusion is from registration/source inspection, not an executed command. | In-house web owner, coordinated through Morgan; developer page changes must wait for any active WO reservation. |
| CLI-A02 | P2: JSON error contract is too absolute | [CLI.md `--json` rules](../CLI.md#L60) and [developer JSON paragraph](../../web/src/pages/developers/index.astro#L173) say stdout contains exactly one JSON object. Existing [test_json_errors_go_to_stderr_not_stdout](../../tests/test_cli_json_headless.py#L174) explicitly expects **empty stdout**, exit 2 and a stderr message for `status --json --profile nomatch`. [_pick_one](../../src/freemyid/cli.py#L70) prints a diagnostic and raises usage exit; it does not call [_fail](../../src/freemyid/cli.py#L251), which emits `error/1`. | State that successful JSON responses contain one object; some usage/selection failures return nonzero with empty stdout and stderr diagnostics, while `_fail` errors return `error/1`. Consumers must inspect the exit status before parsing stdout. Alternatively an in-house API-contract change could unify errors, but the vendor must not make that change or weaken its tests. | In-house CLI/automation owner decides contract; documentation/web owners apply the chosen wording. |
| CLI-A03 | P3: checklist commands missing from command index | [CLI.md command table](../CLI.md#L28) omits the `checklist` group, although the same document has `checklists/1` and `checklist/1` sections. [cli.py](../../src/freemyid/cli.py#L753) registers the group and list/show/done/undo commands; [checklist tests](../../tests/test_checklist_state.py#L89) document text and JSON behavior. | Add table entries for `checklist list`, `checklist show ID`, `checklist done ID`, and `checklist undo ID`, including `-p/--profile` and the appropriate schema names. Link to the existing schema sections rather than duplicating their fields. | In-house CLI documentation owner; `docs/CLI.md` is read-only in WO-117. |
| CLI-A04 | P2: family prefill documentation needs a wiring decision | [README setup row](../../README.md#L88) says `--prefill` imports a family bundle, and [CLI.md](../CLI.md#L32) lists it alongside the default web wizard. In [setup](../../src/freemyid/cli.py#L148), `web=True` is the default; that branch calls `serve(...)` without consuming `prefill`. Only the terminal branch passes `prefill` to `setup_cli`. [profile_add](../../src/freemyid/cli.py#L514) explicitly selects the terminal branch when prefill is supplied. | Ask the in-house CLI/wizard owner whether web prefill should be wired through. Pending that decision, document the currently wired terminal spelling `setup --no-web --prefill BUNDLE` or `profile add --prefill BUNDLE`; do not imply `setup --prefill BUNDLE` imports into the web flow merely because the option is accepted. No feature invocation or bundle import was performed. | In-house CLI/wizard owners. This is a source-observed documentation/product discrepancy, not authorization to change setup or permission logic. |
| CLI-A05 | P3: entry-point documents do not lead to the expanded CLI reference | The [README Commands section](../../README.md#L82) lists older command families but omits doctor, YAML setup, headless/JSON, exposure, checklist and search-engines. The [user-guide helper section](../USER_GUIDE.md#L122) also lacks a link to `CLI.md`; its concise command list need not become exhaustive. The [developer page](../../web/src/pages/developers/index.astro#L175) already provides a full-reference link. | Add a short reference link in README and the helper section. Optionally add the high-value `doctor`, YAML validation and `search-engines` entry points to README. Keep the user guide brief and explain that search-engines opens guided steps; it does not search the engines. Preserve released/planned distinctions for each feature. | README/user-guide documentation owners, with release status confirmed by Morgan. |

No existing document, source file, test or CLI behavior was changed by this audit.
Priority labels rank documentation impact; they are proposed, not owner-approved
release blockers.

## Source matrix: spelling, options and output

“Matches” means the documented spelling/shape agrees with inspected source or
existing tests. It is not a claim of runtime/platform verification. Commands
below are reference spellings, not instructions executed during this audit.

| Surface / command | Documented spelling and options | Source and existing test evidence | Assessment |
| --- | --- | --- | --- |
| Global options | `freemyid -v/--verbose`; command help | [CLI.md](../CLI.md#L14), [README](../../README.md#L84); [callback](../../src/freemyid/cli.py#L137) | Matches declared global option. No logging, configuration or help command executed. |
| Setup | `setup --web/--no-web`, `--prefill`, `--from`, `--yes`, `--check`, `--update` | [setup](../../src/freemyid/cli.py#L148); [YAML tests](../../tests/test_cli_setup_from.py#L79), especially validation-without-saving and refusal-without-confirmation tests | Options match. Developer validation-first sequence agrees with `--check`; prefill/default-web discrepancy is CLI-A04. Setup/permission rules were not modified or exercised. |
| App/dashboard | `app --no-window`; `dashboard` | [app_window/dashboard](../../src/freemyid/cli.py#L236), command table | Matches registration; no application/window launched. |
| Readiness | `doctor --offline --json` → `doctor/1` | [doctor](../../src/freemyid/cli.py#L173); [test_cli_doctor_json_and_exit_codes](../../tests/test_cli_doctor.py#L193) | Matches. `--offline` skips the mail reachability check; it is not permission for this vendor to run other diagnostics. |
| Scan | `scan -p/--profile -b/--broker` (repeatable), `--headless`, `--json` → `run/1` | [scan](../../src/freemyid/cli.py#L321); [test_scan_json_reports_counts](../../tests/test_cli_json_headless.py#L185) | Matches. Source passes `scan_only=True`, `dry_run=True`; no scan performed. |
| Run | `run --dry-run --headless --json -p -b` → `run/1`; preflight failures may use `error/1` | [run/_do_run](../../src/freemyid/cli.py#L269); [headless tests](../../tests/test_cli_json_headless.py#L197) | Public options match. Hidden `--scheduled` appears in developer cron examples and source deliberately marks it hidden; do not call it an absent implementation. JSON failure qualification is CLI-A02. |
| Exposure | `exposure --offline --refresh --headless --json -p` → `exposure/1` | [exposure](../../src/freemyid/cli.py#L395), [exposure_doc](../../src/freemyid/cli_json.py#L202); [exposure footer test](../../tests/test_cli_search_engines.py#L166) | Declared options and schema match. CLI.md explicitly marks added coverage/DROP/old-address fields as v0.3; do not promote them to released v0.2 solely from source presence. No engine executed. |
| Search-engine guidance | `search-engines [-p PROFILE] [--json]`; `open/done/undo ID`; exact engine aliases `google`/`bing`, or step-ID prefixes → `search_engines/1` | [search_engines](../../src/freemyid/cli.py#L881); [CLI tests](../../tests/test_cli_search_engines.py#L60) | Command table and schema section already exist and agree. Listing is the no-action form, not a `list` subcommand. `open` opens an official browser page and records opening; `done/undo` record checklist progress. It never searches Google/Bing. No page opened or progress changed. |
| Guided search state | `not_started`, `opened`, `done`, `do_again`; pending count and timestamps | [CLI.md schema](../CLI.md#L231); [test_list_json_schema](../../tests/test_cli_search_engines.py#L71), [done/undo](../../tests/test_cli_search_engines.py#L98), [engine state tests](../../tests/test_search_engines.py#L94) | Fields and documented lifecycle have source/test support. `do_again` is Bing-specific per docs; public checklist availability still determines which steps exist. Tests were read only. |
| Fill | `fill BROKER -p/--profile`, `--timeout` | [fill](../../src/freemyid/cli.py#L347); CLI command table | Documented command matches. Source additionally exposes bounded `--timeout` (30–3600, default 600); table is a summary rather than a complete option inventory. No browser/form launched. |
| Saved status | `status -p/--profile --json` → `status/1` | [status](../../src/freemyid/cli.py#L365), [status_doc](../../src/freemyid/cli_json.py#L46); [JSON shape test](../../tests/test_cli_json_headless.py#L84) | Field names, broker ordering, optional tier/timestamps and skipped rows agree. Empty stdout on unknown profile is the documented-contract issue CLI-A02. |
| Reports | `report -p --format html\|pdf --json` → `reports/1` | [report](../../src/freemyid/cli.py#L490), [reports_doc](../../src/freemyid/cli_json.py#L155); [test_report_json](../../tests/test_cli_json_headless.py#L163) | Options/schema match registration. JSON test mocks report generation: neither this audit nor that test establishes PDF rendering availability or installed dependencies. |
| Profiles | `profile list --json` → `profiles/1`; add/edit/remove/export | [profile commands](../../src/freemyid/cli.py#L514), [profiles_doc](../../src/freemyid/cli_json.py#L71); [test_profile_list_json](../../tests/test_cli_json_headless.py#L69) | Names and schema match. README profile-add shorthand should be read with CLI-A04's prefill branch distinction; no profile operations performed. |
| To-dos | `todo list -p --json` → `todos/1`; `todo done ID` | [todo commands](../../src/freemyid/cli.py#L704), [todos_doc](../../src/freemyid/cli_json.py#L87); [no-copy-fields test](../../tests/test_cli_json_headless.py#L112) | CLI/README/user-guide spelling matches. Developer paragraph uses the incomplete group command, CLI-A01. |
| Outbox | `outbox list --json` → `outbox/1`; approve command registered | [outbox commands](../../src/freemyid/cli.py#L728), [outbox_doc](../../src/freemyid/cli_json.py#L104); [test_outbox_list_json](../../tests/test_cli_json_headless.py#L126) | Names and list shape match. Sending/approval implementation is in-house-only and was not invoked or audited for safety here. |
| Scheduling | `schedule install/remove/status`; status `--json` → `schedule/1` | [schedule registration](../../src/freemyid/cli.py#L623), [schedule_doc](../../src/freemyid/cli_json.py#L148); [status JSON tests](../../tests/test_cli_json_headless.py#L155) | Spellings/schema match. Developer scheduling examples use hidden `--scheduled` consistently with the run signature. No scheduler/system command was executed; platform job installation not verified. |
| Registry | `registry show --json` → `registry/1`; `source --plain/--json` → `registry-source/1`; update/validate | [registry commands](../../src/freemyid/cli.py#L652), [serializer shapes](../../src/freemyid/cli_json.py#L120); [fixture-backed tests](../../tests/test_cli_json_headless.py#L138) | Names and public example fields match. No private registry/research file was read, loaded or validated. |
| Checklist | `checklist list/show/done/undo`, `-p/--profile`, `--json`; `checklists/1` vs `checklist/1` | [commands](../../src/freemyid/cli.py#L753), [JSON tests](../../tests/test_checklist_state.py#L107) | Schema examples exist and command tests support them; top-level table omission is CLI-A03. Multiple-profile selection requires `-p`, as documented in the schema prose. |
| Remaining registered controls | `secrets status/migrate`; `config set/enable-submissions`; `wipe` | Registration/signatures in [cli.py](../../src/freemyid/cli.py#L950); `secrets/1` shape in [cli_json.py](../../src/freemyid/cli_json.py#L190) | Command index spellings match. No credential/configuration/consent/deletion behavior executed, changed or security-reviewed. All such implementation remains in-house. |

## JSON field and exit-code cross-check

The inspected stable document families agree with the reference names:
`status/1`, `profiles/1`, `todos/1`, `outbox/1`, `registry/1`,
`registry-source/1`, `schedule/1`, `reports/1`, `run/1`, `secrets/1`,
`error/1`, `exposure/1`, `checklists/1`, `checklist/1`, `search_engines/1`.
Search-engine JSON uses an underscore in the schema name even though the
command uses a hyphen; both are already correct in CLI.md.

[cli_json.py constants](../../src/freemyid/cli_json.py#L24) match the documented
0 OK / 1 error / 2 usage / 3 needs a person / 4 not configured mapping.
The following contextual qualifications matter to consumers:

| Case | Source/test evidence | Documentation assessment |
| --- | --- | --- |
| Headless setup/key/practice failures: exit 4 | `_do_run`, `_open_store_or_fail`; tests `test_headless_without_setup_exits_4`, `test_headless_practice_mode_refuses_real_run`, `test_headless_key_unavailable_exits_4` | Matches CLI.md headless table. |
| No eligible profile: headless exit 3 | `_do_run`; `test_headless_no_consenting_profile_exits_3` | Matches table; the `error/1` example showing 4 is an example, not the only possible failure code. Permission behavior is not part of vendor changes. |
| Completed headless run: needs-human 3 before generic errors 1, otherwise 0 | `_do_run`; `test_headless_post_run_exit_codes` | Matches. Interactive run deliberately keeps 0 for those result counters (`test_interactive_run_keeps_exit_0_even_with_needs_human`). |
| Doctor failure: exit 1; warnings alone do not fail | `doctor` checks for a `fail` result; `test_cli_doctor_json_and_exit_codes` | Matches. No diagnostic probes run here. |
| Unknown/ambiguous identifier: exit 2 | `_pick_one`; selection tests in JSON, checklist and search-engine suites | Exit mapping matches; not every such JSON-mode failure emits a JSON document (CLI-A02). |
| Search-engine invalid action or missing ID: 2; unavailable checklist/open/record: 1; no profile: 4 | `search_engines`, `_checklists_or_fail`, `_checklist_profile`; `tests/test_cli_search_engines.py` | Matches CLI.md search-engine section. Existing tests mock browser opening and fake checklist state; the audit did not execute any of them. |

`emit` uses plain `json.dumps` followed by one newline; the Unicode/long-line
round-trip test in
[test_cli_json_serialization_edges.py](../../tests/test_cli_json_serialization_edges.py#L176)
supports that success-output contract. Additive fields are allowed; examples need
not reproduce every optional/additive field to remain useful.

One lower-confidence follow-up for the CLI owner: CLI.md and cli_json.py promise
UTC timestamps, but `_ts` at cli_json.py:32 simply calls the supplied value's
`isoformat()` and does not itself normalize time zones. The inspected tests use
UTC dates; this audit did not determine whether all upstream stored values are
guaranteed UTC. Do not change serialization or relax the public UTC promise
without checking that invariant. This is an open verification question, not an
asserted runtime defect.

## Handoff and limits

Assign CLI-A01/A03/A05 as narrow documentation follow-ups after checking current
reservations. Send CLI-A02/A04 and the timestamp question to the in-house CLI
owner first: they require decisions about the intended contract or wiring.

Existing `docs/CLI.md`, README, user guide, developer page, CLI source and tests
remain unchanged. No functional verification, release verification, credential
access or protected-area implementation was performed. No fresh green suite is
claimed; this audit relies on static evidence and the owner's separately
reported gate.
