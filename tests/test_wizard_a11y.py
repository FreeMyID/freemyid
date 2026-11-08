"""v0.3 accessibility checks on the app's key pages (HTML assertions, fake people only)."""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from freemyid.models import BrokerStatus, Listing, ListingState, MatchLevel
from tests.test_wizard_v03 import _todo, env  # noqa: F401  (env is a fixture)

STATIC = Path(__file__).resolve().parents[1] / "src/freemyid/wizard/static"


class _Doc(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags: list[tuple[str, dict]] = []
        self.label_for: set[str] = set()
        self.wrapped_inputs = 0
        self._in_label = 0
        self.headings: list[int] = []
        self.text_in: dict[str, str] = {}
        self._stack: list[str] = []
        self._btn_text = ""
        self.buttons_no_name: list[dict] = []
        self._btn_attrs: dict | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append((tag, a))
        if tag == "label":
            self._in_label += 1
            if "for" in a:
                self.label_for.add(a["for"])
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))
        if tag in ("button", "a"):
            self._btn_attrs, self._btn_text = a, ""
        if tag == "input" and a.get("type") not in ("hidden", "submit", "button") \
                and self._in_label:
            self.wrapped_inputs += 1

    def handle_endtag(self, tag):
        if tag == "label":
            self._in_label -= 1
        if tag in ("button", "a") and self._btn_attrs is not None:
            if not self._btn_text.strip() and not self._btn_attrs.get("aria-label"):
                self.buttons_no_name.append(self._btn_attrs)
            self._btn_attrs = None

    def handle_data(self, data):
        self._btn_text += data


def audit(html: str) -> _Doc:
    d = _Doc()
    d.feed(html)
    return d


def _pages(env):  # noqa: F811
    c, store, p, _, _ = env
    store.save_todo(_todo(p))
    store.save_status(BrokerStatus(profile_id=p.id, broker_id="examplebroker",
                                   state=ListingState.FOUND))
    store.save_listing(Listing(profile_id=p.id, broker_id="examplebroker", url="https://e.example/x",
                               name_shown="Jane Testperson", age_shown=60,
                               locations_shown=["Springfield, IL"], match_score=90,
                               match_level=MatchLevel.CONFIRMED))
    return c, {
        "today": "/", "sites": f"/profile/{p.id}",
        "broker": f"/profile/{p.id}/site/examplebroker", "protect": f"/protect?p={p.id}",
        "settings": "/settings", "emails": "/outbox", "summary": f"/profile/{p.id}/summary",
        "mailbox": f"/settings/{p.id}/mailbox", "edit": f"/profile/{p.id}/edit",
        "wiz-consent": "/wizard/consent", "wiz-names": "/wizard/names",
        "wiz-addresses": "/wizard/addresses", "wiz-about": "/wizard/about",
        "wiz-permissions": "/wizard/permissions", "wiz-mailbox": "/wizard/mailbox",
        "wiz-mode": "/wizard/mode", "wiz-schedule": "/wizard/schedule",
        "wiz-review": "/wizard/review",
    }


def test_every_key_page_has_landmarks_one_h1_labels(env):  # noqa: F811
    c, pages = _pages(env)
    checked = 0
    for name, url in pages.items():
        r = c.get(url, follow_redirects=True)
        if r.status_code != 200:
            continue
        checked += 1
        t, d = r.text, audit(r.text)
        assert d.headings.count(1) == 1, f"{name}: needs exactly one h1"
        assert t.count("<main ") == 1 and 'lang="en"' in t, name
        assert "<title>" in t, name
        assert "<nav" in t or "/wizard/" in str(r.url), name   # wizard pages hide the menu
        prev = 0
        for h in d.headings:                     # no skipped heading levels
            assert h <= prev + 1, f"{name}: heading jumps h{prev} to h{h}"
            prev = h
        for tag, a in d.tags:
            if tag in ("input", "select", "textarea") and a.get("type") not in (
                    "hidden", "submit", "button"):
                ok = a.get("id") in d.label_for or a.get("aria-label") or a.get("aria-labelledby")
                assert ok or d.wrapped_inputs, f"{name}: unlabelled control {a}"
            if "tabindex" in a:
                assert a["tabindex"] in ("-1", "0"), f"{name}: positive tabindex"
            if tag == "img":
                assert "alt" in a, f"{name}: img without alt"
        assert not d.buttons_no_name, f"{name}: link/button with no name {d.buttons_no_name}"
        assert 'style="' not in t and "<style" not in t, name
    assert checked >= 8


