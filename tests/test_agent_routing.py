"""tools/route.py + tools/agent_routing.yaml: per-work-order model, effort and skills selection."""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("route", ROOT / "tools" / "route.py")
assert _spec and _spec.loader
route = importlib.util.module_from_spec(_spec)
sys.modules["route"] = route
_spec.loader.exec_module(route)


@pytest.fixture(scope="module")
def cfg():
    return route.load_config()


def test_config_is_valid_and_complete(cfg):
    assert set(route.TIER_ORDER) <= set(cfg["tiers"])
    assert {"docs", "tests", "security", "engine", "architecture"} <= set(cfg["kinds"])


def test_every_work_order_resolves_for_every_vendor(cfg):
    for p in sorted((ROOT / "docs" / "vendor").glob("WO-*.md")):
        head, paths = route.parse_work_order(p.read_text(encoding="utf-8"))
        for v in route.VENDORS:
            r = route.resolve(cfg, v, head=head, paths=paths)
            assert r.model and r.effort, p.name


def test_kind_inferred_from_allowed_paths(cfg):
    text = "# WO-999: x\nVendor: codex\n\n## Allowed paths\n- `docs/i18n/STRINGS.md`\n- `VENDOR_STATUS.md`\n"
    head, paths = route.parse_work_order(text)
    r = route.resolve(cfg, "codex", head=head, paths=paths)
    assert (r.kind, r.tier) == ("i18n", "light")


def test_sensitive_paths_escalate_and_add_security_review(cfg):
    r = route.resolve(cfg, "claude", kind="docs", paths=["src/freemyid/crypto.py"])
    assert r.tier == "deep" and "security-review" in r.skills
    assert any("crypto" in why for why in r.reasons)


def test_header_overrides_win(cfg):
    text = ("# WO-998: y\nKind: tests\nTier: max\nEffort: low\nSkills: dataviz, code-review\n\n"
            "## Allowed paths\n- `tests/codex/test_x.py`\n")
    head, paths = route.parse_work_order(text)
    r = route.resolve(cfg, "claude", head=head, paths=paths)
    assert r.tier == "max" and r.effort == "low"
    assert r.model == cfg["tiers"]["max"]["claude"]["model"]
    assert {"dataviz", "code-review"} <= set(r.skills)


def test_unknown_kind_or_tier_is_refused(cfg):
    with pytest.raises(ValueError):
        route.resolve(cfg, "codex", kind="nonsense")
    with pytest.raises(ValueError):
        route.resolve(cfg, "codex", head={"tier": "ultra"})


def test_args_output_is_plain_words_for_shell_splitting(cfg):
    for v in ("codex", "grok"):
        out = route.render(route.resolve(cfg, v, kind="security"), "args")
        assert re.fullmatch(r"[A-Za-z0-9._:= -]+", out), out
    assert route.render(route.resolve(cfg, "codex", kind="docs"), "args").startswith("-m ")


def test_unsafe_override_values_rejected(cfg):
    with pytest.raises(ValueError):
        route.resolve(cfg, "codex", head={"model": "gpt; rm -rf ~"})


def test_skills_only_for_claude(cfg):
    assert route.resolve(cfg, "codex", kind="security").skills == []
    assert route.resolve(cfg, "claude", kind="security").skills


def test_read_first_files_exist(cfg):
    missing = [f for k in cfg["kinds"].values() for f in k.get("read_first", []) if not (ROOT / f).exists()]
    assert not missing, missing


def test_cli_check_passes(capsys):
    assert route.main(["check"]) == 0
    assert "route check: OK" in capsys.readouterr().out
