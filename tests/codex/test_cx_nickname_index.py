"""Frozen pre-WO-286 expansion sets and deterministic index-operation bounds.

The public return type remains a set: selected membership is deterministic, iteration
order is deliberately not part of this API. Names are public nickname-table tokens.
"""
from __future__ import annotations

from collections.abc import Iterator

import pytest

from freemyid.engine import nicknames

# Captured from the unmodified module before this WO; not computed by the implementation.
GOLDEN = {'abby': ['abby', 'abigail', 'gail'],
 'abigail': ['abby', 'abigail', 'gail'],
 'al': ['al', 'albert', 'alex', 'alexander', 'alf', 'alfred', 'bert', 'fred', 'sandy'],
 'albert': ['al', 'albert', 'bert'],
 'alex': ['al', 'alex', 'alexander', 'alexandra', 'lexi', 'sandra', 'sandy'],
 'alexander': ['al', 'alex', 'alexander', 'sandy'],
 'alexandra': ['alex', 'alexandra', 'lexi', 'sandra', 'sandy'],
 'alf': ['al', 'alf', 'alfred', 'fred'],
 'alfred': ['al', 'alf', 'alfred', 'fred'],
 'andrew': ['andrew', 'andy', 'drew'],
 'andy': ['andrew', 'andy', 'drew'],
 'anthony': ['anthony', 'tony'],
 'babs': ['babs', 'barb', 'barbara', 'barbie'],
 'barb': ['babs', 'barb', 'barbara', 'barbie'],
 'barbara': ['babs', 'barb', 'barbara', 'barbie'],
 'barbie': ['babs', 'barb', 'barbara', 'barbie'],
 'becca': ['becca', 'becky', 'rebecca'],
 'becky': ['becca', 'becky', 'rebecca'],
 'ben': ['ben', 'benjamin', 'benji', 'benny'],
 'benjamin': ['ben', 'benjamin', 'benji', 'benny'],
 'benji': ['ben', 'benjamin', 'benji', 'benny'],
 'benny': ['ben', 'benjamin', 'benji', 'benny'],
 'bert': ['al', 'albert', 'bert', 'bob', 'bobby', 'rob', 'robbie', 'robert'],
 'beth': ['beth', 'betsy', 'betty', 'eliza', 'elizabeth', 'libby', 'lisa', 'liz', 'lizzie'],
 'betsy': ['beth', 'betsy', 'betty', 'eliza', 'elizabeth', 'libby', 'lisa', 'liz', 'lizzie'],
 'betty': ['beth', 'betsy', 'betty', 'eliza', 'elizabeth', 'libby', 'lisa', 'liz', 'lizzie'],
 'bill': ['bill', 'billy', 'liam', 'will', 'william', 'willy'],
 'billy': ['bill', 'billy', 'liam', 'will', 'william', 'willy'],
 'bob': ['bert', 'bob', 'bobby', 'rob', 'robbie', 'robert'],
 'bobby': ['bert', 'bob', 'bobby', 'rob', 'robbie', 'robert'],
 'cat': ['cat', 'catherine', 'cathy', 'kate', 'katie'],
 'catherine': ['cat', 'catherine', 'cathy', 'kate', 'katie'],
 'cathy': ['cat', 'catherine', 'cathy', 'kate', 'katie'],
 'charles': ['charles', 'charlie', 'chas', 'chuck'],
 'charlie': ['charles', 'charlie', 'chas', 'chuck'],
 'chas': ['charles', 'charlie', 'chas', 'chuck'],
 'chris': ['chris', 'chrissy', 'christina', 'christine', 'christopher', 'kit', 'tina', 'topher'],
 'chrissy': ['chris', 'chrissy', 'christina', 'christine', 'tina'],
 'christina': ['chris', 'chrissy', 'christina', 'tina'],
 'christine': ['chris', 'chrissy', 'christine', 'tina'],
 'christopher': ['chris', 'christopher', 'kit', 'topher'],
 'chuck': ['charles', 'charlie', 'chas', 'chuck'],
 'cindy': ['cindy', 'cynthia'],
 'cynthia': ['cindy', 'cynthia'],
 'dan': ['dan', 'daniel', 'danny'],
 'daniel': ['dan', 'daniel', 'danny'],
 'danny': ['dan', 'daniel', 'danny'],
 'dave': ['dave', 'david', 'davy'],
 'david': ['dave', 'david', 'davy'],
 'davy': ['dave', 'david', 'davy'],
 'deb': ['deb', 'debbie', 'debby', 'deborah'],
 'debbie': ['deb', 'debbie', 'debby', 'deborah'],
 'debby': ['deb', 'debbie', 'debby', 'deborah'],
 'deborah': ['deb', 'debbie', 'debby', 'deborah'],
 'dick': ['dick', 'rich', 'richard', 'rick', 'ricky'],
 'dolly': ['dolly', 'dorothy', 'dot', 'dottie'],
 'don': ['don', 'donald', 'donnie'],
 'donald': ['don', 'donald', 'donnie'],
 'donnie': ['don', 'donald', 'donnie'],
 'dorothy': ['dolly', 'dorothy', 'dot', 'dottie'],
 'dot': ['dolly', 'dorothy', 'dot', 'dottie'],
 'dottie': ['dolly', 'dorothy', 'dot', 'dottie'],
 'doug': ['doug', 'douglas'],
 'douglas': ['doug', 'douglas'],
 'drew': ['andrew', 'andy', 'drew'],
 'ed': ['ed', 'eddie', 'edward', 'ned', 'ted'],
 'eddie': ['ed', 'eddie', 'edward', 'ned', 'ted'],
 'edward': ['ed', 'eddie', 'edward', 'ned', 'ted'],
 'eleanor': ['eleanor', 'ellie', 'nell', 'nora'],
 'eliza': ['beth', 'betsy', 'betty', 'eliza', 'elizabeth', 'libby', 'lisa', 'liz', 'lizzie'],
 'elizabeth': ['beth', 'betsy', 'betty', 'eliza', 'elizabeth', 'libby', 'lisa', 'liz', 'lizzie'],
 'ellie': ['eleanor', 'ellie', 'nell', 'nora'],
 'eugene': ['eugene', 'gene'],
 'fran': ['fran', 'frances', 'frannie'],
 'frances': ['fran', 'frances', 'frannie'],
 'francis': ['francis', 'frank'],
 'frank': ['francis', 'frank', 'franklin'],
 'franklin': ['frank', 'franklin'],
 'frannie': ['fran', 'frances', 'frannie'],
 'fred': ['al', 'alf', 'alfred', 'fred', 'freddie', 'frederick'],
 'freddie': ['fred', 'freddie', 'frederick'],
 'frederick': ['fred', 'freddie', 'frederick'],
 'gail': ['abby', 'abigail', 'gail'],
 'gene': ['eugene', 'gene'],
 'gerald': ['gerald', 'gerry', 'jerry'],
 'gerry': ['gerald', 'gerry', 'jerry'],
 'ginger': ['ginger', 'ginny', 'virginia'],
 'ginny': ['ginger', 'ginny', 'virginia'],
 'greg': ['greg', 'gregory'],
 'gregory': ['greg', 'gregory'],
 'greta': ['greta', 'maggie', 'margaret', 'marge', 'margie', 'meg', 'peggy'],
 'hal': ['hal', 'harold', 'harry'],
 'hank': ['hank', 'harry', 'henry'],
 'harold': ['hal', 'harold', 'harry'],
 'harry': ['hal', 'hank', 'harold', 'harry', 'henry'],
 'henry': ['hank', 'harry', 'henry'],
 'jack': ['jack', 'john', 'johnny'],
 'jacob': ['jacob', 'jake'],
 'jake': ['jacob', 'jake'],
 'james': ['james', 'jamie', 'jim', 'jimmy'],
 'jamie': ['james', 'jamie', 'jim', 'jimmy'],
 'jan': ['jan', 'janet'],
 'janet': ['jan', 'janet'],
 'jeff': ['jeff', 'jeffrey'],
 'jeffrey': ['jeff', 'jeffrey'],
 'jen': ['jen', 'jenn', 'jennifer', 'jenny'],
 'jenn': ['jen', 'jenn', 'jennifer', 'jenny'],
 'jennifer': ['jen', 'jenn', 'jennifer', 'jenny'],
 'jenny': ['jen', 'jenn', 'jennifer', 'jenny'],
 'jerry': ['gerald', 'gerry', 'jerry'],
 'jess': ['jess', 'jessica', 'jessie'],
 'jessica': ['jess', 'jessica', 'jessie'],
 'jessie': ['jess', 'jessica', 'jessie'],
 'jim': ['james', 'jamie', 'jim', 'jimmy'],
 'jimmy': ['james', 'jamie', 'jim', 'jimmy'],
 'jo': ['jo', 'josephine', 'josie'],
 'joe': ['joe', 'joey', 'joseph'],
 'joey': ['joe', 'joey', 'joseph'],
 'john': ['jack', 'john', 'johnny', 'jon', 'jonathan'],
 'johnny': ['jack', 'john', 'johnny'],
 'jon': ['john', 'jon', 'jonathan'],
 'jonathan': ['john', 'jon', 'jonathan'],
 'joseph': ['joe', 'joey', 'joseph'],
 'josephine': ['jo', 'josephine', 'josie'],
 'josh': ['josh', 'joshua'],
 'joshua': ['josh', 'joshua'],
 'josie': ['jo', 'josephine', 'josie'],
 'judith': ['judith', 'judy'],
 'judy': ['judith', 'judy'],
 'kat': ['kat', 'kate', 'katherine', 'kathy', 'katie', 'kay', 'kitty'],
 'kate': ['cat',
          'catherine',
          'cathy',
          'kat',
          'kate',
          'katherine',
          'kathleen',
          'kathy',
          'katie',
          'kay',
          'kitty'],
 'katherine': ['kat', 'kate', 'katherine', 'kathy', 'katie', 'kay', 'kitty'],
 'kathleen': ['kate', 'kathleen', 'kathy', 'katie'],
 'kathy': ['kat', 'kate', 'katherine', 'kathleen', 'kathy', 'katie', 'kay', 'kitty'],
 'katie': ['cat',
           'catherine',
           'cathy',
           'kat',
           'kate',
           'katherine',
           'kathleen',
           'kathy',
           'katie',
           'kay',
           'kitty'],
 'kay': ['kat', 'kate', 'katherine', 'kathy', 'katie', 'kay', 'kitty'],
 'ken': ['ken', 'kenneth', 'kenny'],
 'kenneth': ['ken', 'kenneth', 'kenny'],
 'kenny': ['ken', 'kenneth', 'kenny'],
 'kit': ['chris', 'christopher', 'kit', 'topher'],
 'kitty': ['kat', 'kate', 'katherine', 'kathy', 'katie', 'kay', 'kitty'],
 'larry': ['larry', 'lawrence'],
 'lawrence': ['larry', 'lawrence'],
 'len': ['len', 'lenny', 'leo', 'leonard'],
 'lenny': ['len', 'lenny', 'leo', 'leonard'],
 'leo': ['len', 'lenny', 'leo', 'leonard'],
 'leonard': ['len', 'lenny', 'leo', 'leonard'],
 'lexi': ['alex', 'alexandra', 'lexi', 'sandra', 'sandy'],
 'liam': ['bill', 'billy', 'liam', 'will', 'william', 'willy'],
 'libby': ['beth', 'betsy', 'betty', 'eliza', 'elizabeth', 'libby', 'lisa', 'liz', 'lizzie'],
 'lisa': ['beth', 'betsy', 'betty', 'eliza', 'elizabeth', 'libby', 'lisa', 'liz', 'lizzie'],
 'liz': ['beth', 'betsy', 'betty', 'eliza', 'elizabeth', 'libby', 'lisa', 'liz', 'lizzie'],
 'lizzie': ['beth', 'betsy', 'betty', 'eliza', 'elizabeth', 'libby', 'lisa', 'liz', 'lizzie'],
 'lou': ['lou', 'louis'],
 'louis': ['lou', 'louis'],
 'maggie': ['greta', 'maggie', 'margaret', 'marge', 'margie', 'meg', 'peggy'],
 'margaret': ['greta', 'maggie', 'margaret', 'marge', 'margie', 'meg', 'peggy'],
 'marge': ['greta', 'maggie', 'margaret', 'marge', 'margie', 'meg', 'peggy'],
 'margie': ['greta', 'maggie', 'margaret', 'marge', 'margie', 'meg', 'peggy'],
 'matt': ['matt', 'matthew'],
 'matthew': ['matt', 'matthew'],
 'meg': ['greta', 'maggie', 'margaret', 'marge', 'margie', 'meg', 'peggy'],
 'michael': ['michael', 'mick', 'mike', 'mikey'],
 'mick': ['michael', 'mick', 'mike', 'mikey'],
 'mike': ['michael', 'mick', 'mike', 'mikey'],
 'mikey': ['michael', 'mick', 'mike', 'mikey'],
 'ned': ['ed', 'eddie', 'edward', 'ned', 'ted'],
 'nell': ['eleanor', 'ellie', 'nell', 'nora'],
 'nicholas': ['nicholas', 'nick', 'nicky'],
 'nick': ['nicholas', 'nick', 'nicky'],
 'nicky': ['nicholas', 'nick', 'nicky'],
 'nora': ['eleanor', 'ellie', 'nell', 'nora'],
 'paddy': ['paddy', 'pat', 'patrick'],
 'pam': ['pam', 'pamela'],
 'pamela': ['pam', 'pamela'],
 'pat': ['paddy', 'pat', 'patricia', 'patrick', 'patty', 'tricia', 'trish'],
 'patricia': ['pat', 'patricia', 'patty', 'tricia', 'trish'],
 'patrick': ['paddy', 'pat', 'patrick'],
 'patty': ['pat', 'patricia', 'patty', 'tricia', 'trish'],
 'peggy': ['greta', 'maggie', 'margaret', 'marge', 'margie', 'meg', 'peggy'],
 'pete': ['pete', 'peter'],
 'peter': ['pete', 'peter'],
 'phil': ['phil', 'philip'],
 'philip': ['phil', 'philip'],
 'rebecca': ['becca', 'becky', 'rebecca'],
 'rich': ['dick', 'rich', 'richard', 'rick', 'ricky'],
 'richard': ['dick', 'rich', 'richard', 'rick', 'ricky'],
 'rick': ['dick', 'rich', 'richard', 'rick', 'ricky'],
 'ricky': ['dick', 'rich', 'richard', 'rick', 'ricky'],
 'rob': ['bert', 'bob', 'bobby', 'rob', 'robbie', 'robert'],
 'robbie': ['bert', 'bob', 'bobby', 'rob', 'robbie', 'robert'],
 'robert': ['bert', 'bob', 'bobby', 'rob', 'robbie', 'robert'],
 'ron': ['ron', 'ronald', 'ronnie'],
 'ronald': ['ron', 'ronald', 'ronnie'],
 'ronnie': ['ron', 'ronald', 'ronnie'],
 'sam': ['sam', 'samantha', 'sammy', 'samuel'],
 'samantha': ['sam', 'samantha', 'sammy'],
 'sammy': ['sam', 'samantha', 'sammy', 'samuel'],
 'samuel': ['sam', 'sammy', 'samuel'],
 'sandra': ['alex', 'alexandra', 'lexi', 'sandra', 'sandy']}