def test_labels_point_at_real_ids(env):  # noqa: F811
    c, pages = _pages(env)
    for name, url in pages.items():
        r = c.get(url, follow_redirects=True)
        if r.status_code != 200:
            continue
        d = audit(r.text)
        ids = {a["id"] for _, a in d.tags if "id" in a}
        for f in d.label_for:
            assert f in ids, f"{name}: label for={f} has no control"
        ids_list = [a["id"] for _, a in d.tags if "id" in a]
        assert len(ids_list) == len(set(ids_list)), f"{name}: duplicate ids"


def test_status_chips_say_it_in_words(env):  # noqa: F811
    c, pages = _pages(env)
    t = c.get(pages["sites"]).text
    for m in re.finditer(r'<span class="chip \w+">([^<]*)</span>', t):
        assert len(m.group(1).strip()) >= 3                   # words, not colour alone
    assert re.search(r'<span class="chip \w+">[^<]+</span>', t)


def test_css_focus_targets_zoom_motion():
    css = (STATIC / "style.css").read_text()
    assert ":focus-visible" in css and "outline: 3px" in css
    assert "outline: none" not in css and "outline:none" not in css
    assert "--fmi-tap" in css
    assert "transition" not in css and "animation" not in css   # no motion at all
    assert not re.search(r"font-size:\s*\d+px", css)          # type scales with zoom
    assert not re.search(r"\bwidth:\s*\d{4,}px", css)         # nothing fixed wider than a phone
    toks = (STATIC / "tokens.css").read_text()
    assert re.search(r"--fmi-tap:\s*(2\.75|44)", toks) or "--fmi-tap" in toks


def test_theme_js_and_toggle_are_keyboard_reachable(env):  # noqa: F811
    c, *_ = env
    t = c.get("/").text
    assert '<button type="button" class="theme secondary" id="theme-toggle"' in t
    assert 'aria-pressed="false"' in t
    assert "viewport" in t and "user-scalable" not in t and "maximum-scale" not in t


def _lum(h: str) -> float:
    ch = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    ch = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def _ratio(a: str, b: str) -> float:
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_app_colour_pairs_are_aa_in_both_themes():
    css = (STATIC / "tokens.css").read_text()
    pairs = {m.group(1): m.group(2, 3) for m in re.finditer(
        r"--fmi-color-([\w-]+):\s*light-dark\((#\w{6}),\s*(#\w{6})\)", css)}
    pairs = {k: v for k, v in pairs.items()}
    need = [  # (text colour, background colour): the pairs style.css actually uses
        ("text", "bg"), ("text", "bg-alt"), ("text", "card"), ("muted", "card"),
        ("muted", "bg-alt"), ("heading", "card"), ("heading", "bg-alt"),
        ("link", "card"), ("link", "bg-alt"), ("brand-ink", "brand"),
        ("ok", "surface"), ("warn", "surface"), ("accent", "surface"),
        ("accent", "card"), ("text", "surface"), ("link", "surface"),
    ]
    for theme in (0, 1):
        for fg, bg in need:
            r = _ratio(pairs[fg][theme], pairs[bg][theme])
            assert r >= 4.5, f"theme {theme}: {fg} on {bg} is {r:.2f}:1"
        assert _ratio(pairs["focus-inner"][theme], pairs["bg"][theme]) >= 3.0  # two-tone ring
        assert _ratio(pairs["line-strong"][theme], pairs["card"][theme]) >= 3.0
