# WO-252 (issue pending) — Listing states and escalation guide

## Done

- Added `docs/dev/STATE_MACHINE.md` after checking existing developer guides. The architecture
  map is linked instead of repeated; no existing state-machine guide was present.
- Acceptance checklist:
  - [x] Described all ten listing states and distinguished request confirmation from removal.
  - [x] Mermaid diagram has exactly the 24 `TRANSITIONS` edges, including self-edges.
  - [x] Described the separate `NEEDS_HUMAN`/`ERROR` rules as the code implements them:
    entry from every state, exit to every state except `UNKNOWN` (including `REMOVED`).
  - [x] Explained `after_scan`, runner application and manual-letter/blind-search branches.
  - [x] Explained first-send and resubmission counts, and why drafts/queues do not count.
  - [x] Explained the four escalation rungs, processing-days-plus-15 window, timing anchor,
    legal-window/approval holds, dry-run behavior and delayed-send adjustment.
  - [x] Explained next-check intervals, weekly option and runner due/verification behavior.
  - [x] Linked `ARCHITECTURE.md`; the final section is “What this guide does not cover”.
- Manually checked every one of the **24 source citation spans** against this worktree's
  source and the surrounding meaning, not just whether lines exist.
- Used a tilde Markdown fence for the Mermaid block so the existing inline-code citation
  parser sees all citations after it. Explicit verification confirmed the parser finds all
  24 source citation spans, with zero findings.
- No product code, tests, dependencies or other docs changed. No real personal values,
  network access, installs, secret details or git mutations were used in this builder session.

## Next

- Ready for Owen Brooks's independent review before Nora reports delivery and publishes it.
- In-house retains acceptance and merge control.

## Questions for the owner

- Tracker issue is pending in the local issue map; no issue number was invented.
- No implementation or contract change is needed for this guide.

## How to test

From `.vendor-wt/wo-252`:

- `PYTHONPATH=$PWD/src ../../.venv/bin/pytest -q tests/codex/test_cx_dev_source_citations.py`
  — **14 passed**, no skips or xfails (final run: 0.14s).
- Explicit new-document citation and diagram check below — **24 citation spans, zero
  findings; 24 Mermaid edges exactly match `TRANSITIONS`, with no duplicates**.

```bash
PYTHONPATH=$PWD/src ../../.venv/bin/python - <<'PY'
import ast
from pathlib import Path
import re
import runpy

root = Path.cwd()
guard = runpy.run_path('tests/codex/test_cx_dev_source_citations.py')
document = 'docs/dev/STATE_MACHINE.md'
text = (root / document).read_text()
spans = [token for token in guard['CODE_SPAN'].findall(text)
         if guard['parse_citation'](token) is not None]
assert len(spans) == text.count('`src/') == 24
assert not guard['document_findings'](document)
tree = ast.parse((root / 'src/freemyid/state.py').read_text())
table = next(node for node in tree.body if isinstance(node, ast.AnnAssign)
             and isinstance(node.target, ast.Name) and node.target.id == 'TRANSITIONS')
expected = {(source.attr, target.attr)
            for source, targets in zip(table.value.keys, table.value.values)
            for target in targets.elts}
diagram = text.split('~~~mermaid\n', 1)[1].split('\n~~~', 1)[0]
edges = re.findall(r'^\s*([A-Z_]+) --> ([A-Z_]+)\s*$', diagram, re.M)
assert len(edges) == len(set(edges)) == 24
assert set(edges) == expected
print('24 citation spans, zero findings; 24 exact transition edges')
PY
```

The required pytest guard checks a fixed list of existing docs and does not yet include
this new file; the explicit invocation above covers it. Citation bounds alone do not prove
prose accuracy, which is why all 24 spans were also checked manually. Mermaid rendering,
native Windows execution and the full application test suite were not run for this docs WO.
