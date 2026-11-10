#!/usr/bin/env python3
"""Pick the model, reasoning effort, skills and read-first files for a work order.

Config: tools/agent_routing.yaml. Guide: docs/AGENT_ROUTING.md.

    tools/route.py WO-225                      # human summary for every vendor
    tools/route.py WO-225 --vendor codex --format args    # -> -m gpt-6.1-sol -c model_reasoning_effort=low
    tools/route.py WO-225 --vendor grok --format args     # -> -m grok-4.7-build-fast --effort low
    tools/route.py WO-225 --vendor claude --format json   # -> Agent tool model/effort/skills/agent
    tools/route.py WO-225 --vendor claude --format prompt # -> block to paste at the top of an agent prompt
    tools/route.py --kind security --vendor claude        # no work order: route a kind of work directly
    tools/route.py --paths src/freemyid/crypto.py --kind engine
    tools/route.py check                       # every docs/vendor/WO-*.md resolves (CI-safe)
    tools/route.py table                       # the kind x vendor matrix

A work order can override the defaults with header lines (before the first "## " heading):
    Kind: tests          Tier: deep          Model: opus          Effort: high          Skills: code-review, dataviz
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "tools" / "agent_routing.yaml"
VENDORS = ("claude", "codex", "grok")
TIER_ORDER = ("light", "standard", "deep", "max")
HEADER = re.compile(r"^(Kind|Tier|Model|Effort|Skills|Vendor):\s*(.+?)\s*$", re.IGNORECASE)


@dataclass
class Route:
    vendor: str
    kind: str
    tier: str
    model: str
    effort: str
    skills: list[str] = field(default_factory=list)
    agent: str = ""
    read_first: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def load_config(path: Path = CONFIG) -> dict[str, Any]:
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    validate(cfg)
    return cfg


def validate(cfg: dict[str, Any]) -> None:
    tiers, kinds = cfg.get("tiers", {}), cfg.get("kinds", {})
    for t in TIER_ORDER:
        if t not in tiers:
            raise ValueError(f"tier {t!r} missing")
        for v in VENDORS:
            spec = tiers[t].get(v) or {}
            if not spec.get("model") or not spec.get("effort"):
                raise ValueError(f"tier {t!r} has no model/effort for {v}")
    for k, spec in kinds.items():
        if spec.get("tier") not in TIER_ORDER:
            raise ValueError(f"kind {k!r} has unknown tier {spec.get('tier')!r}")
    for rule in cfg.get("infer_kind", []):
        if rule["kind"] not in kinds:
            raise ValueError(f"infer_kind points at unknown kind {rule['kind']!r}")
    for rule in cfg.get("escalate", []):
        if rule.get("tier", "light") not in TIER_ORDER:
            raise ValueError(f"escalate rule {rule['prefix']!r} has unknown tier")


def parse_work_order(text: str) -> tuple[dict[str, str], list[str]]:
    """Header overrides (lines before the first '## ') and the '## Allowed paths' list."""
    head: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("## "):
            break
        m = HEADER.match(line.strip())
        if m:
            head[m.group(1).lower()] = m.group(2)
    paths: list[str] = []
    in_allowed = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_allowed = line.strip().lower().startswith("## allowed paths")
            continue
        if in_allowed:
            m = re.match(r"^[-*]\s*`?([^`\s]+)`?", line.strip())
            if m:
                paths.append(m.group(1))
    return head, paths


def _max_tier(a: str, b: str) -> str:
    return a if TIER_ORDER.index(a) >= TIER_ORDER.index(b) else b


def resolve(cfg: dict[str, Any], vendor: str, *, kind: str | None = None, paths: list[str] | None = None,
            head: dict[str, str] | None = None) -> Route:
    if vendor not in VENDORS:
        raise ValueError(f"unknown vendor {vendor!r} (use {', '.join(VENDORS)})")
    head, paths = head or {}, [p for p in (paths or []) if p != "VENDOR_STATUS.md"]
    reasons: list[str] = []
    kind = (head.get("kind") or kind or "").strip().lower() or None
    if kind:
        reasons.append(f"kind {kind} (stated)")
    else:
        for rule in cfg.get("infer_kind", []):
            if any(p.startswith(rule["prefix"]) for p in paths):
                kind = rule["kind"]
                reasons.append(f"kind {kind} (inferred from {rule['prefix']})")
                break
    if not kind:
        kind = "docs"
        reasons.append("kind docs (default: nothing stated or inferable)")
    if kind not in cfg["kinds"]:
        raise ValueError(f"unknown kind {kind!r} (known: {', '.join(sorted(cfg['kinds']))})")
    kspec = cfg["kinds"][kind]
    tier = kspec["tier"]
    skills = list(kspec.get("skills", []))
    for rule in cfg.get("escalate", []):
        if any(p.startswith(rule["prefix"]) for p in paths):
            new = _max_tier(tier, rule.get("tier", tier))
            if new != tier:
                reasons.append(f"tier {tier} -> {new} (touches {rule['prefix']})")
            tier = new
            skills += [s for s in rule.get("skills", []) if s not in skills]
    if head.get("tier"):
        t = head["tier"].strip().lower()
        if t not in TIER_ORDER:
            raise ValueError(f"unknown tier {t!r}")
        reasons.append(f"tier {t} (work order override)")
        tier = t
    spec = cfg["tiers"][tier][vendor]
    model, effort = spec["model"], spec["effort"]
    if head.get("model"):
        model = head["model"].strip()
        reasons.append("model (work order override)")
    if head.get("effort"):
        effort = head["effort"].strip().lower()
        reasons.append("effort (work order override)")
    if head.get("skills"):
        skills += [s.strip() for s in head["skills"].split(",") if s.strip() and s.strip() not in skills]
    for word in (model, effort):
        if not re.fullmatch(r"[A-Za-z0-9._:-]+", word):
            raise ValueError(f"unsafe model/effort value {word!r}")
    return Route(vendor=vendor, kind=kind, tier=tier, model=model, effort=effort,
                 skills=skills if vendor == "claude" else [], agent=kspec.get("agent", ""),
                 read_first=list(kspec.get("read_first", [])), reasons=reasons)


def work_order_path(wo: str) -> Path:
    name = wo if wo.endswith(".md") else f"{wo.upper()}.md"
    p = Path(name) if "/" in name else ROOT / "docs" / "vendor" / name
    if not p.is_file():
        raise FileNotFoundError(f"no work order file {p}")
    return p


def render(r: Route, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(asdict(r), indent=2)
    if fmt == "args":
        if r.vendor == "codex":
            return f"-m {r.model} -c model_reasoning_effort={r.effort}"   # plain words: safe to word-split
        if r.vendor == "grok":
            return f"-m {r.model} --effort {r.effort}"
        return f"model={r.model} effort={r.effort}"   # Claude: Agent tool parameters
    if fmt == "prompt":
        lines = [f"Routing ({r.kind}, tier {r.tier}): you run on {r.model} at {r.effort} effort."]
        if r.read_first:
            lines.append("Read these first and only open other files when you need them: "
                         + ", ".join(r.read_first) + ".")
        if r.skills:
            lines.append("Load these skills before starting: " + ", ".join(r.skills) + ".")
        lines.append("Keep reports short: results, file:line, exact test counts. No restating the task.")
        return "\n".join(lines)
    extra = f" skills={','.join(r.skills)}" if r.skills else ""
    return (f"{r.vendor:7} {r.model} / {r.effort}  (kind {r.kind}, tier {r.tier}, agent {r.agent or '-'}){extra}\n"
            f"        why: {'; '.join(r.reasons)}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?", help="WO-NNN, a work-order path, 'check' or 'table'")
    ap.add_argument("--vendor", choices=VENDORS)
    ap.add_argument("--kind")
    ap.add_argument("--paths", nargs="*", default=[])
    ap.add_argument("--format", choices=("text", "json", "args", "prompt"), default="text")
    ap.add_argument("--config", type=Path, default=CONFIG)
    a = ap.parse_args(argv)
    cfg = load_config(a.config)

    if a.target == "table":
        print(f"{'kind':13} {'tier':9} " + "  ".join(f"{v:28}" for v in VENDORS))
        for k in sorted(cfg["kinds"]):
            row = [resolve(cfg, v, kind=k) for v in VENDORS]
            print(f"{k:13} {row[0].tier:9} " + "  ".join(f"{r.model + ' / ' + r.effort:28}" for r in row))
        return 0
    if a.target == "check":
        bad = 0
        for p in sorted((ROOT / "docs" / "vendor").glob("WO-*.md")):
            try:
                head, paths = parse_work_order(p.read_text(encoding="utf-8"))
                for v in VENDORS:
                    resolve(cfg, v, head=head, paths=paths)
            except (ValueError, KeyError) as exc:
                bad += 1
                print(f"{p.name}: {exc}")
        print("route check: OK" if not bad else f"route check: {bad} work order(s) fail")
        return 1 if bad else 0

    head: dict[str, str] = {}
    paths = list(a.paths)
    if a.target:
        head, wo_paths = parse_work_order(work_order_path(a.target).read_text(encoding="utf-8"))
        paths += wo_paths
    elif not a.kind and not paths:
        ap.error("give a work order, --kind or --paths")
    vendors = [a.vendor] if a.vendor else ([head["vendor"].strip().lower()] if head.get("vendor", "").strip().lower()
                                          in VENDORS else list(VENDORS))
    for v in vendors:
        print(render(resolve(cfg, v, kind=a.kind, paths=paths, head=head), a.format))
    return 0


if __name__ == "__main__":
    sys.exit(main())
