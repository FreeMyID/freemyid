"""tools/coderabbit_findings.py: parse, dedupe and render CodeRabbit comments (offline)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

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
