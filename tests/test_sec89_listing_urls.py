"""SEC-89: listing links from broker pages must really point at the broker."""
from __future__ import annotations

import pytest

from freemyid.engine import exposure as ex
from freemyid.engine._dev import fixture_registry
from freemyid.submitters.web_form import on_broker_url

DEV = next(b for b in fixture_registry().brokers if b.id == "devauto")
PAGE = "https://devauto.example/name/jane-testperson/il"


def _result(href: str) -> str:
    return (f'<div class="result"><a class="view" href="{href}">View</a>'
            '<span class="name">Jane Q Testperson</span></div>')


@pytest.mark.parametrize("url", [
    "https://evil.example\\@devauto.example/p/1",
    "https://devauto.example/p/1\x1b]52;c;eA==\x07",
    "https://devauto.example/p/1 x",
    "https://user:pw@devauto.example/p/1",
    "https://evil.example/p/1",
    "",
])
def test_on_broker_url_refuses_confusable_or_off_domain(url):
    assert not on_broker_url(DEV, url)


def test_on_broker_url_accepts_the_broker():
    assert on_broker_url(DEV, "https://devauto.example/p/1")


@pytest.mark.parametrize("href", ["https://evil.example\\@devauto.example/p/1",
                                  "//evil.example\\@devauto.example/p/1",
                                  "/p/1\x1b]52;c;eA==\x07"])
def test_parse_candidates_drops_hostile_links(href):
    assert ex.parse_candidates(DEV, PAGE, _result(href)) == []


def test_parse_candidates_keeps_a_plain_link():
    assert [c.url for c in ex.parse_candidates(DEV, PAGE, _result("/p/1"))] == [
        "https://devauto.example/p/1"]
