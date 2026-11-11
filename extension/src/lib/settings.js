// The few things the extension remembers, in storage.local (this computer only).
//
// storage.sync is never used: it would copy the list of sites where the person chose
// "Not now" to the browser vendor's servers.

import { api } from "./browser.js";

/** "Not now" hides the banner on that broker's sites for this long. */
export const DISMISS_DAYS = 30;
const DAY_MS = 24 * 60 * 60 * 1000;

const KEY_BANNER = "showBanner";
const KEY_DISMISSED = "dismissedUntil";

/** @returns {Promise<boolean>} true unless the person turned the banner off */
export async function isBannerEnabled() {
  const stored = await api.storage.local.get(KEY_BANNER);
  return stored[KEY_BANNER] !== false;
}

/** @param {boolean} enabled */
export async function setBannerEnabled(enabled) {
  await api.storage.local.set({ [KEY_BANNER]: enabled === true });
}

/** @returns {Promise<Record<string, number>>} broker id -> time (ms) until which it is hidden */
async function readDismissed() {
  const stored = await api.storage.local.get(KEY_DISMISSED);
  const value = stored[KEY_DISMISSED];
  return value && typeof value === "object" ? value : {};
}

/**
 * @param {string} brokerId
 * @param {number} [now]
 * @returns {Promise<boolean>}
 */
export async function isDismissed(brokerId, now = Date.now()) {
  const until = (await readDismissed())[brokerId];
  return typeof until === "number" && until > now;
}

/**
 * Remember "Not now" for one broker. Old entries are dropped on the way.
 * @param {string} brokerId
 * @param {number} [now]
 */
export async function dismissBroker(brokerId, now = Date.now()) {
  const current = await readDismissed();
  /** @type {Record<string, number>} */
  const kept = {};
  for (const [id, until] of Object.entries(current)) {
    if (typeof until === "number" && until > now) kept[id] = until;
  }
  kept[brokerId] = now + DISMISS_DAYS * DAY_MS;
  await api.storage.local.set({ [KEY_DISMISSED]: kept });
}

/** Forget every "Not now" choice. */
export async function clearDismissed() {
  await api.storage.local.remove(KEY_DISMISSED);
}
