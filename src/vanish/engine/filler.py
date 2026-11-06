"""Deterministic form filler for "Fill it in for me" (PLAN_V1 D9).

No AI and no per-broker code. One JS pass lists the page's form controls (label, aria-label,
name, id, placeholder, autocomplete); `classify()` maps each one to a canonical field with a
fixed synonym table; `fill_page()` fills only the values `plan_values()` allows.

Never touched, whatever the labels say:
  * anything inside a CAPTCHA / challenge widget (recaptcha, hcaptcha, turnstile, ...);
  * password, file, hidden, checkbox, radio, button-like inputs (nothing gets ticked);
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

_NEGATIVE = re.compile(
    r"\b(middle|maiden|nick ?name|user ?name|username|login|company|business|organi[sz]ation|"
    r"employer|card|cvv|cvc|search|query|coupon|promo|phone|tel|telephone|mobile|cell|fax|"
    r"password|passcode|captcha|recaptcha|robot|human|comment|comments|message|subject|"
    r"reason|age|birth|birthday|dob|ssn|social security|country|line 2|address 2|apt|"
    r"apartment|suite|unit|honeypot|leave (this )?blank|confirm(ation)? code|otp|verification)\b")

_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"\b(e ?mail|email address|e mail address)\b"),
    "listing_url": re.compile(
        r"\b(url|uri|link|web ?address|web ?page|profile (address|page)|listing "
        r"(address|page)|record (address|page))\b"),
    "first_name": re.compile(r"\b((first|given|fore) ?name|fname|first|given)\b"),
    "last_name": re.compile(r"\b((last|family|sur) ?name|surname|lname|last|family)\b"),
    "full_name": re.compile(r"\b(full ?name|your name|name)\b"),
    "zip": re.compile(r"\b(zip|zipcode|zip ?code|postal|post ?code|postcode)\b"),
    "state": re.compile(r"\b(state|province)\b"),
    "city": re.compile(r"\b(city|town|locality)\b"),
    "street": re.compile(r"\b(street|address ?line ?1?|address 1|addr|address|street address)\b"),
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
    key: str                      # data-vanish-field marker
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
        """Must never be touched (CAPTCHA, password, file, checkbox, honeypot, ...)."""
        if self.in_captcha or self.disabled or not self.visible:
            return True
        if self.tag == "input" and self.type in _PROTECTED_TYPES:
            return True
        blob = _norm(f"{self.name} {self.id}")
        return bool(re.search(r"\b(g recaptcha|h captcha|cf turnstile|captcha)\b", blob))

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
    for src in c.sources():
        t = _norm(src)
        if not t:
            continue
        if _NEGATIVE.search(t):
            return None
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


def choose_state_option(options: list[dict[str, str]], code: str) -> str | None:
    """The <option> value for a 2-letter state code. Accepts "NC", "North Carolina",
    "NC - North Carolina" style options (case-insensitive)."""
    code = code.upper()
    full = STATE_NAMES.get(code, "").lower()
    for o in options:
        v, t = (o.get("value") or "").strip(), (o.get("text") or "").strip()
        if v.upper() == code or t.upper() == code or (full and (v.lower() == full or
                                                              t.lower() == full)):
            return o.get("value") or t
    for o in options:      # "NC - North Carolina", "North Carolina (NC)"
        t = _norm(o.get("text"))
        if full and full in t and re.search(rf"\b{code.lower()}\b", t):
            return o.get("value") or o.get("text")
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
    withheld: list[str] = field(default_factory=list)     # box found, Vanish may not send it
    already_filled: list[str] = field(default_factory=list)
    protected: int = 0                                    # captcha/password/file/checkbox...
    unknown: int = 0                                      # visible boxes we did not recognise
    errors: int = 0

    def summary(self) -> dict[str, Any]:
        return {"filled": sorted(set(self.filled)), "not_found": sorted(self.not_found),
                "withheld": sorted(set(self.withheld)), "protected": self.protected,
                "unknown": self.unknown, "errors": self.errors}


SCAN_JS = r"""
() => {
  const CAP = /(g-recaptcha|h-captcha|hcaptcha|recaptcha|cf-turnstile|turnstile|captcha|arkose|funcaptcha|px-captcha|cf-challenge|challenge-form)/i;
  const textOf = (node) => {
    if (!node) return '';
    const c = node.cloneNode(true);
    c.querySelectorAll('input,select,textarea,option,script,style').forEach(e => e.remove());
    return (c.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 200);
  };
  const out = [];
  let n = 0;
  for (const el of document.querySelectorAll('input, select, textarea')) {
    const tag = el.tagName.toLowerCase();
    const type = tag === 'input' ? (el.getAttribute('type') || 'text').toLowerCase() : tag;
    let inCaptcha = false, hidden = false;
    for (let a = el; a && a.nodeType === 1; a = a.parentElement) {
      const cls = typeof a.className === 'string' ? a.className : '';
      if (CAP.test((a.id || '') + ' ' + cls) || a.hasAttribute('data-sitekey')) inCaptcha = true;
      if (a.getAttribute('aria-hidden') === 'true' || a.hidden) hidden = true;
    }
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    const visible = !hidden && r.width > 2 && r.height > 2 && r.right > 0 && r.bottom > 0 &&
      cs.visibility !== 'hidden' && cs.display !== 'none' && parseFloat(cs.opacity) > 0.05 &&
      el.getAttribute('tabindex') !== '-1';
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
    el.setAttribute('data-vanish-field', key);
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
  return out;
}
"""


async def scan(page: Page) -> list[Control]:
    """Controls of the page's main frame (CAPTCHA iframes are other frames: never seen)."""
    return [Control.from_js(d) for d in await page.evaluate(SCAN_JS)]


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
        loc = page.locator(f'[data-vanish-field="{c.key}"]')
        try:
            if c.tag == "select":
                if k != "state":
                    rep.unknown += 1
                    continue
                opt = choose_state_option(c.options, val)
                if opt is None:
                    rep.errors += 1
                    continue
                await loc.select_option(value=opt, timeout=timeout_ms)
            elif c.has_value:
                rep.already_filled.append(k)
                continue
            else:
                await loc.fill(val, timeout=timeout_ms)
            rep.filled.append(k)
        except Exception:  # noqa: BLE001 - one stubborn box never stops the rest
            rep.errors += 1
    rep.not_found = [k for k in values if k not in seen and not _covered(k, seen)]
    return rep


def _covered(k: str, seen: set[str]) -> bool:
    """A form with a single 'Full name' box does not need first/last (and vice versa)."""
    if k in ("first_name", "last_name"):
        return "full_name" in seen
    if k == "full_name":
        return {"first_name", "last_name"} <= seen
    return False
