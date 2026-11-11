"""Deterministic form filler for "Fill it in for me" (PLAN_V1 D9).

No AI and no per-broker code. One JS pass lists the page's form controls (label, aria-label,
name, id, placeholder, autocomplete); `classify()` maps each one to a canonical field with a
fixed synonym table; `fill_page()` fills only the values `plan_values()` allows.

Never touched, whatever the labels say:
  * anything inside a CAPTCHA / challenge widget (recaptcha, hcaptcha, turnstile, ...);
  * password, payment, and ID-number fields, plus file, hidden, checkbox, radio and
    button-like inputs (nothing gets ticked, except `tick_safe_checkboxes` for the
    registry's `Broker.safe_checkboxes`);
  * invisible / off-screen / aria-hidden controls (bot "honeypots": filling them marks the
    request as a bot) and disabled / read-only ones;
  * phone, birth date, age, middle name, company, search boxes and anything unrecognised.
Text boxes that already have a value are left alone.

Data minimization: the values come from `submitters.base.form_vars`, the same minimized set
the Automatic tier uses (fields the listing shows that the broker needs, the removal mailbox,
never DOB / relatives / personal emails / phone).

The report holds field keys and counts only (no values), so it is safe to log.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .matcher import STATE_NAMES

if TYPE_CHECKING:
    from playwright.async_api import Page

    from ..models import Broker, Listing, Profile

# Canonical keys, in classification precedence order (email before street because of
# "email address", listing_url before street because of "web address", first/last before
# full name because they contain "name").
KEYS = ("email", "listing_url", "first_name", "last_name", "full_name", "zip", "state",
        "city", "street")

# Payment instruments and government ID numbers. Checked on every descriptor, not just the
# visible label, and treated as protected so a friendly label cannot make them fillable.
_PAYMENT_RE = (
    r"card|cardholder|cardnumber|creditcard|debitcard|cvv|cvc|cvc2|ccv|"
    r"ccnumber|ccnum|cc number|cc num|cc name|cc exp|cc csc"
)
_ID_RE = (
    r"ssn|social security|passport|itin|"
    r"drivers? licen[cs]e|driver s licen[cs]e|driving licen[cs]e|"
    r"id number|identity number|identification number|national id|tax id"
)
_PAYMENT = re.compile(rf"\b(?:{_PAYMENT_RE})\b")
_ID_NUMBER = re.compile(rf"\b(?:{_ID_RE})\b")

_NEGATIVE = re.compile(
    rf"\b(?:middle|maiden|nick ?name|user ?name|username|login|company|business|"
    rf"organi[sz]ation|employer|search|query|coupon|promo|phone|tel|telephone|mobile|cell|fax|"
    rf"password|passcode|captcha|recaptcha|robot|human|comment|comments|message|subject|"
    rf"reason|age|birth|birthday|dob|country|(?:address|addr|street|line) ?[2-9]|zip ?4|plus ?4|apt|apartment|suite|unit|"
    rf"honeypot|leave (this )?blank|confirm(?:ation)? code|otp|verification|"
    rf"{_PAYMENT_RE}|{_ID_RE})\b")

# A box whose whole label / name is one of these is a typical honeypot ("leave this empty")
# and is skipped even when visible (a "Website" box would otherwise get the listing URL).
_HONEYPOT = re.compile(r"(your )?(website|web site|homepage|home page|hp|trap|honey ?pot)( url)?")

_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"\b(e ?mail ?address|e ?mail)\b"),
    "listing_url": re.compile(
        r"\b(url|uri|link|web ?address|web ?page|profile (address|page)|listing "
        r"(address|page)|record (address|page))\b"),
    "first_name": re.compile(r"\b((first|given|fore|christian) ?name|fname|first|given)\b"),
    "last_name": re.compile(r"\b((last|family|sur) ?name|surname|lname|last|family)\b"),
    "full_name": re.compile(r"\b(full ?name|your name|name)\b"),
    # "postal address" is a street; bare "postal" / "postal code" is the ZIP.
    "zip": re.compile(
        r"\b(zipcode|zip ?code|postal ?code|postcode|post ?code|zip ?5|zip)\b|"
        r"\bpostal\b(?! address)"),
    "state": re.compile(r"\b(state|province)\b"),
    "city": re.compile(r"\b(city|town|locality|municipality)\b"),
    "street": re.compile(
        r"\b(street ?address|street ?1|address ?line ?1|address ?1|addr ?1|"
        r"street|address|addr)\b"),
}

_AUTOCOMPLETE = {
    "email": "email", "url": "listing_url", "given-name": "first_name",
    "family-name": "last_name", "name": "full_name", "postal-code": "zip",
    "address-level1": "state", "address-level2": "city", "street-address": "street",
    "address-line1": "street",
}

# Input types we may type into. Everything else (password, file, checkbox, radio, hidden,
# submit, button, image, reset, range, color, date, tel, number, search) is never touched.
_TEXTLIKE = frozenset({"text", "email", "url", ""})
_PROTECTED_TYPES = frozenset({"password", "file", "hidden", "checkbox", "radio", "submit",
                              "button", "image", "reset"})


def _norm(s: str | None) -> str:
    if not s:
        return ""
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    s = re.sub(r"[^a-z0-9]+", " ", s.lower())
    return " ".join(s.split())


@dataclass
class Control:
    """One form control as seen by the page scan (no values, just descriptors)."""
    key: str                      # data-freemyid-field marker
    tag: str = "input"
    type: str = "text"
    name: str = ""
    id: str = ""
    label: str = ""
    labelledby: str = ""
    aria: str = ""
    placeholder: str = ""
    autocomplete: str = ""
    title: str = ""
    visible: bool = True
    in_captcha: bool = False
    disabled: bool = False
    has_value: bool = False
    maxlength: int = -1
    options: list[dict[str, str]] = field(default_factory=list)

    @classmethod
    def from_js(cls, d: dict[str, Any]) -> Control:
        names = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in d.items() if k in names})

    def protected(self) -> bool:
        """Must never be touched (CAPTCHA, password, payment, ID number, ...)."""
        if self.in_captcha or self.disabled or not self.visible:
            return True
        if self.tag == "input" and self.type in _PROTECTED_TYPES:
            return True
        # Any token, not only the first: "billing cc-given-name" is a card field too.
        if any(tok.startswith("cc-") for tok in (self.autocomplete or "").lower().split()):
            return True
        blob = _norm(" ".join([*self.sources(), self.name, self.id, self.autocomplete]))
        if re.search(r"\b(g recaptcha|h captcha|cf turnstile|captcha)\b", blob):
            return True
        return bool(_PAYMENT.search(blob) or _ID_NUMBER.search(blob))

    def fillable(self) -> bool:
        if self.protected():
            return False
        if self.tag == "select" or self.tag == "textarea":
            return True
        return self.tag == "input" and self.type in _TEXTLIKE

    def sources(self) -> list[str]:
        """Descriptor texts in the order we trust them (label first)."""
        return [self.label, self.labelledby, self.aria, self.name, self.id, self.placeholder,
                self.title]


def classify(c: Control) -> str | None:
    """Canonical key for a control, or None (unknown / deliberately skipped)."""
    if not c.fillable():
        return None
    # A payment, ID, phone or honeypot word on any descriptor blocks a friendly label.
    texts = [t for t in (_norm(src) for src in c.sources()) if t]
    for t in texts:
        if _NEGATIVE.search(t) or _HONEYPOT.fullmatch(t):
            return None
    for t in texts:
        for k in KEYS:
            if _PATTERNS[k].search(t):
                return k
    ac = (c.autocomplete or "").lower().split()
    for tok in ac:
        if tok in _AUTOCOMPLETE:
            return _AUTOCOMPLETE[tok]
    if c.tag == "input" and c.type == "email":
        return "email"
    if c.tag == "input" and c.type == "url":
        return "listing_url"
    return None


# Territories matcher.STATE_NAMES does not carry. Kept here so the state list stays a
# contract of the matcher (this file only reads it).
_TERRITORY_NAMES: dict[str, str] = {
    "AS": "American Samoa",
    "GU": "Guam",
    "MP": "Northern Mariana Islands",
    "PR": "Puerto Rico",
    "VI": "Virgin Islands",
}
# Whole-option abbreviations after _norm (punctuation already spaces). "calif" is "Calif.".
_STATE_ALIASES: dict[str, str] = {
    "ala": "AL", "ariz": "AZ", "ark": "AR", "cal": "CA", "calif": "CA", "colo": "CO",
    "conn": "CT", "del": "DE", "fla": "FL", "ill": "IL", "ind": "IN", "kan": "KS",
    "kans": "KS", "mass": "MA", "mich": "MI", "minn": "MN", "miss": "MS", "mont": "MT",
    "neb": "NE", "nebr": "NE", "nev": "NV", "okla": "OK", "ore": "OR", "oreg": "OR",
    "penn": "PA", "penna": "PA", "tenn": "TN", "tex": "TX", "wash": "WA", "wis": "WI",
    "wisc": "WI", "wyo": "WY", "w va": "WV", "n car": "NC", "s car": "SC", "n dak": "ND",
    "s dak": "SD", "n mex": "NM", "washington dc": "DC", "us virgin islands": "VI",
    "virgin islands us": "VI",
}
_PLACEHOLDER_TOKENS = frozenset({
    "a", "an", "choose", "n", "na", "none", "one", "option", "options", "pick", "please",
    "province", "region", "select", "state", "territory", "the", "your",
})
_STATE_FILLER = _PLACEHOLDER_TOKENS | frozenset({
    "and", "commonwealth", "of", "states", "united", "us", "usa",
})


def _build_name_to_code() -> dict[str, str]:
    names = dict(_STATE_ALIASES)
    for code, name in (*STATE_NAMES.items(), *_TERRITORY_NAMES.items()):
        names[name.lower()] = code
    return names


_NAME_TO_CODE = _build_name_to_code()
_CODES = frozenset(STATE_NAMES) | frozenset(_TERRITORY_NAMES)


def _collapse_initials(text: str) -> str:
    """Join runs of single letters so "D. C." and "C. A." become "dc" and "ca"."""
    parts = text.split()
    out: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        if buf:
            out.append("".join(buf))
            buf.clear()

    for part in parts:
        if len(part) == 1 and part.isalpha():
            buf.append(part)
        else:
            flush()
            out.append(part)
    flush()
    return " ".join(out)


def _is_placeholder(raw: str) -> bool:
    text = _collapse_initials(_norm(raw))
    return bool(text) and all(part in _PLACEHOLDER_TOKENS for part in text.split())


def _named(text: str) -> str | None:
    """Code when `text` is a state name or abbreviation, filler words aside."""
    if not text:
        return None
    hit = _NAME_TO_CODE.get(text)
    if hit:
        return hit
    core = " ".join(part for part in text.split() if part not in _STATE_FILLER)
    if core and core != text:
        return _NAME_TO_CODE.get(core)
    return None


def _one_name(text: str) -> str | None:
    """The one state named in `text`, or None when it is ambiguous or leftover junk.

    Longest name wins, so "west virginia" is not Virginia and "arkansas" is not Kansas.
    """
    found: list[tuple[int, str, str]] = []
    for name, code in _NAME_TO_CODE.items():
        if re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", text):
            found.append((len(name), name, code))
    if not found:
        return None
    best = max(length for length, _name, _code in found)
    top = [(name, code) for length, name, code in found if length == best]
    codes = {code for _name, code in top}
    if len(codes) != 1:
        return None
    code = codes.pop()
    rest = text
    for name, _code in top:
        rest = re.sub(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", " ", rest)
    for tok in rest.split():
        if tok in _STATE_FILLER or tok.upper() == code:
            continue
        return None
    return code


def _state_of_text(raw: str | None) -> str | None:
    """2-letter code denoted by one option string, or None if it is not one state."""
    if not raw or not raw.strip():
        return None
    text = _collapse_initials(_norm(raw))
    if not text or _is_placeholder(raw):
        return None
    if text.upper() in _CODES:
        return text.upper()
    named = _NAME_TO_CODE.get(text)
    if named:
        return named
    parts = text.split()
    if len(parts) >= 2:
        head, tail = parts[0].upper(), parts[-1].upper()
        if head in _CODES and _named(" ".join(parts[1:])) == head:
            return head
        if tail in _CODES and _named(" ".join(parts[:-1])) == tail:
            return tail
    return _one_name(text)


def choose_state_option(options: list[dict[str, str]], code: str) -> str | None:
    """The <option> value for a 2-letter state code.

    Accepts "NC", "North Carolina", "CA - California", "California (CA)", "Calif.",
    lower-case and dotted codes ("ca", "D.C."), and territories (PR, DC). A leading
    "Select..." is ignored. When the value and the text name different states, the
    option is skipped so a mismatched value can never select the wrong state.
    """
    want = code.strip().upper()
    if want not in _CODES:
        return None
    for opt in options:
        value = opt.get("value") or ""
        text = opt.get("text") or ""
        if _is_placeholder(text) or _is_placeholder(value):
            continue
        v_code = _state_of_text(value)
        t_code = _state_of_text(text)
        # "SC" / "North Carolina" would submit the wrong state. Skip it.
        if v_code and t_code and v_code != t_code:
            continue
        if (v_code or t_code) == want:
            return value if value.strip() else text.strip()
    return None


def plan_values(profile: Profile, broker: Broker, listing: Listing | None) -> dict[str, str]:
    """Canonical key -> value, data-minimized exactly like the Automatic tier."""
    from ..submitters.base import form_vars
    v = form_vars(profile, broker, listing)
    p = vars(v["profile"])
    out: dict[str, str] = {}
    for k, src in (("first_name", "first"), ("last_name", "last"), ("full_name", "full_name"),
                   ("city", "city"), ("state", "state"), ("zip", "zip"), ("street", "street")):
        if p.get(src):
            out[k] = str(p[src])
    if v["listing"] is not None:
        out["listing_url"] = v["listing"].url
    if v["mailbox"] is not None:
        out["email"] = v["mailbox"].address
    return out


@dataclass
class FillReport:
    """What happened. Keys and counts only (PII-free)."""
    filled: list[str] = field(default_factory=list)
    not_found: list[str] = field(default_factory=list)    # had a value, no matching box
    withheld: list[str] = field(default_factory=list)     # box found, Free My ID may not send it
    already_filled: list[str] = field(default_factory=list)
    protected: int = 0                                    # captcha/password/file/checkbox...
    unknown: int = 0                                      # visible boxes we did not recognise
    errors: int = 0
    ticked: int = 0                                       # Broker.safe_checkboxes ticked
    # (name, id) attributes of the boxes we filled: lets fill_for_me tell whether the filled
    # form is still on the page (SEC-32). Attribute names only, never values.
    controls: list[tuple[str, str]] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        return {"filled": sorted(set(self.filled)), "not_found": sorted(self.not_found),
                "withheld": sorted(set(self.withheld)), "protected": self.protected,
                "unknown": self.unknown, "errors": self.errors, "ticked": self.ticked}


# Shared page-side helpers (SEC-30 / SEC-33). `parentOf` walks up through shadow roots;
# `trulyVisible` is the honeypot test: checkVisibility(), own size and style, not pushed off
# the page, no clipping ancestor (overflow != visible with ~zero size or not overlapping the
# element), and a hit test at the element's centre after scrolling it into view.
_JS_HELPERS = r"""
  const CAP = /(g-recaptcha|h-captcha|hcaptcha|recaptcha|cf-turnstile|turnstile|captcha|arkose|funcaptcha|px-captcha|cf-challenge|challenge-form)/i;
  const parentOf = (a) => {
    if (a.parentElement) return a.parentElement;
    const r = a.getRootNode ? a.getRootNode() : null;
    return (r && r !== a && r.host) ? r.host : null;
  };
  const captchaOrHidden = (el) => {
    let inCaptcha = false, hidden = false;
    for (let a = el; a && a.nodeType === 1; a = parentOf(a)) {
      const cls = typeof a.className === 'string' ? a.className : '';
      if (CAP.test((a.id || '') + ' ' + cls) || a.hasAttribute('data-sitekey')) inCaptcha = true;
      if (a.getAttribute('aria-hidden') === 'true' || a.hidden) hidden = true;
    }
    return [inCaptcha, hidden];
  };
  const labelOf = (el) => {
    let lab = el.closest('label');
    if (!lab && el.id) {
      try {
        lab = el.getRootNode().querySelector('label[for="' + CSS.escape(el.id) + '"]');
      } catch (e) { lab = null; }
    }
    return lab;
  };
  const trulyVisible = (el) => {
    if (typeof el.checkVisibility === 'function' &&
        !el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true,
                             opacityProperty: true, visibilityProperty: true})) return false;
    const cs = getComputedStyle(el);
    if (cs.visibility !== 'visible' || cs.display === 'none' ||
        parseFloat(cs.opacity) <= 0.05 || el.getAttribute('tabindex') === '-1') return false;
    const r0 = el.getBoundingClientRect();
    if (r0.width <= 2 || r0.height <= 2) return false;
    // pushed off the page: left/top of the document, or only reachable by scrolling sideways
    const sx = window.scrollX, sy = window.scrollY;
    if (r0.right + sx <= 0 || r0.bottom + sy <= 0) return false;
    if (r0.left + sx >= window.innerWidth) return false;
    const de = document.documentElement;
    if (r0.top + sy >= Math.max(de.scrollHeight, de.clientHeight)) return false;
    try { el.scrollIntoView({block: 'center', inline: 'nearest', behavior: 'instant'}); }
    catch (e) { /* keep going with the current position */ }
    const r = el.getBoundingClientRect();
    for (let a = parentOf(el); a && a.nodeType === 1; a = parentOf(a)) {
      if (a === document.body || a === de) continue;   // their overflow is the viewport's
      const s = getComputedStyle(a);
      if (parseFloat(s.opacity) <= 0.05) return false;
      if (s.overflowX !== 'visible' || s.overflowY !== 'visible') {
        const ar = a.getBoundingClientRect();
        if (ar.width <= 2 || ar.height <= 2) return false;
        if (ar.right <= r.left || ar.left >= r.right || ar.bottom <= r.top || ar.top >= r.bottom)
          return false;
      }
    }
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    if (cx < 0 || cy < 0 || cx >= window.innerWidth || cy >= window.innerHeight) return false;
    const root = el.getRootNode && el.getRootNode().elementFromPoint ? el.getRootNode() : document;
    const hit = root.elementFromPoint(cx, cy);
    if (!hit) return false;
    if (hit === el || el.contains(hit)) return true;
    const lab = labelOf(el);
    return !!(lab && (lab === hit || lab.contains(hit)));
  };
