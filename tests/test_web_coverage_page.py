"""/brokers/ "Sites we cover": the built page against the public coverage list.

Reads web/dist (build it first: pnpm build in web/). The numbers on the page must be the rows of
brokers/coverage.public.yaml, nothing private may be on the page, and the filters must work with
JavaScript switched off. Browser checks are served offline from the built files.
"""
from __future__ import annotations

import gzip
import html
import re
from collections.abc import Iterator

import pytest
import yaml

from tests.conftest import ROOT

DIST = ROOT / "web" / "dist"
PAGE = DIST / "brokers" / "index.html"
COVERAGE = yaml.safe_load((ROOT / "brokers" / "coverage.public.yaml").read_text(encoding="utf-8"))
SITES, COUNTS = COVERAGE["sites"], COVERAGE["counts"]
ROW = re.compile(r'<li(?P<v> data-v="1")?(?: id="[^"]*")?><b>(?P<name>[^<]*)</b> <span>(?P<site>[^<]*)</span>'
                 r"<small>(?P<meta>.*?)</small></li>")


def page() -> str:
    return PAGE.read_text(encoding="utf-8")


def rows() -> list[dict]:
    return [m.groupdict() for m in ROW.finditer(page())]


def text(markup: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", markup))).strip()


def num(n: int) -> str:
    return f"{n:,}"


def group_of(site: dict) -> str:
    """lib/coverage.ts groupOf: registry-listed data brokers are their own group."""
    return "registered" if site["category"] == "data_broker" and "registered" in site else site["category"]


GROUP_IDS = sorted({group_of(s) for s in SITES})
STATES = {"CA": "California", "VT": "Vermont", "CA,VT": "California and Vermont"}
REGISTERED_NOTE = ("These companies are on a state's official data broker registry. Being listed does not mean "
                   "they did anything wrong; it means the law lets you ask them to delete your data.")


# ---------------------------------------------------------------- the numbers are the rows

def test_every_site_in_the_list_is_on_the_page_once():
    on_page = sorted((html.unescape(r["name"]), r["site"]) for r in rows())
    assert on_page == sorted((s["name"], s["site"]) for s in SITES)
    assert len(on_page) == COUNTS["listed"]


def test_headline_numbers_are_the_listed_and_verified_counts_side_by_side():
    stats = re.search(r'<dl class="stat-group[^"]*"[^>]*>(.*?)</dl>', page(), re.DOTALL)
    assert stats is not None
    values = re.findall(r'<dd class="stat__value">([^<]*)</dd>', stats.group(1))
    labels = re.findall(r'<dt class="stat__label">([^<]*)</dt>', stats.group(1))
    hints = re.findall(r'<dd class="stat__hint">([^<]*)</dd>', stats.group(1))
    assert values == [num(COUNTS["listed"]), num(COUNTS["verified"])]
    assert labels == ["Sites on the list", "Verified by us"]
    assert COUNTS["listed"] == len(SITES)
    assert COUNTS["verified"] == sum(1 for s in SITES if s["status"] == "verified")
    assert sum(1 for r in rows() if r["v"]) == COUNTS["verified"]
    # the one date: the export's month, e.g. "Last checked November 2026"
    year, month = COVERAGE["updated"].split("-")
    name = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
            "October", "November", "December"][int(month) - 1]
    assert hints == [f"Last checked {name} {year}"]


def test_the_page_says_what_verified_means_and_does_not_overclaim():
    body = text(page())
    assert "Verified means we opened that site's own removal page ourselves" in body
    assert f"The other {num(COUNTS['not_verified'])} sites are on the list, but we have not confirmed" in body
    assert "It does not mean every site says yes" in body
    assert "many sites honor but are not required to" in body          # the state-law qualifier
    assert "Sites often list people again later" in body
    for claim in ("all sites", "every data broker", "removes you from", "remove you from all",
                  "every week", "every day", "daily", "weekly", "add new ones"):   # no cadence claims
        assert claim not in body.lower(), claim


def test_sites_with_no_removal_route_are_counted_and_not_named():
    body = text(page())
    n = COUNTS["not_available"]
    line = ("1 site we listed earlier has no way to remove yourself right now; we are watching it." if n == 1 else
            f"{num(n)} sites we listed earlier have no way to remove yourself right now; we are watching them.")
    assert (line in body) == (n > 0)
    assert "Not available right now" not in body and "not available" not in body.lower()
    assert all(s["status"] in ("verified", "not_verified") for s in SITES)


