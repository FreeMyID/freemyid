"""tools/cloudflare_email_obfuscation.py: offline checks (no network, no real token)."""
import importlib.util
import json
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "cloudflare_email_obfuscation", Path(__file__).resolve().parent.parent / "tools" / "cloudflare_email_obfuscation.py")
eo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eo)


def _fake(monkeypatch, tmp_path, state):
    calls = []

    def api(method, path, body=None):
        calls.append((method, path, body))
        if path.startswith("/zones?"):
            return {"success": True, "result": [{"id": "z1"}]}
        if method == "PATCH":
            state["v"] = body["value"]
        return {"success": True, "result": {"value": state["v"]}}

    monkeypatch.setattr(eo.cfh, "api", api)
    monkeypatch.setattr(eo.cfh, "CFG", str(tmp_path))
    return calls


def test_dry_run_writes_nothing(monkeypatch, tmp_path, capsys):
    calls = _fake(monkeypatch, tmp_path, {"v": "on"})
    monkeypatch.setattr(sys, "argv", ["x"])
    eo.main()
    assert not [c for c in calls if c[0] == "PATCH"]
    assert list(tmp_path.iterdir()) == []


def test_apply_backs_up_then_sets_off_and_rollback_restores(monkeypatch, tmp_path):
    state = {"v": "on"}
    calls = _fake(monkeypatch, tmp_path, state)
    monkeypatch.setattr(sys, "argv", ["x", "--apply"])
    eo.main()
    assert state["v"] == "off"
    assert [c[1] for c in calls if c[0] == "PATCH"] == ["/zones/z1/settings/email_obfuscation"]
    bak = next(tmp_path.iterdir())
    assert json.loads(bak.read_text())["value"] == "on"
    monkeypatch.setattr(sys, "argv", ["x", "--rollback", str(bak)])
    eo.main()
    assert state["v"] == "on"
