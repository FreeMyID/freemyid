"""Common English given-name nickname groups, for the matcher. No I/O.

A people-search page often lists "Bob" for a Robert or "Peggy" for a Margaret. Each group is
one formal name and the short forms people commonly go by. Lookup is symmetric: "bob" finds
the Robert group and "robert" finds it too. A name in several groups ("chris") gets the union,
but there is no chaining: "christopher" never reaches "christina".

This only widens the NAME check. A listing still needs 2 supporting signals (city, age,
relative, phone, email) before it is CONFIRMED, so a looser name never auto-submits alone.
The profile's own `nicknames` list is always used as well.
"""
from __future__ import annotations

from functools import cache

#: formal name first, then the short forms. Lower case, ASCII.
GROUPS: tuple[tuple[str, ...], ...] = (
    ("abigail", "abby", "gail"),
    ("albert", "al", "bert"),
    ("alexander", "alex", "al", "sandy"),
    ("alexandra", "alex", "sandra", "sandy", "lexi"),
    ("alfred", "al", "fred", "alf"),
    ("andrew", "andy", "drew"),
    ("anthony", "tony"),
    ("barbara", "barb", "barbie", "babs"),
    ("benjamin", "ben", "benny", "benji"),
    ("catherine", "cathy", "kate", "katie", "cat"),
    ("katherine", "kathy", "kate", "katie", "kat", "kay", "kitty"),
    ("kathleen", "kathy", "kate", "katie"),
    ("charles", "charlie", "chuck", "chas"),
    ("christina", "chris", "tina", "chrissy"),
    ("christine", "chris", "tina", "chrissy"),
    ("christopher", "chris", "kit", "topher"),
    ("cynthia", "cindy"),
    ("daniel", "dan", "danny"),
    ("david", "dave", "davy"),
    ("deborah", "debbie", "deb", "debby"),
    ("donald", "don", "donnie"),
    ("dorothy", "dot", "dottie", "dolly"),
    ("douglas", "doug"),
    ("edward", "ed", "eddie", "ted", "ned"),
    ("eleanor", "ellie", "nell", "nora"),
    ("elizabeth", "liz", "beth", "betty", "betsy", "eliza", "lisa", "libby", "lizzie"),
    ("eugene", "gene"),
    ("frances", "fran", "frannie"),
    ("francis", "frank"),
    ("franklin", "frank"),
    ("frederick", "fred", "freddie"),
    ("gerald", "jerry", "gerry"),
    ("gregory", "greg"),
    ("harold", "hal", "harry"),
    ("henry", "hank", "harry"),
    ("jacob", "jake"),
    ("james", "jim", "jimmy", "jamie"),
    ("janet", "jan"),
    ("jeffrey", "jeff"),
    ("jennifer", "jen", "jenny", "jenn"),
    ("jessica", "jess", "jessie"),
    ("john", "jack", "johnny"),
    ("jonathan", "jon", "john"),
    ("joseph", "joe", "joey"),
    ("josephine", "jo", "josie"),
    ("joshua", "josh"),
    ("judith", "judy"),
    ("kenneth", "ken", "kenny"),
    ("lawrence", "larry"),
    ("leonard", "len", "lenny", "leo"),
    ("louis", "lou"),
    ("margaret", "maggie", "meg", "peggy", "marge", "margie", "greta"),
    ("matthew", "matt"),
    ("michael", "mike", "mikey", "mick"),
    ("nicholas", "nick", "nicky"),
    ("pamela", "pam"),
    ("patricia", "pat", "patty", "trish", "tricia"),
    ("patrick", "pat", "paddy"),
    ("peter", "pete"),
    ("philip", "phil"),
    ("rebecca", "becky", "becca"),
    ("richard", "rick", "dick", "rich", "ricky"),
    ("robert", "bob", "rob", "bobby", "robbie", "bert"),
    ("ronald", "ron", "ronnie"),
    ("samantha", "sam", "sammy"),
    ("samuel", "sam", "sammy"),
    ("stephen", "steve"),
    ("steven", "steve"),
    ("susan", "sue", "susie", "suzy"),
    ("theodore", "ted", "teddy", "theo"),
    ("thomas", "tom", "tommy"),
    ("timothy", "tim", "timmy"),
    ("victoria", "vicky", "tori"),
    ("virginia", "ginny", "ginger"),
    ("walter", "walt", "wally"),
    ("william", "bill", "will", "billy", "willy", "liam"),
)


@cache
def _index() -> dict[str, frozenset[str]]:
    idx: dict[str, set[str]] = {}
    for g in GROUPS:
        for n in g:
            idx.setdefault(n, set()).update(g)
    return {k: frozenset(v) for k, v in idx.items()}


def expand(first: str) -> set[str]:
    """`first` (already normalized: lower case ASCII) plus every name in a group it is in."""
    f = first.strip()
    if not f:
        return set()
    return {f, *_index().get(f, ())}
