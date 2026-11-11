"""Keep the public broker-guide file and line citations in range.

The guide uses backticked ``path:start-end,start`` references. Its current
public targets are ``schema/registry.schema.json`` and
``brokers/registry.sample.yaml``; private or research references are out of
scope for this check.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs/dev/CONTRIBUTING_BROKERS.md"
TARGETS = (
    "schema/registry.schema.json",
    "brokers/registry.sample.yaml",
)
RANGE_LIST = re.compile(r"\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*\Z")


@pytest.mark.parametrize("target", TARGETS)
def test_broker_guide_public_citations_are_in_bounds(target: str) -> None:
    guide = GUIDE.read_text(encoding="utf-8")
    target_file = ROOT / target
    assert target_file.is_file(), f"Cited public file does not exist: {target}"
    line_count = len(target_file.read_text(encoding="utf-8").splitlines())

    # Limit parsing to the guide's existing backticked path:range syntax.
    citations = [citation for citation in re.findall(r"`([^`\n]+)`", guide) if target in citation]
    assert citations, f"No citation found for {target}"

    for citation in citations:
        assert citation.startswith(target + ":"), (
            f"Malformed citation for {target}: `{citation}`"
        )
        ranges = citation.removeprefix(target + ":")
        assert RANGE_LIST.fullmatch(ranges), f"Malformed line range for {target}: `{citation}`"
        for item in ranges.split(","):
            start_text, separator, end_text = item.partition("-")
            start = int(start_text)
            end = int(end_text) if separator else start
            assert start >= 1 and end >= start, (
                f"Invalid line range for {target}: {item}"
            )
            assert end <= line_count, (
                f"Citation {target}:{item} exceeds {line_count} lines"
            )