"""

SCAN_JS = r"""
() => {
""" + _JS_HELPERS + r"""
  const textOf = (node) => {
    if (!node) return '';
    const c = node.cloneNode(true);
    c.querySelectorAll('input,select,textarea,option,script,style').forEach(e => e.remove());
    return (c.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 200);
  };
  const sx0 = window.scrollX, sy0 = window.scrollY;
  const out = [];
  let n = 0;
  for (const el of document.querySelectorAll('input, select, textarea')) {
    const tag = el.tagName.toLowerCase();
    const type = tag === 'input' ? (el.getAttribute('type') || 'text').toLowerCase() : tag;
    const [inCaptcha, hidden] = captchaOrHidden(el);
    let visible = false;
    if (!hidden && type !== 'hidden') {
      try { visible = trulyVisible(el); } catch (e) { visible = false; }
    }
    let label = '';
    if (el.id) {
      try { label = textOf(document.querySelector('label[for="' + CSS.escape(el.id) + '"]')); }
      catch (e) { label = ''; }
    }
    if (!label) label = textOf(el.closest('label'));
    let lb = '';
    const ids = el.getAttribute('aria-labelledby');
    if (ids) lb = ids.split(/\s+/).map(i => textOf(document.getElementById(i))).join(' ');
    const key = 'f' + (n++);
    el.setAttribute('data-freemyid-field', key);
    out.push({
      key, tag, type, name: el.getAttribute('name') || '', id: el.id || '', label,
      labelledby: lb, aria: el.getAttribute('aria-label') || '',
      placeholder: el.getAttribute('placeholder') || '',
      autocomplete: el.getAttribute('autocomplete') || '', title: el.getAttribute('title') || '',
      visible, in_captcha: inCaptcha, disabled: !!(el.disabled || el.readOnly),
      has_value: tag === 'select' ? false : !!(el.value && el.value.trim()),
      maxlength: el.maxLength || -1,
      options: tag === 'select' ? Array.from(el.options).slice(0, 120)
        .map(o => ({value: o.value, text: (o.text || '').trim()})) : [],
    });
  }
  try { window.scrollTo(sx0, sy0); } catch (e) { /* ignore */ }
  return out;
}
"""


async def scan(page: Page) -> list[Control]:
    """Controls of the page's main frame (CAPTCHA iframes are other frames: never seen)."""
    return [Control.from_js(d) for d in await page.evaluate(SCAN_JS)]


