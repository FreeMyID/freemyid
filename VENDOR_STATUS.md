# WO-253 (issue pending) — Evidence lifecycle guide

## Done

- Added `docs/dev/PROOF_VAULT.md` after checking the existing architecture map and developer guides. The new guide follows the evidence lifecycle instead of repeating the module map.
- Acceptance checklist:
  - [x] Matched mailbox replies: duplicate-content handling and optional answered-request link.
  - [x] Hand-completed steps: user-attestation creation, request association and non-blocking save failure.
  - [x] Optional call notes and postal receipts: current limits, accepted file kinds and request association.
  - [x] Queued letter copies: shared evidence writer and the distinction from later sent-email evidence.
  - [x] Signed authorization: `_consent` evidence, saved consent reference and on-file lookup.
  - [x] Storage described only as encrypted through `Store.save_evidence`; lookup/read flow included without key or cipher detail.
  - [x] Profile/broker receipt presentation and the evidence-view route, including attachment behavior and missing/read-failure responses.
  - [x] Report behavior described accurately: a status/date summary, not an evidence bundle; generated HTML/PDF output is distinguished from stored evidence.
  - [x] Wipe behavior: selected folder, confirmation, owned-entry removal, other top-level names and copies elsewhere.
  - [x] Existing architecture guide linked; final section is “What this guide does not cover”.
- Manually checked **all 25 inline citation spans**, comprising **34 line ranges**, against this worktree's source for wording and meaning. Explicitly applying the existing citation helper to the new document reports **zero findings**. The architecture link resolves.
- No product defect is asserted and no source, test or other documentation file was changed. No personal data, network, installation, real mailbox, keyring or user evidence was accessed.

## Next

- Ready for Owen Brooks's independent read-only review before Nora reports delivery or publishes the branch.
- In-house retains acceptance and merge control.

## Questions for the owner

- Tracker issue ID remains pending in the local work-order metadata.
- The existing automatic citation test lists four documents and does not include this new file. WO-255 is intended to expand that guard; this session explicitly checked the new file without editing the guard.
- No contract or scope decision blocks review.

## How to test

From `.vendor-wt/wo-253`:

- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/codex/test_cx_dev_source_citations.py` — **14 passed**, zero skipped or xfailed, in 0.16s.
- Explicit new-document check, executed after the final wording/citation adjustment:

```bash
python3 - <<'PY'
from pathlib import Path
import runpy
root = Path.cwd()
g = runpy.run_path('tests/codex/test_cx_dev_source_citations.py')
doc = 'docs/dev/PROOF_VAULT.md'
refs = [g['parse_citation'](x) for x in g['CODE_SPAN'].findall((root / doc).read_text())]
refs = [x for x in refs if x is not None]
findings = g['document_findings'](doc, root=root)
print(f'{len(refs)} citation spans; {sum(len(x.ranges) for x in refs)} line ranges; {len(findings)} findings')
assert not findings, findings
assert (root / 'docs/dev/ARCHITECTURE.md').is_file()
PY
```

Result: **25 citation spans; 34 line ranges; 0 findings**. The helper checks path existence and line bounds only; manual inspection supplied the content check. This documentation session did not run browser, mailbox, cryptographic or native Windows checks.
