// Copy strings live in _locales/<lang>/messages.json and nowhere else.
// Pages mark text with data-i18n="key"; scripts call t("key").

import { api } from "./browser.js";

/**
 * Look up one string. Falls back to the key so a missing string is visible in testing.
 * @param {string} key
 * @param {...string} substitutions
 * @returns {string}
 */
export function t(key, ...substitutions) {
  return api.i18n.getMessage(key, substitutions) || key;
}

/**
 * Fill every element that has data-i18n with its string, as text (never as HTML).
 * @param {Document|Element} root
 */
export function localize(root) {
  for (const el of root.querySelectorAll("[data-i18n]")) {
    const key = el.getAttribute("data-i18n");
    if (!key) continue;
    const text = api.i18n.getMessage(key);
    if (text) el.textContent = text;
  }
  if (root instanceof Document) {
    root.documentElement.lang = api.i18n.getUILanguage();
  }
}