_KEY_RE = re.compile(r"f\d{1,6}")
_FILL_TAGS = frozenset({"input", "select", "textarea"})
# Ancestor-or-self CAPTCHA containers, evaluated by Playwright's own selector engine (its
# isolated world), not by page script.
_LOWER = "translate(concat(@class,' ',@id),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')"
_CAPTCHA_ANCESTOR_XPATH = (
    "xpath=ancestor-or-self::*[@data-sitekey or "
    + " or ".join(f"contains({_LOWER},'{w}')" for w in (
        "captcha", "turnstile", "arkose", "cf-challenge", "challenge-form"))
    + "]")


def _locator_for(page: Page, c: Control) -> Any | None:
    """Playwright locator for a scanned control, or None if the scan output looks forged
    (SEC-34: the key and tag come from page-world JS and go into a selector)."""
    if not isinstance(c.key, str) or not _KEY_RE.fullmatch(c.key) or c.tag not in _FILL_TAGS:
        return None
    return page.locator(f'{c.tag}[data-freemyid-field="{c.key}"]')


async def _still_safe(loc: Any, c: Control, timeout_ms: int) -> bool:
    """Re-check through Playwright (not page JS) right before typing: exactly one element,
    a text-like type, visible, editable, not named like or inside a CAPTCHA (SEC-34)."""
    if await loc.count() != 1:
        return False
    if c.tag == "input":
        t = ((await loc.get_attribute("type", timeout=timeout_ms)) or "text").strip().lower()
        if t not in _TEXTLIKE:
            return False
    name = _norm(f"{await loc.get_attribute('name', timeout=timeout_ms) or ''} "
                 f"{await loc.get_attribute('id', timeout=timeout_ms) or ''}")
    if re.search(r"\b(g recaptcha|h captcha|cf turnstile|captcha)\b", name):
        return False
    if not await loc.is_visible() or not await loc.is_editable(timeout=timeout_ms):
        return False
    return await loc.locator(_CAPTCHA_ANCESTOR_XPATH).count() == 0


