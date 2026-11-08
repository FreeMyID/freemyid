"""Tiny static HTML tree + CSS selector subset (stdlib only). No I/O, no scripts.

Used by the exposure scan (engine/exposure.py) to read a broker's search results page from
a plain HTTP fetch with the same `Broker.search` selectors the browser path uses
(`submitters.web_form.parse_results`). Page text is data, never instructions.

Supported selectors: `tag`, `*`, `.class`, `#id`, `[attr]`, `[attr=value]` (quoted or not),
compounds of those (`a.view[href]`), descendant (`a b`) and child (`a > b`) combinators, and
comma lists. Anything else raises `UnsupportedSelector`, which the caller turns into "check
by hand" rather than guessing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

MAX_NODES = 50_000
# SEC-92: start tags nested deeper than this are dropped (their text is kept), so every
# ancestor walk below is bounded by MAX_DEPTH
MAX_DEPTH = 256

_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param",
         "source", "track", "wbr"}
_SKIP_TEXT = {"script", "style", "noscript", "template", "head", "title"}
_BLOCK = {"address", "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt",
          "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5",
          "h6", "header", "hr", "li", "main", "nav", "ol", "p", "pre", "section", "table",
          "tbody", "td", "tfoot", "th", "thead", "tr", "ul"}


class UnsupportedSelector(ValueError):
    pass


@dataclass(eq=False)
class Node:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list[Node | str] = field(default_factory=list)
    parent: Node | None = None

    @property
    def classes(self) -> set[str]:
        return set(self.attrs.get("class", "").split())

    def get(self, name: str) -> str | None:
        return self.attrs.get(name)

    def iter(self) -> list[Node]:
        """All descendant elements in document order (not self)."""
        out: list[Node] = []
        stack = [c for c in reversed(self.children) if isinstance(c, Node)]
        while stack:
            n = stack.pop()
            out.append(n)
            stack.extend(c for c in reversed(n.children) if isinstance(c, Node))
        return out

    def text(self) -> str:
        """Visible text, newlines between block elements (like innerText, roughly)."""
        parts: list[str] = []
        # SEC-92: iterative (no recursion per nesting level); a str on the stack is output
        stack: list[Node | str] = [self]
        while stack:
            n = stack.pop()
            if isinstance(n, str):
                parts.append(n)
                continue
            if n.tag in _SKIP_TEXT:
                continue
            block = n.tag in _BLOCK
            if block:
                parts.append("\n")
                stack.append("\n")
            for c in reversed(n.children):
                # source newlines are spaces
                stack.append(re.sub(r"\s+", " ", c) if isinstance(c, str) else c)
        lines = [re.sub(r"[ \t\r\f\v]+", " ", ln).strip() for ln in "".join(parts).split("\n")]
        return "\n".join(ln for ln in lines if ln)

    def select(self, selector: str) -> list[Node]:
        groups = [_ChainMatcher(g, self) for g in compile_selector(selector)]
        nodes = self.iter()
        return [n for n in nodes if any(g.match(n) for g in groups)]

    def select_one(self, selector: str) -> Node | None:
        r = self.select(selector)
        return r[0] if r else None


class _Builder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#document")
        self.cur = self.root
        self.count = 0
        self.depth = 0       # depth of self.cur (root = 0)
        self.dropped = 0     # open non-void start tags dropped past MAX_DEPTH

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.count += 1
        if self.count > MAX_NODES:
            return
        t = tag.lower()
        if self.depth >= MAX_DEPTH:
            if t not in _VOID:
                self.dropped += 1
            return
        n = Node(t, {k.lower(): (v or "") for k, v in attrs}, parent=self.cur)
        self.cur.children.append(n)
        if n.tag not in _VOID:
            self.cur = n
            self.depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        if self.depth >= MAX_DEPTH:
            self.count += 1      # self-closed: dropped, and nothing stays open
            return
        if t in _VOID or self.count >= MAX_NODES:
            self.handle_starttag(tag, attrs)     # adds nothing that stays open
            return
        self.handle_starttag(tag, attrs)
        if self.cur.tag == t and self.cur.parent:
            self.cur = self.cur.parent
            self.depth -= 1

    def handle_endtag(self, tag: str) -> None:
        if self.dropped:
            self.dropped -= 1     # closes a start tag dropped past MAX_DEPTH
            return
        t = tag.lower()
        n: Node | None = self.cur
        up = 0
        while n is not None and n is not self.root and n.tag != t:   # <= MAX_DEPTH steps
            n = n.parent
            up += 1
        if n is not None and n is not self.root and n.parent is not None:
            self.cur = n.parent
            self.depth -= up + 1

    def handle_data(self, data: str) -> None:
        if self.count <= MAX_NODES:
            self.cur.children.append(data)


def parse(html: str) -> Node:
    b = _Builder()
    b.feed(html)
    b.close()
    return b.root


# --------------------------------------------------------------------------- selectors

_COMPOUND = re.compile(
    r"""(?P<tag>\*|[a-zA-Z][a-zA-Z0-9-]*)?
        (?P<rest>(?:\.[\w-]+|\#[\w-]+|\[\s*[\w-]+\s*(?:=\s*(?:"[^"]*"|'[^']*'|[\w-]+)\s*)?\])*)$""",
    re.VERBOSE)
_PART = re.compile(r"""\.([\w-]+)|\#([\w-]+)|\[\s*([\w-]+)\s*(?:=\s*("[^"]*"|'[^']*'|[\w-]+)\s*)?\]""")


@dataclass(frozen=True)
class _Compound:
    tag: str | None
    classes: tuple[str, ...]
    ids: tuple[str, ...]
    attrs: tuple[tuple[str, str | None], ...]

    def matches(self, n: Node) -> bool:
        if self.tag and self.tag != "*" and n.tag != self.tag:
            return False
        if self.classes and not set(self.classes) <= n.classes:
            return False
        if any(n.attrs.get("id") != i for i in self.ids):
            return False
        for k, v in self.attrs:
            if k not in n.attrs or (v is not None and n.attrs[k] != v):
                return False
        return True


# chain: [(combinator, compound)] left to right; combinator of the first is ""
_Chain = list[tuple[str, _Compound]]


def _compound(tok: str) -> _Compound:
    m = _COMPOUND.match(tok)
    if not m or not tok:
        raise UnsupportedSelector(tok[:40])
    classes, ids, attrs = [], [], []
    for cls, ident, attr, val in _PART.findall(m.group("rest") or ""):
        if cls:
            classes.append(cls)
        elif ident:
            ids.append(ident)
        else:
            attrs.append((attr.lower(), val.strip("\"'") if val else None))
    tag = m.group("tag")
    return _Compound(tag.lower() if tag else None, tuple(classes), tuple(ids), tuple(attrs))


def compile_selector(selector: str) -> list[_Chain]:
    if not selector or len(selector) > 300:
        raise UnsupportedSelector("empty_or_long")
    out: list[_Chain] = []
    for group in selector.split(","):
        toks = re.sub(r"\s*>\s*", " > ", group.strip()).split()
        if not toks:
            raise UnsupportedSelector("empty_group")
        chain: _Chain = []
        comb = ""
        for t in toks:
            if t == ">":
                if comb or not chain:
                    raise UnsupportedSelector("bad_combinator")
                comb = ">"
                continue
            chain.append((comb or (" " if chain else ""), _compound(t)))
            comb = ""
        if comb:
            raise UnsupportedSelector("trailing_combinator")
        out.append(chain)
    return out


class _ChainMatcher:
    """Right-to-left match of one chain; ancestors are limited to inside `scope` (like
    el.query_selector). SEC-92: memoized per (node, index) for one select() call, and the
    descendant combinator's "some ancestor matches" is memoized too, so a select is
    O(nodes x chain length) instead of exponential backtracking."""

    def __init__(self, chain: _Chain, scope: Node) -> None:
        self.chain, self.scope = chain, scope
        self._m: dict[tuple[int, int], bool] = {}
        self._anc: dict[tuple[int, int], bool] = {}

    def match(self, n: Node) -> bool:
        return self._at(n, len(self.chain) - 1)

    def _at(self, node: Node, i: int) -> bool:
        key = (id(node), i)
        hit = self._m.get(key)
        if hit is not None:
            return hit
        comb, comp = self.chain[i]
        if not comp.matches(node):
            r = False
        elif i == 0:
            r = True
        elif comb == ">":
            p = node.parent
            r = p is not None and p is not self.scope and self._at(p, i - 1)
        else:
            r = self._any_ancestor(node.parent, i - 1)
        self._m[key] = r
        return r

    def _any_ancestor(self, p: Node | None, j: int) -> bool:
        """Does p or one of its ancestors (strictly inside scope) match chain[j]? Iterative."""
        path: list[Node] = []
        r = False
        while p is not None and p is not self.scope:
            hit = self._anc.get((id(p), j))
            if hit is not None:
                r = hit
                break
            path.append(p)
            if self._at(p, j):
                r = True
                break
            p = p.parent
        for q in path:
            self._anc[(id(q), j)] = r
        return r


def _match_chain(n: Node, chain: _Chain, scope: Node) -> bool:
    """One-off match (no memo shared across calls)."""
    return _ChainMatcher(chain, scope).match(n)
