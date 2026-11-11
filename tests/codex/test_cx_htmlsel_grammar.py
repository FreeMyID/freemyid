"""The static HTML selector parser accepts only its documented grammar."""
from __future__ import annotations

import pytest

from freemyid.engine import htmlsel

PAGE = """<!doctype html>
<html id="document-html"><head id="document-head">head-only marker<title id="page-title">hidden title marker</title></head>
<body id="document-body"><main id="content" class="page">
  <section id="first" class="result card" data-kind="person" data-key="one">
    <a id="link-one" class="view primary" href="/one" data-label="One">Open one</a>
    <span id="name-one" class="name">Jane Q Testperson</span>
    <div id="details-one" class="details"><b id="city-one" class="city">Springfield IL</b></div>
  </section>
  <section id="second" class="result" data-kind="organization" data-key="two">
    <a id="link-two" class="view" href="/two" data-label="Two">Open two</a>
    <span id="name-two" class="name">Example Listing</span>
  </section>
  <div id="void-parent">Before<br id="break">After<img id="picture" src="/fake.png"><span id="after-void">Sibling remains</span></div>
  <script id="script">script-only marker</script><style id="style">style-only marker</style>
  <noscript id="noscript">noscript-only marker</noscript><template id="template">template-only marker</template>
</main></body></html>"""


@pytest.fixture
def root() -> htmlsel.Node:
    return htmlsel.parse(PAGE)


def _ids(nodes: list[htmlsel.Node]) -> list[str | None]:
    return [node.get("id") for node in nodes]


@pytest.mark.parametrize(
    ("selector", "expected"),
    [
        ("section", ["first", "second"]),
        ("*", [
            "document-html", "document-head", "page-title", "document-body", "content",
            "first", "link-one", "name-one", "details-one", "city-one", "second",
            "link-two", "name-two", "void-parent", "break", "picture", "after-void",
            "script", "style", "noscript", "template",
        ]),
        (".result", ["first", "second"]),
        ("#first", ["first"]),
        ("[href]", ["link-one", "link-two"]),
        ('[data-kind="person"]', ["first"]),
        ("[data-kind=person]", ["first"]),
        ("a.view[href]", ["link-one", "link-two"]),
        (".result a", ["link-one", "link-two"]),
        (".result > a", ["link-one", "link-two"]),
        (".details > .city", ["city-one"]),
        (".name, .city", ["name-one", "city-one", "name-two"]),
    ],
)
def test_documented_selector_forms_select_exact_nodes(
    root: htmlsel.Node, selector: str, expected: list[str],
) -> None:
    assert _ids(root.select(selector)) == expected


@pytest.mark.parametrize(
    "selector",
    [
        "a + b", "a ~ b", ":hover", "::before", "[href^=x]", "[href*=x]",
        "a >", "> a", "a,,b", "", "a" * 301,
    ],
)
def test_unsupported_selector_forms_are_refused(selector: str) -> None:
    root = htmlsel.parse(PAGE)
    with pytest.raises(htmlsel.UnsupportedSelector):
        root.select(selector)


def test_non_visible_elements_and_void_tags_do_not_corrupt_text_or_tree(
    root: htmlsel.Node,
) -> None:
    text = root.text()
    for marker in (
        "head-only marker", "hidden title marker", "script-only marker", "style-only marker",
        "noscript-only marker", "template-only marker",
    ):
        assert marker not in text

    parent = root.select_one("#void-parent")
    assert parent is not None
    assert [node.get("id") for node in parent.iter()] == ["break", "picture", "after-void"]
    sibling = root.select_one("#after-void")
    assert sibling is not None and sibling.text() == "Sibling remains"


def test_parse_caps_element_nodes_without_failing() -> None:
    page = "<p></p>" * (htmlsel.MAX_NODES + 10)
    root = htmlsel.parse(page)

    assert len(root.iter()) <= htmlsel.MAX_NODES


def test_comma_list_deduplicates_and_preserves_document_order(root: htmlsel.Node) -> None:
    assert _ids(root.select(".name, .result, .name")) == [
        "first", "name-one", "second", "name-two",
    ]