async def fill_page(page: Page, values: dict[str, str], *, timeout_ms: int = 5000) -> FillReport:
    """Fill every recognised box we have an allowed value for. Never submits, never ticks."""
    rep = FillReport()
    seen: set[str] = set()
    for c in await scan(page):
        if c.protected():
            rep.protected += 1
            continue
        k = classify(c)
        if k is None:
            if c.fillable():
                rep.unknown += 1
            continue
        seen.add(k)
        val = values.get(k)
        if not val:
            rep.withheld.append(k)
            continue
        loc = _locator_for(page, c)
        if loc is None:
            rep.errors += 1
            continue
        try:
            if c.tag == "select":
                if k != "state":
                    rep.unknown += 1
                    continue
                opt = choose_state_option(c.options, val)
                if opt is None:
                    rep.errors += 1
                    continue
                if not await _still_safe(loc, c, timeout_ms):
                    rep.protected += 1
                    continue
                await loc.select_option(value=opt, timeout=timeout_ms)
            elif c.has_value:
                rep.already_filled.append(k)
                continue
            else:
                if not await _still_safe(loc, c, timeout_ms):
                    rep.protected += 1
                    continue
                await loc.fill(val, timeout=timeout_ms)
            rep.filled.append(k)
            rep.controls.append((c.name[:100], c.id[:100]))
        except Exception:  # noqa: BLE001 - one stubborn box never stops the rest
            rep.errors += 1
    rep.not_found = [k for k in values if k not in seen and not _covered(k, seen)]
    return rep


