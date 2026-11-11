# Listing states and escalation

Use this guide when tracing one profile's status at one broker. The state module makes
deterministic decisions without I/O; the runner applies them and saves the status
(`src/freemyid/state.py:1-4`; `src/freemyid/engine/runner.py:466-500`). For the wider module
map, read [ARCHITECTURE.md](ARCHITECTURE.md).

## States and allowed moves

The status belongs to a profile/broker pair. `CONFIRMED` means the broker acknowledged the
request or verification was clicked; `REMOVED` means a re-scan no longer finds the listing.
Those are different observations (`src/freemyid/models.py:130-141`).

| State | Meaning in this flow |
| --- | --- |
| `UNKNOWN` | No scan has established an answer yet. |
| `NOT_FOUND` | No confirmed listing was found; this can remain the state after a prior submission. |
| `FOUND` | The listing is eligible for the submission path. |
| `SUBMITTED` | A send has been recorded. |
| `AWAITING_VERIFICATION` | The submitted request needs verification. |
| `CONFIRMED` | The request has been acknowledged or verification clicked. |
| `REMOVED` | A later scan no longer finds the listing. |
| `REAPPEARED` | A listing is found after removal, or becomes visible again after a prior submission. |
| `NEEDS_HUMAN` | The flow needs a person's action. |
| `ERROR` | Processing encountered an error. |

The table summarizes the enum, scan decisions, submission eligibility and send recording
(`src/freemyid/models.py:130-141`; `src/freemyid/state.py:64-95`;
`src/freemyid/engine/runner.py:416-423,678-698`). A broker without a usable search can also
enter `FOUND` through the runner's presumed-listing path; `FOUND` alone therefore does not
prove a successful search (`src/freemyid/engine/runner.py:594-600`).

The diagram contains exactly the edges in `TRANSITIONS`, including unchanged-state edges
(`src/freemyid/state.py:18-27`).

~~~mermaid
stateDiagram-v2
    UNKNOWN --> NOT_FOUND
    UNKNOWN --> FOUND
    NOT_FOUND --> NOT_FOUND
    NOT_FOUND --> FOUND
    NOT_FOUND --> REAPPEARED
    FOUND --> FOUND
    FOUND --> SUBMITTED
    FOUND --> NOT_FOUND
    SUBMITTED --> SUBMITTED
    SUBMITTED --> AWAITING_VERIFICATION
    SUBMITTED --> CONFIRMED
    SUBMITTED --> REMOVED
    AWAITING_VERIFICATION --> AWAITING_VERIFICATION
    AWAITING_VERIFICATION --> CONFIRMED
    AWAITING_VERIFICATION --> SUBMITTED
    AWAITING_VERIFICATION --> REMOVED
    CONFIRMED --> CONFIRMED
    CONFIRMED --> REMOVED
    CONFIRMED --> SUBMITTED
    REMOVED --> REMOVED
    REMOVED --> REAPPEARED
    REAPPEARED --> REAPPEARED
    REAPPEARED --> SUBMITTED
    REAPPEARED --> REMOVED
~~~

Two recovery states sit outside that dictionary. `can_transition` permits entry to
`NEEDS_HUMAN` or `ERROR` from every state. From either recovery state, it permits every
destination except `UNKNOWN`, including `REMOVED` and another recovery state. These rules
are additional to the diagram (`src/freemyid/state.py:28,35-40`).

`transition` rejects a disallowed move with `TransitionError`, copies the status and updates
its state/time. It clears the human-action reason unless the destination is `NEEDS_HUMAN`;
entering `REMOVED` or `NOT_FOUND` resets the escalation level and its timestamp
(`src/freemyid/state.py:43-61`).

## Applying a scan

`after_scan` returns a destination; it does not save a status. Its decisions are below
(`src/freemyid/state.py:74-91`). Here, "found" is the Boolean passed to that function.

| Current situation | Found | Not found |
| --- | --- | --- |
| `UNKNOWN`, `NOT_FOUND`, `ERROR` or `NEEDS_HUMAN`, with no recorded submission | `FOUND` | `NOT_FOUND` |
| `REMOVED` | `REAPPEARED` | `REMOVED` |
| `SUBMITTED`, `AWAITING_VERIFICATION` or `CONFIRMED` | Keep current state | `REMOVED` |
| `REAPPEARED` | `REAPPEARED` | `REMOVED` |
| `FOUND` | `FOUND` | `NOT_FOUND` |
| Remaining cases after a prior submission | `REAPPEARED` | Keep `NOT_FOUND` if already there; otherwise `REMOVED` |

