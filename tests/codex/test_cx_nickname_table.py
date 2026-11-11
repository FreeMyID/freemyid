"""Check every nickname group against the direct-membership lookup contract."""
from __future__ import annotations

from itertools import product

import pytest

from freemyid.engine import nicknames

ALL_NAMES = sorted({name for group in nicknames.GROUPS for name in group})


def test_table_has_unique_formal_names() -> None:
    assert nicknames.GROUPS, "The nickname table must contain groups"
    assert all(nicknames.GROUPS), "Every group must contain a formal name"
    formal_names = [group[0] for group in nicknames.GROUPS]
    assert len(formal_names) == len(set(formal_names))


@pytest.mark.parametrize("group", nicknames.GROUPS)
def test_each_group_has_distinct_normalized_ascii_names(group: tuple[str, ...]) -> None:
    assert len(group) >= 2
    assert len(group) == len(set(group)), group
    for name in group:
        assert name == name.strip(), (group, name)
        assert name.isascii() and name.isalpha() and name.islower(), (group, name)


@pytest.mark.parametrize("group", nicknames.GROUPS)
def test_every_pair_in_each_group_expands_in_both_directions(group: tuple[str, ...]) -> None:
    for left, right in product(group, repeat=2):
        assert right in nicknames.expand(left), (group, left, right)
        assert left in nicknames.expand(right), (group, right, left)


@pytest.mark.parametrize("name", ALL_NAMES)
def test_expansion_is_exactly_direct_group_membership(name: str) -> None:
    expected = {
        member for group in nicknames.GROUPS if name in group for member in group
    }

    assert name in nicknames.expand(name)
    assert nicknames.expand(name) == expected
    assert nicknames.expand(f"  {name} ") == expected


@pytest.mark.parametrize("name", ALL_NAMES)
def test_groups_of_reports_only_direct_formal_names(name: str) -> None:
    expected = frozenset(group[0] for group in nicknames.GROUPS if name in group)

    assert nicknames.groups_of(name) == expected
    assert nicknames.groups_of(f"  {name} ") == expected


@pytest.mark.parametrize("name", ["", " ", "\t\n"])
def test_blank_names_have_no_expansion_or_groups(name: str) -> None:
    assert nicknames.expand(name) == set()
    assert nicknames.groups_of(name) == frozenset()


def test_unknown_name_expands_only_to_itself() -> None:
    unknown = "syntheticunknownname"
    assert unknown not in ALL_NAMES
    assert nicknames.expand(unknown) == {unknown}
    assert nicknames.expand(f"  {unknown} ") == {unknown}
    assert nicknames.groups_of(unknown) == frozenset()
