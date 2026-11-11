"""Static selection stays bounded on large synthetic pages, without timing assertions."""
from __future__ import annotations

import pytest

from freemyid.engine import htmlsel


def test_five_megabyte_page_keeps_last_element_searchable() -> None:
    # Stay below MAX_NODES so this checks the complete input, rather than a capped prefix.
    chunk = '<p class="filler">' + "x" * 200 + "</p>"
    page = "<main>" + chunk * 25_000 + '<span id="last">end marker</span></main>'
    assert len(page.encode("ascii")) >= 5 * 1024 * 1024
    root = htmlsel.parse(page)
    assert len(root.iter()) == 25_002
    last = root.select_one("#last")
    assert last is not None and last.text() == "end marker"
    assert root.select(".missing") == []


@pytest.mark.parametrize("length", [10, 75, 150])
def test_deep_page_long_descendant_chain_has_linear_match_bound(
    monkeypatch: pytest.MonkeyPatch, length: int,
) -> None:
    # Existing SEC-92 covers short selectors on deep pages; this stresses near-limit chains.
    root = htmlsel.parse("<b>" * 2000 + "deep marker" + "</b>" * 2000)
    nodes = root.iter()
    assert len(nodes) == htmlsel.MAX_DEPTH
    assert root.text() == "deep marker"
    calls = 0
    original = htmlsel._Compound.matches

    def counting(compound: htmlsel._Compound, node: htmlsel.Node) -> bool:
        nonlocal calls
        calls += 1
        return original(compound, node)

    monkeypatch.setattr(htmlsel._Compound, "matches", counting)
    result = root.select(" ".join(["b"] * length))
    assert len(result) == htmlsel.MAX_DEPTH - length + 1
    # At most one compound evaluation per (node, chain index), including failed paths.
    assert 0 < calls <= len(nodes) * length


@pytest.mark.parametrize("groups", [5, 25, 50])
def test_repeated_failing_groups_have_bounded_compound_work(
    monkeypatch: pytest.MonkeyPatch, groups: int,
) -> None:
    root = htmlsel.parse("<b>" * 2000 + "marker" + "</b>" * 2000)
    calls = 0
    original = htmlsel._Compound.matches

    def counting(compound: htmlsel._Compound, node: htmlsel.Node) -> bool:
        nonlocal calls
        calls += 1
        return original(compound, node)

    monkeypatch.setattr(htmlsel._Compound, "matches", counting)
    # Repeated ancestor alternatives formerly risked exponential exploration.
    selector = ",".join(["a b b"] * groups)
    assert len(selector) <= 300
    assert root.select(selector) == []
    assert 0 < calls <= len(root.iter()) * 3 * groups


@pytest.mark.parametrize("selector", ["a," * 2000, "b " * 2000, ".x" * 2000])
def test_oversize_hostile_selector_is_rejected_before_tree_walk(
    monkeypatch: pytest.MonkeyPatch, selector: str,
) -> None:
    root = htmlsel.parse("<b>marker</b>")

    def forbidden_walk(node: htmlsel.Node) -> list[htmlsel.Node]:
        pytest.fail("oversize selector must be refused before visiting the page")

    monkeypatch.setattr(htmlsel.Node, "iter", forbidden_walk)
    with pytest.raises(htmlsel.UnsupportedSelector, match="empty_or_long"):
        root.select(selector)