For an actual scan, the runner passes whether there are confirmed matches, applies the
destination through `_set`, stamps `last_scan_at`, and creates a review to-do when only
possible matches remain. An open manual-letter task with no prior send has a separate
branch that keeps the current human-action state. `_set` records and skips a move that
`can_transition` refuses (`src/freemyid/engine/runner.py:534-542,572-593`).

## When a send counts

Entering `SUBMITTED` from another state through `transition` increments `attempts` and
sets `last_submitted_at`. An unchanged `SUBMITTED` transition does neither. A successful
resubmission uses `mark_submitted`, which increments the count and restamps the send even
when the state was already `SUBMITTED` (`src/freemyid/state.py:43-71`).

In the runner's outcome handler, only a request with status `SENT` takes that send-recording
path; it may then enter `AWAITING_VERIFICATION`. A draft or queued request returns the
existing status after updating reporting counts, so preparing a letter is not recorded as
a send (`src/freemyid/engine/runner.py:672-694`). During escalation, a resubmit calls
`mark_submitted` only when its returned request is `SENT`
(`src/freemyid/engine/runner.py:858-867`).

## Escalation timing and runner safeguards

The ladder advances in this order: resubmit, follow-up, legal demand, complaint.
`next_escalation` returns an action, the next level and a due time. It returns no action
unless the state is `SUBMITTED`, `AWAITING_VERIFICATION` or `CONFIRMED`, a submission time
exists, and another rung remains (`src/freemyid/state.py:101-138`).

One window is the broker's `typical_processing_days` plus `GRACE_DAYS`, currently 15 days.
The next rung becomes due at or after one window from the later of `last_submitted_at`
and `last_escalated_at`; the pure function does not itself apply its decision
(`src/freemyid/state.py:14,119-138`).

The runner performs more checks before acting. A parent's ladder covers its child broker;
a blind broker in `CONFIRMED` does not escalate without a scan. An unsent previous rung
blocks advancement. Legal-demand and complaint rungs also wait for the runner's legal
window; an early follow-up drops the law citation and remains a polite reminder. A dry run
records that escalation is due without advancing the saved level
(`src/freemyid/engine/runner.py:823-852`).

A legal-demand email always waits for approval, including in automatic email mode. Without
a mailbox, the runner creates a manual-letter to-do instead
(`src/freemyid/engine/outbox.py:285-289`; `src/freemyid/engine/runner.py:935-955`).

The runner creates the corresponding resubmit, letter or complaint to-do, then records the
new level/time. A failed letter keeps the old level and updates the retry anchor. Its
`_ladder_view` also accounts for a letter actually sent later than it was queued, so the
following wait starts from that later send (`src/freemyid/engine/runner.py:853-884,912-924`).

## Scheduling the next check

`next_check_at` adds the following number of days to `now`
(`src/freemyid/state.py:141-151`):

| State | Delay |
| --- | --- |
| `SUBMITTED`, `AWAITING_VERIFICATION`, `CONFIRMED` | Broker processing days, clamped to 3–14 days. |
| `REMOVED`, `NOT_FOUND` | Broker's `recheck_interval_days`. |
| Other states | 7 days. |

The `weekly` option caps `FOUND`, `REAPPEARED` and `NEEDS_HUMAN` at seven days; those states
already use seven days in the current function. It does not cap the removed/not-found
broker interval (`src/freemyid/state.py:141-151`).

After submission/verification/escalation work, the runner calls `next_check_at` with the
profile's `weekly_recheck` setting and saves the status. With `only_due`, a future scheduled
check skips normal processing, although submitted or awaiting-verification states can still
check verification mail first (`src/freemyid/engine/runner.py:450-459,488-500`).

## What this guide does not cover

This guide describes the current worktree's state policy and the runner calls that apply it.
It is not a legal interpretation, a promise of removal, or a full account of mailbox,
submitter, consent, storage, key or secret handling. Use [ARCHITECTURE.md](ARCHITECTURE.md)
to find the broader component map; changes in those areas require their owning team's
review.