@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_captured_expansion_sets(name: str) -> None:
    assert nicknames.expand(name) == set(GOLDEN[name])


def test_index_builds_once_across_one_thousand_lookups(monkeypatch: pytest.MonkeyPatch) -> None:
    class CountingGroups(tuple[tuple[str, ...], ...]):
        iterations = 0

        def __iter__(self) -> Iterator[tuple[str, ...]]:
            self.iterations += 1
            return super().__iter__()

    groups = CountingGroups(nicknames.GROUPS)
    nicknames._index.cache_clear()
    try:
        with monkeypatch.context() as patch:
            patch.setattr(nicknames, "GROUPS", groups)
            for index in range(1000):
                name = tuple(GOLDEN)[index % len(GOLDEN)]
                assert nicknames.expand(name) == set(GOLDEN[name])
            assert groups.iterations == 1
            assert nicknames._index.cache_info().misses == 1
            assert nicknames._index.cache_info().hits == 999
    finally:
        nicknames._index.cache_clear()


def test_large_group_caps_membership_and_keeps_requested_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    names = tuple(f"synthetic{index:03d}" for index in range(100))
    target = names[-1]
    expected = {target, *sorted(set(names) - {target})[:nicknames.MAX_VARIANTS - 1]}
    try:
        for group in (names, tuple(reversed(names))):
            nicknames._index.cache_clear()
            with monkeypatch.context() as patch:
                patch.setattr(nicknames, "GROUPS", (group,))
                result = nicknames.expand(target)
                assert isinstance(result, set)
                assert result == expected
                assert len(result) == nicknames.MAX_VARIANTS
    finally:
        nicknames._index.cache_clear()


def test_all_current_tokens_stay_bounded_without_chaining() -> None:
    for group in nicknames.GROUPS:
        for name in group:
            result = nicknames.expand(name)
            assert name in result
            assert len(result) <= nicknames.MAX_VARIANTS
    assert "christina" not in nicknames.expand("christopher")
    assert nicknames.expand("synthetic_unknown") == {"synthetic_unknown"}
    assert nicknames.expand("   ") == set()
