"""tools/coderabbit_findings.py: parse, dedupe and render CodeRabbit comments (offline)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("crf", ROOT / "tools" / "coderabbit_findings.py")
crf = importlib.util.module_from_spec(_spec)
sys.modules["crf"] = crf
_spec.loader.exec_module(crf)

ICON = ('<picture><img src="https://example.invalid/major-16.svg" width="16" height="16" '
        'align="absmiddle" alt=""></picture> ')


def _c(path="src/x.py", line=10, sev="Major", title="Preserve the state.", login="coderabbitai[bot]",
       url="https://github.com/o/r/pull/1#discussion_r1"):
    body = (f"<!-- coderabbit-ai-generated:v1 -->\n\n**{ICON}{sev}** · **Data** · **Quick win**\n\n"
            f"**{title}**\n\nExplanation text.\n<details>hidden prompt</details>")
    return {"user": {"login": login}, "path": path, "line": line, "body": body, "html_url": url}


def test_parse_reads_severity_title_and_location():
    f = crf.parse_comment(_c(), 61)
    assert (f.path, f.line, f.severity, f.title, f.prs) == (
        "src/x.py", 10, "Major", "Preserve the state.", [61])


def test_non_bot_comments_are_ignored():
    assert crf.parse_comment(_c(login="a-human"), 61) is None


def test_hidden_details_never_become_the_title():
    c = _c()
    c["body"] = "<details>**Not this**</details>"
    f = crf.parse_comment(c, 1)
    assert f is not None and "Not this" not in f.title


def test_duplicates_across_prs_merge_and_sort_by_severity():
    rows = [crf.parse_comment(_c(sev="Minor", title="Small thing.", path="a.py", line=1), 55),
            crf.parse_comment(_c(), 57),
            crf.parse_comment(_c(url="https://github.com/o/r/pull/2#discussion_r2"), 60)]
    merged = crf.merge(rows)
    assert [f.severity for f in merged] == ["Major", "Minor"]
    assert merged[0].prs == [57, 60] and len(merged[0].urls) == 2


def test_render_has_one_row_per_unique_finding_and_escapes_pipes():
    merged = crf.merge([crf.parse_comment(_c(title="Use a | b."), 61)])
    out = crf.render(merged, [61])
    assert "1 unique (1 Major)" in out
    assert "Use a \\| b." in out and out.count("\n| 1 |") == 1


def test_original_line_is_used_when_line_is_missing():
    c = _c()
    c["line"] = None
    c["original_line"] = 42
    assert crf.parse_comment(c, 1).line == 42


def test_html_comments_never_become_the_title():
    c = _c()
    c["body"] = "<!-- coderabbit-ai-generated:v1 -->\n\n_Major_\n\nKeep the to-do and status consistent.\n"
    assert crf.parse_comment(c, 1).title == "Keep the to-do and status consistent."


def test_title_after_a_collapsed_block_is_found():
    c = _c()
    c["body"] = (f"**{ICON}Major** · **Data**\n\n<details><summary>Static analysis</summary>"
                 "<details>inner</details>**Hidden**</details>\n\n**Keep it consistent.**\n")
    assert crf.parse_comment(c, 1).title == "Keep it consistent."


def test_only_the_exact_coderabbit_app_login_is_trusted():
    for login in ("coderabbit-reviewer", "CodeRabbitAI", "coderabbitai", "evil-coderabbitai[bot]"):
        assert crf.parse_comment(_c(login=login), 61) is None, login


def test_merge_keeps_the_highest_severity_when_a_finding_is_escalated():
    merged = crf.merge([crf.parse_comment(_c(sev="Minor"), 61),
                        crf.parse_comment(_c(sev="Major", url="https://x.invalid/2"), 61)])
    assert len(merged) == 1 and merged[0].severity == "Major"


def _fake_gh(monkeypatch, responses):
    """Offline gh: maps the endpoint argument to the JSON text gh would print."""
    calls = []

    def fake(args):
        calls.append(args)
        assert args[:3] == ["api", "--paginate", "--slurp"], args
        return responses[args[3]]
    monkeypatch.setattr(crf, "_gh", fake)
    return calls


def test_fetch_flattens_slurped_pages_without_editing_the_text(monkeypatch):
    c1, c2 = _c(title="Watch ][ this."), _c(path="b.py", title="Second page.")
    _fake_gh(monkeypatch, {"repos/o/r/pulls/7/comments?per_page=100":
                           json.dumps([[c1], [c2]], indent=1)})
    got = crf.fetch(7, "o/r")
    assert [g["path"] for g in got] == ["src/x.py", "b.py"]
    assert got[0]["body"] == c1["body"]  # "][" inside a body is untouched


def test_fetch_of_an_empty_response_is_empty(monkeypatch):
    _fake_gh(monkeypatch, {"repos/o/r/pulls/7/comments?per_page=100": ""})
    assert crf.fetch(7, "o/r") == []


def test_open_prs_reads_every_page(monkeypatch):
    pages = [[{"number": n} for n in range(1, 101)], [{"number": 101}, {"number": 102}]]
    _fake_gh(monkeypatch, {"repos/o/r/pulls?state=open&per_page=100": json.dumps(pages)})
    assert crf.open_prs("o/r") == list(range(1, 103))


def test_main_open_writes_the_checklist_to_out(monkeypatch, tmp_path, capsys):
    _fake_gh(monkeypatch, {
        "repos/o/r/pulls?state=open&per_page=100": json.dumps([[{"number": 5}]]),
        "repos/o/r/pulls/5/comments?per_page=100": json.dumps([[_c()], [_c(login="a-human")]]),
        "repos/o/r/pulls/9/comments?per_page=100": json.dumps([[]]),
    })
    out = tmp_path / "list.md"
    assert crf.main(["9", "--open", "--repo", "o/r", "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# CodeRabbit findings: PR #5, #9")
    assert "1 unique (1 Major)" in text and "Preserve the state." in text
    assert f"wrote {out}" in capsys.readouterr().out


def test_main_without_prs_is_a_usage_error(monkeypatch):
    _fake_gh(monkeypatch, {})
    with pytest.raises(SystemExit) as e:
        crf.main([])
    assert e.value.code == 2


def test_escalated_row_links_to_the_escalating_comment():
    minor = crf.parse_comment(_c(sev="Minor", url="https://github.com/o/r/pull/1#discussion_r1"), 1)
    major = crf.parse_comment(_c(sev="Major", url="https://github.com/o/r/pull/2#discussion_r2"), 2)
    [row] = crf.merge([minor, major])
    assert row.severity == "Major" and row.urls[0].endswith("discussion_r2")


def test_unrated_duplicate_stays_visible():
    rated = crf.parse_comment(_c(sev="Minor"), 1)
    unrated = crf.parse_comment(_c(sev="Minor"), 2)
    unrated.severity = "Unrated"
    [row] = crf.merge([rated, unrated])
    assert row.unrated_dup and "Unrated" in crf.render([row], [1, 2])
