"""CR-C: `web_form._search_page` must never read a changed page as "no results".

A page with neither result rows nor the site's own "no results" text raises
`UnexpectedPage("search_page_unrecognized")` (so the runner never records NOT_FOUND from
it); an HTTP error page raises `search_http_<status>`; the site's "no results" text is a
real empty result. Fake page objects only; no browser, no network. Fake people only."""
from __future__ import annotations

import pytest

from freemyid.engine._dev import fixture_registry
from freemyid.submitters import web_form

from .conftest import make_profile


class _Resp:
    def __init__(self, status: int) -> None:
        self.status = status


class _Page:
    def __init__(self, html: str) -> None:
        self.html = html

    async def content(self) -> str:
        return self.html

    async def screenshot(self, **kw) -> bytes:
        return b"png"


class _Ctx:
    def __init__(self, page: _Page) -> None:
        self.page, self.closed = page, False

    async def new_page(self) -> _Page:
        return self.page

    async def close(self) -> None:
        self.closed = True


class _BM:
    def __init__(self, html: str, status: int = 200) -> None:
        self.ctx = _Ctx(_Page(html))
        self.status = status

    async def new_context(self, domains):
        return self.ctx

    async def goto(self, page, url):
        return _Resp(self.status)


def _run_ctx(store):
    from freemyid.engine.runner import NullNotifier
    from freemyid.interfaces import RunContext
    from freemyid.netpolicy import NetPolicy
    p = make_profile()
    store.save_profile(p)
    return RunContext(profile=p, broker=fixture_registry().get("devauto"), store=store,
                      netpolicy=NetPolicy(None), handoff=None, notifier=NullNotifier(),
                      mailer=None, dry_run=True, interactive=False)


URL = "https://devauto.example/name/jane-testperson/il"


async def test_changed_page_is_unrecognized_not_empty(store, monkeypatch) -> None:
    async def nothing(page, broker):
        return []

    monkeypatch.setattr(web_form, "parse_results", nothing)
    bm = _BM("<h1>Our new look!</h1>")
    with pytest.raises(web_form.UnexpectedPage, match="search_page_unrecognized"):
        await web_form._search_page(bm, _run_ctx(store), URL)
    assert bm.ctx.closed                       # the context is closed on the raise too


async def test_no_results_text_is_a_real_empty_result(store, monkeypatch) -> None:
    async def boom(page, broker):
        raise AssertionError("not parsed: the site said no results")

    monkeypatch.setattr(web_form, "parse_results", boom)
    bm = _BM("<p>No records found for that name.</p>")
    assert await web_form._search_page(bm, _run_ctx(store), URL) == ([], None)


async def test_http_error_page_is_never_no_results(store) -> None:
    bm = _BM("<p>No records found</p>", status=403)
    with pytest.raises(web_form.UnexpectedPage, match="search_http_403"):
        await web_form._search_page(bm, _run_ctx(store), URL)