# The element must be a real, visible, enabled, unticked checkbox input that is not inside
# a CAPTCHA / challenge container (also across shadow roots, SEC-33), and whose wording is
# not a robot / human check (SEC-31) or a marketing opt-in. Returns '' when it is ok to tick.
_ROBOT_WORDS = r"robot|human|\bbot\b|captcha|verify|verification|not a machine|security check"
_MARKETING_WORDS = (r"newsletter|offers?\b|marketing|partners?\b|subscribe|promotion|"
                    r"promotional|special deals|third.?part")
_ROBOT_RE = re.compile(_ROBOT_WORDS, re.IGNORECASE)
_MARKETING_RE = re.compile(_MARKETING_WORDS, re.IGNORECASE)

CHECKBOX_OK_JS = r"""
(el) => {
""" + _JS_HELPERS + r"""
  const ROBOT = new RegExp(""" + json.dumps(_ROBOT_WORDS) + r""", 'i');
  const MKT = new RegExp(""" + json.dumps(_MARKETING_WORDS) + r""", 'i');
  if (!el || el.tagName !== 'INPUT' || (el.getAttribute('type') || '').toLowerCase() !== 'checkbox')
    return 'not_checkbox';
  if (el.disabled || el.readOnly) return 'disabled';
  if (el.checked) return 'already';
  const [inCaptcha, hidden] = captchaOrHidden(el);
  if (inCaptcha) return 'captcha';
  if (hidden) return 'hidden';
  const blob = (el.name || '') + ' ' + (el.id || '');
  if (CAP.test(blob)) return 'captcha';
  const parts = [el.getAttribute('name'), el.id, el.getAttribute('aria-label'),
                 el.getAttribute('title'), el.getAttribute('value')];
  const lab = labelOf(el);
  if (lab) parts.push(lab.textContent);
  const lb = el.getAttribute('aria-labelledby');
  if (lb) lb.split(/\s+/).forEach(i => {
    const n = document.getElementById(i); if (n) parts.push(n.textContent);
  });
  const words = parts.filter(Boolean).join(' ').replace(/[_-]+/g, ' ');
  if (ROBOT.test(words)) return 'robot';
  if (MKT.test(words)) return 'marketing';
  const sx0 = window.scrollX, sy0 = window.scrollY;
  let vis = false;
  try { vis = trulyVisible(el); } catch (e) { vis = false; }
  try { window.scrollTo(sx0, sy0); } catch (e) { /* ignore */ }
  return vis ? '' : 'hidden';
}
"""

