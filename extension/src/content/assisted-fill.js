// Content script: "Fill in the form for me" on a known broker's own page.
//
// Runs only on the hosts in the manifest (the public broker list), top frame, isolated world,
// and does nothing until the background asks. The background asks only after the person
// clicked "Fill in the form for me" in the banner or the popup (a real click).
//
// Fixed rules (shared rules 5 and 6, docs/EXTENSION.md section 3a):
//   1. It runs only after the person clicks a button in the banner or the popup, for the tab
//      they are looking at. Never on page load, never on a schedule, never in the background.
//   2. It fills only what the desktop app sends for this one click. The app decides, with the
//      same rules as "Fill it in for me" (engine/filler.py): only fields the broker's listing
//      already shows plus the removal mailbox, only boxes it recognises. The extension never
//      stores a value; it is dropped as soon as the boxes are filled.
//   3. It never touches a CAPTCHA or any "are you human" check: it does not tick the box, does
//      not solve anything, does not hide or move it, and does not press Submit. The person
//      does those steps.
//   4. It never pretends to be something else: no changed user agent, no fake key presses. It
//      sets a box's value and sends the same "input" and "change" events a browser's own
//      autofill sends, so the page notices the new value.
//   5. It never pays, never creates an account, never uploads an ID and never gives a phone
//      number (the app never sends one).
//   6. If the page does not look like a form, it fills nothing and says so; the Assisted card
//      in the desktop app is the fallback.
//
// The page scan below is generated from freemyid.engine.filler.SCAN_JS, so the app and the
// extension see a form the same way. tests/test_extension_link.py keeps them identical.
//
// This is a classic script (manifest content scripts cannot be ES modules). Message names
// repeat lib/protocol.js; tests keep them in step.

(() => {
  "use strict";

  if (window.top !== window) return;

  /** @type {typeof chrome} */
  const api = /** @type {any} */ (globalThis).browser ?? /** @type {any} */ (globalThis).chrome;

  const MSG_FORM_PROBE = "fmid.form_probe";
  const MSG_SCAN = "fmid.scan";
  const MSG_APPLY = "fmid.apply";

  // BEGIN generated from freemyid.engine.filler.SCAN_JS (do not edit by hand)
  const scanControls = () => {

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
};
  // END generated from freemyid.engine.filler.SCAN_JS

  const HELPERS = (() => {

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
    return { captchaOrHidden, trulyVisible };
  })();

  /** Elements of the last scan, by key. Taken from our own scan, never from page attributes. */
  /** @type {Map<string, HTMLInputElement|HTMLSelectElement|HTMLTextAreaElement>} */
  let scanned = new Map();
  /** @type {ReturnType<typeof setTimeout>|undefined} */
  let forget;

  const TEXTLIKE = new Set(["text", "email", "url", ""]);
  const KEY = /^f\d{1,6}$/;

  /** Is there anything that could be a form here? Counts boxes only; reads no value. */
  function probe() {
    let n = 0;
    for (const el of document.querySelectorAll("input, select, textarea")) {
      const type = el.tagName === "INPUT" ? (el.getAttribute("type") || "text").toLowerCase() : "";
      if (el.tagName !== "INPUT" || TEXTLIKE.has(type)) n += 1;
    }
    return { ok: true, boxes: n };
  }

  function scan() {
    const controls = scanControls();
    scanned = new Map();
    for (const el of document.querySelectorAll("[data-freemyid-field]")) {
      const key = el.getAttribute("data-freemyid-field") || "";
      if (KEY.test(key) && !scanned.has(key)) scanned.set(key, /** @type {any} */ (el));
    }
    clearTimeout(forget);
    forget = setTimeout(() => { scanned = new Map(); }, 60000);
    return {
      ok: true,
      controls: controls.slice(0, 200).map((/** @type {any} */ c) => ({
        key: c.key, tag: c.tag, type: c.type, name: c.name.slice(0, 200), id: c.id.slice(0, 200),
        label: c.label.slice(0, 200), labelledby: c.labelledby.slice(0, 200),
        aria: c.aria.slice(0, 200), placeholder: c.placeholder.slice(0, 200),
        autocomplete: c.autocomplete.slice(0, 200), title: c.title.slice(0, 200),
        visible: c.visible, in_captcha: c.in_captcha, disabled: c.disabled,
        has_value: c.has_value, maxlength: c.maxlength,
        option_values: c.options.map((/** @type {any} */ o) => String(o.value).slice(0, 200)),
        option_texts: c.options.map((/** @type {any} */ o) => String(o.text).slice(0, 200)),
      })),
    };
  }

  /**
   * Still the same safe box it was at scan time? Checked again right before filling.
   * @param {HTMLInputElement|HTMLSelectElement|HTMLTextAreaElement} el
   */
  function stillSafe(el) {
    if (!el.isConnected || el.disabled || /** @type {any} */ (el).readOnly) return false;
    const tag = el.tagName.toLowerCase();
    if (tag === "input" && !TEXTLIKE.has((el.getAttribute("type") || "text").toLowerCase())) return false;
    const [inCaptcha, hidden] = HELPERS.captchaOrHidden(el);
    if (inCaptcha || hidden) return false;
    try { return HELPERS.trulyVisible(el); } catch { return false; }
  }

  /**
   * Put a value in a box the way a browser's autofill does, then tell the page.
   * @param {HTMLInputElement|HTMLSelectElement|HTMLTextAreaElement} el
   * @param {string} value
   */
  function setValue(el, value) {
    const proto = Object.getPrototypeOf(el);
    const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
    if (setter) setter.call(el, value);
    else el.value = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  /** @param {unknown} assignments */
  function apply(assignments) {
    let filled = 0;
    let skipped = 0;
    if (!Array.isArray(assignments)) return { ok: false, error: "bad_request" };
    for (const a of assignments.slice(0, 200)) {
      const key = typeof a?.key === "string" ? a.key : "";
      const value = typeof a?.value === "string" ? a.value : "";
      const el = KEY.test(key) ? scanned.get(key) : undefined;
      if (!el || !value || value.length > 300 || !stillSafe(el)) {
        skipped += 1;
        continue;
      }
      if (el.tagName === "SELECT") {
        const sel = /** @type {HTMLSelectElement} */ (el);
        if (!Array.from(sel.options).some((o) => o.value === value)) {
          skipped += 1;
          continue;
        }
      } else if (el.value && el.value.trim()) {
        skipped += 1;          // never overwrite what is already in a box
        continue;
      }
      setValue(el, value);
      filled += 1;
    }
    scanned = new Map();       // the values and the boxes are forgotten right away
    clearTimeout(forget);
    return { ok: true, filled, skipped };
  }

  api.runtime.onMessage.addListener((message, sender, sendResponse) => {
    // Only the extension's own background may ask (a message from a page never arrives here,
    // and the background's messages carry no tab).
    if (sender.id !== api.runtime.id || sender.tab) return false;
    const type = message?.type;
    try {
      if (type === MSG_FORM_PROBE) sendResponse(probe());
      else if (type === MSG_SCAN) sendResponse(scan());
      else if (type === MSG_APPLY) sendResponse(apply(message.assignments));
      else return false;
    } catch {
      sendResponse({ ok: false, error: "internal_error" });
    }
    return false;
  });
})();
