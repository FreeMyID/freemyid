import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("pm_sync", Path(__file__).resolve().parent.parent / "tools" / "pm_sync.py")
pm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pm)

WO = """# WO-103: Home hero fix (CP-01)
Status: open
Vendor: codex
Agent: web-designer
Source: docs/vendor/CODEX_PROPOSALS.md CP-01

## Allowed paths (the vendor may change ONLY these)
- web/src/pages/index.astro
- VENDOR_STATUS.md

## Out of scope
- nothing/here
"""

BL = """## IN — in-house
### Platform / devops-engineer (Dana)
- BL-IN-42 Reproducible builds + published SBOM (0.3).
## CX — Codex team
- CX-08 docs/dev/ARCHITECTURE.md: module map
"""


def test_wo_parser(tmp_path):
    p = tmp_path / "WO-103.md"
    p.write_text(WO)
    it = pm.parse_wo(p)
    assert it["key"] == "WO-103" and it["team"] == "Codex" and it["agent"] == "web-designer"
    assert it["allowed_paths"] == ["web/src/pages/index.astro", "VENDOR_STATUS.md"]
    assert it["title"].startswith("WO-103: Home hero")


def test_wo_no_vendor_is_inhouse_and_merge_done(tmp_path):
    p = tmp_path / "WO-001.md"
    p.write_text("# WO-001: x\nStatus: accepted (merged)\n")
    assert pm.parse_wo(p)["team"] == "In-house"
    assert pm.wo_status_to_field("open", True) == "Done"
    assert pm.wo_status_to_field("open", False) == "Ready"
    assert pm.wo_status_to_field("queued after WO-125", False) == "Backlog"


def test_merged_sha():
    log = "abc1234 Merge WO-137 (Codex)\ndef5678 Merge WO-137 (Codex)\n1111111 Merge WO-5"
    assert pm.merged_wos(log) == {"WO-137": "abc1234", "WO-5": "1111111"}


def test_backlog():
    items = pm.parse_backlog(BL)
    assert [i["key"] for i in items] == ["BL-IN-42", "CX-08"]
    assert items[0]["release"] == "v0.3" and items[0]["kind"] == "Ops" and items[0]["team"] == "In-house"
    assert items[1]["team"] == "Codex" and items[1]["kind"] == "Docs"


def test_sec_body_redacted():
    h = "- SEC-99 MED (matcher: household member CONFIRMED on secret detail) -> automation-engineer, open\n"
    (item,) = pm.parse_sec(h)
    body = pm.issue_body(item)
    assert "secret detail" not in body and "matcher" not in body
    assert body.splitlines()[0] == "ID: SEC-99" and "Severity: MED" in body
    assert "docs/handoff/qa-security.md" in body and len(body.splitlines()) == 5


def test_plan_idempotent():
    items = [{"key": "WO-1", "title": "WO-1: a", "team": "Codex", "lane": "CX", "kind": "Work order",
              "priority": "P2", "closed": False, "project_status": "Ready", "merge_sha": ""}]
    assert pm.plan(items, {"items": {}})[0]["action"] == "create"
    m = {"items": {"WO-1": {"number": 5, "state": "open"}}}
    assert pm.plan(items, m)[0]["action"] == "none"
    items[0]["closed"] = True
    assert pm.plan(items, m)[0]["action"] == "close"
    assert len(pm.plan(items + items, {"items": {}})) == 1


def test_apply_gate_and_mock_runner():
    p = pm.plan([{"key": "WO-1", "title": "t", "team": "Codex", "lane": "CX", "kind": "Work order",
                  "priority": "P2", "closed": True, "project_status": "Done", "merge_sha": "abc1234"}], {"items": {}})
    calls = []
    with pytest.raises(pm.ApplyRefused):
        pm.apply_plan(p, {"items": {}}, "o/r", "o", None, run=calls.append, env={})
    assert calls == []
    out = []

    def run(args):
        out.append(args)
        assert isinstance(args, list)
        if args[:3] == ["gh", "issue", "list"]:
            return "[]"
        return "https://github.com/o/r/issues/7\n"

    m = pm.apply_plan(p, {"items": {}}, "o/r", "o", None, run=run, env={"FREEMYID_PM_APPLY": "1"})
    assert m["items"]["WO-1"]["number"] == 7 and m["items"]["WO-1"]["state"] == "closed"
    assert out[0][:3] == ["gh", "issue", "list"]
    assert out[1][:3] == ["gh", "issue", "create"] and out[2][:3] == ["gh", "issue", "close"]
    assert "abc1234" in out[2][-1]


def test_existing_issue_is_adopted_not_duplicated():
    p = pm.plan([{"key": "WO-2", "title": "t", "team": "Codex", "lane": "CX", "kind": "Work order",
                  "priority": "P2", "closed": False, "project_status": "Ready", "merge_sha": ""}],
                {"items": {}})
    out = []

    def run(args):
        out.append(args)
        if args[:3] == ["gh", "issue", "list"]:
            return json.dumps([{"number": 9, "title": "WO-2: made by Codex",
                                "url": "https://github.com/o/r/issues/9", "state": "OPEN"}])
        raise AssertionError(f"unexpected call {args}")

    m = pm.apply_plan(p, {"items": {}}, "o/r", "o", None, run=run, env={"FREEMYID_PM_APPLY": "1"})
    assert m["items"]["WO-2"]["number"] == 9 and len(out) == 1


def test_main_apply_refused(monkeypatch):
    monkeypatch.delenv("FREEMYID_PM_APPLY", raising=False)
    assert pm.main(["--apply"]) == 2


def test_dry_run_json(capsys):
    assert pm.main(["--summary"]) == 0
    assert json.loads(capsys.readouterr().out)["mode"] == "dry-run"


def test_tracked_json_sec_and_owner_items(tmp_path):
    import json as _json
    collect, issue_body = pm.collect, pm.issue_body
    (tmp_path / "docs" / "pm").mkdir(parents=True)
    (tmp_path / "docs" / "vendor").mkdir(parents=True)
    (tmp_path / "docs" / "pm" / "tracked.json").write_text(_json.dumps({
        "security": [{"id": "SEC-900", "severity": "LOW", "owner": "Theo", "status": "open",
                      "detail": "secret repro steps"}],
        "owner_tasks": [{"key": "OWN-x", "title": "Do a thing"},
                        {"key": "OWN-y", "title": "Done thing", "done": True}]}))
    items = {i["key"]: i for i in collect(tmp_path, git_log="")}
    sec = items["SEC-900"]
    body = issue_body(sec)
    assert "Severity: LOW" in body and "secret" not in body and not sec["closed"]
    assert items["OWN-x"]["closed"] is False and items["OWN-y"]["closed"] is True
