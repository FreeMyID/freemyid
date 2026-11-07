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

        def walk(n: Node) -> None:
            if n.tag in _SKIP_TEXT:
                return
            block = n.tag in _BLOCK
            if block:
                parts.append("\n")
            for c in n.children:
                if isinstance(c, str):
                    parts.append(c)
                else:
                    walk(c)
            if block:
                parts.append("\n")

        walk(self)
        lines = [re.sub(r"[ \t\r\f\v]+", " ", ln).strip() for ln in "".join(parts).split("\n")]
        return "\n".join(ln for ln in lines if ln)

    def select(self, selector: str) -> list[Node]:
        groups = compile_selector(selector)
        nodes = self.iter()
        return [n for n in nodes if any(_match_chain(n, g, self) for g in groups)]

    def select_one(self, selector: str) -> Node | None:
        r = self.select(selector)
        return r[0] if r else None


class _Builder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#document")
        self.cur = self.root
        self.count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.count += 1
        if self.count > MAX_NODES:
            return
        n = Node(tag.lower(), {k.lower(): (v or "") for k, v in attrs}, parent=self.cur)
        self.cur.children.append(n)
        if n.tag not in _VOID:
            self.cur = n

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in _VOID and self.cur.tag == tag.lower() and self.cur.parent:
            self.cur = self.cur.parent

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        n: Node | None = self.cur
        while n is not None and n is not self.root and n.tag != t:
            n = n.parent
        if n is not None and n is not self.root and n.parent is not None:
            self.cur = n.parent

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


def _match_chain(n: Node, chain: _Chain, scope: Node) -> bool:
    """Right-to-left match; ancestors are limited to inside `scope` (like el.query_selector)."""
    def rec(node: Node, i: int) -> bool:
        comb, comp = chain[i]
        if not comp.matches(node):
            return False
        if i == 0:
            return True
        p = node.parent
        if comb == ">":
            return p is not None and p is not scope and rec(p, i - 1)
        while p is not None and p is not scope:
            if rec(p, i - 1):
                return True
            p = p.parent
        return False

    return rec(n, len(chain) - 1)