def test_each_row_says_how_the_site_is_handled():
    by_site = {r["site"]: r for r in rows()}
    route = {"email": "By email", "assisted": "Step by step", "automatic": "Filled in for you",
             "by_hand": "By hand"}
    for s in SITES:
        meta = text(by_site[s["site"]]["meta"])
        parts = [p.strip() for p in meta.split("·")]
        assert parts[0].startswith("Verified " if s["status"] == "verified" else "Not yet verified"), s["site"]
        assert parts[1] == route[s["route"]], s["site"]
        assert bool(by_site[s["site"]]["v"]) == (s["status"] == "verified")
        registered = [p for p in parts if p.startswith("Registered as a data broker in ")]
        assert registered == ([f"Registered as a data broker in {STATES[s['registered']]}"]
                              if "registered" in s else []), s["site"]
        family = [p for p in parts if p.startswith("Part of the ")]
        assert family == ([f"Part of the {s['family']} group"] if "family" in s else []), s["site"]
        assert "Owned by" not in meta


def test_groups_show_their_own_counts():
    groups = re.findall(r'<section class="cov-group" data-c="([a-z_]+)"[^>]*>(.*?)</section>', page(), re.DOTALL)
    assert sorted(c for c, _ in groups) == GROUP_IDS
    total = 0
    for group, markup in groups:
        mine = [s for s in SITES if group_of(s) == group]
        verified = sum(1 for s in mine if s["status"] == "verified")
        count = text(re.search(r'<p class="cov-count">(.*?)</p>', markup, re.DOTALL).group(1))
        assert count == f"{num(len(mine))} site{'' if len(mine) == 1 else 's'}, {num(verified)} verified", group
        assert len(ROW.findall(markup)) == len(mine)
        names = [html.unescape(m.group("name")) for m in ROW.finditer(markup)]
        assert names == sorted(names, key=str.casefold), group
        total += len(mine)
    assert total == COUNTS["listed"]