_MAX_SAFE_SELECTORS = 3      # models.Broker allows at most 3
_MAX_PER_SELECTOR = 5


async def tick_safe_checkboxes(page: Page, selectors: list[str], *,
                               timeout_ms: int = 5000) -> int:
    """Tick the registry's `Broker.safe_checkboxes` (plain consent boxes) and nothing else.

    Main frame only (`page.query_selector_all` never looks into iframes, where CAPTCHA
    widgets live); every element must pass CHECKBOX_OK_JS. Returns how many were ticked.
    """
    ticked = 0
    for sel in selectors[:_MAX_SAFE_SELECTORS]:
        if not sel or len(sel) > 300:
            continue
        try:
            els = await page.query_selector_all(sel)
        except Exception:  # noqa: BLE001, S112 - malformed selector from the registry
            continue
        for el in els[:_MAX_PER_SELECTOR]:
            try:
                if await el.evaluate(CHECKBOX_OK_JS) != "":
                    continue
                if not await _checkbox_still_safe(el):
                    continue
                await el.check(timeout=timeout_ms)
                ticked += 1
            except Exception:  # noqa: BLE001, S112 - detached / covered element
                continue
    return ticked


async def _checkbox_still_safe(el: Any) -> bool:
    """Second opinion through Playwright's handle API (not page JS): a visible, enabled
    checkbox whose name / id / aria-label / title has no robot or marketing words and that
    is not inside a CAPTCHA container (SEC-31 / SEC-34)."""
    if ((await el.get_attribute("type")) or "").strip().lower() != "checkbox":
        return False
    words = " ".join([(await el.get_attribute(a)) or "" for a in
                      ("name", "id", "aria-label", "title")]).replace("_", " ").replace("-", " ")
    if _ROBOT_RE.search(words) or _MARKETING_RE.search(words):
        return False
    if not await el.is_visible() or not await el.is_enabled():
        return False
    return not await el.query_selector(_CAPTCHA_ANCESTOR_XPATH)


def _covered(k: str, seen: set[str]) -> bool:
    """A form with a single 'Full name' box does not need first/last (and vice versa)."""
    if k in ("first_name", "last_name"):
        return "full_name" in seen
    if k == "full_name":
        return {"first_name", "last_name"} <= seen
    return False
