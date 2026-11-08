#!/usr/bin/env python3
"""Mirror the local work tracking files into GitHub issues + one Project v2.

Sources (the files stay the source of truth; vendors cannot run gh):
  docs/vendor/WO-*.md, docs/BACKLOG.md, SEC-* in docs/handoff/qa-security.md,
  the Owner TODO line of the latest PROGRESS.md checkpoint.

Default is --dry-run: prints the plan as JSON, makes NO network calls.
--apply talks to GitHub through the gh CLI and refuses to run unless the
environment variable FREEMYID_PM_APPLY=1 is set.

Stdlib only. gh is called with argument lists (never shell=True).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP_PATH = ROOT / "docs" / "pm" / "issue_map.json"
DEFAULT_REPO = "FreeMyID/freemyid-pm"
DEFAULT_OWNER = "FreeMyID"
SEC_POINTER = "Details: docs/handoff/qa-security.md (not repeated here)."

TEAMS = {"codex": "Codex", "copilot": "Copilot"}
LANE_BY_TEAM = {"In-house": "IN", "Codex": "CX", "Copilot": "CP"}


class ApplyRefused(RuntimeError):
    pass


# ---------------------------------------------------------------- parsing

def _field(text: str, name: str) -> str:
    m = re.search(rf"^{name}:[ \t]*(.*)$", text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def parse_wo(path: Path) -> dict:
    """Parse one docs/vendor/WO-NNN.md into an item dict."""
    text = path.read_text(encoding="utf-8")
    first = text.splitlines()[0] if text else ""
    m = re.match(r"#\s*(WO-\d+):\s*(.*)", first)
    num = m.group(1) if m else path.stem
    title = m.group(2).strip() if m else first.lstrip("# ").strip()
    status = _field(text, "Status")
    vendor = _field(text, "Vendor").lower()
    team = TEAMS.get(vendor, "In-house")
    allowed: list[str] = []
    sec = re.search(r"^##\s*Allowed paths[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.MULTILINE | re.DOTALL)
    if sec:
        for line in sec.group(1).splitlines():
            line = line.strip()
            if line.startswith("- "):
                allowed.append(line[2:].strip())
    return {
        "key": num,
        "title": f"{num}: {title}",
        "team": team,
        "lane": LANE_BY_TEAM[team],
        "kind": "Work order",
        "priority": "P2",
        "agent": _field(text, "Agent"),
        "wo": num,
        "wo_status": status,
        "source": _field(text, "Source"),
        "allowed_paths": allowed,
        "release": "",
        "file": str(path.relative_to(ROOT)) if path.is_absolute() and ROOT in path.parents else str(path),
    }


def wo_status_to_field(status: str, merged: bool) -> str:
    s = status.lower()
    if merged or s.startswith(("accepted", "merged", "done")):
        return "Done"
    if s.startswith(("queued", "blocked")):
        return "Backlog" if s.startswith("queued") else "Blocked"
    if "progress" in s or "started" in s:
        return "In progress"
    if "review" in s:
        return "In review"
    return "Ready"


def merged_wos(git_log: str) -> dict[str, str]:
    """Parse `git log --format='%H %s' --grep 'Merge WO-'` into {WO-NNN: sha}."""
    out: dict[str, str] = {}
    for line in git_log.splitlines():
        m = re.match(r"([0-9a-f]{7,40})\s+Merge (WO-\d+)", line.strip())
        if m and m.group(2) not in out:  # newest first: keep the first seen
            out[m.group(2)] = m.group(1)
    return out


_SECTION_AGENT = re.compile(r"^###\s*(.*?)\s*/\s*([\w-]+)\s*\(([^)]*)\)")


def parse_backlog(text: str) -> list[dict]:
    """Parse BL-/CX-/CP- bullet items from docs/BACKLOG.md."""
    items: list[dict] = []
    team = "In-house"
    agent = ""
    section = ""
    for line in text.splitlines():
        if line.startswith("## "):
            head = line.lower()
            team = "Codex" if "codex" in head else "Copilot" if "copilot" in head else "In-house"
            agent, section = "", ""
            continue
        if line.startswith("### "):
            section = line[4:].strip()
            m = re.search(r"\(([A-Za-z]+)\)\s*$", section)
            agent = m.group(1) if m else ""
            continue
        m = re.match(r"-\s+((?:BL-IN|CX|CP)-[\w]+)\s+(.*)", line)
        if not m:
            continue
        key, rest = m.group(1), m.group(2).strip()
        rel = ""
        rm = re.search(r"\((\d\.\d)\)\s*\.?\s*$", rest)
        if rm:
            rel = f"v{rm.group(1)}"
            rest = rest[: rm.start()].strip()
        low = rest.lower()
        sec_low = section.lower()
        if "sec-" in low:
            kind = "Security"
        elif "owner" in low and "(owner" in low:
            kind = "Owner task"
        elif "platform" in sec_low or "devops" in sec_low:
            kind = "Ops"
        elif "docs" in low or "doc " in low or key.startswith(("CX-0", "CP-0")) and "docs" in sec_low:
            kind = "Docs"
        elif low.startswith(("fix", "installer 10-second")) or "fix" in low.split()[:4]:
            kind = "Bug"
        else:
            kind = "Feature"
        items.append({
            "key": key,
            "title": f"{key}: {rest}",
            "team": team,
            "lane": LANE_BY_TEAM[team],
            "kind": kind,
            "priority": "P2",
            "agent": agent if team == "In-house" else "",
            "wo": "",
            "release": rel,
            "section": section,
        })
    return items


_SEV = r"(CRITICAL|HIGH|MED|LOW|INFO)"


def parse_sec(handoff: str, review: str = "") -> list[dict]:
    """SEC-* ids seen in the qa-security handoff. Severity/status are best effort.

    Only id, severity, owner and status are kept; details never leave the file.
    """
    sev: dict[str, str] = {}
    status: dict[str, str] = {}
    owner: dict[str, str] = {}
    ids: list[str] = []
    for m in re.finditer(r"\|\s*(SEC-\d+[a-z]?)\s*\|\s*([A-Z]+)", review):
        sev[m.group(1)] = m.group(2)
    for line in handoff.splitlines():
        for m in re.finditer(r"(SEC-\d+[a-z]?)", line):
            sid = m.group(1)
            if sid not in ids:
                ids.append(sid)
            tail = line[m.end(): m.end() + 70].lower()
            sm = re.match(rf"\s*\(?{_SEV}\b", line[m.end():])
            if sm:
                sev[sid] = sm.group(1)
            if re.search(r"\b(fixed|closed|accepted|verified)\b", tail):
                status[sid] = "closed"
            elif re.search(r"\bopen\b", tail) or sm:
                status[sid] = "open"
            om = re.search(r"->\s*([a-z][a-z-]+)", line[m.end(): m.end() + 200])
            if om:
                owner[sid] = om.group(1)
    out = []
    for sid in ids:
        if sid not in status:
            status[sid] = "closed"  # only mentioned in passing; reviewed
        out.append({
            "key": sid,
            "title": f"{sid}: security finding",
            "team": "In-house",
            "lane": "IN",
            "kind": "Security",
            "priority": {"HIGH": "P0", "CRITICAL": "P0", "MED": "P1", "LOW": "P2", "INFO": "P3"}.get(sev.get(sid, ""), "P2"),
            "agent": owner.get(sid, ""),
            "wo": "",
            "release": "",
            "sec_severity": sev.get(sid, "unknown"),
            "sec_status": status[sid],
            "sec_owner": owner.get(sid, "unassigned"),
        })
    return out


def parse_owner_todo(progress: str) -> list[dict]:
    """The Owner TODO line of the latest (last) PROGRESS.md checkpoint."""
    parts = re.split(r"^## CHECKPOINT[^\n]*\n", progress, flags=re.MULTILINE)
    heads = re.findall(r"^## CHECKPOINT ([^\n(]*)", progress, flags=re.MULTILINE)
    if len(parts) < 2:
        return []
    latest = parts[-1]
    stamp = heads[-1].strip() if heads else "latest"
    m = re.search(r"\*\*Owner TODO:?\*\*:?\s*(.*)", latest) or re.search(r"Owner TODO:?\s*(.*)", latest)
    if not m:
        return []
    line = m.group(1).strip()
    out = []
    for i, chunk in enumerate([c.strip(" .") for c in re.split(r";\s+", line) if c.strip(" .")], 1):
        out.append({
            "key": f"OWN-{re.sub(r'[^0-9]', '', stamp)[:8]}-{i:02d}",
            "title": f"Owner task: {chunk[:110]}",
            "team": "In-house",
            "lane": "IN",
            "kind": "Owner task",
            "priority": "P2",
            "agent": "Owner",
            "wo": "",
            "release": "",
            "body_text": chunk,
        })
    return out


# ---------------------------------------------------------------- planning

def issue_body(item: dict, sha: str = "") -> str:
    if item["kind"] == "Security" and item["key"].startswith("SEC-"):
        # Redaction rule: ID, severity, owner, status and a pointer. Nothing else.
        return "\n".join([
            f"ID: {item['key']}",
            f"Severity: {item.get('sec_severity', 'unknown')}",
            f"Owner: {item.get('sec_owner', 'unassigned')}",
            f"Status: {item.get('sec_status', 'open')}",
            SEC_POINTER,
        ])
    lines = [f"Tracked item: {item['key']}", f"Team: {item['team']}  Lane: {item['lane']}"]
    if item.get("agent"):
        lines.append(f"Agent: {item['agent']}")
    if item.get("source"):
        lines.append(f"Source: {item['source']}")
    if item.get("file"):
        lines.append(f"File: {item['file']}")
    if item.get("allowed_paths"):
        lines.append("Allowed paths:")
        lines += [f"- {p}" for p in item["allowed_paths"]]
    if item.get("body_text"):
        lines.append(item["body_text"])
    if sha:
        lines.append(f"Merged: {sha}")
    lines.append("The local file is the source of truth; this issue is a mirror (docs/SDLC.md).")
    return "\n".join(lines)


def labels_for(item: dict) -> list[str]:
    slug = lambda s: s.lower().replace(" ", "-")
    out = [f"team:{slug(item['team'])}", f"kind:{slug(item['kind'])}",
           f"lane:{item['lane'].lower()}", f"priority:{item['priority'].lower()}"]
    return out


def collect(root: Path = ROOT, git_log: str | None = None) -> list[dict]:
    if git_log is None:
        git_log = subprocess.run(
            ["git", "-C", str(root), "log", "--format=%H %s", "--grep", "Merge WO-"],
            capture_output=True, text=True, check=True,
        ).stdout
    merged = merged_wos(git_log)
    items: list[dict] = []
    for p in sorted((root / "docs" / "vendor").glob("WO-[0-9][0-9][0-9].md")):
        it = parse_wo(p)
        sha = merged.get(it["key"], "")
        it["merge_sha"] = sha
        it["project_status"] = wo_status_to_field(it["wo_status"], bool(sha))
        it["closed"] = it["project_status"] == "Done"
        items.append(it)
    bl = root / "docs" / "BACKLOG.md"
    if bl.exists():
        for it in parse_backlog(bl.read_text(encoding="utf-8")):
            if it["key"].startswith(("CX-", "CP-")):  # these became WO-127..150: no duplicates
                continue
            it.update(project_status="Backlog", closed=False, merge_sha="")
            items.append(it)
    # SEC findings and owner tasks come from the curated docs/pm/tracked.json: the narrative
    # handoff is too loose to parse statuses from (wrong open/closed guesses), and owner-task keys
    # must stay stable across checkpoints.
    tp = root / "docs" / "pm" / "tracked.json"
    if tp.exists():
        tracked = json.loads(tp.read_text(encoding="utf-8"))
        for s in tracked.get("security", []):
            closed = s.get("status") == "closed"
            items.append({
                "key": s["id"], "title": f"{s['id']}: security finding", "team": "In-house",
                "lane": "IN", "kind": "Security",
                "priority": {"HIGH": "P0", "MED": "P1", "LOW": "P2"}.get(s.get("severity", ""), "P3"),
                "agent": s.get("owner", ""), "wo": "", "release": "",
                "sec_severity": s.get("severity", ""), "sec_owner": s.get("owner", ""),
                "sec_status": s.get("status", "open"),
                "project_status": "Done" if closed else {
                    "in progress": "In progress", "in review": "In review",
                }.get(s.get("status", ""), "Ready"),
                "closed": closed, "merge_sha": "",
            })
        for o in tracked.get("owner_tasks", []):
            done = bool(o.get("done"))
            items.append({
                "key": o["key"], "title": f"Owner task: {o['title'][:110]}", "team": "In-house",
                "lane": "IN", "kind": "Owner task", "priority": "P2", "agent": "Owner", "wo": "",
                "release": "", "body_text": o["title"],
                "project_status": "Done" if done else "Ready", "closed": done, "merge_sha": "",
            })
    return items


def load_map(path: Path = MAP_PATH) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"repo": DEFAULT_REPO, "items": {}}


def save_map(data: dict, path: Path = MAP_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def plan(items: list[dict], mapping: dict) -> list[dict]:
    """Idempotent plan: an item already in the map is never created again."""
    seen: set[str] = set()
    out = []
    for it in items:
        key = it["key"]
        if key in seen:  # duplicate key in sources: first wins
            continue
        seen.add(key)
        rec = mapping.get("items", {}).get(key)
        if rec and rec.get("number"):
            want_closed = it["closed"]
            if want_closed and rec.get("state") != "closed":
                action = "close"
            elif not want_closed and rec.get("state") == "closed":
                action = "reopen"
            else:
                action = "none"
        else:
            action = "create"
        out.append({
            "key": key, "action": action, "number": (rec or {}).get("number"),
            "title": it["title"], "labels": labels_for(it),
            "body": issue_body(it, it.get("merge_sha", "")),
            "close": it["closed"], "merge_sha": it.get("merge_sha", ""),
            "milestone": it.get("release", ""),
            "fields": {
                "Status": it["project_status"], "Team": it["team"], "Lane": it["lane"],
                "Kind": it["kind"], "Priority": it["priority"],
                "Agent": it.get("agent", ""), "WO": it.get("wo", ""),
                "Release": it.get("release", ""),
            },
        })
    return out


def summarize(p: list[dict]) -> dict:
    return {
        "total": len(p),
        "by_action": dict(Counter(x["action"] for x in p)),
        "by_team": dict(Counter(x["fields"]["Team"] for x in p)),
        "by_kind": dict(Counter(x["fields"]["Kind"] for x in p)),
        "by_team_kind": dict(Counter(f"{x['fields']['Team']}/{x['fields']['Kind']}" for x in p)),
        "closing": sum(1 for x in p if x["close"]),
    }


# ---------------------------------------------------------------- apply

def default_runner(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


def check_gate(env: dict | None = None) -> None:
    e = os.environ if env is None else env
    if e.get("FREEMYID_PM_APPLY") != "1":
        raise ApplyRefused("--apply refused: set FREEMYID_PM_APPLY=1 to confirm GitHub writes")


def _json(run, args):
    return json.loads(run(args) or "{}")


def apply_plan(p: list[dict], mapping: dict, repo: str, owner: str, project: int | None,
               run=default_runner, env: dict | None = None) -> dict:
    """Create/close issues and set project fields. Gate is checked first."""
    check_gate(env)
    items = mapping.setdefault("items", {})
    fields = {}
    proj_id = ""
    if project is not None:
        proj_id = _json(run, ["gh", "project", "view", str(project), "--owner", owner, "--format", "json"])["id"]
        for f in _json(run, ["gh", "project", "field-list", str(project), "--owner", owner, "--format", "json"])["fields"]:
            fields[f["name"]] = f
    for x in p:
        rec = items.get(x["key"], {})
        if x["action"] == "create":
            # Codex can open issues itself now (GitHub plugin): adopt an existing "KEY: ..." issue
            # instead of making a duplicate.
            found = _json(run, ["gh", "issue", "list", "--repo", repo, "--state", "all", "--search",
                                f'"{x["key"]}" in:title', "--json", "number,title,url,state"])
            hit = next((i for i in found if i["title"].startswith(x["key"] + ":")), None)
            if hit:
                rec = {"number": hit["number"], "url": hit["url"], "state": hit["state"].lower()}
                items[x["key"]] = rec
                x = {**x, "action": "adopted"}
        if x["action"] == "create":
            cmd = ["gh", "issue", "create", "--repo", repo, "--title", x["title"], "--body", x["body"]]
            for lab in x["labels"]:
                cmd += ["--label", lab]
            if x["milestone"]:
                cmd += ["--milestone", x["milestone"]]
            url = run(cmd).strip().splitlines()[-1]
            m = re.search(r"/issues/(\d+)$", url)
            rec = {"number": int(m.group(1)) if m else None, "url": url, "state": "open"}
            items[x["key"]] = rec
            if project is not None:
                add = _json(run, ["gh", "project", "item-add", str(project), "--owner", owner,
                                  "--url", url, "--format", "json"])
                rec["project_item"] = add.get("id", "")
        if x["action"] in ("create", "close", "adopted") and x["close"] and rec.get("number"):
            cmd = ["gh", "issue", "close", str(rec["number"]), "--repo", repo]
            if x["merge_sha"]:
                cmd += ["--comment", f"Merged locally as {x['merge_sha']}."]
            run(cmd)
            rec["state"] = "closed"
        elif x["action"] == "reopen" and rec.get("number"):
            run(["gh", "issue", "reopen", str(rec["number"]), "--repo", repo])
            rec["state"] = "open"
        if project is not None and rec.get("url") and not rec.get("project_item"):
            # issues created before the board existed (or by an earlier run) join it here
            add = _json(run, ["gh", "project", "item-add", str(project), "--owner", owner,
                              "--url", rec["url"], "--format", "json"])
            rec["project_item"] = add.get("id", "")
        if project is not None and rec.get("project_item"):
            last = rec.setdefault("fields", {})
            for name, val in x["fields"].items():
                f = fields.get(name)
                if not f or val == "" or last.get(name) == val:
                    continue  # unchanged since the last sync: no API call
                cmd = ["gh", "project", "item-edit", "--id", rec["project_item"],
                       "--project-id", proj_id, "--field-id", f["id"]]
                if f.get("options"):
                    opt = next((o["id"] for o in f["options"] if o["name"] == val), None)
                    if not opt:
                        continue
                    cmd += ["--single-select-option-id", opt]
                else:
                    cmd += ["--text", val]
                run(cmd)
                last[name] = val
    return mapping


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", help="print the plan, no network (default)")
    g.add_argument("--apply", action="store_true", help="write to GitHub (needs FREEMYID_PM_APPLY=1)")
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--owner", default=DEFAULT_OWNER)
    ap.add_argument("--project", type=int, default=None, help="Project v2 number")
    ap.add_argument("--summary", action="store_true", help="print only the counts")
    a = ap.parse_args(argv)
    mapping = load_map()
    p = plan(collect(), mapping)
    if a.apply:
        try:
            check_gate()
        except ApplyRefused as e:
            print(str(e), file=sys.stderr)
            return 2
        mapping["repo"] = a.repo
        save_map(apply_plan(p, mapping, a.repo, a.owner, a.project, env=None))
        print(json.dumps(summarize(p), indent=2))
        return 0
    out = {"mode": "dry-run", "repo": a.repo, "summary": summarize(p)}
    if not a.summary:
        out["plan"] = p
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