def test_registered_data_brokers_have_their_own_group_and_plain_sentence():
    groups = dict(re.findall(r'<section class="cov-group" data-c="([a-z_]+)"[^>]*>(.*?)</section>', page(), re.DOTALL))
    registered = [s for s in SITES if group_of(s) == "registered"]
    if not registered:
        pytest.skip("no registry-listed data broker in this list")
    markup = groups["registered"]
    assert text(re.search(r"<h3[^>]*>(.*?)</h3>", markup, re.DOTALL).group(1)) == "Registered data brokers"
    assert REGISTERED_NOTE in text(markup)
    assert all("Registered as a data broker in" in text(m.group("meta")) for m in ROW.finditer(markup))
    assert text(page()).count(REGISTERED_NOTE) == 1
    if "data_broker" in groups:      # the rest keep the guides index label
        heading = re.search(r"<h3[^>]*>(.*?)</h3>", groups["data_broker"], re.DOTALL).group(1)
        assert text(heading) == "Marketing data companies"
        assert "Registered as a data broker" not in text(groups["data_broker"])
    assert "Marketing data companies" in text((DIST / "guides" / "index.html").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- nothing private, nothing heavy

def test_no_private_data_script_or_form_on_the_page():
    raw = page()
    assert "<form" not in raw and "<iframe" not in raw
    scripts = re.findall(r"<script\b([^>]*)>", raw)
    assert scripts and all('type="application/ld+json"' in s for s in scripts)
    assert "script-src 'none'" in raw
    list_markup = "".join(re.findall(r'<ul class="cov-list".*?</ul>', raw, re.DOTALL))
    assert "@" not in list_markup and "mailto:" not in list_markup
    # The only links in the list are our own guides; no link leaves the site from a row.
    hrefs = re.findall(r'href="([^"]*)"', list_markup)
    assert hrefs and all(re.fullmatch(r"/(?:[a-z0-9-]+/)*guides/[a-z0-9-]+/", h) for h in hrefs)
    assert "registry.yaml" not in raw and "opt_out" not in raw


def test_page_weight_budget():
    raw = page()
    css = sum(len(gzip.compress((DIST / href.lstrip("/")).read_bytes(), 9))
              for href in re.findall(r'<link rel="stylesheet" href="([^"]+)"', raw))
    total = len(gzip.compress(raw.encode(), 9)) + css
    assert total < 50 * 1024, f"HTML + CSS is {total / 1024:.1f} KiB gzip (budget 50)"
    per_row = len(gzip.compress("".join(m.group(0) for m in ROW.finditer(raw)).encode(), 9)) / len(rows())
    assert per_row < 32, f"{per_row:.1f} gzip bytes per row: 1,000 rows would not fit the budget"


def test_in_the_sitemap_and_linked_from_the_pages_that_mention_coverage():
    base_url = yaml.safe_load((ROOT / "site_src" / "site.yaml").read_text(encoding="utf-8"))["base_url"]
    assert f"<loc>{base_url}brokers/</loc>" in (DIST / "sitemap.xml").read_text(encoding="utf-8")
    for rel in ("index.html", "how-it-works/index.html", "guides/index.html"):
        main = re.search(r"<main\b.*?</main>", (DIST / rel).read_text(encoding="utf-8"), re.DOTALL)
        assert main is not None and re.search(r'href="[^"]*brokers/"', main.group(0)), rel
    footer = re.search(r"<footer\b.*?</footer>", (DIST / "safety" / "index.html").read_text(encoding="utf-8"), re.DOTALL)
    assert footer is not None and ">Sites we cover</a>" in footer.group(0)


# ---------------------------------------------------------------- filters with JavaScript off

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Browser, Page

from tests.test_web_home_hero_layout import BASE, ORIGIN, browser, serve

__all__ = ["browser"]  # the shared module-scoped fixture


@pytest.fixture
def coverage_page(browser: Browser, request: pytest.FixtureRequest) -> Iterator[Page]:
    width, theme = request.param
    context = browser.new_context(viewport={"width": width, "height": 800}, color_scheme=theme,
                                  reduced_motion="reduce", java_script_enabled=False)
    context.route("**/*", serve)
    try:
        tab = context.new_page()
        response = tab.goto(ORIGIN + BASE + "brokers/", wait_until="load")
        assert response is not None and response.status == 200, "Build web/dist first"
        yield tab
    finally:
        context.close()


SIZES = [(320, "light"), (360, "dark"), (768, "light"), (1280, "dark")]
IDS = [f"{w}-{t}" for w, t in SIZES]


@pytest.mark.parametrize("coverage_page", SIZES, ids=IDS, indirect=True)
def test_no_sideways_scroll_and_numbers_stay_side_by_side(coverage_page: Page):
    tab = coverage_page
    assert tab.evaluate("document.documentElement.scrollWidth <= innerWidth")
    boxes = [b.bounding_box() for b in tab.locator(".cov-stats .stat").all()]
    assert len(boxes) == 2 and all(b is not None for b in boxes)
    assert abs(boxes[0]["y"] - boxes[1]["y"]) < 1 and boxes[0]["x"] + boxes[0]["width"] <= boxes[1]["x"]
    assert tab.locator(".cov-list li:visible").count() == COUNTS["listed"]


@pytest.mark.parametrize("coverage_page", [(360, "light"), (1280, "light")], ids=["360", "1280"], indirect=True)
def test_verified_only_filter_works_without_javascript(coverage_page: Page):
    tab = coverage_page
    tab.locator("label", has=tab.locator("#cov-v")).click()
    assert tab.locator(".cov-list li:visible").count() == COUNTS["verified"]
    assert tab.locator(".cov-list li:not([data-v]):visible").count() == 0
    tab.locator("label", has=tab.locator("#cov-v")).click()
    assert tab.locator(".cov-list li:visible").count() == COUNTS["listed"]


@pytest.mark.parametrize("coverage_page", [(360, "light")], ids=["360"], indirect=True)
def test_every_group_filter_works_without_javascript(coverage_page: Page):
    tab = coverage_page
    assert tab.locator(".cov-controls input[type=radio]").count() == len(GROUP_IDS) + 1
    for group in GROUP_IDS:
        tab.locator("label", has=tab.locator(f"#cov-c-{group}")).click()
        shown = tab.locator(".cov-group:visible")
        assert shown.count() == 1 and shown.first.get_attribute("data-c") == group
        assert tab.locator(".cov-list li:visible").count() == sum(1 for s in SITES if group_of(s) == group)
    # both filters together: a group with no verified site says so instead of showing an empty list
    tab.locator("label", has=tab.locator("#cov-v")).click()
    for group in GROUP_IDS:
        tab.locator("label", has=tab.locator(f"#cov-c-{group}")).click()
        verified = sum(1 for s in SITES if group_of(s) == group and s["status"] == "verified")
        assert tab.locator(".cov-list li:visible").count() == verified
        assert tab.locator(".cov-empty:visible").count() == (0 if verified else 1)
    tab.locator("label", has=tab.locator("#cov-c-all")).click()
    assert tab.locator(".cov-group:visible").count() == len(GROUP_IDS)


@pytest.mark.parametrize("coverage_page", [(360, "light")], ids=["360"], indirect=True)
def test_filters_are_keyboard_reachable_and_big_enough_to_tap(coverage_page: Page):
    tab = coverage_page
    for label in tab.locator(".cov-controls label").all():
        box = label.bounding_box()
        assert box is not None and box["height"] >= 48, label.inner_text()
    tab.locator("#cov-c-all").focus()
    tab.keyboard.press("ArrowDown")
    assert tab.locator(".cov-group:visible").count() == 1            # arrow keys move the radio choice
    tab.locator("#cov-v").focus()
    tab.keyboard.press("Space")
    assert tab.locator(".cov-list li:not([data-v]):visible").count() == 0
